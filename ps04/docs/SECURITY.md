# PS-04 Security Notes

This document describes what the code in `ps04/app` actually does. Where something is not done, it says so.

## 1. Roles and permissions

| Capability | System admin | Client admin (own tenant) | Client employee (own tenant) |
|---|---|---|---|
| Create/list/suspend tenants, create users and memberships | yes | no | no |
| Offboard a user (disable, revoke sessions, remove memberships) | yes | no | no |
| Read all audit events (`/admin/audit`) | yes | no | no |
| Read tenant audit (`/tenants/{tid}/audit`) | no (not a member) | yes | no |
| Verify ledger (`/audit/verify`) | yes (full detail) | yes (`ok` only) | no (403) |
| Write ledger checkpoint | yes | no | no |
| Manage members | no | yes | no |
| Upload documents / new versions | no | yes | no |
| Read current documents, open citations, chat | no | yes | yes |
| Read superseded versions / failed uploads of own tenant | no | yes | no |
| Create/revoke/list shares | no | yes | no |
| Read conversation history | own only | own only | own only |

The system administrator has no implicit tenant access: tenant routes check an active *membership*, and the
sysadmin has none unless one is explicitly added. `test_sysadmin_has_no_implicit_document_access` covers this.

## 2. Threat model

In scope: a user of tenant A trying to read tenant B's content (directly, via citations, via search results or scoring,
via conversation ids, via natural-language tricks); hostile text in questions or uploaded documents; stale access
after revocation, offboarding or suspension; after-the-fact edits to audit history; login guessing.

Out of scope / not defended: an attacker with code execution on the host; an attacker holding both the database and
`PS04_SECRET`; a malicious system administrator (they can create users and add themselves to tenants, though this is
logged); data at rest (the SQLite file is not encrypted); denial of service; TLS (terminate it in front of the app);
side channels; a compromised dependency.

## 3. Tenant isolation

Three layers, all server-side:

1. **Authentication.** Tokens are HMAC-signed session ids; each request also looks up the session row, which must be
   unrevoked, unexpired and belong to an `active` user. Offboarding revokes sessions immediately.
2. **Per-route membership checks.** Every `/tenants/{tid}/...` route calls `member()`/`role_in()`, which requires an
   `active` membership in an `active` tenant (and `client_admin` for admin routes). The tenant id in the path is
   never trusted on its own. Failure returns the same `404 Not found` whether the tenant exists or not, and is
   written to the ledger as `access.denied`. A suspended tenant therefore fails closed for everyone in it.
3. **SQL predicate in retrieval.** `retrieval.VISIBLE` is part of the SQL that selects candidate chunks: a chunk is
   visible only if its document belongs to the caller's tenant, or an unrevoked, unexpired `shares` row exists from
   the owner to the caller's tenant (document-scoped or whole-KB) and the owner tenant is `active`. Search, document
   listing/reading and citation opening all use it. Other tenants' chunks are never loaded, scored or passed to
   answer generation, and BM25 statistics (IDF, average length) are computed only over the authorised set. Only
   current, `ready` versions are searched.

Uniform 404: unknown ids and forbidden ids return identical responses (`test_unknown_and_forbidden_documents_are_indistinguishable`).
Login returns the same error for unknown email and wrong password and does a dummy hash for unknown emails; five failures
in 300 s locks the email (429).

Conversations are keyed by (tenant, user): a conversation id from another user or tenant is a 404.

## 4. Prompt injection

The answer path (`answer.py`) is extractive: output is built only from sentences found in authorised chunks. There is no
generative model that could be instructed, and nothing the question or a document says can change which tenant is
queried, which tools run, or what is visible (those come from the authenticated session and the SQL predicate).
On top of that, a regex (`INJECTION`) flags instruction-like text:

- In a question: `question_flagged: true` in the response and a `security.injection_suspected` ledger event. The query
  is still answered from authorised evidence only (normally producing `insufficient_evidence`).
- In a document: matching sentences are excluded from evidence, counted in `flagged_document_sentences`, and logged.

Limits: the regex is a heuristic and will miss rephrasings and may flag benign text. Containment relies on the
architecture (no generative model, access control outside the answer path), not on detection. If a generative model
is added later, the same property must be kept: access decisions happen before text reaches it.

## 5. Sharing model

- Owner client admin grants a share to one other tenant: for one document (`document_id`) or the whole KB (no
  document), optionally with `expires_at`. Grants are one directional.
- Effective immediately on grant and on revoke (`revoked_at` set); there is no cache. Expired grants and grants from a
  suspended owner are ignored by the same SQL predicate.
- Shared results are marked `shared_from` in citations. Each use writes `share.used` to the owner's side of the ledger
  (`counterparty` = the user's tenant), and grants/revocations are logged as `share.grant`/`share.revoke`.
- Grantees get only current versions of shared documents; superseded versions stay owner-admin only.
- Shares do not chain: a grantee cannot re-share what it received (the share endpoint only accepts documents owned by the tenant).
- Conversation history already containing shared content is not retroactively redacted when a share is revoked (answers
  are stored in the grantee's own conversation). Opening the citations and re-querying are blocked.

## 6. Audit ledger ("blockchain-lite")

Design (`audit.py`): each event is `(seq, ts, tenant, counterparty, actor, action, details)`. `hash = SHA-256(prev_hash | canonical_json(event))`,
genesis `0`*64. Appends happen inside the same SQLite transaction as the action they record, so both commit or neither does.
Every `checkpoint_every` (10) events, and on `POST /audit/checkpoint`, a line `{seq, hash, ts, mac}` is appended to
`audit_checkpoints.jsonl`, with `mac = HMAC-SHA256(key, seq|hash)`. The key is derived through the simulated TEE key release.
`verify` recomputes the chain (sequence gaps/reorder, prev-hash links, event hashes) and then checks each checkpoint's
MAC, existence and hash. Events hold ids and digests only: questions are stored as SHA-256, document text is never written.

Detects: edited, deleted, inserted or reordered events; tail truncation back past a checkpoint; a complete re-hash of the
chain by someone without the checkpoint key (when a checkpoint covers the rewritten range); forged or edited checkpoints.

**Honest limitations**
- Not a distributed or immutable ledger. Single node; there is no consensus and no external anchor.
- Anyone holding the DB **and** the signing secret (`PS04_SECRET`) can rewrite history and re-sign checkpoints.
- Truncation of events newer than the latest checkpoint, or deletion of the checkpoint file, is not detected: an
  attacker who drops events after the last checkpoint, or removes the whole checkpoint file, leaves a chain that verifies.
  Checkpoint the head and copy the file off-box regularly to narrow this.
- Rewrites after the last checkpoint with a full re-hash are not detected either, for the same reason.
- Detection only; nothing prevents modification, and `verify` must be run (CLI or endpoint) to notice.
- Timestamps come from the host clock.
- Failed-login and denied-access events are logged, so the log can grow under attack (no rate-limit on denials).

## 7. TEE integration (SIMULATED)

**This is a simulation. No hardware enclave (SGX, SEV-SNP, Nitro) is used and nothing here proves anything about the host.**
`tee.py` defines the interface a real backend would implement: `attest(nonce)` returns a report with a code measurement
(SHA-256 over `answer.py`, `retrieval.py`, `audit.py`, `ingest.py`) signed with an HMAC using `PS04_SECRET`;
`verify(report, expected_measurement)` checks the signature and measurement; `release_key(purpose, report, expected)`
returns a key only when verification passes. The ledger checkpoint key is obtained through this path at startup.
`GET /security/status` reports `mode: "simulated"`, `hardware_backed: false`, `enabled: false`. Nonces are not
tracked for freshness, there is no stale-evidence check, and the "attester" and "verifier" share one secret, so it is
a policy-shape demonstration only.

## 8. Operational notes

Fails closed without `PS04_SECRET` (>= 16 chars). Passwords use PBKDF2-SHA256 (200k iterations). Responses carry a CSP,
`nosniff` and `no-store`. Uploads are limited to `.txt/.md/.pdf` and 5 MiB, filenames are stripped to their basename, and
parse failures are visible (422, status `failed`) without replacing the previous current version. No outbound network
calls are made; there is no model to download, hence no online fallback to disable.

## 9. Spec section 11 test mapping

Tests are in `ps04/tests`. Run `python -m pytest`. "None" means no automated test exists.

| Spec 11 item | Test(s) |
|---|---|
| A asks own policy: permitted | `test_isolation.py::test_employee_gets_grounded_answer_with_citation` |
| A asks B's exact document: denied, no existence leak | `test_isolation.py::test_document_and_citation_endpoints_enforce_same_policy`, `test_unknown_and_forbidden_documents_are_indistinguishable` |
| A asks indirectly for B's data: no B retrieval | `test_isolation.py::test_cross_tenant_query_never_returns_other_tenant_content` |
| Change tenant id in request | `test_isolation.py::test_cannot_use_other_tenant_context` |
| Other tenant's citation endpoint | `test_isolation.py::test_document_and_citation_endpoints_enforce_same_policy` |
| Revoke share: retrieval, citations, history | `test_sharing_audit.py::test_revocation_blocks_retrieval_and_source_access_immediately` (history redaction is not implemented; see section 5) |
| Injection: "ignore previous instructions" | `test_grounding.py::test_question_injection_cannot_widen_scope` |
| Injection: uploaded document | `test_grounding.py::test_injection_text_in_document_is_not_evidence_and_is_flagged` |
| Retrieved content asks for tool/secrets | `test_grounding.py::test_document_cannot_grant_access` (no tool-calling exists in the app) |
| User overrides tenant in natural language | `test_grounding.py::test_question_injection_cannot_widen_scope` (the "I am an administrator of Beta" case) |
| Supported question, current-version citation | `test_isolation.py::test_employee_gets_grounded_answer_with_citation`, `test_grounding.py::test_new_version_supersedes_old_and_is_cited`, `test_citation_quote_is_verbatim_from_cited_chunk` |
| Unsupported question: `insufficient_evidence` | `test_grounding.py::test_unsupported_question_is_refused`, `test_partial_overlap_does_not_hallucinate` |
| Contradictory current docs: conflict, cite both | `test_grounding.py::test_conflict_within_authorised_sources`, `test_polarity_conflict` (outcome string is `conflict_detected`, not the spec's `conflicting_sources`) |
| Superseded document excluded | `test_grounding.py::test_new_version_supersedes_old_and_is_cited`, `test_superseded_version_readable_only_by_owner_admin` |
| Citation irrelevant/missing text rejected | `test_grounding.py::test_citation_quote_is_verbatim_from_cited_chunk` (quotes are checked against the cited chunk) |
| Missing page/section metadata not fabricated | Partial: `test_grounding.py::test_pdf_ingestion_with_page_numbers` checks real page numbers; no test for absent metadata |
| Corrupt/unsupported file: visible failure | `test_grounding.py::test_upload_validation`, `test_failed_first_upload_is_not_available_but_visible_to_admin`, `test_failed_version_does_not_replace_current` |
| Replacement upload: new active, old retained | `test_grounding.py::test_new_version_supersedes_old_and_is_cited`, `test_superseded_version_readable_only_by_owner_admin`, `test_sha256_and_metadata_recorded` |
| Smoke test with network blocked | `test_sharing_audit.py::test_full_flow_works_with_network_blocked` |
| Remove a required local model: clear error | None: the app has no local model (extractive, BM25) |
| Ledger: change payload | `test_sharing_audit.py::test_detects_modified_event` |
| Ledger: break previous-hash link | Covered by `test_detects_modified_event` / `test_detects_full_rehash_rewrite_via_checkpoint`; no dedicated prev_hash-only test |
| Ledger: delete or reorder | `test_detects_deleted_middle_event`, `test_detects_reordered_events`, `test_detects_tail_truncation_via_checkpoint` |
| Ledger: intact passes | `test_sharing_audit.py::test_clean_ledger_verifies` |
| Ledger: unauthorised read/alter denied | `test_clean_ledger_verifies` (employee gets 403 on verify), `test_isolation.py::test_employee_cannot_administer`, `test_denials_are_audited`; the app exposes no write endpoint for events |
| TEE: valid attestation permitted | `test_sharing_audit.py::test_simulated_key_release_requires_matching_measurement` |
| TEE: invalid/unapproved evidence denied, no key | `test_simulated_key_release_requires_matching_measurement` (wrong measurement, tampered report); stale/missing evidence: no test |
| TEE: simulated clearly labelled | `test_sharing_audit.py::test_security_status_is_honest_about_tee` |

Additional tests: sharing (`test_no_access_without_grant_then_access_with_grant`, `test_grant_is_scoped_to_the_named_document`,
`test_whole_kb_grant_covers_future_documents`, `test_expired_grant_is_ignored`, `test_sharing_is_one_directional`,
`test_only_owner_admin_can_grant_or_revoke`, `test_share_history_and_usage_are_audited_for_both_sides`,
`test_suspended_owner_stops_sharing`), lifecycle (`test_offboarding_revokes_access_immediately`,
`test_removed_member_loses_tenant_access_but_keeps_session`, `test_suspended_tenant_fails_closed`,
`test_login_lockout_and_no_user_enumeration`, `test_conversations_are_private_to_their_user`, `test_no_token_or_bad_token_denied`),
and ledger content (`test_audit_covers_required_events`, `test_ledger_never_stores_question_text_or_document_text`,
`test_forged_checkpoint_rejected`, `test_ledger_event_is_atomic_with_action`).

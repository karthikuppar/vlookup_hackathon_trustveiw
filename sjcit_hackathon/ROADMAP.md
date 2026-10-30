# AegisKB roadmap: what to do next

Written after the security review in PR #3. Items are ordered by priority inside each section. Every item has a **done when** line so it can be checked rather than argued about. "Exists" notes say what the code already does, so nobody rebuilds it.

Legend: **P0** do before anything is shown to real users, **P1** next sprint, **P2** when time allows.

---

## 0. Right now (housekeeping)

| # | Task | Done when |
|---|---|---|
| 0.1 | Tell the repo owner about the two critical holes fixed in PR #3 (anonymous self-registration as `system_admin`; any tenant admin could corrupt the shared audit ledger). Both were public on `main`. | Owner has read PR #3 and replied |
| 0.2 | Review and merge PR #3. | PR merged; `main` passes the suite |
| 0.3 | Decide the fate of PR #2 (`ps04/`, a separate parallel implementation). Two implementations of the same product will drift. Either merge it as a reference build or close it and port what is useful (see 4.1). | PR #2 merged or closed with a note |
| 0.4 | Click through the app in a browser: register toggle, 403/429 messages, ledger filters, tamper-simulation card, injection-warning banner. Nobody has done this yet. | A short checklist with screenshots in the PR |
| 0.5 | Fix the flaky `test_12_performance_benchmark_graph_vs_fallback` (asserts avg latency under 50 ms; fails on slower machines). Make the threshold configurable (`AEGIS_BENCH_MAX_MS`) and report the number. | Passes on a laptop and in CI |

---

## 1. Required before real use (P0)

These are gaps that remain after PR #3. They are listed in `SECURITY.md` as known limitations.

| # | Task | Done when |
|---|---|---|
| 1.1 | **Tenant-scope the admin metrics.** `/api/admin/nlp-stats`, `/api/admin/interaction-metrics`, `/api/graph/stats` return cross-tenant aggregates to any `client_admin`. Filter by the caller's tenant; only `system_admin` sees global numbers. | A `client_admin` of tenant A cannot infer tenant B's document/chunk/vocabulary counts (test added) |
| 1.2 | **Token lifecycle.** Access tokens live 60 min and cannot be revoked. Add a server-side session/`jti` table, logout, "sign out everywhere", revoke on password change and on user removal, and short access tokens with rotating refresh tokens. | Removing a user invalidates their token immediately (test) |
| 1.3 | **User management.** There is no way to disable or remove a user, change a role, reset a password, or force a password change on first login. Demo accounts and bootstrap admins should be forced to change the password. | Admin UI + endpoints + audit events + tests |
| 1.4 | **Password policy.** Minimum length is 8 and there is no breach/common-password check. Raise to 12, block the top common passwords locally (offline list), and reject a password equal to the email. | Weak passwords rejected (test) |
| 1.5 | **Gateway-level rate limits.** Current limits are in-memory per process. Put the same limits at the reverse proxy (nginx/Caddy) and keep the app limits as a second layer. Trust `X-Forwarded-For` only from the proxy's address. | Documented proxy config; limits hold with 2+ workers |
| 1.6 | **Transport and cookies.** Terminate TLS at the proxy, set HSTS, and add `Secure`/`SameSite` settings if any cookie is introduced. Add a production checklist that fails startup when `AEGIS_ENV=production` and a secret/key/CORS origin is missing or default. | Startup self-check with clear errors |
| 1.7 | **Encryption at rest.** Uploaded content and the SQLite file are plaintext. Add field- or file-level encryption keyed from the environment (and, when real hardware exists, from a TEE key release). | Documented threat model; DB file unreadable without the key |
| 1.8 | **Backups and migrations.** `init_db` uses ad-hoc `ALTER TABLE`. Add numbered migrations, a backup/restore command, and a ledger export that can be verified offline. | `migrate` and `backup` commands + a restore test |
| 1.9 | **Ledger anchoring.** Checkpoints are signed with a local key in the same database. Write checkpoints to a second location (a separate file/volume, or printed hashes in a signed report) so a database-only attacker cannot rewrite history silently. | Verify detects rewriting the DB while the external checkpoint file is intact |
| 1.10 | **Dependency and secret hygiene.** Pin versions (`requirements.txt` pins only `bcrypt`), add `pip-audit`/`npm audit` to CI, add a secrets scanner (gitleaks) so keys are never committed. | CI fails on a known-vulnerable dependency or a committed secret |

---

## 2. Retrieval quality (P1)

**Exists today:** adaptive hybrid retrieval (TF-IDF + BM25, optional local dense embeddings with a TruncatedSVD fallback, reciprocal-rank fusion, a small SOP graph), typo/acronym dictionary, intent classifier, extractive answers, a conflict response, unresolved-query logging, and a benchmark suite (`tests/test_trustview_intelligence_benchmark.py`). Improve what is measurable; do not rewrite it.

| # | Task | Why | Done when |
|---|---|---|---|
| 2.1 | **Evaluation harness first.** Build a gold set of 50 to 100 questions with expected document/section citations, expected refusals and expected conflicts, per demo tenant. Report recall@k, MRR, citation accuracy, refusal precision/recall and p95 latency, and fail CI on regressions. | Without it every change below is guesswork. The existing benchmark checks a few cases; this makes it a gate | `python -m eval` prints a table; CI blocks a drop of more than 2 points |
| 2.2 | **Real local embeddings.** `embedding_manager` silently falls back to SVD when the BAAI/bge-small-en directory is missing. Ship a documented model download step (or vendor a quantised ONNX model), surface "semantic: on/off" in the admin hub, and fail loudly in production if it is off. "Money back" must find "refund". | Paraphrases are the most common failure of lexical search | Recall@5 on the paraphrase subset improves by a measured margin |
| 2.3 | **Better answer-sentence selection.** Scoring by term coverage is blunt (it caused one wrong-tenant answer and one refused refund question in the reference build). Add a local cross-encoder reranker, or a small local model that may only quote retrieved text. Add a **verifier**: every quoted span must appear verbatim in the cited chunk, otherwise the answer is downgraded to "insufficient evidence". | Keeps the "cannot invent" guarantee while answering more questions | Verifier test: a fabricated quote is always rejected |
| 2.4 | **Query understanding.** Per-tenant synonym and acronym lists managed by admins (the current dictionary is hardcoded), plus follow-up resolution from conversation history ("what about for enterprise?"). Learn from the unresolved-query log with admin approval. | Employees ask in their own words | Follow-up set in the eval passes |
| 2.5 | **Smarter chunking.** Overlap between chunks, keep tables and numbered lists together, detect headings in PDFs by font size (section metadata is mostly empty for PDFs), and carry page numbers. | Better citations and fewer split answers | Chunk-quality tests on a sample of real SOP PDFs |
| 2.6 | **Better conflict detection.** Today it compares numbers and mandatory/optional wording. Add dates, named entities, `must`/`should`/`may` strength, units, and say **which source is newer** and which version is current. | Conflicts are a headline feature | Conflict cases in the eval set, with a false-positive budget |
| 2.7 | **Freshness and ownership.** Show last-updated date, owner and review-due date per document; warn when an answer cites a stale SOP. | Trust | Visible in citations and the document list |
| 2.8 | **Multilingual.** Decide whether non-English questions are in scope; if yes, use a multilingual local embedding model and extend the injection guard (it is English-only). | Injection filters are weakest in other languages | Decision recorded; tests if in scope |

---

## 3. UI (P1/P2)

**Exists today (verify in the browser):** login/register toggle, grounded chat with citations, documents and versions, sharing, audit ledger view with filters, TEE view, admin hub. Not found in `ChatView`: suggested questions, per-answer feedback, conversation history sidebar.

| # | Task | Done when |
|---|---|---|
| 3.1 | **Source panel.** Show the cited passage beside the answer with the quoted sentence highlighted, plus document, version, page and section. | Clicking a citation opens the passage at the right place |
| 3.2 | **Inline `[1]` markers** that scroll to the citation; colour-coded outcome cards (grounded / insufficient / conflict / refusal); conflicts as a side-by-side comparison with the newer source marked. | Visual check + a11y check |
| 3.3 | **Streaming and progress.** Stream answers and show "searching N authorised documents" while waiting. | No blank wait over 300 ms |
| 3.4 | **Feedback loop.** Thumbs up/down with a reason; wrong answers feed the evaluation set (2.1) and the knowledge-gap tickets that already exist in the backend. | Feedback visible to admins and exportable as eval cases |
| 3.5 | **Conversation history** in a sidebar, per user, with delete. Suggested questions per tenant (admin-curated). | Works after reload |
| 3.6 | **Admin ergonomics.** Drag-and-drop upload with live ingestion status and the injection-warning banner; version diff view; a sharing wizard with a tenant picker and expiry; audit timeline with filters, export (formula-safe CSV) and a tamper-check badge; user management screens (1.3). | Admin can complete each task without the API |
| 3.7 | **Accessibility and themes.** Dark/light mode, keyboard shortcuts, ARIA labels, contrast (WCAG AA), reduced-motion, 360 px layouts. Add an automated axe check to CI. | Zero serious axe violations |
| 3.8 | **Frontend tests.** None exist besides the markdown test. Add component tests (Vitest + Testing Library) for login, chat, upload and the ledger view, and one end-to-end run (Playwright) against a seeded backend. | CI runs them |
| 3.9 | **Content-Security-Policy for the frontend host.** The API sends `default-src 'none'`; the static host serving the React build needs its own strict CSP (no inline scripts; styles from the build only). | CSP header on the dev preview and the production host |

---

## 4. Code quality and delivery (P1/P2)

| # | Task | Done when |
|---|---|---|
| 4.1 | **One implementation.** `ps04/` (reference build) and `sjcit_hackathon/` (the product) overlap. Port the useful parts of `ps04` (strict per-route authorisation tests, ledger tamper tests, evaluation of answers) and retire the duplicate. | One app, one test suite |
| 4.2 | **Split `backend/main.py`** (about 1,400 lines) into routers (`auth`, `clients`, `documents`, `chat`, `audit`, `admin`) with shared dependencies. | No file over about 400 lines |
| 4.3 | **Replace deprecated startup hooks** (`@app.on_event`) with lifespan handlers; move globals (vector DB, graph, limiter) behind app state so tests do not share state. | No deprecation warnings |
| 4.4 | **Type checking and linting for Python** (`ruff`, `mypy` or `pyright`) alongside the existing ESLint. | CI green |
| 4.5 | **CI.** One workflow: backend tests, frontend lint/build/tests, dependency audit, secret scan. Required status checks on `main`; protect `main` (no direct pushes). | Branch protection on |
| 4.6 | **Observability.** Structured logs with request ids (never log tokens or document text), health/readiness endpoints, basic metrics. | Logs reviewed for secrets |
| 4.7 | **Deployment.** Dockerfile exists for the backend; add a compose file with the proxy, volumes for the database and keys, and a non-root user. | `docker compose up` gives a hardened stack |
| 4.8 | **Docs.** Replace the copied/outdated README sections: run instructions (including `AEGIS_SEED_DEMO`), architecture, roles, API list, threat model, and the demo script against the spec's acceptance criteria. | New teammate can run it in 10 minutes |

---

## 5. Honest status vs the spec

Keep these labels accurate in the UI and docs; do not oversell.

- **TEE:** simulated. Real attestation needs supported hardware (SGX / SEV-SNP / TDX / Nitro); until then keep the "SIMULATED" banner.
- **Audit ledger:** a local hash chain with signed checkpoints. It detects edits, deletions, reordering and truncation, not an attacker who holds both the database and the key. Do not call it immutable.
- **Offline:** the app makes no outbound calls, but the model download step (2.2) and any package install need a one-time online step; document it.
- **Multi-tenant model:** the owner's docs now describe two roles (Employee and Main Admin) while the code and the spec are multi-tenant. Decide which is the product, then make the docs, UI wording and tests agree.

---

## Suggested order

1. Section 0 (this week).
2. 1.1, 1.2, 1.3, 1.4 and 1.10 (closes the remaining authorisation and supply-chain gaps).
3. 2.1 (evaluation harness), then 2.2 and 2.3, measuring each against the gold set.
4. 3.1 to 3.4 (what users notice), with 3.8 so the UI does not regress.
5. 1.5 to 1.9 and 4.x before any real deployment.

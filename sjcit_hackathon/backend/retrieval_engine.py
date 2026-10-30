"""Grounded retrieval engine — tenant-isolated, offline, AI-feeling responses.

Key improvements over v1:
- Intent-aware routing (greetings, help, onboarding, knowledge)
- Synonym/semantic query expansion to increase recall on natural language
- Sentence-level extraction instead of raw chunk dumps
- Conversational answer synthesis via response_synthesizer
- Smarter relevance threshold: lower floor + score normalization
- Better conflict detection with per-doc deduplication
"""
from __future__ import annotations
import math
import re
import uuid
from collections import Counter
from typing import Any

from crypto_utils import now_utc_iso, sha256_digest
from database import get_connection
from ledger_engine import AuditLedger
from response_synthesizer import (
    GREETING_RESPONSES,
    HELP_RESPONSE,
    build_conflict_response,
    build_grounded_answer,
    build_insufficient_evidence_response,
    classify_intent,
    expand_query_tokens,
)
from sharing_service import SharingService

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself",
}


def tokenize(text: str) -> list[str]:
    """Tokenize, normalize, and filter to meaningful query terms."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = clean.split()
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def compute_chunk_relevance(query_tokens: list[str], chunk_text: str) -> float:
    """
    Compute relevance of a chunk against expanded query tokens.

    Scoring factors:
    - TF / sqrt(chunk_length) per matched token (BM25-inspired)
    - Match ratio bonus (reward chunks covering more of the query)
    - Bigram phrase proximity bonus
    - Section-header bonus (numbered / titled sections get a boost)
    - SOP action-verb density bonus

    Returns 0.0 if ZERO query tokens match (prevents spurious verb-density hits).
    """
    if not query_tokens:
        return 0.0
    text_lower = chunk_text.lower()
    chunk_tokens = tokenize(chunk_text)
    if not chunk_tokens:
        return 0.0

    chunk_len = max(len(chunk_tokens), 1)
    chunk_counter = Counter(chunk_tokens)
    matched_terms = 0
    score = 0.0

    for token in query_tokens:
        if token in chunk_counter:
            matched_terms += 1
            tf = chunk_counter[token] / math.sqrt(chunk_len)
            score += tf * 2.0

    # Hard gate: at least 1 actual query token must appear in the chunk
    if matched_terms == 0:
        return 0.0

    match_ratio = matched_terms / len(query_tokens)
    score += match_ratio * 4.0

    # Bigram phrase bonus
    for i in range(len(query_tokens) - 1):
        bigram = f"{query_tokens[i]} {query_tokens[i + 1]}"
        if bigram in text_lower:
            score += 2.5

    # Section header bonus (numbered steps, bold-like markers)
    if re.search(r"^\d+[\.\)]|\bstep\s+\d+\b|\bsection\b|\bprocedure\b|\bpolicy\b", text_lower):
        score += 1.0

    # SOP action-verb density
    sop_verbs = ["must", "shall", "required", "ensure", "submit", "contact", "report", "complete",
                 "notify", "request", "approve", "review", "sign", "escalate", "follow"]
    verb_count = sum(1 for v in sop_verbs if v in text_lower)
    score += min(verb_count * 0.3, 1.5)

    return score


def detect_conflicts(matching_chunks: list[dict[str, Any]]) -> tuple[bool, str, list[dict[str, Any]]]:
    """
    Detect contradictory rules between distinct top-ranked SOP chunks.
    Returns (has_conflict, conflict_summary, conflicting_chunks).
    """
    if len(matching_chunks) < 2:
        return False, "", []

    for i in range(len(matching_chunks)):
        for j in range(i + 1, len(matching_chunks)):
            c1 = matching_chunks[i]
            c2 = matching_chunks[j]

            # Skip duplicates from same doc/version
            if c1["doc_id"] == c2["doc_id"]:
                continue

            t1, t2 = c1["text"].lower(), c2["text"].lower()

            # Timeframe conflicts
            nums1 = re.findall(r"(\d+)\s*(days?|hours?|weeks?|months?)", t1)
            nums2 = re.findall(r"(\d+)\s*(days?|hours?|weeks?|months?)", t2)
            for val1, unit1 in nums1:
                for val2, unit2 in nums2:
                    if unit1 == unit2 and val1 != val2:
                        summary = (
                            f"**{c1['title']}** (v{c1['version_num']}) specifies **{val1} {unit1}**, "
                            f"while **{c2['title']}** (v{c2['version_num']}) specifies **{val2} {unit2}**."
                        )
                        return True, summary, [c1, c2]

            # Mandatory vs optional
            req1 = any(w in t1 for w in ("mandatory", "required", "must", "shall", "compulsory"))
            opt2 = any(w in t2 for w in ("optional", "voluntary", "discretionary", "may choose"))
            req2 = any(w in t2 for w in ("mandatory", "required", "must", "shall", "compulsory"))
            opt1 = any(w in t1 for w in ("optional", "voluntary", "discretionary", "may choose"))
            if req1 and opt2:
                return True, (
                    f"**{c1['title']}** marks this as **mandatory/required**, while "
                    f"**{c2['title']}** marks it as **optional/voluntary**."
                ), [c1, c2]
            if req2 and opt1:
                return True, (
                    f"**{c2['title']}** marks this as **mandatory/required**, while "
                    f"**{c1['title']}** marks it as **optional/voluntary**."
                ), [c2, c1]

            # Forbidden vs allowed
            forb1 = any(w in t1 for w in ("strictly forbidden", "prohibited", "not allowed", "disallowed"))
            allow2 = any(w in t2 for w in ("permitted", "allowed", "authorized", "acceptable"))
            if forb1 and allow2:
                return True, (
                    f"**{c1['title']}** explicitly **prohibits** this action, while "
                    f"**{c2['title']}** marks it as **permitted/allowed**."
                ), [c1, c2]

    return False, "", []


class RetrievalEngine:
    @staticmethod
    def query_knowledge_base(
        user_id: str,
        user_tenant_id: str,
        question: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Tenant-isolated knowledge retrieval with conversational answer synthesis.

        Guarantees:
        1. Tenant scope enforced in data layer BEFORE any retrieval.
        2. Natural-language prompt injection cannot bypass tenant isolation.
        3. Answers cite only authorized active document versions.
        4. Intent-aware routing: greetings/help get instant conversational responses.
        5. Synonym expansion improves recall on natural employee queries.
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        query_hash = f"sha256:{sha256_digest(question)}"

        # ---- Intent Classification (handle non-knowledge intents instantly) ----
        intent = classify_intent(question)

        if intent == "greeting":
            import hashlib
            idx = int(hashlib.md5(question.encode()).hexdigest(), 16) % len(GREETING_RESPONSES)
            return {
                "request_id": request_id,
                "answer_status": "conversational",
                "answer": GREETING_RESPONSES[idx],
                "citations": [],
                "limitations": None,
                "is_shared_knowledge_used": False,
            }

        if intent == "help":
            return {
                "request_id": request_id,
                "answer_status": "conversational",
                "answer": HELP_RESPONSE,
                "citations": [],
                "limitations": None,
                "is_shared_knowledge_used": False,
            }

        # ---- Tenant Authorization: resolve permitted scope ----
        active_shared_tenants = SharingService.get_active_shared_tenants_for_user(user_tenant_id)
        permitted_tenants = [user_tenant_id] + active_shared_tenants

        placeholders = ",".join("?" for _ in permitted_tenants)
        sql = f"""
            SELECT c.id AS chunk_id, c.doc_id, c.version_num, c.tenant_id, c.page, c.section, c.text,
                   d.title, d.original_filename
            FROM document_chunks c
            JOIN document_versions v ON c.doc_id = v.doc_id AND c.version_num = v.version_num
            JOIN documents d ON c.doc_id = d.id
            WHERE c.tenant_id IN ({placeholders}) AND v.status = 'active'
        """

        with get_connection() as conn:
            rows = conn.execute(sql, permitted_tenants).fetchall()

        all_chunks = [dict(r) for r in rows]

        # ---- Query Expansion ----
        base_tokens = tokenize(question)
        expanded_tokens = expand_query_tokens(base_tokens) if base_tokens else base_tokens

        # Special handling for onboarding intent: add rich onboarding tokens
        if intent == "onboarding":
            extra = ["onboarding", "first", "day", "new", "hire", "checklist",
                     "start", "orientation", "begin", "join", "welcome"]
            seen = set(expanded_tokens)
            for e in extra:
                if e not in seen:
                    expanded_tokens.append(e)

        # ---- Lexical Scoring ----
        scored_chunks: list[tuple[float, dict[str, Any]]] = []
        for chunk in all_chunks:
            score = compute_chunk_relevance(expanded_tokens, chunk["text"])
            if score > 1.4:  # Threshold: needs at least meaningful token match
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # ---- De-duplicate by doc+section (keep best score per section) ----
        seen_sections: dict[str, float] = {}
        deduped: list[tuple[float, dict[str, Any]]] = []
        for score, chunk in scored_chunks:
            key = f"{chunk['doc_id']}|{chunk.get('section', '')}|{chunk.get('page', '')}"
            if key not in seen_sections or seen_sections[key] < score:
                seen_sections[key] = score
                deduped.append((score, chunk))

        deduped.sort(key=lambda x: x[0], reverse=True)

        # ---- OUTCOME: Insufficient Evidence ----
        if not deduped:
            answer_text = build_insufficient_evidence_response(question)
            AuditLedger.append_event(
                event_type="chat_query_processed",
                actor_id=user_id,
                tenant_id=user_tenant_id,
                resource_id=request_id,
                action="query_knowledge_base",
                decision="insufficient_evidence",
                details={"query_hash": query_hash, "citations_count": 0},
            )
            return {
                "request_id": request_id,
                "answer_status": "insufficient_evidence",
                "answer": answer_text,
                "citations": [],
                "limitations": "No relevant SOP content found in your authorized active documents.",
                "is_shared_knowledge_used": False,
            }

        top_chunks = [c for _, c in deduped[:5]]

        # ---- OUTCOME: Conflict Detection ----
        has_conflict, conflict_summary, conflicting_chunks = detect_conflicts(top_chunks)
        if has_conflict:
            answer_text = build_conflict_response(conflict_summary)
            citations = [
                {
                    "doc_id": c["doc_id"],
                    "version_num": c["version_num"],
                    "title": c["title"],
                    "page": c["page"],
                    "section": c["section"],
                    "excerpt": c["text"][:300] + ("..." if len(c["text"]) > 300 else ""),
                    "is_shared": c["tenant_id"] != user_tenant_id,
                    "source_tenant": c["tenant_id"],
                }
                for c in conflicting_chunks
            ]
            is_shared_used = any(c["tenant_id"] != user_tenant_id for c in conflicting_chunks)

            AuditLedger.append_event(
                event_type="chat_query_processed",
                actor_id=user_id,
                tenant_id=user_tenant_id,
                resource_id=request_id,
                action="query_knowledge_base",
                decision="conflicting_sources",
                details={"query_hash": query_hash, "conflict_summary": conflict_summary},
            )
            return {
                "request_id": request_id,
                "answer_status": "conflicting_sources",
                "answer": answer_text,
                "citations": citations,
                "limitations": "Active documents contain contradictory guidelines on this topic.",
                "is_shared_knowledge_used": is_shared_used,
            }

        # ---- OUTCOME: Grounded Answer ----
        answer_text = build_grounded_answer(question, expanded_tokens, top_chunks)

        citations = [
            {
                "doc_id": c["doc_id"],
                "version_num": c["version_num"],
                "title": c["title"],
                "page": c["page"],
                "section": c["section"],
                "excerpt": c["text"][:300] + ("..." if len(c["text"]) > 300 else ""),
                "is_shared": c["tenant_id"] != user_tenant_id,
                "source_tenant": c["tenant_id"],
            }
            for c in top_chunks[:3]
        ]
        is_shared_used = any(c["tenant_id"] != user_tenant_id for c in top_chunks[:3])

        # Persist query log
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO query_logs (
                    id, timestamp, user_id, tenant_id, query_text, query_hash, answer_status,
                    returned_doc_ids, citation_ids, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    now_utc_iso(),
                    user_id,
                    user_tenant_id,
                    question,
                    query_hash,
                    "grounded",
                    ",".join(set(c["doc_id"] for c in citations)),
                    ",".join(set(f"{c['doc_id']}_v{c['version_num']}" for c in citations)),
                    session_id,
                ),
            )

        AuditLedger.append_event(
            event_type="chat_query_processed",
            actor_id=user_id,
            tenant_id=user_tenant_id,
            resource_id=request_id,
            action="query_knowledge_base",
            decision="grounded_answer",
            details={
                "query_hash": query_hash,
                "citations_count": len(citations),
                "is_shared_used": is_shared_used,
            },
        )

        return {
            "request_id": request_id,
            "answer_status": "grounded",
            "answer": answer_text,
            "citations": citations,
            "limitations": None,
            "is_shared_knowledge_used": is_shared_used,
        }

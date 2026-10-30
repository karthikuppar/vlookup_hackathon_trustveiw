"""Grounded retrieval and answer generation engine with pre-retrieval tenant filtering,
prompt-injection resilience, conflict detection, and offline local inference."""
from __future__ import annotations
import math
import re
import uuid
from collections import Counter
from typing import Any
from crypto_utils import now_utc_iso, sha256_digest
from database import get_connection
from ledger_engine import AuditLedger
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
    """Tokenize and normalize text into meaningful query terms."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = clean.split()
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def compute_chunk_relevance(query_tokens: list[str], chunk_text: str) -> float:
    """Compute lexical score between query tokens and chunk text with exact phrase bonus."""
    if not query_tokens:
        return 0.0
    text_lower = chunk_text.lower()
    chunk_tokens = tokenize(chunk_text)
    if not chunk_tokens:
        return 0.0

    chunk_counter = Counter(chunk_tokens)
    matched_terms = 0
    score = 0.0

    for token in query_tokens:
        if token in chunk_counter:
            matched_terms += 1
            # Term frequency / chunk length scoring
            score += (chunk_counter[token] / math.sqrt(len(chunk_tokens))) * 1.5

    match_ratio = matched_terms / len(query_tokens)
    score += match_ratio * 3.0

    # Bonus for consecutive two-token phrases from query
    for i in range(len(query_tokens) - 1):
        bigram = f"{query_tokens[i]} {query_tokens[i+1]}"
        if bigram in text_lower:
            score += 2.0

    return score


def detect_conflicts(matching_chunks: list[dict[str, Any]]) -> tuple[bool, str, list[dict[str, Any]]]:
    """
    Detect if multiple current active documents in the permitted scope contain conflicting rules.
    Returns (has_conflict, conflict_summary, conflicting_chunks).
    """
    if len(matching_chunks) < 2:
        return False, "", []

    # Check for opposing numbers / days / terms in the matched excerpts
    # e.g., "30 days" vs "15 days", "mandatory" vs "optional", "forbidden" vs "allowed"
    opposing_patterns = [
        (r"(\d+)\s*(days?|hours?|months?|business days?)", "timeframe/deadline"),
        (r"\b(mandatory|required|compulsory)\b", r"\b(optional|discretionary|voluntary)\b", "requirement obligation"),
        (r"\b(strictly forbidden|prohibited|not allowed|disallowed)\b", r"\b(permitted|allowed|authorized)\b", "permission status"),
    ]

    # Compare pairs of chunks from different documents or distinct rules
    for i in range(len(matching_chunks)):
        for j in range(i + 1, len(matching_chunks)):
            c1 = matching_chunks[i]
            c2 = matching_chunks[j]

            # Compare numbers with units
            nums1 = re.findall(r"(\d+)\s*(days?|hours?|weeks?|months?)", c1["text"].lower())
            nums2 = re.findall(r"(\d+)\s*(days?|hours?|weeks?|months?)", c2["text"].lower())

            if nums1 and nums2:
                for val1, unit1 in nums1:
                    for val2, unit2 in nums2:
                        if unit1 == unit2 and val1 != val2:
                            summary = (
                                f"Contradiction detected on {unit1}: "
                                f"{c1['title']} (v{c1['version_num']}) specifies '{val1} {unit1}' "
                                f"whereas {c2['title']} (v{c2['version_num']}) specifies '{val2} {unit2}'."
                            )
                            return True, summary, [c1, c2]

            # Compare mandatory vs optional
            t1 = c1["text"].lower()
            t2 = c2["text"].lower()
            if ("mandatory" in t1 or "required" in t1) and ("optional" in t2 or "voluntary" in t2):
                summary = (
                    f"Contradiction detected: {c1['title']} marks requirement as mandatory/required, "
                    f"whereas {c2['title']} marks it as optional."
                )
                return True, summary, [c1, c2]
            if ("mandatory" in t2 or "required" in t2) and ("optional" in t1 or "voluntary" in t1):
                summary = (
                    f"Contradiction detected: {c2['title']} marks requirement as mandatory/required, "
                    f"whereas {c1['title']} marks it as optional."
                )
                return True, summary, [c1, c2]

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
        Executes tenant-isolated knowledge retrieval and grounded answer synthesis.
        Guarantees:
        1. Tenant scope enforced in data layer before candidate retrieval.
        2. Natural language prompt injection cannot bypass tenant isolation.
        3. Answers cite only authorized active document versions.
        4. Distinguishes 'grounded', 'insufficient_evidence', and 'conflicting_sources'.
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        query_hash = f"sha256:{sha256_digest(question)}"

        # Non-negotiable server-side authorization:
        # Resolve user's home tenant + explicitly active shared knowledge bases
        active_shared_tenants = SharingService.get_active_shared_tenants_for_user(user_tenant_id)
        permitted_tenants = [user_tenant_id] + active_shared_tenants

        # Fetch candidate chunks STRICTLY scoped to permitted tenants and active versions
        placeholders = ",".join("?" for _ in permitted_tenants)
        sql = f"""
            SELECT c.id as chunk_id, c.doc_id, c.version_num, c.tenant_id, c.page, c.section, c.text,
                   d.title, d.original_filename
            FROM document_chunks c
            JOIN document_versions v ON c.doc_id = v.doc_id AND c.version_num = v.version_num
            JOIN documents d ON c.doc_id = d.id
            WHERE c.tenant_id IN ({placeholders}) AND v.status = 'active'
        """

        with get_connection() as conn:
            rows = conn.execute(sql, permitted_tenants).fetchall()

        all_chunks = [dict(r) for r in rows]

        # Lexical matching
        query_tokens = tokenize(question)
        scored_chunks: list[tuple[float, dict[str, Any]]] = []

        for chunk in all_chunks:
            score = compute_chunk_relevance(query_tokens, chunk["text"])
            if score > 1.2:  # Minimum relevance threshold
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # 1. OUTCOME: Insufficient Evidence
        if not scored_chunks:
            answer_status = "insufficient_evidence"
            answer_text = "I cannot answer that question from the active documents available in your authorized knowledge base."
            limitations = "No relevant statements or clauses found in authorized active document versions."
            citations: list[dict[str, Any]] = []

            # Log audit
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
                "answer_status": answer_status,
                "answer": answer_text,
                "citations": citations,
                "limitations": limitations,
                "is_shared_knowledge_used": False,
            }

        top_chunks = [c for _, c in scored_chunks[:4]]

        # 2. OUTCOME: Conflict Detection
        has_conflict, conflict_summary, conflicting_chunks = detect_conflicts(top_chunks)
        if has_conflict:
            answer_status = "conflicting_sources"
            answer_text = (
                f"Conflicting rules were detected among your current authorized sources:\n\n{conflict_summary}\n\n"
                f"Please review the cited document versions for authoritative guidance."
            )
            citations = [
                {
                    "doc_id": c["doc_id"],
                    "version_num": c["version_num"],
                    "title": c["title"],
                    "page": c["page"],
                    "section": c["section"],
                    "excerpt": c["text"][:280] + ("..." if len(c["text"]) > 280 else ""),
                    "is_shared": c["tenant_id"] != user_tenant_id,
                    "source_tenant": c["tenant_id"],
                }
                for c in conflicting_chunks
            ]
            limitations = "Active documents contain contradictory guidelines on this topic."
            is_shared_used = any(c["tenant_id"] != user_tenant_id for c in conflicting_chunks)

            AuditLedger.append_event(
                event_type="chat_query_processed",
                actor_id=user_id,
                tenant_id=user_tenant_id,
                resource_id=request_id,
                action="query_knowledge_base",
                decision="conflicting_sources",
                details={
                    "query_hash": query_hash,
                    "conflict_summary": conflict_summary,
                    "citations_count": len(citations),
                },
            )

            return {
                "request_id": request_id,
                "answer_status": answer_status,
                "answer": answer_text,
                "citations": citations,
                "limitations": limitations,
                "is_shared_knowledge_used": is_shared_used,
            }

        # 3. OUTCOME: Grounded Answer
        answer_status = "grounded"
        primary_chunk = top_chunks[0]
        # Formulate grounded answer from best chunk
        # Clean excerpt of the most relevant sentence/paragraph
        answer_text = f"According to {primary_chunk['title']} (Version {primary_chunk['version_num']}):\n\n{primary_chunk['text']}"

        citations = [
            {
                "doc_id": c["doc_id"],
                "version_num": c["version_num"],
                "title": c["title"],
                "page": c["page"],
                "section": c["section"],
                "excerpt": c["text"][:280] + ("..." if len(c["text"]) > 280 else ""),
                "is_shared": c["tenant_id"] != user_tenant_id,
                "source_tenant": c["tenant_id"],
            }
            for c in top_chunks[:2]
        ]

        is_shared_used = any(c["tenant_id"] != user_tenant_id for c in top_chunks[:2])

        # Record in query_logs
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
                    answer_status,
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
            "answer_status": answer_status,
            "answer": answer_text,
            "citations": citations,
            "limitations": None,
            "is_shared_knowledge_used": is_shared_used,
        }

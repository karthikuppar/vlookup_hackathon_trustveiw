"""TransparentView domain service.  Uses the existing retrieval pipeline and SQLite store."""
from __future__ import annotations
import hashlib
import json
import re
import uuid
from typing import Any

from crypto_utils import now_utc_iso
from database import get_connection

KNOWLEDGE_GAP_CONFIDENCE_THRESHOLD = 0.15
CONFIDENCE_METHOD_VERSION = "evidence-score-v1-heuristic"
OPEN_STATUSES = ("OPEN", "TRIAGED", "INVESTIGATING", "AWAITING_SOP_UPDATE", "VERIFYING", "REOPENED")
TRANSITIONS = {
    "OPEN": {"TRIAGED"}, "TRIAGED": {"INVESTIGATING"},
    "INVESTIGATING": {"AWAITING_SOP_UPDATE", "VERIFYING"},
    "AWAITING_SOP_UPDATE": {"VERIFYING"}, "VERIFYING": {"INVESTIGATING", "RESOLVED"},
    "RESOLVED": {"REOPENED"}, "REOPENED": {"TRIAGED", "INVESTIGATING"},
}

def normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value.lower())).strip()

def fingerprint(value: str) -> str:
    return hashlib.sha256(normalize_query(value).encode("utf-8")).hexdigest()[:32]

class TrustViewService:
    @staticmethod
    def record_interaction(*, interaction_id: str, query: str, user_id: str | None, tenant_id: str,
                           response_status: str, retrieval_path: str, candidate_count: int,
                           confidence: float | None, selected_candidates: list[str] | None = None) -> str | None:
        """Atomically persist diagnostics and create/associate a low-confidence ticket."""
        now = now_utc_iso()
        confidence = None if confidence is None else max(0.0, min(1.0, float(confidence)))
        fp = fingerprint(query)
        evidence_status = "PASSED" if response_status == "grounded" else "NOT_SUFFICIENT"
        methods = [retrieval_path] if retrieval_path else []
        ticket_id = None
        with get_connection() as conn:
            conn.execute("""INSERT OR IGNORE INTO trust_interactions
                (interaction_id,normalized_query,query_fingerprint,retrieval_confidence,confidence_method_version,
                 evidence_validation_status,response_status,retrieval_methods,selected_candidate_ids,knowledge_base_version)
                 VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (interaction_id, normalize_query(query), fp, confidence, CONFIDENCE_METHOD_VERSION,
                 evidence_status, response_status.upper(), json.dumps(methods), json.dumps(selected_candidates or []), "current"))
            if confidence is not None and confidence < KNOWLEDGE_GAP_CONFIDENCE_THRESHOLD:
                existing = conn.execute(f"""SELECT ticket_id FROM knowledge_gap_tickets
                    WHERE tenant_id=? AND query_fingerprint=? AND status IN ({','.join('?' * len(OPEN_STATUSES))})
                    ORDER BY updated_at DESC LIMIT 1""", (tenant_id, fp, *OPEN_STATUSES)).fetchone()
                if existing:
                    ticket_id = existing["ticket_id"]
                    conn.execute("""UPDATE knowledge_gap_tickets SET latest_interaction_id=?, interaction_count=interaction_count+1,
                        updated_at=? WHERE ticket_id=?""", (interaction_id, now, ticket_id))
                else:
                    ticket_id = f"kgt_{uuid.uuid4().hex[:12]}"
                    summary = json.dumps({"methods": methods, "candidate_count": candidate_count,
                                          "reason": "Final retrieval confidence below configured 15% threshold."})
                    conn.execute("""INSERT INTO knowledge_gap_tickets
                       (ticket_id,tenant_id,title,representative_query,query_fingerprint,employee_id,first_interaction_id,
                        latest_interaction_id,candidate_count,retrieval_summary,confidence_score,confidence_method_version,
                        knowledge_base_version,created_at,updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (ticket_id, tenant_id, "Knowledge gap: " + query[:90], query, fp, user_id, interaction_id,
                        interaction_id, candidate_count, summary, confidence, CONFIDENCE_METHOD_VERSION, "current", now, now))
                    conn.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?)",
                                 (f"tev_{uuid.uuid4().hex[:12]}", ticket_id, user_id or "system", "CREATED", None, "OPEN", None, now))
                conn.execute("INSERT OR IGNORE INTO ticket_interactions VALUES (?,?,?)", (ticket_id, interaction_id, now))
                conn.execute("UPDATE trust_interactions SET ticket_id=? WHERE interaction_id=?", (ticket_id, interaction_id))
        return ticket_id

    @staticmethod
    def transition(ticket_id: str, actor_id: str, to_status: str, note: str | None = None, verified: bool = False) -> dict:
        to_status = to_status.upper()
        with get_connection() as conn:
            ticket = conn.execute("SELECT * FROM knowledge_gap_tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
            if not ticket: raise ValueError("Ticket not found")
            old = ticket["status"]
            if to_status not in TRANSITIONS.get(old, set()): raise ValueError(f"Invalid ticket transition: {old} -> {to_status}")
            if to_status == "RESOLVED" and not verified: raise ValueError("A verified retrieval result is required before resolution")
            now = now_utc_iso()
            conn.execute("UPDATE knowledge_gap_tickets SET status=?, resolution_notes=COALESCE(?,resolution_notes), updated_at=?, resolved_at=? WHERE ticket_id=?",
                         (to_status, note, now, now if to_status == "RESOLVED" else None, ticket_id))
            conn.execute("INSERT INTO ticket_events VALUES (?,?,?,?,?,?,?,?)", (f"tev_{uuid.uuid4().hex[:12]}", ticket_id, actor_id, "STATUS_CHANGED", old, to_status, note, now))
            return dict(conn.execute("SELECT * FROM knowledge_gap_tickets WHERE ticket_id=?", (ticket_id,)).fetchone())

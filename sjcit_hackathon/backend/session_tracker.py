"""
Persistent Session and Interaction Logging Engine for Trust View.

Fulfills Section 5 of Technical Specification:
- Application run lifecycle tracking (run_id, process_id, running/completed/interrupted detection)
- User session persistence (session_id, user_id, start/end timestamps, termination reasons)
- Interaction logging for all queries (including failures and no-result responses)
- High-resolution monotonic timing (time.perf_counter) and exception-isolated DB persistence.
"""
from __future__ import annotations
import logging
import os
import time
import uuid
from typing import Any

from crypto_utils import now_utc_iso
from database import get_connection

logger = logging.getLogger("trustview.session_tracker")

_CURRENT_RUN_ID: str | None = None
_RUN_START_TIME: float = time.monotonic()


class SessionTracker:
    """Manages application runs, user sessions, and persistent interaction records."""

    @classmethod
    def start_application_run(cls, application_version: str = "1.0.0") -> str:
        """
        Record a new application execution run.
        Detects any unclosed previous runs and marks them as 'interrupted'.
        """
        global _CURRENT_RUN_ID, _RUN_START_TIME
        now = now_utc_iso()
        _RUN_START_TIME = time.monotonic()
        pid = os.getpid()
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        try:
            with get_connection() as conn:
                # Mark previously unclosed runs as interrupted
                conn.execute(
                    """
                    UPDATE application_runs
                    SET status = 'interrupted', ended_at = ?
                    WHERE status = 'running'
                    """,
                    (now,),
                )

                # Record new execution run
                conn.execute(
                    """
                    INSERT INTO application_runs (run_id, started_at, status, process_id, application_version)
                    VALUES (?, ?, 'running', ?, ?)
                    """,
                    (run_id, now, pid, application_version),
                )
        except Exception as e:
            logger.error(f"Failed to record application run: {e}")

        _CURRENT_RUN_ID = run_id
        return run_id

    @classmethod
    def end_application_run(cls, status: str = "completed") -> None:
        """Record shutdown of the current application execution."""
        global _CURRENT_RUN_ID
        if not _CURRENT_RUN_ID:
            return

        now = now_utc_iso()
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    UPDATE application_runs
                    SET status = ?, ended_at = ?
                    WHERE run_id = ?
                    """,
                    (status, now, _CURRENT_RUN_ID),
                )
        except Exception as e:
            logger.error(f"Failed to record application shutdown: {e}")

    @classmethod
    def get_current_run_id(cls) -> str:
        """Retrieve active application execution identifier or initialize fallback."""
        global _CURRENT_RUN_ID
        if not _CURRENT_RUN_ID:
            cls.start_application_run()
        return _CURRENT_RUN_ID or "run_fallback"

    @classmethod
    def ensure_user_session(cls, session_id: str | None, user_id: str | None = None) -> str:
        """
        Ensure a logical user session exists in the database.
        Reuses existing session or creates a new persistent record.
        """
        run_id = cls.get_current_run_id()
        now = now_utc_iso()
        actual_session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"

        try:
            with get_connection() as conn:
                row = conn.execute("SELECT session_id FROM user_sessions WHERE session_id = ?", (actual_session_id,)).fetchone()
                if not row:
                    conn.execute(
                        """
                        INSERT INTO user_sessions (session_id, run_id, user_id, started_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (actual_session_id, run_id, user_id, now),
                    )
        except Exception as e:
            logger.error(f"Failed to persist user session {actual_session_id}: {e}")

        return actual_session_id

    @classmethod
    def end_user_session(cls, session_id: str, reason: str = "logout") -> None:
        """Mark a user session as closed with termination reason."""
        now = now_utc_iso()
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    UPDATE user_sessions
                    SET ended_at = ?, termination_reason = ?
                    WHERE session_id = ?
                    """,
                    (now, reason, session_id),
                )
        except Exception as e:
            logger.error(f"Failed to end user session {session_id}: {e}")

    @classmethod
    def log_interaction(
        cls,
        session_id: str | None,
        user_id: str | None,
        tenant_id: str,
        query_text: str,
        intent: str,
        intent_confidence: float,
        retrieval_path: str,
        candidate_count: int,
        result_status: str,
        latency_ms: float,
        error_code: str | None = None,
        chunk_scores: list[tuple[str, float]] | None = None,
        retrieval_confidence: float | None = None,
    ) -> str:
        """
        Persist an interaction record and associated chunk results into SQLite.
        Fault-tolerant: Database write errors never fail the user query response.
        """
        interaction_id = f"int_{uuid.uuid4().hex[:12]}"
        run_id = cls.get_current_run_id()
        now = now_utc_iso()

        # Sanitize query text for privacy / data minimization (no passwords or credentials logged)
        sanitized_query = query_text[:256] if query_text else ""

        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO interaction_logs (
                        interaction_id, run_id, session_id, timestamp, user_id, tenant_id,
                        query_text, intent, intent_confidence, retrieval_path,
                        candidate_count, result_status, latency_ms, error_code
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        interaction_id,
                        run_id,
                        session_id,
                        now,
                        user_id,
                        tenant_id,
                        sanitized_query,
                        intent,
                        round(float(intent_confidence), 3),
                        retrieval_path,
                        candidate_count,
                        result_status,
                        round(float(latency_ms), 2),
                        error_code,
                    ),
                )

                if chunk_scores:
                    for chunk_id, score in chunk_scores[:10]:
                        res_id = f"ires_{uuid.uuid4().hex[:10]}"
                        conn.execute(
                            """
                            INSERT INTO interaction_results (id, interaction_id, chunk_id, relevance_score)
                            VALUES (?, ?, ?, ?)
                            """,
                            (res_id, interaction_id, chunk_id, round(float(score), 3)),
                        )
            # The canonical Trust View record is written after the legacy interaction
            # has committed, so a dashboard failure never changes chat behavior.
            from trust_view import TrustViewService
            TrustViewService.record_interaction(
                interaction_id=interaction_id, query=query_text, user_id=user_id,
                tenant_id=tenant_id, response_status=result_status,
                retrieval_path=retrieval_path, candidate_count=candidate_count,
                confidence=retrieval_confidence,
                selected_candidates=[chunk_id for chunk_id, _ in (chunk_scores or [])],
            )
        except Exception as e:
            logger.error(f"Failed to log interaction {interaction_id}: {e}")

        return interaction_id

    @classmethod
    def get_summary_metrics(cls, tenant_id: str | None = None) -> dict[str, Any]:
        """Aggregate performance and retrieval path statistics, optionally scoped by tenant."""
        where_clause = " WHERE tenant_id = ?" if tenant_id else ""
        params = (tenant_id,) if tenant_id else ()

        with get_connection() as conn:
            total_runs = conn.execute("SELECT COUNT(*) as c FROM application_runs").fetchone()["c"]
            active_run = conn.execute("SELECT * FROM application_runs WHERE run_id = ?", (cls.get_current_run_id(),)).fetchone()

            total_interactions = conn.execute(f"SELECT COUNT(*) as c FROM interaction_logs{where_clause}", params).fetchone()["c"]
            path_counts = conn.execute(
                f"SELECT retrieval_path, COUNT(*) as c FROM interaction_logs{where_clause} GROUP BY retrieval_path", params
            ).fetchall()
            status_counts = conn.execute(
                f"SELECT result_status, COUNT(*) as c FROM interaction_logs{where_clause} GROUP BY result_status", params
            ).fetchall()
            avg_latency = conn.execute(
                f"SELECT AVG(latency_ms) as avg_lat FROM interaction_logs{where_clause}", params
            ).fetchone()["avg_lat"] or 0.0

            recent = conn.execute(
                f"""
                SELECT interaction_id, timestamp, user_id, intent, intent_confidence,
                       retrieval_path, candidate_count, result_status, latency_ms
                FROM interaction_logs{where_clause}
                ORDER BY timestamp DESC
                LIMIT 20
                """, params
            ).fetchall()

        return {
            "current_run": dict(active_run) if active_run else None,
            "total_runs": total_runs,
            "total_interactions": total_interactions,
            "average_latency_ms": round(float(avg_latency), 2),
            "retrieval_paths": {r["retrieval_path"]: r["c"] for r in path_counts},
            "result_statuses": {r["result_status"]: r["c"] for r in status_counts},
            "recent_interactions": [dict(r) for r in recent],
            "scoped_tenant_id": tenant_id,
        }

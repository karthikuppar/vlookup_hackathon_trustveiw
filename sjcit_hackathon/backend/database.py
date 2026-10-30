"""Database schema and connection management for PS-04 Knowledge Chatbot."""
from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("PS04_DB_PATH", str(Path(__file__).resolve().parent / "ps04_knowledge.sqlite3"))


def get_db_path() -> str:
    return DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- system_admin, client_admin, client_employee
            tenant_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            media_type TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS document_versions (
            id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            version_num INTEGER NOT NULL,
            content_digest TEXT NOT NULL, -- SHA-256 of original content
            status TEXT NOT NULL, -- active, superseded, failed
            failure_reason TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            activated_at TEXT,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
            UNIQUE(doc_id, version_num)
        );

        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            version_num INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            page INTEGER NOT NULL,
            section TEXT NOT NULL,
            char_offset INTEGER NOT NULL,
            text TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_tenant_ver ON document_chunks(tenant_id, doc_id, version_num);

        CREATE TABLE IF NOT EXISTS knowledge_shares (
            id TEXT PRIMARY KEY,
            source_tenant_id TEXT NOT NULL,
            recipient_tenant_id TEXT NOT NULL,
            granted_by TEXT NOT NULL,
            permission TEXT NOT NULL DEFAULT 'read',
            status TEXT NOT NULL, -- active, revoked, expired
            reason TEXT,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (source_tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (recipient_tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_shares_recipient ON knowledge_shares(recipient_tenant_id, status);

        CREATE TABLE IF NOT EXISTS audit_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            action TEXT NOT NULL,
            decision TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            details_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_seq ON audit_events(sequence);

        CREATE TABLE IF NOT EXISTS ledger_checkpoints (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            sequence_head INTEGER NOT NULL,
            chain_head_hash TEXT NOT NULL,
            signature TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS query_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            query_text TEXT NOT NULL,
            query_hash TEXT NOT NULL,
            answer_status TEXT NOT NULL,
            returned_doc_ids TEXT NOT NULL,
            citation_ids TEXT NOT NULL,
            session_id TEXT
        );

        CREATE TABLE IF NOT EXISTS unresolved_queries (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            query_text TEXT NOT NULL,
            user_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            detected_tokens TEXT,
            suggested_intent TEXT,
            status TEXT DEFAULT 'pending_training'
        );

        CREATE TABLE IF NOT EXISTS dynamic_intent_prompts (
            id TEXT PRIMARY KEY,
            query_pattern TEXT NOT NULL UNIQUE,
            mapped_intent TEXT NOT NULL,
            expansion_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- =====================================================================
        -- Persistent Session and Interaction Logging (Trust View Specification)
        -- =====================================================================
        CREATE TABLE IF NOT EXISTS application_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL, -- running, completed, failed, interrupted
            process_id INTEGER,
            application_version TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_app_runs_status ON application_runs(status);

        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            run_id TEXT,
            user_id TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            termination_reason TEXT,
            FOREIGN KEY (run_id) REFERENCES application_runs(run_id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_user_sessions_run ON user_sessions(run_id);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);

        CREATE TABLE IF NOT EXISTS interaction_logs (
            interaction_id TEXT PRIMARY KEY,
            run_id TEXT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            tenant_id TEXT,
            query_text TEXT,
            intent TEXT,
            intent_confidence REAL,
            retrieval_path TEXT, -- graph, fallback, conversational, security_blocked
            candidate_count INTEGER DEFAULT 0,
            result_status TEXT, -- grounded, insufficient_evidence, conflict, conversational, security_refusal
            latency_ms REAL,
            error_code TEXT,
            FOREIGN KEY (run_id) REFERENCES application_runs(run_id) ON DELETE SET NULL,
            FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_interactions_run ON interaction_logs(run_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_session ON interaction_logs(session_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_status ON interaction_logs(result_status);
        CREATE INDEX IF NOT EXISTS idx_interactions_time ON interaction_logs(timestamp);

        CREATE TABLE IF NOT EXISTS interaction_results (
            id TEXT PRIMARY KEY,
            interaction_id TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            relevance_score REAL,
            FOREIGN KEY (interaction_id) REFERENCES interaction_logs(interaction_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_interaction_res_id ON interaction_results(interaction_id);

        -- TransparentView: durable diagnostics, feedback and knowledge-gap workflow.
        -- Kept separate from the legacy interaction log so existing reporting remains stable.
        CREATE TABLE IF NOT EXISTS trust_interactions (
            interaction_id TEXT PRIMARY KEY,
            normalized_query TEXT NOT NULL,
            query_fingerprint TEXT NOT NULL,
            retrieval_confidence REAL,
            confidence_method_version TEXT NOT NULL DEFAULT 'evidence-score-v1-heuristic',
            evidence_validation_status TEXT NOT NULL,
            response_status TEXT NOT NULL,
            retrieval_methods TEXT NOT NULL,
            selected_candidate_ids TEXT NOT NULL DEFAULT '[]',
            knowledge_base_version TEXT,
            feedback_status TEXT NOT NULL DEFAULT 'PENDING',
            ticket_id TEXT,
            FOREIGN KEY (interaction_id) REFERENCES interaction_logs(interaction_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_trust_interactions_fingerprint ON trust_interactions(query_fingerprint);
        CREATE INDEX IF NOT EXISTS idx_trust_interactions_ticket ON trust_interactions(ticket_id);

        CREATE TABLE IF NOT EXISTS knowledge_gap_tickets (
            ticket_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            representative_query TEXT NOT NULL,
            query_fingerprint TEXT NOT NULL,
            employee_id TEXT,
            first_interaction_id TEXT NOT NULL UNIQUE,
            latest_interaction_id TEXT NOT NULL,
            interaction_count INTEGER NOT NULL DEFAULT 1,
            candidate_count INTEGER NOT NULL DEFAULT 0,
            retrieval_summary TEXT NOT NULL DEFAULT '{}',
            confidence_score REAL,
            confidence_method_version TEXT NOT NULL,
            knowledge_base_version TEXT,
            root_cause_category TEXT,
            assigned_admin_id TEXT,
            priority TEXT NOT NULL DEFAULT 'NORMAL',
            status TEXT NOT NULL DEFAULT 'OPEN',
            resolution_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_gap_open ON knowledge_gap_tickets(tenant_id, status, query_fingerprint);

        CREATE TABLE IF NOT EXISTS ticket_interactions (
            ticket_id TEXT NOT NULL,
            interaction_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            PRIMARY KEY(ticket_id, interaction_id),
            FOREIGN KEY(ticket_id) REFERENCES knowledge_gap_tickets(ticket_id) ON DELETE CASCADE,
            FOREIGN KEY(interaction_id) REFERENCES interaction_logs(interaction_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS query_feedback (
            feedback_id TEXT PRIMARY KEY,
            interaction_id TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            rating TEXT NOT NULL,
            comment TEXT,
            missing_information TEXT,
            created_at TEXT NOT NULL,
            feedback_schema_version TEXT NOT NULL DEFAULT '1',
            review_status TEXT NOT NULL DEFAULT 'PENDING',
            reviewed_by TEXT,
            reviewed_at TEXT,
            review_outcome TEXT,
            UNIQUE(interaction_id, employee_id),
            FOREIGN KEY(interaction_id) REFERENCES interaction_logs(interaction_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_review ON query_feedback(review_status, created_at);
        CREATE TABLE IF NOT EXISTS ticket_events (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES knowledge_gap_tickets(ticket_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id TEXT PRIMARY KEY,
            identifier TEXT NOT NULL,
            attempted_at TEXT NOT NULL,
            success INTEGER NOT NULL,
            ip_address TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_login_attempts_ident ON login_attempts(identifier, attempted_at);
        """)
        # Migration: older databases lack the column that lets verify() recompute each payload digest.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(audit_events)").fetchall()}
        if "details_json" not in cols:
            conn.execute("ALTER TABLE audit_events ADD COLUMN details_json TEXT")

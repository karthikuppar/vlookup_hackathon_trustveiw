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
            entry_hash TEXT NOT NULL
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
        """)

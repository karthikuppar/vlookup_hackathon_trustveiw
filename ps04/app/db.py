"""SQLite schema and transaction helper. Every write path runs inside tx()."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL, password_hash TEXT NOT NULL,
  is_sysadmin INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memberships(user_id TEXT NOT NULL, tenant_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('client_admin','employee')),
  status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL, PRIMARY KEY(user_id, tenant_id));
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS login_failures(email TEXT NOT NULL, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, title TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS document_versions(id TEXT PRIMARY KEY, document_id TEXT NOT NULL, tenant_id TEXT NOT NULL, version_no INTEGER NOT NULL,
  filename TEXT NOT NULL, media_type TEXT NOT NULL, uploaded_by TEXT NOT NULL, uploaded_at TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('processing','ready','failed')), error TEXT, is_current INTEGER NOT NULL DEFAULT 0,
  superseded_at TEXT, superseded_by_version TEXT, file_path TEXT NOT NULL, UNIQUE(document_id, version_no));
CREATE UNIQUE INDEX IF NOT EXISTS one_current_version ON document_versions(document_id) WHERE is_current=1;
CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, version_id TEXT NOT NULL, document_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
  ord INTEGER NOT NULL, page INTEGER, section TEXT, char_start INTEGER NOT NULL, char_end INTEGER NOT NULL, text TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS chunks_tenant ON chunks(tenant_id, version_id);
CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY, owner_tenant_id TEXT NOT NULL, grantee_tenant_id TEXT NOT NULL, document_id TEXT,
  granted_by TEXT NOT NULL, granted_at TEXT NOT NULL, expires_at TEXT, revoked_at TEXT, revoked_by TEXT);
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
  outcome TEXT, citations TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events(seq INTEGER PRIMARY KEY, ts TEXT NOT NULL, tenant_id TEXT, counterparty_tenant_id TEXT, actor TEXT,
  action TEXT NOT NULL, details TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
"""


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn) -> None:
    conn.executescript(SCHEMA)


@contextmanager
def tx(conn):
    """Serialised write transaction; audit appends must happen inside one."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")

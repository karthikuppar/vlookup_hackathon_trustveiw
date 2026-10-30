"""Cryptographic and canonical serialization utilities for PS-04."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

def _load_audit_key() -> bytes:
    """Audit-signing key from the environment, else a random per-install key kept in a local file.

    There is no built-in default: a published key would let anyone forge ledger checkpoints.
    NOTE: a database whose checkpoints were signed with the old default key will report
    checkpoint_signature_invalid; recreate it (or re-checkpoint) after upgrading."""
    env = os.getenv("PS04_AUDIT_HMAC_KEY") or os.getenv("VICO_AUDIT_HMAC_KEY")
    if env and env.strip():
        return env.strip().encode("utf-8")
    key_file = Path(__file__).resolve().parent / ".audit_hmac_key"
    try:
        if key_file.exists():
            stored = key_file.read_text("utf-8").strip()
            if len(stored) >= 32:
                return stored.encode("utf-8")
    except OSError:
        pass
    import secrets
    new_key = secrets.token_hex(32)
    try:
        key_file.write_text(new_key, "utf-8")
    except OSError:
        if os.getenv("AEGIS_ENV", "").lower() == "production":
            raise RuntimeError("PS04_AUDIT_HMAC_KEY must be set (cannot persist a generated audit key)")
    return new_key.encode("utf-8")


HMAC_KEY = _load_audit_key()


def now_utc_iso() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def canonical_json(data: Any) -> str:
    """Deterministic, sorted, whitespace-trimmed canonical JSON representation."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_digest(content: str | bytes) -> str:
    """Return sha256 hex digest for given text or bytes."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def hmac_actor(actor_id: str) -> str:
    """Generate pseudonymized HMAC for actor identity to prevent leaking credentials/IDs in audit."""
    return hmac.new(HMAC_KEY, actor_id.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

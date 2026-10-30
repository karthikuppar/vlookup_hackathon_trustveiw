"""Cryptographic and canonical serialization utilities for PS-04."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any

HMAC_KEY = os.getenv("PS04_AUDIT_HMAC_KEY", "ps04_secure_audit_secret_key_default").encode("utf-8")


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

"""Blockchain-lite audit ledger: a SHA-256 hash chain plus HMAC-signed checkpoints kept outside the DB.

Detects: edited, deleted, inserted or reordered events, tail truncation (via checkpoints), and a full
re-hash of the chain by someone without the checkpoint key. It does NOT stop an attacker who holds
both the DB and the signing key, and it is not a distributed or immutable ledger.
Events never carry raw document text or raw questions -- only ids and digests.
"""
from __future__ import annotations
import hashlib, hmac, json
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def canonical(seq, ts, tenant_id, counterparty, actor, action, details) -> bytes:
    return json.dumps([seq, ts, tenant_id, counterparty, actor, action, details],
                      sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def event_hash(prev: str, body: bytes) -> str:
    return hashlib.sha256(prev.encode() + b"|" + body).hexdigest()


class Ledger:
    def __init__(self, checkpoint_path: Path, key: bytes, checkpoint_every: int = 10):
        self.path = Path(checkpoint_path)
        self.key = key
        self.every = checkpoint_every

    def append(self, conn, action, actor=None, tenant_id=None, counterparty=None, **details) -> int:
        """Append inside the caller's transaction so the action and its audit record commit together."""
        row = conn.execute("SELECT seq, hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        seq, prev = (row["seq"] + 1, row["hash"]) if row else (1, GENESIS)
        ts = now()
        det = json.dumps(details, sort_keys=True, default=str)
        h = event_hash(prev, canonical(seq, ts, tenant_id, counterparty, actor, action, json.loads(det)))
        conn.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?)",
                     (seq, ts, tenant_id, counterparty, actor, action, det, prev, h))
        if seq % self.every == 0:
            self._write_checkpoint(seq, h)
        return seq

    def _mac(self, seq, h) -> str:
        return hmac.new(self.key, f"{seq}|{h}".encode(), hashlib.sha256).hexdigest()

    def _write_checkpoint(self, seq, h):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"seq": seq, "hash": h, "ts": now(), "mac": self._mac(seq, h)}) + "\n")

    def checkpoint(self, conn) -> dict | None:
        row = conn.execute("SELECT seq, hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        if not row:
            return None
        self._write_checkpoint(row["seq"], row["hash"])
        return {"seq": row["seq"], "hash": row["hash"]}

    def verify(self, conn) -> dict:
        """Recompute the chain and cross-check signed checkpoints. Returns ok plus the first problem found."""
        prev, expect, hashes = GENESIS, 1, {}
        for r in conn.execute("SELECT * FROM audit_events ORDER BY seq"):
            if r["seq"] != expect:
                return {"ok": False, "broken_at": expect, "reason": "missing_or_reordered_event"}
            if r["prev_hash"] != prev:
                return {"ok": False, "broken_at": r["seq"], "reason": "prev_hash_mismatch"}
            body = canonical(r["seq"], r["ts"], r["tenant_id"], r["counterparty_tenant_id"], r["actor"], r["action"], json.loads(r["details"]))
            if event_hash(prev, body) != r["hash"]:
                return {"ok": False, "broken_at": r["seq"], "reason": "hash_mismatch"}
            hashes[r["seq"]] = prev = r["hash"]
            expect += 1
        checkpoints = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    cp = json.loads(line)
                except ValueError:
                    return {"ok": False, "broken_at": None, "reason": "checkpoint_unreadable"}
                if not hmac.compare_digest(self._mac(cp.get("seq"), cp.get("hash")), str(cp.get("mac"))):
                    return {"ok": False, "broken_at": cp.get("seq"), "reason": "checkpoint_signature_invalid"}
                if cp["seq"] not in hashes:
                    return {"ok": False, "broken_at": cp["seq"], "reason": "truncated_after_checkpoint"}
                if hashes[cp["seq"]] != cp["hash"]:
                    return {"ok": False, "broken_at": cp["seq"], "reason": "checkpoint_hash_mismatch"}
                checkpoints += 1
        return {"ok": True, "events": expect - 1, "head": prev, "checkpoints_verified": checkpoints}

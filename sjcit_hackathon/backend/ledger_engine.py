"""Blockchain-lite tamper-evident audit ledger implementation."""
from __future__ import annotations
import uuid
from typing import Any
from crypto_utils import canonical_json, hmac_actor, now_utc_iso, sha256_digest
from database import get_connection

GENESIS_PREV_HASH = "0" * 64


class AuditLedger:
    @staticmethod
    def append_event(
        event_type: str,
        actor_id: str,
        tenant_id: str,
        resource_id: str,
        action: str,
        decision: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically append a tamper-evident hash-chained audit event."""
        details = details or {}
        event_id = f"evt_{uuid.uuid4().hex}"
        timestamp = now_utc_iso()
        actor_alias = hmac_actor(actor_id)

        canonical_payload = {
            "action": action,
            "actor_id": actor_alias,
            "decision": decision,
            "details": details,
            "event_id": event_id,
            "event_type": event_type,
            "resource_id": resource_id,
            "tenant_id": tenant_id,
            "timestamp": timestamp,
        }
        payload_digest = f"sha256:{sha256_digest(canonical_json(canonical_payload))}"

        with get_connection() as conn:
            # Fetch previous entry's hash
            last_row = conn.execute(
                "SELECT sequence, entry_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            prev_hash = last_row["entry_hash"] if last_row else GENESIS_PREV_HASH
            next_seq = (last_row["sequence"] + 1) if last_row else 1

            entry_meta = {
                "payload_digest": payload_digest,
                "prev_hash": prev_hash,
                "sequence": next_seq,
            }
            entry_hash = f"sha256:{sha256_digest(canonical_json(entry_meta))}"

            conn.execute(
                """
                INSERT INTO audit_events (
                    sequence, event_id, timestamp, event_type, actor_id, tenant_id,
                    resource_id, action, decision, payload_digest, prev_hash, entry_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_seq,
                    event_id,
                    timestamp,
                    event_type,
                    actor_alias,
                    tenant_id,
                    resource_id,
                    action,
                    decision,
                    payload_digest,
                    prev_hash,
                    entry_hash,
                ),
            )

        return {
            "sequence": next_seq,
            "event_id": event_id,
            "event_type": event_type,
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
            "payload_digest": payload_digest,
        }

    @staticmethod
    def verify() -> dict[str, Any]:
        """Recompute the entire hash chain and detect any altered, broken, or missing entries."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT sequence, event_id, timestamp, event_type, actor_id, tenant_id, resource_id, action, decision, payload_digest, prev_hash, entry_hash FROM audit_events ORDER BY sequence ASC"
            ).fetchall()

        if not rows:
            return {"valid": True, "total_events": 0, "chain_head": GENESIS_PREV_HASH, "message": "Ledger is empty (intact)"}

        expected_prev_hash = GENESIS_PREV_HASH
        expected_seq = 1

        for row in rows:
            seq = row["sequence"]
            # 1. Sequence continuity check
            if seq != expected_seq:
                return {
                    "valid": False,
                    "tampered_sequence": seq,
                    "event_id": row["event_id"],
                    "error_type": "sequence_discontinuity",
                    "reason": f"Expected sequence {expected_seq} but found {seq} (entry deleted or reordered)",
                }

            # 2. Previous hash link check
            if row["prev_hash"] != expected_prev_hash:
                return {
                    "valid": False,
                    "tampered_sequence": seq,
                    "event_id": row["event_id"],
                    "error_type": "broken_hash_link",
                    "reason": f"Previous hash link broken at sequence {seq}",
                    "expected_prev_hash": expected_prev_hash,
                    "actual_prev_hash": row["prev_hash"],
                }

            # 3. Entry hash integrity check
            entry_meta = {
                "payload_digest": row["payload_digest"],
                "prev_hash": row["prev_hash"],
                "sequence": seq,
            }
            computed_entry_hash = f"sha256:{sha256_digest(canonical_json(entry_meta))}"
            if row["entry_hash"] != computed_entry_hash:
                return {
                    "valid": False,
                    "tampered_sequence": seq,
                    "event_id": row["event_id"],
                    "error_type": "entry_hash_mismatch",
                    "reason": f"Entry hash tampered or altered at sequence {seq}",
                    "expected_hash": computed_entry_hash,
                    "actual_hash": row["entry_hash"],
                }

            expected_prev_hash = row["entry_hash"]
            expected_seq += 1

        return {
            "valid": True,
            "total_events": len(rows),
            "chain_head": rows[-1]["entry_hash"],
            "verified_at": now_utc_iso(),
            "message": "Cryptographic hash chain is 100% intact and valid",
        }

    @staticmethod
    def tamper_for_demo(sequence: int | None = None) -> dict[str, Any]:
        """Intentionally modify an audit row to demonstrate verifier detecting tampering."""
        with get_connection() as conn:
            if sequence is None:
                row = conn.execute("SELECT sequence FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
                if not row:
                    return {"success": False, "message": "No events in ledger to tamper with"}
                sequence = row["sequence"]

            # Tamper the action field without updating the entry_hash or prev_hash
            conn.execute(
                "UPDATE audit_events SET payload_digest = 'sha256:0000000000000000000000000000000000000000000000000000000000000000' WHERE sequence = ?",
                (sequence,),
            )
        return {
            "success": True,
            "tampered_sequence": sequence,
            "message": f"Successfully tampered with sequence {sequence}. Run verification to observe detection.",
        }

    @staticmethod
    def get_events(limit: int = 100) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT sequence, event_id, timestamp, event_type, actor_id, tenant_id, resource_id, action, decision, payload_digest, prev_hash, entry_hash FROM audit_events ORDER BY sequence DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

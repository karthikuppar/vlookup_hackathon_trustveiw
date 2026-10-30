"""Secure knowledge-base sharing service with explicit grants and immediate revocation."""
from __future__ import annotations
import uuid
from typing import Any
from crypto_utils import now_utc_iso
from database import get_connection
from ledger_engine import AuditLedger


class SharingService:
    @staticmethod
    def create_share_grant(
        source_tenant_id: str,
        recipient_tenant_id: str,
        granted_by: str,
        reason: str | None = None,
        permission: str = "read",
    ) -> dict[str, Any]:
        """Create an explicit, audited knowledge base sharing grant."""
        if source_tenant_id == recipient_tenant_id:
            raise ValueError("Source and recipient tenants cannot be the same")

        with get_connection() as conn:
            # Check recipient tenant exists
            recipient = conn.execute("SELECT id FROM tenants WHERE id = ?", (recipient_tenant_id,)).fetchone()
            if not recipient:
                raise ValueError(f"Recipient tenant '{recipient_tenant_id}' does not exist")

            # Check if active grant already exists
            existing = conn.execute(
                "SELECT id FROM knowledge_shares WHERE source_tenant_id = ? AND recipient_tenant_id = ? AND status = 'active'",
                (source_tenant_id, recipient_tenant_id),
            ).fetchone()
            if existing:
                return {
                    "share_id": existing["id"],
                    "source_tenant_id": source_tenant_id,
                    "recipient_tenant_id": recipient_tenant_id,
                    "status": "active",
                    "message": "Active grant already exists",
                }

            share_id = f"shr_{uuid.uuid4().hex[:12]}"
            now = now_utc_iso()

            conn.execute(
                """
                INSERT INTO knowledge_shares (id, source_tenant_id, recipient_tenant_id, granted_by, permission, status, reason, created_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (share_id, source_tenant_id, recipient_tenant_id, granted_by, permission, reason, now),
            )

        AuditLedger.append_event(
            event_type="knowledge_share_granted",
            actor_id=granted_by,
            tenant_id=source_tenant_id,
            resource_id=share_id,
            action="grant_knowledge_share",
            decision="permitted",
            details={
                "recipient_tenant_id": recipient_tenant_id,
                "permission": permission,
                "reason": reason,
            },
        )

        return {
            "share_id": share_id,
            "source_tenant_id": source_tenant_id,
            "recipient_tenant_id": recipient_tenant_id,
            "status": "active",
            "permission": permission,
            "created_at": now,
        }

    @staticmethod
    def revoke_share_grant(share_id: str, actor_id: str, actor_tenant_id: str) -> dict[str, Any]:
        """Revoke a knowledge base share grant with immediate effect."""
        now = now_utc_iso()
        with get_connection() as conn:
            share = conn.execute("SELECT * FROM knowledge_shares WHERE id = ?", (share_id,)).fetchone()
            if not share:
                raise ValueError("Share grant not found")

            # Authorization: only source tenant admin or system admin can revoke
            if share["source_tenant_id"] != actor_tenant_id and actor_tenant_id != "system":
                raise PermissionError("Only the granting tenant administrator can revoke this share")

            conn.execute(
                "UPDATE knowledge_shares SET status = 'revoked', revoked_at = ? WHERE id = ?",
                (now, share_id),
            )

        AuditLedger.append_event(
            event_type="knowledge_share_revoked",
            actor_id=actor_id,
            tenant_id=share["source_tenant_id"],
            resource_id=share_id,
            action="revoke_knowledge_share",
            decision="revoked",
            details={
                "recipient_tenant_id": share["recipient_tenant_id"],
                "revoked_at": now,
            },
        )

        return {
            "share_id": share_id,
            "status": "revoked",
            "revoked_at": now,
        }

    @staticmethod
    def get_active_shared_tenants_for_user(recipient_tenant_id: str) -> list[str]:
        """Resolve permitted shared tenant IDs inside the retrieval layer."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT source_tenant_id FROM knowledge_shares WHERE recipient_tenant_id = ? AND status = 'active'",
                (recipient_tenant_id,),
            ).fetchall()
        return [r["source_tenant_id"] for r in rows]

    @staticmethod
    def list_shares(tenant_id: str) -> dict[str, list[dict[str, Any]]]:
        """List outgoing and incoming sharing grants."""
        with get_connection() as conn:
            outgoing = conn.execute(
                "SELECT * FROM knowledge_shares WHERE source_tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
            incoming = conn.execute(
                "SELECT * FROM knowledge_shares WHERE recipient_tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
        return {
            "outgoing": [dict(r) for r in outgoing],
            "incoming": [dict(r) for r in incoming],
        }

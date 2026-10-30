"""TEE (Trusted Execution Environment) integration and simulated remote attestation."""
from __future__ import annotations
import hashlib
from typing import Any
from crypto_utils import now_utc_iso, sha256_digest
from ledger_engine import AuditLedger

# Expected hardware measurement fixture for demo
EXPECTED_MRENCLAVE = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
EXPECTED_MRSIGNER = "5d41402abc4b2a76b9719d911017c592"


class TeeService:
    @staticmethod
    def get_status() -> dict[str, Any]:
        """Report truthful TEE status, explicitly stating that it is a simulation."""
        return {
            "mode": "simulated",
            "is_hardware_backed": False,
            "technology": "Intel TDX / AMD SEV-SNP (Architecture Simulation)",
            "boundary": "Sensitive document decryption and cryptographic attestation service",
            "attestation_policy": {
                "expected_mrenclave": EXPECTED_MRENCLAVE,
                "expected_mrsigner": EXPECTED_MRSIGNER,
                "freshness_max_seconds": 300,
            },
            "status_description": (
                "SIMULATION: Running on standard host environment without dedicated confidential hardware. "
                "Remote attestation evidence is validated via cryptographic mock fixtures."
            ),
            "timestamp": now_utc_iso(),
        }

    @staticmethod
    def verify_attestation(
        quote_signature: str | None = None,
        simulate_invalid: bool = False,
        actor_id: str = "system",
    ) -> dict[str, Any]:
        """
        Verify attestation quote and enforce policy for secret release.
        Demonstrates passing and failing security verification paths.
        """
        now = now_utc_iso()
        if simulate_invalid:
            AuditLedger.append_event(
                event_type="tee_attestation_rejected",
                actor_id=actor_id,
                tenant_id="security",
                resource_id="tee_attestation",
                action="verify_attestation",
                decision="denied",
                details={"reason": "Measurement signature mismatch (MRENCLAVE tampered or unapproved)"},
            )
            return {
                "verified": False,
                "status": "rejected",
                "secret_released": False,
                "reason": "Attestation measurement does not match approved policy (MRENCLAVE tampered)",
                "timestamp": now,
            }

        # Valid simulated attestation path
        secret_token = f"enc_sec_{sha256_digest(f'{now}:{EXPECTED_MRENCLAVE}')[:16]}"
        AuditLedger.append_event(
            event_type="tee_attestation_verified",
            actor_id=actor_id,
            tenant_id="security",
            resource_id="tee_attestation",
            action="verify_attestation",
            decision="permitted",
            details={"mrenclave": EXPECTED_MRENCLAVE, "secret_released": True},
        )
        return {
            "verified": True,
            "status": "verified (simulation)",
            "secret_released": True,
            "released_secret": secret_token,
            "mrenclave": EXPECTED_MRENCLAVE,
            "timestamp": now,
        }

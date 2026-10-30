"""TEE integration path -- SIMULATED.

No hardware enclave is used. This module defines the interface a real TEE backend (SGX/SEV-SNP/
Nitro) would implement: produce an attestation report bound to a nonce and a code measurement, and
release a key only when the report satisfies a policy. The simulated backend signs the report with
a software key, so it proves nothing about the host. /security/status reports this honestly.
"""
from __future__ import annotations
import hashlib, hmac, secrets
from pathlib import Path

MEASURED_FILES = ("answer.py", "retrieval.py", "audit.py", "ingest.py")


class SimulatedTee:
    mode = "simulated"
    hardware_backed = False

    def __init__(self, secret: bytes):
        self._secret = secret

    def measurement(self) -> str:
        h = hashlib.sha256()
        base = Path(__file__).parent
        for name in MEASURED_FILES:
            h.update((base / name).read_bytes() if (base / name).exists() else b"")
        return h.hexdigest()

    def attest(self, nonce: str | None = None) -> dict:
        nonce = nonce or secrets.token_hex(16)
        m = self.measurement()
        mac = hmac.new(self._secret, f"{nonce}|{m}".encode(), hashlib.sha256).hexdigest()
        return {"mode": self.mode, "hardware_backed": False, "nonce": nonce, "measurement": m, "signature": mac}

    def verify(self, report: dict, expected_measurement: str) -> bool:
        mac = hmac.new(self._secret, f"{report.get('nonce')}|{report.get('measurement')}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(mac, str(report.get("signature"))) and report.get("measurement") == expected_measurement

    def release_key(self, purpose: str, report: dict, expected_measurement: str) -> bytes | None:
        """Key-release policy: only a verified report matching the expected measurement gets a key."""
        if not self.verify(report, expected_measurement):
            return None
        return hmac.new(self._secret, f"key-release|{purpose}".encode(), hashlib.sha256).digest()

    def status(self) -> dict:
        return {"tee": {"mode": self.mode, "hardware_backed": False, "enabled": False,
                        "note": "Simulated interface only; no hardware enclave or remote attestation is in use."}}

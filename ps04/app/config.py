"""Runtime settings. Fails closed: no secret, no start."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path
    secret: bytes
    token_ttl: int = 3600
    max_upload_bytes: int = 5 * 1024 * 1024
    allowed_media: tuple = (".txt", ".md", ".pdf")
    checkpoint_every: int = 10
    max_failed_logins: int = 5
    lockout_seconds: int = 300
    pbkdf2_iterations: int = 200_000

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.environ.get("PS04_SECRET", "")
        if len(secret) < 16:
            raise RuntimeError("PS04_SECRET must be set to a random value of at least 16 characters")
        return cls(data_dir=Path(os.environ.get("PS04_DATA_DIR", "ps04_data")), secret=secret.encode())

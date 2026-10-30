# backend/auth_security.py

import os
import hmac
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# Secret management: Load from environment, or generate a persistent local secret file
def _load_or_create_secret() -> str:
    env_secret = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    if env_secret and env_secret.strip():
        return env_secret.strip()

    secret_file = Path(__file__).resolve().parent / ".jwt_secret"
    if secret_file.exists():
        try:
            stored = secret_file.read_text("utf-8").strip()
            if len(stored) >= 32:
                return stored
        except Exception:
            pass

    import secrets
    new_secret = secrets.token_hex(32)
    try:
        secret_file.write_text(new_secret, "utf-8")
    except Exception:
        pass
    return new_secret


SECRET_KEY = _load_or_create_secret()
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", f"{SECRET_KEY}_refresh")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

MAX_PASSWORD_BYTES = 72

# --- In-Memory Sliding-Window Login Throttling ---
# Max 5 failed attempts per 5-minute window per identifier
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def check_login_rate_limit(identifier: str) -> tuple[bool, int]:
    """
    Check if identifier (email or IP) is currently rate-limited due to repeated failures.
    Returns: (is_locked, remaining_seconds)
    """
    now = time.time()
    identifier_clean = identifier.strip().lower()
    timestamps = _failed_attempts[identifier_clean]

    # Purge attempts older than the window
    valid_timestamps = [t for t in timestamps if now - t < LOCKOUT_WINDOW_SECONDS]
    _failed_attempts[identifier_clean] = valid_timestamps

    if len(valid_timestamps) >= MAX_FAILED_ATTEMPTS:
        oldest_attempt = min(valid_timestamps)
        remaining = int(LOCKOUT_WINDOW_SECONDS - (now - oldest_attempt))
        return True, max(remaining, 1)

    return False, 0


def record_failed_login(identifier: str) -> None:
    """Record a failed login attempt for the identifier."""
    identifier_clean = identifier.strip().lower()
    _failed_attempts[identifier_clean].append(time.time())


def reset_failed_logins(identifier: str) -> None:
    """Reset failed attempts upon successful authentication."""
    identifier_clean = identifier.strip().lower()
    _failed_attempts.pop(identifier_clean, None)


def _normalize_password(password: str) -> str:
    if password is None:
        return ""
    password = str(password).strip()
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > MAX_PASSWORD_BYTES:
        pwd_bytes = pwd_bytes[:MAX_PASSWORD_BYTES]
        password = pwd_bytes.decode("utf-8", errors="ignore")
    return password


def hash_password(password: str) -> str:
    password = _normalize_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _is_bcrypt_hash(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password = _normalize_password(plain_password)
    stored_password = (hashed_password or "").strip()
    if not stored_password:
        return False

    if _is_bcrypt_hash(stored_password):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_password.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    return hmac.compare_digest(plain_password, stored_password)


def password_needs_rehash(hashed_password: str) -> bool:
    stored_password = (hashed_password or "").strip()
    if not stored_password:
        return False
    return not _is_bcrypt_hash(stored_password)


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        if not payload.get("user_id"):
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        if not payload.get("user_id"):
            return None
        return payload
    except JWTError:
        return None

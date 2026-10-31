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


COMMON_WEAK_PASSWORDS = {
    "password1234", "password12345", "123456789012", "qwertyuiop12", "administrator1",
    "admin1234567", "welcome12345", "changeme1234", "trustview123", "letmein12345",
    "iloveyou1234", "passphrase123", "defaultpass12", "aegiskb12345", "supersecret12"
}


def validate_password_policy(password: str, email: str | None = None) -> None:
    """Enforces strict password policy (Roadmap 1.4):
    - Minimum length of 12 characters
    - Not identical to email or containing user handle
    - Not in offline common weak password blacklist
    """
    if not password or len(password) < 12:
        raise ValueError("Password policy violation: Password must be at least 12 characters long.")

    clean_pwd = str(password).strip().lower()
    if email:
        clean_email = str(email).strip().lower()
        if clean_pwd == clean_email:
            raise ValueError("Password policy violation: Password cannot be identical to email address.")
        user_handle = clean_email.split("@")[0]
        if len(user_handle) >= 3 and user_handle in clean_pwd:
            raise ValueError("Password policy violation: Password cannot contain email username.")

    if clean_pwd in COMMON_WEAK_PASSWORDS:
        raise ValueError("Password policy violation: Password is too common. Please select a stronger password.")


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
    import uuid
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    if "jti" not in to_encode:
        to_encode["jti"] = f"tok_{uuid.uuid4().hex}"
    to_encode.setdefault("iat", now.timestamp())
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS) -> str:
    import uuid
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=expires_days)
    if "jti" not in to_encode:
        to_encode["jti"] = f"rtk_{uuid.uuid4().hex}"
    to_encode.setdefault("iat", now.timestamp())
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


def blacklist_token(jti: str, user_id: str, token_type: str = "access", expires_at: str | None = None, reason: str = "logout") -> None:
    """Store revoked token identifier in database blacklist."""
    from database import get_connection
    from crypto_utils import now_utc_iso
    now = now_utc_iso()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO token_blacklist (jti, user_id, token_type, expires_at, revoked_at, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (jti, user_id, token_type, expires_at or now, now, reason),
        )


def is_token_blacklisted(jti: str) -> bool:
    """Check if token identifier has been revoked."""
    if not jti:
        return False
    from database import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT jti FROM token_blacklist WHERE jti = ?", (jti,)).fetchone()
        return row is not None


def revoke_all_user_tokens(user_id: str) -> None:
    """Revoke all current tokens for a user by setting tokens_revoked_before timestamp."""
    from database import get_connection
    from crypto_utils import now_utc_iso
    now = now_utc_iso()
    with get_connection() as conn:
        conn.execute("UPDATE users SET tokens_revoked_before = ? WHERE id = ?", (now, user_id))



# Verified against when the account does not exist, so unknown emails cost the same as wrong passwords.
DUMMY_PASSWORD_HASH = hash_password("timing-equaliser-not-a-real-password")

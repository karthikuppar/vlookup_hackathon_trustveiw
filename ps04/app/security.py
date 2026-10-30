"""Password hashing and signed, server-revocable session tokens (stdlib only, offline)."""
from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time


def hash_password(password: str, iterations: int = 200_000) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, dk = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(calc.hex(), dk)
    except Exception:
        return False


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(secret: bytes, session_id: str, ttl: int) -> str:
    payload = _b64(json.dumps({"sid": session_id, "exp": time.time() + ttl}).encode())
    sig = _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(secret: bytes, token: str) -> str | None:
    """Return the session id if the signature and expiry are valid, else None."""
    try:
        payload, sig = token.split(".")
        good = _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(_unb64(payload))
        return data["sid"] if data["exp"] > time.time() else None
    except Exception:
        return None

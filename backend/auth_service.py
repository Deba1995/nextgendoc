import hashlib
import hmac
import os
import time
from typing import Optional


def is_auth_required() -> bool:
    """
    Returns True if an APP_ACCESS_KEY is configured in the environment.
    If not set or empty, authentication is disabled (open access).
    """
    return bool(os.environ.get("APP_ACCESS_KEY", "").strip())


def get_access_key() -> str:
    """
    Returns the configured secret access key from the environment.
    """
    return os.environ.get("APP_ACCESS_KEY", "").strip()


def create_session_token(access_key: str, ttl_hours: int = 48) -> str:
    """
    Creates a stateless, tamper-proof session token with expiration.
    Format: <unix_expiry_timestamp>:<hmac_sha256_signature>
    """
    expiry = int(time.time()) + (ttl_hours * 3600)
    signature = hmac.new(
        access_key.encode("utf-8"),
        str(expiry).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{expiry}:{signature}"


def verify_session_token(token: Optional[str], access_key: str) -> bool:
    """
    Validates a session token's signature and expiration against the secret access key.
    """
    if not token or not access_key:
        return False

    parts = token.strip().split(":")
    if len(parts) != 2:
        return False

    try:
        expiry = int(parts[0])
    except ValueError:
        return False

    # Check if token is expired
    if time.time() > expiry:
        return False

    expected_sig = hmac.new(
        access_key.encode("utf-8"),
        str(expiry).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(parts[1], expected_sig)

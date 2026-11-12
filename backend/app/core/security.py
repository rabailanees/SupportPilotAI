from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain password against its stored hash."""
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Verify and decode a JWT access token."""
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    return payload

"""
security.py — Password hashing and JWT access tokens.

Replaces the original plaintext-password storage with industry-standard
bcrypt hashing (via passlib) and stateless JWT bearer authentication.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from .config import settings

# bcrypt work factor 12 is a sensible 2020s default.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

_bearer = HTTPBearer(auto_error=True)


# ── Password hashing ─────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Return a bcrypt hash for a plaintext password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verify a plaintext password against a stored hash."""
    try:
        return _pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


# ── JWT access tokens ─────────────────────────────────────────────────────────


def create_access_token(email: str) -> str:
    """Create a signed JWT whose subject is the user's email."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Return the email (``sub``) from a valid token, or raise 401."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        if not email:
            raise ValueError("token missing subject")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        ) from None
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from None


# ── FastAPI dependency ────────────────────────────────────────────────────────


def current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """FastAPI dependency that resolves the authenticated user's email."""
    return decode_access_token(credentials.credentials)

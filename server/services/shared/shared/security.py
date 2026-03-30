"""Security utilities — JWT, password hashing, token generation."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Hashing ────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────────────

def create_access_token(
    *,
    subject: str,
    role: str = "member",
    username: str = "",
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 30,
) -> str:
    """Create a signed JWT with user claims."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, *, secret_key: str, algorithm: str = "HS256") -> dict | None:
    """Decode and verify a JWT. Returns payload or None on failure."""
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except InvalidTokenError:
        return None


# ── Opaque Tokens ────────────────────────────────────────────────────

def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

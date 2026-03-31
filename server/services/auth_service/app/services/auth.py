"""Auth service — registration, authentication, tokens, password management."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from shared.exceptions import ConflictError, UnauthorizedError, ValidationError
from shared.logging import get_logger
from shared.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)

from app.core.config import get_settings
from app.models import RefreshToken, User, UserRole
from app.repositories import UserRepository, TokenRepository
from app.services.helpers import _publish_user_status_change

logger = get_logger(__name__)
settings = get_settings()


# ── Default Admin Seed ────────────────────────────────────────────────

async def seed_default_admin(db: AsyncSession) -> None:
    """Create the default admin user if it doesn't already exist."""
    existing = await UserRepository.find_by_email_or_username(db, settings.DEFAULT_ADMIN_EMAIL, settings.DEFAULT_ADMIN_USERNAME)

    if existing is not None:
        logger.info("default_admin_exists", username=existing.username)
        return

    admin = User(
        email=settings.DEFAULT_ADMIN_EMAIL,
        username=settings.DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        name="Admin",
        role=UserRole.ADMIN.value,
    )
    db.add(admin)
    await db.commit()
    logger.info("default_admin_created", username=admin.username, email=admin.email)


# ── Registration ─────────────────────────────────────────────────────

async def create_user(db: AsyncSession, data) -> User:
    existing = await UserRepository.find_by_email_or_username(db, data.email, data.username)

    if existing is not None:
        if existing.email == data.email:
            raise ConflictError("A user with this email already exists")
        raise ConflictError("A user with this username already exists")

    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
        name=data.name,
    )
    user = await UserRepository.create(db, user)
    logger.info("user_created", user_id=str(user.id), username=user.username)
    return user


# ── Authentication ───────────────────────────────────────────────────

async def authenticate_user(db: AsyncSession, login: str, password: str) -> User:
    user = await UserRepository.find_by_login(db, login)

    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email/username or password")
    if not user.is_active:
        if user.deactivated_by_admin:
            raise UnauthorizedError("Account is deactivated by an administrator")
        # Self-deactivated: auto-reactivate on login
        user.is_active = True
        user.deactivated_by_admin = False
        await db.flush()
        await _publish_user_status_change(user.id, True)
        logger.info("user_self_reactivated", user_id=str(user.id))
    return user


# ── Token Pair ───────────────────────────────────────────────────────

async def create_token_pair(db: AsyncSession, user: User) -> dict[str, str]:
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        username=user.username,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    raw_refresh = generate_opaque_token()
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await TokenRepository.create_refresh(db, refresh_row)

    return {"access_token": access_token, "refresh_token": raw_refresh, "token_type": "bearer"}


# ── Refresh Token Rotation ──────────────────────────────────────────

async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> dict[str, str]:
    token_hash = hash_token(raw_token)
    token_row = await TokenRepository.find_refresh_by_hash(db, token_hash, for_update=True)

    if token_row is None:
        raise UnauthorizedError("Invalid refresh token")

    if token_row.is_revoked:
        logger.warning("refresh_token_reuse_detected", user_id=str(token_row.user_id))
        await TokenRepository.revoke_all_user_refresh(db, token_row.user_id)
        raise UnauthorizedError("Refresh token reuse detected — all sessions revoked")

    if token_row.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token expired")

    user = await UserRepository.find_by_id(db, token_row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or deactivated")

    token_row.is_revoked = True
    new_pair = await create_token_pair(db, user)

    new_hash = hash_token(new_pair["refresh_token"])
    new_row = await TokenRepository.find_refresh_by_hash(db, new_hash)
    if new_row is not None:
        token_row.replaced_by = new_row.id

    await db.flush()
    return new_pair


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    await TokenRepository.revoke_by_hash(db, token_hash)


# ── Password Change ─────────────────────────────────────────────────

async def change_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    await TokenRepository.revoke_all_user_refresh(db, user.id)
    await db.flush()

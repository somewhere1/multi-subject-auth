import logging
import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.credential import Credential, CredentialType
from app.models.session import Session
from app.models.subject import Subject, SubjectType
from app.schemas.auth import AuthResponse, LoginPasswordRequest, RegisterRequest, SubjectResponse
from app.utils.device import parse_device_name
from app.utils.security import generate_token, hash_password, hash_token, verify_password

logger = logging.getLogger(__name__)


async def register(
    db: AsyncSession,
    request: RegisterRequest,
    subject_type: SubjectType,
) -> SubjectResponse:
    """Register a new subject with password credential."""
    existing = await db.execute(
        select(Subject).where(
            Subject.email == request.email,
            Subject.subject_type == subject_type,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered for this subject type")

    subject = Subject(
        id=uuid.uuid4(),
        email=request.email,
        display_name=request.display_name,
        subject_type=subject_type,
    )
    db.add(subject)

    credential = Credential(
        subject_id=subject.id,
        credential_type=CredentialType.PASSWORD,
        credential_data={"hash": hash_password(request.password)},
    )
    db.add(credential)
    await db.commit()
    await db.refresh(subject)

    logger.info("Registered subject %s (%s)", subject.id, subject_type.value)
    return SubjectResponse.model_validate(subject)


async def login_password(
    db: AsyncSession,
    redis: aioredis.Redis,
    request: LoginPasswordRequest,
    subject_type: SubjectType,
    user_agent: str,
    ip_address: str,
) -> AuthResponse | dict:
    """Authenticate with email + password. Returns AuthResponse or MFA challenge."""
    # Rate limit: 5 failed attempts per email per 15 minutes
    rate_key = f"login_fail:{subject_type.value}:{request.email}"
    fail_count = await redis.get(rate_key)
    if fail_count and int(fail_count) >= 5:
        raise ValueError("Too many failed login attempts. Please try again later.")

    result = await db.execute(
        select(Subject).where(
            Subject.email == request.email,
            Subject.subject_type == subject_type,
            Subject.is_active == True,  # noqa: E712
        )
    )
    subject = result.scalar_one_or_none()
    if not subject:
        await _increment_login_failures(redis, rate_key)
        raise ValueError("Invalid email or password")

    cred_result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject.id,
            Credential.credential_type == CredentialType.PASSWORD,
            Credential.is_active == True,  # noqa: E712
        )
    )
    credential = cred_result.scalar_one_or_none()
    if not credential or not verify_password(request.password, credential.credential_data["hash"]):
        await _increment_login_failures(redis, rate_key)
        raise ValueError("Invalid email or password")

    credential.last_used_at = datetime.now(UTC)
    await db.commit()

    # Clear failed login counter on success
    rate_key = f"login_fail:{subject_type.value}:{request.email}"
    await redis.delete(rate_key)

    # If MFA is enabled, return a challenge token instead of a full session
    if subject.mfa_enabled:
        from app.services.mfa_service import create_mfa_challenge
        mfa_token = await create_mfa_challenge(redis, subject.id)
        return {"mfa_required": True, "mfa_token": mfa_token}

    return await _create_session(db, redis, subject, user_agent, ip_address)


async def _increment_login_failures(redis: aioredis.Redis, rate_key: str) -> None:
    """Increment failed login counter with 15-minute TTL."""
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, 900)  # 15 minutes


async def logout(
    db: AsyncSession,
    redis: aioredis.Redis,
    access_token_hash: str,
) -> None:
    """Logout: remove session from DB and Redis."""
    result = await db.execute(
        select(Session).where(Session.token_hash == access_token_hash)
    )
    session = result.scalar_one_or_none()
    if session:
        await redis.delete(f"session:{session.token_hash}")
        await db.delete(session)
        await db.commit()
        logger.info("Logged out session %s", session.id)


async def refresh_token(
    db: AsyncSession,
    redis: aioredis.Redis,
    refresh_token_str: str,
) -> AuthResponse:
    """Rotate refresh token and issue new access token."""
    old_hash = hash_token(refresh_token_str)
    result = await db.execute(
        select(Session).where(
            Session.refresh_token_hash == old_hash,
            Session.expires_at > datetime.now(UTC),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Invalid or expired refresh token")

    # Remove old access token from Redis
    await redis.delete(f"session:{session.token_hash}")

    # Generate new tokens
    new_access = generate_token()
    new_refresh = generate_token()
    session.token_hash = hash_token(new_access)
    session.refresh_token_hash = hash_token(new_refresh)
    session.last_active_at = datetime.now(UTC)
    session.expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Store new access token in Redis
    await redis.setex(
        f"session:{session.token_hash}",
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        str(session.subject_id),
    )

    await db.commit()

    subject_result = await db.execute(
        select(Subject).where(Subject.id == session.subject_id)
    )
    subject = subject_result.scalar_one()

    return AuthResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        subject=SubjectResponse.model_validate(subject),
    )


async def _create_session(
    db: AsyncSession,
    redis: aioredis.Redis,
    subject: Subject,
    user_agent: str,
    ip_address: str,
) -> AuthResponse:
    """Create a new session with access + refresh tokens."""
    access_token = generate_token()
    refresh_token_str = generate_token()

    session = Session(
        subject_id=subject.id,
        device_name=parse_device_name(user_agent),
        ip_address=ip_address,
        token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token_str),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()

    # Store access token in Redis with TTL
    await redis.setex(
        f"session:{session.token_hash}",
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        str(subject.id),
    )

    logger.info("Created session %s for subject %s", session.id, subject.id)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        subject=SubjectResponse.model_validate(subject),
    )

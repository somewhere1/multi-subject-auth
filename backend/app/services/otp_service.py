import hmac
import logging
import secrets

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject, SubjectType
from app.schemas.auth import AuthResponse, SubjectResponse
from app.services.auth_service import _create_session

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 300  # 5 minutes
OTP_LENGTH = 6


async def request_otp(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    subject_type: SubjectType,
) -> None:
    """Generate OTP and store in Redis. In demo mode, log to console."""
    result = await db.execute(
        select(Subject).where(
            Subject.email == email,
            Subject.subject_type == subject_type,
            Subject.is_active == True,  # noqa: E712
        )
    )
    subject = result.scalar_one_or_none()
    if not subject:
        # Don't reveal whether email exists — silently succeed
        logger.warning("OTP requested for unknown email: %s (%s)", email, subject_type.value)
        return

    # Rate limit: 3 requests per minute per email
    rate_key = f"otp_rate:{subject_type.value}:{email}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, 60)
    if count > 3:
        raise ValueError("Too many OTP requests. Please wait a minute.")

    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])
    otp_key = f"otp:{subject_type.value}:{email}"
    await redis.setex(otp_key, OTP_TTL_SECONDS, otp_code)

    # Demo mode: log OTP to console instead of sending email
    logger.info("=" * 50)
    logger.info("OTP for %s (%s): %s", email, subject_type.value, otp_code)
    logger.info("=" * 50)


async def verify_otp(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    otp_code: str,
    subject_type: SubjectType,
    user_agent: str,
    ip_address: str,
) -> AuthResponse:
    """Verify OTP and create session."""
    otp_key = f"otp:{subject_type.value}:{email}"
    attempts_key = f"otp_attempts:{subject_type.value}:{email}"

    # Brute-force protection: max 5 attempts per OTP
    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, OTP_TTL_SECONDS)
    if attempts > 5:
        await redis.delete(otp_key)
        await redis.delete(attempts_key)
        raise ValueError("Too many failed attempts. Please request a new OTP.")

    stored_otp = await redis.get(otp_key)

    if not stored_otp or not hmac.compare_digest(stored_otp, otp_code):
        raise ValueError("Invalid or expired OTP")

    # Delete OTP + attempts after successful verification (one-time use)
    await redis.delete(otp_key)
    await redis.delete(attempts_key)

    result = await db.execute(
        select(Subject).where(
            Subject.email == email,
            Subject.subject_type == subject_type,
            Subject.is_active == True,  # noqa: E712
        )
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise ValueError("Subject not found")

    logger.info("OTP verified for %s (%s)", email, subject_type.value)
    return await _create_session(db, redis, subject, user_agent, ip_address)

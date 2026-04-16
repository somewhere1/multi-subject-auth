import io
import logging
import uuid
from base64 import b64encode

import pyotp
import qrcode
import qrcode.image.svg
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Credential, CredentialType
from app.models.subject import Subject

logger = logging.getLogger(__name__)

MFA_ISSUER = "MultiSubjectAuth"
MFA_PENDING_TTL = 600  # 10 minutes for pending MFA challenge


async def setup_totp(
    db: AsyncSession,
    subject_id: uuid.UUID,
) -> dict:
    """Generate TOTP secret and return provisioning URI + QR code (base64 SVG)."""
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one()

    if subject.mfa_enabled:
        raise ValueError("MFA is already enabled")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=subject.email,
        issuer_name=MFA_ISSUER,
    )

    # Generate QR code as base64 SVG
    qr = qrcode.make(provisioning_uri, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    qr.save(buffer)
    qr_svg_b64 = b64encode(buffer.getvalue()).decode()

    # Store the secret temporarily as an inactive credential
    # It will be activated after verification
    existing = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject_id,
            Credential.credential_type == CredentialType.OTP,
            Credential.is_active == False,  # noqa: E712
        )
    )
    pending_cred = existing.scalar_one_or_none()
    if pending_cred:
        pending_cred.credential_data = {"secret": secret, "method": "totp"}
    else:
        pending_cred = Credential(
            subject_id=subject_id,
            credential_type=CredentialType.OTP,
            credential_data={"secret": secret, "method": "totp"},
            is_active=False,
        )
        db.add(pending_cred)
    await db.commit()

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "qr_code_svg": qr_svg_b64,
    }


async def confirm_totp(
    db: AsyncSession,
    subject_id: uuid.UUID,
    code: str,
) -> dict:
    """Verify TOTP code to confirm MFA setup, then activate."""
    result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject_id,
            Credential.credential_type == CredentialType.OTP,
            Credential.is_active == False,  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise ValueError("No pending MFA setup found. Please start setup first.")

    secret = credential.credential_data["secret"]
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise ValueError("Invalid TOTP code")

    # Activate the credential and enable MFA on subject
    credential.is_active = True
    subject_result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = subject_result.scalar_one()
    subject.mfa_enabled = True
    await db.commit()

    logger.info("MFA enabled for subject %s", subject_id)
    return {"status": "ok", "message": "MFA enabled successfully"}


async def disable_mfa(
    db: AsyncSession,
    subject_id: uuid.UUID,
    code: str,
) -> dict:
    """Disable MFA after verifying current TOTP code."""
    result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject_id,
            Credential.credential_type == CredentialType.OTP,
            Credential.is_active == True,  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise ValueError("MFA is not enabled")

    secret = credential.credential_data["secret"]
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise ValueError("Invalid TOTP code")

    credential.is_active = False
    subject_result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = subject_result.scalar_one()
    subject.mfa_enabled = False
    await db.commit()

    logger.info("MFA disabled for subject %s", subject_id)
    return {"status": "ok", "message": "MFA disabled"}


async def create_mfa_challenge(
    redis: aioredis.Redis,
    subject_id: uuid.UUID,
) -> str:
    """Create a pending MFA challenge token. Returns the mfa_token."""
    import secrets
    mfa_token = secrets.token_hex(32)
    await redis.setex(f"mfa_pending:{mfa_token}", MFA_PENDING_TTL, str(subject_id))
    return mfa_token


async def verify_mfa_challenge(
    db: AsyncSession,
    redis: aioredis.Redis,
    mfa_token: str,
    code: str,
    user_agent: str,
    ip_address: str,
) -> dict:
    """Verify MFA challenge and create full session."""
    from app.services.auth_service import _create_session

    subject_id_str = await redis.get(f"mfa_pending:{mfa_token}")
    if not subject_id_str:
        raise ValueError("MFA challenge expired or invalid")

    # Brute-force protection: max 5 attempts per MFA challenge
    attempts_key = f"mfa_attempts:{mfa_token}"
    attempts = await redis.incr(attempts_key)
    if attempts == 1:
        await redis.expire(attempts_key, MFA_PENDING_TTL)
    if attempts > 5:
        await redis.delete(f"mfa_pending:{mfa_token}")
        await redis.delete(attempts_key)
        raise ValueError("Too many failed attempts. Please login again.")

    subject_id = uuid.UUID(subject_id_str)

    # Verify TOTP
    result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject_id,
            Credential.credential_type == CredentialType.OTP,
            Credential.is_active == True,  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise ValueError("MFA credential not found")

    secret = credential.credential_data["secret"]
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise ValueError("Invalid TOTP code")

    # Delete challenge + attempts
    await redis.delete(f"mfa_pending:{mfa_token}")
    await redis.delete(attempts_key)

    # Create full session
    subject_result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = subject_result.scalar_one()

    auth_response = await _create_session(db, redis, subject, user_agent, ip_address)
    logger.info("MFA verified for subject %s", subject_id)
    return {
        "access_token": auth_response.access_token,
        "refresh_token": auth_response.refresh_token,
        "token_type": "bearer",
        "subject": auth_response.subject.model_dump(),
    }

import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.models.credential import Credential, CredentialType
from app.models.subject import Subject, SubjectType
from app.schemas.auth import AuthResponse
from app.services.auth_service import _create_session

logger = logging.getLogger(__name__)

RP_ID = "localhost"
RP_NAME = "Multi-Subject Auth"
ORIGIN = "http://localhost:5173"
CHALLENGE_TTL = 300  # 5 minutes


async def registration_options(
    db: AsyncSession,
    redis: aioredis.Redis,
    subject_id: uuid.UUID,
) -> dict:
    """Generate WebAuthn registration options for a logged-in subject."""
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one()

    # Get existing passkey credentials
    cred_result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject_id,
            Credential.credential_type == CredentialType.PASSKEY,
            Credential.is_active == True,  # noqa: E712
        )
    )
    existing_creds = cred_result.scalars().all()
    exclude_credentials = [
        PublicKeyCredentialDescriptor(
            id=base64url_to_bytes(c.credential_data["credential_id"])
        )
        for c in existing_creds
    ]

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(subject.id).encode(),
        user_name=subject.email,
        user_display_name=subject.display_name,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    # Store challenge in Redis
    challenge_key = f"webauthn_reg:{subject.id}"
    await redis.setex(challenge_key, CHALLENGE_TTL, bytes_to_base64url(options.challenge))

    # Serialize for JSON response
    return {
        "rp": {"id": options.rp.id, "name": options.rp.name},
        "user": {
            "id": bytes_to_base64url(options.user.id),
            "name": options.user.name,
            "displayName": options.user.display_name,
        },
        "challenge": bytes_to_base64url(options.challenge),
        "pubKeyCredParams": [
            {"type": "public-key", "alg": p.alg} for p in options.pub_key_cred_params
        ],
        "timeout": options.timeout,
        "excludeCredentials": [
            {"type": "public-key", "id": bytes_to_base64url(c.id)}
            for c in (options.exclude_credentials or [])
        ],
        "authenticatorSelection": {
            "residentKey": options.authenticator_selection.resident_key.value
            if options.authenticator_selection
            else "preferred",
            "userVerification": options.authenticator_selection.user_verification.value
            if options.authenticator_selection
            else "preferred",
        },
        "attestation": options.attestation.value if options.attestation else "none",
    }


async def verify_registration(
    db: AsyncSession,
    redis: aioredis.Redis,
    subject_id: uuid.UUID,
    credential_json: dict,
) -> dict:
    """Verify WebAuthn registration response and store credential."""
    challenge_key = f"webauthn_reg:{subject_id}"
    stored_challenge = await redis.get(challenge_key)
    if not stored_challenge:
        raise ValueError("Registration challenge expired")
    await redis.delete(challenge_key)

    verification = verify_registration_response(
        credential=credential_json,
        expected_challenge=base64url_to_bytes(stored_challenge),
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
    )

    # Store credential
    credential = Credential(
        subject_id=subject_id,
        credential_type=CredentialType.PASSKEY,
        credential_data={
            "credential_id": bytes_to_base64url(verification.credential_id),
            "public_key": bytes_to_base64url(verification.credential_public_key),
            "sign_count": verification.sign_count,
            "transports": credential_json.get("response", {}).get("transports", []),
        },
    )
    db.add(credential)
    await db.commit()

    logger.info("Passkey registered for subject %s", subject_id)
    return {"status": "ok", "credential_id": str(credential.id)}


async def authentication_options(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    subject_type: SubjectType,
) -> dict:
    """Generate WebAuthn authentication options."""
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

    cred_result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject.id,
            Credential.credential_type == CredentialType.PASSKEY,
            Credential.is_active == True,  # noqa: E712
        )
    )
    credentials = cred_result.scalars().all()
    if not credentials:
        raise ValueError("No passkeys registered for this account")

    allow_credentials = [
        PublicKeyCredentialDescriptor(
            id=base64url_to_bytes(c.credential_data["credential_id"]),
        )
        for c in credentials
    ]

    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    # Store challenge
    challenge_key = f"webauthn_auth:{subject_type.value}:{email}"
    await redis.setex(challenge_key, CHALLENGE_TTL, bytes_to_base64url(options.challenge))

    return {
        "challenge": bytes_to_base64url(options.challenge),
        "timeout": options.timeout,
        "rpId": RP_ID,
        "allowCredentials": [
            {
                "type": "public-key",
                "id": bytes_to_base64url(c.id),
            }
            for c in (options.allow_credentials or [])
        ],
        "userVerification": options.user_verification.value if options.user_verification else "preferred",
    }


async def verify_authentication(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    subject_type: SubjectType,
    credential_json: dict,
    user_agent: str,
    ip_address: str,
) -> AuthResponse:
    """Verify WebAuthn authentication response and create session."""
    challenge_key = f"webauthn_auth:{subject_type.value}:{email}"
    stored_challenge = await redis.get(challenge_key)
    if not stored_challenge:
        raise ValueError("Authentication challenge expired")
    await redis.delete(challenge_key)

    # Find the subject
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

    # Find matching credential
    credential_id = credential_json.get("id", "")
    cred_result = await db.execute(
        select(Credential).where(
            Credential.subject_id == subject.id,
            Credential.credential_type == CredentialType.PASSKEY,
            Credential.is_active == True,  # noqa: E712
        )
    )
    credentials = cred_result.scalars().all()
    matched_cred = None
    for c in credentials:
        if c.credential_data["credential_id"] == credential_id:
            matched_cred = c
            break

    if not matched_cred:
        raise ValueError("Credential not found")

    verification = verify_authentication_response(
        credential=credential_json,
        expected_challenge=base64url_to_bytes(stored_challenge),
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        credential_public_key=base64url_to_bytes(matched_cred.credential_data["public_key"]),
        credential_current_sign_count=matched_cred.credential_data["sign_count"],
    )

    # Update sign count
    matched_cred.credential_data = {
        **matched_cred.credential_data,
        "sign_count": verification.new_sign_count,
    }
    matched_cred.last_used_at = datetime.now(UTC)
    await db.commit()

    logger.info("Passkey auth successful for %s (%s)", email, subject_type.value)
    return await _create_session(db, redis, subject, user_agent, ip_address)

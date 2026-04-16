import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.dependencies import AuthenticatedSubject, get_current_subject
from app.models.credential import Credential
from app.services import passkey_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("/")
async def list_credentials(
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Credential).where(
            Credential.subject_id == auth.subject.id,
            Credential.is_active == True,  # noqa: E712
        )
    )
    creds = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "type": c.credential_type.value,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        }
        for c in creds
    ]


@router.post("/passkey/register/options")
async def passkey_register_options(
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    return await passkey_service.registration_options(db, redis, auth.subject.id)


@router.post("/passkey/register/verify")
async def passkey_register_verify(
    req: Request,
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    body = await req.json()
    try:
        return await passkey_service.verify_registration(db, redis, auth.subject.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: uuid.UUID,
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Credential).where(
            Credential.id == credential_id,
            Credential.subject_id == auth.subject.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    cred.is_active = False
    await db.commit()

import uuid
import logging

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.models.subject import Subject
from app.utils.security import hash_token

logger = logging.getLogger(__name__)


class AuthenticatedSubject:
    """Holds the authenticated subject and token hash for the current request."""

    def __init__(self, subject: Subject, token_hash: str) -> None:
        self.subject = subject
        self.token_hash = token_hash


async def get_current_subject(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthenticatedSubject:
    """Extract and validate the access token, return the authenticated subject."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.removeprefix("Bearer ")
    token_h = hash_token(token)

    # Look up in Redis first (fast path)
    subject_id_str = await redis.get(f"session:{token_h}")
    if not subject_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid",
        )

    result = await db.execute(
        select(Subject).where(Subject.id == uuid.UUID(subject_id_str))
    )
    subject = result.scalar_one_or_none()
    if not subject or not subject.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Subject not found or inactive",
        )

    return AuthenticatedSubject(subject=subject, token_hash=token_h)

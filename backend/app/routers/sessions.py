import uuid
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.dependencies import AuthenticatedSubject, get_current_subject
from app.schemas.session import SessionResponse
from app.services import session_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    return await session_service.list_sessions(db, auth.subject.id, auth.token_hash)


@router.delete("/{session_id}", status_code=204)
async def revoke_session(
    session_id: uuid.UUID,
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    try:
        await session_service.revoke_session(db, redis, session_id, auth.subject.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

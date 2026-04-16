

import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.schemas.session import SessionResponse

logger = logging.getLogger(__name__)


async def list_sessions(
    db: AsyncSession,
    subject_id: uuid.UUID,
    current_token_hash: str,
) -> list[SessionResponse]:
    """List all active (non-expired) sessions for a subject."""
    result = await db.execute(
        select(Session)
        .where(
            Session.subject_id == subject_id,
            Session.expires_at > datetime.now(UTC),
        )
        .order_by(Session.last_active_at.desc())
    )
    sessions = result.scalars().all()

    return [
        SessionResponse(
            id=s.id,
            device_name=s.device_name,
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_active_at=s.last_active_at,
            is_current=(s.token_hash == current_token_hash),
        )
        for s in sessions
    ]


async def revoke_session(
    db: AsyncSession,
    redis: aioredis.Redis,
    session_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> None:
    """Revoke a specific session (kick device)."""
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.subject_id == subject_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Session not found")

    await redis.delete(f"session:{session.token_hash}")
    await db.delete(session)
    await db.commit()
    logger.info("Revoked session %s", session_id)

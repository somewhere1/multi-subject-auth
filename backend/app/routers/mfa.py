import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.dependencies import AuthenticatedSubject, get_current_subject
from app.schemas.mfa import MfaConfirmRequest, MfaDisableRequest, MfaVerifyRequest
from app.services import mfa_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mfa", tags=["mfa"])


@router.post("/setup")
async def setup_mfa(
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start MFA setup — returns TOTP secret and QR code."""
    try:
        return await mfa_service.setup_totp(db, auth.subject.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/confirm")
async def confirm_mfa(
    request: MfaConfirmRequest,
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify TOTP code to activate MFA."""
    try:
        return await mfa_service.confirm_totp(db, auth.subject.id, request.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/disable")
async def disable_mfa(
    request: MfaDisableRequest,
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disable MFA after TOTP verification."""
    try:
        return await mfa_service.disable_mfa(db, auth.subject.id, request.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify")
async def verify_mfa(
    request: MfaVerifyRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    """Verify MFA challenge during login (no auth required — uses mfa_token)."""
    user_agent = req.headers.get("User-Agent", "")
    ip_address = req.client.host if req.client else "unknown"
    try:
        return await mfa_service.verify_mfa_challenge(
            db, redis, request.mfa_token, request.code, user_agent, ip_address
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

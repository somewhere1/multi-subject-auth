import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.dependencies import AuthenticatedSubject, get_current_subject
from app.models.subject import SubjectType
from app.schemas.auth import (
    AuthResponse,
    LoginPasswordRequest,
    RefreshRequest,
    RegisterRequest,
    SubjectResponse,
)
from app.schemas.otp import OtpRequestBody, OtpVerifyBody
from app.schemas.passkey import PasskeyLoginOptionsRequest
from app.services import auth_service, otp_service, passkey_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _parse_subject_type(subject_type: str) -> SubjectType:
    mapping = {
        "member": SubjectType.MEMBER,
        "community-staff": SubjectType.COMMUNITY_STAFF,
        "platform-staff": SubjectType.PLATFORM_STAFF,
    }
    st = mapping.get(subject_type)
    if not st:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subject type: {subject_type}",
        )
    return st


@router.post("/{subject_type}/register", response_model=SubjectResponse, status_code=201)
async def register(
    subject_type: str,
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> SubjectResponse:
    st = _parse_subject_type(subject_type)
    try:
        return await auth_service.register(db, request, st)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{subject_type}/login/password")
async def login_password(
    subject_type: str,
    request: LoginPasswordRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthResponse | dict:
    st = _parse_subject_type(subject_type)
    user_agent = req.headers.get("User-Agent", "")
    ip_address = req.client.host if req.client else "unknown"
    try:
        return await auth_service.login_password(db, redis, request, st, user_agent, ip_address)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=204)
async def logout(
    auth: AuthenticatedSubject = Depends(get_current_subject),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    await auth_service.logout(db, redis, auth.token_hash)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthResponse:
    try:
        return await auth_service.refresh_token(db, redis, request.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=SubjectResponse)
async def get_me(
    auth: AuthenticatedSubject = Depends(get_current_subject),
) -> SubjectResponse:
    return SubjectResponse.model_validate(auth.subject)


# --- OTP endpoints ---


@router.post("/{subject_type}/login/otp/request", status_code=202)
async def otp_request(
    subject_type: str,
    body: OtpRequestBody,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, str]:
    st = _parse_subject_type(subject_type)
    try:
        await otp_service.request_otp(db, redis, body.email, st)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    return {"message": "If the email exists, an OTP has been sent"}


@router.post("/{subject_type}/login/otp/verify", response_model=AuthResponse)
async def otp_verify(
    subject_type: str,
    body: OtpVerifyBody,
    req: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthResponse:
    st = _parse_subject_type(subject_type)
    user_agent = req.headers.get("User-Agent", "")
    ip_address = req.client.host if req.client else "unknown"
    try:
        return await otp_service.verify_otp(db, redis, body.email, body.otp_code, st, user_agent, ip_address)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# --- Passkey endpoints ---


@router.post("/{subject_type}/login/passkey/options")
async def passkey_login_options(
    subject_type: str,
    body: PasskeyLoginOptionsRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    st = _parse_subject_type(subject_type)
    try:
        return await passkey_service.authentication_options(db, redis, body.email, st)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{subject_type}/login/passkey/verify", response_model=AuthResponse)
async def passkey_login_verify(
    subject_type: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthResponse:
    st = _parse_subject_type(subject_type)
    body = await req.json()
    email = body.get("email", "")
    credential = body.get("credential", {})
    user_agent = req.headers.get("User-Agent", "")
    ip_address = req.client.host if req.client else "unknown"
    try:
        return await passkey_service.verify_authentication(
            db, redis, email, st, credential, user_agent, ip_address
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

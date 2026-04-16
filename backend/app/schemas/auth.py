import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.subject import SubjectType


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)


class LoginPasswordRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    subject: "SubjectResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class SubjectResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    subject_type: SubjectType
    mfa_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}

from pydantic import BaseModel, Field


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str = Field(..., min_length=6, max_length=6)


class MfaConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class MfaDisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

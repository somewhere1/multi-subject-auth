from pydantic import BaseModel, Field


class OtpRequestBody(BaseModel):
    email: str = Field(..., max_length=255)


class OtpVerifyBody(BaseModel):
    email: str = Field(..., max_length=255)
    otp_code: str = Field(..., min_length=6, max_length=6)

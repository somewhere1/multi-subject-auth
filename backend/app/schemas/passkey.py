from pydantic import BaseModel, Field


class PasskeyLoginOptionsRequest(BaseModel):
    email: str = Field(..., max_length=255)

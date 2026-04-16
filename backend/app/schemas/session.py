import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: uuid.UUID
    device_name: str | None
    ip_address: str | None
    created_at: datetime
    last_active_at: datetime
    is_current: bool

    model_config = {"from_attributes": True}

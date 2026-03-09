from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    spotify_id: str
    display_name: str | None
    email: str | None
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusResponse(BaseModel):
    ok: bool
    message: str

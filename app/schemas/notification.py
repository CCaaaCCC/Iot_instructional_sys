from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    title: str
    content: str
    link: str | None = None


class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    content: str
    link: str | None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

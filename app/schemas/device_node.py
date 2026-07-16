from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceNodeBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=100)


class DeviceNodeCreate(DeviceNodeBase):
    pass


class DeviceNodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    online: bool | None = None
    last_reported_at: datetime | None = None


class DeviceNodeOut(DeviceNodeBase):
    id: int
    online: bool
    last_reported_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

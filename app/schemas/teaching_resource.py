from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeachingResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    resource_type: str = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=20)
    classroom_id: int | None = None
    group_id: int | None = None
    task_id: int | None = None
    is_published: bool = False


class TeachingResourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    resource_type: str | None = Field(default=None, max_length=20)
    subject: str | None = Field(default=None, max_length=20)
    classroom_id: int | None = None
    group_id: int | None = None
    task_id: int | None = None
    is_published: bool | None = None


class TeachingResourceOut(BaseModel):
    id: int
    title: str
    description: str | None
    resource_type: str
    file_url: str
    preview_url: str | None
    file_size: int | None
    subject: str
    classroom_id: int | None
    group_id: int | None
    task_id: int | None
    is_published: bool
    publisher_id: int
    download_count: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

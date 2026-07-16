from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CoursewareCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    file_type: str = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=20)
    grade_level: str | None = Field(default=None, max_length=20)
    tags: str | None = Field(default=None, max_length=255)
    is_public: bool = False


class CoursewareUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    subject: str | None = Field(default=None, max_length=20)
    grade_level: str | None = Field(default=None, max_length=20)
    tags: str | None = Field(default=None, max_length=255)
    is_public: bool | None = None


class CoursewareOut(BaseModel):
    id: int
    title: str
    description: str | None
    file_type: str
    file_url: str
    preview_url: str | None
    file_size: int | None
    subject: str
    grade_level: str | None
    tags: str | None
    is_public: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CoursewareListOut(BaseModel):
    id: int
    title: str
    description: str | None
    file_type: str
    file_url: str
    preview_url: str | None
    file_size: int | None
    subject: str
    grade_level: str | None
    tags: str | None
    is_public: bool
    owner_id: int
    owner_name: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

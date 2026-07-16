from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CourseSubject


class ClassroomBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject: CourseSubject


class ClassroomCreate(ClassroomBase):
    teacher_id: int | None = None


class ClassroomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    subject: CourseSubject | None = None
    teacher_id: int | None = None


class ClassroomOut(ClassroomBase):
    id: int
    teacher_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

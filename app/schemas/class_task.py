from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CourseSubject, TaskStatus, TaskType


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    assigned_date: date | None = None
    due_date: date | None = None
    status: TaskStatus = TaskStatus.pending
    group_id: int | None = None
    course_subject: CourseSubject | None = None
    task_type: TaskType | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    assigned_date: date | None = None
    due_date: date | None = None
    status: TaskStatus | None = None
    group_id: int | None = None
    course_subject: CourseSubject | None = None
    task_type: TaskType | None = None


class TaskOut(TaskBase):
    id: int
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

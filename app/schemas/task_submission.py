from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.submission_file import SubmissionFileOut


class TaskSubmissionCreate(BaseModel):
    content: str | None = Field(default=None, max_length=500)


class TaskSubmissionOut(BaseModel):
    id: int
    task_id: int
    student_id: int
    content: str | None
    submitted_at: datetime
    score: int | None
    feedback: str | None
    reviewed_at: datetime | None
    reviewed_by: int | None
    files: list[SubmissionFileOut] = []

    model_config = ConfigDict(from_attributes=True)


class SubmissionReview(BaseModel):
    score: int = Field(ge=0, le=100)
    feedback: str | None = Field(default=None, max_length=255)

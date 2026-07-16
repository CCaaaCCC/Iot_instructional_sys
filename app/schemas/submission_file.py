from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubmissionFileOut(BaseModel):
    id: int
    submission_id: int
    filename: str
    original_name: str
    file_url: str
    file_size: int
    file_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

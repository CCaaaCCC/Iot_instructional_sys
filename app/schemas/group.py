from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import _validate_password_complexity


class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    class_id: int = Field(gt=0)
    node_id: int | None = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    node_id: int | None = None


class GroupOut(GroupBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchStudentCreate(BaseModel):
    group_id: int = Field(gt=0)
    count: int = Field(gt=0, le=50)
    password: str = Field(min_length=8, max_length=128)
    display_names: list[str] | None = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_complexity(v)

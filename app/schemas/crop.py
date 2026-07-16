from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CropBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    growth_stage: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)
    group_id: int | None = None


class CropCreate(CropBase):
    pass


class CropUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    growth_stage: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)
    group_id: int | None = None


class CropOut(CropBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

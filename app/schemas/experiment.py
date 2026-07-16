from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExperimentRole, ExperimentStatus, SensorMetric


class ExperimentBase(BaseModel):
    class_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=100)
    hypothesis: str = Field(min_length=1, max_length=255)
    variable_metric: SensorMetric
    start_date: date
    end_date: date
    status: ExperimentStatus = ExperimentStatus.ongoing
    conclusion: str | None = Field(default=None, max_length=500)


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    hypothesis: str | None = Field(default=None, min_length=1, max_length=255)
    variable_metric: SensorMetric | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ExperimentStatus | None = None
    conclusion: str | None = Field(default=None, max_length=500)


class ExperimentOut(ExperimentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentGroupCreate(BaseModel):
    group_id: int = Field(ge=1)
    role: ExperimentRole
    variable_target: str | None = Field(default=None, max_length=100)


class ExperimentGroupOut(ExperimentGroupCreate):
    id: int
    experiment_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentObservationCreate(BaseModel):
    sensor_data_id: int | None = None
    content: str | None = Field(default=None, max_length=500)


class ExperimentObservationOut(ExperimentObservationCreate):
    id: int
    experiment_id: int
    student_id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

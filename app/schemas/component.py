from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComponentStatus, ComponentType, SensorMetric


class ComponentBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: ComponentType
    metric: SensorMetric | None = None


class ComponentCreate(ComponentBase):
    pass


class ComponentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    status: ComponentStatus | None = None
    metric: SensorMetric | None = None


class ComponentOut(ComponentBase):
    id: int
    node_id: int
    status: ComponentStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComponentControlRequest(BaseModel):
    action: ComponentStatus
    message: str | None = Field(default=None, max_length=255)

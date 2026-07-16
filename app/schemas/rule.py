from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComponentStatus, ComponentType, RuleOperator, SensorMetric


class RuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    metric: SensorMetric
    operator: RuleOperator
    threshold: float
    action_component_type: ComponentType
    action: ComponentStatus
    enabled: bool = True
    description: str | None = Field(default=None, max_length=255)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    metric: SensorMetric | None = None
    operator: RuleOperator | None = None
    threshold: float | None = None
    action_component_type: ComponentType | None = None
    action: ComponentStatus | None = None
    enabled: bool | None = None
    description: str | None = Field(default=None, max_length=255)


class RuleOut(RuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

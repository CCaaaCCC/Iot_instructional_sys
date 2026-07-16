from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RuleLogOut(BaseModel):
    id: int
    rule_id: int
    sensor_data_id: int | None
    node_id: int | None
    component_id: int | None
    message: str | None
    triggered_at: datetime

    model_config = ConfigDict(from_attributes=True)

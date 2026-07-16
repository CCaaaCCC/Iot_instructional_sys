from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ComponentStatus


class DeviceOperationLogOut(BaseModel):
    id: int
    node_id: int | None
    component_id: int | None
    operator_id: int | None
    action: ComponentStatus
    message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

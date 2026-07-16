from pydantic import BaseModel

from app.models.enums import ComponentType
from app.schemas.sensor_data import SensorDataOut


class ComponentSummary(BaseModel):
    type: ComponentType
    total: int
    status_on: int
    status_off: int
    status_auto: int


class DashboardOverview(BaseModel):
    total_nodes: int
    online_nodes: int
    total_rules: int
    enabled_rules: int
    total_tasks: int
    pending_tasks: int
    latest_sensor_data: SensorDataOut | None

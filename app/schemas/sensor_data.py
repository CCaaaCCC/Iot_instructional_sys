from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SensorDataCreate(BaseModel):
    node_id: int = Field(gt=0)
    air_temp: float | None = Field(default=None, ge=-50, le=80)
    air_humidity: float | None = Field(default=None, ge=0, le=100)
    soil_humidity: float | None = Field(default=None, ge=0, le=100)
    light_intensity: float | None = Field(default=None, ge=0, le=100000)
    soil_ph: float | None = Field(default=None, ge=0, le=14)
    co2: float | None = Field(default=None, ge=0, le=5000)
    recorded_at: datetime | None = None


class SensorDataOut(SensorDataCreate):
    id: int
    created_at: datetime
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EChartsSeries(BaseModel):
    name: str
    data: list[float | None]


class EChartsResponse(BaseModel):
    x: list[str]
    series: list[EChartsSeries]

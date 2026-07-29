from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.device_node import DeviceNode
from app.models.enums import SensorMetric
from app.models.sensor_data import SensorData
from app.schemas.sensor_data import EChartsResponse, EChartsSeries, SensorDataCreate
from app.services import rule_service


def create_sensor_data(db: Session, data_in: SensorDataCreate) -> SensorData:
    node = db.get(DeviceNode, data_in.node_id)
    if not node:
        raise ValueError("Device node not found")
    recorded_at = data_in.recorded_at or datetime.now()
    sensor_data = SensorData(
        node_id=data_in.node_id,
        air_temp=data_in.air_temp,
        air_humidity=data_in.air_humidity,
        soil_humidity=data_in.soil_humidity,
        light_intensity=data_in.light_intensity,
        soil_ph=data_in.soil_ph,
        co2=data_in.co2,
        recorded_at=recorded_at,
    )
    db.add(sensor_data)
    node.last_reported_at = recorded_at
    node.online = True
    db.flush()
    rule_service.evaluate_rules(db, sensor_data)
    db.commit()
    db.refresh(sensor_data)
    # WebSocket 实时广播
    from app.core.websocket_manager import ws_manager
    ws_manager.broadcast_sync("sensor_data", {
        "id": sensor_data.id,
        "node_id": sensor_data.node_id,
        "air_temp": sensor_data.air_temp,
        "air_humidity": sensor_data.air_humidity,
        "soil_humidity": sensor_data.soil_humidity,
        "light_intensity": sensor_data.light_intensity,
        "soil_ph": sensor_data.soil_ph,
        "co2": sensor_data.co2,
        "recorded_at": sensor_data.recorded_at.isoformat() if sensor_data.recorded_at else None,
    }, node_id=sensor_data.node_id)
    return sensor_data


def list_sensor_data(
    db: Session,
    node_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SensorData]:
    stmt = select(SensorData)
    if node_id is not None:
        stmt = stmt.where(SensorData.node_id == node_id)
    if start_time:
        stmt = stmt.where(SensorData.recorded_at >= start_time)
    if end_time:
        stmt = stmt.where(SensorData.recorded_at <= end_time)
    stmt = stmt.order_by(SensorData.recorded_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def latest_sensor_data(db: Session, node_id: int | None = None) -> SensorData | None:
    stmt = select(SensorData)
    if node_id is not None:
        stmt = stmt.where(SensorData.node_id == node_id)
    stmt = stmt.order_by(desc(SensorData.recorded_at)).limit(1)
    return db.execute(stmt).scalar_one_or_none()


def build_echarts_data(
    rows: list[SensorData], metrics: list[SensorMetric] | None
) -> EChartsResponse:
    metrics = metrics or [metric for metric in SensorMetric]
    x_values = [row.recorded_at.isoformat() for row in reversed(rows)]
    series = []
    for metric in metrics:
        values: list[float | None] = []
        for row in reversed(rows):
            values.append(getattr(row, metric.value))
        series.append(EChartsSeries(name=metric.value, data=values))
    return EChartsResponse(x=x_values, series=series)

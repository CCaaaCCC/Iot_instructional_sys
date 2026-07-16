from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_task import ClassTask
from app.models.component import Component
from app.models.device_node import DeviceNode
from app.models.enums import ComponentStatus, ComponentType, TaskStatus
from app.models.rule import Rule
from app.models.sensor_data import SensorData


def component_summary(db: Session) -> list[dict]:
    components = db.execute(select(Component)).scalars().all()
    summary_map: dict[ComponentType, dict] = {}
    for comp in components:
        if comp.type not in summary_map:
            summary_map[comp.type] = {
                "type": comp.type,
                "total": 0,
                "status_on": 0,
                "status_off": 0,
                "status_auto": 0,
            }
        item = summary_map[comp.type]
        item["total"] += 1
        if comp.status == ComponentStatus.on:
            item["status_on"] += 1
        elif comp.status == ComponentStatus.off:
            item["status_off"] += 1
        elif comp.status == ComponentStatus.auto:
            item["status_auto"] += 1
    return list(summary_map.values())


def overview(db: Session) -> dict:
    total_nodes = db.execute(select(func.count(DeviceNode.id))).scalar_one()
    online_nodes = (
        db.execute(select(func.count(DeviceNode.id)).where(DeviceNode.online.is_(True)))
        .scalar_one()
    )
    total_rules = db.execute(select(func.count(Rule.id))).scalar_one()
    enabled_rules = (
        db.execute(select(func.count(Rule.id)).where(Rule.enabled.is_(True)))
        .scalar_one()
    )
    total_tasks = db.execute(select(func.count(ClassTask.id))).scalar_one()
    pending_tasks = (
        db.execute(
            select(func.count(ClassTask.id)).where(ClassTask.status == TaskStatus.pending)
        )
        .scalar_one()
    )
    latest_sensor = (
        db.execute(select(SensorData).order_by(SensorData.recorded_at.desc()).limit(1))
        .scalar_one_or_none()
    )
    return {
        "total_nodes": total_nodes,
        "online_nodes": online_nodes,
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "latest_sensor_data": latest_sensor,
    }

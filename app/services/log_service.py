from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_log import DeviceOperationLog
from app.models.operation_log import OperationLog
from app.models.rule_log import RuleLog


def create_operation_log(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    detail: str | None = None,
) -> OperationLog:
    log = OperationLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(log)
    db.flush()
    return log


def list_operation_logs(
    db: Session,
    user_id: int | None = None,
    entity_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[OperationLog]:
    stmt = select(OperationLog).order_by(OperationLog.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(OperationLog.user_id == user_id)
    if entity_type:
        stmt = stmt.where(OperationLog.entity_type == entity_type)
    if start_time:
        stmt = stmt.where(OperationLog.created_at >= start_time)
    if end_time:
        stmt = stmt.where(OperationLog.created_at <= end_time)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def list_device_logs(
    db: Session,
    node_id: int | None = None,
    component_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[DeviceOperationLog]:
    stmt = select(DeviceOperationLog).order_by(DeviceOperationLog.created_at.desc())
    if node_id is not None:
        stmt = stmt.where(DeviceOperationLog.node_id == node_id)
    if component_id is not None:
        stmt = stmt.where(DeviceOperationLog.component_id == component_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def list_rule_logs(
    db: Session,
    rule_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[RuleLog]:
    stmt = select(RuleLog).order_by(RuleLog.triggered_at.desc())
    if rule_id is not None:
        stmt = stmt.where(RuleLog.rule_id == rule_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()

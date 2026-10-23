import logging
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.device_log import DeviceOperationLog
from app.models.enums import RuleOperator
from app.models.operation_log import OperationLog
from app.models.rule import Rule
from app.models.rule_log import RuleLog
from app.models.sensor_data import SensorData
from app.schemas.rule import RuleCreate, RuleUpdate

logger = logging.getLogger(__name__)


def list_rules(db: Session, skip: int = 0, limit: int = 200) -> list[Rule]:
    stmt = select(Rule).order_by(Rule.created_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_rule(db: Session, rule_id: int) -> Rule | None:
    return db.get(Rule, rule_id)


def create_rule(db: Session, rule_in: RuleCreate) -> Rule:
    existing = db.execute(select(Rule).where(Rule.name == rule_in.name)).scalar_one_or_none()
    if existing:
        raise ValueError("Rule name already exists")
    rule = Rule(
        name=rule_in.name,
        metric=rule_in.metric,
        operator=rule_in.operator,
        threshold=rule_in.threshold,
        action_component_type=rule_in.action_component_type,
        action=rule_in.action,
        enabled=rule_in.enabled,
        description=rule_in.description,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule: Rule, rule_in: RuleUpdate) -> Rule:
    if rule_in.name and rule_in.name != rule.name:
        existing = db.execute(select(Rule).where(Rule.name == rule_in.name)).scalar_one_or_none()
        if existing:
            raise ValueError("Rule name already exists")
        rule.name = rule_in.name
    if rule_in.metric is not None:
        rule.metric = rule_in.metric
    if rule_in.operator is not None:
        rule.operator = rule_in.operator
    if rule_in.threshold is not None:
        rule.threshold = rule_in.threshold
    if rule_in.action_component_type is not None:
        rule.action_component_type = rule_in.action_component_type
    if rule_in.action is not None:
        rule.action = rule_in.action
    if rule_in.enabled is not None:
        rule.enabled = rule_in.enabled
    if rule_in.description is not None:
        rule.description = rule_in.description
    db.commit()
    db.refresh(rule)
    return rule


def toggle_rule(db: Session, rule: Rule) -> Rule:
    rule.enabled = not rule.enabled
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule: Rule) -> None:
    # rule_logs.rule_id 为非空外键，需先清理，避免 MySQL 外键约束导致删除失败
    db.execute(delete(RuleLog).where(RuleLog.rule_id == rule.id))
    db.delete(rule)
    db.commit()


def _compare(value: float, operator: RuleOperator, threshold: float) -> bool:
    if operator == RuleOperator.gt:
        return value > threshold
    if operator == RuleOperator.gte:
        return value >= threshold
    if operator == RuleOperator.lt:
        return value < threshold
    if operator == RuleOperator.lte:
        return value <= threshold
    return False


def evaluate_rules(db: Session, sensor_data: SensorData) -> int:
    rules = db.execute(select(Rule).where(Rule.enabled.is_(True))).scalars().all()
    triggered = 0
    for rule in rules:
        value = getattr(sensor_data, rule.metric.value)
        if value is None:
            continue
        if not _compare(value, rule.operator, rule.threshold):
            continue
        components = (
            db.execute(
                select(Component).where(
                    Component.type == rule.action_component_type,
                    Component.node_id == sensor_data.node_id,
                )
            )
            .scalars()
            .all()
        )
        if not components:
            db.add(
                RuleLog(
                    rule_id=rule.id,
                    sensor_data_id=sensor_data.id,
                    node_id=None,
                    component_id=None,
                    message="No matching components for rule",
                )
            )
            triggered += 1
            continue
        for component in components:
            component.status = rule.action
            db.add(
                DeviceOperationLog(
                    node_id=component.node_id,
                    component_id=component.id,
                    operator_id=None,
                    action=rule.action,
                    message=f"Rule '{rule.name}' triggered",
                )
            )
            db.add(
                RuleLog(
                    rule_id=rule.id,
                    sensor_data_id=sensor_data.id,
                    node_id=component.node_id,
                    component_id=component.id,
                    message=f"Applied action {rule.action}",
                )
            )
            db.add(
                OperationLog(
                    user_id=None,
                    action="rule_trigger",
                    entity_type="rule",
                    entity_id=str(rule.id),
                    detail=f"Rule '{rule.name}' applied to component {component.id}",
                )
            )
            from app.core.mqtt_client import publish_component_control

            if not publish_component_control(
                component.node_id, component.id, rule.action.value,
                f"Rule '{rule.name}' triggered",
                component_type=component.type.value,
            ):
                logger.warning(
                    "Rule '%s' triggered but MQTT control NOT delivered (broker down) for component %s",
                    rule.name, component.id,
                )
            triggered += 1
            # WebSocket 实时广播组件状态变更
            from app.core.websocket_manager import ws_manager
            ws_manager.broadcast_sync("component_status", {
                "component_id": component.id,
                "node_id": component.node_id,
                "type": component.type.value,
                "status": component.status.value,
                "triggered_by_rule": rule.name,
            }, node_id=component.node_id)
    return triggered

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.component import Component
from app.models.device_log import DeviceOperationLog
from app.models.device_node import DeviceNode
from app.models.enums import ComponentStatus, ComponentType
from app.models.operation_log import OperationLog
from app.schemas.component import ComponentCreate, ComponentUpdate
from app.schemas.device_node import DeviceNodeCreate, DeviceNodeUpdate

logger = logging.getLogger(__name__)


def list_nodes(
    db: Session,
    online: bool | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[DeviceNode]:
    stmt = select(DeviceNode)
    if online is not None:
        stmt = stmt.where(DeviceNode.online == online)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_node(db: Session, node_id: int) -> DeviceNode | None:
    return db.get(DeviceNode, node_id)


def get_node_by_name(db: Session, name: str) -> DeviceNode | None:
    return db.execute(select(DeviceNode).where(DeviceNode.name == name)).scalar_one_or_none()


def create_node(db: Session, node_in: DeviceNodeCreate) -> DeviceNode:
    existing = get_node_by_name(db, node_in.name)
    if existing:
        raise ValueError("Node name already exists")
    node = DeviceNode(name=node_in.name, location=node_in.location)
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def update_node(db: Session, node: DeviceNode, node_in: DeviceNodeUpdate) -> DeviceNode:
    if node_in.name and node_in.name != node.name:
        existing = get_node_by_name(db, node_in.name)
        if existing:
            raise ValueError("Node name already exists")
        node.name = node_in.name
    if node_in.location is not None:
        node.location = node_in.location
    if node_in.online is not None:
        node.online = node_in.online
    if node_in.last_reported_at is not None:
        node.last_reported_at = node_in.last_reported_at
    db.commit()
    db.refresh(node)
    return node


def delete_node(db: Session, node: DeviceNode) -> None:
    db.delete(node)
    db.commit()


def list_components(
    db: Session,
    node_id: int | None = None,
    component_type: ComponentType | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[Component]:
    stmt = select(Component)
    if node_id is not None:
        stmt = stmt.where(Component.node_id == node_id)
    if component_type:
        stmt = stmt.where(Component.type == component_type)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_component(db: Session, component_id: int) -> Component | None:
    return db.get(Component, component_id)


def create_component(db: Session, node_id: int, comp_in: ComponentCreate) -> Component:
    node = get_node(db, node_id)
    if not node:
        raise ValueError("Node not found")
    component = Component(
        node_id=node_id,
        name=comp_in.name,
        type=comp_in.type,
        metric=comp_in.metric,
    )
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


def update_component(
    db: Session, component: Component, comp_in: ComponentUpdate
) -> Component:
    if comp_in.name is not None:
        component.name = comp_in.name
    if comp_in.status is not None:
        component.status = comp_in.status
    if comp_in.metric is not None:
        component.metric = comp_in.metric
    db.commit()
    db.refresh(component)
    return component


def control_component(
    db: Session,
    component: Component,
    action: ComponentStatus,
    operator_id: int | None,
    message: str | None = None,
) -> Component:
    component.status = action
    log = DeviceOperationLog(
        node_id=component.node_id,
        component_id=component.id,
        operator_id=operator_id,
        action=action,
        message=message,
    )
    operation = OperationLog(
        user_id=operator_id,
        action="component_control",
        entity_type="component",
        entity_id=str(component.id),
        detail=message,
    )
    db.add(log)
    db.add(operation)
    db.commit()
    db.refresh(component)
    from app.core.mqtt_client import publish_component_control

    if not publish_component_control(
        component.node_id, component.id, action.value, message or "",
        component_type=component.type.value,
    ):
        logger.warning(
            "Component %s status updated to '%s' in DB, but MQTT control command was NOT delivered "
            "(broker disconnected) — device may not reflect the new state until reconnected",
            component.id, action.value,
        )
    # WebSocket 实时广播组件状态变更（与 rule_service 保持一致）
    from app.core.websocket_manager import ws_manager
    ws_manager.broadcast_sync("component_status", {
        "component_id": component.id,
        "node_id": component.node_id,
        "type": component.type.value,
        "status": component.status.value,
        "triggered_by_rule": None,  # 手动控制，非规则触发
    }, node_id=component.node_id)
    return component

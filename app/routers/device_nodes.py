from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.enums import ComponentType, UserRole
from app.schemas.component import (
    ComponentControlRequest,
    ComponentCreate,
    ComponentOut,
    ComponentUpdate,
)
from app.schemas.device_log import DeviceOperationLogOut
from app.schemas.device_node import DeviceNodeCreate, DeviceNodeOut, DeviceNodeUpdate
from app.services import device_node_service, log_service

router = APIRouter(prefix="/device-nodes", tags=["device-nodes"])


@router.get("", response_model=list[DeviceNodeOut])
def list_nodes(
    online: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[DeviceNodeOut]:
    return device_node_service.list_nodes(db, online=online, skip=skip, limit=limit)


@router.post("", response_model=DeviceNodeOut, status_code=status.HTTP_201_CREATED)
def create_node(
    payload: DeviceNodeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> DeviceNodeOut:
    try:
        node = device_node_service.create_node(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_node",
        entity_type="device_node",
        entity_id=str(node.id),
        detail=f"Created node {node.name}",
    )
    return node


@router.get("/{node_id}", response_model=DeviceNodeOut)
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DeviceNodeOut:
    node = device_node_service.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


@router.patch("/{node_id}", response_model=DeviceNodeOut)
def update_node(
    node_id: int,
    payload: DeviceNodeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> DeviceNodeOut:
    node = device_node_service.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    try:
        node = device_node_service.update_node(db, node, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_node",
        entity_type="device_node",
        entity_id=str(node.id),
        detail="Updated node metadata",
    )
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> None:
    node = device_node_service.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_node",
        entity_type="device_node",
        entity_id=str(node.id),
        detail=f"Deleted node {node.name}",
    )
    device_node_service.delete_node(db, node)


# ── Component endpoints ─────────────────────────────────


@router.get("/{node_id}/components", response_model=list[ComponentOut])
def list_components(
    node_id: int,
    component_type: ComponentType | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ComponentOut]:
    node = device_node_service.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return device_node_service.list_components(
        db, node_id=node_id, component_type=component_type, skip=skip, limit=limit
    )


@router.post("/{node_id}/components", response_model=ComponentOut, status_code=status.HTTP_201_CREATED)
def create_component(
    node_id: int,
    payload: ComponentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ComponentOut:
    try:
        comp = device_node_service.create_component(db, node_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_component",
        entity_type="component",
        entity_id=str(comp.id),
        detail=f"Created component {comp.name}",
    )
    return comp


@router.patch("/{node_id}/components/{component_id}", response_model=ComponentOut)
def update_component(
    node_id: int,
    component_id: int,
    payload: ComponentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ComponentOut:
    comp = device_node_service.get_component(db, component_id)
    if not comp or comp.node_id != node_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    return device_node_service.update_component(db, comp, payload)


@router.post("/{node_id}/components/{component_id}/control", response_model=ComponentOut)
def control_component(
    node_id: int,
    component_id: int,
    payload: ComponentControlRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher, UserRole.operator)),
) -> ComponentOut:
    comp = device_node_service.get_component(db, component_id)
    if not comp or comp.node_id != node_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    return device_node_service.control_component(
        db,
        comp,
        action=payload.action,
        operator_id=current_user.id,
        message=payload.message,
    )


@router.get("/{node_id}/logs", response_model=list[DeviceOperationLogOut])
def get_node_logs(
    node_id: int,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[DeviceOperationLogOut]:
    node = device_node_service.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return log_service.list_device_logs(db, node_id=node_id, skip=skip, limit=limit)

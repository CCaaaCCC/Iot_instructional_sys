from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.group import (
    BatchStudentCreate,
    GroupCreate,
    GroupOut,
    GroupUpdate,
)
from app.schemas.user import UserOut
from app.services import group_service, log_service

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupOut])
def list_groups(
    class_id: int | None = None,
    node_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[GroupOut]:
    return group_service.list_groups(
        db, class_id=class_id, node_id=node_id, skip=skip, limit=limit
    )


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> GroupOut:
    group = group_service.create_group(db, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_group",
        entity_type="group",
        entity_id=str(group.id),
        detail=f"Created group {group.name}",
    )
    return group


@router.get("/{group_id}", response_model=GroupOut)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> GroupOut:
    group = group_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> GroupOut:
    group = group_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group = group_service.update_group(db, group, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_group",
        entity_type="group",
        entity_id=str(group.id),
        detail=f"Updated group {group.name}",
    )
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    group = group_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    name = group.name
    group_service.delete_group(db, group)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_group",
        entity_type="group",
        entity_id=str(group_id),
        detail=f"Deleted group {name}",
    )


@router.post("/{group_id}/bind-node", response_model=GroupOut)
def bind_node(
    group_id: int,
    node_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> GroupOut:
    group = group_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    try:
        group = group_service.bind_node(db, group, node_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="bind_node",
        entity_type="group",
        entity_id=str(group.id),
        detail=f"Bound group {group.name} to node {node_id}",
    )
    return group


@router.post("/{group_id}/unbind-node", response_model=GroupOut)
def unbind_node(
    group_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> GroupOut:
    group = group_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group = group_service.unbind_node(db, group)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="unbind_node",
        entity_type="group",
        entity_id=str(group.id),
        detail=f"Unbound node from group {group.name}",
    )
    return group


@router.get("/{group_id}/students", response_model=list[UserOut])
def list_students(
    group_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher, UserRole.student)),
) -> list[UserOut]:
    group = group_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group_service.list_students(db, group_id)


@router.post(
    "/{group_id}/students/batch",
    response_model=list[UserOut],
    status_code=status.HTTP_201_CREATED,
)
def batch_create_students(
    group_id: int,
    payload: BatchStudentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[UserOut]:
    if payload.group_id != group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_id in body must match path parameter",
        )
    try:
        students = group_service.batch_create_students(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="batch_create_students",
        entity_type="group",
        entity_id=str(group_id),
        detail=f"Created {len(students)} students in group {group_id}",
    )
    return students

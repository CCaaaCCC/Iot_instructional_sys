from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.class_task import TaskCreate, TaskOut, TaskUpdate
from app.services import log_service, task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    group_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[TaskOut]:
    return task_service.list_tasks(db, group_id=group_id, skip=skip, limit=limit)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TaskOut:
    task = task_service.create_task(db, payload, created_by=current_user.id)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_task",
        entity_type="task",
        entity_id=str(task.id),
        detail=f"Created task {task.title}",
    )
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TaskOut:
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TaskOut:
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task = task_service.update_task(db, task, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_task",
        entity_type="task",
        entity_id=str(task.id),
        detail=f"Updated task {task.title}",
    )
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task_service.delete_task(db, task)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_task",
        entity_type="task",
        entity_id=str(task_id),
        detail=f"Deleted task {task.title}",
    )

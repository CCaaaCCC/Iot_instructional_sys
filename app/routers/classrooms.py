from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.classroom import ClassroomCreate, ClassroomOut, ClassroomUpdate
from app.services import classroom_service, log_service

router = APIRouter(prefix="/classrooms", tags=["classrooms"])


@router.get("", response_model=list[ClassroomOut])
def list_classrooms(
    teacher_id: int | None = None,
    subject: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[ClassroomOut]:
    return classroom_service.list_classrooms(
        db, teacher_id=teacher_id, subject=subject, skip=skip, limit=limit
    )


@router.post("", response_model=ClassroomOut, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ClassroomOut:
    create_data = payload.model_copy()
    if create_data.teacher_id is None and current_user.role == UserRole.teacher:
        create_data.teacher_id = current_user.id
    classroom = classroom_service.create_classroom(db, create_data)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_classroom",
        entity_type="classroom",
        entity_id=str(classroom.id),
        detail=f"Created classroom {classroom.name}",
    )
    return classroom


@router.get("/{classroom_id}", response_model=ClassroomOut)
def get_classroom(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ClassroomOut:
    classroom = classroom_service.get_classroom(db, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    return classroom


@router.patch("/{classroom_id}", response_model=ClassroomOut)
def update_classroom(
    classroom_id: int,
    payload: ClassroomUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ClassroomOut:
    classroom = classroom_service.get_classroom(db, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    classroom = classroom_service.update_classroom(db, classroom, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_classroom",
        entity_type="classroom",
        entity_id=str(classroom.id),
        detail=f"Updated classroom {classroom.name}",
    )
    return classroom


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    classroom = classroom_service.get_classroom(db, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    name = classroom.name
    classroom_service.delete_classroom(db, classroom)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_classroom",
        entity_type="classroom",
        entity_id=str(classroom_id),
        detail=f"Deleted classroom {name}",
    )

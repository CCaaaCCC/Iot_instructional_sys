from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import log_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> list[UserOut]:
    return user_service.list_users(db, skip=skip, limit=limit)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> UserOut:
    try:
        user = user_service.create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_user",
        entity_type="user",
        entity_id=str(user.id),
        detail=f"Created user {user.username}",
    )
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> UserOut:
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        user = user_service.update_user(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_user",
        entity_type="user",
        entity_id=str(user.id),
        detail=f"Updated user {user.username}",
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> None:
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    user_service.delete_user(db, user)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_user",
        entity_type="user",
        entity_id=str(user_id),
        detail=f"Deleted user {user.username}",
    )

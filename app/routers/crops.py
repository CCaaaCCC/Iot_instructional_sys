from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.crop import CropCreate, CropOut, CropUpdate
from app.services import crop_service, log_service

router = APIRouter(prefix="/crops", tags=["crops"])


@router.get("", response_model=list[CropOut])
def list_crops(
    group_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[CropOut]:
    return crop_service.list_crops(db, group_id=group_id, skip=skip, limit=limit)


@router.post("", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def create_crop(
    payload: CropCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CropOut:
    try:
        crop = crop_service.create_crop(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_crop",
        entity_type="crop",
        entity_id=str(crop.id),
        detail=f"Created crop {crop.name}",
    )
    return crop


@router.get("/{crop_id}", response_model=CropOut)
def get_crop(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CropOut:
    crop = crop_service.get_crop(db, crop_id)
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    return crop


@router.patch("/{crop_id}", response_model=CropOut)
def update_crop(
    crop_id: int,
    payload: CropUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CropOut:
    crop = crop_service.get_crop(db, crop_id)
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    try:
        crop = crop_service.update_crop(db, crop, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_crop",
        entity_type="crop",
        entity_id=str(crop.id),
        detail=f"Updated crop {crop.name}",
    )
    return crop


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    crop = crop_service.get_crop(db, crop_id)
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    crop_service.delete_crop(db, crop)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_crop",
        entity_type="crop",
        entity_id=str(crop_id),
        detail=f"Deleted crop {crop.name}",
    )

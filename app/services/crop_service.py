from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop import Crop
from app.schemas.crop import CropCreate, CropUpdate


def list_crops(
    db: Session,
    group_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[Crop]:
    stmt = select(Crop).order_by(Crop.created_at.desc())
    if group_id is not None:
        stmt = stmt.where(Crop.group_id == group_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_crop(db: Session, crop_id: int) -> Crop | None:
    return db.get(Crop, crop_id)


def create_crop(db: Session, crop_in: CropCreate) -> Crop:
    existing = db.execute(select(Crop).where(Crop.name == crop_in.name)).scalar_one_or_none()
    if existing:
        raise ValueError("Crop name already exists")
    crop = Crop(
        name=crop_in.name,
        description=crop_in.description,
        growth_stage=crop_in.growth_stage,
        start_date=crop_in.start_date,
        end_date=crop_in.end_date,
        notes=crop_in.notes,
        group_id=crop_in.group_id,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


def update_crop(db: Session, crop: Crop, crop_in: CropUpdate) -> Crop:
    update_data = crop_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != crop.name:
        existing = db.execute(select(Crop).where(Crop.name == update_data["name"])).scalar_one_or_none()
        if existing:
            raise ValueError("Crop name already exists")
    for field in ("name", "description", "growth_stage", "start_date",
                  "end_date", "notes", "group_id"):
        if field in update_data:
            setattr(crop, field, update_data[field])
    db.commit()
    db.refresh(crop)
    return crop


def delete_crop(db: Session, crop: Crop) -> None:
    db.delete(crop)
    db.commit()

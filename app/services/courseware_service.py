import os

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.courseware import Courseware
from app.schemas.courseware import CoursewareCreate, CoursewareUpdate


def list_my_courseware(
    db: Session,
    owner_id: int,
    file_type: str | None = None,
    subject: str | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[Courseware]:
    stmt = (
        select(Courseware)
        .where(Courseware.owner_id == owner_id)
        .order_by(Courseware.created_at.desc())
    )
    if file_type:
        stmt = stmt.where(Courseware.file_type == file_type)
    if subject:
        stmt = stmt.where(Courseware.subject == subject)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def list_public_courseware(
    db: Session,
    file_type: str | None = None,
    subject: str | None = None,
    grade_level: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[Courseware]:
    stmt = (
        select(Courseware)
        .where(Courseware.is_public.is_(True))
        .order_by(Courseware.created_at.desc())
    )
    if file_type:
        stmt = stmt.where(Courseware.file_type == file_type)
    if subject:
        stmt = stmt.where(Courseware.subject == subject)
    if grade_level:
        stmt = stmt.where(Courseware.grade_level == grade_level)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Courseware.title.ilike(pattern),
                Courseware.description.ilike(pattern),
                Courseware.tags.ilike(pattern),
            )
        )
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_courseware(db: Session, courseware_id: int) -> Courseware | None:
    return db.get(Courseware, courseware_id)


def create_courseware(
    db: Session,
    owner_id: int,
    payload: CoursewareCreate,
    file_url: str,
    file_size: int | None,
    preview_url: str | None = None,
) -> Courseware:
    courseware = Courseware(
        title=payload.title,
        description=payload.description,
        file_type=payload.file_type,
        file_url=file_url,
        preview_url=preview_url,
        file_size=file_size,
        subject=payload.subject,
        grade_level=payload.grade_level,
        tags=payload.tags,
        is_public=payload.is_public,
        owner_id=owner_id,
    )
    db.add(courseware)
    db.commit()
    db.refresh(courseware)
    return courseware


def update_courseware(
    db: Session, courseware: Courseware, payload: CoursewareUpdate
) -> Courseware:
    update_data = payload.model_dump(exclude_unset=True)
    for field in (
        "title", "description", "subject", "grade_level", "tags", "is_public",
    ):
        if field in update_data:
            setattr(courseware, field, update_data[field])
    db.commit()
    db.refresh(courseware)
    return courseware


def delete_courseware(db: Session, courseware: Courseware) -> None:
    file_path = _file_path_from_url(courseware.file_url)
    preview_path = _file_path_from_url(courseware.preview_url) if courseware.preview_url else None
    db.delete(courseware)
    db.commit()
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    if preview_path and os.path.isfile(preview_path):
        try:
            os.remove(preview_path)
        except OSError:
            pass


def _file_path_from_url(file_url: str) -> str | None:
    if not file_url:
        return None
    filename = file_url.rsplit("/", 1)[-1] if "/" in file_url else file_url
    return os.path.join("data", "courseware", filename)

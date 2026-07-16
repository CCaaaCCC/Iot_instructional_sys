import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.teaching_resource import TeachingResource
from app.models.user import User
from app.schemas.teaching_resource import TeachingResourceCreate, TeachingResourceUpdate


def list_resources(
    db: Session,
    publisher_id: int | None = None,
    classroom_id: int | None = None,
    group_id: int | None = None,
    subject: str | None = None,
    resource_type: str | None = None,
    published_only: bool = False,
    skip: int = 0,
    limit: int = 200,
) -> list[TeachingResource]:
    stmt = select(TeachingResource).order_by(TeachingResource.created_at.desc())
    if publisher_id is not None:
        stmt = stmt.where(TeachingResource.publisher_id == publisher_id)
    if classroom_id is not None:
        stmt = stmt.where(TeachingResource.classroom_id == classroom_id)
    if group_id is not None:
        stmt = stmt.where(TeachingResource.group_id == group_id)
    if subject:
        stmt = stmt.where(TeachingResource.subject == subject)
    if resource_type:
        stmt = stmt.where(TeachingResource.resource_type == resource_type)
    if published_only:
        stmt = stmt.where(TeachingResource.is_published.is_(True))
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_resource(db: Session, resource_id: int) -> TeachingResource | None:
    return db.get(TeachingResource, resource_id)


def create_resource(
    db: Session,
    publisher_id: int,
    payload: TeachingResourceCreate,
    file_url: str,
    file_size: int | None,
    preview_url: str | None = None,
) -> TeachingResource:
    resource = TeachingResource(
        title=payload.title,
        description=payload.description,
        resource_type=payload.resource_type,
        file_url=file_url,
        preview_url=preview_url,
        file_size=file_size,
        subject=payload.subject,
        classroom_id=payload.classroom_id,
        group_id=payload.group_id,
        task_id=payload.task_id,
        is_published=payload.is_published,
        publisher_id=publisher_id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def update_resource(
    db: Session, resource: TeachingResource, payload: TeachingResourceUpdate
) -> TeachingResource:
    update_data = payload.model_dump(exclude_unset=True)
    for field in (
        "title", "description", "resource_type", "subject",
        "classroom_id", "group_id", "task_id", "is_published",
    ):
        if field in update_data:
            setattr(resource, field, update_data[field])
    db.commit()
    db.refresh(resource)
    return resource


def delete_resource(db: Session, resource: TeachingResource) -> None:
    file_path = _file_path_from_url(resource.file_url)
    preview_path = _file_path_from_url(resource.preview_url) if resource.preview_url else None
    db.delete(resource)
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


def increment_download(db: Session, resource: TeachingResource) -> None:
    resource.download_count += 1
    db.commit()


def list_resources_for_student(
    db: Session, student: User
) -> list[TeachingResource]:
    if student.group_id is None:
        return []
    group = db.get(Group, student.group_id)
    if not group:
        return []
    stmt = select(TeachingResource).where(
        TeachingResource.is_published.is_(True),
    ).where(
        (TeachingResource.group_id == student.group_id)
        | (TeachingResource.classroom_id == group.class_id)
        | (
            (TeachingResource.group_id.is_(None))
            & (TeachingResource.classroom_id.is_(None))
        ),
    ).order_by(TeachingResource.created_at.desc())
    return db.execute(stmt).scalars().all()


def _file_path_from_url(file_url: str) -> str | None:
    if not file_url:
        return None
    filename = file_url.rsplit("/", 1)[-1] if "/" in file_url else file_url
    return os.path.join("data", "resources", filename)

import os
import secrets
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.teaching_resource import (
    TeachingResourceCreate,
    TeachingResourceOut,
    TeachingResourceUpdate,
)
from app.services import log_service, teaching_resource_service
from app.services import preview_service

router = APIRouter(prefix="/resources", tags=["teaching-resources"])

RESOURCE_DIR = "data/resources"
ALLOWED_RESOURCE_TYPES = {
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "video/mp4",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_RESOURCE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.get("", response_model=list[TeachingResourceOut])
def list_resources(
    classroom_id: int | None = None,
    group_id: int | None = None,
    subject: str | None = None,
    resource_type: str | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[TeachingResourceOut]:
    return teaching_resource_service.list_resources(
        db,
        classroom_id=classroom_id,
        group_id=group_id,
        subject=subject,
        resource_type=resource_type,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=TeachingResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(
    title: str = Form(...),
    description: str | None = Form(None),
    resource_type: str = Form(...),
    subject: str = Form(...),
    classroom_id: int | None = Form(None),
    group_id: int | None = Form(None),
    task_id: int | None = Form(None),
    is_published: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TeachingResourceOut:
    if file.content_type not in ALLOWED_RESOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: pdf, ppt, pptx, mp4, doc, docx, txt",
        )
    content = file.file.read(MAX_RESOURCE_BYTES + 1)
    if len(content) > MAX_RESOURCE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds 50MB limit",
        )
    ext_map = {
        "application/pdf": "pdf",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "video/mp4": "mp4",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
    }
    ext = ext_map.get(file.content_type or "", "bin")
    os.makedirs(RESOURCE_DIR, exist_ok=True)
    filename = f"{current_user.id}_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(RESOURCE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    file_url = f"/resource-files/{filename}"

    # 生成 PDF 预览（Office 文件）
    preview_url = None
    base_name = filename.rsplit(".", 1)[0]
    if preview_service.is_convertible(filename):
        preview_name = f"preview_{base_name}"
        pdf_filename = preview_service.convert_to_pdf(filepath, RESOURCE_DIR, preview_name)
        if pdf_filename:
            preview_url = f"/resource-files/{pdf_filename}"

    payload = TeachingResourceCreate(
        title=title,
        description=description,
        resource_type=resource_type,
        subject=subject,
        classroom_id=classroom_id,
        group_id=group_id,
        task_id=task_id,
        is_published=is_published,
    )
    resource = teaching_resource_service.create_resource(
        db, current_user.id, payload, file_url, len(content), preview_url=preview_url,
    )
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_resource",
        entity_type="teaching_resource",
        entity_id=str(resource.id),
        detail=f"Created teaching resource {resource.title}",
    )
    return resource


@router.get("/{resource_id}", response_model=TeachingResourceOut)
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TeachingResourceOut:
    resource = teaching_resource_service.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    return resource


@router.patch("/{resource_id}", response_model=TeachingResourceOut)
def update_resource(
    resource_id: int,
    payload: TeachingResourceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TeachingResourceOut:
    resource = teaching_resource_service.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    if resource.publisher_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the publisher or admin can modify this resource",
        )
    resource = teaching_resource_service.update_resource(db, resource, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_resource",
        entity_type="teaching_resource",
        entity_id=str(resource.id),
        detail=f"Updated teaching resource {resource.title}",
    )
    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    resource = teaching_resource_service.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    if resource.publisher_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the publisher or admin can delete this resource",
        )
    teaching_resource_service.delete_resource(db, resource)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_resource",
        entity_type="teaching_resource",
        entity_id=str(resource_id),
        detail=f"Deleted teaching resource {resource.title}",
    )


@router.patch("/{resource_id}/publish", response_model=TeachingResourceOut)
def toggle_publish(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TeachingResourceOut:
    resource = teaching_resource_service.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    if resource.publisher_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the publisher or admin can toggle this resource's publish state",
        )
    from app.schemas.teaching_resource import TeachingResourceUpdate
    resource = teaching_resource_service.update_resource(
        db, resource, TeachingResourceUpdate(is_published=not resource.is_published)
    )
    return resource

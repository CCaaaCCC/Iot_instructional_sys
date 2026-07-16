import os
import secrets
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.courseware import (
    CoursewareCreate,
    CoursewareListOut,
    CoursewareOut,
    CoursewareUpdate,
)
from app.services import courseware_service, log_service
from app.services import preview_service

router = APIRouter(prefix="/courseware", tags=["courseware"])

COURSEWARE_DIR = "data/courseware"
ALLOWED_COURSEWARE_TYPES = {
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "video/mp4",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_COURSEWARE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.get("/my", response_model=list[CoursewareOut])
def list_my_courseware(
    file_type: str | None = None,
    subject: str | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[CoursewareOut]:
    return courseware_service.list_my_courseware(
        db,
        owner_id=current_user.id,
        file_type=file_type,
        subject=subject,
        skip=skip,
        limit=limit,
    )


@router.get("/public", response_model=list[CoursewareListOut])
def list_public_courseware(
    file_type: str | None = None,
    subject: str | None = None,
    grade_level: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[CoursewareListOut]:
    rows = courseware_service.list_public_courseware(
        db,
        file_type=file_type,
        subject=subject,
        grade_level=grade_level,
        search=search,
        skip=skip,
        limit=limit,
    )
    result: list[CoursewareListOut] = []
    for r in rows:
        owner_name = r.owner.display_name or r.owner.username if r.owner else None
        result.append(
            CoursewareListOut(
                id=r.id,
                title=r.title,
                description=r.description,
                file_type=r.file_type,
                file_url=r.file_url,
                file_size=r.file_size,
                subject=r.subject,
                grade_level=r.grade_level,
                tags=r.tags,
                is_public=r.is_public,
                owner_id=r.owner_id,
                owner_name=owner_name,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return result


@router.post("", response_model=CoursewareOut, status_code=status.HTTP_201_CREATED)
def create_courseware(
    title: str = Form(...),
    description: str | None = Form(None),
    file_type: str = Form(...),
    subject: str = Form(...),
    grade_level: str | None = Form(None),
    tags: str | None = Form(None),
    is_public: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CoursewareOut:
    if file.content_type not in ALLOWED_COURSEWARE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: pdf, ppt, pptx, mp4, doc, docx, txt",
        )
    content = file.file.read(MAX_COURSEWARE_BYTES + 1)
    if len(content) > MAX_COURSEWARE_BYTES:
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
    os.makedirs(COURSEWARE_DIR, exist_ok=True)
    filename = f"{current_user.id}_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(COURSEWARE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    file_url = f"/courseware-files/{filename}"

    # 生成 PDF 预览（Office 文件）
    preview_url = None
    base_name = filename.rsplit(".", 1)[0]
    if preview_service.is_convertible(filename):
        preview_name = f"preview_{base_name}"
        pdf_filename = preview_service.convert_to_pdf(filepath, COURSEWARE_DIR, preview_name)
        if pdf_filename:
            preview_url = f"/courseware-files/{pdf_filename}"

    payload = CoursewareCreate(
        title=title,
        description=description,
        file_type=file_type,
        subject=subject,
        grade_level=grade_level,
        tags=tags,
        is_public=is_public,
    )
    courseware = courseware_service.create_courseware(
        db, current_user.id, payload, file_url, len(content), preview_url=preview_url,
    )
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_courseware",
        entity_type="courseware",
        entity_id=str(courseware.id),
        detail=f"Created courseware {courseware.title}",
    )
    return courseware


@router.get("/{courseware_id}", response_model=CoursewareListOut)
def get_courseware(
    courseware_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CoursewareListOut:
    cw = courseware_service.get_courseware(db, courseware_id)
    if not cw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Courseware not found"
        )
    owner_name = cw.owner.display_name or cw.owner.username if cw.owner else None
    return CoursewareListOut(
        id=cw.id,
        title=cw.title,
        description=cw.description,
        file_type=cw.file_type,
        file_url=cw.file_url,
        file_size=cw.file_size,
        subject=cw.subject,
        grade_level=cw.grade_level,
        tags=cw.tags,
        is_public=cw.is_public,
        owner_id=cw.owner_id,
        owner_name=owner_name,
        created_at=cw.created_at,
        updated_at=cw.updated_at,
    )


@router.patch("/{courseware_id}", response_model=CoursewareOut)
def update_courseware(
    courseware_id: int,
    payload: CoursewareUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CoursewareOut:
    cw = courseware_service.get_courseware(db, courseware_id)
    if not cw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Courseware not found"
        )
    if cw.owner_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or admin can modify this courseware",
        )
    cw = courseware_service.update_courseware(db, cw, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_courseware",
        entity_type="courseware",
        entity_id=str(cw.id),
        detail=f"Updated courseware {cw.title}",
    )
    return cw


@router.delete("/{courseware_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_courseware(
    courseware_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    cw = courseware_service.get_courseware(db, courseware_id)
    if not cw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Courseware not found"
        )
    if cw.owner_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or admin can delete this courseware",
        )
    courseware_service.delete_courseware(db, cw)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_courseware",
        entity_type="courseware",
        entity_id=str(courseware_id),
        detail=f"Deleted courseware {cw.title}",
    )


@router.patch("/{courseware_id}/toggle-public", response_model=CoursewareOut)
def toggle_public(
    courseware_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> CoursewareOut:
    cw = courseware_service.get_courseware(db, courseware_id)
    if not cw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Courseware not found"
        )
    if cw.owner_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or admin can toggle this courseware's visibility",
        )
    cw = courseware_service.update_courseware(
        db, cw, CoursewareUpdate(is_public=not cw.is_public)
    )
    return cw

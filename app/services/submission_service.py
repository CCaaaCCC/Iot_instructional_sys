import os
import time
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.submission_file import SubmissionFile
from app.models.task_submission import TaskSubmission
from app.schemas.task_submission import SubmissionReview

SUBMISSION_DIR = "data/submissions"
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_FILES_PER_SUBMISSION = 10

ALLOWED_SUBMISSION_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "video/mp4",
}


def _save_upload_files(
    db: Session, submission_id: int, files: list[UploadFile]
) -> list[SubmissionFile]:
    os.makedirs(SUBMISSION_DIR, exist_ok=True)
    saved: list[SubmissionFile] = []
    ts = int(time.time())
    for idx, file in enumerate(files):
        if file.content_type not in ALLOWED_SUBMISSION_TYPES:
            raise ValueError(
                f"Unsupported file type: {file.content_type or 'unknown'}. "
                f"Allowed: images, pdf, ppt, pptx, doc, docx, txt, mp4"
            )
        content = file.file.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise ValueError(
                f"File '{file.filename}' exceeds 20MB limit ({len(content)} bytes)"
            )
        original_name = file.filename or "untitled"
        safe_name = f"{submission_id}_{ts}_{idx}_{original_name}"
        filepath = os.path.join(SUBMISSION_DIR, safe_name)
        with open(filepath, "wb") as f:
            f.write(content)
        file_url = f"/submission-files/{safe_name}"
        sf = SubmissionFile(
            submission_id=submission_id,
            filename=safe_name,
            original_name=original_name,
            file_url=file_url,
            file_size=len(content),
            file_type=file.content_type or "application/octet-stream",
        )
        db.add(sf)
        saved.append(sf)
    if saved:
        db.commit()
        for sf in saved:
            db.refresh(sf)
    return saved


def _delete_submission_files(db: Session, submission_id: int) -> None:
    stmt = select(SubmissionFile).where(
        SubmissionFile.submission_id == submission_id
    )
    existing = db.execute(stmt).scalars().all()
    for sf in existing:
        file_path = os.path.join(SUBMISSION_DIR, sf.filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        db.delete(sf)
    if existing:
        db.commit()


def list_submissions(
    db: Session,
    task_id: int | None = None,
    student_id: int | None = None,
    reviewed: bool | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[TaskSubmission]:
    stmt = select(TaskSubmission).order_by(TaskSubmission.submitted_at.desc())
    if task_id is not None:
        stmt = stmt.where(TaskSubmission.task_id == task_id)
    if student_id is not None:
        stmt = stmt.where(TaskSubmission.student_id == student_id)
    if reviewed is not None:
        if reviewed:
            stmt = stmt.where(TaskSubmission.reviewed_at.isnot(None))
        else:
            stmt = stmt.where(TaskSubmission.reviewed_at.is_(None))
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_submission(db: Session, submission_id: int) -> TaskSubmission | None:
    return db.get(TaskSubmission, submission_id)


def get_student_submission_for_task(
    db: Session, task_id: int, student_id: int
) -> TaskSubmission | None:
    stmt = select(TaskSubmission).where(
        TaskSubmission.task_id == task_id,
        TaskSubmission.student_id == student_id,
    )
    return db.execute(stmt).scalars().first()


def create_submission(
    db: Session,
    task_id: int,
    student_id: int,
    content: str | None = None,
    files: list[UploadFile] | None = None,
) -> TaskSubmission:
    if not content and (not files or len(files) == 0):
        raise ValueError("Must provide content or at least one file")

    if files and len(files) > MAX_FILES_PER_SUBMISSION:
        raise ValueError(
            f"Maximum {MAX_FILES_PER_SUBMISSION} files allowed per submission"
        )

    existing = get_student_submission_for_task(db, task_id, student_id)
    if existing:
        existing.content = content
        existing.submitted_at = datetime.now()
        existing.score = None
        existing.feedback = None
        existing.reviewed_at = None
        existing.reviewed_by = None
        if files:
            _delete_submission_files(db, existing.id)
            _save_upload_files(db, existing.id, files)
        db.commit()
        db.refresh(existing)
        return existing

    submission = TaskSubmission(
        task_id=task_id,
        student_id=student_id,
        content=content,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    if files:
        _save_upload_files(db, submission.id, files)
        db.refresh(submission)
    return submission


def review_submission(
    db: Session,
    submission: TaskSubmission,
    payload: SubmissionReview,
    reviewer_id: int,
) -> TaskSubmission:
    submission.score = payload.score
    submission.feedback = payload.feedback
    submission.reviewed_at = datetime.now()
    submission.reviewed_by = reviewer_id
    db.commit()
    db.refresh(submission)
    _notify_student_reviewed(db, submission)
    return submission


def _notify_student_reviewed(db: Session, submission: TaskSubmission) -> None:
    """作业批阅后通知学生。"""
    try:
        from app.services import notification_service
        from app.core.websocket_manager import ws_manager
        task_title = submission.task.title if submission.task else "作业"
        feedback_preview = (submission.feedback[:40] + "...") if submission.feedback and len(submission.feedback) > 40 else (submission.feedback or "无评语")
        title = "作业已批阅"
        content = f"你的作业「{task_title}」已批阅，得分 {submission.score} 分。评语：{feedback_preview}"
        link = "/student/submissions"
        n = notification_service.create_notification(
            db, submission.student_id, "reviewed", title, content, link
        )
        db.commit()
        ws_manager.send_to_user_sync("notification", {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "link": n.link,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }, user_id=submission.student_id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to notify student for reviewed submission %s", submission.id)

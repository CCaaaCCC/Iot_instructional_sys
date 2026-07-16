from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.task_submission import (
    SubmissionReview,
    TaskSubmissionOut,
)
from app.services import log_service, submission_service, task_service

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("", response_model=list[TaskSubmissionOut])
def list_submissions(
    task_id: int | None = None,
    student_id: int | None = None,
    reviewed: bool | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[TaskSubmissionOut]:
    return submission_service.list_submissions(
        db,
        task_id=task_id,
        student_id=student_id,
        reviewed=reviewed,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=TaskSubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_task(
    task_id: int,
    content: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.student)),
) -> TaskSubmissionOut:
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.group_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is not assigned to any group",
        )
    if task.group_id is not None and task.group_id != current_user.group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task does not belong to your group",
        )
    try:
        submission = submission_service.create_submission(
            db,
            task_id=task_id,
            student_id=current_user.id,
            content=content,
            files=files if files else None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return submission


@router.get("/{submission_id}", response_model=TaskSubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskSubmissionOut:
    submission = submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    if current_user.role == UserRole.student and submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other students' submissions",
        )
    return submission


@router.post("/{submission_id}/review", response_model=TaskSubmissionOut)
def review_submission(
    submission_id: int,
    payload: SubmissionReview,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> TaskSubmissionOut:
    submission = submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    submission = submission_service.review_submission(
        db, submission, payload, reviewer_id=current_user.id
    )
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="review_submission",
        entity_type="submission",
        entity_id=str(submission.id),
        detail=f"Reviewed submission {submission.id} with score {payload.score}",
    )
    return submission

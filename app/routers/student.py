from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
import os
import secrets
import time

from app.core.dependencies import get_current_user, get_db
from app.models.enums import SensorMetric, UserRole
from app.models.user import User
from app.schemas.class_task import TaskOut
from app.schemas.experiment import ExperimentGroupOut, ExperimentObservationCreate, ExperimentObservationOut, ExperimentOut
from app.schemas.group import GroupOut
from app.schemas.sensor_data import EChartsResponse, SensorDataOut
from app.schemas.student_analytics import StudentAnalyticsSummary
from app.schemas.task_submission import TaskSubmissionOut
from app.schemas.teaching_resource import TeachingResourceOut
from app.schemas.pest_diagnosis import PestDiagnosisListOut
from app.schemas.user import StudentPasswordChange, StudentProfileUpdate, UserOut
from app.services import (
    experiment_service,
    pest_diagnosis_service,
    student_analytics_service,
    student_service,
    submission_service,
    task_service,
    teaching_resource_service,
)

router = APIRouter(prefix="/student", tags=["student"])

AVATAR_DIR = "data/avatars"
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


@router.get("/me/group", response_model=GroupOut | None)
def my_group(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupOut | None:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    group = student_service.get_student_group(db, current_user)
    return group


@router.get("/me/tasks", response_model=list[TaskOut])
def my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskOut]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.list_tasks_for_student(db, current_user)


@router.get("/me/submissions", response_model=list[TaskSubmissionOut])
def my_submissions(
    task_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskSubmissionOut]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.list_submissions_for_student(db, current_user, task_id=task_id)


@router.get("/me/sensor-data", response_model=list[SensorDataOut])
def my_sensor_data(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SensorDataOut]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.list_sensor_data_for_student(db, current_user, limit=limit)


@router.get("/me/sensor-data/latest", response_model=SensorDataOut | None)
def my_latest_sensor_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SensorDataOut | None:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.latest_sensor_data_for_student(db, current_user)


@router.post(
    "/me/tasks/{task_id}/submit",
    response_model=TaskSubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_my_task(
    task_id: int,
    content: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskSubmissionOut:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
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
        return submission_service.create_submission(
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


@router.get("/me/sensor-data/echarts", response_model=EChartsResponse)
def my_echarts_data(
    metrics: list[SensorMetric] | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EChartsResponse:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.echarts_data_for_student(db, current_user, metrics=metrics, limit=limit)


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile(
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.update_student_profile(db, current_user, payload)


@router.patch("/me/password", response_model=UserOut)
def change_my_password(
    payload: StudentPasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    try:
        return student_service.change_student_password(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/me/avatar")
def upload_my_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
) -> dict[str, str]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: jpg, png, webp",
        )
    content = file.file.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file exceeds 2MB limit",
        )
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type or "", "jpg")
    os.makedirs(AVATAR_DIR, exist_ok=True)
    # 删除旧头像文件，避免磁盘堆积
    if current_user.avatar_url and current_user.avatar_url.startswith("/avatars/"):
        old_name = current_user.avatar_url.rsplit("/", 1)[-1]
        old_path = os.path.join(AVATAR_DIR, old_name)
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
    filename = f"{current_user.id}_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    avatar_url = f"/avatars/{filename}"
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)
    return {"avatar_url": avatar_url}


@router.get("/me/analytics", response_model=StudentAnalyticsSummary | None)
def my_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAnalyticsSummary | None:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_analytics_service.get_analytics_summary_for_student(
        db, current_user.id
    )


@router.get("/me/resources", response_model=list[TeachingResourceOut])
def my_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TeachingResourceOut]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return teaching_resource_service.list_resources_for_student(db, current_user)


@router.get("/me/experiments", response_model=list[ExperimentOut])
def my_experiments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentOut]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.list_experiments_for_student(db, current_user)


@router.get("/me/experiments/{experiment_id}", response_model=ExperimentOut)
def my_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentOut:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    experiment = student_service.get_experiment_for_student(db, current_user, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment


@router.get("/me/experiments/{experiment_id}/group", response_model=ExperimentGroupOut | None)
def my_experiment_group(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentGroupOut | None:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    return student_service.get_experiment_group_for_student(db, current_user, experiment_id)


@router.get("/me/experiments/{experiment_id}/observations", response_model=list[ExperimentObservationOut])
def my_experiment_observations(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentObservationOut]:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    experiment = student_service.get_experiment_for_student(db, current_user, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment_service.list_observations(db, experiment_id)


@router.post(
    "/me/experiments/{experiment_id}/observations",
    response_model=ExperimentObservationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_my_experiment_observation(
    experiment_id: int,
    payload: ExperimentObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExperimentObservationOut:
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    experiment = student_service.get_experiment_for_student(db, current_user, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment_service.create_observation(db, experiment_id, current_user.id, payload)


@router.get("/me/pest-diagnoses", response_model=list[PestDiagnosisListOut])
def my_pest_diagnoses(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PestDiagnosisListOut]:
    """学生查看本组的病虫害诊断记录（仅本组数据隔离）。"""
    if current_user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Student role required"
        )
    if current_user.group_id is None:
        return []
    records = pest_diagnosis_service.list_diagnoses(
        db, group_id=current_user.group_id, limit=limit
    )
    result: list[PestDiagnosisListOut] = []
    for r in records:
        group_name = r.group.name if r.group else None
        node_name = r.node.name if r.node else None
        result.append(
            PestDiagnosisListOut(
                id=r.id,
                group_id=r.group_id,
                node_id=r.node_id,
                device_token_id=r.device_token_id,
                image_url=r.image_url,
                diagnosis_result=r.diagnosis_result,
                confidence=r.confidence,
                suggestion=r.suggestion,
                created_at=r.created_at,
                group_name=group_name,
                node_name=node_name,
            )
        )
    return result

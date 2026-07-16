from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.class_task import ClassTask
from app.models.enums import SensorMetric
from app.models.experiment import Experiment, ExperimentGroup
from app.models.group import Group
from app.models.sensor_data import SensorData
from app.models.task_submission import TaskSubmission
from app.models.user import User
from app.schemas.sensor_data import EChartsResponse
from app.schemas.user import StudentPasswordChange, StudentProfileUpdate
from app.services import experiment_service, group_service, sensor_service


def get_student_group(db: Session, student: User) -> Group | None:
    if student.group_id is None:
        return None
    return group_service.get_group(db, student.group_id)


def list_tasks_for_student(db: Session, student: User) -> list[ClassTask]:
    if student.group_id is None:
        return []
    stmt = (
        select(ClassTask)
        .where(
            or_(
                ClassTask.group_id == student.group_id,
                ClassTask.group_id.is_(None),
            )
        )
        .order_by(ClassTask.created_at.desc())
    )
    return db.execute(stmt).scalars().all()


def list_submissions_for_student(
    db: Session,
    student: User,
    task_id: int | None = None,
) -> list[TaskSubmission]:
    stmt = (
        select(TaskSubmission)
        .where(TaskSubmission.student_id == student.id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    if task_id is not None:
        stmt = stmt.where(TaskSubmission.task_id == task_id)
    return db.execute(stmt).scalars().all()


def list_sensor_data_for_student(
    db: Session,
    student: User,
    limit: int = 50,
) -> list[SensorData]:
    group = get_student_group(db, student)
    if not group or group.node_id is None:
        return []
    return sensor_service.list_sensor_data(
        db, node_id=group.node_id, limit=limit
    )


def latest_sensor_data_for_student(
    db: Session, student: User
) -> SensorData | None:
    group = get_student_group(db, student)
    if not group or group.node_id is None:
        return None
    return sensor_service.latest_sensor_data(db, node_id=group.node_id)


def echarts_data_for_student(
    db: Session,
    student: User,
    metrics: list[SensorMetric] | None = None,
    limit: int = 200,
) -> EChartsResponse:
    group = get_student_group(db, student)
    if not group or group.node_id is None:
        return EChartsResponse(x=[], series=[])
    rows = sensor_service.list_sensor_data(
        db, node_id=group.node_id, limit=limit
    )
    return sensor_service.build_echarts_data(rows, metrics)


def update_student_profile(
    db: Session, student: User, payload: StudentProfileUpdate
) -> User:
    update_data = payload.model_dump(exclude_unset=True)
    if "display_name" in update_data:
        student.display_name = update_data["display_name"]
    if "avatar_url" in update_data:
        student.avatar_url = update_data["avatar_url"]
    db.commit()
    db.refresh(student)
    return student


def change_student_password(
    db: Session, student: User, payload: StudentPasswordChange
) -> User:
    if not verify_password(payload.old_password, student.hashed_password):
        raise ValueError("Old password is incorrect")
    student.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    db.refresh(student)
    return student


def list_experiments_for_student(db: Session, student: User) -> list[Experiment]:
    if student.group_id is None:
        return []
    group = group_service.get_group(db, student.group_id)
    if not group:
        return []
    return experiment_service.list_experiments(db, class_id=group.class_id)


def get_experiment_for_student(db: Session, student: User, experiment_id: int) -> Experiment | None:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        return None
    if student.group_id is None:
        return None
    group = group_service.get_group(db, student.group_id)
    if not group or group.class_id != experiment.class_id:
        return None
    return experiment


def get_experiment_group_for_student(db: Session, student: User, experiment_id: int) -> ExperimentGroup | None:
    if student.group_id is None:
        return None
    groups = experiment_service.list_experiment_groups(db, experiment_id)
    for eg in groups:
        if eg.group_id == student.group_id:
            return eg
    return None

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experiment import Experiment, ExperimentGroup, ExperimentObservation
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentGroupCreate,
    ExperimentObservationCreate,
    ExperimentUpdate,
)


def list_experiments(
    db: Session,
    class_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[Experiment]:
    stmt = select(Experiment).order_by(Experiment.created_at.desc())
    if class_id is not None:
        stmt = stmt.where(Experiment.class_id == class_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_experiment(db: Session, experiment_id: int) -> Experiment | None:
    return db.get(Experiment, experiment_id)


def create_experiment(db: Session, exp_in: ExperimentCreate) -> Experiment:
    experiment = Experiment(
        class_id=exp_in.class_id,
        title=exp_in.title,
        hypothesis=exp_in.hypothesis,
        variable_metric=exp_in.variable_metric,
        start_date=exp_in.start_date,
        end_date=exp_in.end_date,
        status=exp_in.status,
        conclusion=exp_in.conclusion,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def update_experiment(db: Session, experiment: Experiment, exp_in: ExperimentUpdate) -> Experiment:
    update_data = exp_in.model_dump(exclude_unset=True)
    for field in ("title", "hypothesis", "variable_metric", "start_date",
                  "end_date", "status", "conclusion"):
        if field in update_data:
            setattr(experiment, field, update_data[field])
    db.commit()
    db.refresh(experiment)
    return experiment


def delete_experiment(db: Session, experiment: Experiment) -> None:
    db.delete(experiment)
    db.commit()


def list_experiment_groups(db: Session, experiment_id: int) -> list[ExperimentGroup]:
    stmt = (
        select(ExperimentGroup)
        .where(ExperimentGroup.experiment_id == experiment_id)
        .order_by(ExperimentGroup.created_at)
    )
    return db.execute(stmt).scalars().all()


def create_experiment_group(
    db: Session, experiment_id: int, eg_in: ExperimentGroupCreate
) -> ExperimentGroup:
    eg = ExperimentGroup(
        experiment_id=experiment_id,
        group_id=eg_in.group_id,
        role=eg_in.role,
        variable_target=eg_in.variable_target,
    )
    db.add(eg)
    db.commit()
    db.refresh(eg)
    return eg


def delete_experiment_group(db: Session, eg: ExperimentGroup) -> None:
    db.delete(eg)
    db.commit()


def list_observations(
    db: Session,
    experiment_id: int,
    student_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[ExperimentObservation]:
    stmt = (
        select(ExperimentObservation)
        .where(ExperimentObservation.experiment_id == experiment_id)
        .order_by(ExperimentObservation.recorded_at.desc())
    )
    if student_id is not None:
        stmt = stmt.where(ExperimentObservation.student_id == student_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def create_observation(
    db: Session,
    experiment_id: int,
    student_id: int,
    obs_in: ExperimentObservationCreate,
) -> ExperimentObservation:
    obs = ExperimentObservation(
        experiment_id=experiment_id,
        student_id=student_id,
        sensor_data_id=obs_in.sensor_data_id,
        content=obs_in.content,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.enums import UserRole
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentGroupCreate,
    ExperimentGroupOut,
    ExperimentObservationCreate,
    ExperimentObservationOut,
    ExperimentOut,
    ExperimentUpdate,
)
from app.services import experiment_service, log_service

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentOut])
def list_experiments(
    class_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[ExperimentOut]:
    return experiment_service.list_experiments(db, class_id=class_id, skip=skip, limit=limit)


@router.post("", response_model=ExperimentOut, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ExperimentOut:
    experiment = experiment_service.create_experiment(db, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_experiment",
        entity_type="experiment",
        entity_id=str(experiment.id),
        detail=f"Created experiment {experiment.title}",
    )
    return experiment


@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ExperimentOut:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment


@router.patch("/{experiment_id}", response_model=ExperimentOut)
def update_experiment(
    experiment_id: int,
    payload: ExperimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ExperimentOut:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    experiment = experiment_service.update_experiment(db, experiment, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_experiment",
        entity_type="experiment",
        entity_id=str(experiment.id),
        detail=f"Updated experiment {experiment.title}",
    )
    return experiment


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    experiment_service.delete_experiment(db, experiment)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_experiment",
        entity_type="experiment",
        entity_id=str(experiment_id),
        detail=f"Deleted experiment {experiment.title}",
    )


@router.get("/{experiment_id}/groups", response_model=list[ExperimentGroupOut])
def list_experiment_groups(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[ExperimentGroupOut]:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment_service.list_experiment_groups(db, experiment_id)


@router.post(
    "/{experiment_id}/groups",
    response_model=ExperimentGroupOut,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment_group(
    experiment_id: int,
    payload: ExperimentGroupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ExperimentGroupOut:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    eg = experiment_service.create_experiment_group(db, experiment_id, payload)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="add_experiment_group",
        entity_type="experiment_group",
        entity_id=str(eg.id),
        detail=f"Added group {eg.group_id} as {eg.role.value} to experiment {experiment_id}",
    )
    return eg


@router.delete(
    "/{experiment_id}/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_experiment_group(
    experiment_id: int,
    group_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    for eg in experiment_service.list_experiment_groups(db, experiment_id):
        if eg.group_id == group_id:
            experiment_service.delete_experiment_group(db, eg)
            log_service.create_operation_log(
                db,
                user_id=current_user.id,
                action="remove_experiment_group",
                entity_type="experiment_group",
                entity_id=str(eg.id),
                detail=f"Removed group {group_id} from experiment {experiment_id}",
            )
            return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Group not assigned to this experiment",
    )


@router.get("/{experiment_id}/observations", response_model=list[ExperimentObservationOut])
def list_observations(
    experiment_id: int,
    student_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ExperimentObservationOut]:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment_service.list_observations(
        db, experiment_id, student_id=student_id, skip=skip, limit=limit
    )


@router.post(
    "/{experiment_id}/observations",
    response_model=ExperimentObservationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_observation(
    experiment_id: int,
    payload: ExperimentObservationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ExperimentObservationOut:
    experiment = experiment_service.get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment_service.create_observation(db, experiment_id, current_user.id, payload)

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.device_log import DeviceOperationLogOut
from app.schemas.operation_log import OperationLogOut
from app.schemas.rule_log import RuleLogOut
from app.services import log_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/operations", response_model=list[OperationLogOut])
def operation_logs(
    user_id: int | None = None,
    entity_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> list[OperationLogOut]:
    return log_service.list_operation_logs(
        db,
        user_id=user_id,
        entity_type=entity_type,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )


@router.get("/device", response_model=list[DeviceOperationLogOut])
def device_logs(
    node_id: int | None = None,
    component_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[DeviceOperationLogOut]:
    return log_service.list_device_logs(
        db, node_id=node_id, component_id=component_id, skip=skip, limit=limit
    )


@router.get("/rules", response_model=list[RuleLogOut])
def rules_logs(
    rule_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[RuleLogOut]:
    return log_service.list_rule_logs(db, rule_id=rule_id, skip=skip, limit=limit)

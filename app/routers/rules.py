from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.rule import RuleCreate, RuleOut, RuleUpdate
from app.schemas.rule_log import RuleLogOut
from app.services import log_service, rule_service

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[RuleOut]:
    return rule_service.list_rules(db, skip=skip, limit=limit)


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> RuleOut:
    try:
        rule = rule_service.create_rule(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="create_rule",
        entity_type="rule",
        entity_id=str(rule.id),
        detail=f"Created rule {rule.name}",
    )
    return rule


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> RuleOut:
    rule = rule_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    try:
        rule = rule_service.update_rule(db, rule, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="update_rule",
        entity_type="rule",
        entity_id=str(rule.id),
        detail=f"Updated rule {rule.name}",
    )
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> None:
    rule = rule_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    rule_service.delete_rule(db, rule)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_rule",
        entity_type="rule",
        entity_id=str(rule_id),
        detail=f"Deleted rule {rule.name}",
    )


@router.post("/{rule_id}/toggle", response_model=RuleOut)
def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> RuleOut:
    rule = rule_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    rule = rule_service.toggle_rule(db, rule)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="toggle_rule",
        entity_type="rule",
        entity_id=str(rule.id),
        detail=f"Rule enabled={rule.enabled}",
    )
    return rule


@router.get("/logs", response_model=list[RuleLogOut])
def rule_logs(
    rule_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[RuleLogOut]:
    return log_service.list_rule_logs(db, rule_id=rule_id, skip=skip, limit=limit)

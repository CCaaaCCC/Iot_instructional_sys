from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.dashboard import ComponentSummary, DashboardOverview
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/component-summary", response_model=list[ComponentSummary])
def component_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[ComponentSummary]:
    return dashboard_service.component_summary(db)


@router.get("/overview", response_model=DashboardOverview)
def overview(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> DashboardOverview:
    return dashboard_service.overview(db)

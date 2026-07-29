from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import SensorMetric, UserRole
from app.schemas.sensor_data import EChartsResponse, SensorDataCreate, SensorDataOut
from app.services import sensor_service

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/data", response_model=SensorDataOut, status_code=status.HTTP_201_CREATED)
def create_sensor_data(
    payload: SensorDataCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> SensorDataOut:
    try:
        return sensor_service.create_sensor_data(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/data", response_model=list[SensorDataOut])
def list_sensor_data(
    node_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[SensorDataOut]:
    return sensor_service.list_sensor_data(
        db,
        node_id=node_id,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )


@router.get("/data/latest", response_model=SensorDataOut | None)
def latest_sensor_data(
    node_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> SensorDataOut | None:
    return sensor_service.latest_sensor_data(db, node_id=node_id)


@router.get("/data/echarts", response_model=EChartsResponse)
def echarts_data(
    node_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    metrics: list[SensorMetric] | None = Query(None),
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> EChartsResponse:
    rows = sensor_service.list_sensor_data(
        db,
        node_id=node_id,
        start_time=start_time,
        end_time=end_time,
        skip=0,
        limit=limit,
    )
    return sensor_service.build_echarts_data(rows, metrics)

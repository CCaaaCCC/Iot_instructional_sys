from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.schemas.student_analytics import (
    ClassroomOverview,
    StudentAnalyticsFull,
    StudentEChartsResponse,
    StudentStats,
)
from app.services import student_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/students", response_model=list[StudentStats])
def list_students_stats(
    group_id: int | None = None,
    classroom_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> list[StudentStats]:
    return student_analytics_service.list_students_with_stats(
        db,
        group_id=group_id,
        classroom_id=classroom_id,
        skip=skip,
        limit=limit,
    )


@router.get("/students/{student_id}", response_model=StudentAnalyticsFull)
def get_student_analytics(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> StudentAnalyticsFull:
    result = student_analytics_service.get_analytics_for_student(db, student_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or user is not a student",
        )
    return result


@router.get("/students/{student_id}/echarts", response_model=StudentEChartsResponse)
def get_student_echarts(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> StudentEChartsResponse:
    return student_analytics_service.build_analytics_echarts(db, student_id)


@router.get(
    "/classrooms/{classroom_id}/overview", response_model=ClassroomOverview
)
def get_classroom_overview(
    classroom_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin, UserRole.teacher)),
) -> ClassroomOverview:
    """班级驾驶舱：教师一眼看清班级整体学情、小组排行、任务完成情况和评分分布"""
    result = student_analytics_service.get_classroom_overview(db, classroom_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found",
        )
    return result

from datetime import date
from typing import Any

from pydantic import BaseModel


class StudentAnalyticsSummary(BaseModel):
    student_id: int
    student_name: str
    total_submissions: int
    avg_score: float | None
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    on_time_count: int
    late_count: int
    on_time_ratio: float


class SubmissionTrendPoint(BaseModel):
    date: str
    count: int


class ScoreTrendPoint(BaseModel):
    date: str
    avg_score: float | None


class RecentActivity(BaseModel):
    type: str
    task_title: str | None
    date: str
    score: int | None
    detail: str | None


class StudentAnalyticsFull(BaseModel):
    summary: StudentAnalyticsSummary
    submission_frequency: list[SubmissionTrendPoint]
    score_trend: list[ScoreTrendPoint]
    recent_activity: list[RecentActivity]


class StudentStats(BaseModel):
    student_id: int
    student_name: str
    total_submissions: int
    avg_score: float | None
    reviewed_count: int
    completed_tasks: int
    completion_rate: float


class StudentEChartsResponse(BaseModel):
    x: list[str]
    series: list[dict]


# ===== 班级驾驶舱相关 Schema =====


class GroupStat(BaseModel):
    """小组统计数据"""
    group_id: int
    group_name: str
    student_count: int
    submission_count: int
    avg_score: float | None
    completion_rate: float
    pending_review_count: int


class TaskStat(BaseModel):
    """任务统计数据"""
    task_id: int
    task_title: str
    task_type: str | None
    status: str
    due_date: date | None
    total_submissions: int
    unsubmitted_count: int
    avg_score: float | None


class ScoreDistribution(BaseModel):
    """评分分布"""
    range_0_60: int
    range_60_70: int
    range_70_80: int
    range_80_90: int
    range_90_100: int


class ClassroomOverview(BaseModel):
    """班级驾驶舱概览数据"""
    classroom_id: int
    classroom_name: str
    subject: str | None
    teacher_name: str | None
    total_students: int
    total_groups: int
    total_tasks: int
    avg_completion_rate: float
    avg_score: float | None
    pending_review_count: int
    on_time_ratio: float
    groups: list[GroupStat]
    tasks: list[TaskStat]
    score_distribution: ScoreDistribution
    echarts: dict[str, Any]

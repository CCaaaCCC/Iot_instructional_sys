from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_task import ClassTask
from app.models.classroom import Classroom
from app.models.enums import UserRole
from app.models.group import Group
from app.models.task_submission import TaskSubmission
from app.models.user import User
from app.schemas.student_analytics import (
    ClassroomOverview,
    GroupStat,
    RecentActivity,
    ScoreDistribution,
    ScoreTrendPoint,
    StudentAnalyticsFull,
    StudentAnalyticsSummary,
    StudentEChartsResponse,
    StudentStats,
    SubmissionTrendPoint,
    TaskStat,
)


def _compute_summary(db: Session, student_id: int) -> StudentAnalyticsSummary | None:
    student = db.get(User, student_id)
    if not student or student.role != UserRole.student:
        return None

    submissions = (
        db.execute(
            select(TaskSubmission)
            .where(TaskSubmission.student_id == student_id)
            .order_by(TaskSubmission.submitted_at.asc())
        )
        .scalars()
        .all()
    )

    total_submissions = len(submissions)
    scores = [s.score for s in submissions if s.score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # Tasks assigned to student's group
    total_tasks = 0
    if student.group_id is not None:
        total_tasks = db.execute(
            select(func.count(ClassTask.id)).where(
                ClassTask.group_id == student.group_id
            )
        ).scalar_one()

    submitted_task_ids = {s.task_id for s in submissions}
    completed_tasks = len(submitted_task_ids)
    completion_rate = round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0.0

    on_time_count = 0
    late_count = 0
    for s in submissions:
        task = db.get(ClassTask, s.task_id) if s.task_id else None
        if task and task.due_date:
            if s.submitted_at.date() <= task.due_date:
                on_time_count += 1
            else:
                late_count += 1
        else:
            on_time_count += 1  # no due date = on time

    on_time_ratio = (
        round(on_time_count / total_submissions * 100, 1) if total_submissions > 0 else 0.0
    )

    student_name = student.display_name or student.username
    return StudentAnalyticsSummary(
        student_id=student_id,
        student_name=student_name,
        total_submissions=total_submissions,
        avg_score=avg_score,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        completion_rate=completion_rate,
        on_time_count=on_time_count,
        late_count=late_count,
        on_time_ratio=on_time_ratio,
    )


def get_analytics_for_student(
    db: Session, student_id: int
) -> StudentAnalyticsFull | None:
    student = db.get(User, student_id)
    if not student or student.role != UserRole.student:
        return None

    summary = _compute_summary(db, student_id)
    if summary is None:
        return None

    submissions = (
        db.execute(
            select(TaskSubmission)
            .where(TaskSubmission.student_id == student_id)
            .order_by(TaskSubmission.submitted_at.asc())
        )
        .scalars()
        .all()
    )

    # Submission frequency by date
    freq_map: dict[str, int] = defaultdict(int)
    score_by_date: dict[str, list[int]] = defaultdict(list)
    for s in submissions:
        d = s.submitted_at.strftime("%Y-%m-%d")
        freq_map[d] += 1
        if s.score is not None:
            score_by_date[d].append(s.score)

    submission_frequency = sorted(
        [SubmissionTrendPoint(date=k, count=v) for k, v in freq_map.items()],
        key=lambda x: x.date,
    )
    score_trend = sorted(
        [
            ScoreTrendPoint(
                date=k,
                avg_score=round(sum(v) / len(v), 1) if v else None,
            )
            for k, v in score_by_date.items()
        ],
        key=lambda x: x.date,
    )

    # Recent activity (last 10 submissions)
    recent_subs = (
        db.execute(
            select(TaskSubmission)
            .where(TaskSubmission.student_id == student_id)
            .order_by(TaskSubmission.submitted_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    recent_activity: list[RecentActivity] = []
    for s in recent_subs:
        task_title = s.task.title if s.task else None
        if s.reviewed_at:
            recent_activity.append(
                RecentActivity(
                    type="reviewed",
                    task_title=task_title,
                    date=s.reviewed_at.strftime("%Y-%m-%d %H:%M"),
                    score=s.score,
                    detail=f"得分 {s.score}，评语：{s.feedback or '无'}",
                )
            )
        else:
            recent_activity.append(
                RecentActivity(
                    type="submission",
                    task_title=task_title,
                    date=s.submitted_at.strftime("%Y-%m-%d %H:%M"),
                    score=None,
                    detail=f"提交了作业" + (f"（{s.content[:30]}...）" if s.content else ""),
                )
            )

    return StudentAnalyticsFull(
        summary=summary,
        submission_frequency=submission_frequency,
        score_trend=score_trend,
        recent_activity=recent_activity,
    )


def list_students_with_stats(
    db: Session,
    group_id: int | None = None,
    classroom_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[StudentStats]:
    stmt = select(User).where(
        User.role == UserRole.student, User.is_active.is_(True)
    )
    if group_id is not None:
        stmt = stmt.where(User.group_id == group_id)
    if classroom_id is not None:
        group_ids = (
            db.execute(
                select(Group.id).where(Group.class_id == classroom_id)
            )
            .scalars()
            .all()
        )
        if group_ids:
            stmt = stmt.where(User.group_id.in_(group_ids))
        else:
            return []
    stmt = stmt.order_by(User.username.asc()).offset(skip).limit(limit)
    students = db.execute(stmt).scalars().all()

    result: list[StudentStats] = []
    for student in students:
        submission_count = db.execute(
            select(func.count(TaskSubmission.id)).where(
                TaskSubmission.student_id == student.id
            )
        ).scalar_one()
        scores = (
            db.execute(
                select(TaskSubmission.score).where(
                    TaskSubmission.student_id == student.id,
                    TaskSubmission.score.isnot(None),
                )
            )
            .scalars()
            .all()
        )
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        reviewed_count = len(scores)
        submitted_task_ids = set(
            db.execute(
                select(TaskSubmission.task_id).where(
                    TaskSubmission.student_id == student.id
                )
            )
            .scalars()
            .all()
        )
        completed_tasks = len(submitted_task_ids)
        total_tasks = 0
        if student.group_id is not None:
            total_tasks = db.execute(
                select(func.count(ClassTask.id)).where(
                    ClassTask.group_id == student.group_id
                )
            ).scalar_one()
        completion_rate = (
            round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0.0
        )

        result.append(
            StudentStats(
                student_id=student.id,
                student_name=student.display_name or student.username,
                total_submissions=submission_count,
                avg_score=avg_score,
                reviewed_count=reviewed_count,
                completed_tasks=completed_tasks,
                completion_rate=completion_rate,
            )
        )
    return result


def build_analytics_echarts(
    db: Session, student_id: int
) -> StudentEChartsResponse:
    full = get_analytics_for_student(db, student_id)
    if full is None:
        return StudentEChartsResponse(x=[], series=[])

    x = [p.date for p in full.submission_frequency]
    freq_data = [p.count for p in full.submission_frequency]

    # Align score trend with submission frequency dates
    score_map = {p.date: p.avg_score for p in full.score_trend}
    score_data = [score_map.get(d) for d in x]

    return StudentEChartsResponse(
        x=x,
        series=[
            {"name": "提交次数", "data": freq_data},
            {"name": "平均得分", "data": score_data},
        ],
    )


def get_analytics_summary_for_student(
    db: Session, student_id: int
) -> StudentAnalyticsSummary | None:
    return _compute_summary(db, student_id)


def get_classroom_overview(
    db: Session, classroom_id: int
) -> ClassroomOverview | None:
    """获取班级驾驶舱概览数据：班级整体指标 + 小组排行 + 任务完成情况 + 评分分布 + ECharts 数据"""
    classroom = db.get(Classroom, classroom_id)
    if not classroom:
        return None

    # 1. 获取班级所有小组
    groups = (
        db.execute(select(Group).where(Group.class_id == classroom_id))
        .scalars()
        .all()
    )
    group_ids = [g.id for g in groups]

    # 2. 获取班级所有学生
    if not group_ids:
        return ClassroomOverview(
            classroom_id=classroom_id,
            classroom_name=classroom.name,
            subject=classroom.subject.value if classroom.subject else None,
            teacher_name=_get_user_display_name(db, classroom.teacher_id),
            total_students=0,
            total_groups=0,
            total_tasks=0,
            avg_completion_rate=0.0,
            avg_score=None,
            pending_review_count=0,
            on_time_ratio=0.0,
            groups=[],
            tasks=[],
            score_distribution=ScoreDistribution(
                range_0_60=0, range_60_70=0, range_70_80=0, range_80_90=0, range_90_100=0
            ),
            echarts={
                "group_completion": {"x": [], "series": []},
                "score_distribution": {
                    "x": ["0-60", "60-70", "70-80", "80-90", "90-100"],
                    "series": [{"name": "人数", "data": [0, 0, 0, 0, 0]}],
                },
            },
        )

    students = (
        db.execute(
            select(User).where(
                User.role == UserRole.student,
                User.is_active.is_(True),
                User.group_id.in_(group_ids),
            )
        )
        .scalars()
        .all()
    )
    student_ids = [s.id for s in students]

    # 3. 获取班级所有任务
    tasks = (
        db.execute(
            select(ClassTask)
            .where(ClassTask.group_id.in_(group_ids))
            .order_by(ClassTask.created_at.desc())
        )
        .scalars()
        .all()
    )

    # 4. 获取所有提交记录
    submissions = (
        db.execute(
            select(TaskSubmission).where(TaskSubmission.student_id.in_(student_ids))
        ).scalars().all()
        if student_ids
        else []
    )

    # 5. 计算每个小组的统计
    group_stats: list[GroupStat] = []
    for g in groups:
        g_student_ids = [s.id for s in students if s.group_id == g.id]
        g_submissions = [s for s in submissions if s.student_id in g_student_ids]
        g_scores = [s.score for s in g_submissions if s.score is not None]
        g_avg_score = round(sum(g_scores) / len(g_scores), 1) if g_scores else None
        g_pending = sum(1 for s in g_submissions if s.reviewed_at is None)
        g_tasks = [t for t in tasks if t.group_id == g.id]
        g_submitted_task_ids = {s.task_id for s in g_submissions}
        g_completion_rate = (
            round(len(g_submitted_task_ids) / len(g_tasks) * 100, 1)
            if g_tasks
            else 0.0
        )
        group_stats.append(
            GroupStat(
                group_id=g.id,
                group_name=g.name,
                student_count=len(g_student_ids),
                submission_count=len(g_submissions),
                avg_score=g_avg_score,
                completion_rate=g_completion_rate,
                pending_review_count=g_pending,
            )
        )

    # 6. 计算每个任务的统计
    task_stats: list[TaskStat] = []
    for t in tasks:
        t_student_count = sum(1 for s in students if s.group_id == t.group_id)
        t_submissions = [s for s in submissions if s.task_id == t.id]
        t_scores = [s.score for s in t_submissions if s.score is not None]
        t_avg_score = (
            round(sum(t_scores) / len(t_scores), 1) if t_scores else None
        )
        t_submitted_student_ids = {s.student_id for s in t_submissions}
        t_unsubmitted = max(0, t_student_count - len(t_submitted_student_ids))
        task_stats.append(
            TaskStat(
                task_id=t.id,
                task_title=t.title,
                task_type=t.task_type.value if t.task_type else None,
                status=t.status.value if t.status else "pending",
                due_date=t.due_date,
                total_submissions=len(t_submissions),
                unsubmitted_count=t_unsubmitted,
                avg_score=t_avg_score,
            )
        )

    # 7. 计算评分分布
    all_scores = [s.score for s in submissions if s.score is not None]
    score_dist = ScoreDistribution(
        range_0_60=sum(1 for s in all_scores if s < 60),
        range_60_70=sum(1 for s in all_scores if 60 <= s < 70),
        range_70_80=sum(1 for s in all_scores if 70 <= s < 80),
        range_80_90=sum(1 for s in all_scores if 80 <= s < 90),
        range_90_100=sum(1 for s in all_scores if 90 <= s <= 100),
    )

    # 8. 计算班级整体指标
    all_completion_rates = [g.completion_rate for g in group_stats] or [0.0]
    avg_completion_rate = round(
        sum(all_completion_rates) / len(all_completion_rates), 1
    )
    avg_score = (
        round(sum(all_scores) / len(all_scores), 1) if all_scores else None
    )
    pending_review_count = sum(1 for s in submissions if s.reviewed_at is None)

    # 按时率
    on_time_count = 0
    total_with_due = 0
    task_map = {t.id: t for t in tasks}
    for s in submissions:
        task = task_map.get(s.task_id)
        if task and task.due_date:
            total_with_due += 1
            if s.submitted_at.date() <= task.due_date:
                on_time_count += 1
    on_time_ratio = (
        round(on_time_count / total_with_due * 100, 1)
        if total_with_due > 0
        else 0.0
    )

    # 9. ECharts 数据
    group_names = [g.group_name for g in group_stats]
    group_rates = [g.completion_rate for g in group_stats]
    score_ranges = ["0-60", "60-70", "70-80", "80-90", "90-100"]
    score_counts = [
        score_dist.range_0_60,
        score_dist.range_60_70,
        score_dist.range_70_80,
        score_dist.range_80_90,
        score_dist.range_90_100,
    ]

    echarts = {
        "group_completion": {
            "x": group_names,
            "series": [{"name": "完成率(%)", "data": group_rates}],
        },
        "score_distribution": {
            "x": score_ranges,
            "series": [{"name": "人数", "data": score_counts}],
        },
    }

    return ClassroomOverview(
        classroom_id=classroom_id,
        classroom_name=classroom.name,
        subject=classroom.subject.value if classroom.subject else None,
        teacher_name=_get_user_display_name(db, classroom.teacher_id),
        total_students=len(students),
        total_groups=len(groups),
        total_tasks=len(tasks),
        avg_completion_rate=avg_completion_rate,
        avg_score=avg_score,
        pending_review_count=pending_review_count,
        on_time_ratio=on_time_ratio,
        groups=group_stats,
        tasks=task_stats,
        score_distribution=score_dist,
        echarts=echarts,
    )


def _get_user_display_name(db: Session, user_id: int | None) -> str | None:
    """辅助函数：获取用户显示名"""
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if not user:
        return None
    return user.display_name or user.username

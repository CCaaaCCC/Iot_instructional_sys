import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_task import ClassTask
from app.schemas.class_task import TaskCreate, TaskUpdate

SUBMISSION_DIR = "data/submissions"


def _notify_students_new_task(db: Session, task: ClassTask) -> None:
    """任务发布后通知该组学生（group_id 为 None 时跳过，班级任务通知后续完善）。"""
    if task.group_id is None:
        return
    try:
        from app.services import notification_service
        from app.core.websocket_manager import ws_manager
        student_ids = notification_service.get_student_ids_by_group(db, task.group_id)
        if not student_ids:
            return
        title = "新任务发布"
        content = f"老师发布了新任务「{task.title}」，请及时完成。"
        link = "/student/tasks"
        notifications = notification_service.create_notification_for_users(
            db, student_ids, "task_published", title, content, link
        )
        db.commit()
        # WebSocket 实时推送
        for n in notifications:
            ws_manager.send_to_user_sync("notification", {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "link": n.link,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }, user_id=n.user_id)
    except Exception:
        # 通知失败不应影响任务创建主流程
        import logging
        logging.getLogger(__name__).exception("Failed to notify students for new task %s", task.id)


def list_tasks(
    db: Session,
    group_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[ClassTask]:
    stmt = select(ClassTask).order_by(ClassTask.created_at.desc())
    if group_id is not None:
        stmt = stmt.where(ClassTask.group_id == group_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_task(db: Session, task_id: int) -> ClassTask | None:
    return db.get(ClassTask, task_id)


def create_task(db: Session, task_in: TaskCreate, created_by: int | None) -> ClassTask:
    task = ClassTask(
        title=task_in.title,
        description=task_in.description,
        assigned_date=task_in.assigned_date,
        due_date=task_in.due_date,
        status=task_in.status,
        created_by=created_by,
        group_id=task_in.group_id,
        course_subject=task_in.course_subject,
        task_type=task_in.task_type,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    _notify_students_new_task(db, task)
    return task


def update_task(db: Session, task: ClassTask, task_in: TaskUpdate) -> ClassTask:
    update_data = task_in.model_dump(exclude_unset=True)
    for field in ("title", "description", "assigned_date", "due_date", "status",
                  "group_id", "course_subject", "task_type"):
        if field in update_data:
            setattr(task, field, update_data[field])
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: ClassTask) -> None:
    for submission in task.submissions:
        for sf in submission.files:
            file_path = os.path.join(SUBMISSION_DIR, sf.filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
    db.delete(task)
    db.commit()

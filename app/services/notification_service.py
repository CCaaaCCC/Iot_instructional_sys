from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.models.enums import UserRole


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    title: str,
    content: str,
    link: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        link=link,
    )
    db.add(notification)
    db.flush()
    return notification


def create_notification_for_users(
    db: Session,
    user_ids: list[int],
    type: str,
    title: str,
    content: str,
    link: str | None = None,
) -> list[Notification]:
    notifications: list[Notification] = []
    for uid in user_ids:
        n = create_notification(db, uid, type, title, content, link)
        notifications.append(n)
    db.flush()
    return notifications


def list_notifications_for_user(
    db: Session,
    user_id: int,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_unread_count(db: Session, user_id: int) -> int:
    from sqlalchemy import func
    result = db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).scalar_one()
    return result


def mark_as_read(db: Session, notification_id: int, user_id: int) -> Notification | None:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        return None
    notification.is_read = True
    db.flush()
    return notification


def mark_all_as_read(db: Session, user_id: int) -> int:
    result = db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.flush()
    return result.rowcount or 0


def get_student_ids_by_group(db: Session, group_id: int) -> list[int]:
    stmt = select(User.id).where(
        User.group_id == group_id,
        User.role == UserRole.student,
        User.is_active.is_(True),
    )
    return list(db.execute(stmt).scalars().all())


def get_admin_and_teacher_ids(db: Session) -> list[int]:
    stmt = select(User.id).where(
        User.role.in_([UserRole.admin, UserRole.teacher]),
        User.is_active.is_(True),
    )
    return list(db.execute(stmt).scalars().all())

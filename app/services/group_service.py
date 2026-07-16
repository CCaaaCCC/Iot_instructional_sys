from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.device_node import DeviceNode
from app.models.group import Group
from app.models.user import User
from app.schemas.group import BatchStudentCreate, GroupCreate, GroupUpdate


def list_groups(
    db: Session,
    class_id: int | None = None,
    node_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[Group]:
    stmt = select(Group).order_by(Group.created_at.asc())
    if class_id is not None:
        stmt = stmt.where(Group.class_id == class_id)
    if node_id is not None:
        stmt = stmt.where(Group.node_id == node_id)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_group(db: Session, group_id: int) -> Group | None:
    return db.get(Group, group_id)


def create_group(db: Session, group_in: GroupCreate) -> Group:
    group = Group(
        name=group_in.name,
        class_id=group_in.class_id,
        node_id=group_in.node_id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, group: Group, group_in: GroupUpdate) -> Group:
    if group_in.name is not None:
        group.name = group_in.name
    if group_in.node_id is not None:
        group.node_id = group_in.node_id
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group: Group) -> None:
    db.delete(group)
    db.commit()


def bind_node(db: Session, group: Group, node_id: int) -> Group:
    node = db.get(DeviceNode, node_id)
    if not node:
        raise ValueError("Node not found")
    group.node_id = node_id
    db.commit()
    db.refresh(group)
    return group


def unbind_node(db: Session, group: Group) -> Group:
    group.node_id = None
    db.commit()
    db.refresh(group)
    return group


def list_students(db: Session, group_id: int) -> list[User]:
    stmt = (
        select(User)
        .where(User.group_id == group_id)
        .order_by(User.username.asc())
    )
    return db.execute(stmt).scalars().all()


def batch_create_students(
    db: Session, payload: BatchStudentCreate
) -> list[User]:
    group = get_group(db, payload.group_id)
    if not group:
        raise ValueError("Group not found")
    hashed = get_password_hash(payload.password)
    existing_students = list_students(db, payload.group_id)
    existing_count = len(existing_students)
    count = payload.count
    names = payload.display_names or []
    created: list[User] = []
    for i in range(count):
        seq = existing_count + i + 1
        username = f"g{payload.group_id}s{seq}"
        display_name = names[i] if i < len(names) else f"学生{seq}"
        user = User(
            username=username,
            hashed_password=hashed,
            role="student",
            is_active=True,
            display_name=display_name,
            group_id=payload.group_id,
        )
        db.add(user)
        created.append(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Student username conflict — please retry with a different sequence") from exc
    for user in created:
        db.refresh(user)
    return created

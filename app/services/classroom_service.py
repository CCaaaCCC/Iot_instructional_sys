from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.classroom import Classroom
from app.schemas.classroom import ClassroomCreate, ClassroomUpdate


def list_classrooms(
    db: Session,
    teacher_id: int | None = None,
    subject: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Classroom]:
    stmt = select(Classroom).order_by(Classroom.created_at.desc())
    if teacher_id is not None:
        stmt = stmt.where(Classroom.teacher_id == teacher_id)
    if subject:
        stmt = stmt.where(Classroom.subject == subject)
    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_classroom(db: Session, classroom_id: int) -> Classroom | None:
    return db.get(Classroom, classroom_id)


def create_classroom(db: Session, classroom_in: ClassroomCreate) -> Classroom:
    classroom = Classroom(
        name=classroom_in.name,
        teacher_id=classroom_in.teacher_id,
        subject=classroom_in.subject,
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


def update_classroom(
    db: Session, classroom: Classroom, classroom_in: ClassroomUpdate
) -> Classroom:
    if classroom_in.name is not None:
        classroom.name = classroom_in.name
    if classroom_in.subject is not None:
        classroom.subject = classroom_in.subject
    if classroom_in.teacher_id is not None:
        classroom.teacher_id = classroom_in.teacher_id
    db.commit()
    db.refresh(classroom)
    return classroom


def delete_classroom(db: Session, classroom: Classroom) -> None:
    db.delete(classroom)
    db.commit()

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TeachingResource(Base):
    __tablename__ = "teaching_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    preview_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str] = mapped_column(String(20), nullable=False)
    classroom_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("class_tasks.id"), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    publisher = relationship("User", foreign_keys=[publisher_id])
    classroom = relationship("Classroom", foreign_keys=[classroom_id])
    group = relationship("Group", foreign_keys=[group_id])
    task = relationship("ClassTask", foreign_keys=[task_id])

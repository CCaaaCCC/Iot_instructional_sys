from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ExperimentRole, ExperimentStatus, SensorMetric


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    hypothesis: Mapped[str] = mapped_column(String(255), nullable=False)
    variable_metric: Mapped[SensorMetric] = mapped_column(Enum(SensorMetric), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus), default=ExperimentStatus.ongoing
    )
    conclusion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    classroom = relationship("Classroom")
    experiment_groups = relationship(
        "ExperimentGroup", back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentGroup(Base):
    __tablename__ = "experiment_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    role: Mapped[ExperimentRole] = mapped_column(Enum(ExperimentRole), nullable=False)
    variable_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    experiment = relationship("Experiment", back_populates="experiment_groups")
    group = relationship("Group")


class ExperimentObservation(Base):
    __tablename__ = "experiment_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    sensor_data_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_data.id"), nullable=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    experiment = relationship("Experiment")
    sensor_data = relationship("SensorData")
    student = relationship("User")

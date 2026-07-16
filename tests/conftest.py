import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.models.enums import UserRole
from app.scripts.init_db import init_db as populate_db

TEST_DB_PATH = Path(__file__).parent / "test_greenhouse.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from app.core.rate_limit import _attempts
    _attempts.clear()
    yield
    _attempts.clear()


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
    except PermissionError:
        pass


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db(test_session_factory):
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def client(test_session_factory, sample_data):
    from app.main import app
    from app.core import dependencies

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[dependencies.get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    return create_access_token("1")


@pytest.fixture
def teacher_token():
    return create_access_token("2")


@pytest.fixture
def operator_token():
    return create_access_token("3")


@pytest.fixture
def student_token():
    return create_access_token("4")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def teacher_headers(teacher_token):
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture
def student_headers(student_token):
    return {"Authorization": f"Bearer {student_token}"}


@pytest.fixture(scope="session")
def sample_data(test_session_factory):
    from app.models import (
        ClassTask,
        Classroom,
        Component,
        Crop,
        DeviceNode,
        Experiment,
        ExperimentGroup,
        Group,
        Rule,
        SensorData,
        User,
    )
    from app.models.enums import (
        ComponentStatus,
        ComponentType,
        CourseSubject,
        ExperimentRole,
        ExperimentStatus,
        RuleOperator,
        SensorMetric,
        TaskStatus,
        TaskType,
        UserRole,
    )
    from app.core.security import get_password_hash
    from datetime import datetime, timedelta

    db = test_session_factory()

    admin = User(
        id=1, username="admin", hashed_password=get_password_hash("Admin123456"),
        role=UserRole.admin, is_active=True
    )
    teacher = User(
        id=2, username="teacher", hashed_password=get_password_hash("Teacher123456"),
        role=UserRole.teacher, is_active=True
    )
    operator = User(
        id=3, username="operator", hashed_password=get_password_hash("Operator123456"),
        role=UserRole.operator, is_active=True
    )
    inactive = User(
        id=6, username="inactive", hashed_password=get_password_hash("Inactive123"),
        role=UserRole.teacher, is_active=False
    )
    db.add_all([admin, teacher, operator, inactive])

    node = DeviceNode(
        id=1, name="Node-1", location="Greenhouse A", online=True,
        last_reported_at=datetime.now()
    )
    db.add(node)

    fan = Component(
        id=1, node_id=1, name="Fan-1", type=ComponentType.fan, status=ComponentStatus.off
    )
    pump = Component(
        id=2, node_id=1, name="Pump-1", type=ComponentType.pump, status=ComponentStatus.off
    )
    light = Component(
        id=3, node_id=1, name="Light-1", type=ComponentType.light, status=ComponentStatus.off
    )
    sensor = Component(
        id=4, node_id=1, name="Sensor-1", type=ComponentType.sensor,
        status=ComponentStatus.on, metric=SensorMetric.air_temp
    )
    db.add_all([fan, pump, light, sensor])

    classroom = Classroom(
        id=1, name="Test Class", teacher_id=2, subject=CourseSubject.labor
    )
    db.add(classroom)

    group = Group(id=1, name="Group-1", class_id=1, node_id=1)
    db.add(group)

    student = User(
        id=4, username="g1s1", hashed_password=get_password_hash("Student123456"),
        role=UserRole.student, is_active=True, display_name="Student One", group_id=1
    )
    db.add(student)

    rule = Rule(
        id=1, name="High Temp Fan",
        metric=SensorMetric.air_temp, operator=RuleOperator.gt,
        threshold=30.0, action_component_type=ComponentType.fan,
        action=ComponentStatus.on, enabled=True, description="Auto fan"
    )
    db.add(rule)

    crop = Crop(
        id=1, name="Tomato", description="Cherry tomato",
        growth_stage="seedling", start_date=datetime.now().date(),
        group_id=1
    )
    db.add(crop)

    task = ClassTask(
        id=1, title="Test Task", description="A test task",
        status=TaskStatus.pending, created_by=1, group_id=1,
        course_subject=CourseSubject.labor, task_type=TaskType.observation
    )
    db.add(task)

    sensor_data = SensorData(
        id=1, node_id=1, air_temp=25.0, air_humidity=60.0,
        soil_temp=20.0, soil_humidity=45.0, light_intensity=350.0, soil_ph=6.5,
        recorded_at=datetime.now()
    )
    db.add(sensor_data)

    experiment = Experiment(
        id=1, class_id=1, title="Test Experiment",
        hypothesis="More light increases growth",
        variable_metric=SensorMetric.light_intensity,
        start_date=datetime.now().date(),
        end_date=(datetime.now() + timedelta(days=7)).date(),
        status=ExperimentStatus.ongoing,
    )
    db.add(experiment)

    exp_group = ExperimentGroup(
        id=1, experiment_id=1, group_id=1,
        role=ExperimentRole.experimental,
        variable_target="Light 12h/day",
    )
    db.add(exp_group)

    db.commit()
    db.close()
    yield

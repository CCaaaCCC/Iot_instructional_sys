import pytest
from datetime import datetime, date
from pydantic import ValidationError

from app.models.enums import (
    UserRole, ComponentType, ComponentStatus, RuleOperator,
    SensorMetric, TaskStatus, CourseSubject, TaskType, ExperimentStatus
)
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.schemas.device_node import DeviceNodeCreate, DeviceNodeUpdate
from app.schemas.component import ComponentCreate, ComponentUpdate, ComponentControlRequest
from app.schemas.sensor_data import SensorDataCreate
from app.schemas.rule import RuleCreate, RuleUpdate
from app.schemas.crop import CropCreate, CropUpdate
from app.schemas.class_task import TaskCreate, TaskUpdate
from app.schemas.classroom import ClassroomCreate, ClassroomUpdate
from app.schemas.group import GroupCreate, GroupUpdate, BatchStudentCreate
from app.schemas.task_submission import TaskSubmissionCreate, SubmissionReview


class TestUserSchema:
    def test_create_valid_user(self):
        u = UserCreate(username="testuser", password="pass1234", role=UserRole.teacher)
        assert u.username == "testuser"
        assert u.password == "pass1234"
        assert u.role == UserRole.teacher
        assert u.is_active is True

    def test_create_user_default_role(self):
        u = UserCreate(username="testuser", password="pass1234")
        assert u.role == UserRole.teacher

    def test_create_user_empty_username(self):
        with pytest.raises(ValidationError):
            UserCreate(username="", password="pass1234")

    def test_create_user_long_username(self):
        with pytest.raises(ValidationError):
            UserCreate(username="a" * 51, password="pass1234")

    def test_create_user_empty_password(self):
        with pytest.raises(ValidationError):
            UserCreate(username="test", password="")

    def test_create_user_long_password(self):
        with pytest.raises(ValidationError):
            UserCreate(username="test", password="a" * 129)

    def test_create_user_short_password(self):
        with pytest.raises(ValidationError):
            UserCreate(username="test", password="ab1")

    def test_create_user_password_no_digit(self):
        with pytest.raises(ValidationError):
            UserCreate(username="test", password="password")

    def test_create_user_password_no_letter(self):
        with pytest.raises(ValidationError):
            UserCreate(username="test", password="12345678")

    def test_update_user_partial(self):
        u = UserUpdate(username="newname")
        assert u.username == "newname"
        assert u.password is None
        assert u.role is None

    def test_update_user_empty_username(self):
        with pytest.raises(ValidationError):
            UserUpdate(username="")

    def test_user_out_from_attributes(self):
        data = {
            "id": 1, "username": "admin", "role": "admin",
            "is_active": True, "display_name": None, "group_id": None,
            "created_at": datetime.now(), "updated_at": datetime.now()
        }
        u = UserOut.model_validate(data)
        assert u.id == 1
        assert u.username == "admin"


class TestDeviceNodeSchema:
    def test_create_valid_node(self):
        n = DeviceNodeCreate(name="TestNode", location="Zone A")
        assert n.name == "TestNode"
        assert n.location == "Zone A"

    def test_create_node_empty_name(self):
        with pytest.raises(ValidationError):
            DeviceNodeCreate(name="", location="Zone A")

    def test_create_node_long_name(self):
        with pytest.raises(ValidationError):
            DeviceNodeCreate(name="a" * 101)

    def test_create_node_long_location(self):
        with pytest.raises(ValidationError):
            DeviceNodeCreate(name="Node", location="a" * 101)

    def test_update_node_partial(self):
        u = DeviceNodeUpdate(location="New Zone")
        assert u.location == "New Zone"
        assert u.name is None


class TestComponentSchema:
    def test_create_valid_component(self):
        c = ComponentCreate(name="TestFan", type=ComponentType.fan)
        assert c.name == "TestFan"
        assert c.type == ComponentType.fan
        assert c.metric is None

    def test_create_component_empty_name(self):
        with pytest.raises(ValidationError):
            ComponentCreate(name="", type=ComponentType.fan)

    def test_create_component_long_name(self):
        with pytest.raises(ValidationError):
            ComponentCreate(name="a" * 51, type=ComponentType.fan)

    def test_control_request_valid(self):
        req = ComponentControlRequest(action=ComponentStatus.on, message="Turn on")
        assert req.action == ComponentStatus.on
        assert req.message == "Turn on"

    def test_control_request_long_message(self):
        with pytest.raises(ValidationError):
            ComponentControlRequest(action=ComponentStatus.on, message="a" * 256)

    def test_update_component_status(self):
        u = ComponentUpdate(status=ComponentStatus.on)
        assert u.status == ComponentStatus.on
        assert u.name is None


class TestSensorDataSchema:
    def test_create_valid(self):
        s = SensorDataCreate(
            node_id=1, air_temp=25.0, air_humidity=60.0,
            soil_temp=20.0, soil_humidity=45.0,
            light_intensity=350.0, soil_ph=6.5
        )
        assert s.node_id == 1
        assert s.air_temp == 25.0

    def test_create_invalid_node_id(self):
        with pytest.raises(ValidationError):
            SensorDataCreate(node_id=0)

    def test_create_negative_node_id(self):
        with pytest.raises(ValidationError):
            SensorDataCreate(node_id=-1)

    def test_create_out_of_range_air_temp(self):
        with pytest.raises(ValidationError):
            SensorDataCreate(node_id=1, air_temp=100.0)

    def test_create_out_of_range_humidity(self):
        with pytest.raises(ValidationError):
            SensorDataCreate(node_id=1, air_humidity=150.0)

    def test_create_out_of_range_ph(self):
        with pytest.raises(ValidationError):
            SensorDataCreate(node_id=1, soil_ph=20.0)

    def test_create_out_of_range_light(self):
        with pytest.raises(ValidationError):
            SensorDataCreate(node_id=1, light_intensity=3000.0)

    def test_create_minimal(self):
        s = SensorDataCreate(node_id=1)
        assert s.air_temp is None
        assert s.air_humidity is None


class TestRuleSchema:
    def test_create_valid_rule(self):
        r = RuleCreate(
            name="Test Rule",
            metric=SensorMetric.air_temp,
            operator=RuleOperator.gt,
            threshold=30.0,
            action_component_type=ComponentType.fan,
            action=ComponentStatus.on,
        )
        assert r.name == "Test Rule"
        assert r.threshold == 30.0
        assert r.enabled is True

    def test_create_rule_empty_name(self):
        with pytest.raises(ValidationError):
            RuleCreate(
                name="", metric=SensorMetric.air_temp,
                operator=RuleOperator.gt, threshold=30.0,
                action_component_type=ComponentType.fan, action=ComponentStatus.on,
            )

    def test_create_rule_long_name(self):
        with pytest.raises(ValidationError):
            RuleCreate(
                name="a" * 101, metric=SensorMetric.air_temp,
                operator=RuleOperator.gt, threshold=30.0,
                action_component_type=ComponentType.fan, action=ComponentStatus.on,
            )

    def test_update_rule_partial(self):
        r = RuleUpdate(threshold=25.0)
        assert r.threshold == 25.0
        assert r.name is None


class TestCropSchema:
    def test_create_valid_crop(self):
        c = CropCreate(name="Wheat", description="Winter wheat")
        assert c.name == "Wheat"
        assert c.description == "Winter wheat"

    def test_create_crop_empty_name(self):
        with pytest.raises(ValidationError):
            CropCreate(name="")

    def test_create_crop_long_name(self):
        with pytest.raises(ValidationError):
            CropCreate(name="a" * 101)

    def test_update_crop(self):
        c = CropUpdate(growth_stage="flowering")
        assert c.growth_stage == "flowering"
        assert c.name is None


class TestTaskSchema:
    def test_create_valid_task(self):
        t = TaskCreate(title="Water plants", description="Water all plants")
        assert t.title == "Water plants"
        assert t.status == TaskStatus.pending

    def test_create_task_empty_title(self):
        with pytest.raises(ValidationError):
            TaskCreate(title="")

    def test_create_task_long_title(self):
        with pytest.raises(ValidationError):
            TaskCreate(title="a" * 101)

    def test_update_task_status(self):
        t = TaskUpdate(status=TaskStatus.done)
        assert t.status == TaskStatus.done
        assert t.title is None


class TestClassroomSchema:
    def test_create_valid_classroom(self):
        c = ClassroomCreate(name="Class 1", subject=CourseSubject.labor)
        assert c.name == "Class 1"
        assert c.subject == CourseSubject.labor
        assert c.teacher_id is None

    def test_create_classroom_empty_name(self):
        with pytest.raises(ValidationError):
            ClassroomCreate(name="", subject=CourseSubject.labor)

    def test_create_classroom_long_name(self):
        with pytest.raises(ValidationError):
            ClassroomCreate(name="a" * 101, subject=CourseSubject.labor)

    def test_update_classroom_partial(self):
        u = ClassroomUpdate(name="New Name")
        assert u.name == "New Name"
        assert u.subject is None


class TestGroupSchema:
    def test_create_valid_group(self):
        g = GroupCreate(name="Group 1", class_id=1, node_id=1)
        assert g.name == "Group 1"
        assert g.class_id == 1
        assert g.node_id == 1

    def test_create_group_empty_name(self):
        with pytest.raises(ValidationError):
            GroupCreate(name="", class_id=1)

    def test_create_group_invalid_class_id(self):
        with pytest.raises(ValidationError):
            GroupCreate(name="Group 1", class_id=0)

    def test_update_group_partial(self):
        u = GroupUpdate(name="New Group")
        assert u.name == "New Group"
        assert u.node_id is None


class TestBatchStudentSchema:
    def test_create_valid_batch(self):
        b = BatchStudentCreate(group_id=1, count=5, password="Student123")
        assert b.group_id == 1
        assert b.count == 5
        assert b.password == "Student123"

    def test_create_batch_zero_count(self):
        with pytest.raises(ValidationError):
            BatchStudentCreate(group_id=1, count=0, password="Student123")

    def test_create_batch_too_many(self):
        with pytest.raises(ValidationError):
            BatchStudentCreate(group_id=1, count=51, password="Student123")

    def test_create_batch_short_password(self):
        with pytest.raises(ValidationError):
            BatchStudentCreate(group_id=1, count=1, password="short1")

    def test_create_batch_password_no_digit(self):
        with pytest.raises(ValidationError):
            BatchStudentCreate(group_id=1, count=1, password="students")


class TestTaskSubmissionSchema:
    def test_create_valid_submission(self):
        s = TaskSubmissionCreate(content="My observation notes")
        assert s.content == "My observation notes"

    def test_create_submission_no_content(self):
        s = TaskSubmissionCreate()
        assert s.content is None

    def test_create_submission_long_content(self):
        with pytest.raises(ValidationError):
            TaskSubmissionCreate(content="a" * 501)

    def test_review_valid(self):
        r = SubmissionReview(score=88, feedback="Good work")
        assert r.score == 88
        assert r.feedback == "Good work"

    def test_review_invalid_score_too_low(self):
        with pytest.raises(ValidationError):
            SubmissionReview(score=-1)

    def test_review_invalid_score_too_high(self):
        with pytest.raises(ValidationError):
            SubmissionReview(score=101)

    def test_review_long_feedback(self):
        with pytest.raises(ValidationError):
            SubmissionReview(score=85, feedback="a" * 256)


class TestExperimentSchema:
    def test_create_valid_experiment(self):
        from app.schemas.experiment import ExperimentCreate
        from datetime import date
        e = ExperimentCreate(
            class_id=1, title="光照实验", hypothesis="增加光照会加速生长",
            variable_metric="light_intensity",
            start_date=date.today(), end_date=date.today(),
        )
        assert e.title == "光照实验"
        assert e.status.value == "ongoing"

    def test_create_experiment_empty_title(self):
        from app.schemas.experiment import ExperimentCreate
        from datetime import date
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ExperimentCreate(
                class_id=1, title="", hypothesis="Test",
                variable_metric="air_temp",
                start_date=date.today(), end_date=date.today(),
            )

    def test_create_experiment_long_title(self):
        from app.schemas.experiment import ExperimentCreate
        from datetime import date
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ExperimentCreate(
                class_id=1, title="a" * 101, hypothesis="Test",
                variable_metric="air_temp",
                start_date=date.today(), end_date=date.today(),
            )

    def test_experiment_update_partial(self):
        from app.schemas.experiment import ExperimentUpdate
        u = ExperimentUpdate(status="completed")
        assert u.status.value == "completed"
        assert u.title is None

    def test_experiment_group_create_valid(self):
        from app.schemas.experiment import ExperimentGroupCreate
        eg = ExperimentGroupCreate(group_id=1, role="experimental")
        assert eg.group_id == 1
        assert eg.role.value == "experimental"

    def test_observation_create_valid(self):
        from app.schemas.experiment import ExperimentObservationCreate
        o = ExperimentObservationCreate(content="叶片颜色正常")
        assert o.content == "叶片颜色正常"


class TestEnums:
    def test_user_role_values(self):
        assert UserRole.admin.value == "admin"
        assert UserRole.teacher.value == "teacher"
        assert UserRole.operator.value == "operator"
        assert UserRole.student.value == "student"

    def test_component_type_values(self):
        assert ComponentType.fan.value == "fan"
        assert ComponentType.pump.value == "pump"
        assert ComponentType.light.value == "light"
        assert ComponentType.sensor.value == "sensor"

    def test_component_status_values(self):
        assert ComponentStatus.on.value == "on"
        assert ComponentStatus.off.value == "off"
        assert ComponentStatus.auto.value == "auto"

    def test_rule_operator_values(self):
        assert RuleOperator.gt.value == ">"
        assert RuleOperator.lt.value == "<"

    def test_sensor_metric_count(self):
        assert len(list(SensorMetric)) == 6

    def test_task_status_values(self):
        assert TaskStatus.pending.value == "pending"
        assert TaskStatus.in_progress.value == "in_progress"
        assert TaskStatus.done.value == "done"

    def test_course_subject_values(self):
        assert CourseSubject.labor.value == "labor"
        assert CourseSubject.science.value == "science"

    def test_task_type_values(self):
        assert TaskType.observation.value == "observation"
        assert TaskType.experiment.value == "experiment"
        assert TaskType.maintenance.value == "maintenance"

    def test_experiment_status_values(self):
        assert ExperimentStatus.ongoing.value == "ongoing"
        assert ExperimentStatus.completed.value == "completed"

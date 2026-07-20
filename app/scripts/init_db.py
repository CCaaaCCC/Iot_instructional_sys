from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    ClassTask,
    Classroom,
    Component,
    Crop,
    DeviceNode,
    DeviceToken,
    Rule,
    SensorData,
    User,
)
from app.models.enums import (
    ComponentStatus,
    ComponentType,
    CourseSubject,
    DeviceType,
    RuleOperator,
    SensorMetric,
    TaskStatus,
    TaskType,
    UserRole,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    # Migrate task_submissions.content from NOT NULL to NULL (SQLite)
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('task_submissions')")
        columns = {row[1]: row for row in result}
        content_col = columns.get("content")
        if content_col is not None and content_col[3] == 1:  # notnull=1
            conn.exec_driver_sql("BEGIN TRANSACTION")
            conn.exec_driver_sql("""
                CREATE TABLE task_submissions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL REFERENCES class_tasks(id),
                    student_id INTEGER NOT NULL REFERENCES users(id),
                    content VARCHAR(500),
                    image_url VARCHAR(255),
                    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    score INTEGER,
                    feedback VARCHAR(255),
                    reviewed_at DATETIME,
                    reviewed_by INTEGER REFERENCES users(id)
                )
            """)
            conn.exec_driver_sql(
                "INSERT INTO task_submissions_new SELECT id, task_id, student_id, content, "
                "image_url, submitted_at, score, feedback, reviewed_at, reviewed_by "
                "FROM task_submissions"
            )
            conn.exec_driver_sql("DROP TABLE task_submissions")
            conn.exec_driver_sql(
                "ALTER TABLE task_submissions_new RENAME TO task_submissions"
            )
            conn.exec_driver_sql("COMMIT")

    # Migrate experiments: add updated_at column if missing
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('experiments')")
        col_names = {row[1] for row in result}
        if "updated_at" not in col_names:
            conn.exec_driver_sql(
                "ALTER TABLE experiments ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )
            conn.commit()

    # Migrate courseware: add preview_url column if missing
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('courseware')")
        col_names = {row[1] for row in result}
        if "preview_url" not in col_names:
            conn.exec_driver_sql(
                "ALTER TABLE courseware ADD COLUMN preview_url VARCHAR(255)"
            )
            conn.commit()

    # Migrate teaching_resources: add preview_url column if missing
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('teaching_resources')")
        col_names = {row[1] for row in result}
        if "preview_url" not in col_names:
            conn.exec_driver_sql(
                "ALTER TABLE teaching_resources ADD COLUMN preview_url VARCHAR(255)"
            )
            conn.commit()

    with SessionLocal() as db:
        admin = db.execute(
            select(User).where(User.username == settings.INIT_ADMIN_USERNAME)
        ).scalar_one_or_none()
        if not admin:
            admin = User(
                username=settings.INIT_ADMIN_USERNAME,
                hashed_password=get_password_hash(settings.INIT_ADMIN_PASSWORD),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
        if not settings.INIT_SAMPLE_DATA:
            return

        teacher = db.execute(select(User).where(User.username == "teacher")).scalar_one_or_none()
        if not teacher:
            teacher = User(
                username="teacher",
                hashed_password=get_password_hash("Teacher123456"),
                role=UserRole.teacher,
                is_active=True,
                display_name="王老师",
            )
            db.add(teacher)
            db.commit()
            db.refresh(teacher)

        operator = db.execute(select(User).where(User.username == "operator")).scalar_one_or_none()
        if not operator:
            operator = User(
                username="operator",
                hashed_password=get_password_hash("Operator123456"),
                role=UserRole.operator,
                is_active=True,
                display_name="大棚管理员",
            )
            db.add(operator)
            db.commit()
            db.refresh(operator)

        if db.execute(select(DeviceNode)).first() is None:
            nodes = [
                DeviceNode(name="Node-A", location="A区1号棚", online=True),
                DeviceNode(name="Node-B", location="A区2号棚", online=True),
                DeviceNode(name="Node-C", location="B区1号棚", online=False),
            ]
            db.add_all(nodes)
            db.commit()
            for n in nodes:
                db.refresh(n)

            components = [
                Component(node_id=1, name="温湿度传感器", type=ComponentType.sensor, status=ComponentStatus.on),
                Component(node_id=1, name="风扇", type=ComponentType.fan, status=ComponentStatus.off),
                Component(node_id=1, name="水泵", type=ComponentType.pump, status=ComponentStatus.off),
                Component(node_id=1, name="补光灯", type=ComponentType.light, status=ComponentStatus.off),
                Component(node_id=2, name="温湿度传感器", type=ComponentType.sensor, status=ComponentStatus.on),
                Component(node_id=2, name="风扇", type=ComponentType.fan, status=ComponentStatus.off),
                Component(node_id=2, name="水泵", type=ComponentType.pump, status=ComponentStatus.off),
                Component(node_id=2, name="补光灯", type=ComponentType.light, status=ComponentStatus.on),
                Component(node_id=3, name="温湿度传感器", type=ComponentType.sensor, status=ComponentStatus.off),
                Component(node_id=3, name="风扇", type=ComponentType.fan, status=ComponentStatus.off),
                Component(node_id=3, name="水泵", type=ComponentType.pump, status=ComponentStatus.off),
            ]
            db.add_all(components)
            db.commit()
            for c in components:
                db.refresh(c)

        if db.execute(select(Classroom)).first() is None:
            classroom = Classroom(
                name="五(3)班",
                teacher_id=teacher.id,
                subject=CourseSubject.labor,
            )
            db.add(classroom)
            db.commit()
            db.refresh(classroom)

            from app.models.group import Group
            g1 = Group(name="第1组", class_id=classroom.id, node_id=1)
            g2 = Group(name="第2组", class_id=classroom.id, node_id=2)
            g3 = Group(name="第3组", class_id=classroom.id, node_id=3)
            db.add_all([g1, g2, g3])
            db.commit()
            for g in [g1, g2, g3]:
                db.refresh(g)

            students = [
                User(
                    username="g1s1",
                    hashed_password=get_password_hash("Student123456"),
                    role=UserRole.student,
                    is_active=True,
                    display_name="张小明",
                    group_id=g1.id,
                ),
                User(
                    username="g1s2",
                    hashed_password=get_password_hash("Student123456"),
                    role=UserRole.student,
                    is_active=True,
                    display_name="李小红",
                    group_id=g1.id,
                ),
                User(
                    username="g2s1",
                    hashed_password=get_password_hash("Student123456"),
                    role=UserRole.student,
                    is_active=True,
                    display_name="王大力",
                    group_id=g2.id,
                ),
                User(
                    username="g3s1",
                    hashed_password=get_password_hash("Student123456"),
                    role=UserRole.student,
                    is_active=True,
                    display_name="刘小华",
                    group_id=g3.id,
                ),
            ]
            db.add_all(students)
            db.commit()

        if db.execute(select(Rule)).first() is None:
            rules = [
                Rule(
                    name="High Temp -> Fan On",
                    metric=SensorMetric.air_temp,
                    operator=RuleOperator.gt,
                    threshold=30.0,
                    action_component_type=ComponentType.fan,
                    action=ComponentStatus.on,
                    enabled=True,
                    description="Auto turn on fan when air temp above 30C",
                ),
                Rule(
                    name="Low Soil Humidity -> Pump On",
                    metric=SensorMetric.soil_humidity,
                    operator=RuleOperator.lt,
                    threshold=40.0,
                    action_component_type=ComponentType.pump,
                    action=ComponentStatus.on,
                    enabled=True,
                    description="Auto water when soil humidity is low",
                ),
            ]
            db.add_all(rules)
            db.commit()

        if db.execute(select(Crop)).first() is None:
            from app.models.group import Group
            g1 = db.execute(select(Group).where(Group.name == "第1组")).scalar_one()
            g2 = db.execute(select(Group).where(Group.name == "第2组")).scalar_one()
            crops = [
                Crop(
                    name="番茄",
                    description="樱桃番茄",
                    growth_stage="开花期",
                    start_date=datetime.now().date() - timedelta(days=45),
                    group_id=g1.id,
                ),
                Crop(
                    name="生菜",
                    description="绿叶生菜",
                    growth_stage="生长期",
                    start_date=datetime.now().date() - timedelta(days=15),
                    group_id=g2.id,
                ),
            ]
            db.add_all(crops)
            db.commit()

        if db.execute(select(ClassTask)).first() is None:
            from app.models.group import Group
            g1 = db.execute(select(Group).where(Group.name == "第1组")).scalar_one()
            tasks = [
                ClassTask(
                    title="观察番茄生长状态",
                    description="记录番茄叶片颜色、高度变化，拍照上传",
                    assigned_date=datetime.now().date(),
                    due_date=datetime.now().date() + timedelta(days=7),
                    status=TaskStatus.pending,
                    created_by=teacher.id,
                    group_id=g1.id,
                    course_subject=CourseSubject.labor,
                    task_type=TaskType.observation,
                ),
                ClassTask(
                    title="测量土壤湿度",
                    description="使用传感器读取土壤湿度数据并记录",
                    assigned_date=datetime.now().date(),
                    due_date=datetime.now().date() + timedelta(days=3),
                    status=TaskStatus.in_progress,
                    created_by=teacher.id,
                    group_id=g1.id,
                    course_subject=CourseSubject.labor,
                    task_type=TaskType.maintenance,
                ),
            ]
            db.add_all(tasks)
            db.commit()

        if db.execute(select(SensorData)).first() is None:
            now = datetime.now()
            samples = []
            for offset in range(5):
                samples.append(
                    SensorData(
                        node_id=1,
                        air_temp=24.0 + offset,
                        air_humidity=55.0 - offset,
                        soil_temp=20.0 + offset * 0.5,
                        soil_humidity=50.0 - offset * 2,
                        light_intensity=300.0 + offset * 15,
                        soil_ph=6.5,
                        recorded_at=now - timedelta(hours=4 - offset),
                    )
                )
            for offset in range(3):
                samples.append(
                    SensorData(
                        node_id=2,
                        air_temp=26.0 + offset,
                        air_humidity=58.0 - offset,
                        soil_temp=21.0 + offset * 0.5,
                        soil_humidity=48.0 - offset * 2,
                        light_intensity=800.0 + offset * 10,
                        soil_ph=6.8,
                        recorded_at=now - timedelta(hours=2 - offset),
                    )
                )
            db.add_all(samples)
            db.commit()

        # 设备令牌种子数据：第1组的 3 个设备各持一个 token（固定值便于演示）
        if db.execute(select(DeviceToken)).first() is None:
            from app.models.group import Group

            g1 = db.execute(select(Group).where(Group.name == "第1组")).scalar_one_or_none()
            if g1 is not None:
                tokens = [
                    DeviceToken(
                        token="esp32_g1_demo_token_seed_0001",
                        group_id=g1.id,
                        device_type=DeviceType.esp32,
                        device_name="第1组-ESP32主控",
                        node_id=1,
                        is_active=True,
                    ),
                    DeviceToken(
                        token="esp32cam_g1_demo_token_seed_0001",
                        group_id=g1.id,
                        device_type=DeviceType.esp32cam,
                        device_name="第1组-ESP32-CAM视觉",
                        node_id=1,
                        is_active=True,
                    ),
                    DeviceToken(
                        token="esp32s3_g1_demo_token_seed_0001",
                        group_id=g1.id,
                        device_type=DeviceType.esp32s3,
                        device_name="第1组-ESP32-S3小智",
                        node_id=1,
                        is_active=True,
                    ),
                ]
                db.add_all(tokens)
                db.commit()

        # 启动时清理过期的 MCP 调用日志（expires_at < now）
        try:
            from app.services import mcp_service

            cleaned = mcp_service.cleanup_expired_mcp_logs(db)
            if cleaned > 0:
                print(f"[init_db] Cleaned up {cleaned} expired MCP call logs")
        except Exception as e:
            # 清理失败不应阻断启动
            print(f"[init_db] MCP log cleanup skipped: {e}")

        # 启动时清理超过 180 天的 AI 对话会话（级联删除消息）
        try:
            from app.services import ai_service

            cleaned_ai = ai_service.cleanup_old_sessions(db)
            if cleaned_ai > 0:
                print(f"[init_db] Cleaned up {cleaned_ai} old AI chat sessions")
        except Exception as e:
            # 清理失败不应阻断启动
            print(f"[init_db] AI session cleanup skipped: {e}")


if __name__ == "__main__":
    init_db()

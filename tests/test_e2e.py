import pytest
from datetime import datetime, timedelta
import io


class TestE2EAuthFlow:
    def test_login_and_use_token(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "admin", "password": "Admin123456"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_teacher_login_limited_access(self, client, auth_headers):
        client.patch("/api/v1/users/2", json={
            "password": "Teacher123456"
        }, headers=auth_headers)

        resp = client.post("/api/v1/auth/login", data={
            "username": "teacher", "password": "Teacher123456"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/device-nodes", headers=headers)
        assert resp.status_code == 200

        resp = client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 403

    def test_operator_login_limited_access(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "operator", "password": "Operator123456"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/device-nodes", headers=headers)
        assert resp.status_code == 200

        resp = client.post("/api/v1/device-nodes/1/components/1/control", json={
            "action": "on"
        }, headers=headers)
        assert resp.status_code == 200

        resp = client.post("/api/v1/device-nodes", json={
            "name": "OpForbiddenNode", "location": "Zone"
        }, headers=headers)
        assert resp.status_code == 403

    def test_student_login_can_submit(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "g1s1", "password": "Student123456"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/student/me/tasks", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestE2EDeviceNodeCRUD:
    def test_node_full_lifecycle(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes", json={
            "name": "E2E-Node", "location": "E2E Zone"
        }, headers=auth_headers)
        assert resp.status_code == 201
        node = resp.json()
        node_id = node["id"]
        assert node["name"] == "E2E-Node"

        resp = client.get(f"/api/v1/device-nodes/{node_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "E2E-Node"

        resp = client.patch(f"/api/v1/device-nodes/{node_id}", json={
            "location": "Updated Zone"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["location"] == "Updated Zone"


class TestE2EComponentCRUD:
    def test_component_full_lifecycle(self, client, auth_headers):
        create_node = client.post("/api/v1/device-nodes", json={
            "name": "CompTestNode", "location": "Comp Zone"
        }, headers=auth_headers)
        node_id = create_node.json()["id"]

        resp = client.post(f"/api/v1/device-nodes/{node_id}/components", json={
            "name": "E2E-Fan", "type": "fan"
        }, headers=auth_headers)
        assert resp.status_code == 201
        component = resp.json()
        component_id = component["id"]
        assert component["name"] == "E2E-Fan"
        assert component["status"] == "off"

        resp = client.patch(f"/api/v1/device-nodes/{node_id}/components/{component_id}", json={
            "name": "E2E-Fan-Renamed"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "E2E-Fan-Renamed"

        resp = client.post(
            f"/api/v1/device-nodes/{node_id}/components/{component_id}/control",
            json={"action": "on", "message": "E2E test"},
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "on"

        resp = client.get(f"/api/v1/device-nodes/{node_id}/logs", headers=auth_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert any(log["action"] == "on" for log in logs)


class TestE2ESensorDataFlow:
    def test_sensor_data_flow_and_rules(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1,
            "air_temp": 35.0,
            "air_humidity": 40.0,
            "soil_temp": 25.0,
            "soil_humidity": 30.0,
            "light_intensity": 500.0,
            "soil_ph": 6.5,
        }, headers=auth_headers)
        assert resp.status_code == 201
        sensor_data = resp.json()
        assert sensor_data["air_temp"] == 35.0

        resp = client.get("/api/v1/sensors/data/latest?node_id=1", headers=auth_headers)
        assert resp.status_code == 200
        latest = resp.json()
        assert latest["air_temp"] == 35.0

        resp = client.get("/api/v1/sensors/data/echarts?node_id=1&limit=5", headers=auth_headers)
        assert resp.status_code == 200
        echarts = resp.json()
        assert len(echarts["x"]) > 0
        assert len(echarts["series"]) > 0

    def test_multiple_sensor_readings(self, client, auth_headers):
        now = datetime.now()
        for i in range(5):
            resp = client.post("/api/v1/sensors/data", json={
                "node_id": 1,
                "air_temp": 25.0 + i,
                "air_humidity": 60.0 - i,
                "soil_temp": 20.0 + i * 0.5,
                "soil_humidity": 50.0 - i * 2,
                "light_intensity": 300.0 + i * 10,
                "soil_ph": 6.5 + i * 0.1,
                "recorded_at": (now - timedelta(hours=i)).isoformat(),
            }, headers=auth_headers)
            assert resp.status_code == 201

        resp = client.get("/api/v1/sensors/data?node_id=1&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5


class TestE2ECropFlow:
    def test_crop_full_lifecycle(self, client, auth_headers):
        resp = client.post("/api/v1/crops", json={
            "name": "E2E-Pepper",
            "description": "Bell pepper",
            "growth_stage": "seedling",
            "start_date": datetime.now().date().isoformat(),
            "group_id": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        crop = resp.json()
        crop_id = crop["id"]
        assert crop["name"] == "E2E-Pepper"

        resp = client.get(f"/api/v1/crops/{crop_id}", headers=auth_headers)
        assert resp.status_code == 200

        resp = client.patch(f"/api/v1/crops/{crop_id}", json={
            "growth_stage": "growing",
            "notes": "Growing well",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["growth_stage"] == "growing"
        assert resp.json()["notes"] == "Growing well"


class TestE2ETaskFlow:
    def test_task_full_lifecycle(self, client, auth_headers):
        resp = client.post("/api/v1/tasks", json={
            "title": "E2E Inspection",
            "description": "Check all sensors",
            "assigned_date": datetime.now().date().isoformat(),
            "due_date": (datetime.now().date() + timedelta(days=7)).isoformat(),
            "status": "pending",
            "group_id": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        task = resp.json()
        task_id = task["id"]
        assert task["title"] == "E2E Inspection"
        assert task["status"] == "pending"

        resp = client.patch(f"/api/v1/tasks/{task_id}", json={
            "status": "in_progress"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

        resp = client.patch(f"/api/v1/tasks/{task_id}", json={
            "status": "done"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"


class TestE2ESubmissionFlow:
    def test_student_submit_and_teacher_review(self, client, auth_headers, student_headers):
        resp = client.post("/api/v1/submissions?task_id=1", data={
            "content": "E2E observation submission"
        }, headers=student_headers)
        assert resp.status_code == 201
        submission = resp.json()
        submission_id = submission["id"]
        assert submission["score"] is None

        resp = client.get(f"/api/v1/submissions/{submission_id}", headers=auth_headers)
        assert resp.status_code == 200

        resp = client.post(f"/api/v1/submissions/{submission_id}/review", json={
            "score": 92, "feedback": "Excellent work!"
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 92
        assert data["feedback"] == "Excellent work!"
        assert data["reviewed_at"] is not None
        assert data["reviewed_by"] == 1

        resp = client.get("/api/v1/submissions?reviewed=true", headers=auth_headers)
        assert resp.status_code == 200
        reviewed = resp.json()
        assert any(s["id"] == submission_id for s in reviewed)


class TestE2EClassroomFlow:
    def test_classroom_group_student_lifecycle(self, client, auth_headers):
        resp = client.post("/api/v1/classrooms", json={
            "name": "E2E Class", "subject": "science"
        }, headers=auth_headers)
        assert resp.status_code == 201
        classroom = resp.json()
        class_id = classroom["id"]

        resp = client.post("/api/v1/groups", json={
            "name": "E2E Group", "class_id": class_id
        }, headers=auth_headers)
        assert resp.status_code == 201
        group = resp.json()
        group_id = group["id"]

        resp = client.post(f"/api/v1/groups/{group_id}/students/batch", json={
            "group_id": group_id, "count": 3, "password": "E2Epass123"
        }, headers=auth_headers)
        assert resp.status_code == 201
        students = resp.json()
        assert len(students) == 3
        assert students[0]["username"] == f"g{group_id}s1"
        assert students[1]["username"] == f"g{group_id}s2"
        assert students[2]["username"] == f"g{group_id}s3"

        resp = client.get(f"/api/v1/groups/{group_id}/students", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

        create_node = client.post("/api/v1/device-nodes", json={
            "name": "E2E-Bind-Node", "location": "E2E Zone"
        }, headers=auth_headers)
        node_id = create_node.json()["id"]
        resp = client.post(f"/api/v1/groups/{group_id}/bind-node?node_id={node_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["node_id"] == node_id


class TestE2ERuleEngine:
    def test_rule_triggered_by_sensor_data(self, client, auth_headers):
        resp = client.post("/api/v1/rules", json={
            "name": "E2E-High-Humidity-Pump",
            "metric": "air_humidity",
            "operator": ">",
            "threshold": 80.0,
            "action_component_type": "pump",
            "action": "on",
            "enabled": True,
            "description": "E2E test rule",
        }, headers=auth_headers)
        assert resp.status_code == 201
        rule = resp.json()
        assert rule["enabled"] is True

        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1,
            "air_temp": 30.0,
            "air_humidity": 85.0,
        }, headers=auth_headers)
        assert resp.status_code == 201

        resp = client.get("/api/v1/rules/logs", headers=auth_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert isinstance(logs, list)
        assert len(logs) > 0, "Rule should have generated log entries after trigger"
        assert any(log["rule_id"] == rule["id"] for log in logs), "Log should reference the triggered rule"

        resp = client.patch(f"/api/v1/rules/{rule['id']}", json={
            "enabled": False
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False


class TestE2EUserManagement:
    def test_admin_creates_manages_user(self, client, auth_headers):
        resp = client.post("/api/v1/users", json={
            "username": "e2e_user",
            "password": "e2epass1234",
            "role": "operator",
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        user = resp.json()
        assert user["username"] == "e2e_user"
        assert user["role"] == "operator"
        user_id = user["id"]

        resp = client.patch(f"/api/v1/users/{user_id}", json={
            "role": "teacher",
            "is_active": False,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "teacher"
        assert resp.json()["is_active"] is False

        resp = client.post("/api/v1/auth/login", data={
            "username": "e2e_user", "password": "e2epass1234"
        })
        assert resp.status_code == 400


class TestE2EDashboardFlow:
    def test_dashboard_reflects_changes(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/overview", headers=auth_headers)
        assert resp.status_code == 200
        overview = resp.json()
        assert overview["total_nodes"] >= 0
        assert overview["total_rules"] >= 0
        assert overview["total_tasks"] >= 0

        resp = client.get("/api/v1/dashboard/component-summary", headers=auth_headers)
        assert resp.status_code == 200
        summary = resp.json()
        assert isinstance(summary, list)


class TestE2EBoundaryConditions:
    def test_concurrent_sensor_data(self, client, auth_headers):
        for i in range(10):
            resp = client.post("/api/v1/sensors/data", json={
                "node_id": 1,
                "air_temp": 20.0 + i,
                "air_humidity": 50.0 + i,
                "soil_temp": 15.0 + i * 0.3,
                "soil_humidity": 30.0 + i,
                "light_intensity": 100.0 + i * 50,
                "soil_ph": 5.5 + i * 0.1,
            }, headers=auth_headers)
            assert resp.status_code == 201

        resp = client.get("/api/v1/sensors/data?limit=20", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 10

    def test_empty_list_responses(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes?online=true", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_max_values_accepted(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1,
            "air_temp": 80.0,
            "air_humidity": 100.0,
            "soil_temp": 60.0,
            "soil_humidity": 100.0,
            "light_intensity": 2000.0,
            "soil_ph": 14.0,
        }, headers=auth_headers)
        assert resp.status_code == 201

    def test_min_values_accepted(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1,
            "air_temp": -50.0,
            "air_humidity": 0.0,
            "soil_temp": -30.0,
            "soil_humidity": 0.0,
            "light_intensity": 0.0,
            "soil_ph": 0.0,
        }, headers=auth_headers)
        assert resp.status_code == 201


class TestE2ESecurity:
    def test_login_rate_limit_locks_after_5_failures(self, client):
        for _ in range(5):
            resp = client.post("/api/v1/auth/login", data={
                "username": "admin",
                "password": "wrong_password_123"
            })
            assert resp.status_code in (400, 401)

        resp = client.post("/api/v1/auth/login", data={
            "username": "admin",
            "password": "Admin123456"
        })
        assert resp.status_code == 429

    def test_student_cannot_submit_other_group_task(self, client, auth_headers, student_headers):
        create_class = client.post("/api/v1/classrooms", json={
            "name": "Other Class",
            "teacher_id": 2,
            "subject": "science"
        }, headers=auth_headers)
        assert create_class.status_code == 201
        other_class_id = create_class.json()["id"]

        create_group = client.post("/api/v1/groups", json={
            "name": "Other Group",
            "class_id": other_class_id
        }, headers=auth_headers)
        assert create_group.status_code == 201
        other_group_id = create_group.json()["id"]

        create_task = client.post("/api/v1/tasks", json={
            "title": "Other Group Task",
            "description": "Task for another group",
            "status": "in_progress",
            "group_id": other_group_id,
            "course_subject": "science",
            "task_type": "observation"
        }, headers=auth_headers)
        assert create_task.status_code == 201
        other_task_id = create_task.json()["id"]

        resp = client.post(
            f"/api/v1/student/me/tasks/{other_task_id}/submit",
            data={"content": "attempted submission"},
            headers=student_headers
        )
        assert resp.status_code == 403


class TestE2EStudentECharts:
    def test_student_echarts_endpoint(self, client, student_headers):
        resp = client.get("/api/v1/student/me/sensor-data/echarts", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "x" in data
        assert "series" in data
        assert isinstance(data["x"], list)
        assert isinstance(data["series"], list)
        assert len(data["x"]) > 0, "Should have at least one data point from seed data"

    def test_student_echarts_with_metrics_filter(self, client, student_headers):
        resp = client.get(
            "/api/v1/student/me/sensor-data/echarts?metrics=air_temp&metrics=air_humidity",
            headers=student_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["series"]) == 2
        names = [s["name"] for s in data["series"]]
        assert "air_temp" in names
        assert "air_humidity" in names

    def test_teacher_cannot_access_student_echarts(self, client, teacher_headers):
        resp = client.get("/api/v1/student/me/sensor-data/echarts", headers=teacher_headers)
        assert resp.status_code == 403


class TestE2EStudentProfile:
    def test_student_update_profile(self, client, student_headers):
        resp = client.patch("/api/v1/student/me/profile", json={
            "display_name": "Updated Name",
            "avatar_url": "/avatars/test.jpg",
        }, headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Updated Name"
        assert data["avatar_url"] == "/avatars/test.jpg"

    def test_student_update_profile_partial(self, client, student_headers):
        resp = client.patch("/api/v1/student/me/profile", json={
            "display_name": "Only Name Changed",
        }, headers=student_headers)
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Only Name Changed"

    def test_teacher_cannot_access_student_profile(self, client, teacher_headers):
        resp = client.patch("/api/v1/student/me/profile", json={
            "display_name": "Hijack",
        }, headers=teacher_headers)
        assert resp.status_code == 403


class TestE2EStudentPasswordChange:
    def test_student_change_password_success(self, client, student_headers):
        resp = client.patch("/api/v1/student/me/password", json={
            "old_password": "Student123456",
            "new_password": "NewPass123456",
        }, headers=student_headers)
        assert resp.status_code == 200

        resp = client.post("/api/v1/auth/login", data={
            "username": "g1s1",
            "password": "NewPass123456",
        })
        assert resp.status_code == 200

    def test_student_change_password_wrong_old(self, client, student_headers):
        resp = client.patch("/api/v1/student/me/password", json={
            "old_password": "WrongOldPassword1",
            "new_password": "NewPass123456",
        }, headers=student_headers)
        assert resp.status_code == 400

    def test_student_change_password_weak_new(self, client, student_headers):
        resp = client.patch("/api/v1/student/me/password", json={
            "old_password": "Student123456",
            "new_password": "weak",
        }, headers=student_headers)
        assert resp.status_code == 422

    def test_teacher_cannot_access_student_password(self, client, teacher_headers):
        resp = client.patch("/api/v1/student/me/password", json={
            "old_password": "x",
            "new_password": "NewPass123456",
        }, headers=teacher_headers)
        assert resp.status_code == 403


class TestE2EStudentAvatar:
    def test_student_upload_avatar_success(self, client, student_headers):
        png_header = b"\x89PNG\r\n\x1a\n"
        fake_image = io.BytesIO(png_header + b"\x00" * 100)
        resp = client.post(
            "/api/v1/student/me/avatar",
            files={"file": ("avatar.png", fake_image, "image/png")},
            headers=student_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "avatar_url" in data
        assert data["avatar_url"].startswith("/avatars/")
        assert data["avatar_url"].endswith(".png")

        resp = client.get("/api/v1/auth/me", headers=student_headers)
        assert resp.json()["avatar_url"] == data["avatar_url"]

    def test_student_upload_avatar_invalid_type(self, client, student_headers):
        fake_text = io.BytesIO(b"not an image")
        resp = client.post(
            "/api/v1/student/me/avatar",
            files={"file": ("avatar.txt", fake_text, "text/plain")},
            headers=student_headers,
        )
        assert resp.status_code == 400

    def test_teacher_cannot_upload_avatar(self, client, teacher_headers):
        fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
        resp = client.post(
            "/api/v1/student/me/avatar",
            files={"file": ("avatar.png", fake_image, "image/png")},
            headers=teacher_headers,
        )
        assert resp.status_code == 403


class TestE2EExperimentFlow:
    def test_experiment_lifecycle(self, client, auth_headers, student_headers):
        # 1. 教师创建实验
        create = client.post("/api/v1/experiments", json={
            "class_id": 1, "title": "光照对植物生长的影响",
            "hypothesis": "更长的光照时间会促进生长",
            "variable_metric": "light_intensity",
            "start_date": "2026-03-01", "end_date": "2026-03-14",
        }, headers=auth_headers)
        assert create.status_code == 201
        exp_id = create.json()["id"]

        # 2. 分配实验组
        add_group = client.post(f"/api/v1/experiments/{exp_id}/groups", json={
            "group_id": 1, "role": "experimental",
            "variable_target": "每天光照 12 小时",
        }, headers=auth_headers)
        assert add_group.status_code == 201

        # 3. 学生查看实验
        student_resp = client.get("/api/v1/student/me/experiments", headers=student_headers)
        assert student_resp.status_code == 200
        assert any(e["id"] == exp_id for e in student_resp.json())

        # 4. 学生记录观察
        obs = client.post(f"/api/v1/student/me/experiments/{exp_id}/observations", json={
            "content": "第1天：叶片颜色正常，无明显变化"
        }, headers=student_headers)
        assert obs.status_code == 201
        assert obs.json()["content"] == "第1天：叶片颜色正常，无明显变化"

        # 5. 教师查看观察记录
        all_obs = client.get(f"/api/v1/experiments/{exp_id}/observations", headers=auth_headers)
        assert all_obs.status_code == 200
        assert len(all_obs.json()) > 0

        # 6. 教师完成实验
        complete = client.patch(f"/api/v1/experiments/{exp_id}", json={
            "status": "completed",
            "conclusion": "实验组植物比对照组高出约3厘米，证实假设成立"
        }, headers=auth_headers)
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

        # 7. 删除实验（级联删除 groups + observations）
        delete = client.delete(f"/api/v1/experiments/{exp_id}", headers=auth_headers)
        assert delete.status_code == 204

        # 8. 验证已删除
        gone = client.get(f"/api/v1/experiments/{exp_id}", headers=auth_headers)
        assert gone.status_code == 404

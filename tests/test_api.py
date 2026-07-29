import pytest
from datetime import datetime, timedelta

from app.models.enums import (
    UserRole, ComponentType, ComponentStatus, SensorMetric, RuleOperator, TaskStatus
)


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "mqtt" in data


class TestAuthAPI:
    def test_login_admin(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "admin", "password": "Admin123456"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "admin", "password": "wrong"
        })
        assert resp.status_code == 400

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "nobody", "password": "Admin123456"
        })
        assert resp.status_code == 400

    def test_login_inactive_user(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "inactive", "password": "Inactive123"
        })
        assert resp.status_code == 400

    def test_get_me(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_get_me_unauthorized(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401


class TestDeviceNodesAPI:
    def test_list_nodes(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all("name" in d for d in data)

    def test_list_nodes_filter_online(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes?online=true", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(d["online"] is True for d in data)

    def test_create_node(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes", json={
            "name": "NewNode", "location": "Zone B"
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "NewNode"
        assert data["location"] == "Zone B"

    def test_create_node_duplicate_name(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes", json={
            "name": "Node-1", "location": "Zone A"
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_node_empty_name(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes", json={
            "name": "", "location": "Zone A"
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_get_node(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Node-1"

    def test_get_node_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_node(self, client, auth_headers):
        resp = client.patch("/api/v1/device-nodes/1", json={
            "location": "New Location"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["location"] == "New Location"

    def test_delete_node(self, client, auth_headers):
        create = client.post("/api/v1/device-nodes", json={
            "name": "DeleteMe", "location": "Zone C"
        }, headers=auth_headers)
        node_id = create.json()["id"]
        resp = client.delete(f"/api/v1/device-nodes/{node_id}", headers=auth_headers)
        assert resp.status_code == 204


class TestComponentsAPI:
    def test_list_components(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes/1/components", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_list_components_filter_by_type(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes/1/components?component_type=fan", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["type"] == "fan" for c in data)

    def test_create_component(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes/1/components", json={
            "name": "NewFan", "type": "fan"
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "NewFan"
        assert data["type"] == "fan"

    def test_update_component(self, client, auth_headers):
        resp = client.patch("/api/v1/device-nodes/1/components/1", json={
            "name": "UpdatedFan"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "UpdatedFan"

    def test_control_component_on(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes/1/components/1/control", json={
            "action": "on", "message": "Test control"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "on"

    def test_control_component_off(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes/1/components/1/control", json={
            "action": "off"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "off"

    def test_control_component_auto(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes/1/components/1/control", json={
            "action": "auto"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "auto"

    def test_control_component_not_found(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes/1/components/9999/control", json={
            "action": "on"
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_get_node_logs(self, client, auth_headers):
        resp = client.get("/api/v1/device-nodes/1/logs", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestSensorsAPI:
    def test_create_sensor_data(self, client, auth_headers):
        now = datetime.now().isoformat()
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1,
            "air_temp": 28.5,
            "air_humidity": 65.0,
            "soil_humidity": 48.0,
            "light_intensity": 400.0,
            "soil_ph": 6.8,
            "co2": 600.0,
            "recorded_at": now,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["node_id"] == 1
        assert data["air_temp"] == 28.5

    def test_create_sensor_data_invalid_node(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 9999, "air_temp": 25.0
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_sensor_data_out_of_range_temp(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1, "air_temp": 100.0
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_sensor_data_out_of_range_humidity(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1, "air_humidity": 150.0
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_sensor_data_out_of_range_ph(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1, "soil_ph": 20.0
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_sensor_data_out_of_range_light(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1, "light_intensity": 200000.0
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_sensor_data_negative_node_id(self, client, auth_headers):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": -1, "air_temp": 25.0
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_list_sensor_data(self, client, auth_headers):
        resp = client.get("/api/v1/sensors/data", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_sensor_data_filter_by_node(self, client, auth_headers):
        resp = client.get("/api/v1/sensors/data?node_id=1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(d["node_id"] == 1 for d in data)

    def test_latest_sensor_data(self, client, auth_headers):
        resp = client.get("/api/v1/sensors/data/latest", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert "air_temp" in data

    def test_latest_sensor_data_by_node(self, client, auth_headers):
        resp = client.get("/api/v1/sensors/data/latest?node_id=1", headers=auth_headers)
        assert resp.status_code == 200

    def test_echarts_data(self, client, auth_headers):
        resp = client.get("/api/v1/sensors/data/echarts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "x" in data
        assert "series" in data

    def test_echarts_data_with_metrics(self, client, auth_headers):
        resp = client.get(
            "/api/v1/sensors/data/echarts?metrics=air_temp&metrics=air_humidity",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["series"]) == 2

    def test_unauthorized_sensor_data(self, client):
        resp = client.post("/api/v1/sensors/data", json={
            "node_id": 1, "air_temp": 25.0
        })
        assert resp.status_code == 401


class TestRulesAPI:
    def test_list_rules(self, client, auth_headers):
        resp = client.get("/api/v1/rules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_rule(self, client, auth_headers):
        resp = client.post("/api/v1/rules", json={
            "name": "Low Temp Heater",
            "metric": "air_temp",
            "operator": "<",
            "threshold": 15.0,
            "action_component_type": "light",
            "action": "on",
            "description": "Heat when cold",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Low Temp Heater"

    def test_create_rule_duplicate(self, client, auth_headers):
        resp = client.post("/api/v1/rules", json={
            "name": "High Temp Fan",
            "metric": "air_temp",
            "operator": ">",
            "threshold": 30.0,
            "action_component_type": "fan",
            "action": "on",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_rule_empty_name(self, client, auth_headers):
        resp = client.post("/api/v1/rules", json={
            "name": "",
            "metric": "air_temp",
            "operator": ">",
            "threshold": 30.0,
            "action_component_type": "fan",
            "action": "on",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_update_rule(self, client, auth_headers):
        resp = client.patch("/api/v1/rules/1", json={
            "threshold": 35.0,
            "enabled": False,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["threshold"] == 35.0
        assert resp.json()["enabled"] is False

    def test_toggle_rule(self, client, auth_headers):
        resp = client.post("/api/v1/rules/1/toggle", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_rule_logs(self, client, auth_headers):
        resp = client.get("/api/v1/rules/logs", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_rule_not_found(self, client, auth_headers):
        resp = client.patch("/api/v1/rules/9999", json={
            "threshold": 35.0
        }, headers=auth_headers)
        assert resp.status_code == 404


class TestCropsAPI:
    def test_list_crops(self, client, auth_headers):
        resp = client.get("/api/v1/crops", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_crop(self, client, auth_headers):
        resp = client.post("/api/v1/crops", json={
            "name": "Cucumber",
            "description": "Green cucumber",
            "growth_stage": "seedling",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Cucumber"

    def test_create_crop_duplicate(self, client, auth_headers):
        resp = client.post("/api/v1/crops", json={
            "name": "Tomato"
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_crop_empty_name(self, client, auth_headers):
        resp = client.post("/api/v1/crops", json={
            "name": ""
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_get_crop(self, client, auth_headers):
        resp = client.get("/api/v1/crops/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Tomato"

    def test_get_crop_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/crops/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_crop(self, client, auth_headers):
        resp = client.patch("/api/v1/crops/1", json={
            "growth_stage": "vegetative"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["growth_stage"] == "vegetative"


class TestTasksAPI:
    def test_list_tasks(self, client, auth_headers):
        resp = client.get("/api/v1/tasks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_tasks_filter_by_group(self, client, auth_headers):
        resp = client.get("/api/v1/tasks?group_id=1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["group_id"] == 1 for t in data)

    def test_create_task(self, client, auth_headers):
        resp = client.post("/api/v1/tasks", json={
            "title": "New Task",
            "description": "Do something",
            "status": "pending",
            "group_id": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["title"] == "New Task"

    def test_create_task_empty_title(self, client, auth_headers):
        resp = client.post("/api/v1/tasks", json={
            "title": ""
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_get_task(self, client, auth_headers):
        resp = client.get("/api/v1/tasks/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Task"

    def test_get_task_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/tasks/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_task_status(self, client, auth_headers):
        resp = client.patch("/api/v1/tasks/1", json={
            "status": "in_progress"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_update_task_to_done(self, client, auth_headers):
        resp = client.patch("/api/v1/tasks/1", json={
            "status": "done"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"


class TestClassroomsAPI:
    def test_list_classrooms(self, client, auth_headers):
        resp = client.get("/api/v1/classrooms", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_create_classroom(self, client, auth_headers):
        resp = client.post("/api/v1/classrooms", json={
            "name": "Science Class",
            "subject": "science"
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Science Class"
        assert resp.json()["subject"] == "science"

    def test_create_classroom_empty_name(self, client, auth_headers):
        resp = client.post("/api/v1/classrooms", json={
            "name": "", "subject": "labor"
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_get_classroom(self, client, auth_headers):
        resp = client.get("/api/v1/classrooms/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Class"

    def test_get_classroom_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/classrooms/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_classroom(self, client, auth_headers):
        resp = client.patch("/api/v1/classrooms/1", json={
            "name": "Updated Class"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Class"


class TestGroupsAPI:
    def test_list_groups(self, client, auth_headers):
        resp = client.get("/api/v1/groups", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_groups_filter_by_class(self, client, auth_headers):
        resp = client.get("/api/v1/groups?class_id=1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(g["class_id"] == 1 for g in data)

    def test_create_group(self, client, auth_headers):
        resp = client.post("/api/v1/groups", json={
            "name": "New Group",
            "class_id": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Group"

    def test_get_group(self, client, auth_headers):
        resp = client.get("/api/v1/groups/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Group-1"

    def test_get_group_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/groups/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_bind_node_to_group(self, client, auth_headers):
        create_node = client.post("/api/v1/device-nodes", json={
            "name": "BindTestNode", "location": "Zone X"
        }, headers=auth_headers)
        node_id = create_node.json()["id"]
        resp = client.post(f"/api/v1/groups/1/bind-node?node_id={node_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["node_id"] == node_id

    def test_unbind_node_from_group(self, client, auth_headers):
        resp = client.post("/api/v1/groups/1/unbind-node", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["node_id"] is None

    def test_list_students(self, client, auth_headers):
        resp = client.get("/api/v1/groups/1/students", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(s["username"] == "g1s1" for s in data)

    def test_batch_create_students(self, client, auth_headers):
        resp = client.post("/api/v1/groups/1/students/batch", json={
            "group_id": 1, "count": 2, "password": "Student123"
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 2
        assert data[0]["username"].startswith("g1s")
        assert data[0]["role"] == "student"

    def test_batch_create_students_group_mismatch(self, client, auth_headers):
        resp = client.post("/api/v1/groups/2/students/batch", json={
            "group_id": 1, "count": 1, "password": "Student123"
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_batch_create_students_invalid_password(self, client, auth_headers):
        resp = client.post("/api/v1/groups/1/students/batch", json={
            "group_id": 1, "count": 1, "password": "short1"
        }, headers=auth_headers)
        assert resp.status_code == 422


class TestSubmissionsAPI:
    def test_student_submit_task(self, client, student_headers):
        resp = client.post("/api/v1/submissions?task_id=1", data={
            "content": "My observation"
        }, headers=student_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "My observation"
        assert data["score"] is None

    def test_student_resubmit_updates(self, client, student_headers):
        client.post("/api/v1/submissions?task_id=1", data={
            "content": "First submission"
        }, headers=student_headers)
        resp = client.post("/api/v1/submissions?task_id=1", data={
            "content": "Updated submission"
        }, headers=student_headers)
        assert resp.status_code == 201
        assert resp.json()["content"] == "Updated submission"

    def test_list_submissions(self, client, auth_headers):
        resp = client.get("/api/v1/submissions", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_unreviewed_submissions(self, client, auth_headers, student_headers):
        client.post("/api/v1/submissions?task_id=1", data={
            "content": "Test submission"
        }, headers=student_headers)
        resp = client.get("/api/v1/submissions?reviewed=false", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["reviewed_at"] is None for s in data)

    def test_review_submission(self, client, auth_headers, student_headers):
        submit = client.post("/api/v1/submissions?task_id=1", data={
            "content": "Review me"
        }, headers=student_headers)
        submission_id = submit.json()["id"]
        resp = client.post(f"/api/v1/submissions/{submission_id}/review", json={
            "score": 88, "feedback": "Good work"
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 88
        assert data["feedback"] == "Good work"
        assert data["reviewed_at"] is not None

    def test_review_invalid_score(self, client, auth_headers, student_headers):
        submit = client.post("/api/v1/submissions?task_id=1", data={
            "content": "Bad score"
        }, headers=student_headers)
        submission_id = submit.json()["id"]
        resp = client.post(f"/api/v1/submissions/{submission_id}/review", json={
            "score": 101
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_student_cannot_review(self, client, student_headers):
        resp = client.post("/api/v1/submissions/1/review", json={
            "score": 85
        }, headers=student_headers)
        assert resp.status_code == 403


class TestStudentAPI:
    def test_student_my_group(self, client, student_headers, auth_headers):
        client.post("/api/v1/groups/1/bind-node?node_id=1", headers=auth_headers)
        resp = client.get("/api/v1/student/me/group", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["node_id"] == 1

    def test_student_my_tasks(self, client, student_headers):
        resp = client.get("/api/v1/student/me/tasks", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(t["id"] == 1 for t in data)

    def test_student_my_submissions(self, client, student_headers):
        client.post("/api/v1/student/me/tasks/1/submit", data={
            "content": "Student endpoint submit"
        }, headers=student_headers)
        resp = client.get("/api/v1/student/me/submissions", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(s["content"] == "Student endpoint submit" for s in data)

    def test_student_submit_task(self, client, student_headers):
        resp = client.post("/api/v1/student/me/tasks/1/submit", data={
            "content": "Direct submit"
        }, headers=student_headers)
        assert resp.status_code == 201
        assert resp.json()["content"] == "Direct submit"

    def test_student_my_sensor_data(self, client, student_headers):
        resp = client.get("/api/v1/student/me/sensor-data", headers=student_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_student_my_latest_sensor(self, client, student_headers):
        resp = client.get("/api/v1/student/me/sensor-data/latest", headers=student_headers)
        assert resp.status_code == 200

    def test_admin_cannot_access_student_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/student/me/tasks", headers=auth_headers)
        assert resp.status_code == 403


class TestUsersAPI:
    def test_list_users(self, client, auth_headers):
        resp = client.get("/api/v1/users", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(u["username"] == "admin" for u in data)

    def test_create_user(self, client, auth_headers):
        resp = client.post("/api/v1/users", json={
            "username": "newuser",
            "password": "newpass123",
            "role": "teacher",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_create_user_duplicate(self, client, auth_headers):
        resp = client.post("/api/v1/users", json={
            "username": "admin", "password": "pass1234"
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_user_empty_username(self, client, auth_headers):
        resp = client.post("/api/v1/users", json={
            "username": "", "password": "pass1234"
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_user_empty_password(self, client, auth_headers):
        resp = client.post("/api/v1/users", json={
            "username": "testuser", "password": ""
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_update_user(self, client, auth_headers):
        # Use an independent user to avoid polluting the teacher account (id=2),
        # which would break subsequent tests relying on teacher_headers.
        create = client.post("/api/v1/users", json={
            "username": "role-update-target",
            "password": "Target123",
            "role": "teacher",
        }, headers=auth_headers)
        assert create.status_code == 201
        user_id = create.json()["id"]
        resp = client.patch(f"/api/v1/users/{user_id}", json={
            "role": "admin"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_update_user_password(self, client, auth_headers):
        # Use an independent user to avoid changing the teacher account password.
        create = client.post("/api/v1/users", json={
            "username": "pwd-update-target",
            "password": "Target123",
            "role": "teacher",
        }, headers=auth_headers)
        assert create.status_code == 201
        user_id = create.json()["id"]
        resp = client.patch(f"/api/v1/users/{user_id}", json={
            "password": "newpassword123"
        }, headers=auth_headers)
        assert resp.status_code == 200

    def test_update_user_not_found(self, client, auth_headers):
        resp = client.patch("/api/v1/users/9999", json={
            "username": "newname"
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_unauthorized_user_creation(self, client, teacher_headers):
        resp = client.post("/api/v1/users", json={
            "username": "hacker", "password": "hack1234"
        }, headers=teacher_headers)
        assert resp.status_code == 403

    def test_unauthorized_user_list(self, client, teacher_headers):
        # Teachers can list users (needed for grading page student name lookup)
        resp = client.get("/api/v1/users", headers=teacher_headers)
        assert resp.status_code == 200


class TestDashboardAPI:
    def test_overview(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "online_nodes" in data
        assert "total_rules" in data
        assert "total_tasks" in data

    def test_component_summary(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/component-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "type" in data[0]
            assert "total" in data[0]


class TestLogsAPI:
    def test_operation_logs(self, client, auth_headers):
        resp = client.get("/api/v1/logs/operations", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_device_logs(self, client, auth_headers):
        resp = client.get("/api/v1/logs/device", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_rule_logs(self, client, auth_headers):
        resp = client.get("/api/v1/logs/rules", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_unauthorized_operation_logs(self, client, teacher_headers):
        resp = client.get("/api/v1/logs/operations", headers=teacher_headers)
        assert resp.status_code == 403


class TestErrorHandling:
    def test_404_not_found(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404

    def test_422_validation_error(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes", json={
            "name": 123
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_422_invalid_enum(self, client, auth_headers):
        resp = client.post("/api/v1/device-nodes/1/components", json={
            "name": "Test", "type": "invalid_type"
        }, headers=auth_headers)
        assert resp.status_code == 422


class TestExperimentsAPI:
    def test_list_experiments(self, client, auth_headers):
        resp = client.get("/api/v1/experiments", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_experiment(self, client, auth_headers):
        resp = client.post("/api/v1/experiments", json={
            "class_id": 1, "title": "光照实验", "hypothesis": "测试假设",
            "variable_metric": "light_intensity",
            "start_date": "2026-01-01", "end_date": "2026-01-07",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["title"] == "光照实验"

    def test_create_experiment_empty_title(self, client, auth_headers):
        resp = client.post("/api/v1/experiments", json={
            "class_id": 1, "title": "", "hypothesis": "测试",
            "variable_metric": "air_temp",
            "start_date": "2026-01-01", "end_date": "2026-01-07",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_get_experiment(self, client, auth_headers):
        resp = client.get("/api/v1/experiments/1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Experiment"

    def test_get_experiment_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/experiments/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_experiment(self, client, auth_headers):
        resp = client.patch("/api/v1/experiments/1", json={
            "status": "completed", "conclusion": "Light indeed helps growth"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_list_experiment_groups(self, client, auth_headers):
        resp = client.get("/api/v1/experiments/1/groups", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_add_experiment_group(self, client, auth_headers):
        from tests.conftest import test_session_factory
        resp = client.post("/api/v1/experiments/1/groups", json={
            "group_id": 1, "role": "control"
        }, headers=auth_headers)
        # 可能 201（添加成功）或 400（已存在角色）
        assert resp.status_code in (201, 400)

    def test_list_observations(self, client, auth_headers):
        resp = client.get("/api/v1/experiments/1/observations", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_observation_as_student(self, client, student_headers):
        resp = client.post("/api/v1/experiments/1/observations", json={
            "content": "今天叶子颜色正常"
        }, headers=student_headers)
        assert resp.status_code == 201
        assert resp.json()["content"] == "今天叶子颜色正常"

    def test_student_cannot_create_experiment(self, client, student_headers):
        resp = client.post("/api/v1/experiments", json={
            "class_id": 1, "title": "学生创建实验", "hypothesis": "测试",
            "variable_metric": "air_temp",
            "start_date": "2026-01-01", "end_date": "2026-01-07",
        }, headers=student_headers)
        assert resp.status_code == 403

    def test_student_list_experiments(self, client, student_headers):
        resp = client.get("/api/v1/student/me/experiments", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_student_create_observation(self, client, student_headers):
        resp = client.post("/api/v1/student/me/experiments/1/observations", json={
            "content": "学生观察记录"
        }, headers=student_headers)
        assert resp.status_code == 201

    def test_delete_experiment(self, client, auth_headers):
        resp = client.delete("/api/v1/experiments/1", headers=auth_headers)
        assert resp.status_code == 204


class TestWebSocketAPI:
    def test_ws_connect_valid_token(self, client, admin_token):
        with client.websocket_connect(f"/ws?token={admin_token}") as ws:
            ws.send_text("ping")
            data = ws.receive_text()
            assert data == "pong"

    def test_ws_connect_no_token(self, client):
        try:
            with client.websocket_connect("/ws") as ws:
                pass
        except Exception:
            pass  # FastAPI rejects with 422 for missing required query param

    def test_ws_connect_invalid_token(self, client):
        try:
            with client.websocket_connect("/ws?token=invalid") as ws:
                pass
        except Exception:
            pass  # Should close with 4001

    def test_ws_student_scoped(self, client, student_token):
        with client.websocket_connect(f"/ws?token={student_token}") as ws:
            ws.send_text("ping")
            data = ws.receive_text()
            assert data == "pong"


class TestClassroomDashboardAPI:
    def test_classroom_overview_admin(self, client, auth_headers):
        resp = client.get("/api/v1/analytics/classrooms/1/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["classroom_id"] == 1
        assert data["classroom_name"]  # 非空即可（前置测试可能改过名字）
        assert data["total_students"] >= 1
        assert data["total_groups"] >= 1
        assert "groups" in data
        assert "tasks" in data
        assert "score_distribution" in data
        assert "echarts" in data
        # groups 结构校验
        if data["groups"]:
            g = data["groups"][0]
            assert "group_id" in g
            assert "group_name" in g
            assert "student_count" in g
            assert "completion_rate" in g
        # score_distribution 结构校验
        sd = data["score_distribution"]
        assert "range_0_60" in sd
        assert "range_60_70" in sd
        assert "range_70_80" in sd
        assert "range_80_90" in sd
        assert "range_90_100" in sd
        # echarts 结构校验
        assert "group_completion" in data["echarts"]
        assert "score_distribution" in data["echarts"]

    def test_classroom_overview_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/analytics/classrooms/9999/overview", headers=auth_headers)
        assert resp.status_code == 404

    def test_classroom_overview_student_forbidden(self, client, student_headers):
        resp = client.get("/api/v1/analytics/classrooms/1/overview", headers=student_headers)
        assert resp.status_code == 403

    def test_classroom_overview_unauthorized(self, client):
        resp = client.get("/api/v1/analytics/classrooms/1/overview")
        assert resp.status_code == 401


class TestExportAPI:
    def test_export_student_growth_pdf_admin(self, client, auth_headers):
        """admin 导出学生 4 的成长档案 PDF"""
        resp = client.get("/api/v1/exports/students/4/growth-pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF 文件以 %PDF 魔数开头
        assert resp.content[:4] == b"%PDF"
        # Content-Disposition 包含文件名（中文用 filename* URL 编码）
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "filename*=UTF-8" in cd  # RFC 5987 中文文件名

    def test_export_student_growth_pdf_not_found(self, client, auth_headers):
        """不存在的学生 ID 返回 404"""
        resp = client.get("/api/v1/exports/students/9999/growth-pdf", headers=auth_headers)
        assert resp.status_code == 404

    def test_export_student_growth_pdf_student_forbidden(self, client, student_headers):
        """学生不能导出（即使导出自己的也不行，仅教师/管理员）"""
        resp = client.get("/api/v1/exports/students/4/growth-pdf", headers=student_headers)
        assert resp.status_code == 403

    def test_export_student_growth_pdf_unauthorized(self, client):
        """未授权访问返回 401"""
        resp = client.get("/api/v1/exports/students/4/growth-pdf")
        assert resp.status_code == 401


class TestDeviceTokenAPI:
    """P0-NEW-0 设备鉴权基础设施测试。"""

    def test_list_tokens_admin(self, client, auth_headers):
        """admin 可列出设备令牌（至少返回空列表或已有种子）。"""
        resp = client.get("/api/v1/device-tokens", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_token_admin(self, client, auth_headers):
        """admin 创建 esp32 设备令牌，返回 201 + 明文 token。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32",
            "device_name": "Test ESP32 Main",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["group_id"] == 1
        assert data["device_type"] == "esp32"
        assert data["device_name"] == "Test ESP32 Main"
        assert data["is_active"] is True
        assert "token" in data and len(data["token"]) > 0
        # 记录 token 供后续 /me 测试使用
        TestDeviceTokenAPI._esp32_token = data["token"]
        TestDeviceTokenAPI._esp32_token_id = data["id"]

    def test_create_token_duplicate_rejected(self, client, auth_headers):
        """同组同类型重复签发返回 400。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32",
            "device_name": "Duplicate ESP32",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    def test_create_token_invalid_group(self, client, auth_headers):
        """不存在的小组 ID 返回 400。"""
        payload = {
            "group_id": 9999,
            "device_type": "esp32cam",
            "device_name": "Invalid Group CAM",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_token_invalid_node(self, client, auth_headers):
        """不存在的节点 ID 返回 400。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32s3",
            "device_name": "Invalid Node S3",
            "node_id": 9999,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_token_cam_for_me_test(self, client, auth_headers):
        """创建 CAM 令牌（用于 /me 端点测试，避免与 esp32 冲突）。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32cam",
            "device_name": "Test CAM Node",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        TestDeviceTokenAPI._cam_token = resp.json()["token"]
        TestDeviceTokenAPI._cam_token_id = resp.json()["id"]

    def test_device_self_verify_valid(self, client):
        """设备用有效 token 调用 /me，返回 200 + 自身信息。"""
        token = getattr(TestDeviceTokenAPI, "_cam_token", None)
        assert token is not None, "前置：test_create_token_cam_for_me_test 须先运行"
        resp = client.get(
            "/api/v1/device-tokens/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_type"] == "esp32cam"
        assert data["group_id"] == 1

    def test_device_self_verify_invalid_token(self, client):
        """无效 token 调用 /me 返回 401。"""
        resp = client.get(
            "/api/v1/device-tokens/me",
            headers={"Authorization": "Bearer invalid_token_string_xxx"},
        )
        assert resp.status_code == 401

    def test_device_self_verify_missing_header(self, client):
        """缺少 Authorization 头调用 /me 返回 401。"""
        resp = client.get("/api/v1/device-tokens/me")
        assert resp.status_code == 401

    def test_reset_token(self, client, auth_headers):
        """重置 token：旧 token 失效，新 token 返回。"""
        token_id = getattr(TestDeviceTokenAPI, "_cam_token_id", None)
        assert token_id is not None
        old_token = TestDeviceTokenAPI._cam_token
        resp = client.post(
            f"/api/v1/device-tokens/{token_id}/reset", headers=auth_headers
        )
        assert resp.status_code == 200
        new_token = resp.json()["token"]
        assert new_token != old_token
        TestDeviceTokenAPI._cam_token = new_token  # 更新为新 token
        # 旧 token 已失效
        resp_old = client.get(
            "/api/v1/device-tokens/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert resp_old.status_code == 401
        # 新 token 可用
        resp_new = client.get(
            "/api/v1/device-tokens/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert resp_new.status_code == 200

    def test_revoke_token(self, client, auth_headers):
        """吊销 token：is_active=False，设备调用返回 401。"""
        token_id = getattr(TestDeviceTokenAPI, "_cam_token_id", None)
        assert token_id is not None
        resp = client.post(
            f"/api/v1/device-tokens/{token_id}/revoke", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        # 吊销后 token 失效
        resp_me = client.get(
            "/api/v1/device-tokens/me",
            headers={"Authorization": f"Bearer {TestDeviceTokenAPI._cam_token}"},
        )
        assert resp_me.status_code == 401

    def test_list_tokens_filter_by_group(self, client, auth_headers):
        """按 group_id 过滤列表。"""
        resp = client.get(
            "/api/v1/device-tokens?group_id=1", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["group_id"] == 1 for t in data)

    def test_list_tokens_invalid_device_type(self, client, auth_headers):
        """无效 device_type 查询参数返回 400。"""
        resp = client.get(
            "/api/v1/device-tokens?device_type=invalid", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_create_token_teacher_allowed(self, client, teacher_headers):
        """教师可签发令牌（为本班设备）。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32s3",
            "device_name": "Teacher-Issued S3",
            "node_id": 1,
        }
        resp = client.post(
            "/api/v1/device-tokens", json=payload, headers=teacher_headers
        )
        assert resp.status_code == 201
        TestDeviceTokenAPI._s3_token_id = resp.json()["id"]

    def test_create_token_student_forbidden(self, client, student_headers):
        """学生无权签发令牌（403）。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32",
            "device_name": "Student Attempt",
            "node_id": 1,
        }
        resp = client.post(
            "/api/v1/device-tokens", json=payload, headers=student_headers
        )
        assert resp.status_code == 403

    def test_list_tokens_student_forbidden(self, client, student_headers):
        """学生无权列出令牌（403）。"""
        resp = client.get("/api/v1/device-tokens", headers=student_headers)
        assert resp.status_code == 403

    def test_unauthorized_access(self, client):
        """未授权访问所有端点返回 401。"""
        assert client.get("/api/v1/device-tokens").status_code == 401
        assert (
            client.post(
                "/api/v1/device-tokens",
                json={
                    "group_id": 1,
                    "device_type": "esp32",
                    "device_name": "x",
                    "node_id": 1,
                },
            ).status_code
            == 401
        )

    def test_reset_not_found(self, client, auth_headers):
        """重置不存在的令牌返回 404。"""
        resp = client.post(
            "/api/v1/device-tokens/9999/reset", headers=auth_headers
        )
        assert resp.status_code == 404

    def test_delete_token_admin_only(self, client, auth_headers, teacher_headers):
        """删除令牌仅 admin 可用，教师返回 403。"""
        # 先创建一个用于删除的令牌（esp32s3 若已被教师测试占用，则跳过）
        # 使用 revoke 后的 cam 令牌 id 删除（已吊销，可硬删除）
        token_id = getattr(TestDeviceTokenAPI, "_cam_token_id", None)
        if token_id is None:
            pytest.skip("前置令牌未创建")
        # 教师不能删除
        resp_t = client.delete(
            f"/api/v1/device-tokens/{token_id}", headers=teacher_headers
        )
        assert resp_t.status_code == 403
        # admin 删除
        resp = client.delete(
            f"/api/v1/device-tokens/{token_id}", headers=auth_headers
        )
        assert resp.status_code == 204


class TestPestDiagnosisAPI:
    """P0-NEW-1 ESP32-CAM 病虫害诊断测试。"""

    _cam_token: str | None = None
    _esp32_token: str | None = None
    _diagnosis_id: int | None = None

    def test_setup_create_cam_device_token(self, client, auth_headers):
        """前置：创建 esp32cam 设备令牌用于上传测试。"""
        # 先尝试创建，若已存在（重复）则从列表中取
        payload = {
            "group_id": 1,
            "device_type": "esp32cam",
            "device_name": "Test CAM for Pest",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        if resp.status_code == 201:
            TestPestDiagnosisAPI._cam_token = resp.json()["token"]
        else:
            # 已存在，从列表获取 — 但明文 token 不可二次获取，需 reset
            resp_list = client.get(
                "/api/v1/device-tokens?device_type=esp32cam&group_id=1",
                headers=auth_headers,
            )
            assert resp_list.status_code == 200
            tokens = resp_list.json()
            assert len(tokens) > 0
            token_id = tokens[0]["id"]
            resp_reset = client.post(
                f"/api/v1/device-tokens/{token_id}/reset", headers=auth_headers
            )
            assert resp_reset.status_code == 200
            TestPestDiagnosisAPI._cam_token = resp_reset.json()["token"]

    def test_setup_create_esp32_device_token(self, client, auth_headers):
        """前置：创建 esp32（非 cam）设备令牌，用于权限测试。若已存在则 reset 获取明文。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32",
            "device_name": "Test ESP32 for Permission",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        if resp.status_code == 201:
            TestPestDiagnosisAPI._esp32_token = resp.json()["token"]
        else:
            # 已存在（TestDeviceTokenAPI 可能已创建），reset 获取明文
            resp_list = client.get(
                "/api/v1/device-tokens?device_type=esp32&group_id=1",
                headers=auth_headers,
            )
            assert resp_list.status_code == 200
            tokens = resp_list.json()
            if tokens:
                token_id = tokens[0]["id"]
                resp_reset = client.post(
                    f"/api/v1/device-tokens/{token_id}/reset", headers=auth_headers
                )
                assert resp_reset.status_code == 200
                TestPestDiagnosisAPI._esp32_token = resp_reset.json()["token"]

    def test_upload_diagnosis_success(self, client):
        """esp32cam 设备上传图片，返回 201 + 诊断结果（5 分类之一）。"""
        token = TestPestDiagnosisAPI._cam_token
        assert token is not None, "前置：cam 令牌未创建"
        fake_image = b"\xff\xd8\xff\xe0test_image_data_for_pest_diagnosis_001\x00" * 10
        resp = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", fake_image, "image/jpeg")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["diagnosis_result"] in [
            "tomato_healthy",
            "tomato_early_blight",
            "tomato_late_blight",
            "strawberry_healthy",
            "strawberry_leaf_scorch",
        ]
        assert 0.0 <= data["confidence"] <= 1.0
        assert "image_url" in data
        assert data["image_url"].startswith("/pest-images/")
        assert data["suggestion"] is not None
        TestPestDiagnosisAPI._diagnosis_id = data["id"]

    def test_upload_diagnosis_deterministic(self, client):
        """同一张图片两次上传应返回相同诊断结果（mock 确定性）。"""
        token = TestPestDiagnosisAPI._cam_token
        assert token is not None
        fake_image = b"deterministic_test_image_002" * 20
        resp1 = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("a.jpg", fake_image, "image/jpeg")},
        )
        resp2 = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("b.jpg", fake_image, "image/jpeg")},
        )
        assert resp1.status_code == 201 and resp2.status_code == 201
        assert resp1.json()["diagnosis_result"] == resp2.json()["diagnosis_result"]
        assert resp1.json()["confidence"] == resp2.json()["confidence"]

    def test_upload_non_cam_device_forbidden(self, client):
        """非 esp32cam 设备（如 esp32）上传返回 403。"""
        token = getattr(TestPestDiagnosisAPI, "_esp32_token", None)
        if token is None:
            pytest.skip("esp32 令牌未创建（可能已存在）")
        resp = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", b"fake", "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_upload_invalid_image_type(self, client):
        """非图片类型上传返回 400。"""
        token = TestPestDiagnosisAPI._cam_token
        assert token is not None
        resp = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_no_auth(self, client):
        """无设备 token 上传返回 401。"""
        resp = client.post(
            "/api/v1/pest-diagnoses/upload",
            files={"file": ("test.jpg", b"fake", "image/jpeg")},
        )
        assert resp.status_code == 401

    def test_upload_invalid_token(self, client):
        """无效设备 token 上传返回 401。"""
        resp = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": "Bearer invalid_device_token"},
            files={"file": ("test.jpg", b"fake", "image/jpeg")},
        )
        assert resp.status_code == 401

    def test_list_diagnoses_admin(self, client, auth_headers):
        """admin 列出诊断记录。"""
        resp = client.get("/api/v1/pest-diagnoses", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) > 0  # 前面上传测试已产生记录

    def test_list_diagnoses_teacher(self, client, teacher_headers):
        """教师可读所有班级诊断。"""
        resp = client.get("/api/v1/pest-diagnoses", headers=teacher_headers)
        assert resp.status_code == 200

    def test_list_diagnoses_filter_by_group(self, client, auth_headers):
        """按 group_id 过滤。"""
        resp = client.get(
            "/api/v1/pest-diagnoses?group_id=1", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(d["group_id"] == 1 for d in data)

    def test_list_diagnoses_filter_by_result(self, client, auth_headers):
        """按 diagnosis_result 过滤。"""
        resp = client.get(
            "/api/v1/pest-diagnoses?diagnosis_result=tomato_healthy",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(d["diagnosis_result"] == "tomato_healthy" for d in data)

    def test_list_diagnoses_invalid_result(self, client, auth_headers):
        """无效 diagnosis_result 返回 400。"""
        resp = client.get(
            "/api/v1/pest-diagnoses?diagnosis_result=invalid",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_get_diagnosis_detail(self, client, auth_headers):
        """获取诊断详情。"""
        diag_id = TestPestDiagnosisAPI._diagnosis_id
        assert diag_id is not None
        resp = client.get(
            f"/api/v1/pest-diagnoses/{diag_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == diag_id

    def test_get_diagnosis_not_found(self, client, auth_headers):
        """不存在的诊断 ID 返回 404。"""
        resp = client.get("/api/v1/pest-diagnoses/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_student_own_group_diagnoses(self, client, student_headers):
        """学生查看本组诊断记录。"""
        resp = client.get(
            "/api/v1/student/me/pest-diagnoses", headers=student_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # 学生 g1s1 属于 group_id=1，应有诊断记录
        assert all(d["group_id"] == 1 for d in data)

    def test_student_list_admin_endpoint_forbidden(self, client, student_headers):
        """学生不能访问管理端列表接口（403）。"""
        resp = client.get("/api/v1/pest-diagnoses", headers=student_headers)
        assert resp.status_code == 403

    def test_delete_diagnosis_admin(self, client, auth_headers):
        """admin 删除诊断记录。"""
        # 先上传一条用于删除
        token = TestPestDiagnosisAPI._cam_token
        assert token is not None
        resp = client.post(
            "/api/v1/pest-diagnoses/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("delete_me.jpg", b"to_be_deleted_data", "image/jpeg")},
        )
        assert resp.status_code == 201
        diag_id = resp.json()["id"]
        resp_del = client.delete(
            f"/api/v1/pest-diagnoses/{diag_id}", headers=auth_headers
        )
        assert resp_del.status_code == 204

    def test_delete_diagnosis_teacher_forbidden(self, client, teacher_headers):
        """教师不能删除诊断记录（403）。"""
        diag_id = TestPestDiagnosisAPI._diagnosis_id
        assert diag_id is not None
        resp = client.delete(
            f"/api/v1/pest-diagnoses/{diag_id}", headers=teacher_headers
        )
        assert resp.status_code == 403

    def test_delete_diagnosis_not_found(self, client, auth_headers):
        """删除不存在的诊断返回 404。"""
        resp = client.delete(
            "/api/v1/pest-diagnoses/9999", headers=auth_headers
        )
        assert resp.status_code == 404


class TestMcpAPI:
    """P0-NEW-2 小智 AI MCP 工具调用测试。"""

    _g1_token: str | None = None  # 1 组 esp32s3 设备 token
    _g2_token: str | None = None  # 2 组 esp32s3 设备 token（跨组隔离验证用）

    def test_setup_create_g1_esp32s3_token(self, client, auth_headers):
        """前置：创建 1 组 esp32s3 设备令牌。若已存在则 reset 获取明文。"""
        payload = {
            "group_id": 1,
            "device_type": "esp32s3",
            "device_name": "Test S3 for MCP G1",
            "node_id": 1,
        }
        resp = client.post("/api/v1/device-tokens", json=payload, headers=auth_headers)
        if resp.status_code == 201:
            TestMcpAPI._g1_token = resp.json()["token"]
        else:
            resp_list = client.get(
                "/api/v1/device-tokens?device_type=esp32s3&group_id=1",
                headers=auth_headers,
            )
            assert resp_list.status_code == 200
            tokens = resp_list.json()
            assert len(tokens) > 0
            token_id = tokens[0]["id"]
            resp_reset = client.post(
                f"/api/v1/device-tokens/{token_id}/reset", headers=auth_headers
            )
            assert resp_reset.status_code == 200
            TestMcpAPI._g1_token = resp_reset.json()["token"]

    def test_setup_create_g2_for_isolation(self, client, auth_headers):
        """前置：创建 2 组（node 2 + fan）+ esp32s3 token，用于跨组隔离验证。"""
        # 创建 node 2
        resp_node = client.post(
            "/api/v1/device-nodes",
            json={"name": "Node-MCP-Test", "location": "Isolation Test"},
            headers=auth_headers,
        )
        node_id = 2  # 默认自增，sample_data 只有 node 1
        if resp_node.status_code == 201:
            node_id = resp_node.json()["id"]
        else:
            # 已存在则用列表中的
            resp_list = client.get("/api/v1/device-nodes", headers=auth_headers)
            nodes = resp_list.json()
            for n in nodes:
                if n["id"] != 1:
                    node_id = n["id"]
                    break

        # 创建 group 2（绑定 node_id）
        resp_group = client.post(
            "/api/v1/groups",
            json={"name": "Group-MCP-Test", "class_id": 1, "node_id": node_id},
            headers=auth_headers,
        )
        group_id = 2
        if resp_group.status_code == 201:
            group_id = resp_group.json()["id"]
        else:
            resp_groups = client.get("/api/v1/groups", headers=auth_headers)
            for g in resp_groups.json():
                if g["id"] != 1:
                    group_id = g["id"]
                    break

        # 创建 fan 组件在 node 上
        client.post(
            f"/api/v1/device-nodes/{node_id}/components",
            json={"name": "Fan-MCP-Test", "type": "fan", "status": "off"},
            headers=auth_headers,
        )

        # 创建 2 组 esp32s3 token
        payload = {
            "group_id": group_id,
            "device_type": "esp32s3",
            "device_name": "Test S3 for MCP G2",
            "node_id": node_id,
        }
        resp_token = client.post(
            "/api/v1/device-tokens", json=payload, headers=auth_headers
        )
        if resp_token.status_code == 201:
            TestMcpAPI._g2_token = resp_token.json()["token"]
        else:
            resp_list = client.get(
                f"/api/v1/device-tokens?device_type=esp32s3&group_id={group_id}",
                headers=auth_headers,
            )
            tokens = resp_list.json()
            if tokens:
                token_id = tokens[0]["id"]
                resp_reset = client.post(
                    f"/api/v1/device-tokens/{token_id}/reset", headers=auth_headers
                )
                assert resp_reset.status_code == 200
                TestMcpAPI._g2_token = resp_reset.json()["token"]

    def test_list_tools(self, client):
        """设备 token 鉴权获取工具列表，应返回 6 个工具。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.get(
            "/api/v1/mcp/tools", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        tools = resp.json()
        assert len(tools) == 6
        names = {t["name"] for t in tools}
        assert "get_latest_sensor_data" in names
        assert "control_components_by_type" in names
        assert "get_group_components" in names
        assert "get_crop_status" in names
        assert "list_pending_tasks" in names
        assert "list_group_rules" in names

    def test_list_tools_no_auth(self, client):
        """无设备 token 获取工具列表返回 401。"""
        resp = client.get("/api/v1/mcp/tools")
        assert resp.status_code == 401

    def test_list_tools_invalid_token(self, client):
        """无效设备 token 返回 401。"""
        resp = client.get(
            "/api/v1/mcp/tools",
            headers={"Authorization": "Bearer invalid_mcp_token"},
        )
        assert resp.status_code == 401

    def test_call_get_latest_sensor_data(self, client):
        """调用 get_latest_sensor_data 返回本组传感器数据。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"tool_name": "get_latest_sensor_data", "arguments": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["result"]["found"] is True
        assert "air_temp" in data["result"]
        assert data["duration_ms"] >= 0

    def test_call_control_fan_on(self, client):
        """调用 control_components_by_type 打开本组风扇。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tool_name": "control_components_by_type",
                "arguments": {"component_type": "fan", "action": "on"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["result"]["controlled_count"] >= 1
        assert all(c["status"] == "on" for c in data["result"]["components"])

    def test_call_control_invalid_type(self, client):
        """调用 control_components_by_type 传非法类型返回 count=0 + error。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tool_name": "control_components_by_type",
                "arguments": {"component_type": "invalid_type", "action": "on"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True  # 工具执行成功，但返回错误信息
        assert data["result"]["controlled_count"] == 0
        assert "error" in data["result"]

    def test_cross_group_isolation(self, client):
        """跨组隔离：1 组 token 控制风扇不影响 2 组。"""
        g1_token = TestMcpAPI._g1_token
        g2_token = TestMcpAPI._g2_token
        if not g1_token or not g2_token:
            pytest.skip("跨组测试前置条件未满足")

        # 1 组 token 打开风扇
        client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {g1_token}"},
            json={
                "tool_name": "control_components_by_type",
                "arguments": {"component_type": "fan", "action": "on"},
            },
        )

        # 查询 2 组组件状态
        resp_g2 = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {g2_token}"},
            json={"tool_name": "get_group_components", "arguments": {}},
        )
        assert resp_g2.status_code == 200
        g2_data = resp_g2.json()
        # 2 组的风扇应不受 1 组控制影响（仍为 off 或非 on）
        g2_fans = [c for c in g2_data["result"]["components"] if c["type"] == "fan"]
        if g2_fans:
            # 2 组风扇不应被 1 组 token 打开
            assert all(c["status"] != "on" for c in g2_fans), "跨组控制泄露：1 组 token 影响了 2 组风扇"

    def test_call_get_group_components(self, client):
        """调用 get_group_components 返回本组执行器列表。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"tool_name": "get_group_components", "arguments": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["result"]["found"] is True
        assert "components" in data["result"]
        # 应包含风扇/水泵/补光灯（非传感器）
        types = {c["type"] for c in data["result"]["components"]}
        assert "sensor" not in types

    def test_call_get_crop_status(self, client):
        """调用 get_crop_status 返回本组作物信息。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"tool_name": "get_crop_status", "arguments": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["result"]["found"] is True
        assert data["result"]["total"] >= 1

    def test_call_list_pending_tasks(self, client):
        """调用 list_pending_tasks 返回本组未完成任务。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"tool_name": "list_pending_tasks", "arguments": {"limit": 5}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "tasks" in data["result"]
        # sample_data 有 1 个 pending 任务（group_id=1）
        assert data["result"]["total"] >= 1

    def test_call_list_group_rules(self, client):
        """调用 list_group_rules 返回本组节点规则。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"tool_name": "list_group_rules", "arguments": {"enabled_only": True}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["result"]["found"] is True

    def test_call_unknown_tool(self, client):
        """调用不存在的工具返回 success=False。"""
        token = TestMcpAPI._g1_token
        assert token is not None
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"tool_name": "nonexistent_tool", "arguments": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Unknown tool" in data["error"]

    def test_call_no_auth(self, client):
        """无设备 token 调用工具返回 401。"""
        resp = client.post(
            "/api/v1/mcp/tools/call",
            json={"tool_name": "get_latest_sensor_data", "arguments": {}},
        )
        assert resp.status_code == 401

    def test_logs_admin(self, client, auth_headers):
        """admin 查询 MCP 调用日志，应包含前面调用产生的记录。"""
        resp = client.get("/api/v1/mcp/logs", headers=auth_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert isinstance(logs, list)
        assert len(logs) > 0  # 前面调用已产生日志
        # 验证日志结构（不含对话原文，仅含工具调用元信息）
        log = logs[0]
        assert "tool_name" in log
        assert "arguments" in log
        assert "result" in log
        assert "duration_ms" in log
        assert "success" in log
        assert "group_id" in log

    def test_logs_teacher(self, client, teacher_headers):
        """教师可查询所有 MCP 调用日志。"""
        resp = client.get("/api/v1/mcp/logs", headers=teacher_headers)
        assert resp.status_code == 200

    def test_logs_student_forbidden(self, client, student_headers):
        """学生不能查询 MCP 日志（403）。"""
        resp = client.get("/api/v1/mcp/logs", headers=student_headers)
        assert resp.status_code == 403

    def test_logs_filter_by_group(self, client, auth_headers):
        """按 group_id 过滤日志。"""
        resp = client.get(
            "/api/v1/mcp/logs?group_id=1", headers=auth_headers
        )
        assert resp.status_code == 200
        logs = resp.json()
        assert all(l["group_id"] == 1 for l in logs)

    def test_cleanup_expired_logs(self, db):
        """过期日志清理：构造 expires_at < now 的日志，调用清理后被删除。"""
        from datetime import datetime, timedelta
        from app.models import McpCallLog

        # 构造一条已过期的日志
        expired_log = McpCallLog(
            group_id=1,
            device_token_id=1,
            tool_name="get_latest_sensor_data",
            arguments="{}",
            result='{"found": true}',
            duration_ms=10,
            success=True,
            error_message=None,
            created_at=datetime.now() - timedelta(days=35),
            expires_at=datetime.now() - timedelta(days=5),  # 已过期
        )
        db.add(expired_log)
        db.commit()

        from app.services import mcp_service
        cleaned = mcp_service.cleanup_expired_mcp_logs(db)
        assert cleaned >= 1

    def test_call_tool_wrong_device_type(self, client, db):
        """非 esp32s3 设备（如 esp32）调用 MCP 工具返回 403。"""
        from app.models.device_token import DeviceToken
        from app.models.enums import DeviceType

        token = DeviceToken(
            group_id=1,
            node_id=1,
            device_type=DeviceType.esp32,
            device_name="ESP32-for-MCP-perm-test",
            token="test-esp32-mcp-perm-token-001",
            is_active=True,
        )
        db.add(token)
        db.commit()
        resp = client.post(
            "/api/v1/mcp/tools/call",
            headers={"Authorization": f"Bearer {token.token}"},
            json={"tool_name": "get_latest_sensor_data", "arguments": {}},
        )
        assert resp.status_code == 403


class TestCoursewareAPI:
    """课件库 API 测试。"""

    _courseware_id: int | None = None

    def test_upload_courseware(self, client, teacher_headers):
        pdf_content = b"%PDF-1.4\n%test pdf content for courseware upload\n"
        resp = client.post(
            "/api/v1/courseware",
            data={
                "title": "Test Courseware",
                "description": "A test PDF courseware",
                "file_type": "pdf",
                "subject": "science",
                "grade_level": "grade_5",
                "tags": "test,pdf",
                "is_public": "false",
            },
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            headers=teacher_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Courseware"
        assert data["file_type"] == "pdf"
        assert data["subject"] == "science"
        assert data["owner_id"] == 2  # teacher id
        assert data["file_url"].startswith("/courseware-files/")
        assert data["is_public"] is False
        TestCoursewareAPI._courseware_id = data["id"]

    def test_list_my_courseware(self, client, teacher_headers):
        resp = client.get("/api/v1/courseware/my", headers=teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        cid = TestCoursewareAPI._courseware_id
        assert cid is not None
        assert any(c["id"] == cid for c in data)

    def test_list_public_courseware(self, client, teacher_headers):
        # 当前课件为私密，公共库不应包含
        resp = client.get("/api/v1/courseware/public", headers=teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        cid = TestCoursewareAPI._courseware_id
        assert cid is not None
        assert not any(c["id"] == cid for c in data)

    def test_get_courseware(self, client, teacher_headers):
        cid = TestCoursewareAPI._courseware_id
        assert cid is not None
        resp = client.get(f"/api/v1/courseware/{cid}", headers=teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cid
        assert data["title"] == "Test Courseware"
        assert "owner_name" in data

    def test_toggle_public(self, client, teacher_headers):
        cid = TestCoursewareAPI._courseware_id
        assert cid is not None
        resp_before = client.get(f"/api/v1/courseware/{cid}", headers=teacher_headers)
        before_state = resp_before.json()["is_public"]
        resp = client.patch(
            f"/api/v1/courseware/{cid}/toggle-public", headers=teacher_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_public"] is (not before_state)

    def test_delete_courseware(self, client, teacher_headers):
        cid = TestCoursewareAPI._courseware_id
        assert cid is not None
        resp = client.delete(f"/api/v1/courseware/{cid}", headers=teacher_headers)
        assert resp.status_code == 204
        resp_get = client.get(f"/api/v1/courseware/{cid}", headers=teacher_headers)
        assert resp_get.status_code == 404

    def test_upload_invalid_file_type(self, client, teacher_headers):
        resp = client.post(
            "/api/v1/courseware",
            data={
                "title": "Invalid Type",
                "file_type": "jpg",
                "subject": "science",
            },
            files={"file": ("test.jpg", b"fake image data", "image/jpeg")},
            headers=teacher_headers,
        )
        assert resp.status_code == 400


class TestTeachingResourcesAPI:
    """教学资源 API 测试。"""

    _resource_id: int | None = None

    def test_create_resource(self, client, teacher_headers):
        pdf_content = b"%PDF-1.4\n%test pdf content for teaching resource\n"
        resp = client.post(
            "/api/v1/resources",
            data={
                "title": "Test Resource",
                "description": "A test teaching resource",
                "resource_type": "pdf",
                "subject": "science",
                "classroom_id": "1",
                "group_id": "1",
                "is_published": "true",
            },
            files={"file": ("resource.pdf", pdf_content, "application/pdf")},
            headers=teacher_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Resource"
        assert data["resource_type"] == "pdf"
        assert data["publisher_id"] == 2  # teacher id
        assert data["file_url"].startswith("/resource-files/")
        assert data["is_published"] is True
        TestTeachingResourcesAPI._resource_id = data["id"]

    def test_list_resources(self, client, teacher_headers):
        resp = client.get("/api/v1/resources", headers=teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        rid = TestTeachingResourcesAPI._resource_id
        assert rid is not None
        assert any(r["id"] == rid for r in data)

    def test_toggle_publish(self, client, teacher_headers):
        rid = TestTeachingResourcesAPI._resource_id
        assert rid is not None
        # 撤回
        resp1 = client.patch(
            f"/api/v1/resources/{rid}/publish", headers=teacher_headers
        )
        assert resp1.status_code == 200
        assert resp1.json()["is_published"] is False
        # 重新发布
        resp2 = client.patch(
            f"/api/v1/resources/{rid}/publish", headers=teacher_headers
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_published"] is True

    def test_student_view_resources(self, client, student_headers):
        resp = client.get("/api/v1/student/me/resources", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        rid = TestTeachingResourcesAPI._resource_id
        assert rid is not None
        assert any(r["id"] == rid for r in data)

    def test_student_cannot_view_unpublished(
        self, client, teacher_headers, student_headers
    ):
        rid = TestTeachingResourcesAPI._resource_id
        assert rid is not None
        # 撤回
        resp_toggle = client.patch(
            f"/api/v1/resources/{rid}/publish", headers=teacher_headers
        )
        assert resp_toggle.json()["is_published"] is False
        # 学生查看，不应包含已撤回资源
        resp = client.get("/api/v1/student/me/resources", headers=student_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert not any(r["id"] == rid for r in data)

    def test_delete_resource(self, client, teacher_headers):
        rid = TestTeachingResourcesAPI._resource_id
        assert rid is not None
        resp = client.delete(f"/api/v1/resources/{rid}", headers=teacher_headers)
        assert resp.status_code == 204
        resp_get = client.get(f"/api/v1/resources/{rid}", headers=teacher_headers)
        assert resp_get.status_code == 404


class TestAnalyticsAPI:
    """学习分析 API 测试。"""

    def test_get_student_analytics(self, client, teacher_headers):
        # student id=4 in sample_data
        resp = client.get("/api/v1/analytics/students/4", headers=teacher_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        summary = data["summary"]
        assert summary["student_id"] == 4
        assert "total_submissions" in summary
        assert "completion_rate" in summary
        assert "submission_frequency" in data
        assert "score_trend" in data
        assert "recent_activity" in data

    def test_get_class_analytics(self, client, teacher_headers):
        # classroom id=1 in sample_data
        resp = client.get(
            "/api/v1/analytics/classrooms/1/overview", headers=teacher_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["classroom_id"] == 1
        assert "total_students" in data
        assert "total_groups" in data
        assert "groups" in data
        assert "tasks" in data
        assert "score_distribution" in data


class TestExportsAPI:
    """学生成长 PDF 导出 API 测试。"""

    def test_export_student_pdf(self, client, teacher_headers):
        resp = client.get(
            "/api/v1/exports/students/4/growth-pdf", headers=teacher_headers
        )
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        # PDF 应有内容
        assert len(resp.content) > 0
        # Content-Disposition 应包含文件名
        assert "content-disposition" in resp.headers
        assert "growth_archive" in resp.headers["content-disposition"]

"""端到端冒烟测试：验证新教师端页面与 API 完整闭环"""
import json
import sys
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error

BASE = "http://127.0.0.1:8001/api/v1"


def multipart_encode(fields: dict) -> tuple[bytes, str]:
    """Encode fields as multipart/form-data (no files)."""
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    body += f"--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def api(method: str, path: str, token: str | None = None, body: dict | None = None, form: bool = False, multipart: bool = False):
    url = f"{BASE}{path}"
    if multipart and body:
        data, content_type = multipart_encode(body)
    elif form and body:
        data = urllib.parse.urlencode(body).encode()
        content_type = "application/x-www-form-urlencoded"
    else:
        data = json.dumps(body).encode() if body else None
        content_type = "application/json"
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", content_type)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def main():
    failures = []
    total = 0

    def check(name: str, ok: bool, detail: str = ""):
        nonlocal total
        total += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    # 1. 管理员登录
    code, resp = api("POST", "/auth/login", body={"username": "admin", "password": "Admin123456"}, form=True)
    check("管理员登录", code == 200, f"code={code}")
    admin_token = resp.get("access_token") if isinstance(resp, dict) else None

    # 2. 获取班级列表
    code, resp = api("GET", "/classrooms", token=admin_token)
    check("获取班级列表", code == 200, f"count={len(resp) if isinstance(resp, list) else 'err'}")
    initial_classroom_count = len(resp) if isinstance(resp, list) else 0

    # 3. 创建新班级
    classroom_name = f"E2E班级_{int(time.time()) % 10000}"
    code, resp = api("POST", "/classrooms", token=admin_token, body={"name": classroom_name, "subject": "labor"})
    check("创建班级", code in (200, 201), f"name={classroom_name} code={code}")
    classroom_id = resp.get("id") if isinstance(resp, dict) and code in (200, 201) else None

    # 4. 获取小组列表
    code, resp = api("GET", "/groups", token=admin_token)
    check("获取小组列表", code == 200)

    # 5. 在新班级下创建小组
    group_name = f"E2E第1组"
    code, resp = api("POST", "/groups", token=admin_token, body={"name": group_name, "class_id": classroom_id})
    check("创建小组", code in (200, 201), f"class_id={classroom_id} code={code}")
    group_id = resp.get("id") if isinstance(resp, dict) and code in (200, 201) else None

    # 6. 获取设备节点列表
    code, resp = api("GET", "/device-nodes", token=admin_token)
    check("获取设备节点列表", code == 200)
    available_node_id = resp[0].get("id") if isinstance(resp, list) and resp else None

    # 7. 绑定节点到小组
    if group_id and available_node_id:
        code, resp = api("POST", f"/groups/{group_id}/bind-node?node_id={available_node_id}", token=admin_token)
        check("绑定节点到小组", code == 200, f"group={group_id} node={available_node_id}")

    # 8. 批量创建学生
    if group_id:
        code, resp = api(
            "POST",
            f"/groups/{group_id}/students/batch",
            token=admin_token,
            body={"group_id": group_id, "count": 3, "password": "Student123"},
        )
        check("批量创建学生", code in (200, 201), f"created={len(resp) if isinstance(resp, list) else 'err'} code={code}")
        created_students = resp if isinstance(resp, list) else []
        if created_students:
            student_username = created_students[0].get("username")
            check("学生用户名格式", student_username.startswith(f"g{group_id}s"), f"username={student_username}")

    # 9. 创建任务
    task_title = f"E2E观察任务_{int(time.time()) % 10000}"
    code, resp = api(
        "POST",
        "/tasks",
        token=admin_token,
        body={
            "title": task_title,
            "description": "观察土壤湿度变化",
            "status": "pending",
            "group_id": group_id,
            "course_subject": "labor",
            "task_type": "observation",
        },
    )
    check("创建任务", code in (200, 201), f"title={task_title} code={code}")
    task_id = resp.get("id") if isinstance(resp, dict) and code in (200, 201) else None

    # 10. 获取提交列表（教师视角）
    code, resp = api("GET", "/submissions", token=admin_token)
    check("获取提交列表（教师）", code == 200)

    # 11. 学生登录
    student_token = None
    if group_id:
        # 先获取小组学生列表找到用户名
        code, resp = api("GET", f"/groups/{group_id}/students", token=admin_token)
        if code == 200 and resp:
            student_username = resp[0].get("username")
            code, resp = api("POST", "/auth/login", body={"username": student_username, "password": "Student123"}, form=True)
            check("学生登录", code == 200, f"username={student_username}")
            student_token = resp.get("access_token") if isinstance(resp, dict) and code == 200 else None

    # 12. 学生获取自己的小组信息
    if student_token:
        code, resp = api("GET", "/student/me/group", token=student_token)
        check("学生获取本组信息", code == 200, f"group_id={resp.get('id')}")

    # 13. 学生获取任务列表
    if student_token:
        code, resp = api("GET", "/student/me/tasks", token=student_token)
        check("学生获取任务列表", code == 200, f"count={len(resp) if isinstance(resp, list) else 'err'}")

    # 14. 学生提交作业
    if student_token and task_id:
        code, resp = api(
            "POST",
            f"/student/me/tasks/{task_id}/submit",
            token=student_token,
            body={"content": "今天观察到土壤湿度从 48% 降到 42%，建议浇水。"},
            multipart=True,
        )
        check("学生提交作业", code in (200, 201), f"task_id={task_id} code={code}")

    # 15. 教师获取待批阅提交
    code, resp = api("GET", "/submissions?reviewed=false", token=admin_token)
    check("获取待批阅提交", code == 200, f"count={len(resp) if isinstance(resp, list) else 'err'}")

    # 16. 教师批阅提交
    if isinstance(resp, list) and resp:
        submission_id = resp[0].get("id")
        code, resp = api(
            "POST",
            f"/submissions/{submission_id}/review",
            token=admin_token,
            body={"score": 90, "feedback": "观察细致，记录详细，建议补充浇水时间。"},
        )
        check("教师批阅提交", code in (200, 201), f"submission_id={submission_id} score={resp.get('score') if isinstance(resp, dict) else 'err'} code={code}")

    # 17. 仪表盘概览
    code, resp = api("GET", "/dashboard/overview", token=admin_token)
    check("仪表盘概览", code == 200, f"total_nodes={resp.get('total_nodes')} pending_tasks={resp.get('pending_tasks')}")

    # 18. 组件汇总
    code, resp = api("GET", "/dashboard/component-summary", token=admin_token)
    check("组件汇总", code == 200, f"types={len(resp) if isinstance(resp, list) else 'err'}")

    # 19. 清理：删除测试小组和班级（非阻塞，仅打印警告）
    if group_id:
        code, _ = api("DELETE", f"/groups/{group_id}", token=admin_token)
        if code not in (200, 204):
            print(f"[WARN] 清理：删除测试小组 - code={code} (非阻塞，测试数据可通过 init_db 重置)")
    if classroom_id:
        code, _ = api("DELETE", f"/classrooms/{classroom_id}", token=admin_token)
        if code not in (200, 204):
            print(f"[WARN] 清理：删除测试班级 - code={code} (非阻塞，测试数据可通过 init_db 重置)")

    print()
    print(f"=== 结果: {len(failures)} 失败 / 共 {total} 项 ===")
    if failures:
        print("失败项:", ", ".join(failures))
        sys.exit(1)
    else:
        print("全部通过")


if __name__ == "__main__":
    main()

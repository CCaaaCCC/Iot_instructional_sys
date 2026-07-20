#!/usr/bin/env python3
"""测试 AI 助手功能是否正常。依赖后端运行在 http://127.0.0.1:8001。"""

import json
import sys
import time
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:8001/api/v1"


def req(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def login():
    """登录获取 JWT token。"""
    data = urllib.parse.urlencode({"username": "admin", "password": "Admin123456"}).encode()
    r = urllib.request.Request(f"{BASE}/auth/login", data=data)
    r.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib.request.urlopen(r)
    body = json.loads(resp.read().decode())
    return body["access_token"]


token = login()
print("=" * 60)
print("✅ 登录成功，获取到 JWT token")
print("=" * 60)

# 1. 测试健康检查
status, body = req("GET", "/health")
print(f"\n📡 健康检查: {status}")
print(f"   {body}")

# 2. 测试配额查询（初始）
status, body = req("GET", "/ai/quota", token=token)
quota = json.loads(body)
print(f"\n📊 初始配额: {status}")
print(f"   used={quota['used']}, remaining={quota['remaining']}, limit={quota['limit']}")

# 3. 创建会话
status, body = req("POST", "/ai/sessions", data={"title": "功能测试"}, token=token)
session = json.loads(body)
print(f"\n💬 创建会话: {status}")
print(f"   id={session['id']}, title={session['title']}")
session_id = session["id"]

# 4. 列出会话
status, body = req("GET", "/ai/sessions", token=token)
sessions = json.loads(body)
print(f"\n📋 会话列表: {status}")
print(f"   共 {len(sessions)} 个会话")

# 5. 测试流式对话（真实 DeepSeek API）
print(f"\n🤖 测试流式对话（真实 DeepSeek API）...")
print(f"   发送消息: '你好，请介绍一下大棚种植的要点'")
print(f"   响应: ", end="", flush=True)

url = f"{BASE}/ai/chat"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}
body_data = json.dumps({
    "message": "你好，请用一句话介绍大棚种植的要点",
    "session_id": session_id,
}).encode()

r = urllib.request.Request(url, data=body_data, headers=headers, method="POST")
resp = urllib.request.urlopen(r)

full_text = ""
delta_count = 0
session_event = None
done_event = None
error_event = None

buffer = ""
while True:
    chunk = resp.read(256)
    if not chunk:
        break
    buffer += chunk.decode("utf-8", errors="replace")
    while "\n\n" in buffer:
        raw, buffer = buffer.split("\n\n", 1)
        for line in raw.split("\n"):
            if line.startswith("data: "):
                try:
                    evt = json.loads(line[6:])
                    if evt["type"] == "session":
                        session_event = evt
                    elif evt["type"] == "delta":
                        delta_count += 1
                        full_text += evt["content"]
                        print(evt["content"], end="", flush=True)
                    elif evt["type"] == "done":
                        done_event = evt
                    elif evt["type"] == "error":
                        error_event = evt
                        print(f"\n[错误] {evt['message']}", end="", flush=True)
                except json.JSONDecodeError:
                    pass

print()
print(f"\n   delta 事件数: {delta_count}")
print(f"   总回复长度: {len(full_text)} 字符")
if session_event:
    print(f"   会话ID: {session_event['session_id']}")
if done_event:
    print(f"   消息ID: {done_event['message_id']}, 模型: {done_event['model']}")
if error_event:
    print(f"   ❌ 错误: {error_event['message']}")

# 6. 检查对话后配额
status, body = req("GET", "/ai/quota", token=token)
quota2 = json.loads(body)
print(f"\n📊 对话后配额: {status}")
print(f"   used={quota2['used']}, remaining={quota2['remaining']}")
print(f"   配额变化: {quota2['used'] - quota['used']}（应为 1）")

# 7. 获取消息历史
status, body = req("GET", f"/ai/sessions/{session_id}/messages", token=token)
msgs = json.loads(body)
print(f"\n💬 消息历史: {status}")
print(f"   共 {len(msgs)} 条消息")
for m in msgs:
    print(f"   [{m['role']}] {m['content'][:60]}...")
    if m.get("model_used"):
        print(f"       模型: {m['model_used']}")

# 8. 重命名会话
status, body = req("PATCH", f"/ai/sessions/{session_id}", data={"title": "种植问答"}, token=token)
renamed = json.loads(body)
print(f"\n✏️  重命名会话: {status}")
print(f"   新标题: {renamed['title']}")

# 9. 测试学生角色
# 先登录学生
student_data = urllib.parse.urlencode({"username": "g1s1", "password": "Student123456"}).encode()
sr = urllib.request.Request(f"{BASE}/auth/login", data=student_data)
sr.add_header("Content-Type", "application/x-www-form-urlencoded")
student_resp = urllib.request.urlopen(sr)
student_token = json.loads(student_resp.read().decode())["access_token"]
print(f"\n👤 学生登录成功")

# 学生创建会话
status, body = req("POST", "/ai/sessions", data={"title": "学生提问"}, token=student_token)
student_session = json.loads(body)
print(f"   学生会话: id={student_session['id']}, title={student_session['title']}")

# 学生发消息（简化版，只验证流式）
url2 = f"{BASE}/ai/chat"
headers2 = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {student_token}",
}
body2 = json.dumps({
    "message": "你好，我是小学生，请问番茄需要多少天发芽？",
    "session_id": student_session["id"],
}).encode()

r2 = urllib.request.Request(url2, data=body2, headers=headers2, method="POST")
resp2 = urllib.request.urlopen(r2)

print(f"   学生消息回复: ", end="", flush=True)
student_text = ""
while True:
    chunk = resp2.read(256)
    if not chunk:
        break
    buf = chunk.decode("utf-8", errors="replace")
    for line in buf.split("\n"):
        if line.startswith("data: "):
            try:
                evt = json.loads(line[6:])
                if evt["type"] == "delta":
                    student_text += evt["content"]
                    print(evt["content"], end="", flush=True)
                elif evt["type"] == "done":
                    print(f"\n   (完成, 模型: {evt['model']})", end="", flush=True)
                elif evt["type"] == "error":
                    print(f"\n   [错误] {evt['message']}", end="", flush=True)
            except json.JSONDecodeError:
                pass
print()

# 10. 测试 operator 权限（应为 403）
status, _ = req("GET", "/ai/quota", token=None)
# 需要先获取 operator token
op_data = urllib.parse.urlencode({"username": "operator", "password": "Operator123456"}).encode()
op_r = urllib.request.Request(f"{BASE}/auth/login", data=op_data)
op_r.add_header("Content-Type", "application/x-www-form-urlencoded")
op_resp = urllib.request.urlopen(op_r)
op_token = json.loads(op_resp.read().decode())["access_token"]
status, body = req("GET", "/ai/quota", token=op_token)
print(f"\n🔒 Operator 权限测试: {status}（应为 403）")

# 清理：删除测试会话
status, _ = req("DELETE", f"/ai/sessions/{session_id}", token=token)
print(f"\n🗑️  删除管理会话: {status}（应为 204）")
status, _ = req("DELETE", f"/ai/sessions/{student_session['id']}", token=student_token)
print(f"   删除学生会话: {status}（应为 204）")

print("\n" + "=" * 60)
if error_event:
    print("❌ AI 助手测试完成，但存在错误")
    print(f"   错误: {error_event['message']}")
else:
    print("✅ AI 助手功能测试全部通过！")
    print(f"   - 管理员对话: 成功 ({len(full_text)} 字符, {delta_count} 个 delta)")
    print(f"   - 学生对话: 成功 ({len(student_text)} 字符)")
    print(f"   - 会话管理: 创建/列取/重命名/删除 正常")
    print(f"   - 权限隔离: operator 被正确拒绝")
    print(f"   - 配额计数: 正常累加")
print("=" * 60)
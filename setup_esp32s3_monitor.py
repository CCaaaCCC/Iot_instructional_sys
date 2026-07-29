"""
为 ESP32-S3 上位机创建测试数据：
  classroom + group + device_node + 3 个 component(fan/pump/light) + esp32s3_monitor token

用法：python setup_esp32s3_monitor.py
前提：后端运行在 8001 端口
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8001/api/v1"


def post(path, data, token=None, form=False):
    url = f"{BASE}{path}"
    headers = {}
    body = None
    if form:
        body = "&".join(f"{k}={v}" for k, v in data.items()).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None


def get(path, token=None):
    url = f"{BASE}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None


def main():
    # 1. 登录
    print("=== 1. 登录 admin ===")
    r = post("/auth/login", {"username": "admin", "password": "Admin123456"}, form=True)
    if not r:
        print("登录失败"); sys.exit(1)
    token = r["access_token"]
    print(f"  token: {token[:20]}...")

    # 2. 查看 classrooms
    print("\n=== 2. 查看 classrooms ===")
    classrooms = get("/classrooms", token=token) or []
    for c in classrooms:
        print(f"  id={c['id']} name={c['name']}")
    if not classrooms:
        print("  无 classroom，创建一个")
        c = post("/classrooms", {"name": "测试班级", "grade": "四年级"}, token=token)
        if not c:
            print("创建 classroom 失败"); sys.exit(1)
        classrooms = [c]
    classroom_id = classrooms[0]["id"]
    print(f"  使用 classroom_id={classroom_id}")

    # 3. 创建 device_node
    print("\n=== 3. 创建 device_node ===")
    # 先看现有 nodes
    nodes = get("/device-nodes", token=token) or []
    for n in nodes[:5]:
        print(f"  id={n['id']} name={n['name']} online={n.get('online')}")
    # 创建新 node（DeviceNodeCreate 只有 name + location）
    node = post("/device-nodes", {
        "name": "上位机测试节点",
        "location": "测试台",
    }, token=token)
    if not node:
        print("创建 device_node 失败"); sys.exit(1)
    node_id = node["id"]
    print(f"  ✅ device_node id={node_id} name={node['name']}")

    # 4. 创建 group（绑定 classroom + node）
    print("\n=== 4. 创建 group ===")
    group = post("/groups", {
        "name": "上位机测试组",
        "class_id": classroom_id,
        "node_id": node_id,
    }, token=token)
    if not group:
        print("创建 group 失败"); sys.exit(1)
    group_id = group["id"]
    print(f"  ✅ group id={group_id} name={group['name']}")

    # 5. 创建 3 个 component（fan/pump/light）
    #    ComponentCreate 字段：name, type, metric(可选)；status 默认 off
    print("\n=== 5. 创建 components ===")
    components = []
    for comp_type, comp_name in [("fan", "风扇"), ("pump", "水泵"), ("light", "补光灯")]:
        comp = post(f"/device-nodes/{node_id}/components", {
            "name": comp_name,
            "type": comp_type,
        }, token=token)
        if comp:
            components.append(comp)
            print(f"  ✅ {comp_type}: id={comp['id']} name={comp['name']}")
        else:
            print(f"  ❌ {comp_type} 创建失败")

    # 6. 创建 esp32s3_monitor device token
    print("\n=== 6. 创建 esp32s3_monitor device token ===")
    tk = post("/device-tokens", {
        "group_id": group_id,
        "device_type": "esp32s3_monitor",
        "device_name": "上位机-ESP32-S3",
        "node_id": node_id,
    }, token=token)
    if not tk:
        print("创建 device token 失败"); sys.exit(1)
    print(f"  ✅ token id={tk['id']}")
    print(f"  token (明文，仅此一次): {tk['token']}")

    # 7. 汇总
    print("\n" + "=" * 60)
    print("  测试数据创建完成！")
    print("=" * 60)
    print(f"  device_node id : {node_id}  ← 填入 wifi_config.h 的 NODE_ID")
    print(f"  group id       : {group_id}")
    print(f"  components     : {[c['id'] for c in components]}")
    print(f"  device token   : {tk['token']}")
    print()
    print("  下一步：")
    print(f"  1. 编辑 wifi_config.h：NODE_ID={node_id}, MQTT_BROKER_HOST=<电脑局域网IP>")
    print("  2. 烧录上位机固件")
    print("  3. 观察后端日志确认收到数据上报")


if __name__ == "__main__":
    main()

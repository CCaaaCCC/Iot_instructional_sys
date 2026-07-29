"""
ESP32-S3 上位机云端通信链路验证脚本（模拟 cloud_comm.cpp 行为）

验证项：
  1. 上报传感器数据 → 后端数据库写入 → 后端日志确认
  2. 订阅控制命令 → 验证 payload 包含 component_type 字段
  3. 上报 online 状态 → 后端设备节点变在线

用法：python verify_esp32s3_monitor.py
前提：后端运行在 8001，mosquitto 运行在 1883
"""
import json
import random
import signal
import sys
import time
from datetime import datetime

import paho.mqtt.client as mqtt

NODE_ID = 4  # 与 setup_esp32s3_monitor.py 创建的 device_node id 一致
MQTT_HOST = "localhost"
MQTT_PORT = 1883

TOPIC_SENSOR_DATA = "greenhouse/sensor/data"
TOPIC_DEVICE_STATUS = "greenhouse/device/status"
TOPIC_DEVICE_CONTROL = "greenhouse/device/control"

running = True
report_count = 0


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"✅ MQTT 已连接 {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(TOPIC_DEVICE_CONTROL)
        print(f"📥 订阅: {TOPIC_DEVICE_CONTROL}")
        # 上报 online
        payload = json.dumps({"node_id": NODE_ID, "online": True})
        client.publish(TOPIC_DEVICE_STATUS, payload, retain=True)
        print(f"📡 上报 online 状态: {payload}")
    else:
        print(f"❌ MQTT 连接失败: rc={reason_code}")


def on_message(client, userdata, msg):
    """收到控制命令 — 验证 payload 格式"""
    try:
        data = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"⚠️ JSON 解析失败: {e}")
        return

    print("\n" + "=" * 60)
    print(f"📨 收到控制命令 (topic={msg.topic})")
    print(f"   完整 payload: {json.dumps(data, ensure_ascii=False)}")

    # 验证关键字段
    cmd_node = data.get("node_id")
    comp_type = data.get("component_type", "<缺失>")
    action = data.get("action", "<缺失>")

    if cmd_node != NODE_ID:
        print(f"   ⏭️ node_id={cmd_node} 不是本节点 {NODE_ID}，忽略")
        return

    print(f"   node_id        : {cmd_node}")
    print(f"   component_type : {comp_type}  ← 上位机据此映射 P/L/F")
    print(f"   action         : {action}")
    print(f"   message        : {data.get('message', '')}")

    # 模拟 cloud_comm.cpp 的映射逻辑
    dev_map = {"fan": "F", "pump": "P", "light": "L"}
    dev = dev_map.get(comp_type)
    if not dev:
        print(f"   ⚠️ 未知 component_type，无法映射")
        return

    if action == "on":
        print(f"   → UART 命令: {dev}:1")
    elif action == "off":
        print(f"   → UART 命令: {dev}:0")
    elif action == "auto":
        print(f"   → UART 命令: (auto, 下位机不支持, 忽略)")
    print("=" * 60 + "\n")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    print(f"⚠️ MQTT 断开: rc={reason_code}")


def publish_sensor_data(client):
    """上报模拟传感器数据"""
    global report_count
    report_count += 1
    payload = {
        "node_id": NODE_ID,
        "air_temp": round(random.uniform(25, 32), 1),
        "air_humidity": round(random.uniform(50, 75), 1),
        "soil_humidity": round(random.uniform(35, 55), 1),
        "light_intensity": random.randint(10000, 50000),
        "soil_ph": round(random.uniform(6.0, 7.0), 2),
        "co2": random.randint(400, 800),
    }
    client.publish(TOPIC_SENSOR_DATA, json.dumps(payload))
    print(f"📊 #{report_count} 上报传感器: temp={payload['air_temp']}°C "
          f"hum={payload['air_humidity']}% co2={payload['co2']}ppm")
    return payload


def stop_handler(*args):
    global running
    running = False
    print("\n🛑 收到停止信号，准备退出...")


def main():
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    print("=" * 60)
    print(f"  ESP32-S3 上位机通信验证 (模拟 cloud_comm)")
    print(f"  node_id={NODE_ID}  broker={MQTT_HOST}:{MQTT_PORT}")
    print("=" * 60)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"verify-esp32s3-monitor-{NODE_ID}",
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # LWT：掉线时自动发布 offline
    lwt = json.dumps({"node_id": NODE_ID, "online": False})
    client.will_set(TOPIC_DEVICE_STATUS, lwt, retain=True)

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    except Exception as e:
        print(f"❌ 无法连接 MQTT broker: {e}")
        sys.exit(1)

    client.loop_start()

    last_report = 0
    last_status = 0

    print("\n💡 提示：在另一个终端运行以下命令触发控制命令测试：")
    print(f"   python -c \"import urllib.request,json; "
          f"r=urllib.request.urlopen(urllib.request.Request("
          f"'http://127.0.0.1:8001/api/v1/auth/login',"
          f"data=b'username=admin&password=Admin123456',"
          f"headers={{'Content-Type':'application/x-www-form-urlencoded'}})); "
          f"t=json.loads(r.read())['access_token']; "
          f"urllib.request.urlopen(urllib.request.Request("
          f"'http://127.0.0.1:8001/api/v1/device-nodes/4/components/12/control',"
          f"data=json.dumps({{'action':'on'}}).encode(),"
          f"headers={{'Content-Type':'application/json','Authorization':f'Bearer {{t}}'}}))\"")
    print()

    try:
        while running:
            now = time.time()
            # 每 5 秒上报一次传感器数据（测试用，比实际 10s 快）
            if now - last_report >= 5:
                publish_sensor_data(client)
                last_report = now
            # 每 20 秒上报 online 心跳
            if now - last_status >= 20:
                client.publish(TOPIC_DEVICE_STATUS,
                               json.dumps({"node_id": NODE_ID, "online": True}),
                               retain=True)
                last_status = now
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        # 上报 offline
        client.publish(TOPIC_DEVICE_STATUS,
                       json.dumps({"node_id": NODE_ID, "online": False}),
                       retain=True)
        client.loop_stop()
        client.disconnect()
        print(f"\n✅ 已退出，共上报 {report_count} 条数据")


if __name__ == "__main__":
    main()

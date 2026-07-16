"""
智慧大棚模拟硬件脚本

模拟 IoT 硬件设备与后台管理系统的交互：
1. 传感器定时上报环境数据（空气温度/湿度、土壤温度/湿度、光照强度、土壤pH）
2. 设备状态上报与控制响应
3. 触发自动化规则验证

使用方法：
    python simulate_hardware.py [--interval 5] [--duration 120] [--base-url http://127.0.0.1:8000]

默认账号: admin / 见 .env 中 INIT_ADMIN_PASSWORD
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# MQTT 支持（可选依赖）
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


# ── 配置 ──────────────────────────────────────────────

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_INTERVAL = 5       # 上报间隔（秒）
DEFAULT_DURATION = 120     # 总运行时长（秒），0 表示无限

# 传感器数据模拟范围
SENSOR_RANGES = {
    "air_temp":        (18.0, 38.0),   # 空气温度 °C
    "air_humidity":    (30.0, 90.0),   # 空气湿度 %
    "soil_temp":       (15.0, 30.0),   # 土壤温度 °C
    "soil_humidity":   (20.0, 80.0),   # 土壤湿度 %
    "light_intensity": (50.0, 800.0),  # 光照强度 lux
    "soil_ph":         (5.5, 7.5),     # 土壤 pH
}

# 模拟日间变化：白天温度高、光照强，夜间反之
def _daytime_factor(now: datetime) -> float:
    """返回 0~1 的日间因子，正午最高，午夜最低"""
    hour = now.hour + now.minute / 60.0
    # 用正弦模拟，6:00 最低，14:00 最高
    return 0.5 + 0.5 * max(0, (hour - 6) / 8 - 1) if hour < 6 or hour > 22 else \
           0.5 + 0.5 * ((hour - 6) / 8) if hour <= 14 else \
           0.5 + 0.5 * (1 - (hour - 14) / 8)


def daytime_adjusted_value(key: str, base_now: float) -> float:
    """根据日间因子微调传感器值"""
    factor = _daytime_factor(datetime.now())
    lo, hi = SENSOR_RANGES[key]
    if key == "air_temp":
        # 白天偏高温区间
        return lo + (hi - lo) * (0.3 + 0.7 * factor) + random.gauss(0, 0.5)
    elif key == "light_intensity":
        # 白天光照强
        return lo + (hi - lo) * factor + random.gauss(0, 10)
    elif key in ("air_humidity", "soil_humidity"):
        # 白天湿度偏低
        return lo + (hi - lo) * (1 - 0.4 * factor) + random.gauss(0, 1)
    else:
        return random.uniform(lo, hi)


# ── HTTP 工具 ─────────────────────────────────────────

class APIClient:
    """简单的 API 客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def login(self, username: str, password: str) -> bool:
        # OAuth2 使用 form-urlencoded 格式
        data = f"username={username}&password={password}".encode()
        req = Request(
            f"{self.base_url}/api/v1/auth/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            resp = urlopen(req)
            body = json.loads(resp.read())
            self.token = body["access_token"]
            return True
        except HTTPError as e:
            print(f"[ERROR] 登录失败: {e.code} {e.read().decode()}")
            return False

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get(self, path: str, params: dict | None = None) -> dict | list | None:
        url = f"{self.base_url}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if qs:
                url += f"?{qs}"
        req = Request(url, headers=self._headers(), method="GET")
        try:
            resp = urlopen(req)
            return json.loads(resp.read())
        except HTTPError as e:
            print(f"[ERROR] GET {path}: {e.code} {e.read().decode()}")
            return None

    def post(self, path: str, body: dict | None = None) -> dict | None:
        data = json.dumps(body or {}).encode()
        req = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            resp = urlopen(req)
            return json.loads(resp.read())
        except HTTPError as e:
            print(f"[ERROR] POST {path}: {e.code} {e.read().decode()}")
            return None

    def patch(self, path: str, body: dict | None = None) -> dict | None:
        data = json.dumps(body or {}).encode()
        req = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(),
            method="PATCH",
        )
        try:
            resp = urlopen(req)
            return json.loads(resp.read())
        except HTTPError as e:
            print(f"[ERROR] PATCH {path}: {e.code} {e.read().decode()}")
            return None


# ── 模拟器 ────────────────────────────────────────────

class HardwareSimulator:
    """模拟大棚硬件设备"""

    def __init__(self, client: APIClient, interval: int = 5):
        self.client = client
        self.interval = interval
        self.sensor_devices: list[dict] = []
        self.control_devices: list[dict] = []
        self.report_count = 0

    def discover_devices(self) -> bool:
        """发现系统中已有的设备"""
        devices = self.client.get("/api/v1/devices")
        if devices is None:
            return False

        for d in devices:
            if d["type"] == "sensor":
                self.sensor_devices.append(d)
            else:
                self.control_devices.append(d)

        print(f"[DISCOVER] 发现 {len(self.sensor_devices)} 个传感器, "
              f"{len(self.control_devices)} 个控制设备")
        for d in self.sensor_devices:
            print(f"  传感器: {d['name']} (id={d['id']})")
        for d in self.control_devices:
            print(f"  控制器: {d['name']} (id={d['id']}, type={d['type']}, status={d['status']})")
        return True

    def ensure_sensor_device(self) -> bool:
        """确保至少有一个传感器设备，没有则创建"""
        if self.sensor_devices:
            return True
        print("[SETUP] 未发现传感器设备，创建模拟传感器...")
        device = self.client.post("/api/v1/devices", {
            "name": "SimSensor-1",
            "type": "sensor",
            "location": "模拟大棚-A区",
        })
        if device:
            self.sensor_devices.append(device)
            print(f"  创建成功: {device['name']} (id={device['id']})")
            return True
        return False

    def ensure_control_devices(self) -> None:
        """确保有控制设备用于测试"""
        existing_types = {d["type"] for d in self.control_devices}
        needed = [
            ("fan", "SimFan-1", "模拟大棚-A区"),
            ("pump", "SimPump-1", "模拟大棚-A区"),
            ("light", "SimLight-1", "模拟大棚-A区"),
        ]
        for dtype, name, loc in needed:
            if dtype not in existing_types:
                print(f"[SETUP] 创建模拟控制设备 {name}...")
                device = self.client.post("/api/v1/devices", {
                    "name": name,
                    "type": dtype,
                    "location": loc,
                })
                if device:
                    self.control_devices.append(device)
                    print(f"  创建成功: {device['name']} (id={device['id']})")

    def generate_sensor_data(self, device_id: int) -> dict:
        """生成一组模拟传感器数据"""
        data = {
            "device_id": device_id,
            "air_temp":        round(daytime_adjusted_value("air_temp", 0), 1),
            "air_humidity":    round(daytime_adjusted_value("air_humidity", 0), 1),
            "soil_temp":       round(daytime_adjusted_value("soil_temp", 0), 1),
            "soil_humidity":   round(daytime_adjusted_value("soil_humidity", 0), 1),
            "light_intensity": round(max(0, daytime_adjusted_value("light_intensity", 0)), 1),
            "soil_ph":         round(daytime_adjusted_value("soil_ph", 0), 2),
        }
        return data

    def report_sensor_data(self) -> dict | None:
        """上报传感器数据"""
        results = []
        for sensor in self.sensor_devices:
            data = self.generate_sensor_data(sensor["id"])
            result = self.client.post("/api/v1/sensors/data", data)
            if result:
                self.report_count += 1
                results.append(data)
                print(f"  [{sensor['name']}] "
                      f"气温={data['air_temp']}°C  气湿={data['air_humidity']}%  "
                      f"土温={data['soil_temp']}°C  土湿={data['soil_humidity']}%  "
                      f"光照={data['light_intensity']}lux  pH={data['soil_ph']}")
            else:
                print(f"  [{sensor['name']}] 上报失败")
        return results[0] if results else None

    def check_rules(self, sensor_data: dict) -> None:
        """检查传感器数据是否可能触发规则，并打印提示"""
        rules = self.client.get("/api/v1/rules")
        if not rules:
            return
        for rule in rules:
            if not rule.get("enabled"):
                continue
            metric = rule["metric"]
            threshold = rule["threshold"]
            operator = rule["operator"]
            value = sensor_data.get(metric)
            if value is None:
                continue
            triggered = False
            if operator == ">" and value > threshold:
                triggered = True
            elif operator == ">=" and value >= threshold:
                triggered = True
            elif operator == "<" and value < threshold:
                triggered = True
            elif operator == "<=" and value <= threshold:
                triggered = True
            if triggered:
                print(f"  [RULE] 规则触发: [{rule['name']}] "
                      f"{metric}={value} {operator} {threshold} → "
                      f"{rule['action_device_type']}.{rule['action']}")

    def simulate_device_control(self) -> None:
        """模拟设备控制操作（随机开关一个控制设备）"""
        if not self.control_devices:
            return
        device = random.choice(self.control_devices)
        # 交替开关
        new_action = "off" if device["status"] == "on" else "on"
        print(f"  [CONTROL] {device['name']}: {device['status']} → {new_action}")
        result = self.client.post(
            f"/api/v1/devices/{device['id']}/control",
            {"action": new_action, "message": f"模拟硬件控制: 切换为{new_action}"},
        )
        if result:
            device["status"] = new_action
            print(f"  [CONTROL] {device['name']} 状态已更新为 {result['status']}")

    def check_device_status(self) -> None:
        """查询所有设备最新状态"""
        devices = self.client.get("/api/v1/devices")
        if devices:
            for d in devices:
                status_icon = "[ON]" if d["online"] else "[OFF]"
                print(f"  {status_icon} {d['name']} ({d['type']}): "
                      f"status={d['status']}, online={d['online']}")

    def run(self, duration: int = 0) -> None:
        """主循环：定时上报传感器数据"""
        print("\n" + "=" * 60)
        print("  智慧大棚硬件模拟器启动")
        print(f"  上报间隔: {self.interval}s | 运行时长: {'无限' if duration == 0 else f'{duration}s'}")
        print("=" * 60 + "\n")

        if not self.discover_devices():
            print("[FATAL] 无法发现设备，退出")
            return

        self.ensure_sensor_device()
        self.ensure_control_devices()

        # 初始状态查询
        print("\n[INIT] 设备初始状态:")
        self.check_device_status()

        start = time.time()
        control_counter = 0

        try:
            while True:
                elapsed = time.time() - start
                if duration > 0 and elapsed >= duration:
                    print(f"\n[DONE] 运行 {duration}s 完成，共上报 {self.report_count} 条传感器数据")
                    break

                now = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{now}] 第 {self.report_count + 1} 次上报")

                # 上报传感器数据
                latest = self.report_sensor_data()

                # 检查规则触发
                if latest:
                    self.check_rules(latest)

                # 每 3 个周期模拟一次设备控制
                control_counter += 1
                if control_counter >= 3:
                    control_counter = 0
                    self.simulate_device_control()

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print(f"\n[STOP] 用户中断，共上报 {self.report_count} 条传感器数据")

        # 最终状态
        print("\n[FINAL] 最终设备状态:")
        self.check_device_status()

        # 打印最新传感器数据
        print("\n[FINAL] 最新传感器数据:")
        latest_data = self.client.get("/api/v1/sensors/data/latest")
        if latest_data:
            print(f"  气温={latest_data.get('air_temp')}°C  "
                  f"气湿={latest_data.get('air_humidity')}%  "
                  f"土温={latest_data.get('soil_temp')}°C  "
                  f"土湿={latest_data.get('soil_humidity')}%  "
                  f"光照={latest_data.get('light_intensity')}lux  "
                  f"pH={latest_data.get('soil_ph')}")


# ── 快速验证测试 ──────────────────────────────────────

def quick_test(client: APIClient) -> bool:
    """快速验证所有核心 API 是否正常"""
    print("\n" + "=" * 60)
    print("  快速 API 验证测试")
    print("=" * 60 + "\n")

    tests = []

    # 1. 健康检查
    try:
        resp = urlopen(f"{client.base_url}/health")
        ok = resp.status == 200
        tests.append(("健康检查 /health", ok))
    except Exception as e:
        tests.append(("健康检查 /health", False))

    # 2. 登录
    ok = client.login("admin", "123456")
    tests.append(("登录 /api/v1/auth/login", ok))
    if not ok:
        print("登录失败，后续测试跳过")
        for name, result in tests:
            icon = "PASS" if result else "FAIL"
            print(f"  [{icon}] {name}")
        return False

    # 3. 获取当前用户
    me = client.get("/api/v1/auth/me")
    tests.append(("获取当前用户 /api/v1/auth/me", me is not None))

    # 4. 设备列表
    devices = client.get("/api/v1/devices")
    tests.append(("设备列表 /api/v1/devices", devices is not None))

    # 5. 创建传感器数据
    sensor = next((d for d in (devices or []) if d["type"] == "sensor"), None)
    if sensor:
        data = {
            "device_id": sensor["id"],
            "air_temp": 25.5,
            "air_humidity": 60.0,
            "soil_temp": 20.0,
            "soil_humidity": 45.0,
            "light_intensity": 350.0,
            "soil_ph": 6.8,
        }
        result = client.post("/api/v1/sensors/data", data)
        tests.append(("上报传感器数据 /api/v1/sensors/data", result is not None))
    else:
        tests.append(("上报传感器数据 /api/v1/sensors/data", False))

    # 6. 查询传感器数据
    sensor_list = client.get("/api/v1/sensors/data", {"limit": 5})
    tests.append(("查询传感器数据 /api/v1/sensors/data", sensor_list is not None))

    # 7. 最新传感器数据
    latest = client.get("/api/v1/sensors/data/latest")
    tests.append(("最新传感器数据 /api/v1/sensors/data/latest", latest is not None))

    # 8. ECharts 数据
    echarts = client.get("/api/v1/sensors/data/echarts", {"limit": 10})
    tests.append(("ECharts 数据 /api/v1/sensors/data/echarts", echarts is not None))

    # 9. 规则列表
    rules = client.get("/api/v1/rules")
    tests.append(("规则列表 /api/v1/rules", rules is not None))

    # 10. 设备控制
    control_device = next((d for d in (devices or []) if d["type"] != "sensor"), None)
    if control_device:
        result = client.post(
            f"/api/v1/devices/{control_device['id']}/control",
            {"action": "on", "message": "快速测试: 开启设备"},
        )
        tests.append(("设备控制 /api/v1/devices/{id}/control", result is not None))
        # 关掉
        client.post(
            f"/api/v1/devices/{control_device['id']}/control",
            {"action": "off", "message": "快速测试: 关闭设备"},
        )
    else:
        tests.append(("设备控制 /api/v1/devices/{id}/control", False))

    # 11. 作物列表
    crops = client.get("/api/v1/crops")
    tests.append(("作物列表 /api/v1/crops", crops is not None))

    # 12. 任务列表
    tasks = client.get("/api/v1/tasks")
    tests.append(("任务列表 /api/v1/tasks", tasks is not None))

    # 13. Dashboard
    dashboard = client.get("/api/v1/dashboard/overview")
    tests.append(("仪表盘 /api/v1/dashboard/overview", dashboard is not None))

    # 14. 日志
    logs = client.get("/api/v1/logs/operations", {"limit": 5})
    tests.append(("操作日志 /api/v1/logs/operations", logs is not None))

    # 打印结果
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    print(f"\n测试结果: {passed}/{total} 通过\n")
    for name, ok in tests:
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {name}")

    return passed == total


# ── MQTT 模拟模式 ─────────────────────────────────────

def run_mqtt_mode(args) -> None:
    """使用 MQTT 协议上报传感器数据（无需登录后端）"""

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"[MQTT] 已连接到 broker {args.mqtt_host}:{args.mqtt_port}")
        else:
            print(f"[MQTT] 连接失败 reason_code={reason_code}")

    mqtt_client = mqtt.Client(client_id="greenhouse-simulator", protocol=mqtt.MQTTv311)
    mqtt_client.on_connect = on_connect
    try:
        mqtt_client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
    except Exception as e:
        print(f"[FATAL] 无法连接到 MQTT broker: {e}")
        print("  请先启动 Mosquitto: mosquitto -v")
        sys.exit(1)

    mqtt_client.loop_start()

    # 先用 HTTP 获取设备列表
    client = APIClient(args.base_url)
    try:
        urlopen(f"{args.base_url}/health")
    except URLError:
        print(f"[WARN] HTTP 后端不可达，使用 MQTT 上报到 device_id=1")
        device_id = 1
    else:
        client.login(args.username, args.password)
        devices = client.get("/api/v1/devices")
        sensor = next((d for d in (devices or []) if d["type"] == "sensor"), None)
        if sensor:
            device_id = sensor["id"]
            print(f"[MQTT] 使用传感器设备: {sensor['name']} (id={device_id})")
        else:
            device_id = 1
            print("[MQTT] 未找到传感器设备，使用 device_id=1")

    print("\n" + "=" * 60)
    print("  智慧大棚 MQTT 模拟器启动")
    print(f"  上报间隔: {args.interval}s | Broker: {args.mqtt_host}:{args.mqtt_port}")
    print("=" * 60 + "\n")

    report_count = 0
    start = time.time()

    try:
        while True:
            elapsed = time.time() - start
            if args.duration > 0 and elapsed >= args.duration:
                print(f"\n[DONE] 运行 {args.duration}s 完成，共上报 {report_count} 条")
                break

            now = datetime.now().strftime("%H:%M:%S")
            data = {
                "device_id": device_id,
                "air_temp": round(daytime_adjusted_value("air_temp", 0), 1),
                "air_humidity": round(daytime_adjusted_value("air_humidity", 0), 1),
                "soil_temp": round(daytime_adjusted_value("soil_temp", 0), 1),
                "soil_humidity": round(daytime_adjusted_value("soil_humidity", 0), 1),
                "light_intensity": round(max(0, daytime_adjusted_value("light_intensity", 0)), 1),
                "soil_ph": round(daytime_adjusted_value("soil_ph", 0), 2),
                "timestamp": datetime.now().isoformat(),
            }
            payload = json.dumps(data)
            mqtt_client.publish("greenhouse/sensor/data", payload)
            report_count += 1
            print(f"  [{now}] MQTT 上报 #{report_count}: "
                  f"气温={data['air_temp']}°C 气湿={data['air_humidity']}%  "
                  f"土温={data['soil_temp']}°C 土湿={data['soil_humidity']}%  "
                  f"光照={data['light_intensity']}lux  pH={data['soil_ph']}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n[STOP] 用户中断，共上报 {report_count} 条")

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[MQTT] 已断开连接")


# ── 主入口 ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="智慧大棚硬件模拟器")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="后端 API 地址")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="上报间隔（秒）")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="运行时长（秒），0=无限")
    parser.add_argument("--username", default="admin", help="登录用户名")
    parser.add_argument("--password", default="123456", help="登录密码")
    parser.add_argument("--test", action="store_true", help="仅运行快速验证测试")
    parser.add_argument("--protocol", choices=["http", "mqtt"], default="http",
                        help="通信协议: http (默认) 或 mqtt")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT broker 地址")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker 端口")
    args = parser.parse_args()

    # MQTT 模式
    if args.protocol == "mqtt":
        if not HAS_MQTT:
            print("[FATAL] paho-mqtt 未安装，请执行: pip install paho-mqtt")
            sys.exit(1)
        run_mqtt_mode(args)
        return

    client = APIClient(args.base_url)

    # 先检查后端是否可达
    try:
        urlopen(f"{args.base_url}/health")
    except URLError:
        print(f"[FATAL] 后端服务不可达: {args.base_url}")
        print("  请先启动后端: python -m uvicorn app.main:app --port 8000")
        sys.exit(1)

    # 登录
    print(f"[AUTH] 登录中... ({args.username})")
    if not client.login(args.username, args.password):
        sys.exit(1)
    print("[AUTH] 登录成功\n")

    if args.test:
        quick_test(client)
        return

    # 运行模拟器
    sim = HardwareSimulator(client, interval=args.interval)
    sim.run(duration=args.duration)


if __name__ == "__main__":
    main()

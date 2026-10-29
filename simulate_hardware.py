"""
智慧大棚 ESP32 硬件模拟器

模拟真实 ESP32 节点行为：
1. 通过 MQTT 定时发布传感器数据 (greenhouse/sensor/data)
2. 通过 MQTT 定时发布设备在线状态 (greenhouse/device/status)
3. 订阅 MQTT 控制命令 (greenhouse/device/control)，响应执行器控制
4. 执行器状态影响环境数据（风扇降温降湿、水泵增湿、补光灯增光）

使用前需启动：
  - 后端: uvicorn app.main:app --host 0.0.0.0 --port 8001
  - MQTT broker: mosquitto -v

使用方法：
  python simulate_hardware.py --node-id 1 [--interval 5] [--duration 0]
"""

import argparse
import json
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# 同项目配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings  # noqa: E402
from app.models.component import Component  # noqa: E402
from app.models.device_node import DeviceNode  # noqa: E402

# ── 日志 ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ESP32Sim")

# ── 传感器数据范围 ────────────────────────────────────

RANGES = {
    "air_temp":        (15.0, 38.0),
    "air_humidity":    (25.0, 95.0),
    "soil_humidity":   (15.0, 85.0),
    "light_intensity": (0.0, 1000.0),
    "soil_ph":         (5.0, 8.0),
    "co2":             (300.0, 2000.0),
}

DEFAULTS = {
    "air_temp":        25.0,
    "air_humidity":    60.0,
    "soil_humidity":   50.0,
    "light_intensity": 300.0,
    "soil_ph":         6.5,
    "co2":             600.0,
}


def _clamp(value: float, key: str) -> float:
    lo, hi = RANGES[key]
    return max(lo, min(hi, value))


# ── 日间变化 ──────────────────────────────────────────

def _daytime_factor(now: datetime) -> float:
    """0~1 日间因子：6:00 最低，14:00 最高。"""
    hour = now.hour + now.minute / 60.0
    if hour < 6 or hour > 22:
        return 0.0
    if hour <= 14:
        return (hour - 6) / 8.0
    return max(0.0, 1.0 - (hour - 14) / 8.0)


# ── 环境状态模型 ──────────────────────────────────────

class GreenhouseEnv:
    """大棚环境状态 — 执行器状态会影响传感器读数。"""

    def __init__(self):
        for key, val in DEFAULTS.items():
            setattr(self, key, val)
        # 执行器状态: component_id -> "on"|"off"|"auto"
        self.actuators: dict[int, str] = {}

    def set_actuator(self, component_id: int, action: str) -> None:
        self.actuators[component_id] = action

    def is_fan_on(self) -> bool:
        """检查是否有风扇开启"""
        return any(v == "on" for k, v in self.actuators.items()
                   if self._actuator_type(k) == "fan")

    def is_pump_on(self) -> bool:
        return any(v == "on" for k, v in self.actuators.items()
                   if self._actuator_type(k) == "pump")

    def is_light_on(self) -> bool:
        return any(v == "on" for k, v in self.actuators.items()
                   if self._actuator_type(k) == "light")

    # actuator_type 由 ESP32Simulator 注入
    _type_map: dict[int, str] = {}

    def _actuator_type(self, component_id: int) -> str:
        return self._type_map.get(component_id, "")

    def tick(self) -> dict:
        """每个上报周期调用，返回当前传感器读数。"""
        factor = _daytime_factor(datetime.now())

        # ── 日间基础值 ──
        # 气温：夜间 15°C → 正午 35°C
        base_air_temp = 15 + 20 * factor
        # 光照：夜间 0 → 正午 800
        base_light = 800 * factor
        # 湿度：白天低(40%) → 夜间高(80%)
        base_air_hum = 80 - 40 * factor
        # 土壤湿度缓慢蒸发
        base_soil_hum = 55 - 5 * factor
        # CO2：夜间呼吸升高 ~1000ppm，正午光合消耗 ~400ppm
        base_co2 = 1000 - 600 * factor

        # ── 执行器影响（每周期叠加）──
        # 风扇：降温降湿，通风换气降低 CO2
        if self.is_fan_on():
            self.air_temp = _clamp(self.air_temp - 0.3, "air_temp")
            self.air_humidity = _clamp(self.air_humidity - 0.5, "air_humidity")
            self.co2 = _clamp(self.co2 - 8, "co2")
        # 水泵：增土壤湿度
        if self.is_pump_on():
            self.soil_humidity = _clamp(self.soil_humidity + 1.0, "soil_humidity")
        # 补光灯：增光照，微增气温
        if self.is_light_on():
            self.light_intensity = _clamp(self.light_intensity + 50, "light_intensity")
            self.air_temp = _clamp(self.air_temp + 0.05, "air_temp")

        # ── 向日间基础值缓慢回归 ──
        self.air_temp = _clamp(
            self.air_temp + (base_air_temp - self.air_temp) * 0.1, "air_temp"
        )
        self.air_humidity = _clamp(
            self.air_humidity + (base_air_hum - self.air_humidity) * 0.1, "air_humidity"
        )
        self.light_intensity = _clamp(
            self.light_intensity + (base_light - self.light_intensity) * 0.15,
            "light_intensity",
        )
        self.soil_humidity = _clamp(
            self.soil_humidity + (base_soil_hum - self.soil_humidity) * 0.03,
            "soil_humidity",
        )
        self.co2 = _clamp(
            self.co2 + (base_co2 - self.co2) * 0.08, "co2"
        )

        # ── 随机噪声 ──
        self.air_temp += random.gauss(0, 0.3)
        self.air_humidity += random.gauss(0, 0.8)
        self.soil_humidity += random.gauss(0, 0.5)
        self.light_intensity += random.gauss(0, 5)
        self.co2 += random.gauss(0, 15)
        # pH 缓慢随机漂移
        self.soil_ph += random.gauss(0, 0.02)

        return {
            "air_temp":        round(_clamp(self.air_temp, "air_temp"), 1),
            "air_humidity":    round(_clamp(self.air_humidity, "air_humidity"), 1),
            "soil_humidity":   round(_clamp(self.soil_humidity, "soil_humidity"), 1),
            "light_intensity": round(max(0, _clamp(self.light_intensity, "light_intensity")), 1),
            "soil_ph":         round(_clamp(self.soil_ph, "soil_ph"), 2),
            "co2":             round(_clamp(self.co2, "co2"), 0),
        }


# ── ESP32 模拟器 ──────────────────────────────────────

class ESP32Simulator:
    """模拟 ESP32 节点：MQTT 通信 + 环境模拟。"""

    def __init__(self, node_id: int, interval: int, duration: int,
                 status_interval: int, mqtt_host: str, mqtt_port: int):
        self.node_id = node_id
        self.interval = interval
        self.duration = duration
        self.status_interval = status_interval
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port

        self.env = GreenhouseEnv()
        self.node_name = f"Node-{node_id}"
        self.report_count = 0
        self._running = True

        # MQTT 客户端
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"esp32-sim-node{node_id}",
            protocol=mqtt.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        if settings.MQTT_USERNAME:
            self.client.username_pw_set(
                settings.MQTT_USERNAME, settings.MQTT_PASSWORD or None
            )
            logger.info("MQTT 认证用户: %s", settings.MQTT_USERNAME)

    # ── 组件加载 ──

    def load_components(self) -> bool:
        """从数据库加载节点的组件配置。"""
        try:
            engine = create_engine(settings.DATABASE_URL)
            with Session(engine) as session:
                node = session.get(DeviceNode, self.node_id)
                if not node:
                    logger.error("数据库中不存在 node_id=%s", self.node_id)
                    return False
                self.node_name = node.name
                logger.info("节点: %s (%s)", node.name, node.location or "")

                stmt = select(Component).where(Component.node_id == self.node_id)
                components = session.execute(stmt).scalars().all()

                if not components:
                    logger.warning("节点 %s 没有组件，使用默认配置", self.node_name)
                    self._load_default_components()
                    return True

                for comp in components:
                    if comp.type.value == "sensor":
                        continue
                    self.env.actuators[comp.id] = comp.status.value
                    GreenhouseEnv._type_map[comp.id] = comp.type.value
                    logger.info("  组件: %s (id=%s, type=%s, status=%s)",
                                comp.name, comp.id, comp.type.value, comp.status.value)
        except SQLAlchemyError as e:
            logger.warning("数据库连接失败 (%s)，使用默认组件配置: %s", settings.DATABASE_URL, e)
            self._load_default_components()
            return True

        return True

    def _load_default_components(self) -> None:
        """数据库不可用时的默认组件配置。"""
        defaults = [
            (1001, "fan"), (1002, "pump"), (1003, "light"),
        ]
        for comp_id, comp_type in defaults:
            self.env.actuators[comp_id] = "off"
            GreenhouseEnv._type_map[comp_id] = comp_type
        logger.info("使用默认组件: fan(id=1001), pump(id=1002), light(id=1003)")

    # ── MQTT 回调 ──

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logger.info("✅ MQTT 已连接 %s:%s", self.mqtt_host, self.mqtt_port)
            client.subscribe(settings.MQTT_TOPIC_DEVICE_CONTROL)
            logger.info("订阅: %s", settings.MQTT_TOPIC_DEVICE_CONTROL)
            # 上线通知
            self._publish_status(online=True)
        else:
            logger.error("MQTT 连接失败: reason_code=%s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        logger.warning("MQTT 断开: reason_code=%s — paho 将自动重连", reason_code)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        """处理控制命令。"""
        try:
            data = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("控制命令 JSON 解析失败: %s", msg.payload[:80])
            return

        cmd_node_id = data.get("node_id")
        if cmd_node_id != self.node_id:
            return  # 不是发给本节点的命令

        component_id = data.get("component_id")
        action = data.get("action", "")
        message = data.get("message", "")

        # 如果 component_id 不在已知列表中，仍然记录（可能是动态添加的组件）
        comp_type = GreenhouseEnv._type_map.get(component_id, "unknown")

        self.env.set_actuator(component_id, action)
        logger.info("📨 控制命令: component=%s type=%s → %s (%s)",
                    component_id, comp_type, action.upper(), message)

    # ── 发布消息 ──

    def _publish_sensor_data(self) -> None:
        """发布传感器数据到 MQTT。"""
        readings = self.env.tick()
        payload = {
            "node_id": self.node_id,
            **readings,
            "timestamp": datetime.now().isoformat(),
        }
        self.client.publish(settings.MQTT_TOPIC_SENSOR_DATA, json.dumps(payload))
        self.report_count += 1

        # 状态图标
        fan = "🌀" if self.env.is_fan_on() else "  "
        pump = "💧" if self.env.is_pump_on() else "  "
        light = "💡" if self.env.is_light_on() else "  "

        logger.info(
            "📊 #%d  气温=%.1f°C  气湿=%.1f%%  土湿=%.1f%%  光照=%.1flux  pH=%.2f  CO₂=%.0fppm  %s%s%s",
            self.report_count,
            readings["air_temp"], readings["air_humidity"],
            readings["soil_humidity"],
            readings["light_intensity"], readings["soil_ph"],
            readings["co2"],
            fan, pump, light,
        )

    def _publish_status(self, online: bool = True) -> None:
        """发布设备在线状态。"""
        payload = {
            "node_id": self.node_id,
            "online": online,
            "last_reported_at": datetime.now().isoformat(),
        }
        self.client.publish(settings.MQTT_TOPIC_DEVICE_STATUS, json.dumps(payload))
        if online:
            logger.info("📡 状态上报: online=True")

    # ── 主循环 ──

    def run(self) -> None:
        logger.info("=" * 60)
        logger.info("  ESP32 硬件模拟器")
        logger.info("  节点: %s (id=%s)", self.node_name, self.node_id)
        logger.info("  上报间隔: %ss | 状态间隔: %ss | 运行时长: %s",
                    self.interval, self.status_interval,
                    f"{self.duration}s" if self.duration > 0 else "无限")
        logger.info("=" * 60)

        # 连接 MQTT
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        except Exception as e:
            logger.error("无法连接 MQTT broker %s:%s — %s", self.mqtt_host, self.mqtt_port, e)
            logger.error("请先启动 Mosquitto: mosquitto -v")
            sys.exit(1)

        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.loop_start()

        start_time = time.time()
        last_status_time = start_time

        try:
            while self._running:
                elapsed = time.time() - start_time
                if self.duration > 0 and elapsed >= self.duration:
                    logger.info("运行 %ss 完成，共上报 %d 条数据", self.duration, self.report_count)
                    break

                # 发布传感器数据
                self._publish_sensor_data()

                # 定时发布状态
                if time.time() - last_status_time >= self.status_interval:
                    self._publish_status(online=True)
                    last_status_time = time.time()

                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            self._publish_status(online=False)
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT 已断开，共上报 %d 条数据", self.report_count)

    def stop(self, *args) -> None:
        self._running = False


# ── 主入口 ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ESP32 硬件模拟器（MQTT 通信）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python simulate_hardware.py --node-id 1              # 模拟节点 1，5秒间隔
  python simulate_hardware.py --node-id 2 --interval 3 # 3秒上报一次
  python simulate_hardware.py --node-id 1 --duration 60 # 运行 60 秒
        """,
    )
    parser.add_argument("--node-id", type=int, default=1, help="节点 ID（默认 1）")
    parser.add_argument("--interval", type=int, default=5, help="传感器上报间隔秒数（默认 5）")
    parser.add_argument("--duration", type=int, default=0, help="运行时长秒数，0=无限（默认 0）")
    parser.add_argument("--status-interval", type=int, default=30, help="状态上报间隔秒数（默认 30）")
    parser.add_argument("--mqtt-host", default=settings.MQTT_BROKER_HOST, help="MQTT broker 地址")
    parser.add_argument("--mqtt-port", type=int, default=settings.MQTT_BROKER_PORT, help="MQTT broker 端口")
    args = parser.parse_args()

    sim = ESP32Simulator(
        node_id=args.node_id,
        interval=args.interval,
        duration=args.duration,
        status_interval=args.status_interval,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
    )

    # 加载组件配置
    if not sim.load_components():
        sys.exit(1)

    # Ctrl+C 优雅退出
    signal.signal(signal.SIGINT, sim.stop)
    signal.signal(signal.SIGTERM, sim.stop)

    sim.run()


if __name__ == "__main__":
    main()

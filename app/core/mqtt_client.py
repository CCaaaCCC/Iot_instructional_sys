"""MQTT 客户端 — FastAPI lifespan 管理"""

import json
import logging
from datetime import datetime

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import device_node_service, sensor_service

logger = logging.getLogger(__name__)

_mqtt_client: mqtt.Client | None = None


def _on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logger.info("MQTT connected to %s:%s", settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT)
        client.subscribe(settings.MQTT_TOPIC_SENSOR_DATA)
        client.subscribe(settings.MQTT_TOPIC_DEVICE_STATUS)
        logger.info("MQTT subscribed: %s, %s", settings.MQTT_TOPIC_SENSOR_DATA, settings.MQTT_TOPIC_DEVICE_STATUS)
    else:
        logger.warning("MQTT connection failed, reason_code=%s", reason_code)


def _on_disconnect(client: mqtt.Client, userdata, disconnect_flags, reason_code, properties=None):
    logger.warning("MQTT disconnected, reason_code=%s — paho will auto-reconnect", reason_code)


def _on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    try:
        payload = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("MQTT invalid JSON on topic %s", msg.topic)
        return

    topic = msg.topic
    if topic == settings.MQTT_TOPIC_SENSOR_DATA:
        _handle_sensor_data(payload)
    elif topic == settings.MQTT_TOPIC_DEVICE_STATUS:
        _handle_device_status(payload)


def _handle_sensor_data(data: dict) -> None:
    """处理 MQTT 传感器上报"""
    node_id = data.get("node_id") or data.get("device_id")
    if not node_id:
        logger.warning("MQTT sensor data missing node_id")
        return

    db = SessionLocal()
    try:
        sensor = sensor_service.create_sensor_data(db, _mqtt_to_sensor_create(node_id, data))
        logger.info(
            "MQTT sensor: node=%s air_temp=%s air_hum=%s",
            node_id, sensor.air_temp, sensor.air_humidity,
        )
    except ValueError as exc:
        db.rollback()
        logger.warning("MQTT sensor create failed: %s", exc)
    except Exception:
        db.rollback()
        logger.exception("MQTT sensor data handling error")
    finally:
        db.close()


def _handle_device_status(data: dict) -> None:
    """处理 MQTT 设备状态上报"""
    node_id = data.get("node_id") or data.get("device_id")
    if not node_id:
        return

    db = SessionLocal()
    try:
        node = device_node_service.get_node(db, node_id)
        if not node:
            logger.warning("MQTT device status: node %s not found", node_id)
            return
        from app.schemas.device_node import DeviceNodeUpdate
        update_data = {}
        was_online = node.online
        if "online" in data:
            update_data["online"] = data["online"]
        if "last_reported_at" in data and data["last_reported_at"]:
            update_data["last_reported_at"] = datetime.fromisoformat(data["last_reported_at"])
        else:
            update_data["last_reported_at"] = datetime.now()
        if update_data:
            node_update = DeviceNodeUpdate(**update_data)
            device_node_service.update_node(db, node, node_update)
            logger.info("MQTT device status: id=%s online=%s",
                        node_id, node.online)
            # WebSocket 实时广播设备状态
            from app.core.websocket_manager import ws_manager
            ws_manager.broadcast_sync("device_status", {
                "node_id": node_id,
                "online": node.online,
                "last_reported_at": node.last_reported_at.isoformat() if node.last_reported_at else None,
            }, node_id=node_id)
            # 设备离线告警：从在线变为离线时通知所有 admin + teacher
            if was_online and not node.online:
                _notify_device_offline(db, node_id, node.name)
    except Exception:
        db.rollback()
        logger.exception("MQTT device status handling error")
    finally:
        db.close()


def _notify_device_offline(db, node_id: int, node_name: str) -> None:
    """设备离线时通知所有 admin + teacher。"""
    try:
        from app.services import notification_service
        from app.core.websocket_manager import ws_manager
        recipient_ids = notification_service.get_admin_and_teacher_ids(db)
        if not recipient_ids:
            return
        title = "设备离线告警"
        content = f"设备节点「{node_name}」已离线，请及时检查。"
        link = "/devices"
        notifications = notification_service.create_notification_for_users(
            db, recipient_ids, "device_alert", title, content, link
        )
        db.commit()
        for n in notifications:
            ws_manager.send_to_user_sync("notification", {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "link": n.link,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }, user_id=n.user_id)
    except Exception:
        logger.exception("Failed to notify device offline for node %s", node_id)


def _mqtt_to_sensor_create(node_id: int, data: dict):
    """将 MQTT JSON payload 转换为 SensorDataCreate 兼容的 dict"""
    from app.schemas.sensor_data import SensorDataCreate
    return SensorDataCreate(
        node_id=node_id,
        air_temp=data.get("air_temp"),
        air_humidity=data.get("air_humidity"),
        soil_temp=data.get("soil_temp"),
        soil_humidity=data.get("soil_humidity"),
        light_intensity=data.get("light_intensity"),
        soil_ph=data.get("soil_ph"),
        recorded_at=data.get("timestamp"),
    )


def publish_component_control(
    node_id: int, component_id: int, action: str, message: str = ""
) -> bool:
    """发布组件控制指令到 MQTT，返回是否成功送达"""
    if _mqtt_client is None or not _mqtt_client.is_connected():
        logger.warning("MQTT not connected, cannot publish control command")
        return False
    payload = json.dumps({
        "node_id": node_id,
        "component_id": component_id,
        "action": action,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    })
    info = _mqtt_client.publish(settings.MQTT_TOPIC_DEVICE_CONTROL, payload)
    logger.info(
        "MQTT control: node=%s component=%s action=%s (mid=%s)",
        node_id, component_id, action, info.mid,
    )
    return True


# 向后兼容别名（规则引擎等可能调用）
publish_device_control = publish_component_control


def get_mqtt_client() -> mqtt.Client | None:
    return _mqtt_client


def start_mqtt() -> None:
    """启动 MQTT 客户端"""
    global _mqtt_client
    _mqtt_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=settings.MQTT_CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )
    _mqtt_client.on_connect = _on_connect
    _mqtt_client.on_disconnect = _on_disconnect
    _mqtt_client.on_message = _on_message

    # 指数退避自动重连：1s → 2s → 4s → ... → 120s
    _mqtt_client.reconnect_delay_set(min_delay=1, max_delay=120)

    # MQTT 5.0 callback_api_version
    try:
        _mqtt_client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
    except Exception:
        logger.warning(
            "MQTT broker not available at %s:%s — starting without MQTT",
            settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT,
        )
        _mqtt_client = None
        return

    _mqtt_client.loop_start()
    logger.info("MQTT client started")


def stop_mqtt() -> None:
    """停止 MQTT 客户端"""
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        logger.info("MQTT client stopped")

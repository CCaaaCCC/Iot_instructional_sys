"""病虫害诊断服务：mock AI 分类 + CRUD + WebSocket 推送 + 教师通知。

设计要点：
- mock AI 基于图片字节哈希确定性分类（同图同结果），6 分类
- 诊断完成后通过 WebSocket 实时推送给同组（node_id 过滤）+ 教师
- 教师收到通知（Notification 表）
- 30 天保留策略：cleanup_old_diagnoses 删除超期记录及图片文件
"""

import hashlib
import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.websocket_manager import ws_manager
from app.models import PestDiagnosis
from app.models.enums import DiagnosisResult
from app.services import notification_service

# 诊断结果 → 中文标签 + 处理建议
_DIAGNOSIS_INFO: dict[DiagnosisResult, dict] = {
    DiagnosisResult.tomato_healthy: {
        "label": "番茄健康",
        "suggestion": "植株生长状态良好，继续保持当前水肥管理。",
    },
    DiagnosisResult.tomato_early_blight: {
        "label": "番茄早疫病",
        "suggestion": "叶片出现同心轮纹病斑，建议清除病叶并喷施代森锰锌或百菌清防治。",
    },
    DiagnosisResult.tomato_late_blight: {
        "label": "番茄晚疫病",
        "suggestion": "高湿环境下易发，叶片出现水浸状病斑，建议降低湿度并喷施霜脲氰防治。",
    },
    DiagnosisResult.cucumber_healthy: {
        "label": "黄瓜健康",
        "suggestion": "植株生长状态良好，继续保持当前水肥管理。",
    },
    DiagnosisResult.cucumber_powdery_mildew: {
        "label": "黄瓜白粉病",
        "suggestion": "叶面出现白色粉状物，建议通风降湿并喷施醚菌酯或硫磺制剂防治。",
    },
    DiagnosisResult.cucumber_anthracnose: {
        "label": "黄瓜炭疽病",
        "suggestion": "叶片出现圆形黄褐色病斑，建议清除病残体并喷施咪鲜胺防治。",
    },
}

_ALL_RESULTS = list(DiagnosisResult)
_RETENTION_DAYS = 30


def mock_ai_classify(image_data: bytes) -> tuple[DiagnosisResult, float]:
    """基于图片字节哈希的确定性 mock 分类。

    同一张图片始终返回同一结果（便于测试复现），
    不同图片在 6 个分类间分布。
    """
    digest = hashlib.md5(image_data).hexdigest()
    # 取哈希前 8 字符转 int，模 6 选分类
    idx = int(digest[:8], 16) % len(_ALL_RESULTS)
    result = _ALL_RESULTS[idx]
    # 置信度：0.72-0.98 之间，基于哈希确定性生成
    conf_raw = int(digest[8:12], 16) % 2700  # 0-2699
    confidence = round(0.72 + conf_raw / 10000, 4)  # 0.72 - 0.9899
    return result, confidence


def _build_suggestion(result: DiagnosisResult) -> str:
    info = _DIAGNOSIS_INFO.get(result, {})
    return info.get("suggestion", "暂无建议")


def get_diagnosis_label(result: DiagnosisResult) -> str:
    info = _DIAGNOSIS_INFO.get(result, {})
    return info.get("label", result.value)


def create_diagnosis(
    db: Session,
    group_id: int,
    node_id: int,
    device_token_id: int,
    image_url: str,
    image_data: bytes,
) -> PestDiagnosis:
    """创建诊断记录：mock AI 分类 + 保存 + WebSocket 推送 + 教师通知。"""
    result, confidence = mock_ai_classify(image_data)
    suggestion = _build_suggestion(result)
    label = get_diagnosis_label(result)

    diagnosis = PestDiagnosis(
        group_id=group_id,
        node_id=node_id,
        device_token_id=device_token_id,
        image_url=image_url,
        diagnosis_result=result,
        confidence=confidence,
        suggestion=suggestion,
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)

    # WebSocket 实时推送给同组（node_id 过滤，学生只看本组）
    ws_manager.broadcast_sync(
        "pest_diagnosis",
        {
            "id": diagnosis.id,
            "group_id": diagnosis.group_id,
            "node_id": diagnosis.node_id,
            "image_url": diagnosis.image_url,
            "diagnosis_result": diagnosis.diagnosis_result.value,
            "diagnosis_label": label,
            "confidence": diagnosis.confidence,
            "suggestion": diagnosis.suggestion,
            "created_at": diagnosis.created_at.isoformat() if diagnosis.created_at else None,
        },
        node_id=node_id,
    )

    # 通知教师（所有 admin + teacher）
    teacher_ids = notification_service.get_admin_and_teacher_ids(db)
    if teacher_ids:
        notification_service.create_notification_for_users(
            db,
            user_ids=teacher_ids,
            type="pest_diagnosis",
            title=f"病虫害诊断：{label}",
            content=f"第 {group_id} 组设备上报，诊断结果：{label}（置信度 {confidence:.0%}）",
            link="/pest-diagnoses",
        )
        db.commit()

    return diagnosis


def list_diagnoses(
    db: Session,
    group_id: int | None = None,
    diagnosis_result: DiagnosisResult | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PestDiagnosis]:
    """列出诊断记录，支持按小组/结果过滤。"""
    stmt = select(PestDiagnosis).order_by(PestDiagnosis.created_at.desc())
    if group_id is not None:
        stmt = stmt.where(PestDiagnosis.group_id == group_id)
    if diagnosis_result is not None:
        stmt = stmt.where(PestDiagnosis.diagnosis_result == diagnosis_result)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_diagnosis(db: Session, diagnosis_id: int) -> PestDiagnosis | None:
    return db.get(PestDiagnosis, diagnosis_id)


def delete_diagnosis(db: Session, diagnosis: PestDiagnosis) -> None:
    """删除诊断记录及其图片文件。"""
    image_path = _image_path_from_url(diagnosis.image_url)
    db.delete(diagnosis)
    db.commit()
    if image_path and os.path.isfile(image_path):
        try:
            os.remove(image_path)
        except OSError:
            pass


def cleanup_old_diagnoses(db: Session) -> int:
    """清理超过 30 天的诊断记录及图片，返回删除条数。"""
    cutoff = datetime.now() - timedelta(days=_RETENTION_DAYS)
    stmt = select(PestDiagnosis).where(PestDiagnosis.created_at < cutoff)
    old_records = list(db.execute(stmt).scalars().all())
    count = 0
    for record in old_records:
        image_path = _image_path_from_url(record.image_url)
        if image_path and os.path.isfile(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass
        db.delete(record)
        count += 1
    if count:
        db.commit()
    return count


def _image_path_from_url(image_url: str) -> str | None:
    if not image_url:
        return None
    filename = image_url.rsplit("/", 1)[-1] if "/" in image_url else image_url
    return os.path.join("data", "pest-images", filename)

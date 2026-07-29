"""病虫害诊断服务：ResNet50 模型推理 + CRUD + WebSocket 推送 + 教师通知。

设计要点：
- 使用训练好的 ResNet50 模型进行真实推理（5 分类）
- 模型懒加载：首次推理时加载，之后复用
- 诊断完成后通过 WebSocket 实时推送给同组（node_id 过滤）+ 教师
- 教师收到通知（Notification 表）
- 30 天保留策略：cleanup_old_diagnoses 删除超期记录及图片文件
"""

import io
import logging
import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.websocket_manager import ws_manager
from app.models import PestDiagnosis
from app.models.enums import DiagnosisResult
from app.services import notification_service

logger = logging.getLogger(__name__)

# ── 诊断结果 → 中文标签 + 处理建议 ──────────────────────────────────
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
    DiagnosisResult.strawberry_healthy: {
        "label": "草莓健康",
        "suggestion": "植株生长状态良好，继续保持当前水肥管理。",
    },
    DiagnosisResult.strawberry_leaf_scorch: {
        "label": "草莓叶焦病",
        "suggestion": "叶缘出现紫褐色焦枯斑，建议清除病叶、加强通风，喷施苯醚甲环唑防治。",
    },
}

_RETENTION_DAYS = 30

# ── 模型类名 → DiagnosisResult 映射 ────────────────────────────────
_CLASS_NAME_MAP: dict[str, DiagnosisResult] = {
    "Tomato___healthy": DiagnosisResult.tomato_healthy,
    "Tomato___Early_blight": DiagnosisResult.tomato_early_blight,
    "Tomato___Late_blight": DiagnosisResult.tomato_late_blight,
    "Strawberry___healthy": DiagnosisResult.strawberry_healthy,
    "Strawberry___Leaf_scorch": DiagnosisResult.strawberry_leaf_scorch,
}

# ── PyTorch 模型懒加载单例 ──────────────────────────────────────────
_model = None
_transform = None
_classes: list[str] | None = None
_device = None


def _load_model():
    """懒加载 PyTorch 模型（首次推理时触发）。"""
    global _model, _transform, _classes, _device

    if _model is not None:
        return

    try:
        import torch
        from torchvision import models, transforms
        import torch.nn as nn
    except ImportError:
        logger.error(
            "PyTorch 未安装，无法进行真实推理。"
            "请安装: pip install torch torchvision"
        )
        raise RuntimeError(
            "PyTorch 未安装，无法进行病虫害诊断。请安装: pip install torch torchvision"
        ) from None

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("病虫害诊断模型加载设备: %s", _device)

    # 推理预处理（与训练时 val_transform 一致）
    IMAGENET_MEAN = [0.485, 0.456, 0.406]
    IMAGENET_STD = [0.229, 0.224, 0.225]
    _transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    # 加载 checkpoint
    model_path = os.environ.get("PEST_MODEL_PATH", "models/pest_model.pth")
    if not os.path.isfile(model_path):
        logger.error("模型文件不存在: %s", model_path)
        raise RuntimeError(f"病虫害诊断模型文件未找到: {model_path}")

    checkpoint = torch.load(model_path, map_location=_device, weights_only=False)

    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        _classes = checkpoint["classes"]
        model_name = checkpoint.get("model_name", "resnet50")
        state_dict = checkpoint["state_dict"]
    else:
        raise ValueError("模型 checkpoint 格式不支持，需要包含 state_dict + classes")

    # 构建模型
    if model_name == "resnet50":
        model = models.resnet50(weights=None)
    else:
        model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(_classes))
    model.load_state_dict(state_dict)
    model.to(_device)
    model.eval()

    _model = model
    logger.info(
        "病虫害诊断模型加载成功: %s, %d 类别, 设备=%s",
        model_name, len(_classes), _device,
    )


def ai_classify(image_data: bytes) -> tuple[DiagnosisResult, float]:
    """使用 ResNet50 模型对图片进行病虫害分类。

    返回 (诊断结果, 置信度)。

    异常：
    - ValueError：图片预处理失败（损坏的图片、非图片数据）
    - RuntimeError：模型推理失败（含 GPU OOM）
    """
    from PIL import Image

    _load_model()

    # bytes → PIL Image → tensor
    try:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        tensor = _transform(image).unsqueeze(0).to(_device)
    except Exception as e:
        raise ValueError(f"图片预处理失败: {e}") from e

    # 推理
    import torch
    try:
        with torch.no_grad():
            output = _model(tensor)
            probs = torch.softmax(output, dim=1)
            confidence, pred_idx = probs[0].max(dim=0)
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        raise RuntimeError("GPU 内存不足，请重试") from None
    except Exception as e:
        raise RuntimeError(f"模型推理失败: {e}") from e

    pred_class = _classes[pred_idx.item()]
    result = _CLASS_NAME_MAP.get(pred_class)
    if result is None:
        logger.warning("模型预测了未知类别: %s，回退到 tomato_healthy", pred_class)
        result = DiagnosisResult.tomato_healthy

    return result, round(confidence.item(), 4)


# ── 业务逻辑 ────────────────────────────────────────────────────────


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
    """创建诊断记录：AI 推理 + 保存 + WebSocket 推送 + 教师通知。"""
    result, confidence = ai_classify(image_data)
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

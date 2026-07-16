"""病虫害诊断路由：ESP32-CAM 设备上传 + 管理端列表/详情/删除。

权限：
- POST /upload：设备 token 鉴权（get_device_context），仅 esp32cam 设备
- GET 列表/详情：admin + teacher + operator（教师可读所有班级）
- DELETE：admin
- 学生通过 /student/me/pest-diagnoses 访问本组数据
"""

import os
import secrets
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.core.device_auth import DeviceContext, get_device_context
from app.models.enums import DiagnosisResult, DeviceType, UserRole
from app.schemas.pest_diagnosis import (
    PestDiagnosisListOut,
    PestDiagnosisOut,
    PestDiagnosisUploadResponse,
)
from app.services import log_service, pest_diagnosis_service

router = APIRouter(prefix="/pest-diagnoses", tags=["pest-diagnoses"])

PEST_IMAGES_DIR = "data/pest-images"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/upload",
    response_model=PestDiagnosisUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_diagnosis(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    device: DeviceContext = Depends(get_device_context),
) -> PestDiagnosisUploadResponse:
    """ESP32-CAM 设备上传照片进行病虫害诊断。

    鉴权：设备 Bearer token（仅 esp32cam 类型设备可用）。
    流程：校验图片 → 保存 → mock AI 分类 → WebSocket 推送 → 教师通知。
    """
    if device.device_type != DeviceType.esp32cam.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only esp32cam devices can upload pest diagnosis images",
        )
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {file.content_type}. Allowed: jpeg, png",
        )
    image_data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(image_data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image exceeds 10MB limit",
        )

    os.makedirs(PEST_IMAGES_DIR, exist_ok=True)
    ext = "jpg" if file.content_type in ("image/jpeg", "image/jpg") else "png"
    filename = f"{device.token.id}_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(PEST_IMAGES_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image_data)
    image_url = f"/pest-images/{filename}"

    diagnosis = pest_diagnosis_service.create_diagnosis(
        db,
        group_id=device.group_id,
        node_id=device.node_id,
        device_token_id=device.token.id,
        image_url=image_url,
        image_data=image_data,
    )

    return PestDiagnosisUploadResponse(
        id=diagnosis.id,
        diagnosis_result=diagnosis.diagnosis_result,
        confidence=diagnosis.confidence,
        suggestion=diagnosis.suggestion,
        image_url=diagnosis.image_url,
        created_at=diagnosis.created_at,
    )


@router.get("", response_model=list[PestDiagnosisListOut])
def list_diagnoses(
    group_id: int | None = None,
    diagnosis_result: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.admin, UserRole.operator, UserRole.teacher)
    ),
) -> list[PestDiagnosisListOut]:
    """列出诊断记录（教师可读所有班级），支持按小组/结果过滤。"""
    result_enum = None
    if diagnosis_result:
        try:
            result_enum = DiagnosisResult(diagnosis_result)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid diagnosis_result. Valid: {[r.value for r in DiagnosisResult]}",
            )
    records = pest_diagnosis_service.list_diagnoses(
        db,
        group_id=group_id,
        diagnosis_result=result_enum,
        skip=skip,
        limit=limit,
    )
    result: list[PestDiagnosisListOut] = []
    for r in records:
        group_name = r.group.name if r.group else None
        node_name = r.node.name if r.node else None
        result.append(
            PestDiagnosisListOut(
                id=r.id,
                group_id=r.group_id,
                node_id=r.node_id,
                device_token_id=r.device_token_id,
                image_url=r.image_url,
                diagnosis_result=r.diagnosis_result,
                confidence=r.confidence,
                suggestion=r.suggestion,
                created_at=r.created_at,
                group_name=group_name,
                node_name=node_name,
            )
        )
    return result


@router.get("/{diagnosis_id}", response_model=PestDiagnosisListOut)
def get_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.admin, UserRole.operator, UserRole.teacher)
    ),
) -> PestDiagnosisListOut:
    """获取诊断记录详情。"""
    record = pest_diagnosis_service.get_diagnosis(db, diagnosis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found"
        )
    group_name = record.group.name if record.group else None
    node_name = record.node.name if record.node else None
    return PestDiagnosisListOut(
        id=record.id,
        group_id=record.group_id,
        node_id=record.node_id,
        device_token_id=record.device_token_id,
        image_url=record.image_url,
        diagnosis_result=record.diagnosis_result,
        confidence=record.confidence,
        suggestion=record.suggestion,
        created_at=record.created_at,
        group_name=group_name,
        node_name=node_name,
    )


@router.delete("/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.admin)),
) -> None:
    """删除诊断记录及图片（仅 admin）。"""
    record = pest_diagnosis_service.get_diagnosis(db, diagnosis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found"
        )
    pest_diagnosis_service.delete_diagnosis(db, record)
    log_service.create_operation_log(
        db,
        user_id=current_user.id,
        action="delete_pest_diagnosis",
        entity_type="pest_diagnosis",
        entity_id=str(diagnosis_id),
        detail=f"Deleted pest diagnosis #{diagnosis_id}",
    )

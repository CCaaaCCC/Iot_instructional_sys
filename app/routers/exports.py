"""学生成长档案 PDF 导出路由"""
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.services.export_service import export_student_growth_pdf

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/students/{student_id}/growth-pdf")
def download_student_growth_pdf(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.teacher)
    ),
) -> Response:
    """导出学生成长档案 PDF。

    返回 application/pdf 文件流，文件名格式：学生成长档案_{姓名}_{日期}.pdf
    中文文件名通过 RFC 5987 filename* 参数传递（URL 编码）。
    """
    try:
        pdf_bytes = export_student_growth_pdf(db, student_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # 查询学生姓名用于文件名
    student = db.get(User, student_id)
    student_name = student.display_name or student.username if student else str(student_id)
    date_str = datetime.now().strftime("%Y%m%d")
    filename_zh = f"学生成长档案_{student_name}_{date_str}.pdf"
    # RFC 5987: filename* 用 UTF-8 URL 编码支持中文，filename 用 ASCII 回退
    filename_ascii = f"growth_archive_{student_id}_{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename_ascii}\"; "
                f"filename*=UTF-8''{quote(filename_zh)}"
            ),
        },
    )

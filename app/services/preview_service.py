"""LibreOffice headless 文件转 PDF 预览服务。"""

import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

# LibreOffice 可执行文件搜索路径
_SOFFICE_CANDIDATES = [
    "soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]

# 支持转换的文件扩展名
_CONVERTIBLE_EXTS = {".ppt", ".pptx", ".doc", ".docx"}

# 转换超时（秒）
_TIMEOUT = 30


def _find_soffice() -> str | None:
    """查找可用的 soffice 可执行文件路径。"""
    for candidate in _SOFFICE_CANDIDATES:
        if shutil.which(candidate):
            return candidate
        if os.path.isfile(candidate):
            return candidate
    return None


def is_convertible(filename: str) -> bool:
    """判断文件是否需要转 PDF 预览。"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in _CONVERTIBLE_EXTS


def convert_to_pdf(source_path: str, output_dir: str, preview_filename: str) -> str | None:
    """调用 LibreOffice headless 将文件转为 PDF。

    Args:
        source_path: 源文件绝对路径
        output_dir: 输出目录
        preview_filename: 预览文件名（不含扩展名，最终输出为 {preview_filename}.pdf）

    Returns:
        成功返回 PDF 文件名（含 .pdf 扩展），失败返回 None
    """
    soffice = _find_soffice()
    if not soffice:
        logger.warning("LibreOffice not found, skipping PDF preview generation")
        return None

    try:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf",
             "--outdir", output_dir, source_path],
            capture_output=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("LibreOffice conversion timed out for %s", source_path)
        return None
    except Exception:
        logger.warning("LibreOffice conversion failed for %s", source_path, exc_info=True)
        return None

    # LibreOffice 输出文件名 = 源文件名（去原扩展）+ .pdf
    source_basename = os.path.splitext(os.path.basename(source_path))[0]
    generated_pdf = os.path.join(output_dir, f"{source_basename}.pdf")
    target_pdf = os.path.join(output_dir, f"{preview_filename}.pdf")

    if not os.path.isfile(generated_pdf):
        logger.warning("LibreOffice did not produce PDF: %s", generated_pdf)
        return None

    # 重命名为预览文件名
    if generated_pdf != target_pdf:
        shutil.move(generated_pdf, target_pdf)

    return f"{preview_filename}.pdf"

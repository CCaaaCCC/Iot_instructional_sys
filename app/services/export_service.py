"""学生成长档案 PDF 导出服务

使用 reportlab 生成包含学习概览、得分趋势、提交频率和近期活动的 PDF 报告。
中文支持通过 reportlab 内置的 STSong-Light CID 字体实现，无需额外字体文件。
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from sqlalchemy.orm import Session

from app.models.classroom import Classroom
from app.models.group import Group
from app.models.user import User
from app.services.student_analytics_service import get_analytics_for_student

# 注册中文 CID 字体（reportlab 内置，无需额外文件）
_FONT = "STSong-Light"
pdfmetrics.registerFont(UnicodeCIDFont(_FONT))

# 颜色方案
_PRIMARY = colors.HexColor("#2D7D6E")
_LIGHT_BG = colors.HexColor("#F0F7F5")
_TEXT = colors.HexColor("#333333")
_MUTED = colors.HexColor("#888888")
_BORDER = colors.HexColor("#DDD")


# 样式定义
_style_title = ParagraphStyle(
    "Title", fontName=_FONT, fontSize=22, leading=28,
    textColor=_PRIMARY, alignment=1, spaceAfter=4 * mm,
)
_style_subtitle = ParagraphStyle(
    "Subtitle", fontName=_FONT, fontSize=10, leading=14,
    textColor=_MUTED, alignment=1, spaceAfter=8 * mm,
)
_style_h2 = ParagraphStyle(
    "H2", fontName=_FONT, fontSize=14, leading=18,
    textColor=_PRIMARY, spaceBefore=6 * mm, spaceAfter=3 * mm,
)
_style_body = ParagraphStyle(
    "Body", fontName=_FONT, fontSize=10, leading=14, textColor=_TEXT,
)
_style_muted = ParagraphStyle(
    "Muted", fontName=_FONT, fontSize=9, leading=12, textColor=_MUTED,
)


def export_student_growth_pdf(db: Session, student_id: int) -> bytes:
    """生成学生成长档案 PDF，返回字节流。

    内容：封面信息 → 学习概览表 → 得分趋势图 → 提交频率图 → 近期活动表 → 教师评语汇总。
    """
    analytics = get_analytics_for_student(db, student_id)
    if analytics is None:
        raise ValueError("学生不存在或不是学生角色")

    student = db.get(User, student_id)
    student_name = analytics.summary.student_name
    username = student.username if student else ""

    # 查询班级和小组信息
    group_name = "-"
    classroom_name = "-"
    subject_label = "-"
    if student and student.group_id:
        group = db.get(Group, student.group_id)
        if group:
            group_name = group.name
            if group.class_id:
                classroom = db.get(Classroom, group.class_id)
                if classroom:
                    classroom_name = classroom.name
                    subject_label = (
                        "劳动课" if classroom.subject and classroom.subject.value == "labor"
                        else "科学课" if classroom.subject else "-"
                    )

    now_str = datetime.now().strftime("%Y年%m月%d日")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"学生成长档案_{student_name}",
    )
    story: list = []

    # ── 1. 封面标题 + 学生信息 ──
    story.append(Paragraph("学生成长档案", _style_title))
    story.append(Paragraph(f"生成日期：{now_str}", _style_subtitle))

    info_data = [
        ["姓名", student_name, "用户名", username],
        ["班级", classroom_name, "科目", subject_label],
        ["小组", group_name, "学生ID", str(student_id)],
    ]
    info_table = Table(info_data, colWidths=[25 * mm, 55 * mm, 25 * mm, 55 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), _LIGHT_BG),
        ("BACKGROUND", (2, 0), (2, -1), _LIGHT_BG),
        ("TEXTCOLOR", (0, 0), (0, -1), _PRIMARY),
        ("TEXTCOLOR", (2, 0), (2, -1), _PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)

    # ── 2. 学习概览 ──
    story.append(Paragraph("学习概览", _style_h2))
    s = analytics.summary
    overview_data = [
        ["指标", "数值", "说明"],
        ["提交次数", str(s.total_submissions), f"共完成 {s.completed_tasks}/{s.total_tasks} 个任务"],
        ["平均得分", f"{s.avg_score} 分" if s.avg_score is not None else "暂无", "已批阅作业的均分"],
        ["任务完成率", f"{s.completion_rate}%", "已提交任务数 / 分配任务数"],
        ["按时提交率", f"{s.on_time_ratio}%", f"按时 {s.on_time_count} 次 / 迟交 {s.late_count} 次"],
    ]
    ov_table = Table(overview_data, colWidths=[35 * mm, 35 * mm, 90 * mm])
    ov_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ov_table)

    # ── 3. 得分趋势折线图 ──
    story.append(Paragraph("得分趋势", _style_h2))
    score_trend = analytics.score_trend
    if score_trend:
        drawing = _make_score_trend_chart(score_trend)
        story.append(drawing)
    else:
        story.append(Paragraph("暂无得分记录", _style_muted))

    # ── 4. 提交频率条形图 ──
    story.append(Paragraph("提交频率", _style_h2))
    freq = analytics.submission_frequency
    if freq:
        drawing = _make_freq_chart(freq)
        story.append(drawing)
    else:
        story.append(Paragraph("暂无提交记录", _style_muted))

    # ── 5. 近期活动 ──
    story.append(Paragraph("近期活动（最近 10 条）", _style_h2))
    activities = analytics.recent_activity
    if activities:
        act_data = [["时间", "任务", "类型", "得分", "详情"]]
        for a in activities:
            type_label = "批阅" if a.type == "reviewed" else "提交"
            score_str = f"{a.score} 分" if a.score is not None else "-"
            # 截断详情避免过长
            detail = (a.detail or "")[:40]
            act_data.append([
                a.date,
                a.task_title or "-",
                type_label,
                score_str,
                detail,
            ])
        act_table = Table(act_data, colWidths=[28 * mm, 35 * mm, 15 * mm, 18 * mm, 64 * mm])
        act_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(act_table)
    else:
        story.append(Paragraph("暂无活动记录", _style_muted))

    # ── 6. 教师评语汇总 ──
    reviewed = [a for a in activities if a.type == "reviewed"]
    story.append(Paragraph("教师评语汇总", _style_h2))
    if reviewed:
        review_data = [["任务", "得分", "评语"]]
        for a in reviewed:
            review_data.append([
                a.task_title or "-",
                f"{a.score} 分" if a.score is not None else "-",
                a.detail or "无",
            ])
        rev_table = Table(review_data, colWidths=[45 * mm, 20 * mm, 95 * mm])
        rev_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(rev_table)
    else:
        story.append(Paragraph("暂无教师评语", _style_muted))

    doc.build(story)
    return buf.getvalue()


def _make_score_trend_chart(score_trend) -> Drawing:
    """生成得分趋势折线图。如果所有点都无分数则返回空 Drawing。"""
    points = [
        (i, p.avg_score)
        for i, p in enumerate(score_trend)
        if p.avg_score is not None
    ]
    drawing = Drawing(160 * mm, 60 * mm)
    if not points:
        return drawing

    lp = LinePlot()
    lp.x = 35
    lp.y = 25
    lp.height = 120
    lp.width = 420
    lp.data = [points]
    lp.lines[0].strokeColor = _PRIMARY
    lp.lines[0].strokeWidth = 2
    lp.lines[0].symbol = None
    lp.joinedLines = 1
    lp.valueAxis.valueMin = 0
    lp.valueAxis.valueMax = 100
    lp.valueAxis.valueStep = 20
    lp.valueAxis.labelTextFormat = "%d"
    lp.valueAxis.labels.fontName = _FONT
    lp.valueAxis.labels.fontSize = 8
    lp.categoryAxis.labels.fontName = _FONT
    lp.categoryAxis.labels.fontSize = 7
    lp.categoryAxis.labels.angle = 30
    lp.categoryAxis.categoryNames = [p.date for p in score_trend]
    lp.categoryAxis.visibleGrid = True
    lp.categoryAxis.gridStrokeColor = _BORDER
    lp.categoryAxis.gridStrokeWidth = 0.3
    drawing.add(lp)
    return drawing


def _make_freq_chart(freq) -> Drawing:
    """生成提交频率条形图。"""
    drawing = Drawing(160 * mm, 60 * mm)
    counts = [p.count for p in freq]
    if not counts:
        return drawing

    bc = VerticalBarChart()
    bc.x = 35
    bc.y = 25
    bc.height = 120
    bc.width = 420
    bc.data = [counts]
    bc.bars[0].fillColor = _PRIMARY
    bc.bars[0].strokeColor = _PRIMARY
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(counts) + 1 if counts else 5
    bc.valueAxis.valueStep = 1
    bc.valueAxis.labels.fontName = _FONT
    bc.valueAxis.labels.fontSize = 8
    bc.categoryAxis.labels.fontName = _FONT
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = [p.date for p in freq]
    bc.categoryAxis.visibleGrid = True
    bc.categoryAxis.gridStrokeColor = _BORDER
    bc.categoryAxis.gridStrokeWidth = 0.3
    drawing.add(bc)
    return drawing

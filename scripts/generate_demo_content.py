"""生成演示用课件和教学资源，并通过 API 上传到系统。"""

import io
import os
import sys
import requests
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from docx import Document
from docx.shared import Inches as DocxInches, Pt as DocxPt, Cm
from docx.dml.color import RGBColor as DocxRGBColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ── 配置 ──
API_BASE = "http://127.0.0.1:8001/api/v1"
TEACHER_USERNAME = "teacher"
TEACHER_PASSWORD = "Teacher123456"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "_demo_content")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 中文字体注册（reportlab）──
FONT_PATH = r"C:\Windows\Fonts\simsun.ttc"
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("SimSun", FONT_PATH))
    CN_FONT = "SimSun"
else:
    CN_FONT = "Helvetica"

# ── PPT 配色 ──
BG_GREEN = RGBColor(0xE8, 0xF5, 0xE9)
TITLE_GREEN = RGBColor(0x2E, 0x7D, 0x32)
DARK_TEXT = RGBColor(0x1B, 0x1B, 0x1B)
ACCENT_ORANGE = RGBColor(0xF5, 0x7C, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def make_ppt(filename, title, subtitle, slides_data):
    """生成 PPT 文件。slides_data: [(slide_title, [bullet_points]), ...]"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # 封面
    cover = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    bg = cover.background.fill
    bg.solid()
    bg.fore_color.rgb = BG_GREEN
    txBox = cover.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(2))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = TITLE_GREEN
    p.alignment = PP_ALIGN.CENTER
    p2 = tf.add_paragraph()
    p2.text = subtitle
    p2.font.size = Pt(18)
    p2.font.color.rgb = ACCENT_ORANGE
    p2.alignment = PP_ALIGN.CENTER

    # 内容页
    for slide_title, bullets in slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        # 标题栏
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(1))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = slide_title
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = TITLE_GREEN
        # 内容
        txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.5), Inches(5.5))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        for i, bullet in enumerate(bullets):
            p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
            p.text = f"• {bullet}"
            p.font.size = Pt(18)
            p.font.color.rgb = DARK_TEXT
            p.space_after = Pt(12)

    # 封底
    end = prs.slides.add_slide(prs.slide_layouts[6])
    bg = end.background.fill
    bg.solid()
    bg.fore_color.rgb = BG_GREEN
    txBox = end.shapes.add_textbox(Inches(1), Inches(3), Inches(8), Inches(1.5))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "谢谢！"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = TITLE_GREEN
    p.alignment = PP_ALIGN.CENTER

    filepath = os.path.join(OUTPUT_DIR, filename)
    prs.save(filepath)
    return filepath


def make_pdf_observation_sheet(filename):
    """生成 PDF 观察记录表"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    cn_title = ParagraphStyle("CnTitle", parent=styles["Title"], fontName=CN_FONT, fontSize=18, textColor=colors.HexColor("#2E7D32"))
    cn_normal = ParagraphStyle("CnNormal", parent=styles["Normal"], fontName=CN_FONT, fontSize=11, leading=20)
    cn_heading = ParagraphStyle("CnHeading", parent=styles["Heading2"], fontName=CN_FONT, fontSize=14, textColor=colors.HexColor("#2E7D32"))

    elems = []
    elems.append(Paragraph("番茄生长观察记录表", cn_title))
    elems.append(Spacer(1, 10 * mm))

    # 基本信息表
    info_data = [
        ["观察日期", "", "观察人", ""],
        ["所在小组", "", "作物名称", "番茄"],
        ["生长阶段", "", "观察地点", "智慧大棚"],
    ]
    t = Table(info_data, colWidths=[30 * mm, 50 * mm, 30 * mm, 50 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F5E9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E8F5E9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 8 * mm))

    # 观察项目
    elems.append(Paragraph("一、环境参数记录", cn_heading))
    env_data = [
        ["参数", "数值", "单位", "是否适宜"],
        ["空气温度", "", "℃", "□ 适宜  □ 偏高  □ 偏低"],
        ["空气湿度", "", "%", "□ 适宜  □ 偏高  □ 偏低"],
        ["土壤温度", "", "℃", "□ 适宜  □ 偏高  □ 偏低"],
        ["土壤湿度", "", "%", "□ 适宜  □ 偏高  □ 偏低"],
        ["光照强度", "", "lux", "□ 适宜  □ 偏强  □ 偏弱"],
        ["土壤 pH", "", "—", "□ 适宜  □ 偏酸  □ 偏碱"],
    ]
    t2 = Table(env_data, colWidths=[30 * mm, 30 * mm, 20 * mm, 60 * mm])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(t2)
    elems.append(Spacer(1, 6 * mm))

    # 植物观察
    elems.append(Paragraph("二、植物生长观察", cn_heading))
    plant_data = [
        ["观察项目", "观察记录"],
        ["株高（cm）", ""],
        ["叶片数量", ""],
        ["叶片颜色", "□ 深绿  □ 浅绿  □ 发黄  □ 有斑点"],
        ["是否有花/果", "□ 无  □ 开花  □ 结果  □ 成熟"],
        ["病虫害情况", "□ 无  □ 轻微  □ 严重（描述：         ）"],
    ]
    t3 = Table(plant_data, colWidths=[40 * mm, 100 * mm])
    t3.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(t3)
    elems.append(Spacer(1, 6 * mm))

    # 文字描述
    elems.append(Paragraph("三、观察心得与发现", cn_heading))
    for _ in range(4):
        elems.append(Paragraph("_________________________________________________________________", cn_normal))
        elems.append(Spacer(1, 4 * mm))

    doc.build(elems)
    return filepath


def make_pdf_sensor_guide(filename):
    """生成 PDF 传感器使用手册"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    cn_title = ParagraphStyle("CnTitle", parent=styles["Title"], fontName=CN_FONT, fontSize=18, textColor=colors.HexColor("#2E7D32"))
    cn_heading = ParagraphStyle("CnHeading", parent=styles["Heading2"], fontName=CN_FONT, fontSize=14, textColor=colors.HexColor("#2E7D32"))
    cn_normal = ParagraphStyle("CnNormal", parent=styles["Normal"], fontName=CN_FONT, fontSize=11, leading=20)

    elems = []
    elems.append(Paragraph("智慧大棚传感器使用手册", cn_title))
    elems.append(Spacer(1, 8 * mm))
    elems.append(Paragraph("本手册介绍智慧大棚中各类传感器的作用、安装方法和数据读取方式。", cn_normal))
    elems.append(Spacer(1, 6 * mm))

    sections = [
        ("一、传感器类型与功能", [
            "1. 空气温湿度传感器（DHT22）：测量大棚内空气温度（0-50℃）和湿度（0-100%RH）",
            "2. 土壤温湿度传感器：测量土壤温度和体积含水量",
            "3. 光照传感器：测量环境光照强度（0-65535 lux）",
            "4. 土壤 pH 传感器：测量土壤酸碱度（0-14）",
        ]),
        ("二、安装注意事项", [
            "1. 空气传感器应安装在植物冠层上方 20-30cm 处，避免阳光直射",
            "2. 土壤传感器插入深度 5-10cm，避免接触肥料集中区域",
            "3. 光照传感器安装在无遮挡的顶部位置",
            "4. 所有传感器线缆应做好防水处理",
        ]),
        ("三、数据读取", [
            "1. 通过 ESP32 主控板读取传感器数据",
            "2. 数据通过 MQTT 协议上传到服务器",
            "3. 在前端「传感器数据」页面可查看实时数据和历史曲线",
            "4. 学生端可通过「我的传感器」查看本组数据",
        ]),
        ("四、常见问题", [
            "1. 数据异常波动 → 检查传感器接线是否松动",
            "2. 数值恒定不变 → 传感器可能损坏，需更换",
            "3. 湿度始终 99% → 传感器表面可能有水珠，擦干即可",
            "4. pH 读数偏差 → 需要用标准液校准",
        ]),
    ]

    for heading, items in sections:
        elems.append(Paragraph(heading, cn_heading))
        elems.append(Spacer(1, 3 * mm))
        for item in items:
            elems.append(Paragraph(item, cn_normal))
        elems.append(Spacer(1, 4 * mm))

    doc.build(elems)
    return filepath


def make_docx_experiment_template(filename):
    """生成 DOCX 实验报告模板"""
    doc = Document()
    # 标题
    title = doc.add_heading("科学实验报告", level=0)
    title.alignment = 1  # center
    for run in title.runs:
        run.font.color.rgb = DocxRGBColor(0x2E, 0x7D, 0x32)

    doc.add_paragraph("")

    # 基本信息表
    table = doc.add_table(rows=4, cols=4)
    table.style = "Table Grid"
    cells = [
        ("实验名称", "", "实验日期", ""),
        ("实验人", "", "所在小组", ""),
        ("实验类型", "□ 对照实验  □ 观察实验  □ 比较实验", "指导教师", ""),
        ("实验地点", "智慧大棚", "实验器材", ""),
    ]
    for row_idx, (a, b, c, d) in enumerate(cells):
        table.cell(row_idx, 0).text = a
        table.cell(row_idx, 1).text = b
        table.cell(row_idx, 2).text = c
        table.cell(row_idx, 3).text = d

    doc.add_paragraph("")

    # 一、实验目的
    doc.add_heading("一、实验目的", level=1)
    doc.add_paragraph("（请描述本次实验的目标和预期效果）")
    doc.add_paragraph("")

    # 二、实验假设
    doc.add_heading("二、实验假设", level=1)
    doc.add_paragraph("如果             ，那么             ，因为             。")
    doc.add_paragraph("")

    # 三、实验变量
    doc.add_heading("三、实验变量", level=1)
    var_table = doc.add_table(rows=4, cols=2)
    var_table.style = "Table Grid"
    var_data = [
        ("自变量（我们改变的条件）", ""),
        ("因变量（我们观察的结果）", ""),
        ("控制变量（保持不变的条件）", ""),
        ("对照组设置", ""),
    ]
    for i, (k, v) in enumerate(var_data):
        var_table.cell(i, 0).text = k
        var_table.cell(i, 1).text = v

    doc.add_paragraph("")

    # 四、实验步骤
    doc.add_heading("四、实验步骤", level=1)
    for i in range(1, 6):
        doc.add_paragraph(f"步骤 {i}：")
    doc.add_paragraph("")

    # 五、数据记录
    doc.add_heading("五、数据记录", level=1)
    data_table = doc.add_table(rows=6, cols=4)
    data_table.style = "Table Grid"
    headers = ["观察时间", "对照组数据", "实验组数据", "差异描述"]
    for i, h in enumerate(headers):
        data_table.cell(0, i).text = h
    for row in range(1, 6):
        for col in range(4):
            data_table.cell(row, col).text = ""

    doc.add_paragraph("")

    # 六、实验结论
    doc.add_heading("六、实验结论", level=1)
    doc.add_paragraph("通过本次实验，我们发现：")
    doc.add_paragraph("")

    # 七、反思与改进
    doc.add_heading("七、反思与改进", level=1)
    doc.add_paragraph("实验中遇到的问题：")
    doc.add_paragraph("下次改进方向：")

    filepath = os.path.join(OUTPUT_DIR, filename)
    doc.save(filepath)
    return filepath


def login():
    """登录获取 token"""
    resp = requests.post(
        f"{API_BASE}/auth/login",
        data={"username": TEACHER_USERNAME, "password": TEACHER_PASSWORD, "grant_type": "password"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


MIME_MAP = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".mp4": "video/mp4",
}


def upload_courseware(token, filepath, title, description, file_type, subject, grade_level, tags, is_public):
    """上传课件"""
    headers = {"Authorization": f"Bearer {token}"}
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()
    mime = MIME_MAP.get(ext, "application/octet-stream")
    with open(filepath, "rb") as f:
        files = {"file": (filename, f, mime)}
        data = {
            "title": title,
            "description": description,
            "file_type": file_type,
            "subject": subject,
            "grade_level": grade_level,
            "tags": tags,
            "is_public": str(is_public).lower(),
        }
        resp = requests.post(f"{API_BASE}/courseware", headers=headers, files=files, data=data)
    resp.raise_for_status()
    print(f"  [课件] {title} → {resp.json()['file_url']}")
    return resp.json()


def upload_resource(token, filepath, title, description, resource_type, subject, classroom_id=None, is_published=True):
    """上传教学资源"""
    headers = {"Authorization": f"Bearer {token}"}
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()
    mime = MIME_MAP.get(ext, "application/octet-stream")
    with open(filepath, "rb") as f:
        files = {"file": (filename, f, mime)}
        data = {
            "title": title,
            "description": description,
            "resource_type": resource_type,
            "subject": subject,
            "is_published": str(is_published).lower(),
        }
        if classroom_id:
            data["classroom_id"] = str(classroom_id)
        resp = requests.post(f"{API_BASE}/resources", headers=headers, files=files, data=data)
    resp.raise_for_status()
    print(f"  [资源] {title} → {resp.json()['file_url']}")
    return resp.json()


def main():
    print("=" * 60)
    print("生成演示用课件和教学资源")
    print("=" * 60)

    # ── 1. 生成 PPT 课件 ──
    print("\n[1/3] 生成 PPT 课件...")

    ppt1 = make_ppt(
        "番茄种植观察指南.pptx",
        "番茄种植观察指南",
        "小学劳动课 · 五年级",
        [
            ("学习目标", [
                "了解番茄的生长周期和适宜环境",
                "掌握番茄种植的基本步骤",
                "学会使用传感器监测生长环境",
                "培养观察记录的科学素养",
            ]),
            ("番茄的生长周期", [
                "种子期：播种后 5-7 天发芽",
                "幼苗期：2-3 片真叶，约 2-3 周",
                "开花期：定植后 30-40 天开始开花",
                "结果期：花后 40-50 天果实成熟",
                "全生长周期约 90-120 天",
            ]),
            ("适宜生长环境", [
                "温度：白天 25-28℃，夜间 15-18℃",
                "湿度：空气湿度 50-65%，土壤湿度 60-70%",
                "光照：每天 8 小时以上充足光照",
                "土壤 pH：6.0-6.8 微酸性",
                "光照强度：20000-40000 lux",
            ]),
            ("智慧大棚中的传感器", [
                "空气温湿度传感器 → 实时监测环境",
                "土壤温湿度传感器 → 精准灌溉",
                "光照传感器 → 补光控制",
                "pH 传感器 → 土壤酸碱度监测",
                "数据通过 ESP32 上传到云端平台",
            ]),
            ("观察任务", [
                "每天记录大棚内温湿度数据",
                "每三天测量一次番茄株高",
                "观察叶片颜色和数量变化",
                "拍照记录生长状态",
                "填写观察记录表并上传到平台",
            ]),
        ],
    )
    print(f"  ✓ {ppt1}")

    ppt2 = make_ppt(
        "传感器与智慧农业.pptx",
        "传感器与智慧农业",
        "小学科学课 · 五年级",
        [
            ("什么是传感器", [
                "传感器：能感受被测量信息并转换成电信号的器件",
                "就像人类的「五官」：眼（光）、皮肤（温度）、鼻（气味）",
                "传感器让大棚变得「聪明」，能自动感知环境",
                "是物联网（IoT）技术的基础",
            ]),
            ("大棚里的传感器家族", [
                "温度传感器 → 类似皮肤感受冷热",
                "湿度传感器 → 检测空气中水分含量",
                "光照传感器 → 类似眼睛感受光线强弱",
                "土壤 pH 传感器 → 检测土壤酸碱度",
                "每个传感器都有特定的测量范围和精度",
            ]),
            ("传感器如何工作", [
                "第一步：传感器感知环境变化",
                "第二步：将物理量转换为电信号",
                "第三步：ESP32 主控板读取信号",
                "第四步：通过 MQTT 协议发送到服务器",
                "第五步：前端页面实时显示数据",
            ]),
            ("自动控制原理", [
                "设定规则：当温度 > 30℃ → 开启风扇",
                "设定规则：当土壤湿度 < 40% → 开启水泵",
                "设定规则：当光照不足 → 开启补光灯",
                "传感器 + 规则 + 执行器 = 智慧农业",
                "减少人工干预，提高种植效率",
            ]),
            ("动手实践", [
                "分组查看本组大棚的传感器数据",
                "记录一天的温湿度变化曲线",
                "讨论：为什么中午温度最高？",
                "思考：如何利用传感器数据照顾植物？",
            ]),
        ],
    )
    print(f"  ✓ {ppt2}")

    ppt3 = make_ppt(
        "大棚环境参数与植物生长.pptx",
        "大棚环境参数与植物生长",
        "小学科学课 · 五年级",
        [
            ("植物生长的条件", [
                "阳光 → 光合作用的能量来源",
                "水分 → 营养运输和蒸腾作用",
                "温度 → 影响酶活性和代谢速度",
                "土壤 → 提供养分和支撑根系",
                "空气 → 二氧化碳用于光合作用",
            ]),
            ("温度对植物的影响", [
                "最适温度：20-30℃（多数蔬菜）",
                "高温（>35℃）：蛋白质变性，生长停滞",
                "低温（<10℃）：代谢减缓，可能冻伤",
                "昼夜温差大有利于积累养分",
                "智慧大棚可自动调节温度",
            ]),
            ("湿度与植物健康", [
                "空气湿度过高 → 病虫害风险增加",
                "空气湿度过低 → 蒸腾过快，萎蔫",
                "土壤湿度过高 → 根系缺氧腐烂",
                "土壤湿度过低 → 缺水枯萎",
                "适宜范围：空气 50-70%，土壤 60-70%",
            ]),
            ("光照与光合作用", [
                "光照是光合作用的能量来源",
                "光照不足 → 植物徒长、叶色发黄",
                "光照过强 → 叶片灼伤",
                "补光灯可在阴天补充光照",
                "不同植物对光照需求不同",
            ]),
            ("数据驱动的种植决策", [
                "利用传感器数据优化种植条件",
                "建立环境参数与产量的关系模型",
                "通过对比实验验证最佳参数",
                "科技让农业更精准、更高效",
            ]),
        ],
    )
    print(f"  ✓ {ppt3}")

    # ── 2. 生成教学资源 ──
    print("\n[2/3] 生成教学资源（PDF + DOCX）...")

    pdf1 = make_pdf_observation_sheet("番茄生长观察记录表.pdf")
    print(f"  ✓ {pdf1}")

    pdf2 = make_pdf_sensor_guide("传感器使用手册.pdf")
    print(f"  ✓ {pdf2}")

    docx1 = make_docx_experiment_template("科学实验报告模板.docx")
    print(f"  ✓ {docx1}")

    # ── 3. 启动后端并上传 ──
    print("\n[3/3] 登录并上传到系统...")

    token = login()
    print(f"  ✓ 教师登录成功")

    # 上传课件
    print("\n  上传课件...")
    upload_courseware(token, ppt1, "番茄种植观察指南", "小学劳动课课件，介绍番茄种植步骤和观察方法", "ppt", "labor", "五年级", "番茄,种植,观察,劳动课", True)
    upload_courseware(token, ppt2, "传感器与智慧农业", "科学课课件，介绍传感器原理和智慧农业概念", "ppt", "science", "五年级", "传感器,物联网,智慧农业,科学课", True)
    upload_courseware(token, ppt3, "大棚环境参数与植物生长", "科学课课件，分析环境参数对植物生长的影响", "ppt", "science", "五年级", "环境,植物,光合作用,科学课", False)

    # 上传教学资源
    print("\n  上传教学资源...")
    upload_resource(token, pdf1, "番茄生长观察记录表", "学生使用的番茄生长观察记录表模板，含环境参数和植物观察项", "pdf", "labor", classroom_id=1, is_published=True)
    upload_resource(token, pdf2, "传感器使用手册", "智慧大棚传感器使用指南，含安装、数据读取和常见问题", "pdf", "science", classroom_id=1, is_published=True)
    upload_resource(token, docx1, "科学实验报告模板", "通用科学实验报告模板，含假设、变量、步骤、数据记录和结论", "doc", "science", classroom_id=1, is_published=True)

    print("\n" + "=" * 60)
    print("✅ 全部完成！共生成并上传 3 个课件 + 3 个教学资源")
    print("=" * 60)


if __name__ == "__main__":
    main()

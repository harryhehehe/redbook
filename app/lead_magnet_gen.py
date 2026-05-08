"""Generate lead-magnet PDFs (e.g. '深圳中考数学特色分析').

设计目标：精品手册风格 PDF，可直接私信发给小红书粉丝。
- 内容：千问输出结构化 JSON（含完整例题解析）
- 排版：A4，小红书红主色，章节卡片化，例题分四段（题目/思路/详解/小结）
- 字符：所有文本经过消毒，去掉雅黑不支持的 emoji 组合符（避免豆腐方框）
"""
from __future__ import annotations
import io
import re
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

from . import llm_client


# ============================================================
# 字体注册
# ============================================================
FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_REGULAR = "MSYH"
FONT_BOLD = "MSYHBD"
_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONT_DIR / "msyh.ttc")))
    try:
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "msyhbd.ttc")))
    except Exception:
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "msyh.ttc")))
    _FONTS_REGISTERED = True


# ============================================================
# 字符消毒：去掉雅黑不支持的 emoji，避免豆腐方框
# ============================================================
# 雅黑不支持的关键字符：
#   U+FE0F  variation selector-16（emoji 表现）
#   U+20E3  combining enclosing keycap（数字键盘符号）
#   U+200D  zero-width joiner
#   U+1F300+ 大部分 emoji 区段
_KEYCAP_DIGITS = {
    "0\ufe0f\u20e3": "⓪", "1\ufe0f\u20e3": "①", "2\ufe0f\u20e3": "②",
    "3\ufe0f\u20e3": "③", "4\ufe0f\u20e3": "④", "5\ufe0f\u20e3": "⑤",
    "6\ufe0f\u20e3": "⑥", "7\ufe0f\u20e3": "⑦", "8\ufe0f\u20e3": "⑧",
    "9\ufe0f\u20e3": "⑨",
}
# 常用 emoji → 文字标签
_EMOJI_REPLACE = {
    "🌰": "", "💡": "", "📝": "", "🎯": "", "✅": "✓", "❌": "✗",
    "🔥": "", "📌": "", "👉": "→", "📚": "", "🎁": "", "⭐": "★",
    "📊": "", "🏫": "", "📖": "", "✏️": "", "🚀": "", "💯": "",
}
_EMOJI_RE = re.compile(
    "[" 
    "\U0001F300-\U0001FAFF"
    "\U0001F900-\U0001F9FF"
    "\u2600-\u27BF"
    "]",
    flags=re.UNICODE,
)


def sanitize(text: str) -> str:
    """去掉雅黑不支持的字符，避免 PDF 中出现豆腐方框。"""
    if not text:
        return ""
    s = str(text)
    # 1. keycap 数字 1️⃣ → ①
    for k, v in _KEYCAP_DIGITS.items():
        s = s.replace(k, v)
    # 2. 已知 emoji 替换
    for k, v in _EMOJI_REPLACE.items():
        s = s.replace(k, v)
    # 3. 兜底：去掉剩余 emoji
    s = _EMOJI_RE.sub("", s)
    # 4. 去掉零宽 / 变体选择符
    s = s.replace("\ufe0f", "").replace("\ufe0e", "").replace("\u200d", "")
    # 5. 规整空白
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def _esc(text: str) -> str:
    """先消毒，再 HTML escape。"""
    s = sanitize(text)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ============================================================
# 内容生成 (LLM)
# ============================================================
CONTENT_SYSTEM_PROMPT = """你是深圳本地一位资深初中数学家教老师，正在为小红书引流的家长/学生制作一份"精品手册"PDF。
这份手册的目标是：让对方读完后觉得"这个老师专业，我要私聊咨询"。

输出严格 JSON，禁止 markdown 代码块包裹：

{
  "title": "资料主标题（≤18字，不要 emoji）",
  "subtitle": "副标题（一句话价值主张，20-35字）",
  "author_tag": "作者署名行，如'深圳初中数学家教 · 8届毕业班 · 押中3次中考压轴'",
  "intro": "开篇引言（120-200字，第一人称'我'，建立信任，点明痛点，说明这份手册的价值）",
  "sections": [
    {
      "heading": "章节标题（5-15字，不要带数字序号，不要 emoji，序号由排版自动加）",
      "summary": "本章一句话总结（20-40字）",
      "points": [
        "要点1（必须 50-100 字，具体、可执行，不要套话）",
        "要点2",
        "要点3"
      ],
      "example": {
        "problem": "完整题目描述（含已知条件、求解目标，不要编造年份和题号，可写'深圳中考真题改编'）",
        "approach": "解题思路（80-150字，讲为什么这么想、关键突破口在哪、用了什么技巧）",
        "solution": "详细解题步骤（用 \\n 换行分步骤，每步说清楚做了什么、为什么、得到什么。150-300字）",
        "answer": "最终答案（一行，如'x = 3 或 x = -2'）",
        "takeaway": "本题知识点提炼（30-60字，告诉读者下次见到同类题怎么办）"
      }
    }
  ],
  "key_insight": "全篇核心金句（一句话，建立认知差，30-50字）",
  "outro": "结尾 CTA（80-150字，引导关注、扣其他关键词领更多资料、私信约课）"
}

硬性要求：
1. sections 数量 4-6 个，每章必须有完整 example（4 段都要写满，不能省略）
2. 内容必须**具体到可操作**，禁止"加强练习""注重基础"这种空话
3. 真题不要编造具体年份和题号，但题目本身要真实可解
4. 全程第一人称"我"，口语化但专业
5. 整份资料必须围绕标题，前后逻辑闭环
6. 严禁在任何字段中使用 emoji 表情符号（包括 1️⃣ 🌰 💡 等），所有图标由排版引擎统一处理
"""


def generate_content(keyword: str, resource_name: str, resource_desc: str = "",
                     audience: str = "parent", extra_instructions: str = "") -> dict:
    extra_block = ""
    if extra_instructions.strip():
        extra_block = f"""

【用户额外要求 — 必须严格遵守，优先级高于上面的默认 schema 规则】
{extra_instructions.strip()}
"""

    user_prompt = f"""【资料关键词】{keyword}
【资料名称】《{resource_name}》
【资料描述】{resource_desc}
【目标受众】{audience}（parent=家长视角讲选择和方法论；student=学生视角讲解题；both=兼顾）
{extra_block}
请按 schema 生成完整 JSON，特别注意：每个 section 的 example 必须含 problem / approach / solution / answer / takeaway 五段，缺一不可。"""
    return llm_client.generate_blocks_raw(CONTENT_SYSTEM_PROMPT, user_prompt)


# ============================================================
# 排版样式
# ============================================================
BRAND = colors.HexColor("#FF2442")        # 小红书红
BRAND_DARK = colors.HexColor("#C81E36")
DARK = colors.HexColor("#1F1F1F")
GRAY = colors.HexColor("#6B6B6B")
LIGHT_GRAY = colors.HexColor("#999999")
SOFT_BG = colors.HexColor("#FFF4F5")      # 例题底色
APPROACH_BG = colors.HexColor("#FFF9E6")  # 思路底色
SOLUTION_BG = colors.HexColor("#F0F7FF")  # 详解底色
DIVIDER = colors.HexColor("#FFD6DC")


def _styles():
    _register_fonts()
    return {
        "title": ParagraphStyle(
            "title", fontName=FONT_BOLD, fontSize=28, leading=36,
            textColor=BRAND, alignment=1, spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=FONT_REGULAR, fontSize=13, leading=22,
            textColor=DARK, alignment=1, spaceAfter=8,
        ),
        "author": ParagraphStyle(
            "author", fontName=FONT_REGULAR, fontSize=10, leading=14,
            textColor=GRAY, alignment=1, spaceAfter=24,
        ),
        "intro": ParagraphStyle(
            "intro", fontName=FONT_REGULAR, fontSize=11, leading=21,
            textColor=DARK, spaceAfter=18, firstLineIndent=22,
            alignment=4,  # justify
        ),
        # 章节大标题（带序号色块由 Table 渲染，这里只渲染右侧文字）
        "h2": ParagraphStyle(
            "h2", fontName=FONT_BOLD, fontSize=17, leading=24,
            textColor=DARK, spaceBefore=0, spaceAfter=0, leftIndent=0,
        ),
        "h2_summary": ParagraphStyle(
            "h2_summary", fontName=FONT_REGULAR, fontSize=10, leading=16,
            textColor=GRAY, spaceBefore=4, spaceAfter=10, leftIndent=0,
        ),
        "point": ParagraphStyle(
            "point", fontName=FONT_REGULAR, fontSize=11, leading=20,
            textColor=DARK, leftIndent=20, bulletIndent=4,
            spaceAfter=6, alignment=4,
        ),
        # 例题相关
        "ex_label": ParagraphStyle(
            "ex_label", fontName=FONT_BOLD, fontSize=10, leading=14,
            textColor=BRAND_DARK, spaceBefore=2, spaceAfter=4,
        ),
        "ex_text": ParagraphStyle(
            "ex_text", fontName=FONT_REGULAR, fontSize=10.5, leading=18,
            textColor=DARK, spaceAfter=2, alignment=4,
        ),
        "ex_solution": ParagraphStyle(
            "ex_solution", fontName=FONT_REGULAR, fontSize=10.5, leading=19,
            textColor=DARK, spaceAfter=2, leftIndent=4,
        ),
        "ex_answer": ParagraphStyle(
            "ex_answer", fontName=FONT_BOLD, fontSize=11, leading=18,
            textColor=BRAND_DARK, spaceAfter=2,
        ),
        "ex_takeaway": ParagraphStyle(
            "ex_takeaway", fontName=FONT_REGULAR, fontSize=10, leading=17,
            textColor=DARK, spaceAfter=2, alignment=4,
        ),
        # 金句
        "insight": ParagraphStyle(
            "insight", fontName=FONT_BOLD, fontSize=14, leading=24,
            textColor=BRAND, alignment=1, spaceBefore=18, spaceAfter=14,
        ),
        "outro": ParagraphStyle(
            "outro", fontName=FONT_REGULAR, fontSize=11, leading=20,
            textColor=DARK, alignment=1, spaceBefore=12, spaceAfter=4,
        ),
        # 序号色块里的白色数字
        "section_num": ParagraphStyle(
            "section_num", fontName=FONT_BOLD, fontSize=20, leading=24,
            textColor=colors.white, alignment=1,
        ),
    }


# ============================================================
# 页眉页脚
# ============================================================
def _on_page(canvas, doc):
    canvas.saveState()
    page_w, page_h = A4

    # 页眉小色条
    canvas.setFillColor(BRAND)
    canvas.rect(0, page_h - 0.4 * cm, page_w, 0.4 * cm, fill=1, stroke=0)

    # 页脚
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(
        page_w / 2, 1.0 * cm,
        sanitize(f"深圳初中数学家教 · 第 {doc.page} 页 · 关注获取更多干货"),
    )
    canvas.setStrokeColor(DIVIDER)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.4 * cm, page_w - 2 * cm, 1.4 * cm)
    canvas.restoreState()


# ============================================================
# 排版组件
# ============================================================
def _brand_divider(width_cm=16.0, color=BRAND, thickness=2):
    t = Table([[""]], colWidths=[width_cm * cm], rowHeights=[thickness])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
    return t


def _section_header(idx: int, heading: str, summary: str, s):
    """带圆角序号块的章节大标题。"""
    num_para = Paragraph(str(idx), s["section_num"])
    head_para = Paragraph(_esc(heading), s["h2"])
    sum_para = Paragraph(_esc(summary), s["h2_summary"]) if summary else Spacer(1, 0)

    # 右侧 cell 用嵌套表组合 heading + summary
    right = Table(
        [[head_para], [sum_para]],
        colWidths=[14.4 * cm],
    )
    right.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    outer = Table(
        [[num_para, right]],
        colWidths=[1.2 * cm, 14.8 * cm],
        rowHeights=[1.2 * cm],
    )
    outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BRAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return outer


def _example_block(ex: dict, s):
    """例题卡片：题目 / 思路 / 详解 / 答案 / 小结。"""
    rows = []

    if ex.get("problem"):
        rows.append([Paragraph("【例题】", s["ex_label"])])
        rows.append([Paragraph(_esc(ex["problem"]), s["ex_text"])])

    if ex.get("approach"):
        rows.append([Paragraph("【解题思路】", s["ex_label"])])
        rows.append([Paragraph(_esc(ex["approach"]), s["ex_text"])])

    if ex.get("solution"):
        rows.append([Paragraph("【详细步骤】", s["ex_label"])])
        # solution 中的 \n 转 <br/>
        sol_html = _esc(ex["solution"]).replace("\n", "<br/>")
        rows.append([Paragraph(sol_html, s["ex_solution"])])

    if ex.get("answer"):
        rows.append([Paragraph(f"【答案】 {_esc(ex['answer'])}", s["ex_answer"])])

    if ex.get("takeaway"):
        rows.append([Paragraph("【知识点提炼】", s["ex_label"])])
        rows.append([Paragraph(_esc(ex["takeaway"]), s["ex_takeaway"])])

    if not rows:
        return Spacer(1, 0)

    t = Table(rows, colWidths=[16 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBEFORE", (0, 0), (0, -1), 3, BRAND),
    ]))
    return t


# ============================================================
# 主渲染
# ============================================================
def render_pdf(content: dict) -> bytes:
    s = _styles()
    buf = io.BytesIO()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=sanitize(content.get("title", "引流资料")),
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_on_page)])

    story = []

    # ---------- 封面区 ----------
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph(_esc(content.get("title", "")), s["title"]))
    if content.get("subtitle"):
        story.append(Paragraph(_esc(content["subtitle"]), s["subtitle"]))
    if content.get("author_tag"):
        story.append(Paragraph(_esc(content["author_tag"]), s["author"]))

    story.append(_brand_divider())
    story.append(Spacer(1, 0.5 * cm))

    # ---------- 引言 ----------
    if content.get("intro"):
        story.append(Paragraph(_esc(content["intro"]), s["intro"]))
        story.append(Spacer(1, 0.3 * cm))

    # ---------- 章节 ----------
    for idx, sec in enumerate(content.get("sections", []), start=1):
        story.append(Spacer(1, 0.9 * cm))
        story.append(_section_header(idx, sec.get("heading", ""), sec.get("summary", ""), s))
        story.append(Spacer(1, 0.35 * cm))

        for pt in sec.get("points", []):
            bullet = f'<font color="#FF2442" size="14"><b>●</b></font>'
            story.append(Paragraph(f"{bullet}  {_esc(pt)}", s["point"]))

        ex = sec.get("example")
        if ex:
            story.append(Spacer(1, 0.2 * cm))
            # example 兼容 dict 和老的 string
            if isinstance(ex, str):
                ex = {"problem": ex}
            story.append(_example_block(ex, s))

    # ---------- 金句 ----------
    if content.get("key_insight"):
        story.append(Spacer(1, 0.5 * cm))
        story.append(_brand_divider(thickness=1, color=DIVIDER))
        story.append(Paragraph(_esc(content["key_insight"]), s["insight"]))
        story.append(_brand_divider(thickness=1, color=DIVIDER))

    # ---------- 结尾 CTA ----------
    if content.get("outro"):
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(_esc(content["outro"]), s["outro"]))

    doc.build(story)
    return buf.getvalue()

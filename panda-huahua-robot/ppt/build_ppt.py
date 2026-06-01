# -*- coding: utf-8 -*-
"""
熊猫花花 AI 互动陪伴机器人 —— 投资人汇报 PPT 生成脚本
依赖: python-pptx, Pillow
运行: python build_ppt.py
输出: 熊猫花花投资汇报.pptx

▶ 使用真实「花花」IP 素材:
   把你已获授权的花花图片(png/jpg/webp)放到 ../assets/ 目录下,
   文件名建议含 "huahua" 或 "花花"(例如 assets/huahua.png),
   重新运行本脚本即可——脚本会自动裁成圆形贴到封面/定位页/结尾页;
   若 assets/ 无图片, 则回退到内置的简笔熊猫图标。
"""
import os
import glob
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
try:
    from PIL import Image, ImageDraw
    _PIL_OK = True
except Exception:
    _PIL_OK = False
import copy

# ---------------- 主题配色 ----------------
INK      = RGBColor(0x1A, 0x1A, 0x1A)   # 熊猫黑
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
PAPER    = RGBColor(0xF6, 0xF7, 0xF3)   # 米白背景
BAMBOO   = RGBColor(0x4C, 0x9A, 0x2A)   # 竹叶绿
BAMBOO_D = RGBColor(0x2F, 0x6B, 0x1C)   # 深绿
PINK     = RGBColor(0xFF, 0x7A, 0x93)   # 暖粉(花花腮红)
GOLD     = RGBColor(0xE8, 0xA8, 0x2B)   # 暖金
GRAY     = RGBColor(0x6B, 0x6F, 0x6A)   # 中灰
LIGHT    = RGBColor(0xE9, 0xEC, 0xE4)   # 浅灰卡片
DARKBG   = RGBColor(0x16, 0x1D, 0x14)   # 深色页背景

FONT = "Microsoft YaHei"  # 中文字体, 回退到系统

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]


# ---------------- 工具函数 ----------------
def add_slide():
    return prs.slides.add_slide(BLANK)


def bg(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def rect(slide, x, y, w, h, color, line=None, shape=MSO_SHAPE.RECTANGLE, shadow=False):
    sp = slide.shapes.add_shape(shape, x, y, w, h)
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1)
    sp.shadow.inherit = False
    if shadow:
        el = sp._element.spPr
        ef = el.makeelement(qn('a:effectLst'), {})
        el.append(ef)
    return sp


def txt(slide, x, y, w, h, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, font=FONT, italic=False, line_spacing=1.0):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        r.font.name = font
        # 中文字体
        rPr = r._r.get_or_add_rPr()
        ea = rPr.makeelement(qn('a:ea'), {'typeface': font})
        rPr.append(ea)
    return tb


def bullet(slide, x, y, w, h, items, size=15, color=INK, gap=1.25, mark="●",
           mark_color=BAMBOO, bold_lead=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_top = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = gap
        p.space_after = Pt(4)
        # mark
        rm = p.add_run()
        rm.text = mark + "  "
        rm.font.size = Pt(size)
        rm.font.color.rgb = mark_color
        rm.font.name = FONT
        rm.font.bold = True
        # text (支持 **加粗** 前缀)
        if "||" in it:
            head, tail = it.split("||", 1)
            r1 = p.add_run(); r1.text = head
            r1.font.size = Pt(size); r1.font.bold = True; r1.font.color.rgb = color; r1.font.name = FONT
            _ea(r1)
            r2 = p.add_run(); r2.text = tail
            r2.font.size = Pt(size); r2.font.color.rgb = color; r2.font.name = FONT
            _ea(r2)
        else:
            r = p.add_run(); r.text = it
            r.font.size = Pt(size); r.font.bold = bold_lead; r.font.color.rgb = color; r.font.name = FONT
            _ea(r)
    return tb


def _ea(run):
    rPr = run._r.get_or_add_rPr()
    ea = rPr.makeelement(qn('a:ea'), {'typeface': FONT})
    rPr.append(ea)


def page_header(slide, kicker, title, idx, dark=False):
    """统一内容页页眉"""
    main = WHITE if dark else INK
    sub = BAMBOO if not dark else RGBColor(0x9C, 0xD6, 0x6B)
    rect(slide, Inches(0.55), Inches(0.55), Inches(0.14), Inches(0.62), BAMBOO)
    txt(slide, Inches(0.8), Inches(0.5), Inches(10), Inches(0.32), kicker, 13, sub, bold=True)
    txt(slide, Inches(0.78), Inches(0.78), Inches(11.5), Inches(0.7), title, 27, main, bold=True)
    # 页码
    txt(slide, Inches(12.3), Inches(6.95), Inches(0.8), Inches(0.4),
        f"{idx:02d}", 12, GRAY, align=PP_ALIGN.RIGHT)
    txt(slide, Inches(0.55), Inches(6.95), Inches(4), Inches(0.4),
        "熊猫花花 · HuaHua AI Companion", 10, GRAY)


def panda_face(slide, cx, cy, r, ec=INK, fc=WHITE):
    """画一个简单的熊猫脸图标. cx,cy 圆心, r 半径(EMU)"""
    # 脸
    face = rect(slide, cx - r, cy - r, 2*r, 2*r, fc, shape=MSO_SHAPE.OVAL)
    # 耳朵
    er = int(r*0.6)
    rect(slide, int(cx - r*0.9 - er/2), int(cy - r*0.95 - er/2), er, er, ec, shape=MSO_SHAPE.OVAL)
    rect(slide, int(cx + r*0.9 - er/2), int(cy - r*0.95 - er/2), er, er, ec, shape=MSO_SHAPE.OVAL)
    # 黑眼圈
    pr = int(r*0.42)
    rect(slide, int(cx - r*0.45 - pr/2), int(cy - r*0.1 - pr/2), pr, pr, ec, shape=MSO_SHAPE.OVAL)
    rect(slide, int(cx + r*0.45 - pr/2), int(cy - r*0.1 - pr/2), pr, pr, ec, shape=MSO_SHAPE.OVAL)
    # 眼睛高光(白点)
    wr = int(r*0.14)
    rect(slide, int(cx - r*0.45 - wr/2), int(cy - r*0.12 - wr/2), wr, wr, WHITE, shape=MSO_SHAPE.OVAL)
    rect(slide, int(cx + r*0.45 - wr/2), int(cy - r*0.12 - wr/2), wr, wr, WHITE, shape=MSO_SHAPE.OVAL)
    # 鼻子
    nr = int(r*0.18)
    rect(slide, int(cx - nr/2), int(cy + r*0.28 - nr/2), nr, nr, ec, shape=MSO_SHAPE.OVAL)


# ---------------- 真实花花 IP 素材支持 ----------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "assets"))
_TMP_DIR = os.path.join(_SCRIPT_DIR, ".asset_cache")


def find_panda_assets():
    """在 assets/ 中查找花花图片, 优先文件名含 huahua/花花/hero 的。"""
    if not os.path.isdir(ASSET_DIR):
        return []
    cands = []
    for ext in ("png", "jpg", "jpeg", "webp", "PNG", "JPG", "JPEG", "WEBP"):
        cands += glob.glob(os.path.join(ASSET_DIR, f"*.{ext}"))
    cands = list(dict.fromkeys(os.path.normcase(os.path.abspath(p)) for p in cands))
    if not cands:
        return []

    def score(p):
        n = os.path.basename(p).lower()
        s = 0
        for kw in ("huahua", "花花", "hero", "panda", "ip"):
            if kw in n:
                s += 10
        return s

    cands.sort(key=score, reverse=True)
    return cands


_ASSET_SRCS = find_panda_assets()
_ASSET_SRC = _ASSET_SRCS[0] if _ASSET_SRCS else None
_circle_cache = {}


def _circle_png(src, size=760):
    """把图片中心裁成正方形再裁成圆形(透明背景), 缓存后返回路径。"""
    if not _PIL_OK:
        return None
    key = (src, size)
    if key in _circle_cache:
        return _circle_cache[key]
    try:
        os.makedirs(_TMP_DIR, exist_ok=True)
        im = Image.open(src).convert("RGBA")
        w, h = im.size
        m = min(w, h)
        left, top = (w - m) // 2, (h - m) // 2
        im = im.crop((left, top, left + m, top + m)).resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        im.putalpha(mask)
        out = os.path.join(_TMP_DIR, "huahua_circle_%d.png" % size)
        im.save(out)
        _circle_cache[key] = out
        return out
    except Exception as e:
        print("  [warn] 处理花花素材失败, 回退简笔熊猫:", e)
        return None


def panda_visual(slide, cx, cy, r, ec=RGBColor(0, 0, 0), fc=WHITE, ring=None, asset_index=0):
    """有授权素材就贴真实花花圆形头像, 否则画简笔熊猫。cx,cy,r 单位为 EMU。"""
    src = _ASSET_SRCS[asset_index % len(_ASSET_SRCS)] if _ASSET_SRCS else None
    png = _circle_png(src) if src else None
    if png:
        if ring is not None:
            rr = int(r * 1.06)
            rect(slide, int(cx - rr), int(cy - rr), 2 * rr, 2 * rr, ring, shape=MSO_SHAPE.OVAL)
        slide.shapes.add_picture(png, Emu(int(cx - r)), Emu(int(cy - r)), Emu(int(2 * r)), Emu(int(2 * r)))
    else:
        panda_face(slide, cx, cy, r, ec=ec, fc=fc)


def asset_path(*parts):
    return os.path.join(ASSET_DIR, *parts)


def crop_image(src, aspect=1.0, size=(900, 900), suffix="crop"):
    if not _PIL_OK or not src or not os.path.exists(src):
        return src if src and os.path.exists(src) else None
    key = (os.path.abspath(src), aspect, size, suffix)
    out = os.path.join(_TMP_DIR, f"{os.path.splitext(os.path.basename(src))[0]}_{suffix}_{size[0]}x{size[1]}.png")
    if os.path.exists(out):
        return out
    try:
        os.makedirs(_TMP_DIR, exist_ok=True)
        im = Image.open(src).convert("RGBA")
        w, h = im.size
        current = w / h
        if current > aspect:
            nw = int(h * aspect)
            left = (w - nw) // 2
            im = im.crop((left, 0, left + nw, h))
        else:
            nh = int(w / aspect)
            top = (h - nh) // 2
            im = im.crop((0, top, w, top + nh))
        im = im.resize(size, Image.LANCZOS)
        im.save(out)
        return out
    except Exception as e:
        print("  [warn] 图片裁切失败:", src, e)
        return src


def add_photo(slide, src, x, y, w, h, fit="cover"):
    if not src or not os.path.exists(src):
        rect(slide, x, y, w, h, LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        return None
    if fit == "cover":
        src = crop_image(src, aspect=float(w) / float(h), size=(1000, max(1, int(1000 * float(h) / float(w)))), suffix="cover")
    return slide.shapes.add_picture(src, x, y, w, h)


COMPETITOR_ASSETS = {
    "Loona": asset_path("competitors", "loona.jpg"),
    "Vector": asset_path("competitors", "vector.jpg"),
    "Eilik": asset_path("competitors", "eilik.jpg"),
    "Ropet": asset_path("competitors", "ropet_1.png"),
    "Moflin": asset_path("competitors", "moflin.jpg"),
    "BubblePal": asset_path("competitors", "bubblepal.jpg"),
}

CONCEPT_DESKTOP = asset_path("concepts", "huahua_desktop_eye_module.png")
CONCEPT_LINEUP = asset_path("concepts", "huahua_size_lineup.png")


def chip(slide, x, y, w, text, color=BAMBOO, tcolor=WHITE, h=Inches(0.42), size=12):
    sp = rect(slide, x, y, w, h, color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    try:
        sp.adjustments[0] = 0.5
    except Exception:
        pass
    tf = sp.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = tcolor; r.font.name = FONT
    _ea(r)
    return sp


# =================================================================
# Slide 1 — 封面
# =================================================================
s = add_slide()
bg(s, INK)
# 背景大色块
rect(s, 0, 0, SW, Inches(0.18), BAMBOO)
rect(s, 0, SH - Inches(0.18), SW, Inches(0.18), BAMBOO)
# 右侧熊猫脸
panda_visual(s, int(Inches(10.4)), int(Inches(3.55)), int(Inches(1.9)), ec=RGBColor(0,0,0), fc=WHITE, ring=RGBColor(0x9C,0xD6,0x6B), asset_index=0)
# 标语
txt(s, Inches(0.9), Inches(1.35), Inches(8.5), Inches(0.5),
    "AI 互动陪伴机器人 · 投资人汇报", 16, RGBColor(0x9C, 0xD6, 0x6B), bold=True)
txt(s, Inches(0.88), Inches(2.0), Inches(8.8), Inches(2.2),
    "熊猫花花", 72, WHITE, bold=True)
txt(s, Inches(0.9), Inches(3.35), Inches(8.8), Inches(1.0),
    "全球第一只 1:1 拟真、会眨眼、会动手脚、会对话、会成长的桌面陪伴熊猫", 21, RGBColor(0xED,0xEF,0xE8), bold=True, line_spacing=1.1)
# 四个关键词 chip
chip(s, Inches(0.9), Inches(4.6), Inches(2.0), "1:1拟真外形", PINK, WHITE, size=14)
chip(s, Inches(3.05), Inches(4.6), Inches(2.0), "仿生眼神", BAMBOO, WHITE, size=14)
chip(s, Inches(5.2), Inches(4.6), Inches(2.0), "可动手脚", GOLD, INK, size=14)
chip(s, Inches(7.35), Inches(4.6), Inches(2.0), "对话·养成", RGBColor(0x5B,0x8D,0xEF), WHITE, size=14)
txt(s, Inches(0.9), Inches(6.45), Inches(9), Inches(0.5),
    "基于现象级熊猫 IP「花花」 ｜ 2026 ｜ 商业计划摘要", 13, RGBColor(0xB9,0xBE,0xB2))

# =================================================================
# Slide 2 — 痛点 / 不可能三角
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "WHY NOW · 行业痛点", "陪伴机器人的「不可能三角」", 2)
txt(s, Inches(0.78), Inches(1.55), Inches(11.7), Inches(0.6),
    "市场上的产品几乎只能做到三点中的一到两点，没有人同时做全。", 16, GRAY)
# 三角三个圆
cy = int(Inches(4.4))
positions = [
    (int(Inches(3.2)), int(Inches(3.2)), "生动的物理动作", "会动的机械结构\n(眼/头/四肢/行走)", PINK),
    (int(Inches(10.1)), int(Inches(3.2)), "自然的智能对话", "大模型理解与表达", GOLD),
    (int(Inches(6.65)), int(Inches(5.6)), "有温度的情感陪伴", "IP / 养成 / 性格", BAMBOO),
]
for (cx, ccy, t, d, c) in positions:
    rr = int(Inches(1.35))
    rect(s, cx-rr, ccy-rr, 2*rr, 2*rr, c, shape=MSO_SHAPE.OVAL)
    txt(s, Emu(cx-rr), Emu(ccy-int(Inches(0.55))), Emu(2*rr), Inches(0.6), t, 16, WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Emu(cx-rr), Emu(ccy+int(Inches(0.05))), Emu(2*rr), Inches(0.8), d, 11, WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP, line_spacing=1.0)
# 中心
txt(s, Inches(5.4), Inches(4.0), Inches(2.5), Inches(0.6), "三者兼得 =\n稀缺空白", 15, INK, bold=True, align=PP_ALIGN.CENTER)
# 右侧说明卡
rect(s, Inches(0.78), Inches(6.2), Inches(11.7), Inches(0.85), LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.0), Inches(6.32), Inches(11.3), Inches(0.6),
    "Loona 偏机器狗(无IP/屏幕画眼) · Moflin/Ropet 软萌但几乎不能动 · BubblePal 只是会说话的插件 —— 花花要一次补齐三角。",
    13.5, INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)

# =================================================================
# Slide 3 — 市场机会
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "MARKET · 市场机会", "毛绒玩具的 AI 升级窗口已经打开", 3)
# 三个数据卡
cards = [
    ("$138.9 亿", "2025 全球毛绒玩具市场规模", BAMBOO),
    ("$285 亿", "2034 预计市场规模", GOLD),
    ("14–16%", "AI 玩具子赛道年复合增速 (CAGR)", PINK),
]
cx = Inches(0.78)
for (num, desc, c) in cards:
    w = Inches(3.78)
    rect(s, cx, Inches(1.75), w, Inches(2.0), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, cx, Inches(1.75), Inches(0.16), Inches(2.0), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, cx+Inches(0.35), Inches(2.0), w-Inches(0.5), Inches(0.9), num, 38, c, bold=True)
    txt(s, cx+Inches(0.35), Inches(2.95), w-Inches(0.5), Inches(0.7), desc, 14, GRAY, line_spacing=1.05)
    cx += Inches(4.0)
# 趋势
txt(s, Inches(0.78), Inches(4.15), Inches(11.7), Inches(0.4), "驱动趋势", 18, INK, bold=True)
bullet(s, Inches(0.9), Inches(4.65), Inches(11.5), Inches(2.3), [
    "从功能玩具到情感伙伴||：用户付费意愿从「好玩」转向「陪伴 / 疗愈 / 养成」，复购与黏性更高",
    "大模型平价化||：DeepSeek / 豆包 / GPT-4o 让自然对话成本骤降，AI 玩具迎来爆发窗口",
    "端侧 AI 成熟||：RK3588(6 TOPS NPU) 等让本地推理、隐私保护、低延迟成为可能",
    "IP 驱动溢价||：泡泡玛特验证「IP+情感」强变现力，花花是稀缺的现象级真实熊猫 IP",
], size=15, gap=1.3)
txt(s, Inches(0.78), Inches(7.0), Inches(11), Inches(0.3),
    "数据来源：第三方行业报告(accio / keyirobot 等)，已按合规改写，正式 BP 需交叉核验权威机构口径。", 9, GRAY)

# =================================================================
# Slide 4 — 竞品实物图对比
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "COMPETITION · 实物对比", "竞品各自只解决了局部体验, 形态短板非常直观", 4)
cards = [
    ("Loona", "机器狗 / 硬壳", "强动作\n弱毛绒陪伴", BAMBOO),
    ("Vector", "履带机器人", "强桌面感\n弱情感载体", RGBColor(0x5B,0x8D,0xEF)),
    ("Eilik", "表情桌面机器人", "强表演\n弱真实生命感", GOLD),
    ("Ropet", "毛绒 AI 宠物", "强柔软\n弱肢体动作", PINK),
    ("Moflin", "毛绒情感宠物", "强养成\n弱对话/动作", RGBColor(0x9B,0x59,0xB6)),
    ("BubblePal", "语音挂件", "强低价\n无机体生命感", GRAY),
]
for i, (name, form, gap, color) in enumerate(cards):
    x = Inches(0.62) + (i % 3) * Inches(4.13)
    y = Inches(1.6) + (i // 3) * Inches(2.28)
    rect(s, x, y, Inches(3.85), Inches(2.05), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    add_photo(s, COMPETITOR_ASSETS.get(name), x+Inches(0.12), y+Inches(0.12), Inches(1.45), Inches(1.25))
    txt(s, x+Inches(1.75), y+Inches(0.16), Inches(1.9), Inches(0.35), name, 16, color, bold=True)
    txt(s, x+Inches(1.75), y+Inches(0.55), Inches(1.9), Inches(0.35), form, 11, GRAY, bold=True)
    txt(s, x+Inches(1.75), y+Inches(0.98), Inches(1.9), Inches(0.8), gap, 13, INK, bold=True, line_spacing=1.05)
    rect(s, x, y+Inches(1.92), Inches(3.85), Inches(0.13), color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)

rows = [
    ("眼睛方案", "屏幕/表情屏为主", "真实眼球 + 眼皮微机构"),
    ("肢体动作", "轮式/履带/局部动作, 或几乎不动", "桌面坐姿 + 前肢/头部/眼神动作库"),
    ("情感载体", "硬壳机器人或无 IP 毛绒", "真实熊猫花花形象 + 毛绒可抱"),
    ("主攻尺寸", "掌上/桌面玩具, 结构空间受限", "桌面级 28-35cm, 留足眼部机构空间"),
]
ty = Inches(5.95)
for i, (dim, market, huahua) in enumerate(rows):
    x = Inches(0.78) + i * Inches(3.0)
    rect(s, x, ty, Inches(2.78), Inches(0.68), LIGHT if i % 2 else WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x+Inches(0.12), ty+Inches(0.08), Inches(2.5), Inches(0.18), dim, 9.5, GRAY, bold=True)
    txt(s, x+Inches(0.12), ty+Inches(0.28), Inches(1.14), Inches(0.32), market, 8.5, RGBColor(0xB0,0x3A,0x3A), line_spacing=0.9)
    txt(s, x+Inches(1.32), ty+Inches(0.26), Inches(1.32), Inches(0.34), huahua, 8.5, BAMBOO_D, bold=True, line_spacing=0.9)
txt(s, Inches(0.78), Inches(6.77), Inches(11.7), Inches(0.3),
    "结论：花花不是再做一个桌面机器人, 而是把「真实熊猫外观 + 机械眼神 + 毛绒陪伴 + AI成长」合成到一个可量产规格里。", 11, INK, bold=True)

# =================================================================
# Slide 5 — 竞品优缺点深度
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "COMPETITION · 优缺点剖析", "四类代表竞品的优势与短板", 5)
comp = [
    ("Loona  最强动作派", "Loona", BAMBOO,
     "优: 5 TOPS BPU+4舵机, 动作流畅, ToF避障, GPT-4o, 700+表情",
     "缺: 塑料机器狗形态, 无柔软可抱感, 眼睛是屏幕, 无IP, 价高"),
    ("Ropet  最强毛绒养成派", "Ropet", GOLD,
     "优: 软萌可抱, 视觉情感识别, 养成系统, 已售约2万台并完成A轮",
     "缺: 几乎不能动(无四肢/行走), 眼睛仍是屏幕, 续航一般, 无IP"),
    ("Moflin/Casio  最强情感派", "Moflin", PINK,
     "优: 情感AI与性格成长顶级, 宣称400万种情感画像, 品牌背书强",
     "缺: 无四肢/不能动/不说话, 交互偏单向, 价格高"),
    ("BubblePal  最轻插件派", "BubblePal", RGBColor(0x5B,0x8D,0xEF),
     "优: 成本极低, 即插即用, 可绑任意玩偶让其开口说话",
     "缺: 没有任何机械动作与生命感, 本质是语音模块"),
]
gx, gy = Inches(0.78), Inches(1.7)
cw, ch = Inches(5.78), Inches(2.5)
for i, (title, asset_key, c, pro, con) in enumerate(comp):
    x = gx + (i % 2) * Inches(6.0)
    y = gy + (i // 2) * Inches(2.65)
    rect(s, x, y, cw, ch, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x, y, cw, Inches(0.62), c, shape=MSO_SHAPE.ROUND_2_SAME_RECTANGLE)
    txt(s, x+Inches(0.25), y+Inches(0.06), cw-Inches(0.4), Inches(0.5), title, 16, WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    add_photo(s, COMPETITOR_ASSETS.get(asset_key), x+Inches(0.28), y+Inches(0.82), Inches(1.35), Inches(1.24))
    txt(s, x+Inches(1.82), y+Inches(0.82), cw-Inches(2.05), Inches(0.72), pro, 12, BAMBOO_D, bold=True, line_spacing=1.02)
    txt(s, x+Inches(1.82), y+Inches(1.58), cw-Inches(2.05), Inches(0.72), con, 12, RGBColor(0xB0,0x3A,0x3A), bold=True, line_spacing=1.02)

# =================================================================
# Slide 6 — 产品定位 / 花花是谁
# =================================================================
s = add_slide()
bg(s, INK)
rect(s, 0, 0, Inches(0.16), SH, BAMBOO)
txt(s, Inches(0.7), Inches(0.55), Inches(8), Inches(0.4), "PRODUCT · 产品定位", 13, RGBColor(0x9C,0xD6,0x6B), bold=True)
txt(s, Inches(0.68), Inches(0.95), Inches(11.5), Inches(0.8), "主攻桌面级：小到能陪伴, 大到能塞进机械仿生眼", 26, WHITE, bold=True)
add_photo(s, CONCEPT_DESKTOP, Inches(6.8), Inches(1.65), Inches(5.85), Inches(3.3))
bullet(s, Inches(0.8), Inches(1.95), Inches(5.65), Inches(1.85), [
    "目标规格||：桌面旗舰约 28-35cm, 坐姿稳定, 头部空间足够容纳双眼微型舵机模块",
    "核心体验||：真实毛绒触感 + 机械眼球/眼皮 + 头部/前肢动作, 先做“坐着也有生命感”的花花",
    "研发取舍||：行走是二期加分项, 不能牺牲拟真外形与眼神机构",
], size=13.5, color=RGBColor(0xEC,0xEF,0xE8), gap=1.12, mark_color=RGBColor(0x9C,0xD6,0x6B))
txt(s, Inches(0.8), Inches(4.05), Inches(5.8), Inches(0.35), "尺寸策略", 16, RGBColor(0x9C,0xD6,0x6B), bold=True)
add_photo(s, CONCEPT_LINEUP, Inches(0.8), Inches(4.45), Inches(5.85), Inches(1.82))
size_notes = [
    ("Mini 18cm", "低价可爱款\n眼部机构空间紧张", RGBColor(0xC9,0xCE,0xC2)),
    ("Desktop 28-35cm", "主攻旗舰\n能放下机械眼睛", GOLD),
    ("Collector 70cm", "展示/联名款\n成本与物流更重", PINK),
]
for i, (label, note, c) in enumerate(size_notes):
    x = Inches(6.95) + i * Inches(1.78)
    rect(s, x, Inches(5.25), Inches(1.55), Inches(1.0), RGBColor(0x24,0x2C,0x22), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x, Inches(5.25), Inches(1.55), Inches(0.1), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x+Inches(0.12), Inches(5.38), Inches(1.3), Inches(0.25), label, 10.5, c, bold=True)
    txt(s, x+Inches(0.12), Inches(5.72), Inches(1.3), Inches(0.45), note, 9.2, RGBColor(0xD7,0xDB,0xD2), line_spacing=0.9)
txt(s, Inches(6.95), Inches(4.48), Inches(5.3), Inches(0.52),
    "桌面级不是妥协，而是机械眼、毛绒外观、可抱体积和量产成本之间的最佳交点。", 15, WHITE, bold=True, line_spacing=1.05)

# =================================================================
# Slide 7 — 技术系统1: 仿生眼
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "TECH 1/4 · 仿生眼睛系统", "会转动、会眨眼的机械仿生眼 (第一差异化)", 7)
txt(s, Inches(0.78), Inches(1.55), Inches(11.7), Inches(0.5),
    "采用机械仿生眼而非屏幕画眼 —— 这是与几乎所有竞品拉开「真实生命感」差距的关键。", 15, GRAY)
# 左: 机构说明
rect(s, Inches(0.78), Inches(2.25), Inches(6.0), Inches(4.3), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.05), Inches(2.45), Inches(5.5), Inches(0.5), "机构与驱动方案", 17, BAMBOO_D, bold=True)
bullet(s, Inches(1.05), Inches(3.05), Inches(5.5), Inches(3.4), [
    "每只眼 3 个微型舵机||：2 轴控制眼球 X/Y 转动 + 1 轴控制眼皮开合",
    "双眼共 6 舵机||：可实现注视、眨眼、眯眼、惊讶睁大、困倦半睁",
    "万向节 + 推杆联动||，3D 打印紧凑机构,可塞进熊猫头部狭小空间",
    "MCU(ESP32/STM32) 输出 PWM||，每眼≥3 路, 静音舵机降噪",
    "前置摄像头检测人脸/视线||→ 眼球自动看向人, 实现对视与眼神跟随",
], size=13, gap=1.2)
# 右: 眼睛情绪示意
rect(s, Inches(7.0), Inches(2.25), Inches(5.55), Inches(4.3), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(7.0), Inches(2.42), Inches(5.55), Inches(0.4), "情绪化眼神映射", 15, WHITE, bold=True, align=PP_ALIGN.CENTER)
# 画几对眼睛 + 标签
def eye_pair(cx, cy, lid_top_ratio, label):
    er = int(Inches(0.42))
    for dx in (-int(Inches(0.55)), int(Inches(0.55))):
        rect(s, cx+dx-er, cy-er, 2*er, 2*er, WHITE, shape=MSO_SHAPE.OVAL)
        pr = int(er*0.55)
        rect(s, cx+dx-pr, cy-pr, 2*pr, 2*pr, INK, shape=MSO_SHAPE.OVAL)
        # 眼皮(绿色矩形从上压下)
        lid_h = int(2*er*lid_top_ratio)
        if lid_h > 0:
            rect(s, cx+dx-er, cy-er, 2*er, lid_h, BAMBOO)
    txt(s, Emu(cx-int(Inches(1.0))), Emu(cy+int(Inches(0.5))), Inches(2.0), Inches(0.35), label, 11.5, RGBColor(0xCF,0xE8,0xB8), align=PP_ALIGN.CENTER, bold=True)

eye_pair(int(Inches(8.1)), int(Inches(3.45)), 0.0, "睁眼·专注")
eye_pair(int(Inches(11.3)), int(Inches(3.45)), 0.5, "半睁·困倦")
eye_pair(int(Inches(8.1)), int(Inches(5.15)), 0.85, "眨眼·闭合")
eye_pair(int(Inches(11.3)), int(Inches(5.15)), 0.0, "睁大·惊喜")
txt(s, Inches(7.0), Inches(6.0), Inches(5.55), Inches(0.45),
    "情感引擎输出情绪标签 → 映射为眼球+眼皮动作曲线", 11, RGBColor(0xB9,0xC8,0xAD), align=PP_ALIGN.CENTER)

# =================================================================
# Slide 8 — 内部结构爆炸示意图 (机构全部藏在毛绒下)
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "TECH 1/4 · 内部结构", "内部结构爆炸示意图：机构全部藏在毛绒下", 8)
txt(s, Inches(0.78), Inches(1.5), Inches(11.7), Inches(0.5),
    "由外到内 4 层：舵机 / 电子 / 线缆全部封装在毛绒蒙皮内，任何角度都看不到机械结构。", 14, GRAY)
# 四层卡片(由外到内)
layers = [
    ("① 拟真毛绒外皮", "看到的就是真熊猫\n可拆洗·背部隐藏拉链", PINK),
    ("② 弹性海绵/记忆棉", "柔软可抱手感\n包裹并隐藏机构", GOLD),
    ("③ 内骨骼 + 关节舵机", "头2·前肢4·腰1\n承力支架+仿生眼6舵机", BAMBOO),
    ("④ 电子核心", "ESP32(小智)·舵机驱动板\n电池·麦克风/扬声器", RGBColor(0x5B,0x8D,0xEF)),
]
lx = Inches(0.78); lw = Inches(2.72); lgap = Inches(0.18)
for i, (t, d, c) in enumerate(layers):
    x = lx + i*(lw+lgap)
    rect(s, x, Inches(2.1), lw, Inches(1.92), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x, Inches(2.1), lw, Inches(0.52), c, shape=MSO_SHAPE.ROUND_2_SAME_RECTANGLE)
    txt(s, x+Inches(0.1), Inches(2.13), lw-Inches(0.2), Inches(0.46), t, 12.5, WHITE if c != GOLD else INK, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, x+Inches(0.18), Inches(2.78), lw-Inches(0.34), Inches(1.15), d, 11.5, INK, line_spacing=1.15)
    if i < 3:
        txt(s, x+lw-Inches(0.02), Inches(2.1), Inches(0.22), Inches(1.92), "›", 20, GRAY, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
# 结果 banner
rect(s, Inches(0.78), Inches(4.16), Inches(11.77), Inches(0.5), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(0.78), Inches(4.16), Inches(11.77), Inches(0.5),
    "＝ 外观零机械裸露的真熊猫，却会眨眼 · 说话 · 招手", 13.5, RGBColor(0x9C,0xD6,0x6B), bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
# 仿生眼模组爆炸细节(底部深色面板)
py = Inches(4.82)
rect(s, Inches(0.78), py, Inches(11.77), Inches(2.08), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.0), py+Inches(0.1), Inches(11.4), Inches(0.4), "仿生眼模组（爆炸视图）· 双眼共 6 舵机 · 整体藏于熊猫头部", 14, WHITE, bold=True)
cyc = int(py) + int(Inches(1.05))   # 零件图标中心 y
lbly = int(py) + int(Inches(1.55))  # 标签 y
SERVO = RGBColor(0xE8, 0xA8, 0x2B)
def part_label(cx, text):
    txt(s, Emu(cx-int(Inches(1.05))), Emu(lbly), Inches(2.1), Inches(0.4), text, 10.5, RGBColor(0xD8,0xDC,0xD2), align=PP_ALIGN.CENTER)
def mini_servo(cx, cy, w=0.46, h=0.34):
    rect(s, Emu(cx-int(Inches(w/2))), Emu(cy-int(Inches(h/2))), Inches(w), Inches(h), SERVO, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
def plus(cx):
    txt(s, Emu(cx-int(Inches(0.2))), Emu(cyc-int(Inches(0.25))), Inches(0.4), Inches(0.5), "+", 20, RGBColor(0x7E,0x86,0x78), bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
# 1) 3D打印支架
x1 = int(Inches(2.05))
rect(s, Emu(x1-int(Inches(0.55))), Emu(cyc-int(Inches(0.5))), Inches(1.1), Inches(1.0), RGBColor(0x2C,0x33,0x2A), line=RGBColor(0x9C,0xD6,0x6B), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
part_label(x1, "3D打印支架")
plus(int(Inches(3.25)))
# 2) X/Y 双轴舵机
x2 = int(Inches(4.4))
mini_servo(x2, cyc-int(Inches(0.28)))
mini_servo(x2, cyc+int(Inches(0.22)))
part_label(x2, "X/Y 双轴舵机")
plus(int(Inches(5.55)))
# 3) 推杆连杆
x3 = int(Inches(6.55))
rect(s, Emu(x3-int(Inches(0.45))), Emu(cyc-int(Inches(0.05))), Inches(0.9), Inches(0.12), RGBColor(0xC9,0xCE,0xC2), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
rect(s, Emu(x3-int(Inches(0.05))), Emu(cyc-int(Inches(0.3))), Inches(0.12), Inches(0.62), RGBColor(0xC9,0xCE,0xC2), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
part_label(x3, "推杆/连杆")
plus(int(Inches(7.7)))
# 4) 眼球(可转)
x4 = int(Inches(8.85))
er = int(Inches(0.5))
rect(s, Emu(x4-er), Emu(cyc-er), Inches(1.0), Inches(1.0), WHITE, shape=MSO_SHAPE.OVAL)
ir = int(Inches(0.22))
rect(s, Emu(x4-ir), Emu(cyc-ir), Inches(0.44), Inches(0.44), INK, shape=MSO_SHAPE.OVAL)
hr = int(Inches(0.07))
rect(s, Emu(x4-int(Inches(0.12))), Emu(cyc-int(Inches(0.14))), Inches(0.14), Inches(0.14), WHITE, shape=MSO_SHAPE.OVAL)
part_label(x4, "眼球(可转)")
plus(int(Inches(10.0)))
# 5) 眼皮 + 眼皮舵机
x5 = int(Inches(11.15))
rect(s, Emu(x5-int(Inches(0.5))), Emu(cyc-int(Inches(0.5))), Inches(1.0), Inches(0.5), BAMBOO, shape=MSO_SHAPE.ROUND_2_SAME_RECTANGLE)
mini_servo(x5, cyc+int(Inches(0.28)))
part_label(x5, "眼皮(可眨)+舵机")

# =================================================================
# Slide 9 — 技术系统2: 头部四肢运动
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "TECH 2/4 · 运动系统", "可动头部与四肢：12–16 自由度", 9)
# DoF 表
data = [
    ("眼睛", "6", "转动 / 眨眼 / 眯眼", PINK),
    ("头部", "2", "点头 / 摇头 / 侧头", BAMBOO),
    ("嘴部", "1", "开合 / 说话同步(可选)", GOLD),
    ("前肢", "4", "挥手 / 招手 / 作揖", RGBColor(0x5B,0x8D,0xEF)),
    ("腰·身体", "1-2", "坐起 / 趴下 / 扭身", RGBColor(0x9B,0x59,0xB6)),
    ("耳朵·后肢", "2+", "耳朵抖动 / 后肢(选配)", BAMBOO_D),
]
gy = Inches(1.8)
for i, (part, dof, act, c) in enumerate(data):
    y = gy + i*Inches(0.74)
    rect(s, Inches(0.78), y, Inches(6.2), Inches(0.62), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, Inches(0.78), y, Inches(0.14), Inches(0.62), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, Inches(1.05), y, Inches(1.6), Inches(0.62), part, 14, INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(2.7), y, Inches(0.9), Inches(0.62), dof+" DoF", 13, c, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(3.7), y, Inches(3.2), Inches(0.62), act, 12.5, GRAY, anchor=MSO_ANCHOR.MIDDLE)
# 右侧方案要点
rect(s, Inches(7.3), Inches(1.8), Inches(5.25), Inches(4.65), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(7.55), Inches(2.0), Inches(4.8), Inches(0.5), "工程方案", 17, WHITE, bold=True)
bullet(s, Inches(7.55), Inches(2.65), Inches(4.8), Inches(3.6), [
    "总线舵机(Feetech/STS)||+控制板,简化布线,可读回位置做闭环",
    "零机械裸露||：内骨骼+海绵+1:1拟真毛绒蒙皮,舵机/线缆/电池全藏于蒙皮内",
    "大脑-小脑分层||：主控下发动作序列, MCU 实时关节控制+安全限位",
    "技能动作库||：招手/作揖/点头/撒娇,由对话与情绪触发;行走为选配",
], size=12.5, color=RGBColor(0xEC,0xEF,0xE8), gap=1.2, mark_color=RGBColor(0x9C,0xD6,0x6B))

# =================================================================
# Slide 9 — 技术系统3: 大模型对话
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "TECH 3/4 · 对话大脑", "端云协同的大模型对话系统", 10)
# 语音链路
txt(s, Inches(0.78), Inches(1.6), Inches(11), Inches(0.4), "语音交互链路", 16, INK, bold=True)
chain = ["拾音\n双麦阵列", "唤醒/VAD\n本地", "ASR\n语音转文字", "LLM\n对话/人设", "TTS\n花花音色", "播放\n扬声器"]
chcolors = [GRAY, BAMBOO, GOLD, PINK, RGBColor(0x5B,0x8D,0xEF), GRAY]
cx = Inches(0.78)
for i, (t, c) in enumerate(zip(chain, chcolors)):
    w = Inches(1.72)
    rect(s, cx, Inches(2.1), w, Inches(0.95), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, cx, Inches(2.1), w, Inches(0.95), t, 12.5, WHITE if c != GOLD else INK, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)
    if i < len(chain)-1:
        txt(s, cx+w-Inches(0.06), Inches(2.1), Inches(0.4), Inches(0.95), "›", 22, INK, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    cx += Inches(1.94)
# 端云两卡
rect(s, Inches(0.78), Inches(3.5), Inches(5.78), Inches(3.0), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
rect(s, Inches(0.78), Inches(3.5), Inches(5.78), Inches(0.6), BAMBOO, shape=MSO_SHAPE.ROUND_2_SAME_RECTANGLE)
txt(s, Inches(1.0), Inches(3.56), Inches(5.4), Inches(0.5), "本地小模型 SLM (端)", 15, WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
bullet(s, Inches(1.05), Inches(4.25), Inches(5.3), Inches(2.1), [
    "唤醒、意图识别、敏感词安全围栏",
    "隐私敏感数据本地处理(回应行业痛点)",
    "断网离线兜底, 低延迟即时反应",
], size=13, gap=1.2)
rect(s, Inches(6.77), Inches(3.5), Inches(5.78), Inches(3.0), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
rect(s, Inches(6.77), Inches(3.5), Inches(5.78), Inches(0.6), GOLD, shape=MSO_SHAPE.ROUND_2_SAME_RECTANGLE)
txt(s, Inches(7.0), Inches(3.56), Inches(5.4), Inches(0.5), "云端大模型 (云)", 15, INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
bullet(s, Inches(7.05), Inches(4.25), Inches(5.3), Inches(2.1), [
    "DeepSeek / 豆包 / 通义 / GPT-4o",
    "复杂对话、知识问答、花花人设扮演",
    "长期记忆向量库 + RAG, 越聊越懂你",
], size=13, gap=1.2, mark_color=GOLD)

# =================================================================
# Slide 10 — 技术系统4: 行走 + 成长系统
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "TECH 4/4 · 肢体动作与养成", "肢体动作(纯舵机) + 成长系统 (留存核心)", 11)
# 肢体动作
rect(s, Inches(0.78), Inches(1.7), Inches(5.78), Inches(2.05), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.0), Inches(1.85), Inches(5.4), Inches(0.4), "肢体动作 (纯舵机·不用轮子)", 16, BAMBOO_D, bold=True)
bullet(s, Inches(1.05), Inches(2.35), Inches(5.3), Inches(1.3), [
    "原地动作(一期必做)||：招手/作揖/点头/坐起/趴下/扭身,零机械裸露",
    "行走(选配)||：仅腿足式,做不到就放弃,不影响核心体验",
], size=12.5, gap=1.15)
# 成长闭环
rect(s, Inches(6.77), Inches(1.7), Inches(5.78), Inches(2.05), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(7.0), Inches(1.85), Inches(5.4), Inches(0.4), "互动—奖励—成长 闭环", 16, RGBColor(0x9C,0xD6,0x6B), bold=True)
loop = ["互动\n说话/抚摸/打卡", "奖励\n经验/亲密度", "解锁\n动作/对话/表情", "性格\n专属花花"]
cx = Inches(7.0)
for i, t in enumerate(loop):
    w = Inches(1.28)
    rect(s, cx, Inches(2.4), w, Inches(0.95), RGBColor(0x2A,0x33,0x27), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, cx, Inches(2.4), w, Inches(0.95), t, 10.5, RGBColor(0xE7,0xEC,0xE0), bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=0.95)
    if i < 3:
        txt(s, cx+w-Inches(0.04), Inches(2.4), Inches(0.3), Inches(0.95), "→", 15, RGBColor(0x9C,0xD6,0x6B), bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    cx += Inches(1.4)
# 下方: 状态维度 + 自己的思维
txt(s, Inches(0.78), Inches(4.0), Inches(11), Inches(0.4), "养成系统设计", 16, INK, bold=True)
bullet(s, Inches(0.9), Inches(4.5), Inches(11.5), Inches(2.3), [
    "状态维度||：心情 / 活力 / 亲密度 / 技能等级 / 成长阶段(幼年→少年→成年)",
    "性格塑造||：长期互动数据驱动性格参数(外向/黏人…), 对标 Moflin 情感画像与 Ropet 养成(已被市场验证)",
    "「自己的思维」||：长期记忆 + 定期反思总结共同经历 → 主动发起对话(\u201c今天怎么没理我\u201d), 营造有想法的伙伴感",
    "App 配套||：成长曲线 / 性格雷达 / 回忆相册 / 任务打卡 / 固件 OTA",
], size=14, gap=1.3)

# =================================================================
# Slide 11 — 系统架构
# =================================================================
s = add_slide()
bg(s, DARKBG)
txt(s, Inches(0.7), Inches(0.5), Inches(8), Inches(0.4), "ARCHITECTURE · 系统架构", 13, RGBColor(0x9C,0xD6,0x6B), bold=True)
txt(s, Inches(0.68), Inches(0.9), Inches(11.5), Inches(0.6), "大脑—小脑—感知 分层架构", 26, WHITE, bold=True)
# 云
rect(s, Inches(1.2), Inches(1.85), Inches(10.9), Inches(0.95), RGBColor(0x2B,0x3A,0x55), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.4), Inches(1.95), Inches(10.5), Inches(0.8), "☁  云端 Cloud", 14, RGBColor(0x9FC2FF if False else 0x9F,0xC2,0xFF) if False else RGBColor(0x9F,0xC2,0xFF), bold=True)
txt(s, Inches(1.4), Inches(2.28), Inches(10.5), Inches(0.5), "大模型(DeepSeek/豆包/GPT-4o) · ASR/TTS · 长期记忆向量库 · OTA · 成长后台 · 内容安全审核 · 数据合规", 11.5, RGBColor(0xD7,0xE2,0xF7))
# 箭头
txt(s, Inches(6.4), Inches(2.82), Inches(1), Inches(0.4), "↕ Wi-Fi 加密", 11, RGBColor(0x9C,0xD6,0x6B), bold=True, align=PP_ALIGN.CENTER)
# 主控
rect(s, Inches(1.2), Inches(3.25), Inches(10.9), Inches(1.25), RGBColor(0x2F,0x4A,0x22), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.4), Inches(3.33), Inches(10.5), Inches(0.4), "🧠  主控大脑  RK3588 类 · 6 TOPS NPU", 14, RGBColor(0xBFE89A if False else 0xBF,0xE8,0x9A) if False else RGBColor(0xBF,0xE8,0x9A), bold=True)
txt(s, Inches(1.4), Inches(3.72), Inches(10.5), Inches(0.7), "本地小模型 SLM · 唤醒/VAD · 视觉(人脸/表情/手势) · 安全围栏 · 情感引擎 · 成长状态机 · 行为编排/技能库 · 端云路由", 11.5, RGBColor(0xDD,0xEA,0xCF), line_spacing=1.1)
# 下两块: MCU + 传感
rect(s, Inches(1.2), Inches(4.95), Inches(5.35), Inches(1.55), RGBColor(0x40,0x33,0x20), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.4), Inches(5.03), Inches(5), Inches(0.4), "⚙  运动 MCU  STM32/ESP32", 13.5, RGBColor(0xF2,0xC9,0x8A), bold=True)
txt(s, Inches(1.4), Inches(5.42), Inches(5), Inches(1.0), "眼球6舵机 · 头2 · 嘴1 · 前肢4 · 腰1-2 · 耳2 · (后肢选配) · 总线舵机闭环+安全限位", 11.5, RGBColor(0xEFD,0xCB if False else 0xEF,0xDC) if False else RGBColor(0xEF,0xDC,0xBC), line_spacing=1.1)
rect(s, Inches(6.75), Inches(4.95), Inches(5.35), Inches(1.55), RGBColor(0x3A,0x2E,0x44), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(6.95), Inches(5.03), Inches(5), Inches(0.4), "👁  传感层 Sensors", 13.5, RGBColor(0xCFA,0xEF if False else 0xCF,0xAE) if False else RGBColor(0xD8,0xC2,0xF0), bold=True)
txt(s, Inches(6.95), Inches(5.42), Inches(5), Inches(1.0), "RGB-D摄像头 · 双麦阵列 · 触摸 · IMU(被抱/跌落) · 光线/温度(可选)", 11.5, RGBColor(0xE4,0xD8,0xF2), line_spacing=1.1)
# 底部
txt(s, Inches(1.2), Inches(6.7), Inches(11), Inches(0.4), "全身无机械裸露：1:1拟真毛绒蒙皮(可抱) + 内骨骼(可动) + 锂电 + 无线充电底座", 12, RGBColor(0x9C,0xD6,0x6B), bold=True, align=PP_ALIGN.CENTER)

# =================================================================
# Slide 12 — BOM 成本
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "COST · 成本结构", "整机 BOM 成本估算与定价 (量产参考)", 13)
bom = [
    ("主控 SoC (RK3588S类)", "220–400"),
    ("运动 MCU + 舵机驱动", "25–50"),
    ("仿生眼模组(6舵机+机构)", "60–120"),
    ("头/前肢/腰/耳舵机", "110–210"),
    ("后肢步态舵机(选配)", "0–120"),
    ("摄像头(RGB/RGB-D)", "25–90"),
    ("音频(双麦+功放+扬声器)", "25–55"),
    ("传感器(触摸/IMU/光线)", "30–70"),
    ("电池/电源/无线充底座", "50–110"),
    ("结构(内骨骼+海绵+拟真毛绒)", "100–200"),
    ("PCB/线材/包装等", "40–80"),
]
gy = Inches(1.75)
for i, (name, cost) in enumerate(bom):
    col = i // 6
    row = i % 6
    x = Inches(0.78) + col*Inches(4.1)
    y = gy + row*Inches(0.56)
    rect(s, x, y, Inches(3.9), Inches(0.48), WHITE if row % 2 == 0 else LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x+Inches(0.2), y, Inches(2.7), Inches(0.48), name, 11.5, INK, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, x+Inches(2.85), y, Inches(1.0), Inches(0.48), "¥"+cost, 11.5, BAMBOO_D, bold=True, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
# 合计卡
rect(s, Inches(9.0), Inches(1.75), Inches(3.55), Inches(3.35), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(9.2), Inches(2.0), Inches(3.2), Inches(0.5), "整机料本合计", 15, RGBColor(0x9C,0xD6,0x6B), bold=True)
txt(s, Inches(9.2), Inches(2.55), Inches(3.2), Inches(0.8), "¥685–1505", 30, WHITE, bold=True)
txt(s, Inches(9.2), Inches(3.45), Inches(3.2), Inches(0.4), "建议零售价", 14, RGBColor(0xC9,0xCE,0xC2), bold=True)
txt(s, Inches(9.2), Inches(3.85), Inches(3.2), Inches(0.7), "¥1499–2499", 26, GOLD, bold=True)
txt(s, Inches(9.2), Inches(4.6), Inches(3.2), Inches(0.4), "目标毛利率 50%+", 13, RGBColor(0xC9,0xCE,0xC2))
# 降本
txt(s, Inches(0.78), Inches(5.4), Inches(11), Inches(0.4), "降本路径", 15, INK, bold=True)
bullet(s, Inches(0.9), Inches(5.85), Inches(11.5), Inches(1.2), [
    "眼模组舵机国产化 · 砍掉后肢/行走(外形不受影响) · 主控按需选4GB版 · 规模化集采议价",
], size=13)
txt(s, Inches(0.78), Inches(6.95), Inches(11), Inches(0.3), "注：千台级量产粗估区间, 最终以选型采购为准。", 9, GRAY)

# =================================================================
# Slide 13 — 安全合规
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "RISK · 安全与合规", "前置安全合规：把行业痛点变成加分项", 14)
risks = [
    ("隐私与数据", "部分AI玩具被曝持续录音、第三方转写、采集儿童数据",
     "本地SLM优先 · 物理静音键 · 录音指示灯 · 数据可一键删除/重置 · 遵循COPPA/儿童信息保护", BAMBOO),
    ("内容安全", "有报告显示部分AI玩具会生成不当内容",
     "本地敏感词+云端审核+年龄分级人设 · 儿童模式白名单 · 家长后台", GOLD),
    ("物理安全", "小零件/夹手/电池风险",
     "通过 3C/CE/EN71 玩具认证 · 舵机限位 · 过流保护", PINK),
    ("IP 合规", "IP授权范围需清晰",
     "明确花花IP授权(形象/名称/声音/区域/期限)可商用", RGBColor(0x5B,0x8D,0xEF)),
]
gy = Inches(1.75)
for i, (t, problem, fix, c) in enumerate(risks):
    y = gy + i*Inches(1.22)
    rect(s, Inches(0.78), y, Inches(11.77), Inches(1.08), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, Inches(0.78), y, Inches(0.16), Inches(1.08), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, Inches(1.1), y+Inches(0.12), Inches(2.1), Inches(0.85), t, 16, c if c != GOLD else RGBColor(0xB5,0x82,0x10), bold=True, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(3.3), y+Inches(0.14), Inches(4.0), Inches(0.85), "痛点：" + problem, 12, GRAY, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)
    txt(s, Inches(7.4), y+Inches(0.14), Inches(5.0), Inches(0.85), "对策：" + fix, 12, INK, bold=True, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)

# =================================================================
# Slide 14 — 路线图
# =================================================================
s = add_slide()
bg(s, INK)
txt(s, Inches(0.7), Inches(0.55), Inches(8), Inches(0.4), "ROADMAP · 研发路线图", 13, RGBColor(0x9C,0xD6,0x6B), bold=True)
txt(s, Inches(0.68), Inches(0.95), Inches(11.5), Inches(0.6), "15 个月：从概念验证到量产上市", 26, WHITE, bold=True)
phases = [
    ("P0", "0–2 月", "概念验证", "仿生眼Demo+端云对话+花花外观手板", PINK),
    ("P1", "2–5 月", "工程样机", "拟真整机(全毛绒/零裸露)+肢体动作库+成长App v0.1", GOLD),
    ("P2", "5–9 月", "设计验证", "静音眼模组+续航达标+安全合规预测试", BAMBOO),
    ("P3", "9–12 月", "量产验证", "产线导入+良率爬坡+认证(3C/CE/EN71)", RGBColor(0x5B,0x8D,0xEF)),
    ("P4", "12–15 月", "量产上市", "首批量产+众筹预售+IP联合营销", RGBColor(0x9B,0x59,0xB6)),
]
# 时间轴线
rect(s, Inches(1.0), Inches(2.55), Inches(11.3), Inches(0.06), BAMBOO)
cx = Inches(1.0)
step = Inches(2.32)
for i, (p, t, name, deliver, c) in enumerate(phases):
    x = cx + i*step
    # 节点
    rect(s, x, Inches(2.35), Inches(0.46), Inches(0.46), c, shape=MSO_SHAPE.OVAL)
    txt(s, x, Inches(2.35), Inches(0.46), Inches(0.46), p, 13, WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 卡片
    cardy = Inches(3.2)
    rect(s, x-Inches(0.2), cardy, Inches(2.05), Inches(2.6), RGBColor(0x24,0x2C,0x22), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, x-Inches(0.2), cardy, Inches(2.05), Inches(0.1), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, x-Inches(0.05), cardy+Inches(0.2), Inches(1.8), Inches(0.4), t, 13, c, bold=True)
    txt(s, x-Inches(0.05), cardy+Inches(0.62), Inches(1.8), Inches(0.5), name, 15, WHITE, bold=True)
    txt(s, x-Inches(0.05), cardy+Inches(1.18), Inches(1.8), Inches(1.3), deliver, 11, RGBColor(0xD3,0xD8,0xCD), line_spacing=1.1)

# =================================================================
# Slide 15 — 商业化与融资
# =================================================================
s = add_slide()
bg(s, PAPER)
page_header(s, "BUSINESS · 商业化", "收入模型、GTM 与融资规划", 16)
# 收入模型
txt(s, Inches(0.78), Inches(1.6), Inches(6), Inches(0.4), "收入模型", 17, INK, bold=True)
rev = [
    ("硬件销售", "首发+多IP形象/限定款", BAMBOO),
    ("会员订阅", "高级对话/专属音色/云记忆扩容", GOLD),
    ("配件养成内购", "服饰/家具/技能包/节日皮肤", PINK),
    ("IP联名内容", "花花直播/周边/品牌联名", RGBColor(0x5B,0x8D,0xEF)),
]
gy = Inches(2.1)
for i, (t, d, c) in enumerate(rev):
    y = gy + i*Inches(0.92)
    rect(s, Inches(0.78), y, Inches(5.7), Inches(0.78), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, Inches(0.78), y, Inches(0.14), Inches(0.78), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, Inches(1.05), y, Inches(2.0), Inches(0.78), t, 14, INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(2.95), y, Inches(3.4), Inches(0.78), d, 11.5, GRAY, anchor=MSO_ANCHOR.MIDDLE)
# 融资用途 (右)
txt(s, Inches(6.9), Inches(1.6), Inches(6), Inches(0.4), "融资用途建议", 17, INK, bold=True)
fund = [("研发与打样", 45, BAMBOO), ("IP授权与营销", 25, GOLD), ("供应链与认证", 20, PINK), ("团队", 10, RGBColor(0x5B,0x8D,0xEF))]
gy = Inches(2.1)
for i, (t, pct, c) in enumerate(fund):
    y = gy + i*Inches(0.92)
    rect(s, Inches(6.9), y, Inches(5.65), Inches(0.78), LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    barw = Inches(0.0001 + 5.65*pct/100.0)
    rect(s, Inches(6.9), y, barw, Inches(0.78), c, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, Inches(7.15), y, Inches(3.5), Inches(0.78), t, 14, WHITE if pct >= 25 else INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(11.4), y, Inches(1.0), Inches(0.78), f"{pct}%", 16, INK, bold=True, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
# GTM + 锚点
rect(s, Inches(0.78), Inches(5.85), Inches(11.77), Inches(1.15), INK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, Inches(1.0), Inches(5.98), Inches(11.3), Inches(0.4), "GTM：众筹预售造势 → 萌宠/疗愈赛道 KOL 种草 → 花花 IP 流量导入 → 线下快闪/收藏展", 13, WHITE, bold=True)
txt(s, Inches(1.0), Inches(6.45), Inches(11.3), Inches(0.45), "估值锚点：竞品 Ropet 售出约 2 万台后完成超 1000 万美元 A 轮, 验证赛道资本热度。", 12, RGBColor(0xC9,0xCE,0xC2))

# =================================================================
# Slide 16 — 结尾愿景
# =================================================================
s = add_slide()
bg(s, INK)
rect(s, 0, 0, SW, Inches(0.18), BAMBOO)
rect(s, 0, SH-Inches(0.18), SW, Inches(0.18), BAMBOO)
panda_visual(s, int(Inches(6.66)), int(Inches(2.7)), int(Inches(1.25)), ec=RGBColor(0,0,0), fc=WHITE, ring=RGBColor(0x33,0x3D,0x30), asset_index=0)
txt(s, Inches(1.0), Inches(4.15), Inches(11.3), Inches(0.9), "让每个人都拥有一只\n会眨眼、会陪伴、会长大的熊猫花花", 30, WHITE, bold=True, align=PP_ALIGN.CENTER, line_spacing=1.1)
txt(s, Inches(1.0), Inches(5.55), Inches(11.3), Inches(0.5), "1:1 拟真外形 × 真实生命感 × 智能大脑 × 现象级 IP", 17, RGBColor(0x9C,0xD6,0x6B), bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(1.0), Inches(6.4), Inches(11.3), Inches(0.4), "诚邀您与我们一起，定义下一代情感陪伴机器人。", 14, RGBColor(0xC9,0xCE,0xC2), align=PP_ALIGN.CENTER)

# ---------------- 保存 ----------------
out = "熊猫花花投资汇报.pptx"
prs.save(out)
if _ASSET_SRCS:
    print("OK 已生成:", out, "共", len(prs.slides._sldIdLst), "页 | 使用花花素材:", ", ".join(os.path.basename(p) for p in _ASSET_SRCS))
else:
    print("OK 已生成:", out, "共", len(prs.slides._sldIdLst), "页 | 未发现 assets/ 花花素材, 使用内置简笔熊猫")
    print("   提示: 把授权花花图片放入", ASSET_DIR, "后重跑即可替换为真实素材")

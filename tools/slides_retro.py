"""The retro deck style: a late-1990s conference look (4:3, deep blue gradient with an embossed watermark,
yellow Arial Bold titles, white Arial Bold text, Wingdings bullets).

All artwork is generated here (no images from any other presentation): the backgrounds are drawn with Pillow
into build/slides-bg/ and embedded in each deck. Used by tools/build_slides.py (the default style).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

import build_slides as base
from citations import REPOS, ROOT, find_citations

W, H = 10.0, 7.5
MX = 0.42                      # left/right margin
BOTTOM = H - 0.75              # content must end above the footer
TITLE_SIZE = 32
YELLOW = RGBColor(0xF2, 0xD6, 0x06)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ICE = RGBColor(0xB9, 0xDB, 0xFD)
NAVY = RGBColor(0x06, 0x08, 0x64)
PANEL = RGBColor(0x0A, 0x12, 0x52)
ROW_A = RGBColor(0x1C, 0x34, 0x8F)
ROW_B = RGBColor(0x24, 0x42, 0xA0)
DOS = RGBColor(0x2F, 0xD3, 0xD8)       # cyan: readable on blue
BSD = RGBColor(0xFF, 0x7A, 0x6B)       # coral
CMT = RGBColor(0x9F, 0xC3, 0xFF)
FONT, CODE_FONT = "Arial", "Courier New"
NBH_FONT = "Tahoma"                    # Arial has no non-breaking hyphen (U+2011); Tahoma does
EM = 0.6                               # average advance of Arial Bold, in em, for wrap estimates
CODE_EM, CODE_LH = 0.6, 1.2            # Courier New advance and line height, in em
BG_VERSION = "3"


# ---- backgrounds -----------------------------------------------------------------------------
def _gradient(size, stops):
    w, h = size
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0)
                col.putpixel((0, y), tuple(round(a + (b - a) * k) for a, b in zip(c0, c1)))
                break
    return col.resize((w, h))


def _emboss(img, draw, strength=0.55, blur=6):
    """Raise the shapes drawn by `draw` out of the background: light upper-left edges, dark lower-right."""
    mask = Image.new("L", img.size, 0)
    draw(ImageDraw.Draw(mask))
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    emb = mask.filter(ImageFilter.EMBOSS)
    light = emb.point(lambda v: max(0, v - 128) * 2 * strength)
    dark = emb.point(lambda v: max(0, 128 - v) * 2 * strength)
    img = Image.composite(Image.new("RGB", img.size, (120, 150, 230)), img, light)
    return Image.composite(Image.new("RGB", img.size, (2, 4, 50)), img, dark)


def _prompt_glyph(d, cx, cy, r, width):
    """The course's own emblem: a ring with a command prompt '>_' inside."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=width)
    s = r * 0.42
    d.line([(cx - s * 1.1, cy - s), (cx - s * 0.1, cy), (cx - s * 1.1, cy + s)], fill=255, width=width,
           joint="curve")
    d.line([(cx + s * 0.15, cy + s), (cx + s * 1.15, cy + s)], fill=255, width=width)


def backgrounds() -> dict[str, Path]:
    out = ROOT / "build" / "slides-bg"
    paths = {k: out / f"{k}-v{BG_VERSION}.png" for k in ("content", "title", "section")}
    if all(p.exists() for p in paths.values()):
        return paths
    out.mkdir(parents=True, exist_ok=True)
    size = (2000, 1500)
    stops = [(0.0, (6, 8, 100)), (0.5, (31, 55, 151)), (1.0, (49, 94, 188))]

    img = _gradient(size, stops)
    img = _emboss(img, lambda d: d.ellipse([-1150, 80, 820, 1720], outline=255, width=70), 0.45)
    img = _emboss(img, lambda d: _prompt_glyph(d, 1560, 930, 360, 46), 0.4)
    img.save(paths["content"])

    sec = _gradient(size, stops)
    sec = _emboss(sec, lambda d: d.ellipse([-900, -300, 1300, 1900], outline=255, width=90), 0.5)
    sec = _emboss(sec, lambda d: _prompt_glyph(d, 1560, 1050, 300, 40), 0.35)
    sec.save(paths["section"])

    t = _gradient(size, stops)
    dark = Image.new("RGB", size, (3, 5, 56))
    ramp = Image.linear_gradient("L").rotate(90).resize(size).point(lambda v: max(0, v - 90) * 1.4)
    t = Image.composite(dark, t, ramp)
    disc = Image.new("L", size, 0)
    ImageDraw.Draw(disc).ellipse([-520, 620, 1080, 2220], fill=255)
    disc = disc.filter(ImageFilter.GaussianBlur(28))
    glow = _gradient(size, [(0.0, (90, 120, 190)), (1.0, (150, 175, 222))])
    t = Image.composite(glow, t, disc.point(lambda v: v * 0.85))
    t = _emboss(t, lambda d: _prompt_glyph(d, 360, 1130, 300, 44), 0.6)
    ring = Image.new("L", (1300, 560), 0)
    ImageDraw.Draw(ring).ellipse([30, 50, 1270, 500], outline=255, width=18)
    ring = ring.rotate(7, resample=Image.BICUBIC, expand=False).filter(ImageFilter.GaussianBlur(1.5))
    layer = Image.new("L", size, 0)
    layer.paste(ring, (670, 20))
    t = Image.composite(Image.new("RGB", size, (242, 196, 0)), t, layer)
    t.save(paths["title"])
    return paths


# ---- text helpers ----------------------------------------------------------------------------
EQ_RE = re.compile(r"(?<=\S) = (?=\S)")
HYPHEN_RE = re.compile(r"(?<=[A-Za-z0-9])-(?=[A-Za-z0-9])")
UNIT_RE = re.compile(r"(?<=\d) (?=(?:KB|MB|GB|bytes?|bits?|sectors?|ms|ns|s)\b)|(?<=\d) (?=[+\u00d7*/=-] ?\d)|"
                     r"(?<=[+\u00d7*/=]) (?=\d)")


def add_runs(p, text, size, color, font=FONT, bold=True, italic=False):
    """Add text to a paragraph without line breaks inside hyphenated words or between a number and its unit."""
    text = UNIT_RE.sub("\u00a0", EQ_RE.sub("\u00a0=\u00a0", text))
    parts = [text] if italic else HYPHEN_RE.split(text)
    for i, part in enumerate(parts):
        for chunk, f in ((part, font), ("\u2011" if i < len(parts) - 1 else "", NBH_FONT)):
            if not chunk:
                continue
            r = p.add_run()
            r.text = chunk
            r.font.size, r.font.name, r.font.bold, r.font.italic = Pt(size), f, bold, italic
            r.font.color.rgb = color


def balanced(text, width, size, em=EM, max_lines=2):
    """Split a title into lines of similar length (no single word left on the last line)."""
    if lines_of(text, width, size) <= 1:
        return [text]
    words = text.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        if lines_of(a, width, size) == 1 and lines_of(b, width, size) <= max_lines - 1:
            score = abs(len(a) - len(b))
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else [text]


def wing_bullet(p, char: str, color: RGBColor, indent_in: float, pct: int = 75) -> None:
    """A Wingdings bullet with a hanging indent ('l' is a round bullet, '\u00d8' an arrowhead)."""
    ppr = p._p.get_or_add_pPr()
    ppr.set("marL", str(int(Inches(indent_in))))
    ppr.set("indent", str(-int(Inches(indent_in))))
    for tag in ("a:buNone", "a:buChar", "a:buClr", "a:buFont", "a:buSzPct"):
        for el in ppr.findall(qn(tag)):
            ppr.remove(el)
    buclr = ppr.makeelement(qn("a:buClr"), {})
    buclr.append(buclr.makeelement(qn("a:srgbClr"), {"val": str(color)}))
    ppr.append(buclr)
    ppr.append(ppr.makeelement(qn("a:buSzPct"), {"val": str(pct * 1000)}))
    ppr.append(ppr.makeelement(qn("a:buFont"), {"typeface": "Wingdings", "pitchFamily": "2", "charset": "2"}))
    ppr.append(ppr.makeelement(qn("a:buChar"), {"char": char}))


def system_color(text: str) -> RGBColor | None:
    c = base.system_color(text)
    return DOS if c == base.DOS else BSD if c == base.BSD else None


_FONTS: dict = {}


def text_w(text, size, bold=True):
    """Width in inches of text in Arial (Bold) at a point size, from the font's own metrics."""
    from PIL import ImageFont
    key = bold
    if key not in _FONTS:
        try:
            _FONTS[key] = ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", 100)
        except OSError:
            _FONTS[key] = None
    f = _FONTS[key]
    if f is None:
        return len(text) * EM * size / 72
    return f.getlength(text) * size / 100 / 72


def lines_of(text, width, size, em=EM, bold=True):
    """Lines needed for text in a box of `width` inches (greedy word wrap, like PowerPoint)."""
    words = UNIT_RE.sub("\u00a0", EQ_RE.sub("\u00a0=\u00a0", text)).split(" ")
    space = text_w(" ", size, bold)
    lines, cur = 1, 0.0
    for wd in words:
        ww = text_w(wd, size, bold)
        if cur and cur + space + ww > width:
            lines += 1
            cur = ww
        else:
            cur += (space if cur else 0) + ww
        while cur > width:
            lines += 1
            cur -= width
    return lines


class RetroDeck:
    def __init__(self, outline: dict):
        self.o = outline
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        cp = self.prs.core_properties
        cp.author = cp.last_modified_by = "Francesco Valerio Buccoli"
        cp.title = f"Module {outline['module']}: {outline['title']}"
        cp.subject = "MS-DOS 4.00 and FreeBSD 15.1, from the boot sector to the shell"
        self.blank = self.prs.slide_layouts[6]
        self.bg = backgrounds()
        self.n = 0
        self.section_no = 0

    # ---- primitives ------------------------------------------------------------------------
    def slide(self, kind="content"):
        s = self.prs.slides.add_slide(self.blank)
        s.shapes.add_picture(str(self.bg[kind]), 0, 0, self.prs.slide_width, self.prs.slide_height)
        self.n += 1
        return s

    @staticmethod
    def box(s, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, weight=1.0):
        shp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill is None:
            shp.fill.background()
        else:
            shp.fill.solid()
            shp.fill.fore_color.rgb = fill
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = line
            shp.line.width = Pt(weight)
        shp.shadow.inherit = False
        return shp

    @staticmethod
    def text(s, x, y, w, h, text, size, color=WHITE, font=FONT, bold=True, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, italic=False, link=None):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        for i, ln in enumerate(text if isinstance(text, list) else [text]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            if font == CODE_FONT:
                r = p.add_run()
                r.text = ln
                r.font.size, r.font.name, r.font.bold, r.font.italic = Pt(size), font, bold, italic
                r.font.color.rgb = color
            else:
                add_runs(p, ln, size, color, font, bold, italic)
        if link:
            tb.click_action.hyperlink.address = link
        return tb

    def tag(self, s, x, y, label, color, size=12):
        w = 0.2 + len(label) * size * 0.0098
        b = self.box(s, x, y, w, 0.32, fill=color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        tf = b.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(size), FONT, True, NAVY
        return w

    def header(self, s, title) -> float:
        """Title at a fixed size and position (one or two balanced lines); returns where content starts."""
        width = W - 2 * MX - 0.05
        size, lines = TITLE_SIZE, [title]
        if lines_of(title, width, TITLE_SIZE) > 1:
            if lines_of(title, width, 28) == 1:
                size = 28
            else:
                lines = balanced(title, width, size)
                if len(lines) > 2 or any(lines_of(ln, width, size) > 1 for ln in lines):
                    size = 28
                    lines = balanced(title, width, size)
        self.text(s, MX, 0.32, W - 2 * MX, 1.2, lines, size, YELLOW)
        return 0.32 + len(lines) * size * 1.18 / 72 + 0.25

    def footer(self, s):
        self.text(s, MX, H - 0.38, 7, 0.26,
                  f"MS-DOS 4.00 \u00d7 FreeBSD 15.1  \u00b7  Module {self.o['module']}  \u00b7  F. V. Buccoli", 10, ICE,
                  bold=False)
        self.text(s, W - MX - 1, H - 0.38, 1, 0.26, str(self.n), 10, ICE, bold=False, align=PP_ALIGN.RIGHT)

    @staticmethod
    def notes(s, text):
        if text:
            s.notes_slide.notes_text_frame.text = text

    @staticmethod
    def fit(items, width, height, start, minimum, gap, em=EM):
        for size in range(start, minimum - 1, -1):
            need = sum(lines_of(t, width, size, em) for t in items) * size * 1.2 / 72 + gap * (len(items) - 1)
            if need <= height:
                return size
        return minimum

    def bullet_box(self, s, x, y, w, h, items, size, char="l", color=YELLOW, gap_pt=10):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, t in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_before = Pt(0 if i == 0 else gap_pt)
            add_runs(p, t, size, WHITE)
            wing_bullet(p, char, color, 0.42 if size >= 20 else 0.34)
        return tb

    # ---- slide types -----------------------------------------------------------------------
    def title_slide(self):
        s = self.slide("title")
        self.text(s, 4.1, 0.62, 5.3, 0.4, "OPERATING SYSTEMS", 20, WHITE, align=PP_ALIGN.CENTER, italic=True)
        self.text(s, 4.1, 1.0, 5.3, 1.1, f"Module {self.o['module']}", 60, ICE, align=PP_ALIGN.CENTER)
        title = self.o["title"]
        for size in (34, 30, 26, 22):
            lines = balanced(title, 5.55, size)
            if len(lines) <= 2 and all(lines_of(ln, 5.55, size) == 1 for ln in lines):
                break
        self.text(s, 3.95, 2.75, 5.65, len(lines) * size * 1.2 / 72 + 0.1, lines, size, YELLOW, align=PP_ALIGN.RIGHT)
        y = 2.75 + len(lines) * size * 1.2 / 72 + 0.15
        s.shapes.add_connector(1, Inches(5.4), Inches(y), Inches(9.6), Inches(y)).line.color.rgb = ICE
        if self.o.get("subtitle"):
            sub = self.o["subtitle"]
            sl = lines_of(sub, 5.6, 16)
            self.text(s, 3.95, y + 0.12, 5.65, sl * 16 * 1.25 / 72 + 0.1, sub, 16, WHITE, align=PP_ALIGN.RIGHT)
            y += 0.12 + sl * 16 * 1.25 / 72 + 0.25
        x = 9.6
        for label, c in (("FreeBSD 15.1", BSD), ("MS-DOS 4.00", DOS)):
            w = 0.2 + len(label) * 12 * 0.0098
            x -= w
            self.tag(s, x, y + 0.1, label, c)
            x -= 0.15
        self.text(s, 5.6, 6.2, 4.0, 0.55, ["Francesco Valerio Buccoli", "francesco@buccoli.com"], 14, WHITE,
                  align=PP_ALIGN.RIGHT)
        self.text(s, 5.0, 6.85, 4.6, 0.3,
                  f"Sources: MS-DOS {REPOS['dos']['sha'][:7]}  \u00b7  FreeBSD release/15.1.0", 11, ICE,
                  align=PP_ALIGN.RIGHT)

    def closing_slide(self):
        s = self.slide("title")
        self.text(s, 4.1, 0.95, 5.3, 1.1, "Questions?", 54, YELLOW, align=PP_ALIGN.CENTER)
        name = f"Module {self.o['module']}: {self.o['title']}"
        lines = balanced(name, 5.6, 20, max_lines=3)
        self.text(s, 3.95, 3.05, 5.65, 1.0, lines, 20, WHITE, align=PP_ALIGN.RIGHT)
        self.text(s, 3.95, 3.05 + len(lines) * 20 * 1.2 / 72 + 0.35, 5.65, 0.9,
                  ["Notes, labs and homework: course/ and labs/", "Every listing links to its exact source lines"],
                  16, ICE, align=PP_ALIGN.RIGHT, bold=False)
        self.text(s, 5.6, 6.2, 4.0, 0.55, ["Francesco Valerio Buccoli", "francesco@buccoli.com"], 14, WHITE,
                  align=PP_ALIGN.RIGHT)

    def section(self, d):
        self.section_no += 1
        s = self.slide("section")
        self.text(s, 0.9, 1.3, 3, 1.5, f"{self.section_no:02d}", 96, YELLOW)
        lines = balanced(d["title"], 8.2, 40, max_lines=3)
        self.text(s, 0.9, 3.0, 8.2, 1.7, lines, 40, WHITE)
        if d.get("subtitle"):
            self.text(s, 0.9, 3.0 + len(lines) * 40 * 1.2 / 72 + 0.3, 7.6, 1.2,
                      balanced(d["subtitle"], 7.6, 18, max_lines=3), 18, ICE)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def bullets(self, d):
        s = self.slide()
        top = self.header(s, d["title"])
        items = d["bullets"]
        size = self.fit(items, W - 2 * MX - 0.45, BOTTOM - top, 24, 16, 0.14)
        self.bullet_box(s, MX, top, W - 2 * MX, BOTTOM - top, items, size)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def compare(self, d):
        s = self.slide()
        top = self.header(s, d["title"])
        gap = 0.3
        col_w = (W - 2 * MX - gap) / 2
        sides = (d["left"], d["right"])
        size = min(self.fit(sd["bullets"], col_w - 0.85, BOTTOM - top - 0.95, 20, 13, 0.1) for sd in sides)
        text_h = max(sum(lines_of(b, col_w - 0.85, size) for b in sd["bullets"]) * size * 1.2 / 72
                     + 0.1 * (len(sd["bullets"]) - 1) for sd in sides)
        card_h = min(BOTTOM - top, 0.75 + text_h + 0.45)
        for i, sd in enumerate(sides):
            x = MX + i * (col_w + gap)
            c = system_color(sd["heading"]) or YELLOW
            self.box(s, x, top, col_w, card_h, fill=PANEL, line=c, weight=1.5)
            self.box(s, x, top, col_w, 0.52, fill=c)
            self.text(s, x + 0.15, top, col_w - 0.3, 0.52, sd["heading"], 18, NAVY, anchor=MSO_ANCHOR.MIDDLE)
            self.bullet_box(s, x + 0.15, top + 0.7, col_w - 0.4, card_h - 0.8, sd["bullets"], size,
                            char="\u00d8", color=c, gap_pt=6)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def _callout(self, s, x, y, w, i, t, size, color):
        b = self.box(s, x, y + 0.02, 0.3, 0.3, fill=color, shape=MSO_SHAPE.OVAL)
        tf = b.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(i)
        r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(11), FONT, True, NAVY
        h = lines_of(t, w - 0.45, size) * size * 1.2 / 72
        self.text(s, x + 0.42, y, w - 0.45, h + 0.05, t, size, WHITE)
        return h

    def code(self, d):
        s = self.slide()
        top = self.header(s, d["title"])
        lines = base.display_code(d["code"].rstrip("\n").split("\n"))
        cites = [c for c in find_citations(d.get("source", "")) if c.start]
        repo = cites[0].repo if cites else None
        color = DOS if repo == "dos" else BSD if repo == "bsd" else YELLOW
        callouts = d.get("callouts") or []
        maxlen = max(len(ln) for ln in lines) if lines else 1
        n = max(len(lines), 4)
        src_h = 0.36 if cites else 0.1
        full_w = W - 2 * MX

        def code_size(panel_w, avail_h):
            by_w = (panel_w - 0.4) * 72 / (CODE_EM * max(maxlen, 30))
            by_h = (avail_h - 0.5 - 0.18) * 72 / (CODE_LH * n)
            return max(8.0, min(16.0, math.floor(min(by_w, by_h) * 2) / 2))

        layout, csize, call_h = "full", 13, 0.0
        if callouts:
            side_w = 3.0
            side = code_size(full_w - side_w - 0.3, BOTTOM - top - src_h)
            cw = (full_w - 0.3) / 2
            csize = self.fit(callouts, cw - 0.45, 10, 14, 11, 0.0)
            rows = [max(lines_of(t, cw - 0.45, csize) for t in callouts[i:i + 2]) for i in range(0, len(callouts), 2)]
            call_h = sum(r * csize * 1.2 / 72 + 0.12 for r in rows) + 0.1
            below = code_size(full_w, BOTTOM - top - src_h - call_h)
            if side > below:
                layout = "side"
                side_csize = self.fit(callouts, side_w - 0.45, BOTTOM - top, 15, 11, 0.15)
        panel_w = full_w - (3.3 if layout == "side" else 0)
        avail = BOTTOM - top - src_h - (call_h if layout == "full" and callouts else 0)
        size = code_size(panel_w, avail)
        panel_h = min(avail, 0.5 + n * size * CODE_LH / 72 + 0.18)
        self.box(s, MX, top, panel_w, panel_h, fill=PANEL, line=color, weight=1.5)
        label = "MS-DOS 4.00" if repo == "dos" else "FreeBSD 15.1" if repo == "bsd" else "Code"
        tw = self.tag(s, MX + 0.18, top + 0.12, label, color, 11)
        if cites:
            c = cites[0]
            self.text(s, MX + 0.18 + tw + 0.15, top + 0.15, panel_w - tw - 0.6, 0.28,
                      f"{c.path.rsplit('/', 1)[-1]}  lines {c.start}-{c.end}", 11, ICE, CODE_FONT)
        tb = s.shapes.add_textbox(Inches(MX + 0.2), Inches(top + 0.5), Inches(panel_w - 0.3), Inches(panel_h - 0.55))
        tf = tb.text_frame
        tf.word_wrap = False
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        path = cites[0].path if cites else ""
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = 1.0
            if ln.strip() == "\u22ee":
                r = p.add_run()
                r.text = ln.replace("\u22ee", "\u2026 (lines omitted)")
                r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(size), CODE_FONT, True, YELLOW
                continue
            split = base.comment_start(ln, path)
            parts = [(ln, WHITE)] if split is None else [(ln[:split], WHITE), (ln[split:], CMT)]
            for txt, col in parts:
                if txt:
                    r = p.add_run()
                    r.text = txt
                    r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(size), CODE_FONT, True, col
        y = top + panel_h + 0.1
        if cites:
            c = cites[0]
            tb = self.text(s, MX, y, panel_w, 0.26,
                           f"Source: {REPOS[c.repo]['slug']} @ {REPOS[c.repo]['sha'][:7]}, {c.path}, lines {c.start}-{c.end}",
                           10, ICE, bold=False, link=c.text)
            for r in tb.text_frame.paragraphs[0].runs:
                r.font.underline = False
        if callouts and layout == "side":
            x, cy = MX + panel_w + 0.3, top + 0.05
            for i, t in enumerate(callouts, 1):
                cy += self._callout(s, x, cy, W - MX - x, i, t, side_csize, color) + 0.15
        elif callouts:
            y += src_h - 0.05
            cw = (full_w - 0.3) / 2
            for row in range(0, len(callouts), 2):
                hs = [self._callout(s, MX + j * (cw + 0.3), y, cw, row + j + 1, t, csize, color)
                      for j, t in enumerate(callouts[row:row + 2])]
                y += max(hs) + 0.12
        self.footer(s)
        self.notes(s, d.get("notes"))

    def diagram(self, d):
        s = self.slide()
        top = self.header(s, d["title"])
        lines = d["text"].rstrip("\n").split("\n")
        maxlen = max(len(ln) for ln in lines)
        max_h = BOTTOM - top
        size = min(16, (W - 2 * MX - 0.6) * 72 / (CODE_EM * max(maxlen, 40)), (max_h - 0.45) * 72 / (CODE_LH * len(lines)))
        size = max(9, math.floor(size * 2) / 2)
        bw = min(W - 2 * MX, maxlen * CODE_EM * size / 72 + 0.6)
        ph = min(max_h, len(lines) * size * CODE_LH / 72 + 0.45)
        x = (W - bw) / 2
        self.box(s, x, top, bw, ph, fill=PANEL, line=ICE)
        tb = s.shapes.add_textbox(Inches(x + 0.3), Inches(top + 0.22), Inches(bw - 0.4), Inches(ph - 0.3))
        tf = tb.text_frame
        tf.word_wrap = False
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = ln
            r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(size), CODE_FONT, True, WHITE
        self.footer(s)
        self.notes(s, d.get("notes"))

    def table(self, d):
        s = self.slide()
        top = self.header(s, d["title"])
        header, rows = d["header"], d["rows"]
        allrows = [header] + rows
        ncol = len(header)
        avail = BOTTOM - top
        total_w = W - 2 * MX
        pad = 0.26

        def longest_word(j, size):
            return max(text_w(w, size, i == 0 or j == 0) for i, r in enumerate(allrows)
                       for w in (UNIT_RE.sub("\u00a0", r[j]).split(" ") or [""]))

        def widths_for(size):
            mins = [longest_word(j, size) * 1.04 + pad + 0.04 for j in range(ncol)]
            if sum(mins) > total_w:
                return None
            weights = [max(8, max(len(r[j]) for r in allrows)) for j in range(ncol)]
            want = [max(m, total_w * w / sum(weights)) for m, w in zip(mins, weights)]
            extra = sum(want) - total_w
            if extra > 0:                                    # take the excess from columns above their minimum
                slack = [w - m for w, m in zip(want, mins)]
                want = [w - extra * sl / sum(slack) for w, sl in zip(want, slack)]
            return want

        size, widths = 18, None
        while size >= 10:
            widths = widths_for(size)
            if widths:
                h = sum(max(lines_of(c, widths[j] - pad, size) for j, c in enumerate(r)) * size * 1.2 / 72 + 0.14
                        for r in allrows)
                if h <= avail:
                    break
            size -= 1
        widths = widths or [total_w / ncol] * ncol
        shape = s.shapes.add_table(len(rows) + 1, ncol, Inches(MX), Inches(top), Inches(total_w),
                                   Inches(min(avail, 0.42 * (len(rows) + 1))))
        tbl = shape.table
        tbl.first_row = True
        for j, w in enumerate(widths):
            tbl.columns[j].width = Emu(int(Inches(w)))
        for i, row in enumerate(allrows):
            for j, val in enumerate(row):
                cell = tbl.cell(i, j)
                cell.margin_left = cell.margin_right = Inches(pad / 2)
                cell.margin_top = cell.margin_bottom = Inches(0.06)
                cell.fill.solid()
                if i == 0:
                    cell.fill.fore_color.rgb = (system_color(val) or YELLOW) if val.strip() else PANEL
                else:
                    cell.fill.fore_color.rgb = ROW_A if i % 2 else ROW_B
                p = cell.text_frame.paragraphs[0]
                add_runs(p, val, size, NAVY if i == 0 else (YELLOW if j == 0 else WHITE), bold=(i == 0 or j == 0))
        self.footer(s)
        self.notes(s, d.get("notes"))

    def stat(self, d):
        s = self.slide()
        top = self.header(s, d["title"])
        stats = d["stats"]
        per_row = len(stats) if len(stats) <= 3 else 2 if len(stats) == 4 else 3
        nrows = math.ceil(len(stats) / per_row)
        gap = 0.3
        cw = (W - 2 * MX - gap * (per_row - 1)) / per_row
        vsize = min(54, min(int((cw - 0.4) * 72 / (0.62 * max(len(st["value"]), 1))) for st in stats))
        lsize = 16 if nrows == 1 else 14
        lab_h = max(lines_of(st["label"], cw - 0.4, lsize) for st in stats) * lsize * 1.25 / 72
        val_h = vsize * 1.2 / 72
        ch = 0.25 + val_h + 0.1 + lab_h + 0.25
        avail = BOTTOM - top
        if nrows * ch + (nrows - 1) * gap > avail:
            ch = (avail - (nrows - 1) * gap) / nrows
        for i, st in enumerate(stats):
            row, col = divmod(i, per_row)
            in_row = min(per_row, len(stats) - row * per_row)
            x = MX + (per_row - in_row) * (cw + gap) / 2 + col * (cw + gap)
            y = top + 0.1 + row * (ch + gap)
            c = system_color(st["label"]) or YELLOW
            self.box(s, x, y, cw, ch, fill=PANEL, line=c, weight=1.5)
            self.text(s, x + 0.2, y + 0.25, cw - 0.4, val_h, st["value"], vsize, c)
            self.text(s, x + 0.2, y + 0.25 + val_h + 0.1, cw - 0.4, lab_h, st["label"], lsize, WHITE)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def figure(self, d):
        s = self.slide()
        top = self.header(s, d["title"]) + 0.08
        cap_h = 0.45 if d.get("caption") else 0.0
        max_w, max_h = W - 0.5, BOTTOM - top - cap_h - 0.1
        # A 4:3 slide often shows the tall (notes) variant of a diagram larger than the wide (slide) variant.
        stem = d["diagram"]
        names = [stem] + ([stem[:-5]] if stem.endswith("-wide") and (ROOT / "diagrams" / f"{stem[:-5]}.json").exists()
                          else [])
        best = None
        for name in names:
            png = base.ensure_png(name)
            with Image.open(png) as im:
                pw, ph = im.size
            scale = min(max_w / pw, max_h / ph)
            if best is None or scale > best[0]:
                best = (scale, png, pw, ph)
        scale, png, pw, ph = best
        w, h = pw * scale, ph * scale
        x = (W - w) / 2
        y = top + max(0.0, (max_h - h) / 3)
        self.box(s, x - 0.08, y - 0.08, w + 0.16, h + 0.16, fill=WHITE, line=YELLOW, weight=2)
        s.shapes.add_picture(str(png), Inches(x), Inches(y), Inches(w), Inches(h))
        if d.get("caption"):
            self.text(s, MX, y + h + 0.16, W - 2 * MX, 0.4, d["caption"], 13, ICE, bold=False, italic=True,
                      align=PP_ALIGN.CENTER)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def build(self) -> Presentation:
        self.title_slide()
        for d in self.o["slides"]:
            getattr(self, d["type"])(d)
        self.closing_slide()
        return self.prs

"""Build one PowerPoint deck per module from slides/NN-*.outline.json.

    python tools/build_slides.py                 # all outlines -> slides/NN-*.pptx
    python tools/build_slides.py slides/01-boot.outline.json
    python tools/build_slides.py --render        # also export PNGs via PowerPoint (Windows) for review
    python tools/build_slides.py --style modern  # the 16:9 light style instead of the default retro style

Code on slides must be verbatim source: every "code" slide is checked against
its line-ranged permalink with the same rules as listings in the notes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_citations import match_listing  # noqa: E402
from citations import ELISION_RE, REPOS, ROOT, find_citations, norm, read_lines  # noqa: E402

W, H = 13.333, 7.5
MARGIN = 0.6
DARK = RGBColor(0x15, 0x19, 0x1E)
INK = RGBColor(0x1F, 0x23, 0x28)
MUTED = RGBColor(0x5C, 0x66, 0x70)
SOFT = RGBColor(0xA8, 0xB0, 0xB8)
PAPER = RGBColor(0xF7, 0xF5, 0xF0)
PANEL = RGBColor(0xEC, 0xE8, 0xE1)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CODE_BG = RGBColor(0x1E, 0x23, 0x29)
CODE_FG = RGBColor(0xE6, 0xED, 0xF3)
CODE_CMT = RGBColor(0x8B, 0x94, 0x9E)
DOS = RGBColor(0x0E, 0x7C, 0x86)
BSD = RGBColor(0xAB, 0x2B, 0x28)
AMBER = RGBColor(0xD9, 0xA4, 0x41)
TITLE_FONT, BODY_FONT, CODE_FONT = "Segoe UI Semibold", "Segoe UI", "Consolas"


PREPROCESSOR = ("#include", "#define", "#if", "#ifdef", "#ifndef", "#else", "#elif", "#endif", "#undef")


def comment_start(line: str, path: str) -> int | None:
    """Column where a comment starts in a line of MASM, GNU as (.S) or C source, if any."""
    stripped = line.lstrip()
    lead = len(line) - len(stripped)
    if path.upper().endswith((".ASM", ".INC", ".SKL", ".EQU", ".MAC")):
        return line.index(";") if ";" in line else None
    if stripped.startswith(("/*", "* ", "*/")) or stripped == "*":
        return lead
    marks = ["/*", "//"]
    if path.endswith(".S") and not stripped.startswith(PREPROCESSOR):
        marks.append("#")
    found = [line.index(m) for m in marks if m in line]
    return min(found) if found else None


def system_color(text: str) -> RGBColor | None:
    """Teal for MS-DOS, red for FreeBSD, but only when the text names exactly one of them."""
    t = text.lower()
    dos = "ms-dos" in t or "command.com" in t
    bsd = "freebsd" in t or "/bin/sh" in t
    if dos and not bsd:
        return DOS
    if bsd and not dos:
        return BSD
    return None


def wrapped_lines(text: str, width_in: float, size: float, em: float = 0.53) -> int:
    """Estimate how many lines PowerPoint needs for text at a font size (greedy word wrap)."""
    cpl = max(6, int(width_in * 72 / (em * size)))
    lines, cur = 1, 0
    for word in text.split():
        n = len(word)
        if cur and cur + 1 + n > cpl:
            lines += 1
            cur = n
        else:
            cur += (1 if cur else 0) + n
        while cur > cpl:
            lines += 1
            cur -= cpl
    return lines


def display_code(lines: list[str]) -> list[str]:
    """Lines as shown on a slide: tabs expanded, common indentation removed, elisions reduced to '⋮'."""
    lines = [norm(ln) for ln in lines]
    lines = [(ln[:len(ln) - len(ln.lstrip())] + "\u22ee") if ELISION_RE.match(ln) else ln for ln in lines]
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    cut = min(indents) if indents else 0
    return [ln[cut:] for ln in lines]


def hanging_bullet(p, color: RGBColor, indent_in: float = 0.28) -> None:
    """Turn a paragraph into a bullet with a hanging indent, so wrapped lines align with the text."""
    from pptx.oxml.ns import qn
    ppr = p._p.get_or_add_pPr()
    ppr.set("marL", str(int(Inches(indent_in))))
    ppr.set("indent", str(-int(Inches(indent_in))))
    for tag in ("a:buNone", "a:buChar", "a:buClr", "a:buFont"):
        for el in ppr.findall(qn(tag)):
            ppr.remove(el)
    buclr = ppr.makeelement(qn("a:buClr"), {})
    srgb = buclr.makeelement(qn("a:srgbClr"), {"val": str(color)})
    buclr.append(srgb)
    bufont = ppr.makeelement(qn("a:buFont"), {"typeface": "Arial"})
    buchar = ppr.makeelement(qn("a:buChar"), {"char": "\u2022"})
    # Schema order inside a:pPr: lnSpc, spcBef, spcAft, buClr..., buFont, buChar
    ppr.append(buclr)
    ppr.append(bufont)
    ppr.append(buchar)


class Deck:
    def __init__(self, outline: dict):
        self.o = outline
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        cp = self.prs.core_properties
        cp.author = cp.last_modified_by = "Francesco Valerio Buccoli"
        cp.title = f"Module {outline['module']}: {outline['title']}"
        cp.subject = "MS-DOS 4.00 and FreeBSD 15.1, from the boot sector to the shell"
        self.blank = self.prs.slide_layouts[6]
        self.n = 0
        self.section_no = 0
        self.kicker = f"MODULE {outline['module']} \u00b7 {outline['title'].split(':')[0].upper()}"

    # ---- primitives -------------------------------------------------------------------------
    def slide(self, bg: RGBColor):
        s = self.prs.slides.add_slide(self.blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = bg
        self.n += 1
        return s

    @staticmethod
    def box(s, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
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
            shp.line.width = Pt(1)
        if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            shp.adjustments[0] = radius
        shp.shadow.inherit = False
        return shp

    @staticmethod
    def text(s, x, y, w, h, text, size, color=INK, font=BODY_FONT, bold=False, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, spacing=None, link=None):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        lines = text if isinstance(text, list) else [text]
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            if spacing:
                p.space_after = Pt(spacing)
            r = p.add_run()
            r.text = ln
            f = r.font
            f.size, f.name, f.bold = Pt(size), font, bold
            f.color.rgb = color
        if link:
            # A shape-level link keeps the run's own colour (run-level links take the theme's link colour).
            tb.click_action.hyperlink.address = link
        return tb

    def tag(self, s, x, y, label, color, filled=True):
        w = 0.12 + len(label) * 0.085
        b = self.box(s, x, y, w, 0.3, fill=color if filled else None, line=color, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
                     radius=0.5)
        tf = b.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.size, r.font.name, r.font.bold = Pt(11), BODY_FONT, True
        r.font.color.rgb = WHITE if filled else color
        return w

    def header(self, s, title):
        self.text(s, MARGIN, 0.38, W - 2 * MARGIN, 0.3, self.kicker, 11, MUTED, BODY_FONT, True)
        size = 30 if len(title) <= 52 else 26
        self.text(s, MARGIN, 0.66, W - 2 * MARGIN, 0.8, title, size, INK, TITLE_FONT)

    def footer(self, s, dark=False):
        c = SOFT if dark else MUTED
        self.text(s, MARGIN, H - 0.42, 9, 0.25, f"MS-DOS 4.00 \u00d7 FreeBSD 15.1 \u00b7 Module {self.o['module']} \u00b7 F. V. Buccoli",
                  9, c)
        self.text(s, W - MARGIN - 1, H - 0.42, 1, 0.25, str(self.n), 9, c, align=PP_ALIGN.RIGHT)

    @staticmethod
    def notes(s, text):
        if text:
            s.notes_slide.notes_text_frame.text = text

    @staticmethod
    def fit_size(items: list[str], width_in: float, height_in: float, start=20, minimum=12, gap=0.18,
                 char_em=0.53) -> int:
        for size in range(start, minimum - 1, -1):
            lines = sum(wrapped_lines(t, width_in, size, char_em) for t in items)
            need = lines * size * 1.3 / 72 + gap * (len(items) - 1)
            if need <= height_in:
                return size
        return minimum

    # ---- slide types ------------------------------------------------------------------------
    def title_slide(self):
        s = self.slide(DARK)
        self.box(s, 0, 0, 0.18, H, fill=DOS)
        self.box(s, 0, H / 2, 0.18, H / 2, fill=BSD)
        self.text(s, 0.9, 1.5, 11, 0.4, f"OPERATING SYSTEMS \u00b7 MODULE {self.o['module']}", 14, AMBER, BODY_FONT, True)
        title_lines = math.ceil(len(self.o["title"]) / 38)
        self.text(s, 0.9, 2.0, 11.5, title_lines * 0.75, self.o["title"], 44, WHITE, TITLE_FONT)
        y = 2.0 + title_lines * 0.78 + 0.3
        if self.o.get("subtitle"):
            self.text(s, 0.9, y, 11, 1.0, self.o["subtitle"], 20, SOFT)
            y += 0.55 * math.ceil(len(self.o["subtitle"]) / 80) + 0.55
        x = 0.9
        x += self.tag(s, x, y, "MS-DOS 4.00", DOS) + 0.15
        self.tag(s, x, y, "FreeBSD 15.1", BSD)
        self.text(s, 0.9, 6.05, 11.5, 0.35, "Francesco Valerio Buccoli  \u00b7  francesco@buccoli.com", 14,
                  RGBColor(0xE6, 0xED, 0xF3), BODY_FONT)
        self.text(s, 0.9, 6.55, 11.5, 0.3,
                  f"Sources: microsoft/MS-DOS @ {REPOS['dos']['sha'][:7]}  \u00b7  freebsd/freebsd-src @ release/15.1.0",
                  13, RGBColor(0xC9, 0xD1, 0xD9), CODE_FONT)

    def section(self, d):
        self.section_no += 1
        s = self.slide(DARK)
        self.text(s, 0.9, 1.4, 4, 1.6, f"{self.section_no:02d}", 96, AMBER, TITLE_FONT)
        self.text(s, 0.9, 3.3, 11.5, 1.6, d["title"], 40, WHITE, TITLE_FONT)
        if d.get("subtitle"):
            self.text(s, 0.9, 4.9, 11, 0.8, d["subtitle"], 18, SOFT)
        self.footer(s, dark=True)
        self.notes(s, d.get("notes"))

    def bullets(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        items = d["bullets"]
        top, bottom = 1.75, H - 0.75
        avail_h = bottom - top
        size = self.fit_size(items, W - 2 * MARGIN - 0.9, avail_h, start=24, minimum=14, gap=0.3)
        row_h = [max(0.55, wrapped_lines(t, W - 2 * MARGIN - 0.9, size) * size * 1.3 / 72) for t in items]
        gap = min(0.35, max(0.15, (avail_h - sum(row_h)) / max(1, len(items))))
        y = top
        for i, (t, rh) in enumerate(zip(items, row_h), 1):
            b = self.box(s, MARGIN, y + 0.02, 0.48, 0.48, fill=DARK, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.18)
            tf = b.text_frame
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = str(i)
            r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(16), TITLE_FONT, True, WHITE
            self.text(s, MARGIN + 0.8, y + max(0, (0.52 - size * 1.25 / 72) / 2), W - 2 * MARGIN - 0.9, rh, t, size, INK)
            y += rh + gap
        self.footer(s)
        self.notes(s, d.get("notes"))

    def compare(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        col_w = (W - 2 * MARGIN - 0.4) / 2
        top, max_h = 1.75, H - 0.75 - 1.75
        sides = (d["left"], d["right"])
        size = min(self.fit_size(side["bullets"], col_w - 0.9, max_h - 1.2, start=20, minimum=12, gap=0.15)
                   for side in sides)
        text_h = max(sum(wrapped_lines(b, col_w - 0.9, size) * size * 1.3 / 72 + 0.15 for b in side["bullets"])
                     for side in sides)
        card_h = min(max_h, max(2.6, 0.85 + text_h + 0.4))
        for i, side in enumerate(sides):
            x = MARGIN + i * (col_w + 0.4)
            c = system_color(side["heading"]) or DARK
            self.box(s, x, top, col_w, card_h, fill=WHITE, line=PANEL)
            self.box(s, x, top, col_w, 0.62, fill=c)
            self.text(s, x + 0.3, top, col_w - 0.6, 0.62, side["heading"], 18, WHITE, TITLE_FONT,
                      anchor=MSO_ANCHOR.MIDDLE)
            tb = self.text(s, x + 0.3, top + 0.85, col_w - 0.6, card_h - 1.0, side["bullets"], size, INK, spacing=8)
            for p in tb.text_frame.paragraphs:
                hanging_bullet(p, c)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def code(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        lines = display_code(d["code"].rstrip("\n").split("\n"))
        cites = [c for c in find_citations(d.get("source", "")) if c.start]
        repo = cites[0].repo if cites else None
        color = DOS if repo == "dos" else BSD if repo == "bsd" else DARK
        callouts = d.get("callouts") or []
        panel_w = W - 2 * MARGIN - (4.1 if callouts else 0)
        top, max_h = 1.7, H - 0.75 - 1.7 - 0.45
        maxlen = max(len(ln) for ln in lines) if lines else 1
        code_w = panel_w - 0.6
        size = min(18, (code_w * 72) / (0.56 * max(maxlen, 30)), ((max_h - 0.95) * 72) / (1.2 * max(len(lines), 6)))
        size = max(9, math.floor(size * 2) / 2)
        code_h = len(lines) * size * 1.2 / 72
        panel_h = min(max_h, max(2.4, 0.7 + code_h + 0.4))
        self.box(s, MARGIN, top, panel_w, panel_h, fill=CODE_BG)
        self.box(s, MARGIN, top, 0.08, panel_h, fill=color)
        label = "MS-DOS 4.00" if repo == "dos" else "FreeBSD 15.1" if repo == "bsd" else "Code"
        tx = MARGIN + 0.3
        tw = self.tag(s, tx, top + 0.18, label, color)
        if cites:
            c = cites[0]
            name = c.path.rsplit("/", 1)[-1]
            self.text(s, tx + tw + 0.15, top + 0.2, panel_w - tw - 0.8, 0.3,
                      f"{name}  lines {c.start}-{c.end}", 12, SOFT, CODE_FONT)
        tb = s.shapes.add_textbox(Inches(tx), Inches(top + 0.7), Inches(code_w), Inches(panel_h - 0.8))
        tf = tb.text_frame
        tf.word_wrap = False
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        path = cites[0].path if cites else ""
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = 1.0
            if ln.strip() == "\u22ee":
                r = p.add_run()
                r.text = ln.replace("\u22ee", "\u22ee  (lines omitted)")
                r.font.size, r.font.name, r.font.color.rgb, r.font.bold = Pt(size), CODE_FONT, AMBER, True
                continue
            split = comment_start(ln, path)
            parts = [(ln, CODE_FG)] if split is None else [(ln[:split], CODE_FG), (ln[split:], CODE_CMT)]
            for txt, col in parts:
                if not txt:
                    continue
                r = p.add_run()
                r.text = txt
                r.font.size, r.font.name, r.font.color.rgb = Pt(size), CODE_FONT, col
        if cites:
            c = cites[0]
            tb = self.text(s, MARGIN, top + panel_h + 0.1, panel_w, 0.3,
                           f"Source: {REPOS[c.repo]['slug']} @ {REPOS[c.repo]['sha'][:7]}, {c.path}, "
                           f"lines {c.start}-{c.end}", 12, color, BODY_FONT, link=c.text)
            tb.text_frame.paragraphs[0].runs[0].font.underline = False
        if callouts:
            x = MARGIN + panel_w + 0.35
            cw = W - MARGIN - x
            size_c = self.fit_size(callouts, cw - 0.6, max_h, start=16, minimum=12, gap=0.3, char_em=0.6)
            y = top + 0.05
            for i, t in enumerate(callouts, 1):
                b = self.box(s, x, y, 0.42, 0.42, fill=color, shape=MSO_SHAPE.OVAL)
                tf = b.text_frame
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                r = p.add_run()
                r.text = str(i)
                r.font.size, r.font.name, r.font.bold, r.font.color.rgb = Pt(13), TITLE_FONT, True, WHITE
                h = max(0.45, wrapped_lines(t, cw - 0.6, size_c, 0.6) * size_c * 1.3 / 72)
                self.text(s, x + 0.6, y + 0.03, cw - 0.6, h, t, size_c, INK)
                y += h + 0.3
        self.footer(s)
        self.notes(s, d.get("notes"))

    def diagram(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        lines = d["text"].rstrip("\n").split("\n")
        maxlen = max(len(ln) for ln in lines)
        top, max_h = 1.75, H - 0.75 - 1.75
        size = min(18, (W - 2 * MARGIN - 0.8) * 72 / (0.55 * max(maxlen, 40)), (max_h - 0.5) * 72 / (1.2 * len(lines)))
        size = max(9, math.floor(size * 2) / 2)
        block_w = min(W - 2 * MARGIN, maxlen * 0.55 * size / 72 + 0.9)
        ph = min(max_h, len(lines) * size * 1.2 / 72 + 0.6)
        top += max(0.0, (max_h - ph) / 3)
        x = (W - block_w) / 2
        self.box(s, x, top, block_w, ph, fill=PANEL)
        tb = s.shapes.add_textbox(Inches(x + 0.45), Inches(top + 0.25), Inches(block_w - 0.6), Inches(ph - 0.4))
        tf = tb.text_frame
        tf.word_wrap = False
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = ln
            r.font.size, r.font.name, r.font.color.rgb = Pt(size), CODE_FONT, INK
        self.footer(s)
        self.notes(s, d.get("notes"))

    def table(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        header, rows = d["header"], d["rows"]
        ncol = len(header)
        top, avail = 1.75, H - 0.75 - 1.75 - 0.1
        total_w = W - 2 * MARGIN
        first_len = max(len(r[0]) for r in rows + [header])
        first_w = min(3.4, max(1.6, first_len * 0.105 + 0.35))
        weights = [max(12, max(len(r[j]) for r in rows + [header])) for j in range(1, ncol)]
        rest = total_w - first_w
        widths = [first_w] + [max(1.8, rest * w / sum(weights)) for w in weights]
        scale = rest / sum(widths[1:])
        widths = [first_w] + [w * scale for w in widths[1:]]
        size = 18
        while size > 11:
            h = 0.0
            for r in [header] + rows:
                n = max(wrapped_lines(c, widths[j] - 0.3, size) for j, c in enumerate(r))
                h += n * size * 1.25 / 72 + 0.2
            if h <= avail:
                break
            size -= 1
        shape = s.shapes.add_table(len(rows) + 1, ncol, Inches(MARGIN), Inches(top), Inches(total_w),
                                   Inches(min(avail, 0.5 * (len(rows) + 1))))
        tbl = shape.table
        tbl.first_row = True
        for j, w in enumerate(widths):
            tbl.columns[j].width = Emu(int(Inches(w)))
        for i, row in enumerate([header] + rows):
            for j, val in enumerate(row):
                cell = tbl.cell(i, j)
                cell.margin_left = cell.margin_right = Inches(0.14)
                cell.margin_top = cell.margin_bottom = Inches(0.07)
                cell.fill.solid()
                if i == 0:
                    cell.fill.fore_color.rgb = system_color(val) or DARK
                else:
                    cell.fill.fore_color.rgb = WHITE if i % 2 else PANEL
                tf = cell.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                r = p.add_run()
                r.text = val
                r.font.name = TITLE_FONT if (i == 0 or j == 0) else BODY_FONT
                r.font.size = Pt(size + (1 if i == 0 else 0))
                r.font.color.rgb = WHITE if i == 0 else INK
        self.footer(s)
        self.notes(s, d.get("notes"))

    def stat(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        stats = d["stats"]
        per_row = len(stats) if len(stats) <= 4 else 3
        nrows = math.ceil(len(stats) / per_row)
        gap = 0.35
        cw = (W - 2 * MARGIN - gap * (per_row - 1)) / per_row
        vsize = min(60, min(int((cw - 0.6) * 72 / (0.62 * max(len(st["value"]), 1))) for st in stats))
        label_size = 18 if nrows == 1 else 16
        label_h = max(wrapped_lines(st["label"], cw - 0.6, label_size) for st in stats) * label_size * 1.3 / 72
        value_h = vsize * 1.25 / 72
        ch = 0.35 + value_h + 0.15 + label_h + 0.35
        avail = H - 0.75 - 1.75
        total = nrows * ch + (nrows - 1) * gap
        if total > avail:
            ch = (avail - (nrows - 1) * gap) / nrows
            total = avail
        top0 = 1.75 + max(0.0, (avail - total) / 2.5)
        for i, st in enumerate(stats):
            row, col = divmod(i, per_row)
            in_row = min(per_row, len(stats) - row * per_row)
            offset = (per_row - in_row) * (cw + gap) / 2
            x = MARGIN + offset + col * (cw + gap)
            y = top0 + row * (ch + gap)
            c = system_color(st["label"])
            self.box(s, x, y, cw, ch, fill=WHITE, line=PANEL)
            self.box(s, x, y, cw, 0.1, fill=c or AMBER)
            self.text(s, x + 0.3, y + 0.35, cw - 0.6, value_h, st["value"], vsize, c or INK, TITLE_FONT)
            self.text(s, x + 0.3, y + 0.35 + value_h + 0.15, cw - 0.6, label_h, st["label"], label_size, INK)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def figure(self, d):
        s = self.slide(PAPER)
        self.header(s, d["title"])
        png = ensure_png(d["diagram"])
        from PIL import Image
        with Image.open(png) as im:
            pw, ph = im.size
        top = 1.65
        cap_h = 0.4 if d.get("caption") else 0.0
        max_w, max_h = W - 2 * MARGIN, H - 0.75 - top - cap_h - 0.1
        scale = min(max_w / pw, max_h / ph)
        w, h = pw * scale, ph * scale
        x = (W - w) / 2
        s.shapes.add_picture(str(png), Inches(x), Inches(top), Inches(w), Inches(h))
        if d.get("caption"):
            self.text(s, MARGIN, top + h + 0.08, W - 2 * MARGIN, 0.35, d["caption"], 13, MUTED,
                      align=PP_ALIGN.CENTER)
        self.footer(s)
        self.notes(s, d.get("notes"))

    def build(self) -> Presentation:
        self.title_slide()
        for d in self.o["slides"]:
            getattr(self, {"section": "section", "bullets": "bullets", "compare": "compare", "code": "code",
                           "diagram": "diagram", "table": "table", "stat": "stat", "figure": "figure"}[d["type"]])(d)
        return self.prs


def ensure_png(name: str) -> Path:
    """PNG of diagrams/<name>.svg for a slide, rendered through PowerPoint when missing or stale."""
    import subprocess
    stem = Path(name).stem
    spec = ROOT / "diagrams" / f"{stem}.json"
    svg = ROOT / "diagrams" / f"{stem}.svg"
    png = ROOT / "build" / "diagrams" / f"{stem}.png"
    if spec.exists() and (not svg.exists() or svg.stat().st_mtime < spec.stat().st_mtime):
        subprocess.run([sys.executable, str(ROOT / "tools" / "diagrams.py"), str(spec)], check=True,
                       stdout=subprocess.DEVNULL)
    if not svg.exists():
        raise SystemExit(f"diagram not found: {svg}")
    if not png.exists() or png.stat().st_mtime < svg.stat().st_mtime:
        shell = "pwsh" if __import__("shutil").which("pwsh") else "powershell"
        subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "tools" / "svg_to_png.ps1"), "-Svg", str(svg), "-OutDir", str(png.parent)],
                       check=True, stdout=subprocess.DEVNULL)
    return png


def verify(outline: dict, path: Path) -> list[str]:
    errs = []
    for i, d in enumerate(outline["slides"], 1):
        if d["type"] != "code":
            continue
        cites = [c for c in find_citations(d.get("source", "")) if c.start]
        if len(cites) != 1:
            errs.append(f"{path.name} slide {i}: code slide needs one line-ranged source permalink")
            continue
        c = cites[0]
        if c.ref != REPOS[c.repo]["sha"]:
            errs.append(f"{path.name} slide {i}: source not pinned")
            continue
        err = match_listing(d["code"].rstrip("\n").split("\n"), read_lines(c.local_path), c.start, c.end)
        if err:
            errs.append(f"{path.name} slide {i} ({d['title']}): {err}")
        if len(d["code"].rstrip("\n").split("\n")) > 18:
            errs.append(f"{path.name} slide {i}: more than 18 code lines")
    return errs


def render(pptx: Path, outdir: Path, attempts: int = 3) -> None:
    import subprocess
    import time
    script = ROOT / "tools" / "render_slides.ps1"
    shell = "pwsh" if __import__("shutil").which("pwsh") else "powershell"
    for attempt in range(1, attempts + 1):
        r = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(pptx),
                            str(outdir)])
        if r.returncode == 0:
            return
        if attempt < attempts:
            # PowerPoint rejects COM calls while it is busy (RPC_E_CALL_REJECTED); wait and try again.
            print(f"render of {pptx.name} failed (attempt {attempt}), retrying", file=sys.stderr)
            time.sleep(10)
    raise SystemExit(f"could not render {pptx.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outlines", nargs="*", type=Path)
    ap.add_argument("--render", action="store_true", help="export slide PNGs to build/slides/<deck>/")
    ap.add_argument("--style", choices=("retro", "modern"), default="retro",
                    help="retro: 4:3, 1990s conference look (tools/slides_retro.py); modern: 16:9, light")
    a = ap.parse_args()
    outlines = [p.resolve() for p in a.outlines] or sorted((ROOT / "slides").glob("*.outline.json"))
    rc = 0
    for path in outlines:
        outline = json.loads(path.read_text(encoding="utf-8"))
        errs = verify(outline, path)
        for e in errs:
            print("error:", e)
        if errs:
            rc = 1
            continue
        out = path.with_name(path.name.replace(".outline.json", ".pptx"))
        if a.style == "retro":
            from slides_retro import RetroDeck
            prs = RetroDeck(outline).build()
        else:
            prs = Deck(outline).build()
        prs.save(out)
        print(f"{out.relative_to(ROOT)}: {len(prs.slides)} slides ({a.style})")
        if a.render:
            render(out, ROOT / "build" / "slides" / out.stem)
    return rc


if __name__ == "__main__":
    sys.exit(main())

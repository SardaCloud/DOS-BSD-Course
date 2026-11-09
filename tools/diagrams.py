"""Block diagrams for the course: JSON specs in diagrams/*.json -> diagrams/*.svg (+ PNG for slides).

    python tools/diagrams.py                 # render every spec to SVG
    python tools/diagrams.py --png           # also render build/diagrams/*.png (PowerPoint on Windows, else Edge headless)
    python tools/diagrams.py diagrams/syscall-path.json --png

Spec (all coordinates in grid units, default 1 unit = 100 px; origin top left):

    {
      "width": 12, "height": 7,
      "lanes": [{"x": 0, "y": 0, "w": 6, "h": 7, "label": "MS-DOS 4.00", "kind": "dos"}],
      "nodes": [{"id": "a", "x": 0.5, "y": 1, "w": 2.5, "h": 0.8, "label": "INT 21h\\nAH=3Fh",
                 "kind": "dos", "shape": "box", "sub": "optional small text"}],
      "edges": [{"from": "a", "to": "b", "label": "handle", "style": "solid", "route": "auto"}],
      "notes": [{"x": 8, "y": 6, "w": 3, "text": "free text", "kind": "neutral"}]
    }

kind:  dos (teal) | bsd (red) | hw (amber) | user | kernel | data | neutral
shape: box | round | cyl (disk, storage) | note
edge style: solid | dashed | thick ; route: auto | straight | hv | vh | hvh | vhv
Optional per edge: "from_side"/"to_side" = left|right|top|bottom, "bidir": true,
"via": grid x of the vertical leg (route hvh) or grid y of the horizontal leg (route vhv),
"from_pos"/"to_pos" = 0..1: where the edge meets its side (default 0.5, the middle; 0 = left or top end).
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = ROOT / "diagrams"
PNG_DIR = ROOT / "build" / "diagrams"
FONT = "Segoe UI, Aptos, Calibri, Helvetica, Arial, sans-serif"
MONO = "Consolas, Menlo, monospace"

KINDS = {
    #          stroke     fill       text
    "dos":     ("#0E7C86", "#E3F2F3", "#0B3D42"),
    "bsd":     ("#AB2B28", "#F8E6E5", "#4A1312"),
    "hw":      ("#B7862A", "#FBF1DC", "#4D3810"),
    "user":    ("#4F6D8A", "#E8EEF4", "#1F2F40"),
    "kernel":  ("#2E3440", "#E4E6EA", "#15191E"),
    "data":    ("#6B7280", "#FFFFFF", "#1F2328"),
    "neutral": ("#6B7280", "#F3F2EE", "#1F2328"),
}
LANE_FILL = {"dos": "#F3FAFA", "bsd": "#FCF4F4", "hw": "#FDF8EE", "user": "#F5F8FB",
             "kernel": "#F4F5F7", "data": "#FAFAFA", "neutral": "#F7F6F2"}


def text_width(s: str, size: float, mono: bool = False) -> float:
    return len(s) * size * (0.6 if mono else 0.53)


class Svg:
    def __init__(self, spec: dict):
        self.s = spec
        self.g = spec.get("grid", 100)
        self.W = spec["width"] * self.g
        self.H = spec["height"] * self.g
        self.out: list[str] = []
        self.nodes = {n["id"]: n for n in spec.get("nodes", [])}
        self.markers: set[str] = set()

    def px(self, v: float) -> float:
        return round(v * self.g, 1)

    def rect_of(self, n: dict) -> tuple[float, float, float, float]:
        return self.px(n["x"]), self.px(n["y"]), self.px(n["w"]), self.px(n["h"])

    def multiline(self, cx: float, cy: float, lines: list[str], size: float, color: str, weight: str = "400",
                  anchor: str = "middle", mono: bool = False) -> None:
        lh = size * 1.22
        y0 = cy - lh * (len(lines) - 1) / 2
        family = MONO if mono else FONT
        for i, ln in enumerate(lines):
            self.out.append(
                f'<text x="{cx}" y="{round(y0 + i * lh + size * 0.35, 1)}" font-family="{family}" font-size="{size}" '
                f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">'
                f"{html.escape(ln)}</text>")

    def fit(self, lines: list[str], w: float, h: float, size: float, mono: bool = False) -> float:
        while size > 9:
            widest = max((text_width(ln, size, mono) for ln in lines), default=0)
            if widest <= w - 14 and len(lines) * size * 1.22 <= h - 8:
                break
            size -= 0.5
        return size

    def lane(self, ln: dict) -> None:
        x, y, w, h = self.px(ln["x"]), self.px(ln["y"]), self.px(ln["w"]), self.px(ln["h"])
        stroke = KINDS.get(ln.get("kind", "neutral"), KINDS["neutral"])[0]
        fill = LANE_FILL.get(ln.get("kind", "neutral"), "#F7F6F2")
        self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
                        f'stroke="{stroke}" stroke-opacity="0.45" stroke-width="1.5"/>')
        if ln.get("label"):
            label = ln["label"]
            tw = text_width(label, 15) + 22
            self.out.append(f'<rect x="{x + 12}" y="{y + 10}" width="{tw}" height="26" rx="13" fill="{stroke}"/>')
            self.out.append(f'<text x="{x + 12 + tw / 2}" y="{y + 28.3}" font-family="{FONT}" font-size="15" '
                            f'font-weight="600" fill="#FFFFFF" text-anchor="middle">'
                            f"{html.escape(label)}</text>")

    def node(self, n: dict) -> None:
        x, y, w, h = self.rect_of(n)
        stroke, fill, ink = KINDS.get(n.get("kind", "neutral"), KINDS["neutral"])
        shape = n.get("shape", "box")
        mono = bool(n.get("mono"))
        if shape == "cyl":
            e = min(14, h * 0.18)
            self.out.append(
                f'<path d="M{x},{y + e} a{w / 2},{e} 0 0,0 {w},0 v{h - 2 * e} a{w / 2},{e} 0 0,1 {-w},0 z" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            self.out.append(f'<ellipse cx="{x + w / 2}" cy="{y + e}" rx="{w / 2}" ry="{e}" fill="{fill}" '
                            f'stroke="{stroke}" stroke-width="2"/>')
            ty, th = y + 2 * e, h - 2 * e
        elif shape == "note":
            self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#FFFDF5" '
                            f'stroke="{stroke}" stroke-width="1.2" stroke-dasharray="5 4"/>')
            ty, th = y, h
        else:
            rx = 18 if shape == "round" else 7
            dash = ' stroke-dasharray="7 5"' if n.get("dashed") else ""
            self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                            f'stroke="{stroke}" stroke-width="2"{dash}/>')
            ty, th = y, h
        lines = str(n.get("label", "")).split("\n")
        sub = n.get("sub")
        size = self.fit(lines + ([sub] if sub else []), w, th, n.get("size", 16), mono)
        if sub:
            sub_size = max(9.0, size * 0.78)
            block = len(lines) * size * 1.22 + sub_size * 1.25
            top = ty + th / 2 - block / 2
            self.multiline(x + w / 2, top + len(lines) * size * 1.22 / 2, lines, size, ink,
                           n.get("weight", "600"), mono=mono)
            self.multiline(x + w / 2, top + len(lines) * size * 1.22 + sub_size * 0.62, [sub], sub_size,
                           stroke, "400", mono=True)
        else:
            self.multiline(x + w / 2, ty + th / 2, lines, size, ink, n.get("weight", "600"), mono=mono)

    @staticmethod
    def side_point(r: tuple[float, float, float, float], side: str, pos: float = 0.5) -> tuple[float, float]:
        x, y, w, h = r
        return {"left": (x, y + h * pos), "right": (x + w, y + h * pos), "top": (x + w * pos, y),
                "bottom": (x + w * pos, y + h)}[side]

    def marker(self, color: str) -> str:
        mid = "arrow" + color.lstrip("#")
        if mid not in self.markers:
            self.markers.add(mid)
            self.defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                             f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
                             f'fill="{color}"/></marker>')
        return mid

    def edge(self, e: dict) -> None:
        a, b = self.nodes[e["from"]], self.nodes[e["to"]]
        ra, rb = self.rect_of(a), self.rect_of(b)
        ax, ay, aw, ah = ra
        bx, by, bw, bh = rb
        route = e.get("route", "auto")
        fs, ts = e.get("from_side"), e.get("to_side")
        if not fs or not ts:
            h_overlap = min(ax + aw, bx + bw) - max(ax, bx)
            v_overlap = min(ay + ah, by + bh) - max(ay, by)
            if h_overlap > 20 and (by >= ay + ah or by + bh <= ay):
                fs, ts = ("bottom", "top") if by >= ay + ah else ("top", "bottom")
            elif v_overlap > 10:
                fs, ts = ("right", "left") if bx >= ax + aw else ("left", "right")
            elif by >= ay + ah:
                fs, ts = "bottom", ("left" if bx >= ax + aw else "right" if bx + bw <= ax else "top")
            else:
                fs, ts = ("right", "left") if bx >= ax + aw else ("left", "right")
        p1, p2 = self.side_point(ra, fs, e.get("from_pos", 0.5)), self.side_point(rb, ts, e.get("to_pos", 0.5))
        if fs in ("top", "bottom") and ts in ("top", "bottom") and abs(p1[0] - p2[0]) < 1 and route == "auto":
            route = "straight"
        if fs in ("left", "right") and ts in ("left", "right") and abs(p1[1] - p2[1]) < 1 and route == "auto":
            route = "straight"
        pts = [p1]
        if route == "auto":
            route = ("vhv" if fs in ("top", "bottom") and ts in ("top", "bottom") else
                     "hvh" if fs in ("left", "right") and ts in ("left", "right") else
                     "vh" if fs in ("top", "bottom") else "hv")
        if route == "hv":
            pts.append((p2[0], p1[1]))
        elif route == "vh":
            pts.append((p1[0], p2[1]))
        elif route == "hvh":
            mx = self.px(e["via"]) if "via" in e else round((p1[0] + p2[0]) / 2, 1)
            pts += [(mx, p1[1]), (mx, p2[1])]
        elif route == "vhv":
            my = self.px(e["via"]) if "via" in e else round((p1[1] + p2[1]) / 2, 1)
            pts += [(p1[0], my), (p2[0], my)]
        pts.append(p2)
        style = e.get("style", "solid")
        color = e.get("color") or {"dos": "#0E7C86", "bsd": "#AB2B28", "hw": "#B7862A"}.get(e.get("kind", ""), "#4B5563")
        width = 3 if style == "thick" else 1.8
        dash = ' stroke-dasharray="7 5"' if style == "dashed" else ""
        mid = self.marker(color)
        start = f' marker-start="url(#{mid})"' if e.get("bidir") else ""
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        self.out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash} '
                        f'stroke-linejoin="round" marker-end="url(#{mid})"{start}/>')
        if e.get("label"):
            # label at the middle of the longest segment
            segs = list(zip(pts, pts[1:]))
            (sx, sy), (tx, ty) = max(segs, key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
            lx, ly = (sx + tx) / 2, (sy + ty) / 2
            lines = str(e["label"]).split("\n")
            size = e.get("size", 13)
            tw = max(text_width(ln, size, bool(e.get("mono"))) for ln in lines) + 10
            th = len(lines) * size * 1.22 + 6
            if abs(sx - tx) < 1 and not e.get("label_on_line"):  # vertical segment: label beside it
                lx += tw / 2 + 6
            self.out.append(f'<rect x="{round(lx - tw / 2, 1)}" y="{round(ly - th / 2, 1)}" width="{round(tw, 1)}" '
                            f'height="{round(th, 1)}" rx="4" fill="#FFFFFF" fill-opacity="0.92"/>')
            self.multiline(round(lx, 1), round(ly, 1), lines, size, color, "500", mono=bool(e.get("mono")))

    def note(self, n: dict) -> None:
        x, y, w = self.px(n["x"]), self.px(n["y"]), self.px(n["w"])
        lines = str(n["text"]).split("\n")
        size = n.get("size", 13)
        color = KINDS.get(n.get("kind", "neutral"), KINDS["neutral"])[2]
        anchor = n.get("align", "start")
        cx = x if anchor == "start" else x + w / 2 if anchor == "middle" else x + w
        lh = size * 1.25
        for i, ln in enumerate(lines):
            self.out.append(f'<text x="{cx}" y="{round(y + size + i * lh, 1)}" font-family="{FONT}" '
                            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
                            f'font-style="{n.get("style", "normal")}">{html.escape(ln)}</text>')

    def render(self) -> str:
        self.defs: list[str] = []
        for ln in self.s.get("lanes", []):
            self.lane(ln)
        body_lanes = self.out
        self.out = []
        for e in self.s.get("edges", []):
            self.edge(e)
        body_edges = self.out
        self.out = []
        for n in self.s.get("nodes", []):
            self.node(n)
        for n in self.s.get("notes", []):
            self.note(n)
        body_nodes = self.out
        title = html.escape(self.s.get("title", ""))
        return "\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" width="{self.W}" '
            f'height="{self.H}" role="img" aria-label="{title}">',
            f"<title>{title}</title>",
            "<defs>" + "".join(self.defs) + "</defs>",
            f'<rect x="0" y="0" width="{self.W}" height="{self.H}" fill="#FFFFFF"/>',
            *body_lanes, *body_edges, *body_nodes, "</svg>", ""])


def find_edge() -> Path | None:
    for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
              Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")):
        if p.exists():
            return p
    return None


def render_png(svg: Path, png: Path, scale: int = 2) -> None:
    import shutil
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if sys.platform == "win32" and shell:
        # Same route as build_slides.py: PowerPoint renders the SVG (headless Edge can hang on Windows).
        before = png.stat().st_mtime if png.exists() else 0
        r = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            str(ROOT / "tools" / "svg_to_png.ps1"), "-Svg", str(svg), "-OutDir", str(png.parent),
                            "-Scale", str(scale)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0 and png.exists() and png.stat().st_mtime > before:
            return
    edge = find_edge()
    if not edge:
        raise SystemExit("no PNG renderer: needs PowerPoint (Windows) or Microsoft Edge (SVG output works without)")
    text = svg.read_text(encoding="utf-8")
    import re
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', text)
    w, h = int(float(m.group(1))), int(float(m.group(2)))
    png.parent.mkdir(parents=True, exist_ok=True)
    page = png.with_suffix(".html")
    page.write_text(f'<!DOCTYPE html><html><body style="margin:0;background:#fff">{text}</body></html>',
                    encoding="utf-8")
    subprocess.run([str(edge), "--headless", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--force-device-scale-factor={scale}", f"--window-size={w},{h}",
                    f"--screenshot={png}", page.resolve().as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    page.unlink(missing_ok=True)
    if not png.exists():
        raise SystemExit(f"Edge did not write {png}")


def build(spec_path: Path, png: bool) -> Path:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    for e in spec.get("edges", []):
        for k in ("from", "to"):
            if e[k] not in {n["id"] for n in spec.get("nodes", [])}:
                raise SystemExit(f"{spec_path.name}: edge refers to unknown node {e[k]!r}")
    svg = spec_path.with_suffix(".svg")
    svg.write_text(Svg(spec).render(), encoding="utf-8", newline="\n")
    if png:
        target = PNG_DIR / (spec_path.stem + ".png")
        if not target.exists() or target.stat().st_mtime < svg.stat().st_mtime:
            render_png(svg, target)
    return svg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("specs", nargs="*", type=Path)
    ap.add_argument("--png", action="store_true", help="also render PNGs for slides into build/diagrams")
    a = ap.parse_args()
    specs = [p.resolve() for p in a.specs] or sorted(DIAGRAMS.glob("*.json"))
    for p in specs:
        out = build(p, a.png)
        print(f"{out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

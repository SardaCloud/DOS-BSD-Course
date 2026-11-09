"""Build the self-contained HTML edition of the course pack.

    python tools/build_html.py            # writes dist/students/*.html and dist/instructor/*.html

Each page needs no network access: CSS and JavaScript are inline, code is
highlighted at build time with Pygments, and colours come only from the
Clawpilot theme variables (--cp-*), with light and dark themes (the
?theme=light|dark query parameter overrides the system preference).

A fenced code block whose caption paragraph starts with **Listing, **Sketch,
**Example, **Exercise, **Template, **Solution or **Output gets that caption as
its header; listing headers are tagged MS-DOS or FreeBSD from their pinned
permalink. Relative links between Markdown files become links between the
generated pages.

Requires: markdown-it-py, pygments.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

sys.path.insert(0, str(Path(__file__).resolve().parent))
from citations import REPOS, ROOT, find_citations  # noqa: E402

DIST = ROOT / "dist"
TEMPLATE = (Path(__file__).resolve().parent / "html_template.html").read_text(encoding="utf-8")
SITE = "MS-DOS 4.00 and FreeBSD 15.1"
AUTHOR = "Francesco Valerio Buccoli"
AUTHOR_EMAIL = "francesco@buccoli.com"
CAPTION_RE = re.compile(r"^\*\*(Listing|Sketch|Example|Exercise|Template|Solution|Output)\b")
LANG_ALIASES = {"asm": None, "masm": "tasm", "x86asm": None, "nasm": "nasm", "gas": "gas", "s": "gas",
                "c": "c", "h": "c", "sh": "sh", "shell": "sh", "console": "console", "bat": "batch",
                "batch": "batch", "dosbatch": "batch", "python": "python", "py": "python", "json": "json",
                "lua": "lua", "make": "make", "makefile": "make", "ini": "ini", "conf": "ini"}
TEXT_LABELS = {"console": "Terminal", "sh": "Shell", "shell": "Shell", "bat": "Batch file",
               "batch": "Batch file", "dosbatch": "Batch file", "python": "Python", "py": "Python",
               "json": "JSON", "lua": "Lua", "ini": "Configuration", "conf": "Configuration",
               "make": "Makefile", "makefile": "Makefile", "nasm": "NASM", "c": "C", "asm": "Assembly"}


def slugify(text: str, used: dict[str, int]) -> str:
    slug = re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")
    count = used.get(slug, 0)
    used[slug] = count + 1
    return slug if count == 0 else f"{slug}-{count}"


def inline_text(token) -> str:
    return "".join(c.content for c in (token.children or []) if c.type in ("text", "code_inline"))


def out_path_for(src: Path) -> Path | None:
    src = src.resolve()
    if src == (ROOT / "README.md").resolve():
        return DIST / "students" / "index.html"
    for sub, dest in (("course", "students"), ("instructor", "instructor")):
        base = (ROOT / sub).resolve()
        if base in src.parents:
            return DIST / dest / src.relative_to(base).with_suffix(".html")
    return None


def rel_url(target: Path, from_file: Path) -> str:
    import os
    return os.path.relpath(target, from_file.parent).replace("\\", "/")


def choose_lexer(lang: str, cite_path: str | None):
    alias = LANG_ALIASES.get(lang, lang or None)
    if lang in ("asm", "x86asm", "s") or (alias is None and lang):
        if cite_path and cite_path.upper().endswith((".ASM", ".INC", ".SKL", ".EQU", ".MAC")):
            alias = "tasm"
        elif cite_path and cite_path.endswith(".S"):
            alias = "gas"
        else:
            alias = "nasm"
    if not alias or lang == "text":
        return None
    try:
        return get_lexer_by_name(alias)
    except ClassNotFound:
        return None


def build_markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "typographer": True}).enable(["table", "replacements"])
    formatter = HtmlFormatter(nowrap=True)

    def render_fence(self, tokens, idx, options, env):
        token = tokens[idx]
        lang = (token.info or "").strip().split(" ")[0].lower()
        code = token.content.rstrip("\n")
        meta = token.meta or {}
        cite = meta.get("cite")
        lexer = choose_lexer(lang, cite.path if cite else None)
        body = highlight(code, lexer, formatter).rstrip("\n") if lexer else html.escape(code)
        kind = meta.get("kind", "plain")
        env["stats"]["code"] += 1
        if kind == "listing":
            env["stats"]["listings"] += 1
        if meta.get("caption_html"):
            tag = ""
            if cite:
                cls = "tag-dos" if cite.repo == "dos" else "tag-bsd"
                label = "MS-DOS 4.00" if cite.repo == "dos" else "FreeBSD 15.1"
                tag = f'<span class="tag {cls}">{label}</span>'
            label_html = tag + meta["caption_html"]
        else:
            is_diagram = lang == "text" and re.search(r"[+|][-=]{2,}|-->|\|\s{2,}\|", code)
            label_html = html.escape("Diagram" if is_diagram else TEXT_LABELS.get(lang, "Text"))
        link = ""
        if cite and cite.start:
            link = (f'<a class="code-src" href="{html.escape(cite.text)}" target="_blank" '
                    f'rel="noopener noreferrer">Source &#8599;</a>')
        head = (f'<div class="code-head"><span class="code-label">{label_html}</span>'
                f'<span class="code-actions">{link}<button type="button" class="copy-btn" '
                f'aria-label="Copy code to clipboard">Copy</button></span></div>')
        css_kind = {"listing": "source", "sketch": "sketch"}.get(kind, "plain")
        return (f'<div class="code code-{css_kind}">{head}<pre><code class="language-{html.escape(lang or "text")}">'
                f"{body}</code></pre></div>\n")

    def render_image(self, tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet("src") or ""
        alt = self.renderInlineAsText(token.children or [], options, env)
        path = (env["src"].parent / src).resolve()
        if path.suffix.lower() == ".svg" and path.is_file():
            svg = path.read_text(encoding="utf-8")
            svg = re.sub(r"^\s*<\?xml[^>]*>\s*", "", svg)
            env["stats"]["figures"] = env["stats"].get("figures", 0) + 1
            return f'<span class="svg-figure" data-caption="{html.escape(alt)}">{svg}</span>'
        if not path.is_file():
            sys.exit(f"error: {env['src'].name}: image not found: {src}")
        return f'<img src="{html.escape(rel_url(path, env["out"]))}" alt="{html.escape(alt)}">'

    def render_link_open(self, tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet("href") or ""
        if re.match(r"https?://", href):
            token.attrSet("target", "_blank")
            token.attrSet("rel", "noopener noreferrer")
        elif href and not href.startswith("#") and not re.match(r"[a-z][a-z0-9+.-]*:", href):
            path_part, _, frag = href.partition("#")
            target = (env["src"].parent / path_part).resolve()
            mapped = out_path_for(target) if target.suffix.lower() == ".md" else None
            new = rel_url(mapped, env["out"]) if mapped else rel_url(target, env["out"])
            token.attrSet("href", new + (f"#{frag}" if frag else ""))
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("fence", render_fence)
    md.add_render_rule("link_open", render_link_open)
    md.add_render_rule("image", render_image)
    md.add_render_rule("table_open", lambda self, t, i, o, e: '<div class="table-wrap">\n<table>\n')
    md.add_render_rule("table_close", lambda self, t, i, o, e: "</table>\n</div>\n")
    return md


def attach_captions(md: MarkdownIt, tokens: list, env: dict) -> list:
    """Move caption paragraphs into the following fence's header."""
    out: list = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if (t.type == "paragraph_open" and i + 3 < len(tokens) and tokens[i + 2].type == "paragraph_close"
                and tokens[i + 3].type == "fence" and CAPTION_RE.match(tokens[i + 1].content)):
            inline, fence = tokens[i + 1], tokens[i + 3]
            caption = inline.content
            kind = CAPTION_RE.match(caption).group(1).lower()
            cites = [c for c in find_citations(caption) if c.start]
            fence.meta = {
                "caption_html": md.renderer.renderInline(inline.children, md.options, env),
                "kind": "listing" if kind == "listing" else ("sketch" if kind == "sketch" else "example"),
                "cite": cites[0] if len(cites) == 1 else None,
            }
            out.append(fence)
            i += 4
            continue
        out.append(t)
        i += 1
    return out


def build_toc(entries: list[tuple[int, str, str]]) -> str:
    out, group_open, sub_open = ['<ol class="toc-list">'], False, False
    for level, title, slug in entries:
        link = f'<a href="#{slug}">{html.escape(title)}</a>'
        if level == 2:
            if sub_open:
                out.append("</ol>")
                sub_open = False
            if group_open:
                out.append("</li>")
            out.append(f'<li class="toc-group">{link}')
            group_open = True
        else:
            if not sub_open:
                out.append('<ol class="toc-sub">')
                sub_open = True
            out.append(f"<li>{link}</li>")
    if sub_open:
        out.append("</ol>")
    if group_open:
        out.append("</li>")
    out.append("</ol>")
    return "\n".join(out)


def page_stats(text: str) -> dict:
    return {
        "words": len(re.findall(r"\w+", text)),
        "listings": len(re.findall(r"^\*\*Listing", text, re.M)),
        "exercises": len(re.findall(r"^#{2,3} Exercise \d", text, re.M)),
        "cases": len(re.findall(r"^### Study case", text, re.M)),
    }


FOOTER = """<p>Course text &copy; 2026 Francesco Valerio Buccoli (<a href="mailto:francesco@buccoli.com">francesco@buccoli.com</a>), MIT License. A <a href="https://www.sardacloud.com" target="_blank" rel="noopener noreferrer">Sarda Cloud</a> Community project. Generated on %%BUILT%% by <code>tools/build_html.py</code>. Nothing is loaded from the network.</p>
<p>Source excerpts are quoted for teaching, each linked to its exact lines: MS-DOS 4.00 &copy; Microsoft Corporation,
MIT License (<a href="https://github.com/microsoft/MS-DOS/blob/%%DOS%%/LICENSE" target="_blank" rel="noopener noreferrer">microsoft/MS-DOS @ %%DOS7%%</a>);
FreeBSD &copy; The FreeBSD Project and contributors, BSD licences (<a href="https://github.com/freebsd/freebsd-src/blob/%%BSD%%/COPYRIGHT" target="_blank" rel="noopener noreferrer">freebsd/freebsd-src @ release/15.1.0</a>).
MS-DOS is a trademark of Microsoft Corporation; FreeBSD is a registered trademark of The FreeBSD Foundation.
See THIRD_PARTY_NOTICES.md.</p>"""


def render_page(md: MarkdownIt, src: Path, out: Path, nav: tuple[Path | None, Path | None],
                edition: str, extra_body: str = "") -> dict:
    text = src.read_text(encoding="utf-8")
    env = {"src": src, "out": out, "stats": {"code": 0, "listings": 0}}
    tokens = attach_captions(md, md.parse(text, env), env)
    used: dict[str, int] = {}
    toc: list[tuple[int, str, str]] = []
    h1 = ""
    for i, t in enumerate(tokens):
        if t.type == "heading_open":
            title = inline_text(tokens[i + 1])
            slug = slugify(title, used)
            t.attrSet("id", slug)
            if t.tag == "h1" and not h1:
                h1 = title
            elif t.tag in ("h2", "h3"):
                toc.append((int(t.tag[1]), title, slug))
    body = md.renderer.render(tokens, md.options, env)
    # A paragraph that holds only a diagram becomes a figure; the image's alt text is the caption.
    body = re.sub(r'<p><span class="svg-figure" data-caption="([^"]*)">(.*?</svg>)\s*</span></p>',
                  lambda m: (f'<figure class="figure diagram">{m.group(2)}'
                             + (f'<figcaption>{m.group(1)}</figcaption>' if m.group(1) else "") + "</figure>"),
                  body, flags=re.S)
    body = re.sub(r'<h([2-4]) id="([^"]+)">(.*?)</h\1>',
                  lambda m: (f'<h{m.group(1)} id="{m.group(2)}">{m.group(3)}<a class="anchor" '
                             f'href="#{m.group(2)}" aria-label="Link to this section">#</a></h{m.group(1)}>'),
                  body, flags=re.S)
    m = re.match(r'\s*<h1 id="([^"]+)">(.*?)</h1>\s*(?:<p>(.*?)</p>)?', body, re.S)
    if not m:
        sys.exit(f"error: {src} must start with an H1")
    h1_id, h1_html, lede = m.group(1), m.group(2), m.group(3) or ""
    body = body[m.end():]
    kicker_txt, _, title_txt = h1_html.partition(": ")
    if not title_txt:
        kicker_txt, title_txt = SITE, h1_html
    st = page_stats(text)
    chips = [f'<span class="chip">MS-DOS <b>{REPOS["dos"]["sha"][:7]}</b></span>',
             f'<span class="chip">FreeBSD <b>release/15.1.0</b></span>']
    if st["listings"]:
        chips.append(f'<span class="chip"><b>{st["listings"]}</b> source listings</span>')
    if st["cases"]:
        chips.append(f'<span class="chip"><b>{st["cases"]}</b> study cases</span>')
    if st["exercises"]:
        chips.append(f'<span class="chip"><b>{st["exercises"]}</b> exercises</span>')
    chips.append(f'<span class="chip">about <b>{max(5, round(st["words"] / 200 / 5) * 5)}</b> min read</span>')
    banner = ('<div class="instructor-banner">Instructor edition: model answers, rubrics and teaching notes. '
              'Do not distribute to students.</div>') if edition == "instructor" else ""
    hero = (f'<header class="hero"><div class="kicker">{kicker_txt}</div><h1 id="{h1_id}">{title_txt}</h1>'
            f'<p class="lede">{lede}</p><div class="chips">{"".join(chips)}</div>'
            f'<div class="author-line">{AUTHOR} &middot; <a href="mailto:{AUTHOR_EMAIL}">{AUTHOR_EMAIL}</a></div>'
            f'{banner}</header>')
    prev, nxt = nav
    nav_html = ""
    if prev or nxt:
        def nav_link(p: Path | None, arrow: str) -> str:
            if not p:
                return "<span></span>"
            title = p.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
            return f'<a href="{rel_url(out_path_for(p), out)}">{arrow} {html.escape(title)}</a>'
        nav_html = f'<nav class="module-nav">{nav_link(prev, "&#8592;")}{nav_link(nxt, "&#8594;")}</nav>'
    built = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    plain_title = re.sub(r"<[^>]+>", "", h1_html)
    page = (TEMPLATE.replace("%%TITLE%%", html.escape(plain_title))
            .replace("%%SITE%%", SITE)
            .replace("%%DESCRIPTION%%", html.escape(re.sub(r"<[^>]+>", "", lede))[:300])
            .replace("%%TOC%%", build_toc(toc))
            .replace("%%HERO%%", hero)
            .replace("%%BODY%%", body + extra_body + nav_html)
            .replace("%%FOOTER%%", FOOTER.replace("%%BUILT%%", built).replace("%%DOS%%", REPOS["dos"]["sha"])
                     .replace("%%DOS7%%", REPOS["dos"]["sha"][:7]).replace("%%BSD%%", REPOS["bsd"]["sha"])))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
    st.update(env["stats"], title=plain_title, lede=re.sub(r"<[^>]+>", "", lede), out=out)
    return st


def cards(pages: list[dict], index_out: Path) -> str:
    items = []
    for p in pages:
        kicker, _, title = p["title"].partition(": ")
        if not title:
            kicker, title = "", p["title"]
        meta = " &middot; ".join(x for x in (
            f'{p["listings"]} listings' if p["listings"] else "",
            f'{p["cases"]} study cases' if p["cases"] else "",
            f'{p["exercises"]} exercises' if p["exercises"] else "",
            f'{p["words"]:,} words') if x)
        items.append(f'<a class="card" href="{rel_url(p["out"], index_out)}"><div class="card-kicker">'
                     f'{html.escape(kicker)}</div><div class="card-title">{html.escape(title)}</div>'
                     f'<div class="card-meta">{meta}</div></a>')
    return f'<h2 id="pages">Pages</h2>\n<div class="cards">{"".join(items)}</div>\n'


def main() -> int:
    md = build_markdown()
    course = sorted((ROOT / "course").glob("*.md"))
    solutions = sorted((ROOT / "instructor").glob("*.md"))
    student_pages = []
    for i, src in enumerate(course):
        nav = (course[i - 1] if i else None, course[i + 1] if i + 1 < len(course) else None)
        student_pages.append(render_page(md, src, out_path_for(src), nav, "students"))
    instructor_pages = []
    for i, src in enumerate(solutions):
        nav = (solutions[i - 1] if i else None, solutions[i + 1] if i + 1 < len(solutions) else None)
        instructor_pages.append(render_page(md, src, out_path_for(src), nav, "instructor"))
    readme = ROOT / "README.md"
    if readme.exists():
        idx = DIST / "students" / "index.html"
        render_page(md, readme, idx, (None, None), "students", cards(student_pages, idx))
        if instructor_pages:
            iidx = DIST / "instructor" / "index.html"
            render_page(md, readme, iidx, (None, None), "instructor",
                        cards(instructor_pages + student_pages, iidx))
    for p in student_pages + instructor_pages:
        print(f'{p["out"].relative_to(ROOT)}: {p["words"]:,} words, {p["listings"]} listings, '
              f'{p["code"]} code blocks, {p["exercises"]} exercises')
    return 0


if __name__ == "__main__":
    sys.exit(main())

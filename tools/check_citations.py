"""Verify every source citation and listing in the course pack.

    python tools/check_citations.py                 # check all course Markdown
    python tools/check_citations.py course/01-boot.md
    python tools/check_citations.py --excerpt dos v4.0/src/BOOT/MSBOOT.ASM 120 135

--excerpt prints the exact lines (tabs expanded) plus a ready-made caption, so
listings can be pasted rather than retyped.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from citations import ELISION_RE, REPOS, ROOT, find_citations, norm, permalink, read_lines  # noqa: E402

FENCE_RE = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
CODE_LANGS = {"asm", "masm", "nasm", "gas", "s", "c", "h", "x86asm"}


def default_files() -> list[Path]:
    files = [ROOT / "README.md"]
    for sub in ("course", "instructor"):
        files += sorted((ROOT / sub).rglob("*.md"))
    return [f for f in files if f.exists()]


def match_listing(body: list[str], src: list[str], start: int, end: int) -> str | None:
    if start < 1 or end > len(src) or start > end:
        return f"range L{start}-L{end} outside file (1-{len(src)})"
    window = [norm(x) for x in src[start - 1:end]]
    segments: list[list[str]] = [[]]
    for line in body:
        if ELISION_RE.match(line):
            segments.append([])
        else:
            segments[-1].append(norm(line))
    if len(segments) == 1:
        seg = segments[0]
        if seg == window:
            return None
        for i, (a, b) in enumerate(zip(seg, window)):
            if a != b:
                return f"line {start + i}: listing has {a!r}, source has {b!r}"
        return f"listing has {len(seg)} lines, range has {len(window)}"
    if any(not s for s in segments):
        return "empty segment around an elision marker"
    pos = 0
    for idx, seg in enumerate(segments):
        if idx == 0:
            if window[:len(seg)] != seg:
                return f"first segment does not start at L{start}"
            pos = len(seg)
            continue
        found = -1
        for j in range(pos + 1, len(window) - len(seg) + 1):
            if window[j:j + len(seg)] == seg:
                found = j
                if idx < len(segments) - 1:
                    break
        if idx == len(segments) - 1:
            if window[len(window) - len(seg):] != seg or len(window) - len(seg) <= pos:
                return f"last segment does not end at L{end} (or no lines elided before it)"
            pos = len(window)
        else:
            if found < 0:
                return f"segment {idx + 1} ({seg[0]!r}...) not found in order"
            pos = found + len(seg)
    return None


def check_file(md: Path) -> tuple[int, int, list[str]]:
    errors: list[str] = []
    rel = md.relative_to(ROOT)
    lines = md.read_text(encoding="utf-8").split("\n")
    n_links = n_listings = 0

    for i, line in enumerate(lines, 1):
        for c in find_citations(line):
            n_links += 1
            info = REPOS[c.repo]
            if c.ref != info["sha"]:
                errors.append(f"{rel}:{i}: link not pinned to {info['sha'][:10]} ({c.ref})")
                continue
            p = c.local_path
            if not p.exists():
                errors.append(f"{rel}:{i}: {info['label']} path not found locally: {c.path}")
                continue
            if c.kind.lower() == "tree":
                if not p.is_dir():
                    errors.append(f"{rel}:{i}: tree link to a file: {c.path}")
                continue
            if p.is_dir():
                errors.append(f"{rel}:{i}: blob link to a directory: {c.path}")
                continue
            if c.start:
                n = len(read_lines(p))
                if c.start < 1 or c.end > n or c.start > c.end:
                    errors.append(f"{rel}:{i}: L{c.start}-L{c.end} outside {c.path} (1-{n})")

    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        fence, info_str = m["fence"], m["info"].strip()
        j = i + 1
        while j < len(lines) and not re.match(rf"^\s{{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$", lines[j]):
            j += 1
        body = lines[i + 1:j]
        k = i - 1
        while k >= 0 and not lines[k].strip():
            k -= 1
        para_end = k
        while k >= 0 and lines[k].strip():
            k -= 1
        caption = "\n".join(lines[k + 1:para_end + 1]).strip()
        lang = info_str.split()[0].lower() if info_str else ""
        if caption.startswith("**Listing"):
            n_listings += 1
            cites = [c for c in find_citations(caption) if c.start]
            if len(cites) != 1:
                errors.append(f"{rel}:{i + 1}: listing caption needs exactly one line-ranged citation (found {len(cites)})")
            else:
                c = cites[0]
                if c.local_path.is_file() and c.ref == REPOS[c.repo]["sha"]:
                    err = match_listing(body, read_lines(c.local_path), c.start, c.end)
                    if err:
                        errors.append(f"{rel}:{i + 1}: listing vs {c.path}: {err}")
        elif lang in CODE_LANGS and not re.match(r"^\*\*(Sketch|Example|Exercise|Template|Solution|Output)", caption):
            errors.append(f"{rel}:{i + 1}: {lang} block without a **Listing/**Sketch/**Example caption")
        i = j + 1
    return n_links, n_listings, errors


def excerpt(repo: str, path: str, start: int, end: int) -> None:
    src = read_lines(REPOS[repo]["local"] / path)
    url = permalink(repo, path, start, end)
    name = path.rsplit("/", 1)[-1]
    print(f"**Listing X.Y** -- [`{name}` lines {start}-{end}]({url})\n")
    print("```")
    for ln in src[start - 1:end]:
        print(norm(ln))
    print("```")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--excerpt", nargs=4, metavar=("REPO", "PATH", "START", "END"))
    a = ap.parse_args()
    if a.excerpt:
        r, p, s, e = a.excerpt
        excerpt(r, p, int(s), int(e))
        return 0
    files = [f.resolve() for f in a.files] or default_files()
    total_l = total_x = 0
    all_err: list[str] = []
    for f in files:
        nl, nx, errs = check_file(f)
        total_l += nl
        total_x += nx
        all_err += errs
    for e in all_err:
        print(e)
    print(f"{len(files)} files, {total_l} citations, {total_x} listings, {len(all_err)} errors")
    return 1 if all_err else 0


if __name__ == "__main__":
    sys.exit(main())

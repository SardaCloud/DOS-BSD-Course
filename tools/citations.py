"""Shared helpers for source citations in the course pack.

A citation is a GitHub permalink to one of the two pinned repositories, e.g.
https://github.com/microsoft/MS-DOS/blob/<sha>/v4.0/src/BOOT/MSBOOT.ASM#L120-L135

A *listing* is a fenced code block whose caption paragraph (the closest
non-blank line above the fence) starts with "**Listing" and contains exactly
one citation with a line range. Its body must match those source lines. A line
holding only the elision marker "⋮" (optionally indented or commented) stands
for one or more omitted source lines.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "src-ext"

REPOS = {
    "dos": {
        "slug": "microsoft/MS-DOS",
        "sha": "2d04cacc5322951f187bb17e017c12920ac8ebe2",
        "local": EXT / "MS-DOS",
        "label": "MS-DOS",
    },
    "bsd": {
        "slug": "freebsd/freebsd-src",
        "sha": "96841ea08dcfa84b954a32dc5ae1a26c28966cf4",
        "local": EXT / "freebsd-src",
        "label": "FreeBSD",
    },
}
SLUG_TO_KEY = {v["slug"].lower(): k for k, v in REPOS.items()}

LINK_RE = re.compile(
    r"https://github\.com/(?P<slug>microsoft/MS-DOS|freebsd/freebsd-src)/(?P<kind>blob|tree)/"
    r"(?P<ref>[^/\s)]+)/(?P<path>[^#\s)]+)(?:#L(?P<start>\d+)(?:-L(?P<end>\d+))?)?",
    re.IGNORECASE,
)
ELISION_RE = re.compile(r"^\s*(?:;|//|#|\*)?\s*⋮\s*$")


@dataclass
class Citation:
    repo: str
    ref: str
    path: str
    start: int | None
    end: int | None
    kind: str
    text: str

    @property
    def local_path(self) -> Path:
        return REPOS[self.repo]["local"] / self.path


def permalink(repo: str, path: str, start: int | None = None, end: int | None = None) -> str:
    info = REPOS[repo]
    url = f"https://github.com/{info['slug']}/blob/{info['sha']}/{path}"
    if start:
        url += f"#L{start}" + (f"-L{end}" if end and end != start else "")
    return url


def find_citations(text: str) -> list[Citation]:
    out = []
    for m in LINK_RE.finditer(text):
        start = int(m["start"]) if m["start"] else None
        end = int(m["end"]) if m["end"] else start
        out.append(Citation(SLUG_TO_KEY[m["slug"].lower()], m["ref"], m["path"], start, end, m["kind"], m[0]))
    return out


_cache: dict[Path, list[str]] = {}


def read_lines(path: Path) -> list[str]:
    """Return the file's lines the way GitHub numbers them (split on LF)."""
    if path not in _cache:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp437")
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        _cache[path] = [ln.rstrip("\r") for ln in lines]
    return _cache[path]


def norm(line: str) -> str:
    return line.replace("\x1a", "").expandtabs(8).rstrip()

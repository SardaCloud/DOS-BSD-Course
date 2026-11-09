"""Lab 8.5: a model of rcorder(8) in Python, to check your hand-made ordering of rc.d scripts.

    python labs/08-memconfig/rcorder.py build/freebsd/root/etc/rc.d/*            (shell expands *)
    python labs/08-memconfig/rcorder.py --dir build/freebsd/root/etc/rc.d -s nostart -s firstboot
    python labs/08-memconfig/rcorder.py --dir DIR --why sshd                       (dependency chain)

It reads the PROVIDE/REQUIRE/BEFORE/KEYWORD block of each file with the rules of
sbin/rcorder/rcorder.c (crunch_file: the block ends at the first other line once it has
started) and computes the "sequence" that rcorder 15.1 gives every file: 1 + the largest
sequence among the providers of everything the file requires; BEFORE: X makes every
provider of X require this file. Like `rcorder -p`, it prints one line per sequence number.
rcorder itself prints the files sorted by sequence with qsort(3), so the order of files
that share a sequence number is not specified; compare sets, not positions.
This is a teaching model, not a replacement: cycles are reported, not broken the way
rcorder breaks them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TAGS = {"# REQUIRE:": "require", "# REQUIRES:": "require", "# PROVIDE:": "provide",
        "# PROVIDES:": "provide", "# BEFORE:": "before", "# KEYWORD:": "keyword", "# KEYWORDS:": "keyword"}


def crunch(path: Path) -> dict[str, list[str]]:
    info = {"require": [], "provide": [], "before": [], "keyword": []}
    started = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for tag, field in TAGS.items():
            if line.startswith(tag):
                info[field] += line[len(tag):].split()
                started = True
                break
        else:
            if started:
                break
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--dir", type=Path, help="use every regular file in this directory")
    ap.add_argument("-s", action="append", default=[], metavar="KEYWORD", help="skip files with this keyword")
    ap.add_argument("-k", action="append", default=[], metavar="KEYWORD", help="keep only files with this keyword")
    ap.add_argument("--why", metavar="FILE", help="print the longest REQUIRE chain that ends in FILE")
    a = ap.parse_args()
    files = list(a.files) + (sorted(p for p in a.dir.iterdir() if p.is_file()) if a.dir else [])
    nodes = {p.name: crunch(p) for p in files}
    providers: dict[str, list[str]] = {}
    for name, info in nodes.items():
        for cond in info["provide"]:
            providers.setdefault(cond, []).append(name)
    deps: dict[str, set[str]] = {name: set() for name in nodes}
    # rcorder enters every REQUIRE'd condition in its table (add_require), so a BEFORE: on a
    # condition that some file requires is silent even if nobody provides it (insert_before).
    known = set(providers) | {c for info in nodes.values() for c in info["require"]}
    for name, info in nodes.items():
        for cond in info["require"]:
            if cond not in providers:
                print(f"rcorder model: requirement `{cond}' in file `{name}' has no providers.", file=sys.stderr)
            deps[name].update(providers.get(cond, []))
        for cond in info["before"]:
            if cond not in known:
                print(f"rcorder model: file `{name}' is before unknown provision `{cond}'", file=sys.stderr)
                known.add(cond)
            for p in providers.get(cond, []):
                deps[p].add(name)
    seq: dict[str, int] = {}
    via: dict[str, str | None] = {}
    state: dict[str, int] = {}

    def visit(n: str) -> int:
        if state.get(n) == 2:
            return seq[n]
        if state.get(n) == 1:
            print(f"rcorder model: circular dependency on file `{n}'.", file=sys.stderr)
            return 0
        state[n] = 1
        best, best_dep = 0, None
        for d in sorted(deps[n]):
            s = visit(d)
            if s > best:
                best, best_dep = s, d
        seq[n], via[n] = best + 1, best_dep
        state[n] = 2
        return seq[n]

    for n in nodes:
        visit(n)
    if a.why:
        chain, n = [], a.why
        while n:
            chain.append(f"{n}({seq[n]})")
            n = via[n]
        print(" <- ".join(chain))
        return 0
    keep = [n for n in nodes
            if not set(nodes[n]["keyword"]) & set(a.s) and (not a.k or set(nodes[n]["keyword"]) & set(a.k))]
    for level in sorted({seq[n] for n in keep}):
        print(f"{level:3}: " + " ".join(sorted(n for n in keep if seq[n] == level)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

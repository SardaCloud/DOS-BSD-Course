"""Lab 8.2: boot MS-DOS 4.00 once per CONFIG.SYS variant and tabulate what MEM reports.

    python labs/08-memconfig/price.py                       # all variants in labs/08-memconfig/cfg
    python labs/08-memconfig/price.py cfg/C02BUF30.SYS      # only some (paths relative to this folder)

Every run boots a fresh copy of the lab image (tools/dos_run.py) with the variant installed as
A:\\CONFIG.SYS and runs MEM /PROGRAM. The first row is always a boot without CONFIG.SYS. The raw
MEM output of every run is saved in build/lab08-price/ so that you can explain each delta.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "build" / "lab08-price"


def run(config: Path | None) -> str:
    target = f"A:\\CONFIG.SYS={config if config else ''}"
    cmd = [sys.executable, str(ROOT / "tools" / "dos_run.py"), "--timeout", "60", "--file", target, "MEM /PROGRAM"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return res.stdout


def number(pattern: str, text: str) -> int | None:
    m = re.search(r"(\d+) (?:bytes )?" + pattern, text)
    return int(m.group(1)) if m else None


def main() -> int:
    configs = [Path(a) if Path(a).is_absolute() else HERE / a for a in sys.argv[1:]]
    configs = configs or sorted((HERE / "cfg").glob("*.SYS"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    base = None
    print(f"{'config':9} {'lines':44} {'largest':>8} {'delta':>7} {'ext':>9} {'ems':>7}")
    for cfg in [None, *configs]:
        name = cfg.stem if cfg else "NONE"
        text = run(cfg)
        (OUT / f"{name}.txt").write_text(text, encoding="utf-8")
        largest = number("largest executable program size", text)
        ext = number("available extended memory", text)
        ems = number("free EMS memory", text)
        lines = " + ".join(cfg.read_text(encoding="ascii").splitlines()) if cfg else "(no CONFIG.SYS)"
        if base is None:
            base = largest
        delta = (base - largest) if (base is not None and largest is not None) else None
        rows.append((name, lines, largest, delta, ext, ems))
        print(f"{name:9} {lines:44} {largest!s:>8} {delta!s:>7} {ext!s:>9} {ems!s:>7}", flush=True)
    print(f"\nlargest = MEM 'largest executable program size'; delta = bytes of conventional memory the line "
          f"costs compared with no CONFIG.SYS; ext/ems = available extended / free EMS bytes. Raw output: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

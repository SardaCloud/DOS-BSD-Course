"""Build MS-DOS 4.00 from source in DOSBox-X, unattended.

    python tools/build_dos.py [--dosbox PATH] [--timeout SECONDS]

Runs tools/prepare_dos_build.py (fresh copy of the source in build/dos4), then
DOSBox-X with build/dos4 mounted as D: running BUILD.BAT, waits for the build
log's final marker, and reports errors and the outputs listed in CPY.BAT.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "build" / "dos4"
DEFAULT_DOSBOX = ROOT / "build" / "tools" / "dosbox-x" / "bin" / "x64" / "Release" / "dosbox-x.exe"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dosbox")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    dosbox = next((Path(c) for c in (a.dosbox, os.environ.get("DOSBOX_X"), str(DEFAULT_DOSBOX),
                                     shutil.which("dosbox-x")) if c and Path(c).is_file()), None)
    if not dosbox:
        raise SystemExit("DOSBox-X not found: pass --dosbox or set DOSBOX_X")

    subprocess.run([sys.executable, str(ROOT / "tools" / "prepare_dos_build.py"), str(DEST)], check=True)
    log = DEST / "BUILD.LOG"
    with tempfile.TemporaryDirectory(prefix="dosbuild-") as tmp:
        conf = Path(tmp) / "build.conf"
        conf.write_text("\n".join([
            "[sdl]", "autolock=false", "[dosbox]", "memsize=16", "[cpu]", "core=dynamic",
            "cputype=pentium", "cycles=max", "[dos]", "ver=4.0", "[autoexec]",
            f'mount d "{DEST}"', "d:", "call BUILD.BAT", "exit", ""]), encoding="ascii")
        start = time.monotonic()
        proc = subprocess.Popen([str(dosbox), "-silent", "-nomenu", "-fastlaunch",
                                 "-time-limit", str(a.timeout), "-conf", str(conf)])
        try:
            while proc.poll() is None:
                if log.exists() and "===== done" in log.read_text(encoding="cp437", errors="replace"):
                    break
                time.sleep(5)
        finally:
            if proc.poll() is None:
                time.sleep(2)
                proc.terminate()
                proc.wait(10)
        minutes = (time.monotonic() - start) / 60

    text = log.read_text(encoding="cp437", errors="replace") if log.exists() else ""
    errors = [ln.strip() for ln in text.splitlines()
              if re.search(r"error [A-Z]\d{4}|fatal error|NMAKE : |Bad command", ln)
              or (re.search(r"Severe\s+Errors", ln) and not re.match(r"\s*0 Severe", ln))]
    outputs = [ln.split()[1][2:] for ln in (DEST / "SRC" / "CPY.BAT").read_text(encoding="ascii").splitlines()
               if ln.lower().startswith("copy .\\")]
    missing = [o for o in outputs if not (DEST / "SRC" / o).exists()]
    done = "===== done" in text
    print(f"build {'finished' if done else 'DID NOT FINISH'} in {minutes:.1f} min; "
          f"{len(errors)} error lines; {len(outputs) - len(missing)}/{len(outputs)} CPY.BAT outputs present")
    for e in errors[:20]:
        print("  ", e)
    if missing:
        print("missing:", ", ".join(missing))
    return 0 if done and not errors and not missing else 1


if __name__ == "__main__":
    sys.exit(main())

"""Run the 1988 Microsoft toolchain from the MS-DOS 4.00 source tree (MASM 5.10, C 5.10, LINK, LIB,
EXE2BIN, NMAKE) in DOSBox-X, on files in a directory of your computer.

    python tools/dos_tools.py --dir labs/hello "CL /c /Fc HELLO.C" "LINK HELLO;"
    python tools/dos_tools.py --dir labs/hello "MASM HELLO;" "LINK HELLO;" "EXE2BIN HELLO HELLO.COM"

The directory is mounted as drive D: (the current drive), the toolchain from build/dos4/SRC/TOOLS
as drive T:. INCLUDE and LIB point at the C compiler's headers and libraries (T:\\BLD\\INC and
T:\\BLD\\LIB), the same corrected settings the MS-DOS build uses (see course/00-lab.md). Each
command's output (standard output and standard error) is printed. The programs you build are DOS
programs: run them on the real MS-DOS 4.00 with tools/dos_run.py --file.

The tools run on DOSBox-X's built-in DOS, not on the MS-DOS 4.00 we built: the toolchain is about
1.5 MB and does not fit on the lab floppy next to the system.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "build" / "dos4" / "SRC" / "TOOLS"
DEFAULT_DOSBOX = ROOT / "build" / "tools" / "dosbox-x" / "bin" / "x64" / "Release" / "dosbox-x.exe"
END = "=== DOS_TOOLS DONE ==="


def find_dosbox(arg: str | None) -> Path:
    for cand in (arg, os.environ.get("DOSBOX_X"), str(DEFAULT_DOSBOX), shutil.which("dosbox-x")):
        if cand and Path(cand).is_file():
            return Path(cand)
    raise SystemExit("DOSBox-X not found: pass --dosbox or set DOSBOX_X")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("commands", nargs="+", help="DOS command lines, run in order on drive D:")
    ap.add_argument("--dir", type=Path, required=True, help="directory mounted as D: (created if missing)")
    ap.add_argument("--dosbox")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()
    if not (TOOLS / "CL.EXE").exists():
        raise SystemExit("toolchain not found: run tools/build_dos.py first (it prepares build/dos4)")
    work = a.dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    dosbox = find_dosbox(a.dosbox)
    out = work / "_TOOLS.LOG"
    out.unlink(missing_ok=True)
    lines = ["@ECHO OFF", "SET PATH=T:\\;Z:\\", "SET INCLUDE=T:\\BLD\\INC", "SET LIB=T:\\BLD\\LIB",
             "SET INIT=T:\\", "SET CL=", "SET LINK=", "SET MASM=", "D:"]
    for cmd in a.commands:
        shown = cmd.replace("|", "!").replace(">", "}").replace("<", "{")
        lines.append(f"ECHO ---- {shown}>>D:\\_TOOLS.LOG")
        lines.append(f"{cmd} >>D:\\_TOOLS.LOG")
    lines.append(f"ECHO {END}>>D:\\_TOOLS.LOG")
    with tempfile.TemporaryDirectory(prefix="dostools-") as tmp:
        tmp = Path(tmp)
        (tmp / "RUN.BAT").write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))
        conf = tmp / "tools.conf"
        conf.write_text("\n".join([
            "[sdl]", "autolock=false", "[dosbox]", "memsize=16", "[cpu]", "core=dynamic", "cputype=pentium",
            "cycles=max", "[dos]", "ver=4.0", "[autoexec]", f'mount t "{TOOLS}"', f'mount d "{work}"',
            f'mount e "{tmp}"', "call E:\\RUN.BAT", "exit", ""]), encoding="ascii")
        proc = subprocess.Popen([str(dosbox), "-silent", "-nomenu", "-fastlaunch", "-time-limit",
                                 str(a.timeout), "-conf", str(conf)])
        try:
            deadline = time.monotonic() + a.timeout + 5
            while proc.poll() is None and time.monotonic() < deadline:
                if out.exists() and END in out.read_text(encoding="cp437", errors="replace"):
                    break
                time.sleep(0.5)
        finally:
            if proc.poll() is None:
                time.sleep(0.5)
                proc.terminate()
                proc.wait(10)
    text = out.read_text(encoding="cp437", errors="replace") if out.exists() else ""
    out.unlink(missing_ok=True)
    sys.stdout.write(text.replace(END, "").rstrip() + "\n")
    return 0 if END in text else 1


if __name__ == "__main__":
    sys.exit(main())

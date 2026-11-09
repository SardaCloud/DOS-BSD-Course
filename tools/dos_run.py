"""Boot MS-DOS 4.00 (built from source) in DOSBox-X: interactively, or to run commands.

Interactive session on a persistent disk image (created on first use):

    python tools/dos_run.py
    python tools/dos_run.py --image build/images/mydisk.img

Unattended: run command lines in the booted system and print their output:

    python tools/dos_run.py "VER" "MEM" "DIR | SORT"
    python tools/dos_run.py --file A:\\HELLO.COM=hello.com "HELLO" --keep after.img

In unattended mode each command runs from a generated AUTOEXEC.BAT on a fresh
copy of the disk, with its standard output redirected to COM1; DOSBox-X writes
COM1 to a file, which this script prints. A command that contains '>' keeps its
own redirection. --file puts extra files in the root directory and --keep saves
the disk image afterwards.

Two consequences of running from AUTOEXEC.BAT: to run a batch file of your own,
use "CALL NAME" or "COMMAND /C NAME" (a plain "NAME" never returns, so the
commands after it and the end marker do not run); and output travels at the
serial port's speed, about 240 bytes per second, so for large outputs redirect
to a file, use --keep, and read the file from the saved image.

The emulated machine is fixed (16 MB of memory, a Pentium-class CPU) unless you
change it with --conf-extra SECTION.KEY=VALUE, which overrides or adds one
DOSBox-X setting (repeatable), for example to boot a 286 with 1 MB:

    python tools/dos_run.py --conf-extra cpu.cputype=286 --conf-extra dosbox.memsize=1 "MEM"

DOSBox-X is found via --dosbox, the DOSBOX_X environment variable,
build/tools/dosbox-x, or the PATH (see course/00-lab.md).
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
DEFAULT_DOSBOX = ROOT / "build" / "tools" / "dosbox-x" / "bin" / "x64" / "Release" / "dosbox-x.exe"
DEFAULT_IMAGE = ROOT / "build" / "images" / "dos400.img"
END_MARK = "=== DOS_RUN DONE ==="


def find_dosbox(arg: str | None) -> Path:
    for cand in (arg, os.environ.get("DOSBOX_X"), str(DEFAULT_DOSBOX), shutil.which("dosbox-x")):
        if cand and Path(cand).is_file():
            return Path(cand)
    raise SystemExit("DOSBox-X not found: pass --dosbox or set DOSBOX_X")


def make_image(out: Path, autoexec: Path | None, files: list[str]) -> None:
    cmd = [sys.executable, str(ROOT / "tools" / "make_floppy.py"), "--out", str(out)]
    if autoexec:
        cmd += ["--autoexec", str(autoexec)]
    for f in files:
        cmd += ["--extra", f]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def apply_conf_extra(lines: list[str], extra: list[str]) -> list[str]:
    """Override or add DOSBox-X settings given as SECTION.KEY=VALUE (for example cpu.cputype=286)."""
    lines = list(lines)
    for item in extra:
        name, sep, value = item.partition("=")
        section, dot, key = name.strip().partition(".")
        if not sep or not dot or not section or not key or section.lower() == "autoexec":
            raise SystemExit(f"--conf-extra expects SECTION.KEY=VALUE, e.g. cpu.cputype=286: {item!r}")
        section, key = section.strip().lower(), key.strip().lower()
        header = f"[{section}]"
        if header not in lines:
            lines += [header, f"{key}={value.strip()}"]
            continue
        i = lines.index(header) + 1
        while i < len(lines) and not lines[i].startswith("["):
            if lines[i].partition("=")[0].strip().lower() == key:
                del lines[i]
                break
            i += 1
        lines.insert(lines.index(header) + 1, f"{key}={value.strip()}")
    return lines


def write_conf(path: Path, image: Path, com1: Path | None, extra: list[str] | None = None) -> None:
    lines = ["[sdl]", "autolock=false", "[dosbox]", "memsize=16", "[cpu]", "cputype=pentium", "cycles=max"]
    if com1:
        lines += ["[serial]", f"serial1=file file:{com1}"]
    if extra:
        lines = apply_conf_extra(lines, extra)
    lines += ["[autoexec]", f'imgmount a "{image}" -t floppy', "boot a:", ""]
    path.write_text("\n".join(lines), encoding="ascii")


def interactive(a, dosbox: Path) -> int:
    image = a.image or DEFAULT_IMAGE
    if not image.exists():
        image.parent.mkdir(parents=True, exist_ok=True)
        make_image(image, None, a.file)
        print(f"created {image}")
    elif a.file:
        raise SystemExit("--file only works when the image is created; delete the image or use unattended mode")
    with tempfile.TemporaryDirectory(prefix="dosrun-") as tmp:
        conf = Path(tmp) / "boot.conf"
        write_conf(conf, image.resolve(), None, a.conf_extra)
        print(f"booting {image} (changes are saved to the image; close the window to stop)")
        return subprocess.call([str(dosbox), "-fastlaunch", "-conf", str(conf)])


def unattended(a, dosbox: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="dosrun-") as tmp:
        tmp = Path(tmp)
        lines = ["@ECHO OFF", "PATH A:\\"]
        for cmd in a.commands:
            # DOS 4.00 has no escape character, so pipes and redirections are shown in words.
            shown = cmd.replace("|", " (pipe) ").replace(">", " (to) ").replace("<", " (from) ")
            # No space before ">COM1": COMMAND.COM keeps it in the command tail ("SET X=1 >COM1" sets "1 ").
            lines.append(f"ECHO ---- {shown}>COM1")
            lines.append(cmd if ">" in cmd else f"{cmd}>COM1")
        lines.append(f"ECHO {END_MARK}>COM1")
        autoexec = tmp / "AUTOEXEC.BAT"
        autoexec.write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))
        img = tmp / "disk.img"
        make_image(img, autoexec, a.file)
        com1 = tmp / "com1.txt"
        conf = tmp / "run.conf"
        write_conf(conf, img, com1, a.conf_extra)
        startup = None
        if os.name == "nt" and not a.show:
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 7  # SW_SHOWMINNOACTIVE
        proc = subprocess.Popen([str(dosbox), "-nomenu", "-fastlaunch", "-time-limit", str(a.timeout),
                                 "-conf", str(conf)], startupinfo=startup)
        try:
            deadline = time.monotonic() + a.timeout + 5
            while time.monotonic() < deadline and proc.poll() is None:
                if com1.exists() and END_MARK in com1.read_text(encoding="cp437", errors="replace"):
                    time.sleep(0.5)
                    break
                time.sleep(0.5)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(10)
        out = com1.read_text(encoding="cp437", errors="replace") if com1.exists() else ""
        sys.stdout.write(out.replace(END_MARK, "").rstrip() + "\n")
        if a.keep:
            a.keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(img, a.keep)
        if END_MARK not in out:
            print(f"(no end marker within {a.timeout} s: a command may be waiting for input)", file=sys.stderr)
            return 1
        return 0


def main() -> int:
    # DOS output contains code page 437 box-drawing characters; never crash on a console that cannot show them.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("commands", nargs="*", help="DOS command lines to run unattended, in order")
    ap.add_argument("--image", type=Path, help=f"disk image for interactive use (default {DEFAULT_IMAGE})")
    ap.add_argument("--file", action="append", default=[], metavar="A:\\NAME=LOCALPATH",
                    help="add a local file to the root directory of a new disk image")
    ap.add_argument("--keep", type=Path, help="unattended mode: save the disk image after the run")
    ap.add_argument("--dosbox", help="path to the dosbox-x executable")
    ap.add_argument("--timeout", type=int, default=60, help="unattended mode: seconds before stopping")
    ap.add_argument("--show", action="store_true", help="unattended mode: show the DOSBox-X window")
    ap.add_argument("--conf-extra", action="append", default=[], metavar="SECTION.KEY=VALUE",
                    help="override or add a DOSBox-X setting, e.g. cpu.cputype=286 or dosbox.memsize=1 "
                         "(repeatable; default settings: dosbox.memsize=16, cpu.cputype=pentium, cpu.cycles=max)")
    a = ap.parse_args()
    dosbox = find_dosbox(a.dosbox)
    return unattended(a, dosbox) if a.commands else interactive(a, dosbox)


if __name__ == "__main__":
    sys.exit(main())

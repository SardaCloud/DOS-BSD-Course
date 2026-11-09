"""Run commands on MS-DOS 4.00 with a second floppy image in drive B: (Module 7 labs).

    python labs/07-filesystems/dosb.py DISK.IMG [dos_run options] "CMD" ...
    python labs/07-filesystems/dosb.py --new DISK.IMG --file A:\\FMTANS.TXT=labs/07-filesystems/FMTANS.TXT
                                       "FORMAT B: /V:LAB7 <FMTANS.TXT" "CHKDSK B:"

This is tools/dos_run.py (Module 0, section 0.5) with one addition: DISK.IMG is
mounted as a second 1.44 MB floppy drive, so MS-DOS 4.00 boots from the lab
image in A: as usual and sees DISK.IMG as drive B:. Everything the commands do
to drive B: is written to DISK.IMG itself, as it would be to a real diskette
in a real drive: make a copy first if you want to keep the original.

--new creates DISK.IMG filled with zero bytes (an unformatted diskette) if it
does not exist yet. All other options (--file, --timeout, --show, --keep and so
on) are those of dos_run.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import dos_run  # noqa: E402

FLOPPY_BYTES = 1474560


def main() -> int:
    args = sys.argv[1:]
    new = "--new" in args
    if new:
        args.remove("--new")
    if not args or args[0].startswith("-"):
        raise SystemExit(__doc__)
    disk = Path(args.pop(0)).resolve()
    if new and not disk.exists():
        disk.parent.mkdir(parents=True, exist_ok=True)
        disk.write_bytes(bytes(FLOPPY_BYTES))
    if not disk.is_file() or disk.stat().st_size != FLOPPY_BYTES:
        raise SystemExit(f"{disk}: not a 1.44 MB floppy image (use --new to create a blank one)")
    if not any(not a.startswith("-") for a in args):
        raise SystemExit("give at least one DOS command to run")

    plain = dos_run.write_conf

    def write_conf(path: Path, *rest, **kw) -> None:
        plain(path, *rest, **kw)
        conf = path.read_text(encoding="ascii")
        conf = conf.replace("boot a:", f'imgmount b "{disk}" -t floppy\nboot a:')
        path.write_text(conf, encoding="ascii")

    dos_run.write_conf = write_conf
    sys.argv = ["dos_run.py", *args]
    return dos_run.main()


if __name__ == "__main__":
    sys.exit(main())

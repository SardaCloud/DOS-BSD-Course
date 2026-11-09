"""Make a bootable 1.44 MB MS-DOS 4.00 floppy image from the binaries built from source.

    python tools/make_floppy.py [--out build/images/dos400.img] [--autoexec FILE]

Uses the boot sector assembled from v4.0/src/BOOT/MSBOOT.ASM (MSBOOT.BIN, origin
0x7C00) with a 1.44 MB BPB, and lays the disk out the way MSBOOT and MSLOAD
expect it: IO.SYS and MSDOS.SYS are the first two root directory entries and
IO.SYS starts at the first data sector (cluster 2). All the files that the
source tree's CPY.BAT collects are copied as well.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "dos4" / "SRC"

SECTOR = 512
TOTAL = 2880
SPC = 1
RESERVED = 1
NFATS = 2
SPF = 9
ROOT_ENTRIES = 224
MEDIA = 0xF0
SPT = 18
HEADS = 2
ROOT_SECTORS = ROOT_ENTRIES * 32 // SECTOR
DATA_START = RESERVED + NFATS * SPF + ROOT_SECTORS
DATE = ((2024 - 1980) << 9) | (4 << 5) | 25
TIME = 12 << 11

CONFIG_SYS = "FILES=20\r\nBUFFERS=20\r\nDEVICE=\\ANSI.SYS\r\n"
AUTOEXEC_BAT = "@ECHO OFF\r\nPROMPT $P$G\r\nPATH A:\\\r\nVER\r\n"


def dos_name(name: str) -> bytes:
    base, _, ext = name.upper().partition(".")
    if len(base) > 8 or len(ext) > 3:
        raise ValueError(f"not an 8.3 name: {name}")
    return base.ljust(8).encode("ascii") + ext.ljust(3).encode("ascii")


def boot_sector() -> bytearray:
    image = (BUILD / "BOOT" / "MSBOOT.BIN").read_bytes()
    bs = bytearray(image[0x7C00:0x7E00])
    if bs[510:512] != b"\x55\xAA" or bs[3:11] != b"MSDOS4.0":
        raise SystemExit("MSBOOT.BIN does not look like the MS-DOS 4.00 boot sector")
    # Offsets follow the BPB in MSBOOT.ASM (ByteSec at 0Bh ... Boot_System_id at 36h).
    struct.pack_into("<HBHBHHBHHHII", bs, 0x0B, SECTOR, SPC, RESERVED, NFATS, ROOT_ENTRIES,
                     TOTAL, MEDIA, SPF, SPT, HEADS, 0, 0)
    bs[0x24] = 0x00                       # Phydrv: floppy drive A:
    bs[0x25] = 0x00                       # Curhd
    bs[0x26] = 0x29                       # Ext_Boot_Sig (41)
    struct.pack_into("<I", bs, 0x27, 0x19880400)
    bs[0x2B:0x36] = b"DOS400LAB  "
    bs[0x36:0x3E] = b"FAT12   "
    return bs


def files_from_cpy() -> list[Path]:
    out = []
    for line in (BUILD / "CPY.BAT").read_text(encoding="ascii").splitlines():
        if line.lower().startswith("copy .\\"):
            out.append(BUILD / line.split()[1][2:])
    missing = [str(p) for p in out if not p.exists()]
    if missing:
        raise SystemExit("missing build outputs (run the build first): " + ", ".join(missing))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "images" / "dos400.img")
    ap.add_argument("--autoexec", type=Path, help="AUTOEXEC.BAT to use instead of the default")
    ap.add_argument("--extra", action="append", default=[], metavar="A:\\NAME=LOCALPATH",
                    help="add a local file to the root directory")
    a = ap.parse_args()

    entries: list[tuple[str, bytes, int]] = []  # (8.3 name, data, attributes)
    binaries = {p.name.upper(): p for p in files_from_cpy()}
    entries.append(("IO.SYS", binaries.pop("IO.SYS").read_bytes(), 0x07))
    entries.append(("MSDOS.SYS", binaries.pop("MSDOS.SYS").read_bytes(), 0x07))
    entries.append(("COMMAND.COM", binaries.pop("COMMAND.COM").read_bytes(), 0x20))
    autoexec = a.autoexec.read_bytes() if a.autoexec else AUTOEXEC_BAT.encode("ascii")
    entries.append(("CONFIG.SYS", CONFIG_SYS.encode("ascii"), 0x20))
    entries.append(("AUTOEXEC.BAT", autoexec, 0x20))
    for name in sorted(binaries):
        entries.append((name, binaries[name].read_bytes(), 0x20))
    for spec in a.extra:
        target, _, local = spec.partition("=")
        name = target.upper().removeprefix("A:").lstrip("\\")
        if "\\" in name or not name:
            raise SystemExit(f"--extra expects A:\\NAME.EXT=LOCALPATH (root directory only): {spec}")
        if name in ("IO.SYS", "MSDOS.SYS"):
            raise SystemExit(f"{name} must stay the first two directory entries; rebuild it instead")
        entries = [e for e in entries if e[0] != name]
        if local:  # an empty path removes the file, e.g. A:\CONFIG.SYS= for a boot without CONFIG.SYS
            entries.append((name, Path(local).read_bytes(), 0x20))

    img = bytearray(TOTAL * SECTOR)
    img[0:SECTOR] = boot_sector()
    fat = [0] * (TOTAL - DATA_START + 2)
    fat[0], fat[1] = 0xF00 | MEDIA, 0xFFF
    root = bytearray(ROOT_SECTORS * SECTOR)
    cluster = 2
    slot = 0

    def add_dir(raw: bytes) -> None:
        nonlocal slot
        root[slot * 32:(slot + 1) * 32] = raw
        slot += 1

    for i, (name, data, attr) in enumerate(entries):
        n = max(1, -(-len(data) // (SECTOR * SPC))) if data else 0
        start = cluster if data else 0
        if data:
            if cluster + n - 1 >= len(fat):
                raise SystemExit(f"disk full while adding {name}")
            for c in range(cluster, cluster + n):
                fat[c] = c + 1 if c < cluster + n - 1 else 0xFFF
            off = (DATA_START + (cluster - 2) * SPC) * SECTOR
            img[off:off + len(data)] = data
            cluster += n
        add_dir(struct.pack("<11sB10sHHHI", dos_name(name), attr, b"\0" * 10, TIME, DATE, start, len(data)))
        if i == 1:  # the volume label must not come before IO.SYS and MSDOS.SYS
            add_dir(struct.pack("<11sB10sHHHI", b"DOS400LAB  ", 0x08, b"\0" * 10, TIME, DATE, 0, 0))

    packed = bytearray(SPF * SECTOR)
    for c in range(0, len(fat), 2):
        a0, a1 = fat[c], fat[c + 1] if c + 1 < len(fat) else 0
        o = c * 3 // 2
        packed[o:o + 3] = bytes((a0 & 0xFF, ((a0 >> 8) & 0x0F) | ((a1 & 0x0F) << 4), (a1 >> 4) & 0xFF))
    for f in range(NFATS):
        off = (RESERVED + f * SPF) * SECTOR
        img[off:off + len(packed)] = packed
    off = (RESERVED + NFATS * SPF) * SECTOR
    img[off:off + len(root)] = root

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(img)
    used = (cluster - 2) * SPC * SECTOR
    print(f"{a.out}: {len(entries)} files, {used:,} bytes used, "
          f"{(TOTAL - DATA_START) * SECTOR - used:,} bytes free")
    return 0


if __name__ == "__main__":
    sys.exit(main())

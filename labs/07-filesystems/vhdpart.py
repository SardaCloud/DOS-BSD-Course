"""vhdpart.py - copy one GPT partition out of a VHD disk image into a raw file (Module 7, Lab 7.5).

    python vhdpart.py DISK.vhd                 list the GPT partitions
    python vhdpart.py DISK.vhd.xz 4 rootfs.img copy partition 4 into rootfs.img

Reads fixed and dynamic VHD files, also still compressed as .xz (it then reads
the stream once, front to back, so it takes a minute or two). The output is a
plain image of the partition, the same bytes FreeBSD sees in /dev/ada0p4, so
ufsx.py, dumpfs or fsdb can read it. Regions of a dynamic VHD that were never
written read as zeros and are not written to the output (on NTFS and most
Unix file systems the result is a sparse file).

The official FreeBSD 15.1 VM image used in the course is
FreeBSD-15.1-RELEASE-amd64-ufs.vhd.xz (Module 0, section 0.6).
"""
from __future__ import annotations

import lzma
import struct
import sys
import uuid

GPT_TYPES = {
    "83bd6b9d-7f41-11dc-be0b-001560b84f0f": "freebsd-boot",
    "c12a7328-f81f-11d2-ba4b-00a0c93ec93b": "efi",
    "516e7cb5-6ecf-11d6-8ff8-00022d09712b": "freebsd-swap",
    "516e7cb6-6ecf-11d6-8ff8-00022d09712b": "freebsd-ufs",
    "516e7cba-6ecf-11d6-8ff8-00022d09712b": "freebsd-zfs",
}


def open_any(path: str):
    return lzma.open(path, "rb") if path.endswith(".xz") else open(path, "rb")


class Vhd:
    """Sequential reader for a VHD: yields (virtual offset, data) chunks in file order."""

    def __init__(self, path: str):
        self.path = path
        with open_any(path) as f:
            footer = f.read(512)
            if footer[:8] != b"conectix":
                raise SystemExit(f"{path}: not a VHD (no 'conectix' cookie at offset 0)")
            self.size = struct.unpack_from(">Q", footer, 48)[0]
            self.dtype = struct.unpack_from(">I", footer, 60)[0]   # 2 = fixed, 3 = dynamic
            if self.dtype == 2:
                return
            dyn = f.read(1024)
            _, table, _, entries, self.block = struct.unpack_from(">QQIII", dyn, 8)
            f.seek(table)
            self.bat = struct.unpack(f">{entries}I", f.read(4 * entries))

    def read_virtual(self, start: int, length: int) -> bytes:
        out = bytearray(length)
        for voff, data in self.chunks(start, start + length):
            out[voff - start:voff - start + len(data)] = data
        return bytes(out)

    def chunks(self, lo: int, hi: int):
        """Yield (virtual offset, bytes) covering the present parts of [lo, hi)."""
        with open_any(self.path) as f:
            if self.dtype == 2:          # fixed VHD: the data, then a 512-byte footer at the end
                f.seek(lo)
                pos = lo
                while pos < hi:
                    data = f.read(min(1 << 20, hi - pos))
                    if not data:
                        break
                    yield pos, data
                    pos += len(data)
                return
            bitmap = ((self.block // 512 + 7) // 8 + 511) // 512 * 512
            blocks = sorted((sec * 512, i) for i, sec in enumerate(self.bat) if sec != 0xFFFFFFFF)
            for foff, i in blocks:       # file order, so an .xz stream is read only forward
                vstart = i * self.block
                a, b = max(lo, vstart), min(hi, vstart + self.block)
                if a >= b:
                    continue
                f.seek(foff + bitmap + (a - vstart))
                yield a, f.read(b - a)


def partitions(v: Vhd) -> list[tuple[int, str, int, int, str]]:
    head = v.read_virtual(0, 34 * 512)
    if head[512:520] != b"EFI PART":
        raise SystemExit("no GPT header at LBA 1")
    lba, n, size = struct.unpack_from("<QII", head, 512 + 72)
    out = []
    for i in range(n):
        e = head[lba * 512 + i * size:lba * 512 + (i + 1) * size]
        if len(e) < size or e[:16] == bytes(16):
            continue
        t = str(uuid.UUID(bytes_le=e[:16]))
        first, last = struct.unpack_from("<QQ", e, 32)
        name = e[56:128].decode("utf-16-le").rstrip("\0")
        out.append((i + 1, GPT_TYPES.get(t, t), first, last, name))
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    v = Vhd(argv[0])
    print(f"{argv[0]}: {'dynamic' if v.dtype == 3 else 'fixed'} VHD, {v.size} bytes ({v.size // 512} sectors)")
    parts = partitions(v)
    for idx, kind, first, last, name in parts:
        print(f"  p{idx}  {kind:13} LBA {first:>9} - {last:>9}  {(last - first + 1) * 512 / 2**20:8.1f} MiB  {name}")
    if len(argv) < 3:
        return 0
    want = int(argv[1])
    sel = [p for p in parts if p[0] == want]
    if not sel:
        raise SystemExit(f"no partition {want}")
    _, kind, first, last, _ = sel[0]
    lo, hi = first * 512, (last + 1) * 512
    written = 0
    open(argv[2], "wb").close()
    if sys.platform == "win32":          # ask NTFS for a sparse file, so unwritten regions take no space
        import subprocess
        subprocess.run(["fsutil", "sparse", "setflag", argv[2]], capture_output=True)
    with open(argv[2], "r+b") as out:
        out.truncate(hi - lo)
        for voff, data in v.chunks(lo, hi):
            if data.count(0) == len(data):
                continue
            out.seek(voff - lo)
            out.write(data)
            written += len(data)
    print(f"p{want} ({kind}) -> {argv[2]}: {hi - lo} bytes, {written} bytes of data written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

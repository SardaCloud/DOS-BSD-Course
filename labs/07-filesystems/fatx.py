"""fatx.py - a FAT12/FAT16 explorer for MS-DOS disk images (Module 7, Lab 7.2).

Read-only unless you use setfat. Works on the 1.44 MB lab floppies and on hard
disk images with an MBR partition table (--part N).

    python fatx.py IMAGE info                BPB, layout, FAT type, cluster count
    python fatx.py IMAGE ls [PATH] [-a]      directory listing (-a: also deleted entries)
    python fatx.py IMAGE entry PATH          the 32-byte directory entry, field by field
    python fatx.py IMAGE chain PATH          cluster chain of a file or directory
    python fatx.py IMAGE fat [FIRST [N]]     raw FAT entries (default: the first 32)
    python fatx.py IMAGE map [LAST]          who owns each cluster (default: up to the last used one)
    python fatx.py IMAGE get PATH OUTFILE    copy a file out of the image
    python fatx.py IMAGE check               a small CHKDSK: lost clusters, cross-links, sizes
    python fatx.py IMAGE setfat N VALUE [--copy K]   write FAT entry N (in every FAT copy, or only copy K)

PATH uses backslashes or slashes: \\, \\SUB, SUB\\FILE.TXT. Names are 8.3, case-insensitive.

Every structure follows the MS-DOS 4.00 sources (v4.0/src):
  boot sector and BPB    INC/BOOTFORM.INC   EXT_BPB_INFO, EXT_IBMBOOT_HEADER
  directory entry        INC/DIRENT.INC     dir_entry, attribute bits, time and date packing
  FAT12 entry            DOS/FAT.ASM        MAPCLUSTER and UNPACK (also INC/DOSSYM.INC)
  FAT12 or FAT16         DOS/FAT.ASM        dpb_max_cluster compared with 4096-10
  cluster -> sector      DOS/ROM.ASM        FIGREC
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field

ATTRS = [(0x01, "R"), (0x02, "H"), (0x04, "S"), (0x08, "V"), (0x10, "D"), (0x20, "A")]  # DIRENT.INC


@dataclass
class Entry:
    name: str           # "NAME.EXT" as DIR would show it
    raw_name: bytes     # the 11 bytes of dir_name
    attr: int           # dir_attr
    time: int           # dir_time
    date: int           # dir_date
    first: int          # dir_first
    size: int           # dir_size_l + 65536 * dir_size_h
    offset: int         # byte offset of the entry in the image
    deleted: bool = False
    raw: bytes = b""

    @property
    def is_dir(self) -> bool:
        return bool(self.attr & 0x10)

    @property
    def is_label(self) -> bool:
        return bool(self.attr & 0x08)


def attr_text(attr: int) -> str:
    return "".join(ch if attr & bit else "-" for bit, ch in ATTRS)


def decode_time(t: int) -> str:
    # DIRENT.INC: bits 0-4 = seconds/2, bits 5-10 = minute, bits 11-15 = hour
    return f"{t >> 11:02d}:{(t >> 5) & 0x3F:02d}:{(t & 0x1F) * 2:02d}"


def decode_date(d: int) -> str:
    # DIRENT.INC: bits 0-4 = day, bits 5-8 = month, bits 9-15 = year - 1980
    return f"{(d >> 9) + 1980:04d}-{(d >> 5) & 0x0F:02d}-{d & 0x1F:02d}"


def dos_name(raw: bytes) -> str:
    base = raw[0:8].decode("cp437").rstrip()
    ext = raw[8:11].decode("cp437").rstrip()
    return f"{base}.{ext}" if ext else base


def to_raw_name(name: str) -> bytes:
    if name in (".", ".."):
        return name.encode("ascii").ljust(11)
    base, _, ext = name.upper().partition(".")
    if not base or len(base) > 8 or len(ext) > 3:
        raise SystemExit(f"not an 8.3 name: {name}")
    return base.encode("cp437").ljust(8) + ext.encode("cp437").ljust(3)


@dataclass
class Volume:
    path: str
    part: int = 0               # MBR partition number (1-4), 0 = no partition table
    writable: bool = False
    img: bytearray = field(init=False)
    base: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        with open(self.path, "rb") as f:
            self.img = bytearray(f.read())
        if self.part:
            # MBR partition table: four 16-byte entries at offset 1BEh; LBA start at +8 (Module 1)
            e = 0x1BE + 16 * (self.part - 1)
            ptype = self.img[e + 4]
            start, count = struct.unpack_from("<II", self.img, e + 8)
            if ptype == 0 or count == 0:
                raise SystemExit(f"partition {self.part} is empty")
            self.ptype = ptype
            self.base = start * 512
        self.read_bpb()

    # ---- boot sector and layout ------------------------------------------------------------
    def read_bpb(self) -> None:
        b = self.base
        (self.bytes_per_sector, self.sec_per_clus, self.reserved, self.nfats, self.root_entries,
         total16, self.media, self.fat_sectors, self.sec_per_track, self.heads, self.hidden,
         total32) = struct.unpack_from("<HBHBHHBHHHII", self.img, b + 0x0B)   # EXT_BPB_INFO
        if self.bytes_per_sector not in (512, 1024, 2048, 4096) or self.sec_per_clus == 0:
            raise SystemExit("sector 0 does not hold a FAT boot sector (try --part 1 for a hard disk image)")
        if self.fat_sectors == 0 and self.root_entries == 0:
            label = bytes(self.img[b + 0x47:b + 0x52]).decode("cp437")
            raise SystemExit(f"FAT32 volume ({label!r}): 0 root entries and a 32-bit FAT size at offset 24h. "
                             "FAT32 came in 1996, after MS-DOS 4.00; fatx.py reads FAT12 and FAT16 only.")
        # A 16-bit total of 0 means "use the 32-bit EBPB_BIGTOTALSECTORS" (DOS 4.00, volumes >= 32 MB)
        self.total_sectors = total16 if total16 else total32
        self.oem = bytes(self.img[b + 3:b + 11]).decode("cp437")
        self.ext_sig = self.img[b + 0x26]
        if self.ext_sig == 41:                                              # EXT_BOOT_SIGNATURE
            self.serial = struct.unpack_from("<I", self.img, b + 0x27)[0]
            self.label = bytes(self.img[b + 0x2B:b + 0x36]).decode("cp437")
            self.fs_id = bytes(self.img[b + 0x36:b + 0x3E]).decode("cp437")
        else:
            self.serial, self.label, self.fs_id = None, None, None
        bps = self.bytes_per_sector
        self.fat_start = self.reserved                                      # dpb_first_FAT
        self.root_start = self.fat_start + self.nfats * self.fat_sectors    # dpb_dir_sector
        self.root_sectors = (self.root_entries * 32 + bps - 1) // bps
        self.data_start = self.root_start + self.root_sectors               # dpb_first_sector
        self.clusters = (self.total_sectors - self.data_start) // self.sec_per_clus
        self.max_cluster = self.clusters + 1                                # dpb_max_cluster
        self.fat12 = self.max_cluster < 4096 - 10                           # FAT.ASM: CMP ...,4096-10
        self.cluster_bytes = self.sec_per_clus * bps

    def sector_offset(self, sector: int) -> int:
        return self.base + sector * self.bytes_per_sector

    def cluster_sector(self, n: int) -> int:
        # FIGREC: (n - 2) * sectors per cluster + first data sector
        return (n - 2) * self.sec_per_clus + self.data_start

    def cluster_offset(self, n: int) -> int:
        return self.sector_offset(self.cluster_sector(n))

    # ---- the FAT -------------------------------------------------------------------------
    def fat_bytes(self, copy: int = 0) -> bytes:
        o = self.sector_offset(self.fat_start + copy * self.fat_sectors)
        return bytes(self.img[o:o + self.fat_sectors * self.bytes_per_sector])

    def fat_entry(self, n: int, copy: int = 0) -> int:
        o = self.sector_offset(self.fat_start + copy * self.fat_sectors)
        if not self.fat12:
            return struct.unpack_from("<H", self.img, o + 2 * n)[0]         # 2 bytes per entry
        word = struct.unpack_from("<H", self.img, o + n + n // 2)[0]       # MAPCLUSTER: n + n/2
        if n & 1:                                                           # UNPACK: High12, SHR x4
            word >>= 4
        return word & 0x0FFF                                                # Unpack12: AND 0FFFh

    def set_fat(self, n: int, value: int, copy: int | None = None) -> None:
        if not self.writable:
            raise SystemExit("volume opened read-only")
        copies = range(self.nfats) if copy is None else [copy]
        for c in copies:
            o = self.sector_offset(self.fat_start + c * self.fat_sectors)
            if not self.fat12:
                struct.pack_into("<H", self.img, o + 2 * n, value & 0xFFFF)
                continue
            p = o + n + n // 2
            word = struct.unpack_from("<H", self.img, p)[0]
            if n & 1:                                                       # PACK keeps the other 4 bits
                word = (word & 0x000F) | ((value & 0x0FFF) << 4)
            else:
                word = (word & 0xF000) | (value & 0x0FFF)
            struct.pack_into("<H", self.img, p, word)

    def save(self) -> None:
        with open(self.path, "wb") as f:
            f.write(self.img)

    def is_eof(self, v: int) -> bool:
        # FAT.ASM IsEof: >= FF8h (FAT12) or FFF8h (FAT16); FF0h is also accepted on FAT12
        return (v >= 0xFF8 or v == 0xFF0) if self.fat12 else v >= 0xFFF8

    def chain(self, first: int, limit: int | None = None) -> list[int]:
        out, c = [], first
        limit = limit or self.max_cluster
        while 2 <= c <= self.max_cluster and len(out) <= limit:
            out.append(c)
            c = self.fat_entry(c)
            if self.is_eof(c):
                break
        return out

    # ---- directories ---------------------------------------------------------------------
    def dir_slots(self, first: int | None):
        """Yield (offset, 32 bytes) for every slot of the root (first=None) or a subdirectory."""
        if first is None:
            o = self.sector_offset(self.root_start)
            for i in range(self.root_entries):
                yield o + 32 * i, bytes(self.img[o + 32 * i:o + 32 * i + 32])
            return
        for c in self.chain(first):          # a subdirectory is a file made of 32-byte entries
            o = self.cluster_offset(c)
            for i in range(self.cluster_bytes // 32):
                yield o + 32 * i, bytes(self.img[o + 32 * i:o + 32 * i + 32])

    def entries(self, first: int | None, deleted: bool = False) -> list[Entry]:
        out = []
        for off, e in self.dir_slots(first):
            if e[0] == 0x00:                 # DIRENT.INC: 00 -> end of allocated directory
                break
            gone = e[0] == 0xE5               # DIRENT.INC: E5 -> free directory entry
            if gone and not deleted:
                continue
            raw = (b"?" + e[1:11]) if gone else e[0:11]
            time, date, first_c, lo, hi = struct.unpack_from("<HHHHH", e, 22)
            shown = raw.decode("cp437").rstrip() if e[11] & 0x08 else dos_name(raw)   # a label is 11 chars
            out.append(Entry(shown, e[0:11], e[11], time, date, first_c, lo + (hi << 16),
                             off, gone, e))
        return out

    def lookup(self, path: str) -> Entry | None:
        """Find a path; returns None for the root directory itself."""
        parts = [p for p in path.replace("/", "\\").split("\\") if p]
        cur: Entry | None = None
        for p in parts:
            want = to_raw_name(p)
            for e in self.entries(cur.first if cur else None):
                if e.raw_name == want and not e.is_label:
                    cur = e
                    break
            else:
                raise SystemExit(f"{path}: not found")
        return cur

    def read_file(self, e: Entry) -> bytes:
        data = b"".join(bytes(self.img[self.cluster_offset(c):self.cluster_offset(c) + self.cluster_bytes])
                        for c in self.chain(e.first))
        return data if e.is_dir else data[:e.size]

    def walk(self, first: int | None = None, prefix: str = "\\"):
        """Yield (path, Entry) for every file and directory, depth first."""
        for e in self.entries(first):
            if e.is_label or e.name in (".", ".."):
                continue
            yield prefix + e.name, e
            if e.is_dir and e.first:
                yield from self.walk(e.first, prefix + e.name + "\\")


def runs(chain: list[int]) -> list[tuple[int, int]]:
    """Group a chain into runs of consecutive clusters: [(start, end), ...]."""
    out: list[tuple[int, int]] = []
    for c in chain:
        if out and c == out[-1][1] + 1:
            out[-1] = (out[-1][0], c)
        else:
            out.append((c, c))
    return out


def runs_text(chain: list[int]) -> str:
    return ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in runs(chain))


# ---- commands ------------------------------------------------------------------------------
def cmd_info(v: Volume, args: list[str]) -> None:
    kind = "FAT12" if v.fat12 else "FAT16"
    print(f"OEM name            {v.oem!r}")
    print(f"bytes per sector    {v.bytes_per_sector}")
    print(f"sectors per cluster {v.sec_per_clus}  ({v.cluster_bytes} bytes per cluster)")
    print(f"reserved sectors    {v.reserved}")
    print(f"FAT copies          {v.nfats} x {v.fat_sectors} sectors")
    print(f"root entries        {v.root_entries}  ({v.root_sectors} sectors)")
    print(f"total sectors       {v.total_sectors}")
    print(f"media byte          {v.media:02X}h")
    print(f"sectors per track   {v.sec_per_track}, heads {v.heads}, hidden sectors {v.hidden}")
    if v.serial is not None:
        print(f"serial number       {v.serial >> 16:04X}-{v.serial & 0xFFFF:04X}")
        print(f"volume label        {v.label!r}")
        print(f"file system id      {v.fs_id!r}  (informational only: not used to pick FAT12/16)")
    else:
        print("extended BPB        absent (signature byte is not 29h)")
    print(f"layout (sectors)    boot 0..{v.fat_start - 1}, FATs {v.fat_start}..{v.root_start - 1}, "
          f"root {v.root_start}..{v.data_start - 1}, data {v.data_start}..{v.total_sectors - 1}")
    print(f"clusters            {v.clusters} (numbered 2..{v.max_cluster}), max_cluster = {v.max_cluster}")
    print(f"FAT type            {kind}  (max_cluster {'<' if v.fat12 else '>='} 4086)")
    free = sum(1 for n in range(2, v.max_cluster + 1) if v.fat_entry(n) == 0)
    print(f"free clusters       {free}  ({free * v.cluster_bytes} bytes)")


def cmd_ls(v: Volume, args: list[str]) -> None:
    show_deleted = "-a" in args
    args = [a for a in args if a != "-a"]
    d = v.lookup(args[0]) if args else None
    if d is not None and not d.is_dir:
        raise SystemExit(f"{args[0]}: not a directory")
    print(f"{'name':12} {'attr':6} {'date':10} {'time':8} {'first':>5} {'size':>8}  slot@offset")
    for e in v.entries(d.first if d else None, show_deleted):
        size = "<DIR>" if e.is_dir else str(e.size)
        mark = "  (deleted)" if e.deleted else ""
        print(f"{e.name:12} {attr_text(e.attr):6} {decode_date(e.date)} {decode_time(e.time)} "
              f"{e.first:5} {size:>8}  {e.offset:#07x}{mark}")


def cmd_entry(v: Volume, args: list[str]) -> None:
    e = v.lookup(args[0])
    if e is None:
        raise SystemExit("the root directory has no directory entry of its own")
    raw = e.raw
    print(f"offset {e.offset:#x} (sector {(e.offset - v.base) // v.bytes_per_sector})")
    for row in range(0, 32, 16):
        print("  " + " ".join(f"{b:02X}" for b in raw[row:row + 16]))
    print(f"  00 dir_name      {raw[0:11]!r}")
    print(f"  0B dir_attr      {raw[11]:02X}h = {attr_text(raw[11])}")
    print(f"  0C reserved      {raw[12:22].hex(' ')}")
    print(f"  16 dir_time      {e.time:04X}h = {decode_time(e.time)}")
    print(f"  18 dir_date      {e.date:04X}h = {decode_date(e.date)}")
    print(f"  1A dir_first     {e.first}")
    print(f"  1C dir_size      {e.size}")


def cmd_chain(v: Volume, args: list[str]) -> None:
    e = v.lookup(args[0])
    if e is None:
        raise SystemExit("the root directory is not a cluster chain on FAT12/16: it has a fixed place")
    ch = v.chain(e.first) if e.first else []
    need = -(-e.size // v.cluster_bytes)
    print(f"{args[0]}: first cluster {e.first}, size {e.size}, {len(ch)} clusters"
          + ("" if e.is_dir else f" (size needs {need})"))
    if ch:
        last = v.fat_entry(ch[-1])
        shown = ch if len(ch) <= 16 else ch[:8] + ["..."] + ch[-4:]
        print(f"chain: {' -> '.join(map(str, shown))} -> {last:03X}h")
        print(f"runs:  {runs_text(ch)}  ({len(runs(ch))} fragment{'s' if len(runs(ch)) != 1 else ''})")
        print(f"sectors of the first run: {v.cluster_sector(runs(ch)[0][0])}..."
              f"{v.cluster_sector(runs(ch)[0][1]) + v.sec_per_clus - 1}")


def cmd_fat(v: Volume, args: list[str]) -> None:
    first = int(args[0], 0) if args else 0
    n = int(args[1], 0) if len(args) > 1 else 32
    width = 3 if v.fat12 else 4
    for row in range(first, min(first + n, v.max_cluster + 1), 8):
        cells = [f"{v.fat_entry(c):0{width}X}" for c in range(row, min(row + 8, first + n, v.max_cluster + 1))]
        print(f"{row:5}: " + " ".join(cells))


def owners(v: Volume) -> tuple[dict[int, list[str]], list[tuple[str, Entry, list[int]]]]:
    own: dict[int, list[str]] = {}
    files = []
    for path, e in v.walk():
        ch = v.chain(e.first) if e.first else []
        files.append((path, e, ch))
        for c in ch:
            own.setdefault(c, []).append(path)
    return own, files


def cmd_map(v: Volume, args: list[str]) -> None:
    own, files = owners(v)
    keys = {}
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    for i, (path, e, ch) in enumerate(files):
        keys[path] = letters[i % len(letters)]
    used = [n for n in range(2, v.max_cluster + 1) if v.fat_entry(n) != 0]
    last = int(args[0], 0) if args else (max(used) if used else 2)
    print("legend: . free  ? allocated in the FAT but in no file (lost)  ! in two files (cross-linked)")
    for path, e, ch in files:
        if ch and ch[0] <= last:
            print(f"  {keys[path]} {path}")
    for row in range(2, last + 1, 64):
        line = []
        for c in range(row, min(row + 64, last + 1)):
            if c in own:
                line.append("!" if len(own[c]) > 1 else keys[own[c][0]])
            else:
                line.append("." if v.fat_entry(c) == 0 else "?")
        print(f"{row:5} {''.join(line)}")


def cmd_get(v: Volume, args: list[str]) -> None:
    e = v.lookup(args[0])
    if e is None or e.is_dir:
        raise SystemExit(f"{args[0]}: not a file")
    data = v.read_file(e)
    with open(args[1], "wb") as f:
        f.write(data)
    print(f"{len(data)} bytes written to {args[1]}")


def cmd_check(v: Volume, args: list[str]) -> None:
    problems = 0
    own, files = owners(v)
    for path, e, ch in files:
        if e.first and not 2 <= e.first <= v.max_cluster:
            print(f"{path}: first cluster {e.first} is invalid")
            problems += 1
            continue
        if ch and not v.is_eof(v.fat_entry(ch[-1])):
            print(f"{path}: chain leaves the disk or loops after cluster {ch[-1]} "
                  f"(FAT entry {v.fat_entry(ch[-1]):X}h)")
            problems += 1
        if not e.is_dir and len(ch) != -(-e.size // v.cluster_bytes):
            print(f"{path}: size {e.size} needs {-(-e.size // v.cluster_bytes)} clusters, chain has {len(ch)}")
            problems += 1
    for c, paths in sorted(own.items()):
        if len(paths) > 1:
            print(f"cluster {c} is in more than one file: {', '.join(paths)}")
            problems += 1
    lost = [n for n in range(2, v.max_cluster + 1) if n not in own and v.fat_entry(n) not in (0, 0xFF7, 0xFFF7)]
    if lost:
        heads = [n for n in lost if not any(v.fat_entry(m) == n for m in lost)]
        print(f"{len(lost)} lost clusters in {len(heads)} chains: {runs_text(lost)}")
        problems += 1
    for k in range(1, v.nfats):
        if v.fat_bytes(k) != v.fat_bytes(0):
            diff = [n for n in range(v.max_cluster + 1) if v.fat_entry(n, k) != v.fat_entry(n, 0)]
            print(f"FAT copy {k + 1} differs from copy 1 in {len(diff)} entries, first at cluster {diff[0]}")
            problems += 1
    print("no problems found" if not problems else f"{problems} problem(s)")


def cmd_setfat(v: Volume, args: list[str]) -> None:
    copy = None
    if "--copy" in args:
        i = args.index("--copy")
        copy = int(args[i + 1]) - 1
        del args[i:i + 2]
    n, value = int(args[0], 0), int(args[1], 0)
    old = v.fat_entry(n, copy or 0)
    v.set_fat(n, value, copy)
    v.save()
    which = "all FAT copies" if copy is None else f"FAT copy {copy + 1}"
    print(f"FAT entry {n}: {old:X}h -> {value:X}h in {which}")


COMMANDS = {"info": cmd_info, "ls": cmd_ls, "entry": cmd_entry, "chain": cmd_chain, "fat": cmd_fat,
            "map": cmd_map, "get": cmd_get, "check": cmd_check, "setfat": cmd_setfat}


def main(argv: list[str]) -> int:
    part = 0
    if "--part" in argv:
        i = argv.index("--part")
        part = int(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        return 2
    v = Volume(argv[0], part, writable=argv[1] == "setfat")
    COMMANDS[argv[1]](v, argv[2:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

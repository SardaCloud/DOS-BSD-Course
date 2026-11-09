"""omfdump.py -- print the records of a Microsoft/Intel OMF object file (.OBJ) or library (.LIB).

    python omfdump.py HELLO.OBJ             every record, decoded
    python omfdump.py HELLO.OBJ --bytes     ... plus the LEDATA bytes in hex
    python omfdump.py MYLIB.LIB --modules   one line per library member, with its public names
    python omfdump.py SLIBCE.LIB --member crt0    only the members whose name contains "crt0"

Module 5 lab tool (MS-DOS 4.00 vs FreeBSD 15.1). An OMF file is a sequence of records:

    +------+--------+---------------------------+----------+
    | type | length | contents (length-1 bytes) | checksum |
    | 1 B  | 2 B LE |                           |   1 B    |
    +------+--------+---------------------------+----------+

Odd record types (91h, 99h, ...) are the 32-bit variants; MS C 5.10 and MASM 5.10 write the
16-bit ones. Names are stored once (LNAMES, EXTDEF, PUBDEF) and later referred to by index,
counting from 1. Indexes below 80h take one byte, larger ones two bytes (high bit set).
A library (.LIB) starts with a header record (F0h) whose length sets a page size; every member
module starts on a page boundary, and a dictionary of public names follows the end record (F1h).
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

RECORD_NAMES = {
    0x80: "THEADR", 0x82: "LHEADR", 0x88: "COMENT", 0x8A: "MODEND", 0x8B: "MODEND32",
    0x8C: "EXTDEF", 0x8E: "TYPDEF", 0x90: "PUBDEF", 0x91: "PUBDEF32", 0x94: "LINNUM",
    0x95: "LINNUM32", 0x96: "LNAMES", 0x98: "SEGDEF", 0x99: "SEGDEF32", 0x9A: "GRPDEF",
    0x9C: "FIXUPP", 0x9D: "FIXUPP32", 0xA0: "LEDATA", 0xA1: "LEDATA32", 0xA2: "LIDATA",
    0xA3: "LIDATA32", 0xB0: "COMDEF", 0xB4: "LEXTDEF", 0xB6: "LPUBDEF", 0xB8: "LCOMDEF",
    0xF0: "LIBHDR", 0xF1: "LIBEND",
}
BIG = {0x8B, 0x91, 0x95, 0x99, 0x9D, 0xA1, 0xA3}      # records with 32-bit offsets
ALIGN = {0: "absolute", 1: "byte", 2: "word", 3: "para", 4: "page", 5: "dword"}
COMBINE = {0: "private", 2: "public", 4: "public", 5: "stack", 6: "common", 7: "public"}
LOCATION = {0: "low byte", 1: "offset16", 2: "segment", 3: "far ptr", 4: "high byte",
            5: "offset16(loader)", 9: "offset32", 11: "far ptr 48", 13: "offset32(loader)"}
FRAME = {0: "SEG", 1: "GRP", 2: "EXT", 3: "FRAME#", 4: "LOCATION", 5: "TARGET"}
TARGET = {0: "SEG", 1: "GRP", 2: "EXT", 3: "FRAME#"}
COMENT_CLASS = {0x00: "translator", 0x9D: "memory model", 0x9E: "DOSSEG", 0x9F: "default library",
                0xA0: "OMF extension", 0xA1: "debug info style", 0xA2: "link pass separator", 0xA3: "library module name",
                0xE9: "dependency file"}


class Reader:
    """Read fields from the contents of one record."""

    def __init__(self, data: bytes, big: bool = False):
        self.d, self.i, self.big = data, 0, big

    def more(self) -> bool:
        return self.i < len(self.d)

    def byte(self) -> int:
        self.i += 1
        return self.d[self.i - 1]

    def word(self) -> int:
        self.i += 2
        return struct.unpack_from("<H", self.d, self.i - 2)[0]

    def offset(self) -> int:
        """2 bytes, or 4 in the 32-bit record variants."""
        if self.big:
            self.i += 4
            return struct.unpack_from("<I", self.d, self.i - 4)[0]
        return self.word()

    def index(self) -> int:
        b = self.byte()
        return ((b & 0x7F) << 8) | self.byte() if b & 0x80 else b

    def name(self) -> str:
        n = self.byte()
        self.i += n
        return self.d[self.i - n:self.i].decode("cp437")

    def rest(self) -> bytes:
        r, self.i = self.d[self.i:], len(self.d)
        return r


class Module:
    """Name tables of one module, so that indexes can be printed as names."""

    def __init__(self):
        self.lnames: list[str] = []
        self.segs: list[str] = []
        self.grps: list[str] = []
        self.exts: list[str] = []

    def table(self, method: int) -> list[str]:
        return {0: self.segs, 1: self.grps, 2: self.exts}.get(method, [])

    @staticmethod
    def get(table: list[str], i: int) -> str:
        return table[i - 1] if 0 < i <= len(table) else f"#{i}"


def records(data: bytes):
    """Yield (file offset, type, contents) for each record, following library paging."""
    pos, page = 0, 0
    while pos + 3 <= len(data):
        rtype = data[pos]
        length = struct.unpack_from("<H", data, pos + 1)[0]
        yield pos, rtype, data[pos + 3:pos + 3 + length - 1]
        pos += 3 + length
        if rtype == 0xF0:                          # library header: its size is the page size
            page = pos
        elif rtype in (0x8A, 0x8B) and page:       # members start on page boundaries
            pos = (pos + page - 1) // page * page
        elif rtype == 0xF1:                        # library end: the dictionary follows
            break


def fixup_target(r: Reader, fixdat: int, m: Module, threads: dict) -> str:
    """Decode the frame and target part of a FIXUP subrecord (or of MODEND's start address)."""
    if fixdat & 0x80:
        frame = f"frame from thread F{(fixdat >> 4) & 3} ({threads.get(('F', (fixdat >> 4) & 3), '?')})"
    else:
        fm = (fixdat >> 4) & 7
        frame = f"frame {FRAME.get(fm, fm)}"
        if fm < 3:
            frame += " " + Module.get(m.table(fm), r.index())
    if fixdat & 0x08:
        target = f"target from thread T{fixdat & 3} ({threads.get(('T', fixdat & 3), '?')})"
    else:
        tm = fixdat & 3
        target = f"target {TARGET[tm]} {Module.get(m.table(tm), r.index())}"
    if not fixdat & 0x04:                          # P bit clear: a displacement follows
        target += f" + {r.offset():#x}"
    return f"{target}; {frame}"


def dump(path: Path, show_bytes: bool, member: str | None = None) -> None:
    data = path.read_bytes()
    m = Module()
    threads: dict = {}
    last_data = "?"
    selected = member is None
    for pos, rtype, body in records(data):
        if rtype == 0x80 and member is not None:   # --member: only modules whose name matches
            selected = member.lower() in Reader(body).name().lower()
        if not selected:
            continue
        name = RECORD_NAMES.get(rtype, f"?{rtype:02X}")
        print(f"{pos:06X}  {rtype:02X} {name:<7}", end="")
        r = Reader(body, big=rtype in BIG)
        if rtype == 0x80:                          # THEADR: module name
            m, threads, last_data = Module(), {}, "?"
            print(f" module {r.name()!r}")
        elif rtype == 0x88:                        # COMENT: attribute byte, class byte, text
            r.byte()
            cls = r.byte()
            text = r.rest()
            shown = repr(text.decode("cp437")) if all(32 <= b < 127 for b in text) else text.hex(" ")
            print(f" class {cls:02X} ({COMENT_CLASS.get(cls, 'other')}) {shown}")
        elif rtype == 0x96:                        # LNAMES: a list of names for later records
            start = len(m.lnames) + 1
            while r.more():
                m.lnames.append(r.name())
            print(" " + ", ".join(f"{k}={n!r}" for k, n in enumerate(m.lnames[start - 1:], start)))
        elif rtype in (0x98, 0x99):                # SEGDEF: one segment of this module
            acbp = r.byte()
            if acbp >> 5 == 0:                     # absolute segment: frame number and offset
                r.word()
                r.byte()
            length = r.offset()
            sname, cname = Module.get(m.lnames, r.index()), Module.get(m.lnames, r.index())
            r.index()
            if acbp & 2:
                length = 0x10000
            m.segs.append(sname)
            print(f" seg {len(m.segs)}={sname} class {cname} length {length:#06x} "
                  f"align={ALIGN.get(acbp >> 5)} combine={COMBINE.get((acbp >> 2) & 7)}")
        elif rtype == 0x9A:                        # GRPDEF: segments that share one frame
            gname = Module.get(m.lnames, r.index())
            members = []
            while r.more():
                r.byte()                           # 0FFh: "a segment index follows"
                members.append(Module.get(m.segs, r.index()))
            m.grps.append(gname)
            print(f" group {len(m.grps)}={gname}: {', '.join(members)}")
        elif rtype in (0x90, 0x91, 0xB6):          # PUBDEF: names this module defines
            grp, seg = r.index(), r.index()
            if grp == 0 and seg == 0:
                r.word()
            base = Module.get(m.segs, seg) if seg else "absolute"
            names = []
            while r.more():
                n, off = r.name(), r.offset()
                r.index()
                names.append(f"{n}={base}:{off:04X}")
            print(" " + ", ".join(names))
        elif rtype in (0x8C, 0xB4):                # EXTDEF: names this module needs
            start = len(m.exts) + 1
            while r.more():
                m.exts.append(r.name())
                r.index()
            print(" " + ", ".join(f"{k}={n}" for k, n in enumerate(m.exts[start - 1:], start)))
        elif rtype in (0xB0, 0xB8):                # COMDEF: communal variables (C globals, no initializer)
            def comlen() -> int:
                b = r.byte()
                if b < 0x80:
                    return b
                n = {0x81: 2, 0x84: 3, 0x88: 4}[b]
                r.i += n
                return int.from_bytes(r.d[r.i - n:r.i], "little")
            out = []
            while r.more():
                n = r.name()
                r.index()
                if r.byte() == 0x61:               # FAR: number of elements, element size
                    count = comlen()
                    out.append(f"{n} far {count} x {comlen()} bytes")
                else:
                    out.append(f"{n} near {comlen()} bytes")
                m.exts.append(n)                   # communals are numbered with the externals
            print(" " + ", ".join(out))
        elif rtype in (0xA0, 0xA1):                # LEDATA: bytes for a segment, at an offset
            last_data = Module.get(m.segs, r.index())
            off = r.offset()
            blob = r.rest()
            print(f" {last_data}:{off:04X}, {len(blob)} bytes")
            if show_bytes:
                for k in range(0, len(blob), 16):
                    print(f"{'':20}{off + k:04X}: {blob[k:k + 16].hex(' ')}")
        elif rtype in (0xA2, 0xA3):                # LIDATA: repeated (iterated) data
            last_data = Module.get(m.segs, r.index())
            print(f" {last_data}:{r.offset():04X}, iterated data")
        elif rtype in (0x9C, 0x9D):                # FIXUPP: patches for the preceding LEDATA
            print(f" for the LEDATA of {last_data}" if last_data != "?" else " (thread definitions only)")
            while r.more():
                b = r.byte()
                if not b & 0x80:                   # THREAD subrecord: remember a frame or target
                    kind = "F" if b & 0x40 else "T"
                    method = (b >> 2) & 7
                    desc = (FRAME if kind == "F" else TARGET).get(method if kind == "F" else method & 3, method)
                    if kind == "T" or method < 3:
                        desc = f"{desc} {Module.get(m.table(method & 3), r.index())}"
                    threads[(kind, b & 3)] = desc
                    print(f"{'':20}THREAD {kind}{b & 3} = {desc}")
                    continue
                locat = (b << 8) | r.byte()
                rel = "seg-relative" if locat & 0x4000 else "self-relative"
                loc = LOCATION.get((locat >> 10) & 0xF, "?")
                print(f"{'':20}+{locat & 0x3FF:03X} {loc}, {rel}: {fixup_target(r, r.byte(), m, threads)}")
        elif rtype in (0x94, 0x95):                # LINNUM: source line -> code offset
            r.index()
            seg = Module.get(m.segs, r.index())
            pairs = []
            while r.more():
                pairs.append(f"{r.word()}@{r.offset():04X}")
            print(f" {seg} " + " ".join(pairs))
        elif rtype in (0x8A, 0x8B):                # MODEND: end of module, maybe a start address
            mtype = r.byte()
            text = " main module" if mtype & 0x80 else ""
            if mtype & 0x40:
                text += f", start address: {fixup_target(r, r.byte(), m, threads)}"
            print(text or " (no start address)")
        elif rtype == 0xF0:                        # library header
            dict_off, dict_blocks = struct.unpack_from("<IH", body, 0)
            print(f" page size {len(body) + 4}, dictionary at {dict_off:#x}, {dict_blocks} blocks of 512")
        else:
            print()


def modules(path: Path) -> None:
    """Library members: module name, bytes of code and data, public names."""
    current, publics, size, start = None, [], 0, 0
    for pos, rtype, body in records(path.read_bytes()):
        r = Reader(body, big=rtype in BIG)
        if rtype == 0x80:
            current, publics, size, start = r.name(), [], 0, pos
        elif rtype in (0x90, 0x91):
            grp, seg = r.index(), r.index()
            if grp == 0 and seg == 0:
                r.word()
            while r.more():
                publics.append(r.name())
                r.offset()
                r.index()
        elif rtype in (0xA0, 0xA1):
            size += len(body) - (7 if rtype == 0xA1 else 3)
        elif rtype in (0x8A, 0x8B) and current:
            print(f"{start:06X}  {current:<12} {size:6} bytes  {' '.join(publics)}")
            current = None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--bytes", action="store_true", help="show LEDATA contents in hex")
    ap.add_argument("--modules", action="store_true", help="library: one line per member module")
    ap.add_argument("--member", help="library: dump only members whose module name contains this text")
    a = ap.parse_args()
    if a.modules:
        modules(a.file)
    else:
        dump(a.file, a.bytes, a.member)
    return 0


if __name__ == "__main__":
    sys.exit(main())

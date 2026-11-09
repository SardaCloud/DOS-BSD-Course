"""mzdump.py -- print the header and relocation table of an MS-DOS .EXE ("MZ") file.

    python mzdump.py HELLO.EXE              header fields and the first 20 relocations
    python mzdump.py HELLO.EXE --all        every relocation
    python mzdump.py HELLO.EXE --quiet      header only

Module 5 lab tool (MS-DOS 4.00 vs FreeBSD 15.1). The field names in the second column are those of
the EXE_file structure in MS-DOS 4.00's v4.0/src/INC/EXE.INC; the first column gives the names
used in most later documentation (e_magic, e_cblp, ...).

    +----------------------+ file offset 0
    | header (28 bytes)    |
    | relocation table     | e_crlc entries of 4 bytes (offset, segment) at e_lfarlc
    | padding              |
    +----------------------+ e_cparhdr * 16
    | load image           | copied to memory at the load segment;
    |                      | every relocated word gets the load segment added
    +----------------------+ end of file: (e_cp - 1) * 512 + e_cblp  (e_cblp = 0: e_cp * 512)
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

FIELDS = [  # (common name, EXE.INC name, meaning)
    ("e_magic", "exe_signature", "signature 'MZ' (4D5Ah)"),
    ("e_cblp", "exe_len_mod_512", "bytes used in the last 512-byte page"),
    ("e_cp", "exe_pages", "number of 512-byte pages in the file"),
    ("e_crlc", "exe_rle_count", "number of relocation entries"),
    ("e_cparhdr", "exe_par_dir", "header size in 16-byte paragraphs"),
    ("e_minalloc", "exe_min_BSS", "extra paragraphs needed after the image"),
    ("e_maxalloc", "exe_max_BSS", "extra paragraphs wanted after the image"),
    ("e_ss", "exe_SS", "initial SS, relative to the load segment"),
    ("e_sp", "exe_SP", "initial SP"),
    ("e_csum", "exe_chksum", "checksum (ignored by MS-DOS)"),
    ("e_ip", "exe_IP", "initial IP"),
    ("e_cs", "exe_CS", "initial CS, relative to the load segment"),
    ("e_lfarlc", "exe_rle_table", "file offset of the relocation table"),
    ("e_ovno", "exe_iov", "overlay number (0 = main program)"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--all", action="store_true", help="list every relocation entry")
    ap.add_argument("--quiet", action="store_true", help="header only, no relocations")
    a = ap.parse_args()

    data = a.file.read_bytes()
    if len(data) < 28 or data[:2] not in (b"MZ", b"ZM"):
        print(f"{a.file}: no MZ signature: MS-DOS would load it as a .COM memory image")
        return 1
    h = dict(zip([f[0] for f in FIELDS], struct.unpack_from("<14H", data, 0)))

    print(f"{a.file.name}: {len(data)} bytes")
    for name, inc, meaning in FIELDS:
        print(f"  {name:<11} {inc:<16} {h[name]:#06x} {h[name]:6}   {meaning}")

    header = h["e_cparhdr"] * 16
    file_size = (h["e_cp"] - 1) * 512 + h["e_cblp"] if h["e_cblp"] else h["e_cp"] * 512
    image = file_size - header
    print()
    print(f"  header + relocation table : {header} bytes")
    print(f"  load image                : {image} bytes ({(image + 15) // 16} paragraphs),"
          f" file offsets {header:#x}-{file_size - 1:#x}")
    if file_size > len(data):
        print(f"  note: the file ends {file_size - len(data)} bytes before the end the header describes;"
              " EXEC accepts a final read that is short by less than 512 bytes")
    elif file_size < len(data):
        print(f"  note: {len(data) - file_size} bytes follow the load image"
              " (overlays or debug information: EXEC does not load them)")
    print(f"  memory needed             : image + {h['e_minalloc']} paragraphs"
          f" = {(image + 15) // 16 + h['e_minalloc']} paragraphs"
          f" ({((image + 15) // 16 + h['e_minalloc']) * 16} bytes), plus 16 paragraphs for the PSP")
    if h["e_minalloc"] == 0 and h["e_maxalloc"] == 0:
        print("  e_minalloc = e_maxalloc = 0: EXEC loads this program at the top of memory")
    print(f"  entry point CS:IP         : {h['e_cs']:04X}:{h['e_ip']:04X} + load segment")
    print(f"  initial stack SS:SP       : {h['e_ss']:04X}:{h['e_sp']:04X} + load segment")
    stub = header + h["e_cs"] * 16                 # where the entry segment starts in the file
    if h["e_ip"] >= 2 and data[stub + h["e_ip"] - 2:stub + h["e_ip"]] == b"RB":
        real_ip, real_cs, _, _, real_sp, real_ss = struct.unpack_from("<6H", data, stub)
        print("  packed by LINK /EXEPACK ('RB' just before the entry point): the entry point is an unpacker")
        print("    that expands the image, applies the packed relocations and jumps to the program's")
        print(f"    own entry point {real_cs:04X}:{real_ip:04X} with stack {real_ss:04X}:{real_sp:04X}")

    if a.quiet:
        return 0
    print()
    print(f"  relocation table: {h['e_crlc']} entries at file offset {h['e_lfarlc']:#x}")
    if h["e_crlc"]:
        print("    entry  seg:off    image offset  word before loading")
    shown = h["e_crlc"] if a.all else min(h["e_crlc"], 20)
    for i in range(shown):
        off, seg = struct.unpack_from("<HH", data, h["e_lfarlc"] + 4 * i)
        where = seg * 16 + off                     # offset of the word inside the load image
        word = struct.unpack_from("<H", data, header + where)[0] if header + where + 2 <= len(data) else None
        shown_word = f"{word:#06x}" if word is not None else "(outside the file)"
        print(f"    {i:5}  {seg:04X}:{off:04X}  {where:#08x}      {shown_word}")
    if shown < h["e_crlc"]:
        print(f"    ... {h['e_crlc'] - shown} more (use --all)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

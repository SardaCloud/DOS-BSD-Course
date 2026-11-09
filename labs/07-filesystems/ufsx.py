"""ufsx.py - a read-only UFS2 explorer (Module 7, Lab 7.5).

Reads a UFS2 file system from a raw image: a partition copied out with vhdpart.py, a file
made with mdconfig + newfs and dd, or (as root, in FreeBSD) a device such as /dev/md0.

    python ufsx.py IMAGE sb                   superblock (compare: dumpfs -m, dumpfs | head)
    python ufsx.py IMAGE cg N                 cylinder group N header and maps (compare: dumpfs)
    python ufsx.py IMAGE layout [N]           where the first N cylinder groups put their parts
    python ufsx.py IMAGE inode INO            one inode, field by field (compare: fsdb 'inode INO')
    python ufsx.py IMAGE ls PATH              directory entries as stored: d_ino, d_reclen, d_type, name
    python ufsx.py IMAGE namei PATH           resolve a path one component at a time
    python ufsx.py IMAGE blocks PATH          logical block -> fragment address map, with indirect blocks
    python ufsx.py IMAGE cat PATH [OUTFILE]   read a file through its block pointers

Structures follow FreeBSD 15.1 (release/15.1.0):
  struct fs, struct cg, cg macros      sys/ufs/ffs/fs.h
  struct ufs2_dinode, UFS_NDADDR       sys/ufs/ufs/dinode.h
  struct direct, DIRBLKSIZ             sys/ufs/ufs/dir.h
All integers are little-endian (amd64). Block addresses in inodes count fragments (fs_fsize bytes).
"""
from __future__ import annotations

import struct
import sys
import time

SBLOCK_UFS2 = 65536            # fs.h: SBLOCK_UFS2
FS_UFS2_MAGIC = 0x19540119     # fs.h
CG_MAGIC = 0x090255            # fs.h
UFS_ROOTINO = 2                # dinode.h
UFS_NDADDR, UFS_NIADDR = 12, 3  # dinode.h
DINODE2_SIZE = 256             # sizeof(struct ufs2_dinode)

FS_FLAGS = [(0x01, "FS_UNCLEAN"), (0x02, "FS_DOSOFTDEP (soft updates)"), (0x04, "FS_NEEDSFSCK"),
            (0x08, "FS_SUJ (soft updates journal)"), (0x10, "FS_ACLS"), (0x20, "FS_MULTILABEL"),
            (0x40, "FS_GJOURNAL"), (0x80, "FS_FLAGS_UPDATED"), (0x100, "FS_NFS4ACLS"),
            (0x200, "FS_METACKHASH"), (0x400, "FS_TRIM"), (0x01000000, "FS_INDEXDIRS")]
TYPES = {0o010000: "fifo", 0o020000: "chr", 0o040000: "dir", 0o060000: "blk", 0o100000: "reg",
         0o120000: "lnk", 0o140000: "sock", 0o160000: "wht"}
DT = {0: "unknown", 1: "fifo", 2: "chr", 4: "dir", 6: "blk", 8: "reg", 10: "lnk", 12: "sock", 14: "wht"}

# struct fs: (name, byte offset, struct format); offsets follow the declaration order in fs.h
FS_FIELDS = [
    ("fs_sblkno", 8, "i"), ("fs_cblkno", 12, "i"), ("fs_iblkno", 16, "i"), ("fs_dblkno", 20, "i"),
    ("fs_ncg", 44, "I"), ("fs_bsize", 48, "i"), ("fs_fsize", 52, "i"), ("fs_frag", 56, "i"),
    ("fs_minfree", 60, "i"), ("fs_bshift", 80, "i"), ("fs_fshift", 84, "i"), ("fs_maxcontig", 88, "i"),
    ("fs_maxbpg", 92, "i"), ("fs_fragshift", 96, "i"), ("fs_fsbtodb", 100, "i"), ("fs_sbsize", 104, "i"),
    ("fs_nindir", 116, "i"), ("fs_inopb", 120, "I"), ("fs_optim", 128, "i"), ("fs_id", 144, "2i"),
    ("fs_cssize", 156, "i"), ("fs_cgsize", 160, "i"), ("fs_ipg", 184, "I"), ("fs_fpg", 188, "i"),
    ("fs_fmod", 208, "b"), ("fs_clean", 209, "b"), ("fs_ronly", 210, "b"), ("fs_old_flags", 211, "B"),
    ("fs_fsmnt", 212, "468s"), ("fs_volname", 680, "32s"), ("fs_swuid", 712, "Q"),
    ("fs_maxbsize", 860, "i"), ("fs_unrefs", 864, "q"), ("fs_providersize", 872, "q"),
    ("fs_metaspace", 880, "q"), ("fs_sblockactualloc", 992, "q"), ("fs_sblockloc", 1000, "q"),
    ("fs_cstotal", 1008, "5q"), ("fs_time", 1072, "q"), ("fs_size", 1080, "q"), ("fs_dsize", 1088, "q"),
    ("fs_csaddr", 1096, "q"), ("fs_avgfilesize", 1196, "I"), ("fs_avgfpdir", 1200, "I"),
    ("fs_mtime", 1208, "q"), ("fs_sujfree", 1216, "i"), ("fs_ckhash", 1304, "I"), ("fs_metackhash", 1308, "I"),
    ("fs_flags", 1312, "i"), ("fs_contigsumsize", 1316, "i"), ("fs_maxsymlinklen", 1320, "i"),
    ("fs_maxfilesize", 1328, "Q"), ("fs_state", 1352, "i"), ("fs_magic", 1372, "i"),
]

# struct ufs2_dinode (dinode.h gives the offsets in its comments)
DI_FIELDS = [
    ("di_mode", 0, "H"), ("di_nlink", 2, "H"), ("di_uid", 4, "I"), ("di_gid", 8, "I"), ("di_blksize", 12, "I"),
    ("di_size", 16, "Q"), ("di_blocks", 24, "Q"), ("di_atime", 32, "q"), ("di_mtime", 40, "q"),
    ("di_ctime", 48, "q"), ("di_birthtime", 56, "q"), ("di_mtimensec", 64, "i"), ("di_atimensec", 68, "i"),
    ("di_ctimensec", 72, "i"), ("di_birthnsec", 76, "i"), ("di_gen", 80, "I"), ("di_kernflags", 84, "I"),
    ("di_flags", 88, "I"), ("di_extsize", 92, "I"), ("di_extb", 96, "2q"), ("di_db", 112, "12q"),
    ("di_ib", 208, "3q"), ("di_modrev", 232, "Q"), ("di_dirdepth", 240, "I"), ("di_ckhash", 244, "I"),
]


def unpack_fields(buf: bytes, fields, base: int = 0) -> dict:
    out = {}
    for name, off, fmt in fields:
        v = struct.unpack_from("<" + fmt, buf, base + off)
        out[name] = v if len(v) > 1 else v[0]
    return out


def utc(t: int, ns: int | None = None) -> str:
    s = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))
    return s + (f".{ns:09d}" if ns is not None else "") + " UTC"


class Ufs:
    def __init__(self, path: str):
        self.f = open(path, "rb")
        self.sb = unpack_fields(self.read(SBLOCK_UFS2, 1376), FS_FIELDS)
        if self.sb["fs_magic"] != FS_UFS2_MAGIC:
            raise SystemExit(f"no UFS2 superblock at byte {SBLOCK_UFS2} (magic {self.sb['fs_magic']:#x})")
        s = self.sb
        self.fsize, self.bsize, self.frag = s["fs_fsize"], s["fs_bsize"], s["fs_frag"]
        self.ipg, self.fpg, self.inopb, self.nindir = s["fs_ipg"], s["fs_fpg"], s["fs_inopb"], s["fs_nindir"]

    def read(self, off: int, n: int) -> bytes:
        self.f.seek(off)
        data = self.f.read(n)
        return data + bytes(n - len(data))

    def frag_bytes(self, daddr: int, n: int) -> bytes:
        return self.read(daddr * self.fsize, n)

    # fs.h macros (UFS2: cgstart == cgbase)
    def cgbase(self, c: int) -> int:
        return self.fpg * c

    def cgtod(self, c: int) -> int:
        return self.cgbase(c) + self.sb["fs_cblkno"]

    def cgimin(self, c: int) -> int:
        return self.cgbase(c) + self.sb["fs_iblkno"]

    def cgdmin(self, c: int) -> int:
        return self.cgbase(c) + self.sb["fs_dblkno"]

    def cgsblock(self, c: int) -> int:
        return self.cgbase(c) + self.sb["fs_sblkno"]

    def ino_to_cg(self, ino: int) -> int:
        return ino // self.ipg

    def ino_to_fsba(self, ino: int) -> int:
        return self.cgimin(self.ino_to_cg(ino)) + (ino % self.ipg) // self.inopb * self.frag

    def ino_to_fsbo(self, ino: int) -> int:
        return ino % self.inopb

    def inode(self, ino: int) -> dict:
        off = self.ino_to_fsba(ino) * self.fsize + self.ino_to_fsbo(ino) * DINODE2_SIZE
        di = unpack_fields(self.read(off, DINODE2_SIZE), DI_FIELDS)
        di["_offset"] = off
        return di

    def block_size(self, di: dict, lbn: int) -> int:
        # ffs blksize(): the last block of a small file may be only some fragments
        size = di["di_size"]
        if lbn >= UFS_NDADDR or size >= (lbn + 1) * self.bsize:
            return self.bsize
        rest = size - lbn * self.bsize
        return -(-rest // self.fsize) * self.fsize

    def bmap(self, di: dict):
        """Yield (logical block, fragment address, level, via) for every allocated data block."""
        nblocks = -(-di["di_size"] // self.bsize)
        for lbn in range(min(nblocks, UFS_NDADDR)):
            yield lbn, di["di_db"][lbn], 0, None
        lbn = UFS_NDADDR
        for level, ib in enumerate(di["di_ib"], start=1):
            if lbn >= nblocks:
                return
            span = self.nindir ** level
            yield from self._indirect(ib, level, lbn, nblocks)
            lbn += span

    def _indirect(self, addr: int, level: int, first: int, nblocks: int):
        if addr == 0:
            return
        ptrs = struct.unpack_from(f"<{self.nindir}q", self.frag_bytes(addr, self.bsize))
        span = self.nindir ** (level - 1)
        for i, p in enumerate(ptrs):
            lbn = first + i * span
            if lbn >= nblocks:
                return
            if level == 1:
                yield lbn, p, 1, addr
            else:
                yield from self._indirect(p, level - 1, lbn, nblocks)

    def read_file(self, di: dict) -> bytes:
        out = bytearray()
        for lbn, addr, _, _ in self.bmap(di):
            n = self.block_size(di, lbn)
            out += self.frag_bytes(addr, n) if addr else bytes(n)
        return bytes(out[:di["di_size"]])

    def dirents(self, di: dict):
        data = self.read_file(di)
        for blk in range(0, len(data), 512):           # dir.h: DIRBLKSIZ = DEV_BSIZE = 512
            off = blk
            while off < min(blk + 512, len(data)):
                ino, reclen, dtype, namlen = struct.unpack_from("<IHBB", data, off)
                if reclen == 0:
                    break
                name = data[off + 8:off + 8 + namlen].decode("utf-8", "replace")
                yield off, ino, reclen, dtype, namlen, name
                off += reclen

    def namei(self, path: str, trace: bool = False) -> int:
        ino = UFS_ROOTINO
        for comp in [p for p in path.split("/") if p]:
            di = self.inode(ino)
            if di["di_mode"] & 0o170000 != 0o040000:
                raise SystemExit(f"{comp}: parent is not a directory")
            for _, dino, _, _, _, name in self.dirents(di):
                if dino and name == comp:
                    if trace:
                        print(f"  in directory inode {ino}: '{comp}' -> inode {dino}")
                    ino = dino
                    break
            else:
                raise SystemExit(f"{path}: '{comp}' not found")
        return ino


def mode_text(mode: int) -> str:
    kind = TYPES.get(mode & 0o170000, "?")
    perms = "".join((c if mode & (1 << (8 - i)) else "-") for i, c in enumerate("rwxrwxrwx"))
    return f"{mode:06o} ({kind}, {perms})"


def cmd_sb(u: Ufs, args) -> None:
    s = u.sb
    print(f"superblock at byte {SBLOCK_UFS2} (fs_sblockloc {s['fs_sblockloc']}), "
          f"magic {s['fs_magic']:#x} = FS_UFS2_MAGIC")
    print(f"fs_volname '{s['fs_volname'].rstrip(bytes(1)).decode()}', fs_fsmnt "
          f"'{s['fs_fsmnt'].rstrip(bytes(1)).decode()}', fs_id {s['fs_id'][0]:08x} {s['fs_id'][1]:08x}")
    print(f"fs_time {utc(s['fs_time'])}, fs_mtime {utc(s['fs_mtime']) if s['fs_mtime'] else 0}")
    print(f"fs_bsize {s['fs_bsize']}  fs_fsize {s['fs_fsize']}  fs_frag {s['fs_frag']}  "
          f"fs_fsbtodb {s['fs_fsbtodb']}  (1 fragment = {1 << s['fs_fsbtodb']} sectors of 512)")
    print(f"fs_size {s['fs_size']} fragments = {s['fs_size'] * u.fsize} bytes; fs_dsize {s['fs_dsize']}; "
          f"fs_providersize {s['fs_providersize']}")
    print(f"fs_ncg {s['fs_ncg']}  fs_fpg {s['fs_fpg']} fragments ({s['fs_fpg'] * u.fsize // 2**20} MiB) per group  "
          f"fs_ipg {s['fs_ipg']} inodes per group")
    print(f"fs_sblkno {s['fs_sblkno']}  fs_cblkno {s['fs_cblkno']}  fs_iblkno {s['fs_iblkno']}  "
          f"fs_dblkno {s['fs_dblkno']}  (fragment offsets inside each group)")
    print(f"fs_inopb {s['fs_inopb']} inodes per block  fs_nindir {s['fs_nindir']} pointers per indirect block")
    print(f"fs_minfree {s['fs_minfree']}%  fs_optim {('time', 'space')[s['fs_optim']]}  "
          f"fs_maxbpg {s['fs_maxbpg']}  fs_maxcontig {s['fs_maxcontig']}  fs_metaspace {s['fs_metaspace']}")
    print(f"fs_avgfilesize {s['fs_avgfilesize']}  fs_avgfpdir {s['fs_avgfpdir']}  "
          f"fs_maxsymlinklen {s['fs_maxsymlinklen']}  fs_maxfilesize {s['fs_maxfilesize']}")
    nd, nb, ni, nf, nc = s["fs_cstotal"]
    print(f"fs_cstotal: {nd} directories, {nb} free blocks, {ni} free inodes, {nf} free fragments, "
          f"{nc} free clusters")
    print(f"fs_clean {s['fs_clean']}  fs_flags {s['fs_flags']:#x}: "
          + (", ".join(n for b, n in FS_FLAGS if s["fs_flags"] & b) or "none"))
    print(f"fs_metackhash {s['fs_metackhash']:#x}  fs_ckhash {s['fs_ckhash']:#010x}  fs_sujfree {s['fs_sujfree']}")


def cmd_layout(u: Ufs, args) -> None:
    n = int(args[0]) if args else 4
    print(f"{'cg':>4} {'cgbase':>10} {'superblock':>10} {'cg block':>10} {'inodes':>10} {'data':>10}  (fragments)")
    for c in range(min(n, u.sb["fs_ncg"])):
        print(f"{c:4} {u.cgbase(c):10} {u.cgsblock(c):10} {u.cgtod(c):10} {u.cgimin(c):10} {u.cgdmin(c):10}")
    ib = u.sb["fs_ipg"] * DINODE2_SIZE
    print(f"each group: {u.sb['fs_ipg']} inodes x {DINODE2_SIZE} bytes = {ib} bytes of inodes "
          f"({ib // u.fsize} fragments) at fs_iblkno")


def popcount_bits(buf: bytes) -> int:
    return sum(bin(b).count("1") for b in buf)


def cmd_cg(u: Ufs, args) -> None:
    c = int(args[0]) if args else 0
    off = u.cgtod(c) * u.fsize
    raw = u.read(off, u.sb["fs_cgsize"])
    (magic,) = struct.unpack_from("<i", raw, 4)
    (cgx,) = struct.unpack_from("<I", raw, 12)
    (ndblk,) = struct.unpack_from("<I", raw, 20)
    ndir, nbfree, nifree, nffree = struct.unpack_from("<4i", raw, 24)
    rotor, frotor, irotor = struct.unpack_from("<3I", raw, 40)
    frsum = struct.unpack_from("<8I", raw, 52)
    iusedoff, freeoff, nextfreeoff, clsumoff, cloff, nclblks, niblk, initediblk, unrefs = \
        struct.unpack_from("<9I", raw, 92)
    (ckhash,) = struct.unpack_from("<I", raw, 132)
    (cgtime,) = struct.unpack_from("<q", raw, 136)
    print(f"cylinder group {c} header at fragment {u.cgtod(c)} (byte {off}): "
          f"cg_magic {magic:#x}{' = CG_MAGIC' if magic == CG_MAGIC else ' BAD'}, cg_cgx {cgx}")
    print(f"cg_time {utc(cgtime)}  cg_ndblk {ndblk} fragments  cg_niblk {niblk}  cg_initediblk {initediblk}")
    print(f"cg_cs: {ndir} directories, {nbfree} free blocks, {nifree} free inodes, {nffree} free fragments")
    print(f"cg_rotor {rotor}  cg_frotor {frotor}  cg_irotor {irotor}  cg_frsum {list(frsum)}")
    used = popcount_bits(raw[iusedoff:iusedoff + (u.ipg + 7) // 8])
    free = popcount_bits(raw[freeoff:freeoff + (ndblk + 7) // 8])
    print(f"inode map at +{iusedoff}: {used} of {u.ipg} inodes in use; "
          f"free-fragment map at +{freeoff}: {free} of {ndblk} fragments free")
    first = raw[iusedoff:iusedoff + 4]
    print(f"first bytes of the inode map {first.hex(' ')}  (bit i = inode {c * u.ipg} + i in use)")
    print(f"cg_ckhash {ckhash:#010x}")


def cmd_inode(u: Ufs, args) -> None:
    ino = int(args[0], 0)
    di = u.inode(ino)
    print(f"inode {ino}: cylinder group {u.ino_to_cg(ino)}, inode block at fragment {u.ino_to_fsba(ino)}, "
          f"slot {u.ino_to_fsbo(ino)}, byte {di['_offset']}")
    print(f"  di_mode      {mode_text(di['di_mode'])}")
    print(f"  di_nlink     {di['di_nlink']}")
    print(f"  di_uid/gid   {di['di_uid']} / {di['di_gid']}")
    print(f"  di_size      {di['di_size']}")
    print(f"  di_blocks    {di['di_blocks']} (512-byte units = {di['di_blocks'] * 512} bytes held)")
    print(f"  di_blksize   {di['di_blksize']}   di_flags {di['di_flags']:#x}   di_gen {di['di_gen']:#x}")
    for t in ("atime", "mtime", "ctime"):
        print(f"  di_{t:9}  {utc(di['di_' + t], di['di_' + t + 'nsec'])}")
    print(f"  di_birthtime {utc(di['di_birthtime'], di['di_birthnsec'])}")
    if di["di_mode"] & 0o170000 == 0o120000 and di["di_size"] < 120 and di["di_db"][0] != 0:
        raw = u.read(di["_offset"] + 112, di["di_size"])
        print(f"  di_shortlink '{raw.decode()}' (symbolic link stored in the inode itself)")
        return
    print(f"  di_db        {list(di['di_db'])}")
    print(f"  di_ib        {list(di['di_ib'])}")
    print(f"  di_extsize   {di['di_extsize']}  di_dirdepth {di['di_dirdepth']}  di_ckhash {di['di_ckhash']:#010x}")


def cmd_ls(u: Ufs, args) -> None:
    ino = u.namei(args[0] if args else "/")
    di = u.inode(ino)
    print(f"directory inode {ino}, {di['di_size']} bytes")
    print(f"{'offset':>6} {'d_ino':>8} {'d_reclen':>8} {'d_type':>7} {'d_namlen':>8}  d_name")
    for off, dino, reclen, dtype, namlen, name in u.dirents(di):
        print(f"{off:6} {dino:8} {reclen:8} {DT.get(dtype, dtype):>7} {namlen:8}  {name}")


def cmd_namei(u: Ufs, args) -> None:
    print(f"start at the root directory, inode {UFS_ROOTINO} (UFS_ROOTINO)")
    ino = u.namei(args[0], trace=True)
    di = u.inode(ino)
    print(f"{args[0]} is inode {ino}: {mode_text(di['di_mode'])}, {di['di_size']} bytes")


def cmd_blocks(u: Ufs, args) -> None:
    ino = u.namei(args[0])
    di = u.inode(ino)
    rows = list(u.bmap(di))
    print(f"{args[0]}: inode {ino}, {di['di_size']} bytes, {len(rows)} logical blocks of {u.bsize}")
    shown = set()
    for lbn, addr, level, via in rows:
        if len(rows) > 20 and 4 <= lbn < len(rows) - 3 and lbn not in (UFS_NDADDR - 1, UFS_NDADDR):
            if "..." not in shown:
                print("   ...")
                shown.add("...")
            continue
        where = f"di_db[{lbn}]" if level == 0 else f"indirect block at {via}"
        print(f"  lbn {lbn:6} -> fragment {addr:10} (byte {addr * u.fsize:>12}, {u.block_size(di, lbn):5} bytes)"
              f"  via {where}")
    print(f"single indirect di_ib[0] = {di['di_ib'][0]}, double di_ib[1] = {di['di_ib'][1]}, "
          f"triple di_ib[2] = {di['di_ib'][2]}")


def cmd_cat(u: Ufs, args) -> None:
    di = u.inode(u.namei(args[0]))
    data = u.read_file(di)
    if len(args) > 1:
        with open(args[1], "wb") as f:
            f.write(data)
        print(f"{len(data)} bytes written to {args[1]}")
    else:
        sys.stdout.buffer.write(data)


COMMANDS = {"sb": cmd_sb, "cg": cmd_cg, "layout": cmd_layout, "inode": cmd_inode, "ls": cmd_ls,
            "namei": cmd_namei, "blocks": cmd_blocks, "cat": cmd_cat}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        return 2
    COMMANDS[argv[1]](Ufs(argv[0]), argv[2:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

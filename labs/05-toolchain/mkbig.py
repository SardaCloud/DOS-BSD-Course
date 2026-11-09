"""mkbig.py -- Module 5, Lab 5.4: pad a .COM image with zero bytes to an exact size.

    python mkbig.py BIGCOM.BIN BIG1.COM 65279
    python mkbig.py BIGCOM.BIN BIG2.COM 65280
"""
import sys
from pathlib import Path

src, dst, size = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
code = src.read_bytes()
if len(code) > size:
    raise SystemExit(f"{src} is already {len(code)} bytes")
dst.write_bytes(code + bytes(size - len(code)))
print(f"{dst}: {size} bytes ({size:#x})")
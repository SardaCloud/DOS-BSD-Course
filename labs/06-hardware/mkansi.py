"""Generate the ANSI.SYS test files for Lab 6.4 (CRLF line endings, ESC = 1Bh).

    python mkansi.py      writes ANSIDEMO.TXT, REMAP.TXT and DSR.TXT next to this script
"""
from pathlib import Path

ESC = "\x1b"
HERE = Path(__file__).resolve().parent

demo = [
    f"{ESC}[2J",                                            # erase display, cursor home
    f"{ESC}[3;10HThis is row 3, column 10",                  # cursor position (1-based)
    f"{ESC}[5;1H{ESC}[1;33;44mBright yellow on blue{ESC}[0m and normal again",
    f"{ESC}[7;1H{ESC}[7mReverse video{ESC}[0m",
    f"{ESC}[9;1HEnd of ANSIDEMO.TXT",
]
remap = [
    f'{ESC}[97;"hello"p' + "Key a now types hello",    # key reassignment: 'a' (97) -> "hello"
]

dsr = [f"{ESC}[6n"]                                        # device status report: where is the cursor?

for name, lines in (("ANSIDEMO.TXT", demo), ("REMAP.TXT", remap)):
    (HERE / name).write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))
    print(name, (HERE / name).stat().st_size, "bytes")
(HERE / "DSR.TXT").write_bytes(dsr[0].encode("ascii"))         # no CR LF: only the request
print("DSR.TXT", (HERE / "DSR.TXT").stat().st_size, "bytes")

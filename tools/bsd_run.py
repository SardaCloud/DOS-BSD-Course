"""Run commands in the course's FreeBSD 15.1 virtual machine (Hyper-V) over SSH and print their output.

    python tools/bsd_run.py "freebsd-version -kru" "truss -f /bin/echo hi"
    python tools/bsd_run.py --put labs/09-toolsmith/wc.c:/root/lab/wc.c "cc -o /root/lab/wc /root/lab/wc.c"
    python tools/bsd_run.py --get /root/lab/out.txt:build/out.txt "..."
    python tools/bsd_run.py --shell          # interactive SSH session

Each command runs in its own `sh -c` as root, in /root/lab (created if missing); output (stdout and
stderr) is printed after a "---- command" line, like tools/dos_run.py does for MS-DOS. --put/--get copy
files with scp before/after the commands. The VM is started if it is off; its address is taken from
Hyper-V (the FreeBSD guest reports it through the Hyper-V key-value-pair service).

Configuration (see course/00-lab.md): VM name FreeBSD151-Course, key build/freebsd/vm/id_course.
Environment overrides: BSD_VM, BSD_HOST (skip Hyper-V lookup), BSD_KEY.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VMDIR = ROOT / "build" / "freebsd" / "vm"
VM = os.environ.get("BSD_VM", "FreeBSD151-Course")
KEY = Path(os.environ.get("BSD_KEY", VMDIR / "id_course"))
KNOWN = VMDIR / "known_hosts"


def ps(cmd: str) -> str:
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    return r.stdout.strip()


def vm_address(start: bool = True) -> str:
    if os.environ.get("BSD_HOST"):
        return os.environ["BSD_HOST"]
    state = ps(f"(Get-VM -Name '{VM}').State")
    if state != "Running":
        if not start:
            raise SystemExit(f"VM {VM} is {state or 'missing'}")
        print(f"(starting VM {VM})", file=sys.stderr)
        ps(f"Start-VM -Name '{VM}'")
    for _ in range(90):
        ips = ps(f"(Get-VMNetworkAdapter -VMName '{VM}').IPAddresses -join ' '").split()
        v4 = [ip for ip in ips if "." in ip]
        if v4 and ssh_ok(v4[0]):
            return v4[0]
        time.sleep(2)
    raise SystemExit(f"VM {VM} did not become reachable over SSH")


def ssh_base(host: str) -> list[str]:
    return ["ssh", "-i", str(KEY), "-o", "BatchMode=yes", "-o", f"UserKnownHostsFile={KNOWN}",
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=8", f"root@{host}"]


def ssh_ok(host: str) -> bool:
    r = subprocess.run(ssh_base(host) + ["true"], capture_output=True)
    return r.returncode == 0


def scp(src: str, dst: str) -> None:
    subprocess.run(["scp", "-q", "-i", str(KEY), "-o", "BatchMode=yes", "-o", f"UserKnownHostsFile={KNOWN}",
                    src, dst], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("commands", nargs="*")
    ap.add_argument("--put", action="append", default=[], metavar="LOCAL:REMOTE")
    ap.add_argument("--get", action="append", default=[], metavar="REMOTE:LOCAL")
    ap.add_argument("--shell", action="store_true", help="open an interactive SSH session")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per command")
    a = ap.parse_args()
    host = vm_address()
    if a.shell:
        return subprocess.call(ssh_base(host)[:-1] + ["-t", f"root@{host}"])
    subprocess.run(ssh_base(host) + ["mkdir -p /root/lab"], check=True)
    for spec in a.put:
        local, _, remote = spec.rpartition(":") if spec.count(":") > 1 else spec.partition(":")
        subprocess.run(ssh_base(host) + [f"mkdir -p \"$(dirname '{remote}')\""], check=True)
        scp(local, f"root@{host}:{remote}")
    rc = 0
    for cmd in a.commands:
        print(f"---- {cmd}", flush=True)
        try:
            r = subprocess.run(ssh_base(host) + [f"cd /root/lab && {cmd}"], capture_output=True,
                               timeout=a.timeout)
        except subprocess.TimeoutExpired:
            print(f"(timed out after {a.timeout} s)")
            rc = 1
            continue
        out = (r.stdout + r.stderr).decode("utf-8", "replace")
        sys.stdout.write(out if out.endswith("\n") or not out else out + "\n")
        if r.returncode:
            print(f"(exit status {r.returncode})")
            rc = r.returncode
    for spec in a.get:
        remote, _, local = spec.partition(":") if not spec[1:3] == ":\\" else (spec, "", "")
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        scp(f"root@{host}:{remote}", local)
    return rc


if __name__ == "__main__":
    sys.exit(main())

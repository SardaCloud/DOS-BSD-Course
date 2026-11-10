# Course pack: MS-DOS 4.00 and FreeBSD 15.1, from the boot sector to the shell

By Francesco Valerio Buccoli ([francesco@buccoli.com](mailto:francesco@buccoli.com)).

A university Operating Systems course built on two real, complete source trees: MS-DOS 4.00, released as open
source by Microsoft and IBM in 2024, and FreeBSD 15.1. Each module follows one part of a PC operating system,
the boot code, the kernel and the shell, through both systems, with every claim tied to a line of source
code at a fixed commit.

## Modules

| Module | Topic | MS-DOS 4.00 | FreeBSD 15.1 |
|---|---|---|---|
| [0. The lab](course/00-lab.md) | Building MS-DOS from source, booting it, the FreeBSD machine | `v4.0/src` build tree | Installation, `/usr/src` |
| [1. Booting](course/01-boot.md) | From the BIOS to the first user program | `FDBOOT`, `MSBOOT`, `MSLOAD`, `SYSINIT`, `CONFIG.SYS` | `mbr`, `boot0`, `boot1`/`boot2`, `gptboot`, BTX, loader, `locore`, `mi_startup`, `SYSINIT()` |
| [2. The kernel](course/02-kernel.md) | System calls, files, memory and programs | INT 21h, SFT/JFT, `FAT.ASM`, MCB arena, `EXEC`, device drivers | `syscall`, file descriptors, `msdosfs`, `vm_map`, `fork`/`execve`, `cdevsw` |
| [3. The shell](course/03-shell.md) | `COMMAND.COM` and `/bin/sh` | Resident/transient design, batch files, pipes through temporary files | Parser and evaluator, real pipes, job control |
| [4. Assembly](course/04-asm.md) | Machine code and assembly language | 8086 real mode, MASM 5.10, `DEBUG`, `INT 21h` | x86-64, NASM and AT&T syntax, `syscall`, libsys stubs |
| [5. The toolchain](course/05-toolchain.md) | From C to a running program | Microsoft C 5.10, OMF, `LINK`, MZ `.EXE` vs `.COM`, memory models, `LIB` | clang, ELF, `ld`, `crt1.o`, shared libraries, `rtld` |
| [6. Hardware](course/06-hardware.md) | BIOS, ports, interrupts, drivers and consoles | BIOS services, port I/O, the device driver chain, `CON`, `CLOCK$`, `ANSI.SYS` | newbus, interrupts, the `vt` console, termios, timecounters |
| [7. File systems](course/07-filesystems.md) | Disks and file systems | FAT12/16, the DPB, `CHKDSK` | UFS2, inodes, soft updates, `msdosfs` |
| [8. Memory and configuration](course/08-memconfig.md) | Memory and configuration in practice | Conventional, upper, expanded and extended memory, `CONFIG.SYS`, EMM386 | Virtual memory, `vmstat`, `rc.conf`, `rc.d`, `sysctl`, `loader.conf` |
| [9. Toolsmith](course/09-toolsmith.md) | The same tools on both systems | Tools in assembly, C and `.BAT` | Tools in assembly, C and `sh` |

Modules 0-3 follow one part of the system through both source trees; Modules 4-9 are hands-on: in every lab
students build or run something on the real MS-DOS 4.00 and on a real FreeBSD 15.1 machine, and every output
shown in the notes was captured that way. Each module has lecture notes with block diagrams, deep study cases
with source listings from both systems, labs and homework. Lab starter files are in `labs/`, and a slide deck
per module is in `slides/`. The HTML edition (`dist/students/index.html`) needs no software: open it in a
browser, also offline.

### Instructor edition

Model answers to every lab question and exercise, grading rubrics, teaching notes and the reference solutions of
all lab programs form a separate instructor edition (`instructor/` and `dist/instructor/`). It is not public, so
that students cannot find the answers. Teachers who use the course can ask the author for it.

## Getting started

[Module 0](course/00-lab.md) sets up the lab: it fetches the pinned sources, builds MS-DOS 4.00 from source in
DOSBox-X, makes a bootable floppy image, and creates the FreeBSD 15.1 virtual machine (Hyper-V, from the
official image) that the FreeBSD labs use. The course was developed and every output captured on Windows 11
with Hyper-V; other hosts and hypervisors should work but have not been tested.

## How the course cites code

| Project | Pinned at | Licence |
|---|---|---|
| MS-DOS 4.00 (`github.com/microsoft/MS-DOS`, folder `v4.0`) | commit `2d04cacc5322951f187bb17e017c12920ac8ebe2` | MIT |
| FreeBSD 15.1 (`github.com/freebsd/freebsd-src`) | tag `release/15.1.0`, commit `96841ea08dcfa84b954a32dc5ae1a26c28966cf4` | BSD (mostly 2-clause) |

Every source listing links to its exact lines at those commits and is checked mechanically against them
(`python tools/check_citations.py`). The sources themselves are not stored in this repository:
`tools/fetch_sources.ps1` fetches them. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Repository layout

| Path | Contents |
|---|---|
| `course/` | Student-facing notes, one Markdown file per module |
| `labs/` | Lab starter files and test data (DOS files keep CRLF line endings) |
| `instructor/` | Instructor edition only: model answers, rubrics, teaching notes and reference solutions in `instructor/code/` |
| `diagrams/` | Block diagrams: JSON specs and the SVG files generated from them |
| `slides/` | Slide outlines (`*.outline.json`) and generated decks (`*.pptx`) |
| `tools/` | Source fetcher, citation checker, MS-DOS build and run tools, FreeBSD VM tools, HTML, diagram and slide builders |
| `dist/` | Generated HTML: `dist/students/` (and `dist/instructor/` in the instructor edition) |
| `src-ext/` | The fetched third-party sources (not committed) |
| `build/` | Build outputs: the MS-DOS build tree, disk images, the FreeBSD VM disk, rendered PNGs (not committed) |

## Tools

| Command | What it does |
|---|---|
| `tools/fetch_sources.ps1` | Fetch both source trees at the pinned commits |
| `python tools/check_citations.py` | Check every citation and listing in the course against the sources |
| `python tools/build_dos.py` | Build MS-DOS 4.00 from source in DOSBox-X (about 2 minutes) |
| `python tools/make_floppy.py` | Make a bootable 1.44 MB floppy image from the build |
| `python tools/dos_run.py ["CMD" ...]` | Boot the image interactively, or run commands on MS-DOS 4.00 and print their output (`--file` adds files to the disk, `--conf-extra` changes the emulated PC, for example its CPU type or memory size, `--keep` saves the disk) |
| `python tools/dos_tools.py --dir DIR "CMD" ...` | Run the 1988 Microsoft toolchain from the source tree (MASM 5.10, C 5.10, `LINK`, `LIB`, `EXE2BIN`) on a folder of your computer |
| `tools/screen.asm` | `SCREEN.COM`: copies the text screen to the output (captures messages printed before `AUTOEXEC.BAT`) |
| `tools/boot_snapshot.ps1` | Boot any disk image in DOSBox-X and save a picture of the screen (boot-sector homework) |
| `tools/new_bsd_vm.ps1` | Create the FreeBSD 15.1 Hyper-V virtual machine from the official disk image |
| `python tools/bsd_run.py ["CMD" ...]` | Run commands in the FreeBSD VM over SSH and print their output (`--put`/`--get` copy files, `--shell` opens a session) |
| `tools/hyperv_console.ps1`, `tools/hyperv_type.ps1` | Type at the FreeBSD VM's console and take screenshots of it (before SSH works) |
| `python tools/diagrams.py [--png]` | Generate the block diagrams in `diagrams/` from their JSON specs (`--png` also renders slide images) |
| `python tools/build_html.py` | Build the self-contained HTML edition in `dist/` |
| `python tools/build_slides.py [--render]` | Build the slide decks from `slides/*.outline.json` (verifying every code slide) in the default 4:3 retro conference style (`tools/slides_retro.py`, all artwork generated); `--style modern` gives 16:9 light decks; `--render` exports PNGs through PowerPoint |

## Licence and trademarks

The course (notes, slides, diagrams, labs and tools) is released under the [MIT License](LICENSE). The quoted
MS-DOS and FreeBSD code remains under its own licences; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The Sarda Cloud name and logo are trademarks of Sarda Cloud Srl and are not licensed under the MIT License.
MS-DOS and Windows are trademarks of the Microsoft group of companies; FreeBSD is a registered trademark of The
FreeBSD Foundation. This course is independent and is not affiliated with or endorsed by Microsoft, IBM or The
FreeBSD Foundation.

---

A Sarda Cloud Community project. Copyright (C) 2026 Francesco Valerio Buccoli.

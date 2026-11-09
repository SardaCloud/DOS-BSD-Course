# Third-party notices

This course pack quotes and links to source code from two projects. Each excerpt
names its file and line range and links to the exact lines at the pinned commit.
No third-party source files are included in this repository; `tools/fetch_sources.ps1`
downloads them into `src-ext/` (which is not committed).

The instructor edition, which is distributed separately, also contains two files
derived from these projects: `instructor/code/09-toolsmith/homework/dos/CAT.C`, a
port of FreeBSD's `bin/cat/cat.c` that keeps its BSD-3-Clause header, and
`instructor/code/08-memconfig/emm386-286fix.diff`, a patch to MS-DOS 4.00's
`EMM386` source (MIT License, below).

## MS-DOS 4.00

Source: https://github.com/microsoft/MS-DOS at commit
`2d04cacc5322951f187bb17e017c12920ac8ebe2` (folder `v4.0`). License text as
published in that repository:

```text
MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE
```

MS-DOS is a trademark of Microsoft Corporation. This course is not affiliated
with or endorsed by Microsoft.

## FreeBSD 15.1

Source: https://github.com/freebsd/freebsd-src at tag `release/15.1.0`
(commit `96841ea08dcfa84b954a32dc5ae1a26c28966cf4`). The compilation is
distributed under the terms below (first section of the `COPYRIGHT` file at
that commit); individual files carry their own copyright and licence headers,
which apply to the excerpts taken from them.

```text
The compilation of software known as FreeBSD is distributed under the
following terms:

Copyright (c) 1992-2025 The FreeBSD Project.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS `AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
```

The full `COPYRIGHT` file:
https://github.com/freebsd/freebsd-src/blob/96841ea08dcfa84b954a32dc5ae1a26c28966cf4/COPYRIGHT

FreeBSD is a registered trademark of The FreeBSD Foundation. This course is not
affiliated with or endorsed by The FreeBSD Foundation.

## Lab tools

The lab instructions (`course/00-lab.md`) use DOSBox-X (GPL-2.0), QEMU (GPL-2.0)
and NASM (BSD-2-Clause). They are downloaded by each student from their official
sites and are not redistributed here.

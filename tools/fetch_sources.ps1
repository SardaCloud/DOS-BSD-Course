# Fetches the pinned third-party sources the course cites into src-ext\ (git-ignored).
#   src-ext\MS-DOS        microsoft/MS-DOS @ 2d04cac (MIT)
#   src-ext\freebsd-src   freebsd/freebsd-src @ release/15.1.0 (sparse: boot code, kernel subsystems, sh)
[CmdletBinding()]
param([string]$Root = (Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference = 'Stop'
$ext = Join-Path $Root 'src-ext'
New-Item -ItemType Directory -Force $ext | Out-Null

$DosSha = '2d04cacc5322951f187bb17e017c12920ac8ebe2'
$BsdTag = 'release/15.1.0'
$BsdSha = '96841ea08dcfa84b954a32dc5ae1a26c28966cf4'
$BsdPaths = @('stand/i386', 'stand/common', 'stand/libsa', 'sys/kern', 'sys/sys', 'sys/amd64/amd64',
              'sys/amd64/include', 'sys/x86/x86', 'sys/x86/include', 'sys/fs/msdosfs', 'sys/vm',
              'sys/geom', 'bin/sh', 'sbin/fdisk', 'usr.sbin/boot0cfg', 'sys/i386/include',
              'stand/lua', 'stand/defaults', 'stand/forth', 'sbin/init', 'lib/libc/sys', 'sys/dev/null',
              'lib/libc/amd64', 'lib/libsys/amd64', 'include', 'share/examples/kld', 'share/mk',
              'sys/amd64/conf', 'sys/conf', 'usr.bin/alias', 'usr.bin/login', 'lib/libsys', 'lib/libc/stdlib',
              # Modules 5-8: toolchain, hardware, file systems, memory and configuration
              'sys/ufs', 'sys/dev/vt', 'sys/dev/atkbdc', 'sys/dev/kbd', 'sys/x86/isa', 'sys/dev/uart',
              'sys/isa', 'sys/dev/md', 'sys/dev/pci', 'sys/dev/hyperv', 'libexec/rtld-elf', 'libexec/rc',
              'lib/csu', 'lib/libc', 'sbin/newfs', 'sbin/dumpfs', 'sbin/fsck_ffs', 'sbin/fsdb', 'sbin/tunefs',
              'sbin/mdconfig', 'sbin/sysctl', 'sbin/newfs_msdos', 'sbin/mount_msdosfs', 'usr.bin/ldd',
              'usr.bin/procstat', 'usr.bin/truss', 'usr.bin/vmstat', 'usr.bin/top', 'usr.sbin/devinfo',
              'usr.sbin/pciconf', 'sbin/rcorder', 'usr.sbin/sysrc', 'usr.sbin/service', 'stand/userboot', 'bin/cat',
              'sbin/geom', 'lib/geom', 'usr.sbin/diskinfo', 'usr.sbin/makefs', 'sbin/mount', 'lib/libufs',
              'sys/teken', 'sys/dev/kbdmux', 'bin/stty', 'sys/dev/speaker', 'contrib/jemalloc', 'usr.sbin/nologin',
              'usr.bin/wc', 'usr.bin/hexdump', 'usr.bin/script', 'bin/test', 'bin/timeout', 'bin/cp', 'usr.bin/xargs',
              'sys/dev/hwpmc')

function Invoke-Git { & git @args; if ($LASTEXITCODE) { throw "git $args failed ($LASTEXITCODE)" } }

$dos = Join-Path $ext 'MS-DOS'
if (-not (Test-Path (Join-Path $dos '.git'))) {
    Invoke-Git -c core.autocrlf=false clone --quiet https://github.com/microsoft/MS-DOS.git $dos
}
Invoke-Git -C $dos -c advice.detachedHead=false checkout --quiet $DosSha

$bsd = Join-Path $ext 'freebsd-src'
if (-not (Test-Path (Join-Path $bsd '.git'))) {
    Invoke-Git -c core.autocrlf=false -c advice.detachedHead=false clone --quiet --depth 1 --filter=blob:none --sparse --branch $BsdTag https://github.com/freebsd/freebsd-src.git $bsd
}
Invoke-Git -C $bsd sparse-checkout set @BsdPaths
$head = (& git -C $bsd rev-parse HEAD).Trim()
if ($head -ne $BsdSha) { throw "FreeBSD checkout is $head, expected $BsdSha" }
"MS-DOS      $((& git -C $dos rev-parse HEAD).Trim())"
"freebsd-src $head ($BsdTag)"


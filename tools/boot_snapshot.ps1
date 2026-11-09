# Boots a disk image in DOSBox-X and saves a picture of the emulator window after a delay.
# For boot-level experiments whose output goes only to the screen (boot sectors, SYSINIT errors).
#   .\tools\boot_snapshot.ps1 -Image build\images\x.img -Out build\snap.png [-Seconds 6] [-Hdd]
param(
    [Parameter(Mandatory)] [string]$Image,
    [Parameter(Mandatory)] [string]$Out,
    [int]$Seconds = 6,
    [switch]$Hdd,
    [string]$DosBox = (Join-Path $PSScriptRoot '..\build\tools\dosbox-x\bin\x64\Release\dosbox-x.exe')
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class Win {
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
'@
$Image = (Resolve-Path $Image).Path
$conf = Join-Path ([IO.Path]::GetTempPath()) ("snap-" + [guid]::NewGuid() + ".conf")
$mount = if ($Hdd) { "imgmount 2 `"$Image`" -t hdd -fs none`nboot -l c" } else { "imgmount a `"$Image`" -t floppy`nboot a:" }
"[sdl]`nautolock=false`n[dosbox]`nmemsize=16`n[cpu]`ncputype=pentium`ncycles=max`n[autoexec]`n$mount`n" | Set-Content -Encoding ascii $conf
$p = Start-Process $DosBox -ArgumentList '-nomenu', '-fastlaunch', '-conf', $conf -PassThru
try {
    Start-Sleep -Seconds $Seconds
    $p.Refresh()
    $h = $p.MainWindowHandle
    if ($h -eq [IntPtr]::Zero) { throw 'DOSBox-X window not found' }
    $r = New-Object Win+RECT
    [void][Win]::GetClientRect($h, [ref]$r)
    $bmp = New-Object System.Drawing.Bitmap ([Math]::Max(1, $r.Right)), ([Math]::Max(1, $r.Bottom))
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [void][Win]::PrintWindow($h, $hdc, 3)   # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    $g.ReleaseHdc($hdc)
    $bmp.Save((Join-Path (Get-Location) $Out), [System.Drawing.Imaging.ImageFormat]::Png)
    "saved $Out ($($r.Right)x$($r.Bottom))"
} finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id }
    Remove-Item $conf -ErrorAction SilentlyContinue
}

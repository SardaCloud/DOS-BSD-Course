# Exports each slide of a .pptx to PNG through PowerPoint (Windows, PowerPoint installed).
#   .\tools\render_slides.ps1 slides\01-boot.pptx build\slides\01-boot
param(
    [Parameter(Mandatory)] [string]$Pptx,
    [Parameter(Mandatory)] [string]$OutDir,
    [int]$Width = 1600
)
$ErrorActionPreference = 'Stop'
$Pptx = (Resolve-Path $Pptx).Path
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
Get-ChildItem $OutDir -Filter 'slide-*.png' | Remove-Item
$app = New-Object -ComObject PowerPoint.Application
try {
    # Open(FileName, ReadOnly, Untitled, WithWindow)
    $pres = $app.Presentations.Open($Pptx, -1, 0, 0)
    try {
        # Keep the deck's aspect ratio (16:9 or 4:3).
        $Height = [int][Math]::Round($Width * $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth)
        foreach ($s in $pres.Slides) {
            $s.Export((Join-Path $OutDir ('slide-{0:D2}.png' -f $s.SlideIndex)), 'PNG', $Width, $Height)
        }
        "exported $($pres.Slides.Count) slides to $OutDir"
    } finally { $pres.Close() }
} finally {
    # PowerPoint is left running: other renders may be using the same instance (COM shares it).
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}

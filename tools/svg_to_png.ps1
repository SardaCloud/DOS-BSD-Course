# Renders SVG files to PNG through PowerPoint (Windows, Office with SVG support).
#   .\tools\svg_to_png.ps1 -Svg diagrams\read-path.svg,diagrams\boot-chain.svg -OutDir build\diagrams [-Scale 2]
param(
    [Parameter(Mandatory)] [string[]]$Svg,
    [Parameter(Mandatory)] [string]$OutDir,
    [double]$Scale = 2
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
$app = New-Object -ComObject PowerPoint.Application
try {
    foreach ($s in $Svg) {
        $path = (Resolve-Path $s).Path
        $text = [IO.File]::ReadAllText($path)
        if ($text -notmatch 'viewBox="0 0 ([\d.]+) ([\d.]+)"') { throw "no viewBox in $path" }
        $w = [double]$Matches[1]; $h = [double]$Matches[2]
        $pres = $app.Presentations.Add(0)   # no window
        try {
            # 1 SVG pixel = 0.75 pt, so the slide has the SVG's size in CSS pixels
            $pres.PageSetup.SlideWidth = $w * 0.75
            $pres.PageSetup.SlideHeight = $h * 0.75
            $slide = $pres.Slides.Add(1, 12)          # ppLayoutBlank
            [void]$slide.Shapes.AddPicture($path, 0, -1, 0, 0, $w * 0.75, $h * 0.75)
            $png = Join-Path $OutDir ([IO.Path]::GetFileNameWithoutExtension($path) + '.png')
            $slide.Export($png, 'PNG', [int]($w * $Scale), [int]($h * $Scale))
            "rendered $png"
        } finally { $pres.Close() }
    }
} finally {
    # PowerPoint is left running: other renders may be using the same instance (COM shares it).
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}

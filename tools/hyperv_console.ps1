# Hyper-V console helper for the course's FreeBSD VM: type text, press keys, save a screenshot.
#   .\tools\hyperv_console.ps1 -VM FreeBSD151-Course -Screenshot build\vmshot.png
#   .\tools\hyperv_console.ps1 -VM FreeBSD151-Course -Type 'root' -Enter
# Runs the Hyper-V WMI calls in Windows PowerShell (the Hyper-V provider lives in root\virtualization\v2).
param(
    [Parameter(Mandatory)] [string]$VM,
    [string]$Type,
    [switch]$Enter,
    [string]$Screenshot,
    [int]$Width = 1024,
    [int]$Height = 768
)
$ErrorActionPreference = 'Stop'
$ns = 'root\virtualization\v2'
$cs = Get-CimInstance -Namespace $ns -ClassName Msvm_ComputerSystem -Filter "ElementName='$VM'"
if (-not $cs) { throw "VM $VM not found" }
if ($Type -or $Enter) {
    $kb = Get-CimAssociatedInstance -InputObject $cs -ResultClassName Msvm_Keyboard
    if ($Type) {
        $r = Invoke-CimMethod -InputObject $kb -MethodName TypeText -Arguments @{ asciiText = $Type }
        if ($r.ReturnValue -ne 0) { throw "TypeText returned $($r.ReturnValue)" }
    }
    if ($Enter) {
        $r = Invoke-CimMethod -InputObject $kb -MethodName TypeKey -Arguments @{ keyCode = [uint32]13 }
        if ($r.ReturnValue -ne 0) { throw "TypeKey returned $($r.ReturnValue)" }
    }
}
if ($Screenshot) {
    Add-Type -AssemblyName System.Drawing
    # The thumbnail must be requested at the guest's current video resolution.
    $vh = Get-CimAssociatedInstance -InputObject $cs -ResultClassName Msvm_VideoHead |
        Where-Object { $_.CurrentHorizontalResolution -gt 0 } | Select-Object -Last 1
    $Width = [int]$vh.CurrentHorizontalResolution; $Height = [int]$vh.CurrentVerticalResolution
    $svc = Get-CimInstance -Namespace $ns -ClassName Msvm_VirtualSystemManagementService
    $settings = Get-CimAssociatedInstance -InputObject $cs -ResultClassName Msvm_VirtualSystemSettingData |
        Where-Object { $_.VirtualSystemType -eq 'Microsoft:Hyper-V:System:Realized' } | Select-Object -First 1
    $r = Invoke-CimMethod -InputObject $svc -MethodName GetVirtualSystemThumbnailImage -Arguments @{
        TargetSystem = $settings; WidthPixels = [uint16]$Width; HeightPixels = [uint16]$Height }
    if ($r.ReturnValue -ne 0) { throw "GetVirtualSystemThumbnailImage returned $($r.ReturnValue)" }
    $data = $r.ImageData
    $bmp = New-Object System.Drawing.Bitmap $Width, $Height, ([System.Drawing.Imaging.PixelFormat]::Format16bppRgb565)
    $rect = New-Object System.Drawing.Rectangle 0, 0, $Width, $Height
    $bd = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::WriteOnly, $bmp.PixelFormat)
    [Runtime.InteropServices.Marshal]::Copy([byte[]]$data, 0, $bd.Scan0, [Math]::Min($data.Length, $bd.Stride * $Height))
    $bmp.UnlockBits($bd)
    $out = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Screenshot))
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    "saved $out"
}

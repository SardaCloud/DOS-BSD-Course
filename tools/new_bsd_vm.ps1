# Creates the course's FreeBSD 15.1 Hyper-V VM from the official disk image (tested on Windows 11 Hyper-V).
#   1. Download FreeBSD-15.1-RELEASE-amd64-ufs.vhd.xz and CHECKSUM.SHA256 from
#      https://download.freebsd.org/releases/VM-IMAGES/15.1-RELEASE/amd64/Latest/ (with your browser).
#   2. In Windows PowerShell as a member of "Hyper-V Administrators":
#      .\tools\new_bsd_vm.ps1 -ImageXz C:\Downloads\FreeBSD-15.1-RELEASE-amd64-ufs.vhd.xz -Sha256 <hash from CHECKSUM.SHA256>
# The VM is Generation 1 (BIOS boot, as Module 1 needs), 2 vCPUs, 2 GB, 20 GB disk, on the "Default Switch".
# A checkpoint is taken before the first boot. Then follow course/00-lab.md, section 0.6.
param(
    [Parameter(Mandatory)] [string]$ImageXz,
    [Parameter(Mandatory)] [string]$Sha256,
    [string]$Name = 'FreeBSD151-Course',
    [string]$Dir = (Join-Path (Split-Path -Parent $PSScriptRoot) 'build\freebsd\vm'),
    [string]$Switch = 'Default Switch',
    [long]$DiskBytes = 20GB
)
$ErrorActionPreference = 'Stop'
if (Get-VM -Name $Name -ErrorAction SilentlyContinue) { throw "A VM named $Name already exists" }
$hash = (Get-FileHash $ImageXz -Algorithm SHA256).Hash.ToLower()
if ($hash -ne $Sha256.ToLower()) { throw "SHA-256 mismatch: $hash" }
New-Item -ItemType Directory -Force $Dir | Out-Null
$vhd = Join-Path $Dir 'FreeBSD-15.1-amd64-ufs.vhd'
$vhdx = Join-Path $Dir "$Name.vhdx"
# Python's lzma module decompresses .xz without extra tools (7-Zip works too).
python -c "import lzma,shutil,sys; shutil.copyfileobj(lzma.open(sys.argv[1]), open(sys.argv[2],'wb'), 1<<24)" $ImageXz $vhd
if ($LASTEXITCODE) { throw 'decompression failed' }
Convert-VHD -Path $vhd -DestinationPath $vhdx -VHDType Dynamic
Remove-Item $vhd
Resize-VHD -Path $vhdx -SizeBytes $DiskBytes          # growfs enlarges / at the first boot
New-VM -Name $Name -Generation 1 -MemoryStartupBytes 2GB -VHDPath $vhdx -SwitchName $Switch -Path $Dir | Out-Null
Set-VMProcessor -VMName $Name -Count 2
Set-VM -Name $Name -AutomaticCheckpointsEnabled $false -CheckpointType Standard -AutomaticStopAction ShutDown
Checkpoint-VM -Name $Name -SnapshotName 'pristine-before-first-boot'
Start-VM -Name $Name
"VM $Name started. Open it with: vmconnect.exe localhost $Name"

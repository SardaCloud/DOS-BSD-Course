# Types ASCII text into a Hyper-V VM as raw PC scan codes (set 1, US layout), for guests whose keyboard
# driver ignores Msvm_Keyboard.TypeText (FreeBSD). Shift is pressed and released explicitly.
#   .\tools\hyperv_type.ps1 -VM FreeBSD151-Course -Text 'echo "hi" | wc -c' -Enter
#   .\tools\hyperv_type.ps1 -VM FreeBSD151-Course -CtrlC
param(
    [Parameter(Mandatory)] [string]$VM,
    [string]$Text = '',
    [switch]$Enter,
    [switch]$CtrlC
)
$ErrorActionPreference = 'Stop'
$ns = 'root\virtualization\v2'
$cs = Get-CimInstance -Namespace $ns -ClassName Msvm_ComputerSystem -Filter "ElementName='$VM'"
$kb = Get-CimAssociatedInstance -InputObject $cs -ResultClassName Msvm_Keyboard | Select-Object -First 1

$base = @{}
$row = '1234567890-='; for ($i = 0; $i -lt $row.Length; $i++) { $base[[string]$row[$i]] = 0x02 + $i }
$row = 'qwertyuiop[]'; for ($i = 0; $i -lt $row.Length; $i++) { $base[[string]$row[$i]] = 0x10 + $i }
$row = "asdfghjkl;'``"; for ($i = 0; $i -lt $row.Length; $i++) { $base[[string]$row[$i]] = 0x1E + $i }
$row = 'zxcvbnm,./'; for ($i = 0; $i -lt $row.Length; $i++) { $base[[string]$row[$i]] = 0x2C + $i }
$base['\'] = 0x2B; $base[' '] = 0x39
$shift = @{}
$pairs = @{ '!' = '1'; '@' = '2'; '#' = '3'; '$' = '4'; '%' = '5'; '^' = '6'; '&' = '7'; '*' = '8'; '(' = '9'; ')' = '0';
            '_' = '-'; '+' = '='; '{' = '['; '}' = ']'; ':' = ';'; '"' = "'"; '~' = '`'; '|' = '\'; '<' = ','; '>' = '.';
            '?' = '/' }
foreach ($k in $pairs.Keys) { $shift[$k] = $base[$pairs[$k]] }

$codes = New-Object System.Collections.Generic.List[byte]
function Add-Key([int]$sc, [bool]$withShift) {
    if ($withShift) { $codes.Add(0x2A) }
    $codes.Add([byte]$sc); $codes.Add([byte]($sc -bor 0x80))
    if ($withShift) { $codes.Add(0xAA) }
}
if ($CtrlC) { $codes.Add(0x1D); $codes.Add(0x2E); $codes.Add(0xAE); $codes.Add(0x9D) }
foreach ($ch in $Text.ToCharArray()) {
    $s = [string]$ch
    if ($s -cmatch '^[A-Z]$') { Add-Key $base[$s.ToLower()] $true }
    elseif ($base.ContainsKey($s)) { Add-Key $base[$s] $false }
    elseif ($shift.ContainsKey($s)) { Add-Key $shift[$s] $true }
    else { throw "cannot type character '$s' (code $([int][char]$s))" }
}
if ($Enter) { Add-Key 0x1C $false }
# Send in chunks so a long line does not overflow the guest's keyboard buffer.
$all = $codes.ToArray()
for ($i = 0; $i -lt $all.Length; $i += 64) {
    $chunk = [byte[]]($all[$i..([Math]::Min($i + 63, $all.Length - 1))])
    $r = Invoke-CimMethod -InputObject $kb -MethodName TypeScancodes -Arguments @{ scancodes = $chunk }
    if ($r.ReturnValue -ne 0) { throw "TypeScancodes returned $($r.ReturnValue)" }
    Start-Sleep -Milliseconds 60
}

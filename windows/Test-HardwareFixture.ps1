# Portable mapping test with synthetic CIM values; never a live Windows claim.
$ErrorActionPreference = 'Stop'
function Get-CimInstance {
    param($ClassName, $ErrorAction)
    switch ($ClassName) {
        'Win32_Processor' { [pscustomobject]@{ Name = 'Fixture CPU'; NumberOfLogicalProcessors = 16; MaxClockSpeed = 5500 } }
        'Win32_VideoController' { [pscustomobject]@{ Name = 'Fixture GPU' } }
        'Win32_OperatingSystem' { [pscustomobject]@{
            Caption = 'Fixture Windows'; Version = '10.0'; OSArchitecture = '64-bit'
            TotalVisibleMemorySize = 33554432; FreePhysicalMemory = 25165824
            LastBootUpTime = (Get-Date).AddHours(-2)
        } }
        'Win32_ComputerSystem' { [pscustomobject]@{ Model = 'Fixture board'; Manufacturer = 'Fixture maker' } }
        'Win32_LogicalDisk' {
            [pscustomobject]@{ DeviceID = 'C:'; DriveType = 3; Size = 100000; FreeSpace = 25000 }
            [pscustomobject]@{ DeviceID = 'Z:'; DriveType = 4; Size = 100000; FreeSpace = 25000 }
        }
        default { throw 'Unexpected CIM class' }
    }
}
. (Join-Path $PSScriptRoot 'Hardware.ps1')
$data = Get-PokemonWindowsHardware
if ($data.cpu.cores.online -ne 16 -or $data.cpu.frequency.max -ne 5500 -or
    $data.gpu[0].name -ne 'Fixture GPU' -or $data.disk.Count -ne 1 -or
    $data.disk[0].bytes.used -ne 75000 -or $data.memory.used -ne 8589934592 -or
    $data.uptime.uptime -lt 7199000 -or $data.uptime.uptime -gt 7201000 -or
    $data.probeErrors.Count -ne 0) { throw 'Windows hardware fixture mapping failed.' }
Write-Host 'Synthetic CIM mapping passed (CPU, GPU, RAM, local storage, uptime).'

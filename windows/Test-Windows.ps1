# Run in Windows PowerShell 5.1. Structural checks are not a live editor test.
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows is required for these checks.' }
. (Join-Path $PSScriptRoot 'Test-Profile.ps1')
foreach ($name in @('Install.ps1', 'Startup.ps1', 'Hardware.ps1', 'Test-Windows.ps1')) {
    $tokens = $null; $errors = $null
    [void][Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name), [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
}
. (Join-Path $PSScriptRoot 'Hardware.ps1')
$data = Get-PokemonWindowsHardware
if (-not $data.os.prettyName -or -not $data.cpu.cpu -or $data.memory.total -le 0) {
    throw ('CIM probes incomplete: ' + ($data.probeErrors -join '; '))
}
Import-Module PSReadLine -ErrorAction Stop
if (-not (Test-Path Function:\PSConsoleHostReadLine)) { throw 'Console PSReadLine hook missing.' }
Write-Host 'Parsing and local CIM checks passed. Complete the manual Windows Terminal checklist in windows/README.md.'

[CmdletBinding()]
param(
    [string]$Gif,
    [string]$Python = 'python',
    [switch]$AllowOtherPokemon,
    [switch]$Uninstall,
    # Exact lines only: inspect your profile and explicitly name a broken legacy call.
    [string[]]$LegacyStartupLine = @()
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run this installer in Windows PowerShell on Windows.' }
if ($PSVersionTable.PSVersion -lt [version]'5.1') { throw 'PowerShell 5.1 or newer is required.' }
$root = Join-Path $env:LOCALAPPDATA 'pokemon-terminal\windows'
$profilePath = $PROFILE.CurrentUserCurrentHost
$begin = '# >>> pokemon-terminal windows >>>'
$end = '# <<< pokemon-terminal windows <<<'

. (Join-Path $PSScriptRoot 'Profile.ps1')

if ($Uninstall) {
    Update-PokemonProfile -ProfilePath $profilePath -Block '' -LegacyStartupLine $LegacyStartupLine
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
    Write-Host 'Windows startup removed. Open a fresh PowerShell tab. Linux was not changed.'
    return
}

Import-Module PSReadLine -ErrorAction Stop
if (-not $Gif) {
    foreach ($candidate in @((Join-Path $PSScriptRoot '..\assets\venusaur.gif'), (Join-Path $root 'Venusaur.gif'))) {
        if (Test-Path -LiteralPath $candidate) { $Gif = $candidate; break }
    }
}
if (-not $Gif -or -not (Test-Path -LiteralPath $Gif -PathType Leaf)) {
    throw 'Supply the original 15-frame asset: .\windows\Install.ps1 -Gif C:\path\Venusaur.gif'
}
$Gif = (Resolve-Path -LiteralPath $Gif).Path
& $Python -c 'import sys; raise SystemExit(sys.version_info < (3,10))'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ with venv/pip is required.' }
New-Item -ItemType Directory -Path $root -Force | Out-Null
& $Python -m venv (Join-Path $root 'venv')
if ($LASTEXITCODE -ne 0) { throw 'Could not create the private Windows environment.' }
$managedPython = Join-Path $root 'venv\Scripts\python.exe'
& $managedPython -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; profile was not changed.' }
# validate before touching the installed GIF or profile; shared imports need a staged copy.
$stage = Join-Path ([IO.Path]::GetTempPath()) ('pokemon-windows-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path (Join-Path $stage 'shared') -Force | Out-Null
    foreach ($name in @('render.py', 'dashboard.py', 'hardware.py')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot "..\animated\$name") -Destination (Join-Path $stage "shared\$name")
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'prepare.py') -Destination $stage
    $validation = @((Join-Path $stage 'prepare.py'), $Gif, 'unused', 'unused', '120', '45', '--validate')
    if ($AllowOtherPokemon) { $validation += '--allow-other-pokemon' }
    & $managedPython @validation
    if ($LASTEXITCODE -ne 0) { throw 'GIF validation failed; profile was not changed.' }
    foreach ($name in @('Startup.ps1', 'Hardware.ps1', 'prepare.py')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $root $name) -Force
    }
    Copy-Item -LiteralPath (Join-Path $stage 'shared') -Destination $root -Recurse -Force
    if ($Gif -ine (Join-Path $root 'Venusaur.gif')) {
        Copy-Item -LiteralPath $Gif -Destination (Join-Path $root 'Venusaur.gif') -Force
    }
} finally { if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force } }
$entry = (Join-Path $root 'Startup.ps1').Replace("'", "''")
Update-PokemonProfile -ProfilePath $profilePath -LegacyStartupLine $LegacyStartupLine -Block ($begin + "`r`n. '" + $entry + "'`r`n" + $end + "`r`n")
Write-Host 'Installed. Open a fresh Windows PowerShell tab in Windows Terminal (100x38 or larger).'
Write-Host 'Animation freezes on first key for PSReadLine input safety. No startup network requests.'

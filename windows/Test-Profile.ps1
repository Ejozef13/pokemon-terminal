# Portable PowerShell tests; no CIM or Windows console claims.
$ErrorActionPreference = 'Stop'
foreach ($file in Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1') {
    $tokens = $null; $errors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
}
. (Join-Path $PSScriptRoot 'Profile.ps1')
$temp = Join-Path ([IO.Path]::GetTempPath()) ('pokemon-profile-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $profileFile = Join-Path $temp 'profile.ps1'
    $original = "# User customization`r`nfunction prompt { 'custom> ' }`r`n. C:\OldPokemon\broken.ps1`r`n# Venusaur mention must survive`r`n"
    [IO.File]::WriteAllText($profileFile, $original)
    $before = [IO.File]::ReadAllBytes($profileFile)
    $block = "# >>> pokemon-terminal windows >>>`r`n. 'C:\User files\Startup.ps1'`r`n# <<< pokemon-terminal windows <<<`r`n"
    Update-PokemonProfile -ProfilePath $profileFile -Block $block -LegacyStartupLine '. C:\OldPokemon\broken.ps1'
    $installed = [IO.File]::ReadAllText($profileFile)
    if (-not $installed.Contains("function prompt { 'custom> ' }") -or
        -not $installed.Contains('# Venusaur mention must survive') -or
        $installed.Contains('broken.ps1')) { throw 'Unrelated profile changed or exact legacy call retained.' }
    $backups = @(Get-ChildItem -LiteralPath $temp -Filter '*.pokemon-backup-*')
    if ($backups.Count -ne 1 -or
        [Convert]::ToBase64String([IO.File]::ReadAllBytes($backups[0].FullName)) -ne
        [Convert]::ToBase64String($before)) { throw 'Original bytes not backed up.' }
    Update-PokemonProfile -ProfilePath $profileFile -Block $block
    if ([IO.File]::ReadAllText($profileFile) -cne $installed) { throw 'Reinstall is not idempotent.' }
    if (@(Get-ChildItem -LiteralPath $temp -Filter '*.pokemon-backup-*').Count -ne 1) { throw 'Unchanged reinstall backed up unnecessarily.' }
    Update-PokemonProfile -ProfilePath $profileFile -Block ''
    $removed = [IO.File]::ReadAllText($profileFile)
    if ($removed.Contains('Startup.ps1') -or -not $removed.Contains('custom> ')) { throw 'Uninstall damaged profile.' }
    Update-PokemonProfile -ProfilePath $profileFile -Block ''
    $legacy = $script:PokemonRetiredProfile.Replace("`n", "`r`n")
    $custom = "function prompt { 'custom> ' }`r`n"
    [IO.File]::WriteAllText($profileFile, $custom + $legacy + "`r`n" + $block)
    Update-PokemonProfile -ProfilePath $profileFile -Block $block
    $migrated = [IO.File]::ReadAllText($profileFile)
    if ($migrated.Contains('Invoke-WebRequest') -or $migrated.Contains('Could not load Venusaur') -or
        -not $migrated.Contains($custom) -or -not $migrated.Contains($block)) { throw 'Recognized legacy migration failed.' }
    Update-PokemonProfile -ProfilePath $profileFile -Block $block
    if ([IO.File]::ReadAllText($profileFile) -cne $migrated) { throw 'Legacy migration not idempotent.' }
    $modified = $legacy.Replace('"System Info"', '"My custom stats"')
    if ((Remove-PokemonRetiredProfile $modified) -cne $modified) { throw 'Modified legacy code was removed.' }
    $unrelated = 'Invoke-WebRequest https://example.com; $venusaur = "my artwork"'
    if ((Remove-PokemonRetiredProfile $unrelated) -cne $unrelated) { throw 'Unrelated request removed.' }
    $laptopVariant = $legacy.Replace('Count / 2', 'Count / 3').Replace('"OS : $os"', '"OS  : $os"')
    if ((Remove-PokemonRetiredProfile $laptopVariant).Contains('Invoke-WebRequest')) {
        throw 'Screenshot legacy variant with one-third offset was not removed.'
    }
    [IO.File]::WriteAllText($profileFile, "# >>> pokemon-terminal windows >>>`n")
    $rejected = $false
    try { Update-PokemonProfile -ProfilePath $profileFile -Block $block } catch { $rejected = $true }
    if (-not $rejected) { throw 'Incomplete markers not rejected.' }
    Write-Host 'All PowerShell files parsed; profile backup, exact legacy removal, reinstall and uninstall tests passed.'
} finally { Remove-Item -LiteralPath $temp -Recurse -Force }

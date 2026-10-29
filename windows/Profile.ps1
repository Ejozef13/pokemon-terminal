# Exact managed-block migration, also tested independently of Windows.
function Update-PokemonProfile {
    param([string]$ProfilePath, [string]$Block, [string[]]$LegacyStartupLine = @())
    $begin = '# >>> pokemon-terminal windows >>>'
    $end = '# <<< pokemon-terminal windows <<<'
    $utf8 = New-Object Text.UTF8Encoding($true)
    $text = if (Test-Path -LiteralPath $profilePath) { [IO.File]::ReadAllText($profilePath) } else { '' }
    # Only our exact, complete marker block is automatically removed.
    if (($text.Contains($begin)) -ne ($text.Contains($end))) { throw 'Incomplete Pokemon profile markers; repair them manually first.' }
    $pattern = '(?ms)^' + [regex]::Escape($begin) + '\r?\n.*?^' + [regex]::Escape($end) + '(?:\r?\n|$)'
    $updated = [regex]::Replace($text, $pattern, '')
    foreach ($line in $LegacyStartupLine) {
        if ($line.Contains("`n") -or $line.Contains("`r")) { throw 'LegacyStartupLine must be a single complete line.' }
        $updated = [regex]::Replace($updated, '(?m)^' + [regex]::Escape($line) + '(?:\r?\n|$)', '')
    }
    if ($Block) {
        if ($updated -and -not $updated.EndsWith("`n")) { $updated += "`r`n" }
        $updated += $Block
    }
    if ($updated -ceq $text) { return }
    New-Item -ItemType Directory -Path (Split-Path $profilePath) -Force | Out-Null
    if (Test-Path -LiteralPath $profilePath) {
        $backup = $profilePath + '.pokemon-backup-' + [guid]::NewGuid().ToString('N')
        Copy-Item -LiteralPath $profilePath -Destination $backup
        Write-Host "Profile backup: $backup"
    }
    $temp = $profilePath + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [IO.File]::WriteAllText($temp, $updated, $utf8)
        Move-Item -LiteralPath $temp -Destination $profilePath -Force
    } finally { if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force } }
}


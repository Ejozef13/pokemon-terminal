# Retired Windows launcher, matched as a complete token sequence, never executed.
# Whitespace/comments may differ; modified or unrelated code is left alone.
$script:PokemonRetiredProfile = @'
try {
    $url = "https://raw.githubusercontent.com/Ejozef13/pokemon-terminal/main/terminal-art/venusaur.txt"
    $venusaur = (Invoke-WebRequest -Uri $url -UseBasicParsing).Content -split "`n"
}
catch {
    $venusaur = @("Could not load Venusaur.")
}
$cpu = (Get-CimInstance Win32_Processor).Name
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
$gpu = (Get-CimInstance Win32_VideoController | Select-Object -First 1).Name
$os = (Get-CimInstance Win32_OperatingSystem).Caption
$info = @(
    "System Info",
    "OS : $os",
    "CPU : $cpu",
    "GPU : $gpu",
    "RAM : $ram GB"
)
$offset = [math]::Floor($venusaur.Count / 2)
for ($i = 0; $i -lt $venusaur.Count; $i++) {
    $left = $venusaur[$i]
    if ($i -ge $offset -and ($i - $offset) -lt $info.Count) {
        $right = $info[$i - $offset]
    } else {
        $right = ""
    }
    "{0,-60} {1}" -f $left, $right
}

'@
function Get-PokemonTokenSignature([string]$Text) {
    $tokens = $null; $errors = $null
    [void][Management.Automation.Language.Parser]::ParseInput($Text, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { return $null }
    return (($tokens | Where-Object { $_.Kind -notin @('NewLine', 'Comment', 'EndOfInput') } |
        ForEach-Object {
            $value = $_.Text
            # The retired label strings appeared with different colon padding.
            # Normalize only these four exact labels/variables, not arbitrary strings.
            if ($value -cmatch '^"(OS|CPU|GPU|RAM)\s*:\s*(\$(?:os|cpu|gpu|ram)(?: GB)?)"$') {
                $value = '"' + $Matches[1] + ' : ' + $Matches[2] + '"'
            }
            $_.Kind.ToString() + ':' + $value
        }) -join "`n")
}
function Remove-PokemonRetiredProfile([string]$Text) {
    $tokens = $null; $errors = $null
    $ast = [Management.Automation.Language.Parser]::ParseInput($Text, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw 'Profile syntax errors; repair the profile before migration.' }
    $statements = @($ast.EndBlock.Statements)
    $referenceTokens = $null; $referenceErrors = $null
    $reference = [Management.Automation.Language.Parser]::ParseInput($script:PokemonRetiredProfile, [ref]$referenceTokens, [ref]$referenceErrors)
    $count = $reference.EndBlock.Statements.Count
    $signatures = @(
        (Get-PokemonTokenSignature $script:PokemonRetiredProfile),
        (Get-PokemonTokenSignature ($script:PokemonRetiredProfile.Replace('Count / 2', 'Count / 3')))
    )
    $original = $Text
    $lastRemoved = $Text.Length
    for ($i = $statements.Count - $count; $i -ge 0; $i--) {
        $start = $statements[$i].Extent.StartOffset
        $length = $statements[$i + $count - 1].Extent.EndOffset - $start
        if ($start + $length -le $lastRemoved -and
            $signatures -ccontains (Get-PokemonTokenSignature $original.Substring($start, $length))) {
            $Text = $Text.Remove($start, $length)
            $lastRemoved = $start
        }
    }
    return $Text
}

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
    $updated = Remove-PokemonRetiredProfile $updated
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


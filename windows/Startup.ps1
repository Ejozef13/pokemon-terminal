# All terminal writes run synchronously on the console-host thread.
# No jobs, timers, event actions, processes, or threads write during PSReadLine.
if ($env:OS -ne 'Windows_NT' -or -not $env:WT_SESSION -or
    [Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or
    $global:PokemonWindowsLoaded) { return }
try {
    Import-Module PSReadLine -ErrorAction Stop
    if (-not (Test-Path Function:\PSConsoleHostReadLine)) { return }
    # Supply the usual clear binding only when no user binding owns this chord.
    $clearBinding = @(Get-PSReadLineKeyHandler -Bound | Where-Object { $_.Key -eq 'Ctrl+l' })
    if ($clearBinding.Count -eq 0) {
        Set-PSReadLineKeyHandler -Chord Ctrl+l -Function ClearScreen
    }
    if (-not ('PokemonTerminal.Native' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace PokemonTerminal {
 public static class Native {
  [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int id);
  [DllImport("kernel32.dll")] static extern bool GetConsoleMode(IntPtr h, out uint mode);
  [DllImport("kernel32.dll")] static extern bool SetConsoleMode(IntPtr h, uint mode);
  public static bool EnableVT() {
   uint mode; var h = GetStdHandle(-11);
   return GetConsoleMode(h, out mode) && SetConsoleMode(h, mode | 4);
  }
 }
}
'@
    }
    if (-not [PokemonTerminal.Native]::EnableVT()) { return }
    # PS 5.1 commonly starts with an OEM code page that replaces Unicode glyphs
    # with '?'. Set the console writer to UTF-8 before emitting shared art/text.
    [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
    $global:PokemonWindowsLoaded = $true
    $global:PokemonWindowsRoot = $PSScriptRoot
    $global:PokemonWindowsReadLine = (Get-Item Function:\PSConsoleHostReadLine).ScriptBlock
    $global:PokemonWindowsPrompt = (Get-Item Function:\prompt).ScriptBlock
    $global:PokemonWindowsFirst = $true
    $global:PokemonWindowsFrames = $null

    function global:prompt {
        if ($global:PokemonWindowsFirst) {
            $global:PokemonWindowsFirst = $false
            $snapshot = $null; $output = $null
            try {
                . (Join-Path $global:PokemonWindowsRoot 'Hardware.ps1')
                $snapshot = [IO.Path]::GetTempFileName()
                $output = [IO.Path]::GetTempFileName()
                Get-PokemonWindowsHardware | ConvertTo-Json -Depth 12 |
                    Set-Content -LiteralPath $snapshot -Encoding UTF8
                $python = Join-Path $global:PokemonWindowsRoot 'venv\Scripts\python.exe'
                & $python (Join-Path $global:PokemonWindowsRoot 'prepare.py') `
                    (Join-Path $global:PokemonWindowsRoot 'Venusaur.gif') $snapshot $output `
                    ([Console]::WindowWidth) ([Console]::WindowHeight) --allow-other-pokemon 2>$null
                if ($LASTEXITCODE -ne 0) { throw 'Frame preparation failed; see Windows troubleshooting.' }
                $global:PokemonWindowsFrames = Get-Content -LiteralPath $output -Raw -Encoding UTF8 | ConvertFrom-Json
                [Console]::Write("$([char]27)[H$([char]27)[2J")
                foreach ($line in $global:PokemonWindowsFrames.initial) { [Console]::Write($line + "`r`n") }
                [Console]::Write("`r`n")
            } catch {
                $global:PokemonWindowsFrames = $null
                Write-Warning ('Pokemon Terminal: ' + $_.Exception.Message)
            } finally {
                if ($snapshot) { Remove-Item -LiteralPath $snapshot -Force -ErrorAction SilentlyContinue }
                if ($output) { Remove-Item -LiteralPath $output -Force -ErrorAction SilentlyContinue }
            }
        }
        & $global:PokemonWindowsPrompt
    }

    function global:PSConsoleHostReadLine {
        $frames = $global:PokemonWindowsFrames
        $global:PokemonWindowsFrames = $null # One attempt per shell, including cancelled/empty input.
        if ($frames) {
            try {
                $width = [Console]::WindowWidth; $height = [Console]::WindowHeight
                $left = [Console]::CursorLeft; $top = [Console]::CursorTop
                $clock = [Diagnostics.Stopwatch]::StartNew(); $next = 125; $index = 0
                while (-not [Console]::KeyAvailable) {
                    if ([Console]::WindowWidth -ne $width -or [Console]::WindowHeight -ne $height -or
                        [Console]::WindowTop -ne 0 -or [Console]::CursorLeft -ne $left -or
                        [Console]::CursorTop -ne $top) { break }
                    if ($clock.ElapsedMilliseconds -ge $next) {
                        # Check input again immediately before writing. Never consume a key.
                        if ([Console]::KeyAvailable) { break }
                        $index = ($index + 1) % $frames.frames.Count
                        [Console]::Write("$([char]27)7" + $frames.frames[$index] + "$([char]27)8")
                        $next = $clock.ElapsedMilliseconds + 125
                    }
                    Start-Sleep -Milliseconds 15
                }
            } catch { } # Always hand control back to the existing editor.
        }
        & $global:PokemonWindowsReadLine
    }
} catch { Write-Warning ('Pokemon Terminal disabled: ' + $_.Exception.Message) }

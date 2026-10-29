# Windows PowerShell port (experimental)

Separate Windows integration for **Windows PowerShell 5.1 in Windows Terminal**.
Linux Fish sources, installation and dependencies are unchanged. Windows uses a
private Python environment and copies the existing Python renderer/dashboard
into its own runtime. No WSL, tmux, Fastfetch, background terminal writer, online
API, or network request is used at startup.

## Important input limitation

The first untouched prompt animates indefinitely at approximately 8 FPS. On the
**first key**, animation freezes and the existing PSReadLine editor takes over
without consuming that key. It stays frozen before any command executes.
Completion, history, selection and editing remain PSReadLine's responsibility.
Empty Enter, cancellation and resize also leave the animation frozen.

This is a deliberate partial implementation of the requested animation lifecycle:
it does **not** animate while editing a command. PowerShell 5.1's bundled
PSReadLine does not expose a documented safe idle drawing callback. An independent
timer writing during PSReadLine would risk corrupting input. There is no custom
replacement editor or unsupported reflection into PSReadLine internals here.
The synchronous read loop checks queued input, size, scroll and cursor position
before drawing; after handoff it never draws again.

## Install

Install Python 3.10+ (with pip/venv) and Windows Terminal, then open a **Windows
PowerShell** tab. Clone this repo and run from its root:

```powershell
.\windows\Install.ps1 -Gif "$HOME\Downloads\Venusaur.gif"
```

The original GIF is not currently bundled: the chat previews did not expose its
bytes. Supply your original **15-frame GIF**; the installer decodes every frame
and rejects a different frame count by default. Frame count cannot establish
artwork identity, so do not substitute a different image expecting the same art.
For your own Pokemon GIF (2-300 frames):

```powershell
.\windows\Install.ps1 -Gif 'C:\Sprites\my-pokemon.gif' -AllowOtherPokemon
```

Open a fresh tab, at least **100 columns by 38 rows** (about 135 columns gives
the full-width layout). Venusaur is on the left, green/blue system/calendar on
the right. Small windows skip the header instead of overwriting the prompt.
Existing profile prompt customizations are called after the header. Profiles
loaded later may replace these wrappers; put the managed block last if needed.

Setup installs Pillow once under
`%LOCALAPPDATA%\pokemon-terminal\windows\venv` and copies the GIF/runtime there.
The clone and Downloads copy can then be moved. Re-running the installer without
`-Gif` reuses the installed GIF (use `-AllowOtherPokemon` again for other sprites).
Setup needs package access; startup does not. Never run the installer elevated.
If script execution is blocked, follow your organization's execution policy;
this project does not bypass it or change it automatically.

The installer modifies only `$PROFILE.CurrentUserCurrentHost` and backs up its
original bytes before changes. It replaces its own exact managed marker block,
preserving unrelated text. It does not guess which unmarked script is broken.
Inspect `$PROFILE` and explicitly identify any old broken startup call:

```powershell
Get-Content -LiteralPath $PROFILE
.\windows\Install.ps1 -LegacyStartupLine '. C:\OldPokemon\broken-startup.ps1'
```

Only that complete matching line is removed; do not supply unrelated lines.
Multiline legacy scripts require manual review. Backups are left alongside the
profile. Unknown old startup code is never silently deleted.

## Data and clearing

Read-only local CIM queries provide CPU names/logical processors/max clock,
GPU names, physical memory use, fixed-drive usage, Windows version, computer
model and uptime. These are a startup snapshot. No network section or Display
row is rendered. Windows does not expose reliable per-GPU/CPU temperature through
these standard CIM classes; this port omits temperatures rather than inventing
them or installing a privileged sensor service. Package counts are explicitly
not collected; Desktop/WM identify the Windows desktop, not process versions.

`clear` and `cls` retain their normal PowerShell behavior. Startup binds Ctrl+L
to ClearScreen only if that chord is unbound. Existing bindings take precedence.
If your custom binding does something else, you can opt into clearing yourself:

```powershell
Set-PSReadLineKeyHandler -Chord Ctrl+l -Function ClearScreen
```

No existing key bindings, aliases or execution policy are overwritten.
Clearing removes the header; it does not restart it until a new tab.

## Testing and troubleshooting

**No live Windows test has been performed in the Linux development environment.**
Do not treat Linux fixtures or parsing checks as proof of Windows compatibility.
Development checks passed with 34 Python tests (including the Linux Fish PTY
regressions and synthetic 15-frame Windows preparation), plus PowerShell 7.4.6
on Linux for script parsing and profile migration tests. This does not test the
Windows PowerShell 5.1 parser, CIM provider or native console API.
Portable PowerShell checks can be repeated with
`pwsh -NoProfile -File windows/Test-Profile.ps1` and
`pwsh -NoProfile -File windows/Test-HardwareFixture.ps1`; the latter mocks CIM
and must run in its own process so it cannot shadow a real hardware probe.
Run the following on Windows before relying on this port:

```powershell
.\windows\Test-Windows.ps1
```

Then manually check in a fresh Windows PowerShell 5.1 tab:

1. Leave the prompt untouched for a minute: all 15 frames loop without flicker.
2. Type immediately and after waiting; the first character must appear once.
3. Edit a long wrapped command, paste multiline text, use arrows, history, Tab
   completion, Unicode, selection and Ctrl+C. Nothing should redraw the sprite.
4. Execute a command: output and every later prompt must remain untouched.
5. Test `clear`, `cls`, Ctrl+L, scrolling and window resizing separately.
6. Compare CIM data with Task Manager (clock and memory sampling can differ).
7. Install twice; inspect one managed block and unchanged custom profile code.
8. Restart with networking disconnected: installed startup must still work.
9. Test a customized prompt and PSReadLine EditMode; confirm handoff behaves
   normally. Hosts other than Windows Terminal skip startup intentionally.

For a startup warning, run the managed Python preparation command manually or
dot-source `Hardware.ps1` and call `Get-PokemonWindowsHardware | ConvertTo-Json
-Depth 12`. Probe errors are included in the snapshot. CIM access may be disabled
by device policy; elevation is not a supported workaround. If PSReadLine fails,
use a `powershell.exe -NoProfile` tab to repair/disable the hook. Font glyph
appearance and terminal wallpaper/transparency are controlled by Windows Terminal.

## Uninstall

```powershell
.\windows\Install.ps1 -Uninstall
```

This backs up and removes only the managed profile block and the Windows runtime
directory, leaving Linux, unrelated profile content and backups intact. Open a
fresh tab afterward. Restore a profile backup manually only after reviewing its
contents: it may contain the obsolete startup code you removed.

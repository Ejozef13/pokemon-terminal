# Pokémon Terminal

Animated Pokémon beside a compact CachyOS green/blue system dashboard and
calendar, in a single terminal with a usable command prompt.

## Choose your platform

| | Linux | Windows |
| --- | --- | --- |
| Setup guide | [For Linux](docs/LINUX.md) | [For Windows](windows/README.md) |
| Shell | Fish (tested with 4.x) | Windows PowerShell 5.1 in Windows Terminal |
| Installer | `bash install.sh` | `.\windows\Install.ps1` |
| Animation freezes | First executed command, clear, cancel or resize | First key or resize, before PSReadLine editing |
| Hardware | Fastfetch and local Linux probes; readable CPU/GPU temperatures | Local CIM queries; no temperature service |

**Bring your animated GIF.** The original Venusaur asset is not bundled. Copy
it to each new machine before installing; there are no startup downloads.
Windows expects the original 15-frame `Venusaur.gif` unless you explicitly choose
another Pokémon. Both installers copy the asset into your user configuration.

## For Linux

Requires Fish, Git, Python 3.10+ with venv/pip, and a UTF-8 true-color terminal.
On CachyOS / Arch, install prerequisites first:

```bash
sudo pacman -S --needed git fish python python-pip fastfetch lm_sensors pciutils
```

Then clone and install:

```bash
git clone https://github.com/Ejozef13/pokemon-terminal.git
cd pokemon-terminal
bash install.sh ~/Downloads/pokemon-venusaur.gif
```

Open a **new Fish terminal**. Use a wide window about 40 text rows tall.
See [For Linux](docs/LINUX.md) for other settings, diagnostics and disabling.

Update an existing Linux installation:

```bash
git pull --ff-only
bash install.sh
```

Disable Linux startup:

```bash
bash install.sh --disable
```

## For Windows

Install Git, Python 3.10+ with pip/venv, and Windows Terminal. Open a
**Windows PowerShell 5.1** tab and run:

```powershell
git clone https://github.com/Ejozef13/pokemon-terminal.git
cd pokemon-terminal
.\windows\Install.ps1 -Gif "$HOME\Downloads\Venusaur.gif"
```

Open a **new Windows PowerShell tab**, at least 100 columns by 38 rows.
The installer backs up your PowerShell profile and adds its managed startup
block. Follow your machine's execution policy if scripts are blocked.
See [For Windows](windows/README.md) for profile migration, testing and troubleshooting.

Update an existing Windows installation:

```powershell
git pull --ff-only
.\windows\Install.ps1
```

Uninstall Windows startup and its private runtime:

```powershell
.\windows\Install.ps1 -Uninstall
```

Windows startup and layout have been reported working by the owner on Windows
PowerShell 5.1. The full live input/resize checklist remains to be verified;
this port freezes on the first key to let PSReadLine edit safely.

## Insert your Pokémon GIF here

Keep the Venusaur layout and substitute your own transparent, looping animated
Pokémon GIF. The dashboard and calendar stay the same:

**Linux:**

```bash
bash install.sh ~/Downloads/my-pokemon.gif
```

**Windows:**

```powershell
.\windows\Install.ps1 -Gif "$HOME\Downloads\my-pokemon.gif" -AllowOtherPokemon
```

To ship a default sprite in your own fork, commit it as `assets/venusaur.gif`.
Both installers look there when no GIF argument is supplied. Windows defaults
to validating 15 frames; use `-AllowOtherPokemon` for a different animation.

## What is shared

The sprite renderer, compact dashboard, blue date/weekdays, white calendar
numbers, black-on-green current date, and terminal palette dots use the same
Python presentation code. Hardware values reflect the machine running it.
Network information and Display rows are omitted. Font, wallpaper, transparency
and palette come from your terminal settings.

Linux lives in `animated/` with `install.sh`; Windows startup, installer and
requirements live in `windows/`. Each installs a separate private Python
environment outside the checkout. Moving the clone after installation is safe.
No obsolete static-art launcher is installed.

See [development notes](docs/DEVELOPMENT.md) and the
[Windows testing guide](windows/README.md#testing-and-troubleshooting).

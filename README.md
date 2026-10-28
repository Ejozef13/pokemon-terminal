# Pokemon Terminal

Animated Venusaur beside centered fastfetch, with a **working Fish prompt
immediately below it**. Type while Venusaur moves. There is **no idle timeout**: it keeps moving while you stay at the initial
prompt. Running your first command freezes the sprite before command output begins. Use `clear` or Ctrl-L for a clean workspace.

One regular terminal, no split view, and no 30-second typing delay.

## Update your desktop

```fish
cd /home/ejmr/pokemon-terminal/pokemon-terminal
git pull --ff-only origin main
.venv/bin/python -m pip install -r requirements-image.txt
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif --duration 0
```

Open a **new Konsole window**. The installer replaces the previous blocking Fish
startup hook. It copies your GIF into the configuration directory, so moving the
download later is fine. Keep the checkout's virtualenv; startup uses its Python.

The live prompt integration requires **Fish on Linux**. Python 3, Pillow, and a
UTF-8 terminal with ANSI true-color support are also needed. Install fastfetch
separately for complete system information. Frame conversion and
system information capture happen once before the first prompt. Fastfetch 2.40+
is recommended for the structured dashboard. Without it, available local Python
statistics are shown and unsupported fields say Unavailable.

Bash still has the foreground fallback, which waits before returning a
prompt (3 seconds when Fish has no idle timeout). The nonblocking integration described here is for Fish.

## Timing and layout

```fish
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif --duration 0 --width 48 --gap 8 --fps 8
```

- `--duration`: 0 for indefinite idle animation (default), or a timeout up to 300 seconds.
- `--width`: preferred sprite width, 8–120 (default 48).
- `--gap`: columns between sprite and fastfetch, 1–40 (default 8).
- `--fps`: maximum redraw rate, 1–30 (default 8).

The reference-inspired dashboard has three boxed sections, arrows, usage meters,
a current-month calendar, a highlighted current day, and palette dots:

- **Hardware** in CachyOS teal: CPU, GPUs, temperatures when supported, RAM,
  mounted disks, and display resolution/scaling/refresh rate.
- **System & Software** in blue: host, distribution, kernel, uptime, packages,
  desktop, window manager, Fish version, and terminal version.
- **Date & Calendar** in purple/cyan: local date/time, ISO week, weekdays, and month.

Network modules are never requested or rendered. Fastfetch runs with an explicit
local module list and without loading your global configuration. Your global
Fastfetch config is left unchanged. Statistics are captured once at startup; the
calendar/time reflect when the terminal opened, rather than updating live.

The combined sprite and dashboard are centered horizontally and vertically.
The image is reduced when necessary to leave room for typing. A wide window with
roughly 40 or more text rows is recommended for the full dashboard. On short
windows, the header is clipped with a message to enlarge the terminal.

The animation stops on the first command, Ctrl-L, Ctrl-C, a new prompt, window resize, or long/multiline
input that might scroll the header. It stays frozen for the rest of that shell
session. Ordinary input and cursor editing work while it animates; no command
runs concurrently with the renderer. Small windows skip the display. A custom
user Ctrl-L binding takes precedence over the default binding; typing `clear`
always stops drawing first.

A new terminal gets a fresh animation. Nested shells inherit a marker and skip
startup. SSH and noninteractive sessions also skip it.

## Removing the duplicate old Venusaur

The installer backs up and disables recognized old art calls in:

- `~/.config/fish/config.fish`
- Fish `conf.d/*.fish` startup files
- `functions/fish_greeting.fish` and Pokemon/Venusaur function files
- The original Bash startup hook

It recognizes fastfetch/neofetch calls and image/text-art commands referring to
Venusaur or the original Pokemon setup. Unrelated lines remain intact.
Linked files and complex multi-line custom commands are left for manual review.

The new display is drawn at the **first prompt**, after startup configuration
and greeting output. It clears that initial screen once, so leftover greeting art
does not create a second Venusaur. Expiry simply stops updates; it does not print
another image or re-run your greeting. Original art files remain stored for
rollback, but are not part of the new Fish display.

## Disable or restore

```fish
.venv/bin/python animated/install.py --disable
```

Then open a new terminal. Recognized original startup lines are restored. Backups
remain under `${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/animated/backups`.
The original static installer and art remain available in the repository.

## Fresh installation and development

```bash
git clone https://github.com/Ejozef13/pokemon-terminal.git
cd pokemon-terminal
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-image.txt
.venv/bin/python animated/install.py /path/to/your/venusaur.gif
```

The GIF is user supplied and is not bundled here.

For tests, install the development dependencies (Pillow and pyte):

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

Fish integration tests use real pseudo-terminals and a terminal emulator to check
typing, visible cursor preservation, command execution, expiry, clearing, resize,
and duplicate-art migration. They require Fish on Linux.

See [animated/README.md](animated/README.md) for implementation notes and optional
foreground ASCII playback.

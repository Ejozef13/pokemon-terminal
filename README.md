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
- **Date & Calendar** in CachyOS green: local date/time, ISO week, weekdays, and month.

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

## Animated-only installation

The static artwork, renderer, conversion helper, and old static installer have
been deleted from the current repository. There is no bundled static fallback:
the player uses only your installed multi-frame GIF.

The installer deletes the known retired files under the application configuration
directory and disables old art calls in Fish/Bash configuration. Changed shell
files are backed up; unrelated settings and unrelated artwork are preserved.
Old calls stay disabled even if you later disable animation.

If you have the nested clones created earlier, update **both** checkouts so old
tracked files are removed from each:

```fish
cd /home/ejmr/pokemon-terminal
git pull --ff-only origin main
cd /home/ejmr/pokemon-terminal/pokemon-terminal
git pull --ff-only origin main
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif
```

The first prompt clears the initial screen and stale scrollback before showing
one animated Venusaur. Original art is not reprinted when animation stops.
Symlinked configuration and complex custom multi-line startup commands are left
for manual inspection rather than overwriting unknown files.

To disable animated startup without bringing back the retired artwork:

```fish
.venv/bin/python animated/install.py --disable
```

## Accurate hardware and temperatures

On CachyOS, ensure the local detection tools are installed:

```fish
sudo pacman -S --needed fastfetch lm_sensors pciutils
```

Terminal startup itself **never uses sudo**, loads drivers, or changes sensor
permissions. Fastfetch's basic CPU/GPU/desktop/package query is separate from its
optional temperature query, so a failed thermal option no longer discards the
other hardware data. The app also reads CPU information, motherboard identity,
AMD/Intel/NVMe kernel temperature files, local PCI GPU names, pacman package
counts, desktop/session information, and KDE display data where available.

CPU package temperature is displayed with CPU information. Other readable sensor
values are labelled by chip/card and sensor name (for example GPU junction or
NVMe composite). Missing or disconnected sensors are not invented. Values are a
startup snapshot, not a continuously refreshed hardware monitor.

If anything still says Unavailable, run the diagnostic command on **your PC**:

```fish
.venv/bin/python animated/dashboard.py --diagnose
```

It reports Fastfetch errors, detected modules, readable temperature files, driver
presence, and local hardware readings. This distinguishes unsupported hardware,
missing tools, and permission errors. Kernel/driver support determines which
temperatures are exposed; installing a Python dependency cannot grant access to
an unexposed sensor. Sensor detection is validated with fixtures in cloud tests;
actual desktop sensor access must be verified on the desktop.

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

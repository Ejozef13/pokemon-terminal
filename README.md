# Pokemon Terminal

Animated Venusaur beside centered fastfetch in your regular terminal. It plays
for **30 seconds**, leaves the last frame visible, and returns to your normal
Fish or Bash prompt directly below. Press **Ctrl-C** to skip early. Use
`clear` whenever you want a clean workspace. No background renderer or split view.

## Update and enable on your desktop

From your existing checkout:

```fish
cd /home/ejmr/pokemon-terminal/pokemon-terminal
git pull --ff-only origin main
.venv/bin/python -m pip install -r requirements-image.txt
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif --duration 30
```

Open a **new Konsole window** to test. The installer replaces the previous
animation launcher and hooks; it does not attach to or create any sessions.
An already open split-view session is unchanged: close that window normally
and test in a fresh terminal.

The GIF is copied into your XDG configuration directory, so moving the original
out of Downloads will not break startup. Keep the checkout's virtualenv; startup
uses its Python. The desktop GIF is user supplied and is not bundled here.

For a fresh installation, clone the repository and create the virtualenv first:

```bash
git clone https://github.com/Ejozef13/pokemon-terminal.git
cd pokemon-terminal
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-image.txt
.venv/bin/python animated/install.py /path/to/your/venusaur.gif
```

Requires Python 3, Pillow, an animated GIF, and a UTF-8 terminal with ANSI color
support. Install fastfetch separately to show system information; neofetch is
the fallback. Information is captured once at startup.

## Layout and timing

```fish
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif --duration 30 --width 48 --gap 8 --fps 8
```

- `--duration`: startup animation seconds, greater than 0 and at most 300 (default 30).
- `--width`: sprite columns, 8–120 (default 48).
- `--gap`: columns between sprite and fastfetch, 1–40 (default 8).
- `--fps`: maximum redraw rate, 1–30 (default 8).

Fastfetch is vertically centered beside Venusaur; the combined display is
horizontally centered. Narrow windows stack information below the sprite;
reduce width for small windows. The final still uses a compact layout so the
prompt follows it without a large blank area. Content exceeding screen height
is clipped. Resize before starting for the best image fit.

The shell waits while the animation runs; Ctrl-C ends that wait immediately.
Once the prompt returns, nothing keeps redrawing. Nested shells inherit a
startup marker and do not repeat the animation. SSH and noninteractive sessions
skip startup. Opening a terminal from a process that already inherited the
marker also skips it.

## Preserve or restore the original

The installer backs up changed shell configuration and disables recognized
old art/fastfetch invocations. The original static art and scripts remain for
rollback. To restore recognized original startup lines:

```fish
.venv/bin/python animated/install.py --disable
```

Then open a new terminal. Backups remain under
`${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/animated/backups`.

Custom Fish functions, multi-line commands, or other conf.d files may still
invoke the old art. Disable those separate invocations manually; the installer
does not overwrite unknown configuration files.

The original static installer remains available as `bash install.sh`.
It supports an optional image or text-art path. Image conversion uses Pillow
only during installation; static startup reads cached terminal art.

## On-demand playback and tests

See [animated/README.md](animated/README.md) for ASCII mode and standalone playback.

```bash
bash -n install.sh bashrc-pokemon.sh
python3 -m unittest discover -s tests -v
```

Tests need Pillow; the real Fish integration test also needs Fish.

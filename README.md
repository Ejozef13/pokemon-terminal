# Pokemon Terminal — animated startup

Animated Venusaur and vertically centered fastfetch in a display pane above your
shell, automatically on every new Fish or Bash terminal. The combined display
is centered horizontally too. Original static files remain available for rollback.

## Enable on your desktop

From your existing checkout:

```fish
git pull --ff-only origin main
.venv/bin/python -m pip install -r requirements-image.txt
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif
```

This uses your existing virtualenv and tmux. For a fresh installation, first run
`python3 -m venv .venv` and install tmux through your package manager.
Open a **new terminal outside the existing tmux session** to test.

The installer copies your GIF to your XDG configuration directory, installs
Fish and Bash hooks, and backs up/disables recognized original startup lines.
It leaves the original art, scripts, and unrelated settings intact. If a custom
Fish function or another conf.d file draws the old art, disable that invocation
separately; unknown configuration files are not rewritten.

Each terminal gets its own tmux session. Your shell is focused in the lower
pane. The animation occupies the upper pane and never draws over typing.
Nested shells inside tmux and SSH sessions do not create another session.
Exiting the lower shell closes that terminal's private tmux session and returns
to the original shell. Stopping the animation only closes its display pane. Other terminals are unaffected. Very small windows
keep a regular shell.

## Tune the layout

Re-run the installer to update settings:

```fish
.venv/bin/python animated/install.py /home/ejmr/Downloads/pokemon-venusaur.gif --width 48 --gap 8 --height 55 --fps 8
```

- `--width`: sprite columns (default 48).
- `--gap`: columns between sprite and fastfetch (default 8).
- `--height`: percentage of terminal height given to the display (default 55).
- `--fps`: maximum redraw rate (default 8).

Fastfetch information is captured once when the terminal opens. Neofetch is the
fallback. Install fastfetch separately for your preferred system information.
Keep the checkout's virtualenv: the installed launcher uses that Python.

## Roll back without deleting anything

```fish
.venv/bin/python animated/install.py --disable
```

Open a new terminal. Recognized original startup lines are restored; backups
remain in `~/.config/pokemon-terminal/animated/backups` (or XDG_CONFIG_HOME).
Manual customizations outside the installer's recognized lines stay under
your control.

The desktop GIF is user supplied and is not bundled in this repository.
See [animated/README.md](animated/README.md) for on-demand GIF and ASCII playback.

---

## Original static terminal (preserved)

Venusaur art at Bash startup, with optional system information alongside it.
Requires Linux, Bash 4+, Python 3, and a UTF-8 terminal. Color images use
24-bit ANSI color and Unicode half blocks, without terminal-specific image protocols.

## Install

Use the included Venusaur design:

```bash
bash install.sh
```

Or supply your own image (transparent PNG recommended):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-image.txt
PATH="$PWD/.venv/bin:$PATH" bash install.sh /path/to/venusaur.png
```

Open a new Bash terminal. The installer works from any directory, requires no
sudo, preserves unrelated Bash configuration, and upgrades the old startup hook.
It supports XDG_CONFIG_HOME. Reinstall without arguments to refresh scripts while
keeping your chosen art. To restore the bundled art, explicitly install
`terminal-art/venusaur.txt`.

PNG, JPEG and other Pillow-supported formats work. GIFs use their first frame.
You can also supply a UTF-8 `.txt` containing plain or ANSI-colored terminal art.
Use printable, single-column characters and color codes; cursor movement and
other control codes in third-party text art are not sanitized.

Set the output width at installation:

```bash
POKEMON_WIDTH=36 PATH="$PWD/.venv/bin:$PATH" bash install.sh venusaur.png
```

Default width is 48 columns. Use a width smaller than your terminal. Transparent
borders are cropped; transparent pixels use the terminal background. Two image
pixels fit into each terminal cell vertically. Images are resized only at install
time; startup reads cached text and needs neither Python nor Pillow.

Install fastfetch or neofetch separately if you want system information.
Without either tool, art still works. Narrow terminals stack the information
below the art. The original bundled art is about 99 columns wide, so choose a
smaller custom image for narrow windows. Noninteractive and TERM=dumb shells
produce no output. Startup uses Bash arrays, with no temporary files or background
processes. Standard terminal cells are assumed to be roughly twice as tall as wide.

## Validate

```bash
bash -n install.sh bashrc-pokemon.sh
python3 -m unittest discover -s tests -v
```

Image tests require Pillow. To remove startup behavior, delete the
pokemon-terminal source line from ~/.bashrc and remove the pokemon-terminal
directory under ${XDG_CONFIG_HOME:-$HOME/.config}.

## Separate animated experiment

The original static setup remains available. See [animated/README.md](animated/README.md)
for an opt-in Venusaur player with fastfetch information, GIF idle frames,
plain ASCII mode, and a bundled-art bobbing demo. Start with:

```bash
python3 animated/venusaur.py --duration 3
```

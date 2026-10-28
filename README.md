# Pokemon Terminal

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

## Animated idle Venusaur

Animation is feasible, but an idle loop sharing the shell's drawing area can
overwrite typing, command output, or scrollback. A reliable approach is a small
dedicated tmux pane running a foreground sprite player at about 6–10 frames/sec.
It can cache GIF/sprite-sheet frames as ANSI art and redraw only its own pane,
restoring the cursor and terminal state on exit. A brief animation before the
prompt is another simpler option.

Colored half-block pixel art already works for sprites; pure ASCII is optional.
A transparent animated GIF or a sprite sheet with frame dimensions/timing is the
best input. A still image can support an artificial bobbing effect, but cannot
recreate the actual idle poses. Animation is a future feature, not implemented
by this static startup installer.

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

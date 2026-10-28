# Animated Venusaur player

For automatic Fish/Bash startup, use [the startup installer](../README.md).

The foreground player below is also available separately. It does not install anything,
change ~/.bashrc, or start a background process. Run it on demand and press Ctrl-C
to return to the shell. It uses the alternate screen and restores cursor visibility
on exit. Fastfetch is captured once at launch; neofetch is the fallback.

Try the included colored text design with a gentle vertical bob:

```bash
python3 animated/venusaur.py
```

For genuine idle poses, provide an animated GIF (requires Pillow):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-image.txt
.venv/bin/python animated/venusaur.py /path/to/venusaur.gif --width 40
```

For literal ASCII rather than colored Unicode half-block pixels:

```bash
.venv/bin/python animated/venusaur.py /path/to/venusaur.gif --ascii --width 48
```

A PNG/JPEG gets the same simulated bob as the bundled text art, not generated idle
poses. GIF frame timings are respected subject to a maximum redraw rate of 8 FPS;
adjust with --fps (1–30). Frames are converted once in memory. There is no image
asset from the chat bundled here: the inline preview was not exposed as a file.
Text input should be trusted terminal art containing printable characters and
SGR colors, not arbitrary control sequences.

To keep it moving while using your shell, run the command in a separate tmux pane.
From the repository directory, for example:

```bash
tmux split-window -h 'python3 animated/venusaur.py'
```

Use the virtualenv Python and GIF path in that command for a custom sprite.
Install tmux separately if needed. The bundled art is around 99 columns wide;
use a custom image with --width 32 for small panes. Narrow layouts stack system
information below the art; content that exceeds pane height is clipped. True-color
Unicode rendering needs a UTF-8 terminal. This player owns its pane while running;
it deliberately does not draw over an active shell prompt.

For a short startup-style preview without changing your existing startup:

```bash
python3 animated/venusaur.py --duration 3
```

## Display alignment

System information is vertically centered alongside the sprite, and the combined
block is centered within the pane. Use `--gap 8` to change the separation. Extra
vertical pane space is balanced above and below the block. Use `--quiet` to hide
the exit hint. Animation uses the alternate screen; Ctrl-C restores the terminal.

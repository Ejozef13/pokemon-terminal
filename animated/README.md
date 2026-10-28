# Venusaur startup animation

The regular-terminal startup plays for 30 seconds, leaves a still frame beside
fastfetch, and returns to the same shell. No split view or background process.
See [the installation guide](../README.md) to enable it automatically.

## Try without changing startup

```bash
.venv/bin/python animated/venusaur.py /path/to/venusaur.gif --duration 30 --keep-frame
```

Press Ctrl-C to skip to the final still. Type `clear` after the prompt appears
to remove it. Without `--keep-frame`, playback restores the previous screen
without leaving artwork. The default duration is 30 seconds; an explicit
`--duration 0` loops until Ctrl-C for manual playback only.

The bundled old text art is also available as a bobbing demo:

```bash
python3 animated/venusaur.py --duration 3 --keep-frame
```

## ASCII and colors

For literal ASCII rendering:

```bash
.venv/bin/python animated/venusaur.py /path/to/venusaur.gif --ascii --width 48 --keep-frame
```

Default rendering uses colored Unicode half blocks, keeping the sprite's pixel
colors and transparent background. PNG/JPEG input gets a simulated bob; GIF input
uses its actual frames and timing. The GIF from your desktop is not bundled here.

Frames are converted once in memory. Default redraw limit is 8 FPS; adjust with
`--fps` (1–30). System information is captured once, with fastfetch preferred
and neofetch as fallback. Playback needs no network access.

Use `--gap 8` to adjust spacing and `--quiet` to hide the skip hint. Text input
must be trusted terminal art. Choose a small enough `--width` for your window;
oversized content is clipped or replaced with a size warning.

During playback the player uses the alternate screen. When it ends, it restores
the original screen and cursor, prints the last frame as ordinary terminal output
if requested, and exits. No process remains to redraw over your commands.

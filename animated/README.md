# Live Fish prompt animation

Enable through [the installer](../README.md). The prompt is available after
preparing the image frames and fetching system information, without waiting for
the animation to finish.

Fish draws a fixed header at the first prompt and serializes frame updates with
its own input editing. A bounded Python timer updates a frame index and notifies
Fish; the timer never writes to the terminal. Fish saves/restores the visible
cursor and never modifies the command buffer.

The first command stops the timer and removes cached frames before command
output begins. Ctrl-L, Ctrl-C, another prompt, expiry, resize, and long/multiline input also stop updates.
The final sprite stays as ordinary terminal content until cleared or scrolled
away. There is no alternate screen, screen split, or scroll-region reservation.

The helper uses Linux process start times to avoid notifying a reused shell PID.
Fish exit stops the timer, and an orphaned timer cleans up when its shell exits.
Frames are cached in a private temporary directory and removed on stop.

The first-prompt clear replaces any old startup greeting image. No second image
is printed after animation expiry. Recognized legacy startup calls are backed up
and disabled by the installer.

## Standalone foreground playback

For a manual player that owns the terminal until it exits:

```bash
.venv/bin/python animated/venusaur.py /path/to/venusaur.gif --duration 30 --keep-frame
```

Ctrl-C skips to the final still. This foreground player is also the Bash startup
fallback; it is separate from the live Fish integration.

For literal ASCII instead of colored Unicode half-block pixels:

```bash
.venv/bin/python animated/venusaur.py /path/to/venusaur.gif --ascii --width 48 --keep-frame
```

Default rendering preserves sprite colors and transparent pixels. GIFs use their
actual frames and timing. PNG/JPEG input to the standalone player gets a simulated
bob. The desktop GIF is not bundled in this repository.

The old text artwork is still available for manual playback or rollback:
`python3 animated/venusaur.py --duration 3 --keep-frame`.

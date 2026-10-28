# Live Fish prompt animation

Enable through [the installer](../README.md). The prompt is available after
preparing the image frames and fetching system information, without waiting for
the animation to finish.

Fish draws a fixed header at the first prompt and serializes frame updates with
its own input editing. A lifecycle-managed Python timer updates a frame index and notifies
Fish; the timer never writes to the terminal. Fish saves/restores the visible
cursor and never modifies the command buffer.

The default idle duration is unlimited (`--duration 0`). The first command stops the timer and removes cached frames before command
output begins. Ctrl-L, Ctrl-C, another prompt, expiry, resize, and long/multiline input also stop updates.
The final sprite stays as ordinary terminal content until cleared or scrolled
away. There is no alternate screen, screen split, or scroll-region reservation.

The helper uses Linux process start times to avoid notifying a reused shell PID.
Fish exit stops the timer, and an orphaned timer cleans up when its shell exits.
Frames are cached in a private temporary directory and removed on stop.

The CachyOS dashboard is generated from Fastfetch JSON with an explicit local
module whitelist. Network modules and the global Fastfetch config are excluded.
Its ANSI-aware layout preserves colored meters and box borders when clipping.
Dates and calendar use the desktop local clock at startup.

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

Rendering preserves sprite colors and transparent pixels. Only multi-frame GIFs
are accepted. The desktop GIF is user supplied, not bundled in the repository.
There is no static-art fallback.


## Detection and cleanup

The compact dashboard uses only CachyOS green and blue. Raw sensor channels are
kept in diagnostics; CPU/GPU temperatures appear inline when identified. Repeated
Btrfs subvolumes share a single filesystem row. Basic Fastfetch data and temperature detection
are separate queries, and read-only local Linux probes fill missing fields.
Use `python3 animated/dashboard.py --diagnose` to inspect real detection failures.
Sensors are labelled by chip/card, and no privileged command runs at startup.

The retired static implementation is removed. Installation cleans its known
configuration copies and never re-enables its startup calls.

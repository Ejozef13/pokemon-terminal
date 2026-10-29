# Development

Platform setup: [For Linux](LINUX.md) · [For Windows](../windows/README.md).
The root README provides separate first-install, update and removal commands.

## Tests

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

Linux and Fish are required for real terminal integration tests. Pillow decodes
GIF frames; pyte checks the visible prompt and cursor across redraws. Fixtures
exercise hardware/sensor parsing without inventing readings on the host.

## Runtime

- `animated/render.py`: GIF frames, transparent half-block pixels, and layout.
- `animated/dashboard.py`: compact hardware/system/calendar presentation.
- `animated/hardware.py`: read-only local device and temperature probes.
- `animated/prompt.py`: cached frames and shell notification timer.
- `animated/fish-prompt.fish`: Fish-owned drawing and lifecycle events.
- `animated/install.py`: install runtime files, GIF, settings, and Fish hook.
- `animated/migration.py`: one-time removal of obsolete startup behavior.
  This installer-only compatibility code is not installed at runtime.

The timer never writes to the terminal. Fish serializes sprite drawing with input
editing and preserves cursor position. The first command stops drawing before
output begins. Exit, cancellation, resize, and timer expiry clean cached frames.
Only sprite cells redraw; the dashboard is a startup snapshot.

Fastfetch queries explicitly select local modules, excluding network data and
the user’s global config. Failed temperature queries cannot discard base system
data. Readable local probes fill missing fields. GPU temperature matching uses
device identity rather than enumeration order.

## Installed paths

Default paths follow XDG overrides:

- `${XDG_DATA_HOME:-~/.local/share}/pokemon-terminal/venv`: private Python environment.
- `${XDG_CONFIG_HOME:-~/.config}/pokemon-terminal/animated`: runtime, GIF, settings, backups.
- `${XDG_CONFIG_HOME:-~/.config}/fish/conf.d/pokemon-terminal-animated.fish`: startup hook.

The installed runtime imports only its own modules and the managed environment.
It does not import code from the checkout. Keep the managed environment in place.

## Animation asset

The installer accepts a multi-frame GIF, preferring a bundled
`assets/venusaur.gif`, then an installed GIF, then
`~/Downloads/pokemon-venusaur.gif` if no argument is supplied.

Use the original GIF bytes to reproduce an exact animation. Inline previews or
a newly generated sprite are not substitutes. No asset should be silently
downloaded or replaced with a different design.

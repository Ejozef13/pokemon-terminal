# Pokémon Terminal

Animated Venusaur and a compact CachyOS dashboard in a normal **Fish** terminal.
Your prompt works while Venusaur idles. The first command freezes the animation;
`clear` or Ctrl-L removes it.

- Green/blue hardware and system sections, with no network or Display row.
- CPU/GPU temperatures inline and one usage meter per filesystem.
- Blue date/weekdays, white calendar numbers, and black-on-green today.
- Aligned open section rules and palette dots from your terminal’s color scheme.
- No idle timeout, split panes, or static Venusaur fallback.

## Install

Requires Linux, Fish (tested with 4.x), Python 3.10+ with venv/pip, and a UTF-8 true-color terminal.
Fastfetch and PCI tools improve hardware detection.

On CachyOS / Arch:

```fish
sudo pacman -S --needed git fish python python-pip fastfetch lm_sensors pciutils
git clone https://github.com/Ejozef13/pokemon-terminal.git
cd pokemon-terminal
bash install.sh ~/Downloads/pokemon-venusaur.gif
```

Use the original animated GIF from your desktop. The installer copies it into
your configuration, so the Downloads copy is not needed afterward. When
`assets/venusaur.gif` is bundled in the checkout, `bash install.sh` also works
without a path. An existing installation automatically reuses its installed GIF.

Open a **new Fish terminal**. If your terminal starts another shell, select Fish
in its profile. For the full layout, use a wide window about 40 text rows tall.
Your terminal controls its own font, wallpaper, transparency, and ANSI palette.

The installed app and its private Python environment live in your user
directories, **outside this checkout**. You can rename or remove the clone after
installation. No desktop-specific paths or existing project virtualenv are needed.

## Update or adjust

From a checkout:

```fish
git pull --ff-only
bash install.sh
```

The approved layout is the default: width 48, gap 8, 8 FPS, no idle timeout.
Optional adjustments:

```fish
bash install.sh --width 48 --gap 8 --fps 8 --duration 0
```

Animation stops on the first command, clearing/cancelling input, resizing,
another prompt, or long/multiline input that could scroll the header. The last
frame stays until cleared or scrolled away. Nested shells and SSH skip startup.

## Disable or diagnose

```fish
bash install.sh --disable
bash install.sh --diagnose
```

No elevated permissions are used during startup. Sensors depend on what the
kernel and drivers expose; unavailable values are never invented. Raw sensor
readings stay in diagnostics rather than cluttering the dashboard.

Updates retire known obsolete launchers and static-art copies. Existing shell
configuration is backed up before recognized conflicting startup calls are
disabled. Unrelated settings and artwork are preserved.

## Project

```text
install.sh          One-command setup, update, disable, and diagnostics
animated/           Fish runtime, rendering, hardware detection, and installer
requirements.txt    Runtime dependency
docs/DEVELOPMENT.md  Architecture and validation
tests/              Rendering, hardware, migration, and live Fish checks
```

Hardware values and available sensors reflect the machine where it runs.
See [development notes](docs/DEVELOPMENT.md) for testing and installed paths.

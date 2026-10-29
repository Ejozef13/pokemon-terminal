# For Linux — Fish

[Back to platform selection](../README.md) · [For Windows](../windows/README.md)

Requires Linux, Fish (tested with 4.x), Python 3.10+ with venv/pip, and a UTF-8 true-color terminal.
Fastfetch and PCI tools improve hardware detection.

On CachyOS / Arch:

```fish
sudo pacman -S --needed git fish python python-pip fastfetch lm_sensors pciutils
git clone https://github.com/Ejozef13/pokemon-terminal.git
cd pokemon-terminal
bash install.sh ~/Downloads/pokemon-venusaur.gif
```

On Debian / Ubuntu, install the base prerequisites instead, then use the same
clone/install commands:

```bash
sudo apt update
sudo apt install git fish python3 python3-venv python3-pip pciutils lm-sensors
```

Fastfetch is optional; install it using your distribution's supported packages
for richer desktop and hardware information. Fish 4.x is the tested version;
older distribution versions have not been verified.

Supply your animated GIF (it is not bundled with this repository). The installer copies it into
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

## Use another Pokémon GIF

Venusaur is the default design for this layout. Want a different Pokémon?
Clone or fork this repository and install your own animated GIF:

```fish
bash install.sh ~/Downloads/your-pokemon.gif
```

The installer copies the GIF into your configuration and keeps the same
dashboard, calendar, colors, and immediately usable Fish prompt. Use a looping,
transparent animated GIF with at least two frames for the best result. Different
sprite proportions may need a width adjustment:

```fish
bash install.sh ~/Downloads/your-pokemon.gif --width 48
```

To make your chosen Pokémon the default in your own fork, put its GIF at
`assets/venusaur.gif` (keep that filename), commit it, and run `bash install.sh`.
Replacing the GIF changes the sprite; it does not change the dashboard layout.

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


See [development notes](DEVELOPMENT.md) for architecture and tests.

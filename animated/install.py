#!/usr/bin/env python3
"""Install animated-only startup and retire obsolete static startup copies."""
import argparse
import math
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
from migration import FISH_NAME, migrate, write_config

RUNTIME_FILES = ('render.py', 'prompt.py', 'dashboard.py', 'hardware.py', 'fish-prompt.fish')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gif', nargs='?', type=Path)
    parser.add_argument('--disable', action='store_true')
    parser.add_argument('--width', type=int, default=48)
    parser.add_argument('--gap', type=int, default=8)
    parser.add_argument('--fps', type=int, default=8)
    parser.add_argument('--duration', type=float, default=0, help='Maximum idle animation seconds; 0 means no timeout')
    args = parser.parse_args()
    if not 8 <= args.width <= 120 or not 1 <= args.gap <= 40 or not 1 <= args.fps <= 30 or not math.isfinite(args.duration) or not 0 <= args.duration <= 300:
        parser.error('width: 8–120, gap: 1–40, fps: 1–30, duration: 0 (indefinite) to 300')
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    base = config_home / 'pokemon-terminal/animated'
    backups = base / 'backups'
    bashrc = Path.home() / '.bashrc'
    fish_config = config_home / 'fish/config.fish'
    fish_hook = config_home / 'fish/conf.d' / FISH_NAME
    # Validate all inputs before changing any startup configuration.
    if not args.disable:
        if not args.gif:
            candidates = (ROOT / 'assets/venusaur.gif', base / 'venusaur.gif',
                          Path.home() / 'Downloads/pokemon-venusaur.gif')
            args.gif = next((path for path in candidates if path.is_file()), None)
        if not args.gif:
            parser.error('Animated GIF not found. Run: bash install.sh /path/to/pokemon-venusaur.gif')
        try:
            from PIL import Image
            with Image.open(args.gif) as image:
                if getattr(image, 'n_frames', 1) < 2:
                    parser.error('Use a multi-frame animated GIF for real idle animation')
                if image.n_frames > 300:
                    parser.error('Use a GIF with at most 300 frames')
                for frame in range(image.n_frames):
                    image.seek(frame)
                    image.load()
        except (ImportError, OSError, ValueError) as error:
            parser.error(f'Cannot read GIF: {error}. Use the virtualenv with Pillow installed.')
    originals = [(bashrc, bashrc.read_text())] if bashrc.is_file() else []
    fish_files = {fish_config}
    fish_files.update((config_home / 'fish/conf.d').glob('*.fish'))
    fish_files.update((config_home / 'fish/functions').glob('*pokemon*.fish'))
    fish_files.update((config_home / 'fish/functions').glob('*venusaur*.fish'))
    fish_files.add(config_home / 'fish/functions/fish_greeting.fish')
    for path in sorted(fish_files):
        if path == fish_hook or not path.is_file():
            continue
        if path.is_symlink():
            print(f'Skipping linked config: {path}; inspect its old art call manually.')
            continue
        originals.append((path, path.read_text()))
    for path, text in originals:
        migrate(text, args.disable)  # Preflight malformed blocks.
    base.mkdir(parents=True, exist_ok=True)
    if args.disable:
        (base / 'enabled').unlink(missing_ok=True)
        for path, text in originals:
            write_config(path, migrate(text, True), backups)
        if fish_hook.exists():
            write_config(fish_hook, '# Animated Pokemon startup disabled.\n', backups)
        print('Animated startup disabled. Retired startup calls remain disabled. Open a new terminal.')
        return
    for name in RUNTIME_FILES:
        shutil.copy2(ROOT / 'animated' / name, base / name)
    # Retire old installed launchers as well as their startup block.
    for name in ('startup.py', 'venusaur.py'):
        (base / name).unlink(missing_ok=True)
    destination = base / 'venusaur.gif'
    if args.gif.resolve() != destination.resolve():
        shutil.copy2(args.gif, destination)
    config = dict(python=str(Path(sys.executable).absolute()), width=args.width,
                  gap=args.gap, fps=args.fps, duration=args.duration)
    (base / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    for path, text in originals:
        write_config(path, migrate(text), backups)
    fish = """# Managed by pokemon-terminal animated installer.
if status is-interactive; and not set -q POKEMON_TERMINAL_SHOWN; and not set -q SSH_CONNECTION
    if test "$TERM" != dumb
        set -l pokemon_config "$HOME/.config"
        if set -q XDG_CONFIG_HOME
            set pokemon_config "$XDG_CONFIG_HOME"
        end
        set -g _pokemon_base "$pokemon_config/pokemon-terminal/animated"
        if test -f "$_pokemon_base/enabled"
            set -g _pokemon_python (python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["python"])' "$_pokemon_base/config.json")
            if test -x "$_pokemon_python"
                set -gx POKEMON_TERMINAL_SHOWN 1
                source "$_pokemon_base/fish-prompt.fish"
            end
        end
    end
end
"""
    write_config(fish_hook, fish, backups)
    # Only delete known retired application files, not unrelated user artwork.
    for retired in (base.parent / 'bashrc-pokemon.sh',
                    base.parent / 'terminal-art/venusaur.txt'):
        if retired.is_file() or retired.is_symlink():
            retired.unlink()
            print(f'Removed retired static file: {retired}')
    retired_dir = base.parent / 'terminal-art'
    if retired_dir.is_dir() and not retired_dir.is_symlink() and not any(retired_dir.iterdir()):
        retired_dir.rmdir()
    (base / 'enabled').touch()
    limit = f'up to {args.duration:g}s' if args.duration else 'no idle timeout'
    print(f'Fish: prompt available during animation ({limit}); first command freezes it.')
    print('Startup runs in Fish; select Fish as your terminal profile shell.')
    print('Open a NEW terminal. Use clear or Ctrl-L for a clean workspace.')
    print('Static implementation removed; matching startup calls backed up and disabled.')
    print('Recognized old art calls in Fish config, conf.d, and greeting files are disabled.')
    print('First-prompt drawing clears stale startup artwork and scrollback.')
    print('Disable: bash install.sh --disable')


if __name__ == '__main__':
    main()

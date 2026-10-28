#!/usr/bin/env python3
"""Enable or disable animated startup, preserving original files for rollback."""
import argparse
import math
import json
import os
import re
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TAG = '# pokemon-terminal animated: disabled original: '
SUPPRESSED = 'true # pokemon-terminal animated: suppressed startup'
BASH_START = '# >>> pokemon-terminal animated >>>'
BASH_END = '# <<< pokemon-terminal animated <<<'
FISH_NAME = 'pokemon-terminal-animated.fish'


def strip_block(text):
    lines, inside = [], False
    for line in text.splitlines(keepends=True):
        if line.rstrip() == BASH_START:
            inside = True
        elif line.rstrip() == BASH_END:
            inside = False
        elif not inside:
            lines.append(line)
    if inside:
        raise ValueError('Incomplete animated startup block; restore its backup first')
    return ''.join(lines)


def migrate(text, disable=False):
    text = strip_block(text)
    result = []
    for line in text.splitlines(keepends=True):
        if disable:
            if line.rstrip() != SUPPRESSED:
                result.append(line[len(TAG):] if line.startswith(TAG) else line)
        elif line.startswith(TAG) or line.lstrip().startswith('#'):
            result.append(line)
        elif ('bashrc-pokemon.sh' in line or
              re.match(r'^\s*(?:command\s+)?(?:fastfetch|neofetch|venusaur|pokemon-terminal|pokemon_terminal)(?:\s|$)', line) or
              (re.match(r'^\s*(?:command\s+)?(?:cat|chafa|viu|jp2a|source|\.)(?:\s|$)', line)
               and re.search(r'venusaur|pokemon-terminal|terminal-art', line, re.I))):
            # Keep an if/function body syntactically valid when its only
            # command was the old startup invocation.
            if line.rstrip().endswith('\\'):
                result.append(line)  # Multi-line custom commands need manual review.
            else:
                result.append(TAG + line.rstrip('\n') + '\n' + SUPPRESSED + '\n')
        else:
            result.append(line)
    return ''.join(result)


def write_config(path, text, backups):
    if path.is_file() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = backups / (path.name + '.' + str(time.time_ns()))
        backups.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        print(f'Backup: {backup}')
    path.write_text(text)


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
            parser.error('Supply your animated GIF, or use --disable')
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
    originals = [(bashrc, bashrc.read_text() if bashrc.exists() else '')]
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
        print('Animated startup disabled. Original startup lines restored. Open a new terminal.')
        return
    shutil.copy2(ROOT / 'animated/venusaur.py', base / 'venusaur.py')
    shutil.copy2(ROOT / 'animated/startup.py', base / 'startup.py')
    shutil.copy2(ROOT / 'animated/prompt.py', base / 'prompt.py')
    shutil.copy2(ROOT / 'animated/dashboard.py', base / 'dashboard.py')
    shutil.copy2(ROOT / 'animated/fish-prompt.fish', base / 'fish-prompt.fish')
    destination = base / 'venusaur.gif'
    if args.gif.resolve() != destination.resolve():
        shutil.copy2(args.gif, destination)
    config = dict(python=str(Path(sys.executable).absolute()), width=args.width,
                  gap=args.gap, fps=args.fps, duration=args.duration)
    (base / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    # Fixed hook paths expand XDG_CONFIG_HOME at startup and support spaces.
    bash_hook = '''
# >>> pokemon-terminal animated >>>
if [[ $- == *i* && -z ${POKEMON_TERMINAL_SHOWN:-} && -z ${SSH_CONNECTION:-} && ${TERM:-dumb} != dumb ]]; then
    _pokemon_dir="${XDG_CONFIG_HOME:-$HOME/.config}/pokemon-terminal/animated"
    if [[ -f "$_pokemon_dir/enabled" ]]; then
        # Read the interpreter path as data, never as shell code.
        _pokemon_python=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["python"])' "$_pokemon_dir/config.json")
        if [[ -x "$_pokemon_python" ]]; then
            export POKEMON_TERMINAL_SHOWN=1
            "$_pokemon_python" "$_pokemon_dir/startup.py"
        fi
    fi
    unset _pokemon_dir _pokemon_python
fi
# <<< pokemon-terminal animated <<<
'''
    for path, text in originals:
        updated = migrate(text)
        if path == bashrc:
            updated = updated.rstrip('\n') + '\n' + bash_hook
        write_config(path, updated, backups)
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
    (base / 'enabled').touch()
    limit = f'up to {args.duration:g}s' if args.duration else 'no idle timeout'
    print(f'Fish: prompt available during animation ({limit}); first command freezes it.')
    print('Bash: timed foreground playback remains available; idle-prompt animation requires Fish.')
    print('Open a NEW terminal. Use clear or Ctrl-L for a clean workspace.')
    print('Original files retained; matching startup lines backed up and disabled.')
    print('Recognized old art calls in Fish config, conf.d, and greeting files are disabled.')
    print('First-prompt drawing clears remaining startup artwork without deleting its files.')
    print('Rollback: python3 animated/install.py --disable')


if __name__ == '__main__':
    main()

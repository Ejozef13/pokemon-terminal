#!/usr/bin/env python3
"""Foreground Bash fallback; Fish uses fish-prompt.fish for a live prompt."""
import json
import os
from pathlib import Path
import sys

from venusaur import main as play


def main():
    base = Path(__file__).resolve().parent
    if os.environ.get('SSH_CONNECTION'):
        return
    if not (base / 'enabled').exists() or not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    try:
        config = json.loads((base / 'config.json').read_text())
        play([str(base / 'venusaur.gif'), '--width', str(config['width']),
              '--gap', str(config['gap']), '--fps', str(config['fps']),
              '--duration', str(config.get('duration', 30)), '--keep-frame', '--quiet'])
    except (SystemExit, KeyboardInterrupt):
        # Player errors already explain themselves; startup must not close the shell.
        return
    except (OSError, ValueError, KeyError) as error:
        print(f'Pokemon startup: {error}; returning to your shell.', file=sys.stderr)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Prepare fixed terminal frames; the timer signals Fish but never draws."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from venusaur import layout, load_frames, system_info

MAGIC = 'pokemon-terminal-prompt-v1'


def prepare(base, columns, lines):
    if columns < 45 or lines < 16:
        return None
    from PIL import Image
    config = json.loads((base / 'config.json').read_text())
    panel_width = min(76, max(32, columns - config['gap'] - min(config['width'], 32) - 1))
    info = system_info(panel_width)
    available = lines - 8
    if len(info) > available:
        from dashboard import color, CYAN
        info = info[:available - 1] + [color('Enlarge the terminal for the full calendar.', CYAN)]
    width = min(config['width'], max(1, columns - config['gap'] - panel_width - 1))
    with Image.open(base / 'venusaur.gif') as image:
        width = min(width, max(1, math.floor(available * 2 * image.width / image.height)))
    frames, durations = load_frames(base / 'venusaur.gif', width, False)
    rendered = [layout(frame, info, columns, available + 2, 0,
                       config['gap'], center_vertical=False) for frame in frames]
    rows = max(map(len, rendered))
    cache = Path(tempfile.mkdtemp(prefix='pokemon-terminal-'))
    try:
        for index, frame in enumerate(rendered):
            # Fully overwrite only the fixed header. Never touch the prompt rows.
            payload = ''.join(f'\033[{row + 1};1H\033[2K' +
                              (frame[row] if row < len(frame) else '')
                              for row in range(rows)) + '\033[0m'
            (cache / f'{index}.ansi').write_text(payload)
        metadata = dict(magic=MAGIC, rows=rows, durations=durations,
                        fps=config['fps'], duration=config.get('duration', 0))
        (cache / 'meta.json').write_text(json.dumps(metadata))
        (cache / 'index').write_text('0\n')
    except BaseException:
        shutil.rmtree(cache)
        raise
    return cache


def metadata(cache):
    if not cache.name.startswith('pokemon-terminal-') or cache.is_symlink():
        raise ValueError('Invalid frame cache')
    data = json.loads((cache / 'meta.json').read_text())
    if data.get('magic') != MAGIC:
        raise ValueError('Invalid frame metadata')
    return data


def process_identity(pid):
    # PID plus Linux start time prevents signalling a subsequently reused PID.
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def tick(cache, pid, identity):
    data = metadata(cache)
    start = time.monotonic()
    index = 0
    deadline = start + max(1 / data['fps'], data['durations'][0])
    try:
        while cache.exists() and process_identity(pid) == identity:
            now = time.monotonic()
            if data['duration'] > 0 and now - start >= data['duration']:
                # Tell Fish to clean up, leaving the last drawn frame untouched.
                next_index = -1
            elif now < deadline:
                time.sleep(min(.05, deadline - now))
                continue
            else:
                index = (index + 1) % len(data['durations'])
                next_index = index
                deadline = now + max(1 / data['fps'], data['durations'][index])
            temporary = cache / 'next'
            temporary.write_text(str(next_index) + '\n')
            temporary.replace(cache / 'index')
            os.kill(pid, signal.SIGUSR1)
            if next_index == -1:
                return
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        pass
    finally:
        # Normal expiry is cleaned by Fish after consuming the -1 index.
        if process_identity(pid) != identity:
            shutil.rmtree(cache, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('base', type=Path)
    prep.add_argument('columns', type=int)
    prep.add_argument('lines', type=int)
    launch = commands.add_parser('start')
    launch.add_argument('cache', type=Path)
    launch.add_argument('pid', type=int)
    timer = commands.add_parser('tick')
    timer.add_argument('cache', type=Path)
    timer.add_argument('pid', type=int)
    timer.add_argument('identity')
    clean = commands.add_parser('stop')
    clean.add_argument('cache', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            cache = prepare(args.base, args.columns, args.lines)
            if cache:
                print(cache)
                print(metadata(cache)['rows'])
        elif args.command == 'start':
            metadata(args.cache)
            identity = process_identity(args.pid)
            if identity is None:
                raise ValueError('Fish process is unavailable')
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'tick',
                              str(args.cache), str(args.pid), identity],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        elif args.command == 'tick':
            tick(args.cache, args.pid, args.identity)
        elif args.command == 'stop' and args.cache.exists():
            metadata(args.cache)
            shutil.rmtree(args.cache)
    except (OSError, ValueError, KeyError, ImportError) as error:
        print(f'Pokemon prompt: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Launch one independent tmux session per terminal, with a display above a shell."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid


def main():
    base = Path(__file__).resolve().parent
    if os.environ.get('TMUX') or os.environ.get('SSH_CONNECTION'):
        return
    if not (base / 'enabled').exists() or not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    tmux = shutil.which('tmux')
    if not tmux:
        print('Pokemon startup: install tmux or disable animated startup.', file=sys.stderr)
        return
    session = 'pokemon-' + uuid.uuid4().hex[:12]
    try:
        config = json.loads((base / 'config.json').read_text())
        python = config['python']
        # Validate before taking over the shell; a broken dependency never traps login.
        subprocess.run([python, '-c', 'from PIL import Image'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if not (base / 'venusaur.gif').is_file():
            raise ValueError('installed GIF is missing')
        columns, lines = shutil.get_terminal_size()
        if columns < 45 or lines < 18:
            print('Pokemon startup: window too small; keeping the normal shell.', file=sys.stderr)
            return
        display_rows = max(8, min(lines - 8, round(lines * config['height'] / 100)))
        shell = os.environ.get('SHELL', '/bin/bash')
        if not Path(shell).is_file():
            shell = '/bin/bash'
        # A shell-local cleanup command targets this exact session. Avoid tmux
        # global exit hooks so separate terminals cannot affect one another.
        shell_command = shlex.join([shell, '-i']) + '; ' + shlex.join(
            [tmux, 'kill-session', '-t', session])
        shell_pane = subprocess.run(
            [tmux, 'new-session', '-d', '-P', '-F', '#{pane_id}', '-s', session,
             '-x', str(columns), '-y', str(lines), '-c', os.getcwd(),
             shlex.join(['/bin/sh', '-c', shell_command])], check=True, capture_output=True, text=True
        ).stdout.strip()
        command = shlex.join([python, str(base / 'venusaur.py'),
                              str(base / 'venusaur.gif'), '--width', str(config['width']),
                              '--gap', str(config['gap']), '--fps', str(config['fps']),
                              '--quiet'])
        subprocess.run([tmux, 'split-window', '-v', '-b', '-l', str(display_rows),
                        '-t', shell_pane, command], check=True)
        # Focus the lower shell. Stopping the animation leaves the shell usable.
        subprocess.run([tmux, 'set-option', '-w', '-t', shell_pane,
                        'remain-on-exit', 'off'], check=True)
        subprocess.run([tmux, 'select-pane', '-t', shell_pane], check=True)
        # Hook runs this launcher as a child. On detach/exit it returns to that
        # original shell; a later terminal gets a distinct, fresh session.
        subprocess.run([tmux, 'attach-session', '-t', session], check=True)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Pokemon startup: {error}; keeping the normal shell.', file=sys.stderr)
    finally:
        # Only ever remove the session created for this terminal.
        subprocess.run([tmux, 'kill-session', '-t', session],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    main()

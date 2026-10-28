import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / 'config with spaces'
        self.base = self.config / 'pokemon-terminal/animated'
        self.tools = self.home / 'bin'
        self.tools.mkdir()
        tmux = self.tools / 'tmux'
        tmux.write_text('#!/bin/sh\nexit 0\n')
        tmux.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.config),
                        PATH=str(self.tools) + ':' + os.environ['PATH'])
        self.gif = self.home / 'sprite with spaces.gif'
        Image.new('RGBA', (4, 4), 'red').save(
            self.gif, save_all=True, append_images=[Image.new('RGBA', (4, 4), 'blue')],
            duration=[120, 240], loop=0)

    def install(self, *args):
        return subprocess.run(['python3', str(ROOT / 'animated/install.py'), *map(str, args)],
                              env=self.env, capture_output=True, text=True)

    def test_install_reinstall_disable(self):
        bashrc = self.home / '.bashrc'
        original = '# my config\n[ -f ~/.config/pokemon-terminal/bashrc-pokemon.sh ] && source ~/.config/pokemon-terminal/bashrc-pokemon.sh\n'
        bashrc.write_text(original)
        fish_config = self.config / 'fish/config.fish'
        fish_config.parent.mkdir(parents=True)
        fish_original = '# keep function\nif status is-interactive\n    fastfetch\nend\n'
        fish_config.write_text(fish_original)
        result = self.install(self.gif)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.base / 'venusaur.gif').read_bytes(), self.gif.read_bytes())
        self.assertTrue((self.base / 'enabled').exists())
        first = bashrc.read_text()
        self.assertIn('# pokemon-terminal animated: disabled original:', first)
        result = self.install(self.gif)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(bashrc.read_text(), first)
        self.assertTrue(list((self.base / 'backups').iterdir()))
        # Installer writes syntactically valid hooks, without interpreting paths.
        subprocess.run(['bash', '-n', str(bashrc)], check=True)
        fish = shutil.which('fish')
        if fish:
            subprocess.run([fish, '-n', str(self.config / 'fish/conf.d/pokemon-terminal-animated.fish')],
                           check=True)
        result = self.install('--disable')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(bashrc.read_text().strip(), original.strip())
        self.assertEqual(fish_config.read_text(), fish_original)
        self.assertFalse((self.base / 'enabled').exists())

    def test_bad_gif_does_not_change_startup(self):
        (self.home / '.bashrc').write_text('# keep exactly\n')
        result = self.install(self.home / 'missing.gif')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.home / '.bashrc').read_text(), '# keep exactly\n')
        self.assertFalse(self.base.exists())

    def test_nested_session_does_not_launch(self):
        subprocess.run(['python3', str(ROOT / 'animated/startup.py')],
                       env=dict(self.env, TMUX='already running'), check=True)

    @unittest.skipUnless(shutil.which('tmux') and shutil.which('fish'), 'requires tmux and Fish')
    def test_real_fish_startup_two_terminals(self):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time

        real_tmux, real_fish = shutil.which('tmux'), shutil.which('fish')
        (self.tools / 'tmux').unlink()
        fetch = self.tools / 'fastfetch'
        fetch.write_text('#!/bin/sh\nprintf "OS: StartupTest\\n"\n')
        fetch.chmod(0o755)
        sockets = self.home / 'sockets'
        sockets.mkdir(mode=0o700)
        # Extracted Fish packages may lack their compiled /usr/share assets.
        # Source the actual generated hook via Fish's init command in that case.
        shell = real_fish
        if not Path('/usr/share/fish/config.fish').exists():
            import shlex
            wrapper = self.tools / 'fish'
            hook = 'source "$XDG_CONFIG_HOME/fish/conf.d/pokemon-terminal-animated.fish"'
            wrapper.write_text('#!/bin/sh\nexec ' + shlex.join(
                [real_fish, '--no-config', '--init-command', hook]) + ' "$@"\n')
            wrapper.chmod(0o755)
            shell = str(wrapper)
        self.env.update(TERM='xterm-256color', SHELL=shell, TMUX_TMPDIR=str(sockets))
        self.env.pop('TMUX', None)
        self.env.pop('SSH_CONNECTION', None)
        (self.home / '.tmux.conf').write_text('set -g base-index 1\nsetw -g pane-base-index 1\n')
        result = self.install(self.gif)
        self.assertEqual(result.returncode, 0, result.stderr)
        processes, masters = [], []

        def terminal():
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 140, 0, 0))

            def controlling_terminal():
                os.setsid()
                fcntl.ioctl(0, termios.TIOCSCTTY, 0)

            process = subprocess.Popen([shell, '-i'], stdin=slave, stdout=slave,
                                       stderr=slave, env=self.env,
                                       preexec_fn=controlling_terminal)
            os.close(slave)
            processes.append(process)
            masters.append(master)

        try:
            terminal()
            terminal()
            deadline = time.monotonic() + 12
            sessions = []
            terminal_output = bytearray()
            while time.monotonic() < deadline:
                for master in masters:
                    if select.select([master], [], [], .02)[0]:
                        try:
                            terminal_output.extend(os.read(master, 65536))
                        except OSError:
                            pass
                listed = subprocess.run([real_tmux, 'list-sessions', '-F', '#S'],
                                        env=self.env, capture_output=True, text=True)
                sessions = listed.stdout.splitlines()
                if len(sessions) == 2:
                    panes = subprocess.run([real_tmux, 'list-panes', '-a', '-F', '#{pane_id}'],
                                           env=self.env, capture_output=True, text=True)
                    if len(panes.stdout.splitlines()) == 4:
                        break
            self.assertEqual(len(sessions), 2, listed.stderr + terminal_output[-2000:].decode(errors='replace'))
            panes = subprocess.run([real_tmux, 'list-panes', '-a', '-F',
                                    '#{pane_id} #{pane_current_command}'],
                                   env=self.env, capture_output=True, text=True, check=True)
            self.assertEqual(len(panes.stdout.splitlines()), 4, panes.stdout)
            # Let fastfetch and the frame renderer finish, then inspect actual panes.
            deadline = time.monotonic() + 5
            captured = ''
            while time.monotonic() < deadline:
                captured = ''
                for line in panes.stdout.splitlines():
                    captured += subprocess.run([real_tmux, 'capture-pane', '-p', '-t', line.split()[0]],
                                               env=self.env, capture_output=True, text=True).stdout
                if 'OS: StartupTest' in captured:
                    break
            self.assertIn('OS: StartupTest', captured)
            active = subprocess.run([real_tmux, 'list-panes', '-t', sessions[0], '-F',
                                     '#{pane_id} #{pane_active}'],
                                    env=self.env, capture_output=True, text=True, check=True)
            shell_pane = next(line.split()[0] for line in active.stdout.splitlines()
                              if line.endswith(' 1'))
            subprocess.run([real_tmux, 'send-keys', '-t', shell_pane,
                            'echo SHELL_READY', 'Enter'], env=self.env, check=True)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                shell_output = subprocess.run([real_tmux, 'capture-pane', '-p', '-t', shell_pane],
                                              env=self.env, capture_output=True, text=True).stdout
                if '\nSHELL_READY\n' in shell_output:
                    break
            self.assertIn('\nSHELL_READY\n', shell_output)
            # Exiting one shell removes only its own animated session.
            subprocess.run([real_tmux, 'send-keys', '-t', shell_pane, 'exit', 'Enter'],
                           env=self.env, check=True)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                remaining = subprocess.run([real_tmux, 'list-sessions', '-F', '#S'],
                                           env=self.env, capture_output=True, text=True).stdout.splitlines()
                if len(remaining) == 1 and sessions[0] not in remaining:
                    break
            self.assertEqual(len(remaining), 1, str(remaining) + panes.stdout)
            self.assertNotIn(sessions[0], remaining, 'initial=' + str(sessions) + ' panes=' + panes.stdout + ' active=' + active.stdout + terminal_output[-500:].decode(errors='replace'))
        finally:
            subprocess.run([real_tmux, 'kill-server'], env=self.env, capture_output=True)
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            for master in masters:
                os.close(master)

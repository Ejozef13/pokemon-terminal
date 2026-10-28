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

    def test_upgrade_replaces_previous_launcher(self):
        self.base.mkdir(parents=True)
        (self.base / 'startup.py').write_text('# previous split-view launcher\n')
        (self.base / 'config.json').write_text(json.dumps({'height': 55}))
        hook = self.config / 'fish/conf.d/pokemon-terminal-animated.fish'
        hook.parent.mkdir(parents=True)
        hook.write_text('# previous split-view hook\n')
        result = self.install(self.gif)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.base / 'config.json').read_text())
        self.assertEqual(config['duration'], 30)
        self.assertNotIn('height', config)
        self.assertNotIn('previous split-view', (self.base / 'startup.py').read_text())
        self.assertIn('POKEMON_TERMINAL_SHOWN', hook.read_text())
        self.assertTrue(list((self.base / 'backups').glob(hook.name + '.*')))

    def test_bad_gif_does_not_change_startup(self):
        (self.home / '.bashrc').write_text('# keep exactly\n')
        result = self.install(self.home / 'missing.gif')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.home / '.bashrc').read_text(), '# keep exactly\n')
        self.assertFalse(self.base.exists())

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_fish_startup_returns_to_same_shell_with_still(self):
        self.check_fish_startup(skip=False)

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_fish_ctrl_c_skips_to_prompt(self):
        self.check_fish_startup(skip=True)

    def check_fish_startup(self, skip):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time

        fish = shutil.which('fish')
        fetch = self.tools / 'fastfetch'
        fetch.write_text('#!/bin/sh\nprintf "OS: StartupTest\\n"\n')
        fetch.chmod(0o755)
        self.env.update(TERM='xterm-256color')
        self.env.pop('POKEMON_TERMINAL_SHOWN', None)
        self.env.pop('SSH_CONNECTION', None)
        result = self.install(self.gif, '--duration', '30' if skip else '.2')
        self.assertEqual(result.returncode, 0, result.stderr)
        hook = 'bind \\r execute; bind \\n execute; source "$XDG_CONFIG_HOME/fish/conf.d/pokemon-terminal-animated.fish"'
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 140, 0, 0))

        def controlling_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        process = subprocess.Popen(
            [fish, '--no-config', '--init-command', hook, '-i'],
            stdin=slave, stdout=slave, stderr=slave, env=self.env,
            preexec_fn=controlling_terminal)
        os.close(slave)
        output = bytearray()

        def read_until(predicate):
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        output.extend(os.read(master, 65536))
                    except OSError:
                        break
                if predicate(bytes(output)):
                    return
            self.fail('Terminal did not reach expected state: ' + repr(bytes(output[-1000:])))

        try:
            if skip:
                read_until(lambda data: b'OS: StartupTest' in data)
                os.write(master, b'\x03')
            read_until(lambda data: b'OS: StartupTest' in data.split(b'\x1b[?1049l')[-1]
                       and b'\x1b[?1049l' in data)
            os.write(master, b'echo SHELL_READY\r')
            read_until(lambda data: b'\rSHELL_READY\r\n' in data)
            # Nested shells inherit the marker and skip another 30-second splash.
            os.write(master, b'fish --no-config --init-command \'source "$XDG_CONFIG_HOME/fish/conf.d/pokemon-terminal-animated.fish"\' -c \'echo NESTED_READY\'\r')
            read_until(lambda data: b'\rNESTED_READY\r\n' in data)
            self.assertEqual(bytes(output).count(b'\x1b[?1049h'), 1)
            self.assertIn(b'\x1b[?25h', output)
            os.write(master, b'exit\r')
            process.wait(timeout=5)
            self.assertEqual(process.returncode, 0)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            os.close(master)

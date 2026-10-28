import json
import re
import pyte
import os
from pathlib import Path
import shutil
import shlex
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
        self.assertIn('# my config', bashrc.read_text())
        self.assertIn('# pokemon-terminal animated: disabled original:', bashrc.read_text())
        self.assertIn('# keep function', fish_config.read_text())
        self.assertIn('# pokemon-terminal animated: disabled original:', fish_config.read_text())
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
        self.assertEqual(config['duration'], 0)
        self.assertNotIn('height', config)
        self.assertNotIn('previous split-view', (self.base / 'startup.py').read_text())
        self.assertIn('POKEMON_TERMINAL_SHOWN', hook.read_text())
        self.assertTrue(list((self.base / 'backups').glob(hook.name + '.*')))

    def test_old_art_in_confd_and_greeting_never_returns_on_disable(self):
        greeting = self.config / 'fish/functions/fish_greeting.fish'
        extra = self.config / 'fish/conf.d/old-pokemon.fish'
        greeting.parent.mkdir(parents=True)
        extra.parent.mkdir(parents=True)
        originals = {
            greeting: 'function fish_greeting\n    cat ~/.config/terminal-art/venusaur.txt\n    echo keep-my-greeting\nend\n',
            extra: 'if status is-interactive\n    chafa ~/Pictures/venusaur.png\nend\n'
        }
        for path, text in originals.items():
            path.write_text(text)
        result = self.install(self.gif)
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in originals:
            self.assertIn('# pokemon-terminal animated: disabled original:', path.read_text())
        self.assertIn('echo keep-my-greeting', greeting.read_text())
        result = self.install('--disable')
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in originals:
            self.assertIn('# pokemon-terminal animated: disabled original:', path.read_text())

    def test_retired_copies_are_deleted_but_other_art_is_preserved(self):
        retired = self.base.parent / 'terminal-art'
        retired.mkdir(parents=True)
        (retired / 'venusaur.txt').write_text('obsolete')
        (retired / 'custom.txt').write_text('user-owned')
        (self.base.parent / 'bashrc-pokemon.sh').write_text('obsolete')
        result = self.install(self.gif)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((retired / 'venusaur.txt').exists())
        self.assertFalse((self.base.parent / 'bashrc-pokemon.sh').exists())
        self.assertEqual((retired / 'custom.txt').read_text(), 'user-owned')

    def test_bad_gif_does_not_change_startup(self):
        (self.home / '.bashrc').write_text('# keep exactly\n')
        result = self.install(self.home / 'missing.gif')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.home / '.bashrc').read_text(), '# keep exactly\n')
        self.assertFalse(self.base.exists())

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_live_prompt_typing_freeze_and_clear(self):
        self.check_live_prompt(clear_key=False)

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_ctrl_l_stops_animation(self):
        self.check_live_prompt(clear_key=True)

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_timer_expires_without_blocking_prompt(self):
        self.check_live_prompt(clear_key=False, expiry=True)

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_resize_freezes_before_coordinates_change(self):
        self.check_live_prompt(clear_key=False, resize=True)

    @unittest.skipUnless(shutil.which('fish'), 'requires Fish')
    def test_ctrl_c_freezes_and_cancels_input(self):
        self.check_live_prompt(clear_key=False, cancel_key=True)

    def check_live_prompt(self, clear_key, expiry=False, resize=False, cancel_key=False):
        import fcntl
        import pty
        import select
        import signal
        import struct
        import termios
        import time

        fish = shutil.which('fish')
        fetch = self.tools / 'fastfetch'
        payload = json.dumps([{'type': 'OS', 'result': {'prettyName': 'LivePromptTest'}}])
        fetch.write_text('#!/bin/sh\nprintf \'%s\\n\' ' + shlex.quote(payload) + '\n')
        fetch.chmod(0o755)
        self.env.update(TERM='xterm-256color', COLUMNS='140', LINES='40')
        self.env.pop('POKEMON_TERMINAL_SHOWN', None)
        self.env.pop('SSH_CONNECTION', None)
        result = self.install(self.gif, '--duration', '1.5' if expiry else '0')
        self.assertEqual(result.returncode, 0, result.stderr)
        hook = (
            'bind \\r execute; bind \\n execute; '
            'source "$XDG_CONFIG_HOME/fish/conf.d/pokemon-terminal-animated.fish"; '
            'printf "OLD_GREETING_ART\\n"; '
            'function _test_record --on-signal USR2; '
            'commandline > "$HOME/buffer"; '
            'printf "%s" "$_pokemon_active" > "$HOME/active"; '
            'printf "%s" "$_pokemon_cache" > "$HOME/cache"; end'
        )
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 140, 0, 0))

        def controlling_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        started = time.monotonic()
        process = subprocess.Popen(
            [fish, '--no-config', '--init-command', hook, '-i'],
            stdin=slave, stdout=slave, stderr=slave, env=self.env,
            preexec_fn=controlling_terminal)
        os.close(slave)
        output = bytearray()
        def consume(chunk):
            output.extend(chunk)

        def visible():
            # pyte predates Kitty keyboard negotiation. Those CSI-u sequences
            # must not be mistaken for its older cursor-restore command.
            screen = pyte.Screen(140, 40)
            stream = pyte.Stream(screen)
            text = output.decode('utf-8', errors='replace')
            text = re.sub(r'\x1b\[[=>?][0-9;:]*u', '', text)
            stream.feed(text)
            return screen

        def read_until(predicate):
            deadline = time.monotonic() + 7
            while time.monotonic() < deadline:
                if select.select([master], [], [], .05)[0]:
                    try:
                        consume(os.read(master, 65536))
                    except OSError:
                        break
                if predicate(bytes(output)):
                    return
            self.fail('Terminal did not reach expected state: ' + repr(bytes(output[-1500:])))

        try:
            read_until(lambda data: b'LivePromptTest' in data and b'> ' in data)
            self.assertLess(time.monotonic() - started, 5)
            # The greeting is gone from the visible display before the prompt.
            self.assertNotIn(b'OLD_GREETING_ART', output.split(b'\x1b[2J')[-1])
            self.assertNotIn(b'\x1b[?1049h', output)
            read_until(lambda data: data.count(b'\x1b8') >= 2)
            os.write(master, b'echo USER_TYPED_OK')
            saves = output.count(b'\x1b8')
            read_until(lambda data: data.count(b'\x1b8') >= saves + 2)
            screen = visible()
            self.assertTrue(any('echo USER_TYPED_OK' in line for line in screen.display))
            cursor_before = (screen.cursor.x, screen.cursor.y)
            restores = output.count(b'\x1b8')
            read_until(lambda data: data.count(b'\x1b8') >= restores + 2)
            screen = visible()
            self.assertEqual((screen.cursor.x, screen.cursor.y), cursor_before)
            self.assertTrue(any('echo USER_TYPED_OK' in line for line in screen.display))
            os.kill(process.pid, signal.SIGUSR2)
            read_until(lambda data: (self.home / 'buffer').exists())
            self.assertEqual((self.home / 'buffer').read_text().strip(), 'echo USER_TYPED_OK')
            if resize:
                fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 42, 145, 0, 0))
                os.kill(process.pid, signal.SIGWINCH)
            if expiry or resize:
                def inactive(data):
                    os.kill(process.pid, signal.SIGUSR2)
                    active = self.home / 'active'
                    return active.exists() and active.read_text() == '0'
                read_until(inactive)
                cache = Path((self.home / 'cache').read_text())
                self.assertFalse(cache.exists())
            if cancel_key:
                os.write(master, b'\x03')
                def cancelled(data):
                    os.kill(process.pid, signal.SIGUSR2)
                    active = self.home / 'active'
                    buffer = self.home / 'buffer'
                    return active.exists() and active.read_text() == '0' and not buffer.read_text().strip()
                read_until(cancelled)
                os.write(master, b'echo USER_TYPED_OK')
            if clear_key:
                os.write(master, b'\x0c')
                read_until(lambda data: data.count(b'\x1b[2J') >= 2 or b'\x1b[J' in data)
            os.write(master, b'\r')
            read_until(lambda data: b'\rUSER_TYPED_OK\r\n' in data)
            # Once a command executes, no more frame updates are allowed.
            frozen = output.count(b'\x1b7')
            deadline = time.monotonic() + .5
            while time.monotonic() < deadline:
                if select.select([master], [], [], .05)[0]:
                    consume(os.read(master, 65536))
            self.assertEqual(output.count(b'\x1b7'), frozen)
            self.assertNotIn(b'OLD_GREETING_ART', output.split(b'\x1b[2J')[-1])
            os.write(master, b'clear\r')
            read_until(lambda data: data.count(b'\x1b[H') >= 2)
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

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / 'custom config'
        self.env = dict(os.environ, HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.config), TERM='xterm-256color')

    def install(self, *args, success=True):
        result = subprocess.run(['bash', str(ROOT / 'install.sh'), *map(str, args)],
                                cwd='/tmp', env=self.env, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return result

    def test_image_install_repeat_failure_and_shell(self):
        image = self.home / 'venusaur image.png'
        Image.new('RGBA', (4, 4), (30, 180, 90, 255)).save(image)
        self.env['POKEMON_WIDTH'] = '4'
        (self.home / '.bashrc').write_text('# keep me\n')
        self.install(image)
        art = self.config / 'pokemon-terminal/terminal-art/venusaur.txt'
        original = art.read_bytes()
        self.assertIn(b'38;2;30;180;90', original)
        self.assertEqual(len(original.splitlines()), 2)
        self.install()
        self.assertEqual(art.read_bytes(), original)
        self.install(self.home / 'missing.png', success=False)
        self.assertEqual(art.read_bytes(), original)
        rc = (self.home / '.bashrc').read_text()
        self.assertIn('# keep me', rc)
        self.assertEqual(rc.count('&& source'), 1)
        result = subprocess.run(['bash', '-ic', 'echo READY'],
                                env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn(original.splitlines()[0], result.stdout)
        self.assertIn(b'READY', result.stdout)
        script = self.config / 'pokemon-terminal/bashrc-pokemon.sh'
        result = subprocess.run(['bash', '-c', 'source "$1"', '_', str(script)],
                                env=self.env, capture_output=True)
        self.assertEqual(result.stdout, b'')

    def test_legacy_hook_migration_and_default(self):
        legacy = '[ -f ~/.config/pokemon-terminal/bashrc-pokemon.sh ] && source ~/.config/pokemon-terminal/bashrc-pokemon.sh'
        (self.home / '.bashrc').write_text(legacy + '\n# retained\n')
        self.install()
        self.install()
        rc = (self.home / '.bashrc').read_text()
        self.assertNotIn(legacy, rc)
        self.assertIn('# retained', rc)
        self.assertEqual(rc.count('&& source'), 1)
        self.assertEqual((self.config / 'pokemon-terminal/terminal-art/venusaur.txt').read_bytes(),
                         (ROOT / 'terminal-art/venusaur.txt').read_bytes())

    def test_transparency_and_invalid_width(self):
        image = self.home / 'transparent.png'
        Image.new('RGBA', (2, 2), (0, 0, 0, 0)).save(image)
        result = subprocess.run(['python3', str(ROOT / 'image-to-art.py'), str(image),
                                 '--width', '2'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(b'38;2', result.stdout)
        self.env['POKEMON_WIDTH'] = '0'
        self.install(image, success=False)

    def test_wide_and_narrow_layout(self):
        tools = self.home / 'bin'
        tools.mkdir()
        fetch = tools / 'fastfetch'
        fetch.write_text('#!/bin/sh\nprintf "OS: TestOS\\nKernel: TestKernel\\n"\n')
        fetch.chmod(0o755)
        self.env['PATH'] = str(tools) + ':' + self.env['PATH']
        art = self.home / 'art.txt'
        art.write_text('ABC\nD\n')
        self.install(art)
        self.env['COLUMNS'] = '120'
        wide = subprocess.run(['bash', '-ic', ':'], env=self.env, capture_output=True)
        self.assertEqual(wide.returncode, 0)
        self.assertIn(b'ABC  OS: TestOS', wide.stdout)
        self.assertIn(b'D    Kernel: TestKernel', wide.stdout)
        self.env['COLUMNS'] = '30'
        narrow = subprocess.run(['bash', '-ic', ':'], env=self.env, capture_output=True)
        self.assertIn(b'ABC\nD\n\nOS: TestOS', narrow.stdout)

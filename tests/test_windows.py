"""Portable checks for Windows preparation, not Windows console compatibility."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class WindowsPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / 'shared').mkdir()
        shutil.copy(ROOT / 'windows/prepare.py', self.base)
        for name in ('render.py', 'dashboard.py', 'hardware.py'):
            shutil.copy(ROOT / 'animated' / name, self.base / 'shared')
        self.gif = self.base / 'Venusaur.gif'
        # Synthetic frame-count fixture; never distributed as Venusaur artwork.
        frames = [Image.new('RGBA', (20, 16), (i * 15, 80, 120, 255)) for i in range(15)]
        frames[0].save(self.gif, save_all=True, append_images=frames[1:], duration=125, loop=0)
        self.snapshot = self.base / 'snapshot.json'
        self.snapshot.write_text(json.dumps({
            'cpu': {'cpu': 'Windows fixture CPU', 'cores': {'online': 16}},
            'gpu': [{'name': 'Windows fixture GPU'}],
            'memory': {'total': 32 * 1024**3, 'used': 8 * 1024**3},
            'disk': [{'mountpoint': 'C:', 'mountFrom': 'C:',
                      'bytes': {'total': 1024**4, 'used': 1024**3}}],
            'os': {'prettyName': 'Windows 11'}, 'uptime': {'uptime': 7200000},
            'shell': {'name': 'Windows PowerShell', 'version': '5.1'},
        }), encoding='utf-8-sig')
        self.output = self.base / 'output.json'

    def run_prepare(self, *args, columns=140, lines=45):
        env = dict(os.environ, PYTHONPATH='')
        return subprocess.run([sys.executable, str(self.base / 'prepare.py'),
                               str(self.gif), str(self.snapshot), str(self.output),
                               str(columns), str(lines), *args], cwd=self.base,
                              env=env, capture_output=True, text=True, timeout=15)

    def test_fifteen_frames_offline_and_installed_imports(self):
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.output.read_text())
        self.assertEqual(len(data['frames']), 15)
        self.assertEqual(data['fps'], 8)
        self.assertNotEqual(data['frames'][0], data['frames'][1])
        initial = '\n'.join(data['initial'])
        self.assertIn('Windows fixture CPU', initial)
        self.assertIn('Windows 11', initial)
        self.assertIn('DATE & CALENDAR', initial)
        self.assertNotIn('NETWORK', initial)
        self.assertNotIn('Display', initial)
        self.assertIn('48;2;0;230;160', initial)
        self.assertLess(data['rows'], 45 - 6)
        # Sprite-only redraws have no full-line erase or dashboard text.
        for frame in data['frames']:
            self.assertNotIn('[2K', frame)
            self.assertNotIn('Windows', frame)

    def test_small_window_fails_without_partial_output(self):
        result = self.run_prepare(columns=80, lines=24)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_wrong_original_count_requires_explicit_override(self):
        first = Image.new('RGB', (8, 8), 'red')
        first.save(self.gif, save_all=True, append_images=[Image.new('RGB', (8, 8), 'blue')])
        result = self.run_prepare('--validate')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('15 frames', result.stderr)
        self.assertEqual(self.run_prepare('--validate', '--allow-other-pokemon').returncode, 0)

    def test_static_asset_rejected_even_with_override(self):
        Image.new('RGB', (8, 8), 'red').save(self.gif)
        self.assertNotEqual(self.run_prepare('--validate', '--allow-other-pokemon').returncode, 0)


if __name__ == '__main__':
    unittest.main()

import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'animated'))
spec = importlib.util.spec_from_file_location('animation', ROOT / 'animated/render.py')
animation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(animation)


class AnimationTests(unittest.TestCase):
    def test_gif_frames_and_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            gif = Path(directory) / 'idle.gif'
            first = Image.new('RGBA', (4, 4), 'red')
            second = Image.new('RGBA', (4, 4), 'blue')
            first.save(gif, save_all=True, append_images=[second],
                       duration=[120, 240], loop=0)
            frames, timings = animation.load_frames(gif, 4)
            self.assertEqual(len(frames), 2)
            self.assertNotEqual(frames[0], frames[1])
            self.assertEqual(timings, [.12, .24])

    def test_layout(self):
        rows = animation.layout(['AB', 'CD'], ['OS: Debian'], 80, 24, 0)
        self.assertTrue(any('AB      OS: Debian' in row for row in rows))
        stacked = animation.layout(['AB'], ['OS: Debian'], 20, 24, 0)
        self.assertEqual([animation.CSI.sub('', r) for r in stacked if r], ['AB', 'OS: Debian'])


    def test_information_is_centered_vertically(self):
        rows = animation.layout(['AB'] * 10, ['OS: Debian', 'Kernel: Linux'], 100, 12, 0)
        self.assertNotIn('OS:', rows[0])
        self.assertIn('OS: Debian', rows[4])
        self.assertIn('Kernel: Linux', rows[5])

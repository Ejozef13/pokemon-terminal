import importlib.util
import os
import json
import shlex
import sys
from pathlib import Path
import pty
import select
import struct
import subprocess
import tempfile
import termios
import fcntl
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'animated'))
spec = importlib.util.spec_from_file_location('animation', ROOT / 'animated/venusaur.py')
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
            frames, timings = animation.load_frames(gif, 4, False)
            self.assertEqual(len(frames), 2)
            self.assertNotEqual(frames[0], frames[1])
            self.assertEqual(timings, [.12, .24])
            ascii_frames, _ = animation.load_frames(gif, 4, True)
            for frame in ascii_frames:
                self.assertTrue(animation.CSI.sub('', ''.join(frame)).isascii())

    def test_layout(self):
        rows = animation.layout(['AB', 'CD'], ['OS: Debian'], 80, 24, 0)
        self.assertTrue(any('AB      OS: Debian' in row for row in rows))
        stacked = animation.layout(['AB'], ['OS: Debian'], 20, 24, 0)
        self.assertEqual([animation.CSI.sub('', r) for r in stacked if r], ['AB', 'OS: Debian'])

    def test_real_terminal_playback_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            fetch = Path(directory) / 'fastfetch'
            payload = json.dumps([{'type': 'OS', 'result': {'prettyName': 'AnimationTest'}}])
            fetch.write_text('#!/bin/sh\nprintf \'%s\\n\' ' + shlex.quote(payload) + '\n')
            art = Path(directory) / 'art.txt'
            art.write_text('ABC\nDEF\n')
            fetch.chmod(0o755)
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            self.addCleanup(os.close, slave)
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 50, 160, 0, 0))
            env = dict(os.environ, TERM='xterm-256color',
                       PATH=directory + ':' + os.environ['PATH'])
            process = subprocess.Popen(
                ['python3', str(ROOT / 'animated/venusaur.py'), str(art), '--duration', '.35'],
                stdout=slave, stderr=slave, env=env)
            output = bytearray()
            while process.poll() is None:
                if select.select([master], [], [], 1)[0]:
                    output.extend(os.read(master, 65536))
            while select.select([master], [], [], .05)[0]:
                output.extend(os.read(master, 65536))
            self.assertEqual(process.wait(timeout=2), 0)
            self.assertIn(b'AnimationTest', output)
            self.assertIn(b'\x1b[?1049h', output)
            self.assertGreaterEqual(output.count(b'\x1b[H\x1b[2J'), 2)
            self.assertTrue(output.endswith(b'\x1b[0m\x1b[?25h\x1b[?1049l'))

    def test_information_is_centered_vertically(self):
        rows = animation.layout(['AB'] * 10, ['OS: Debian', 'Kernel: Linux'], 100, 12, 0)
        self.assertNotIn('OS:', rows[0])
        self.assertIn('OS: Debian', rows[4])
        self.assertIn('Kernel: Linux', rows[5])

    def test_skip_leaves_final_still_and_restores_cursor(self):
        import signal
        import time
        with tempfile.TemporaryDirectory() as directory:
            art = Path(directory) / 'art.txt'
            art.write_text('VENUSAUR_TEST\n')
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            self.addCleanup(os.close, slave)
            process = subprocess.Popen(
                ['python3', str(ROOT / 'animated/venusaur.py'), str(art),
                 '--duration', '30', '--keep-frame'],
                stdout=slave, stderr=slave, env=dict(os.environ, TERM='xterm-256color'))
            self.addCleanup(lambda: process.poll() is None and process.kill())
            output = bytearray()
            deadline = time.monotonic() + 5
            while b'VENUSAUR_TEST' not in output and time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    output.extend(os.read(master, 65536))
            self.assertIn(b'VENUSAUR_TEST', output)
            process.send_signal(signal.SIGINT)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    output.extend(os.read(master, 65536))
                if process.poll() is not None:
                    break
            while select.select([master], [], [], .05)[0]:
                output.extend(os.read(master, 65536))
            self.assertEqual(process.wait(timeout=2), 0)
            self.assertIn(b'VENUSAUR_TEST', output.split(b'\x1b[?1049l')[-1])
            self.assertIn(b'\x1b[?25h', output)

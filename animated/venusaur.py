#!/usr/bin/env python3
"""Separate foreground Venusaur animation; never modifies shell configuration."""
import argparse
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
ROOT = Path(__file__).resolve().parents[1]


def system_info():
    for name, args in [('fastfetch', ['--logo', 'none']),
                       ('neofetch', ['--stdout'])]:
        executable = shutil.which(name)
        if executable:
            try:
                result = subprocess.run([executable, *args], capture_output=True,
                                        text=True, timeout=5, check=True)
                # Keep the display inside our drawing area.
                return CSI.sub('', result.stdout).splitlines()
            except (subprocess.SubprocessError, OSError):
                continue
    return ['Venusaur Terminal', 'Install fastfetch for system information.']


def render(image, ascii_only):
    pixels = image.load()
    rows = []
    ramp = ' .:-=+*#%@'
    for y in range(0, image.height, 2):
        row = []
        for x in range(image.width):
            top = pixels[x, y]
            bottom = pixels[x, y + 1] if y + 1 < image.height else (0, 0, 0, 0)
            a, b = top[3] >= 128, bottom[3] >= 128
            if ascii_only:
                color = top if a else bottom
                light = round((.2126 * color[0] + .7152 * color[1] +
                               .0722 * color[2]) * 9 / 255)
                row.append(ramp[light] if a or b else ' ')
                continue
            codes = ['0']
            fg = top[:3] if a else bottom[:3] if b else None
            if fg:
                codes.append('38;2;' + ';'.join(map(str, fg)))
            if a and b:
                codes.append('48;2;' + ';'.join(map(str, bottom[:3])))
            row.append('\033[' + ';'.join(codes) + 'm' +
                       ('▀' if a else '▄' if b else ' '))
        rows.append(''.join(row) + '\033[0m')
    return rows


def load_frames(path, width, ascii_only):
    if path is None or path.suffix.lower() == '.txt':
        if ascii_only:
            raise ValueError('--ascii requires an image file')
        text = (path or ROOT / 'terminal-art/venusaur.txt').read_text()
        # Bundled art includes cursor control; retain only SGR color sequences.
        text = CSI.sub(lambda m: m[0] if m[0].endswith('m') else '', text)
        return [text.splitlines()], [.125]
    from PIL import Image, ImageOps, ImageSequence
    with Image.open(path) as source:
        if getattr(source, 'n_frames', 1) > 300:
            raise ValueError('Use an animation with at most 300 frames')
        images, durations = [], []
        for frame in ImageSequence.Iterator(source):
            rgba = ImageOps.exif_transpose(frame).convert('RGBA')
            height = max(1, round(rgba.height * width / rgba.width))
            if height > 400:
                raise ValueError('Image is too tall; choose a smaller width')
            rgba = rgba.resize((width, height), Image.Resampling.NEAREST)
            images.append(render(rgba, ascii_only))
            durations.append(max(.04, min(2., frame.info.get('duration', 125) / 1000)))
        return images, durations


def layout(art, info, columns, height, offset):
    width = max((len(CSI.sub('', row)) for row in art), default=0)
    if width > columns - 1:
        art = ['Art is too wide. Use --width with a smaller image.']
        width = len(art[0])
    left = [''] * offset + art
    if columns >= width + 36:
        rows = []
        for i in range(max(len(left), len(info))):
            line = left[i] if i < len(left) else ''
            plain_width = len(CSI.sub('', line))
            right = info[i][:max(0, columns - width - 3)] if i < len(info) else ''
            rows.append(line + ' ' * (width - plain_width + 2) + right)
    else:
        rows = left + [''] + [line[:columns - 1] for line in info]
    return rows[:max(0, height - 2)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', type=Path,
                        help='GIF, PNG, JPEG, or terminal art; defaults to bundled art')
    parser.add_argument('--width', type=int, default=40)
    parser.add_argument('--ascii', action='store_true', help='Plain ASCII image rendering')
    parser.add_argument('--fps', type=float, default=8,
                        help='Maximum redraw rate; GIF timing is preserved when slower')
    parser.add_argument('--duration', type=float, default=0,
                        help='Exit after this many seconds; zero loops until Ctrl-C')
    args = parser.parse_args()
    if not 1 <= args.width <= 160 or not math.isfinite(args.fps) or not 1 <= args.fps <= 30:
        parser.error('width must be 1–160 and fps must be 1–30')
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration must be finite and nonnegative')
    if not sys.stdout.isatty() or os.environ.get('TERM') == 'dumb':
        parser.error('Run in an interactive terminal or tmux pane')
    try:
        frames, timings = load_frames(args.image, args.width, args.ascii)
        info = system_info()
    except (OSError, ValueError, ImportError) as error:
        parser.exit(1, f'Cannot load animation: {error}. Image input requires Pillow.\n')
    # Resize the image to the current pane with --width before launch. Rendering
    # adapts layout to subsequent resizes without reconverting frames.
    started, index = time.monotonic(), 0
    previous_handler = signal.getsignal(signal.SIGTERM)

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        sys.stdout.write('\033[?1049h\033[?25l')
        while True:
            now = time.monotonic()
            if args.duration and now - started >= args.duration:
                break
            columns, height = shutil.get_terminal_size()
            # Still images get an explicit gentle bob; GIFs use their own poses.
            offset = int((now - started) % 1.4 >= .7) if len(frames) == 1 else 0
            rows = layout(frames[index], info, columns, height, offset)
            sys.stdout.write('\033[H\033[2J' + '\r\n'.join(rows) +
                             '\r\n\033[0mCtrl-C to return to your shell')
            sys.stdout.flush()
            delay = max(1 / args.fps, timings[index])
            if args.duration:
                delay = min(delay, max(0, args.duration - (time.monotonic() - started)))
            time.sleep(delay)
            index = (index + 1) % len(frames)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\033[0m\033[?25h\033[?1049l')
        sys.stdout.flush()
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == '__main__':
    main()

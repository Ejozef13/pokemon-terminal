#!/usr/bin/env python3
"""Venusaur animation with centered system information."""
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
        previous = None
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
            colors = tuple(codes)
            if colors != previous:
                row.append('\033[' + ';'.join(codes) + 'm')
                previous = colors
            row.append('▀' if a else '▄' if b else ' ')
        rows.append(''.join(row) + ('' if ascii_only else '\033[0m'))
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


def layout(art, info, columns, height, offset, gap=6):
    width = max((len(CSI.sub('', row)) for row in art), default=0)
    if width > columns - 1:
        art = ['Art too wide; reduce --width.'[:max(0, columns - 1)]]
        width = len(art[0])
    left = [''] * offset + art
    if columns >= width + gap + 30:
        count = max(len(left), len(info))
        # Keep info vertically centered against the whole sprite.
        info_top = max(0, (count - len(info)) // 2)
        info_width = min(max((len(row) for row in info), default=0),
                         max(0, columns - width - gap - 1))
        margin = max(0, (columns - 1 - width - gap - info_width) // 2)
        rows = []
        for i in range(count):
            line = left[i] if i < len(left) else ''
            plain_width = len(CSI.sub('', line))
            j = i - info_top
            right = info[j][:max(0, columns - width - gap - 1)] if 0 <= j < len(info) else ''
            rows.append(' ' * margin + line + ' ' * (width - plain_width + gap) + right)
    else:
        rows = left + [''] + [line[:max(0, columns - 1)] for line in info]
    # Center the display vertically when the pane has room.
    padding = max(0, (height - 2 - len(rows)) // 2)
    return ([''] * padding + rows)[:max(0, height - 2)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', type=Path,
                        help='GIF, PNG, JPEG, or terminal art; defaults to bundled art')
    parser.add_argument('--width', type=int, default=40)
    parser.add_argument('--gap', type=int, default=6, help='Columns between Venusaur and system info')
    parser.add_argument('--quiet', action='store_true', help='Hide the exit hint in a startup pane')
    parser.add_argument('--ascii', action='store_true', help='Plain ASCII image rendering')
    parser.add_argument('--fps', type=float, default=8,
                        help='Maximum redraw rate; GIF timing is preserved when slower')
    parser.add_argument('--duration', type=float, default=0,
                        help='Exit after this many seconds; zero loops until Ctrl-C')
    args = parser.parse_args()
    if not 1 <= args.width <= 160 or not math.isfinite(args.fps) or not 1 <= args.fps <= 30:
        parser.error('width must be 1–160 and fps must be 1–30')
    if not 1 <= args.gap <= 40:
        parser.error('gap must be 1–40')
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration must be finite and nonnegative')
    if not sys.stdout.isatty() or os.environ.get('TERM') == 'dumb':
        parser.error('Run in an interactive terminal or tmux pane')
    try:
        frames, timings = load_frames(args.image, args.width, args.ascii)
        info = system_info()
    except ImportError:
        parser.exit(1, 'Image animation requires Pillow. Install requirements-image.txt.\n')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot load animation: {error}\n')
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
            rows = layout(frames[index], info, columns, height, offset, args.gap)
            sys.stdout.write('\033[H\033[2J' + '\r\n'.join(rows) +
                             ('' if args.quiet else '\r\n\033[0mCtrl-C to return to your shell'))
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

#!/usr/bin/env python3
"""Venusaur animation with centered system information."""
import argparse
import math
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import time

CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
ROOT = Path(__file__).resolve().parents[1]

from dashboard import clip, system_info, visible_width


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


def layout(art, info, columns, height, offset, gap=6, center_vertical=True):
    width = max((visible_width(row) for row in art), default=0)
    if width > columns - 1:
        art = ['Art too wide; reduce --width.'[:max(0, columns - 1)]]
        width = len(art[0])
    left = [''] * offset + art
    if columns >= width + gap + 30:
        count = max(len(left), len(info))
        # Keep info vertically centered against the whole sprite.
        info_top = max(0, (count - len(info)) // 2)
        info_width = min(max((visible_width(row) for row in info), default=0),
                         max(0, columns - width - gap - 1))
        margin = max(0, (columns - 1 - width - gap - info_width) // 2)
        art_top = max(0, (count - len(left)) // 2)
        rows = []
        for i in range(count):
            art_index = i - art_top
            line = left[art_index] if 0 <= art_index < len(left) else ''
            plain_width = visible_width(line)
            j = i - info_top
            right = clip(info[j], max(0, columns - width - gap - 1)) if 0 <= j < len(info) else ''
            rows.append(' ' * margin + line + ' ' * (width - plain_width + gap) + right)
    else:
        rows = left + [''] + [clip(line, max(0, columns - 1)) for line in info]
    # The final still is compact so the prompt sits directly below it.
    padding = max(0, (height - 2 - len(rows)) // 2) if center_vertical else 0
    return ([''] * padding + rows)[:max(0, height - 2)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', type=Path,
                        help='GIF, PNG, JPEG, or terminal art; defaults to bundled art')
    parser.add_argument('--width', type=int, default=40)
    parser.add_argument('--gap', type=int, default=6, help='Columns between Venusaur and system info')
    parser.add_argument('--quiet', action='store_true', help='Hide the skip hint')
    parser.add_argument('--ascii', action='store_true', help='Plain ASCII image rendering')
    parser.add_argument('--fps', type=float, default=8,
                        help='Maximum redraw rate; GIF timing is preserved when slower')
    parser.add_argument('--duration', type=float, default=30,
                        help='Animation seconds (default 30); zero loops until Ctrl-C')
    parser.add_argument('--keep-frame', action='store_true',
                        help='Leave the last frame and system info above the shell prompt')
    args = parser.parse_args(argv)
    if not 1 <= args.width <= 160 or not math.isfinite(args.fps) or not 1 <= args.fps <= 30:
        parser.error('width must be 1–160 and fps must be 1–30')
    if not 1 <= args.gap <= 40:
        parser.error('gap must be 1–40')
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error('duration must be finite and nonnegative')
    if not sys.stdout.isatty() or os.environ.get('TERM') == 'dumb':
        parser.error('Run in an interactive terminal')
    try:
        frames, timings = load_frames(args.image, args.width, args.ascii)
        info = system_info()
    except ImportError:
        parser.exit(1, 'Image animation requires Pillow. Install requirements-image.txt.\n')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot load animation: {error}\n')
    # Frames are converted once; layout adapts to terminal resizes.
    started, index, last_index, last_offset = time.monotonic(), 0, 0, 0
    terminated = False
    previous_handler = signal.getsignal(signal.SIGTERM)

    def stop(signum, frame):
        nonlocal terminated
        terminated = True
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
                             ('' if args.quiet else '\r\n\033[0mCtrl-C to skip animation'))
            sys.stdout.flush()
            last_index, last_offset = index, offset
            delay = max(1 / args.fps, timings[index])
            if args.duration:
                delay = min(delay, max(0, args.duration - (time.monotonic() - started)))
            time.sleep(delay)
            index = (index + 1) % len(frames)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            sys.stdout.write('\033[0m\033[?25h\033[?1049l')
            if args.keep_frame and not terminated:
                columns, height = shutil.get_terminal_size()
                rows = layout(frames[last_index], info, columns, height, last_offset,
                              args.gap, center_vertical=False)
                sys.stdout.write('\r\n'.join(rows) + '\033[0m\r\n\r\n')
            sys.stdout.flush()
        finally:
            signal.signal(signal.SIGTERM, previous_handler)


if __name__ == '__main__':
    main()

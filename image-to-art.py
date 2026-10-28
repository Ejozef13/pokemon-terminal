#!/usr/bin/env python3
"""Convert an image once to cached ANSI half-block art."""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--width', type=int, default=48)
    args = parser.parse_args()
    if not 1 <= args.width <= 200:
        parser.error('--width must be between 1 and 200')
    try:
        from PIL import Image, ImageOps
    except ImportError:
        parser.exit(1, 'Image conversion requires Pillow: python3 -m pip install Pillow\n')
    try:
        with Image.open(args.image) as source:
            image = ImageOps.exif_transpose(source).convert('RGBA')
            bounds = image.getbbox()
            if bounds:
                image = image.crop(bounds)
            height = max(1, round(image.height * args.width / image.width))
            image = image.resize((args.width, height), Image.Resampling.LANCZOS)
            pixels = image.load()
            for y in range(0, height, 2):
                row = []
                previous = None
                for x in range(args.width):
                    top = pixels[x, y]
                    bottom = pixels[x, y + 1] if y + 1 < height else (0, 0, 0, 0)
                    top_on, bottom_on = top[3] >= 128, bottom[3] >= 128
                    fg = top[:3] if top_on else bottom[:3] if bottom_on else None
                    bg = bottom[:3] if top_on and bottom_on else None
                    colors = (fg, bg)
                    if colors != previous:
                        codes = ['0']
                        if fg is not None:
                            codes.append('38;2;' + ';'.join(map(str, fg)))
                        if bg is not None:
                            codes.append('48;2;' + ';'.join(map(str, bg)))
                        row.append('\033[' + ';'.join(codes) + 'm')
                        previous = colors
                    row.append('▀' if top_on else '▄' if bottom_on else ' ')
                sys.stdout.write(''.join(row) + '\033[0m\n')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot convert image: {error}\n')


if __name__ == '__main__':
    main()

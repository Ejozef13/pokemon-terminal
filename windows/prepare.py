"""Offline Windows frame preparation; Linux sources are imported, never changed."""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'shared'))
from dashboard import dashboard, visible_width
from render import layout, load_frames


def prepare(gif, snapshot, columns, lines, width=48):
    from PIL import Image
    if columns < 100 or lines < 38:
        raise ValueError('Use a Windows Terminal window at least 100 columns by 38 rows')
    info = dashboard(snapshot, min(76, columns - 33))
    available = lines - 7
    if len(info) > available:
        raise ValueError('Increase terminal height to fit the full dashboard and prompt')
    width = min(width, columns - min(76, columns - 33) - 8 - 1)
    with Image.open(gif) as image:
        width = min(width, math.floor(available * 2 * image.width / image.height))
    frames, _ = load_frames(gif, max(1, width))
    initial = layout(frames[0], info, columns, available + 2, 0, 8, False)
    sprite_width = max(visible_width(row) for row in frames[0])
    info_width = min(max(map(visible_width, info)), columns - sprite_width - 9)
    margin = max(0, (columns - 1 - sprite_width - 8 - info_width) // 2)
    top = max(0, (max(len(frames[0]), len(info)) - len(frames[0])) // 2)
    payloads = [''.join(f'\033[{top + i + 1};{margin + 1}H' + row
                        for i, row in enumerate(frame)) + '\033[0m'
                for frame in frames]
    return {'initial': initial, 'frames': payloads, 'rows': len(initial), 'fps': 8}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gif', type=Path)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('columns', type=int)
    parser.add_argument('lines', type=int)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--allow-other-pokemon', action='store_true')
    args = parser.parse_args()
    from PIL import Image
    with Image.open(args.gif) as image:
        count = getattr(image, 'n_frames', 1)
        if image.format != 'GIF' or not 2 <= count <= 300:
            raise ValueError('Supply an animated GIF with 2 to 300 frames')
        if not args.allow_other_pokemon and count != 15:
            raise ValueError(f'Original Venusaur must have 15 frames; received {count}. '
                             'Use -AllowOtherPokemon for a different sprite.')
        for index in range(count):
            image.seek(index)
            image.convert('RGBA').load()
    if not args.validate:
        data = json.loads(args.snapshot.read_text(encoding='utf-8-sig'))
        args.output.write_text(json.dumps(prepare(args.gif, data, args.columns, args.lines)),
                               encoding='utf-8')


if __name__ == '__main__':
    main()

"""GIF-to-terminal frame rendering and layout for the Fish startup."""
import re

CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

from dashboard import clip, visible_width


def render(image):
    pixels = image.load()
    rows = []
    for y in range(0, image.height, 2):
        row = []
        previous = None
        for x in range(image.width):
            top = pixels[x, y]
            bottom = pixels[x, y + 1] if y + 1 < image.height else (0, 0, 0, 0)
            a, b = top[3] >= 128, bottom[3] >= 128
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
        rows.append(''.join(row) + '\033[0m')
    return rows


def load_frames(path, width):
    from PIL import Image, ImageOps, ImageSequence
    with Image.open(path) as source:
        if getattr(source, 'n_frames', 1) < 2:
            raise ValueError('Supply a multi-frame animated GIF')
        if getattr(source, 'n_frames', 1) > 300:
            raise ValueError('Use an animation with at most 300 frames')
        images, durations = [], []
        for frame in ImageSequence.Iterator(source):
            rgba = ImageOps.exif_transpose(frame).convert('RGBA')
            height = max(1, round(rgba.height * width / rgba.width))
            if height > 400:
                raise ValueError('Image is too tall; choose a smaller width')
            rgba = rgba.resize((width, height), Image.Resampling.NEAREST)
            images.append(render(rgba))
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

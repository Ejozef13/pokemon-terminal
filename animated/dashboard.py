"""CachyOS-colored local dashboard, built from explicitly selected Fastfetch modules."""
import calendar
from datetime import datetime
import json
import math
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata

CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
RESET = '\033[0m'
TEAL, CYAN, BLUE, PURPLE = '#00cbb8', '#00cfff', '#5b9dff', '#a785ff'
WHITE, GREEN = '#d8e8ee', '#9bd65d'
MODULES = ('CPU', 'GPU', 'Memory', 'Disk', 'Display', 'Host', 'OS', 'Kernel',
           'Uptime', 'Packages', 'DE', 'WM', 'Shell', 'Terminal')
ALLOWED_MODULES = {name.upper() for name in MODULES}


def color(text, hex_color):
    rgb = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    prefix = '\033[38;2;' + ';'.join(map(str, rgb)) + 'm'
    return prefix + str(text).replace(RESET, RESET + prefix) + RESET


def visible_width(text):
    return sum(0 if unicodedata.combining(c) or unicodedata.category(c).startswith('C')
               else 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
               for c in CSI.sub('', text))


def clip(text, width):
    """Clip colored text without breaking escape sequences or leaving styles active."""
    output, used, index = [], 0, 0
    while index < len(text):
        escape = CSI.match(text, index)
        if escape:
            output.append(escape[0])
            index = escape.end()
            continue
        character = text[index]
        size = visible_width(character)
        if used + size > max(0, width):
            break
        output.append(character)
        used += size
        index += 1
    return ''.join(output) + RESET


def clean(value):
    # Machine strings must never inject terminal control sequences.
    return ''.join(c if not unicodedata.category(c).startswith('C') else ' '
                   for c in str(value))


def number(value, default=0):
    return value if isinstance(value, (float, int)) and math.isfinite(value) else default


def local_fallback():
    uname = platform.uname()
    distro = {}
    try:
        distro = platform.freedesktop_os_release()
    except OSError:
        pass
    result = {
        'os': {'prettyName': distro.get('PRETTY_NAME', uname.system)},
        'kernel': {'name': uname.system, 'release': uname.release,
                   'architecture': uname.machine},
        'host': {'name': uname.node},
        'shell': {'prettyName': Path(os.environ.get('SHELL', '')).name or 'Unavailable'},
        'terminal': {'prettyName': os.environ.get('TERM_PROGRAM', 'Unavailable')},
    }
    try:
        result['uptime'] = {'uptime': float(Path('/proc/uptime').read_text().split()[0]) * 1000}
        memory = {line.split(':')[0]: int(line.split()[1]) * 1024
                  for line in Path('/proc/meminfo').read_text().splitlines()}
        result['memory'] = {'total': memory['MemTotal'],
                            'used': memory['MemTotal'] - memory['MemAvailable']}
    except (OSError, ValueError, KeyError):
        pass
    try:
        disk = shutil.disk_usage('/')
        result['disk'] = [{'mountpoint': '/', 'bytes': {'total': disk.total, 'used': disk.used}}]
    except OSError:
        pass
    return result


def shell_context(results):
    # Fastfetch is launched through Python; preserve the actual interactive
    # Fish version rather than accidentally reporting the wrapper process.
    if os.environ.get('POKEMON_SHELL_VERSION'):
        results['shell'] = {'prettyName': 'fish',
                            'version': clean(os.environ['POKEMON_SHELL_VERSION'])}
    konsole = os.environ.get('KONSOLE_VERSION', '')
    if konsole.isdecimal() and 10000 <= int(konsole) < 1000000:
        version = int(konsole)
        results['terminal'] = {'prettyName': 'Konsole',
                               'version': f'{version // 10000}.{version // 100 % 100:02d}.{version % 100}'}
    return results


def collect():
    executable = shutil.which('fastfetch')
    if executable:
        try:
            response = subprocess.run(
                [executable, '--config', 'none', '--structure', ':'.join(MODULES),
                 '--cpu-temp', 'true', '--gpu-temp', 'true', '--detect-version', 'true', '--format', 'json'],
                capture_output=True, text=True, timeout=5, check=True)
            entries = json.loads(response.stdout)
            if not isinstance(entries, list):
                raise ValueError('Expected a module list')
            results = {entry['type'].lower(): entry['result'] for entry in entries
                       if isinstance(entry, dict) and 'result' in entry and 'type' in entry
                       and entry['type'].upper() in ALLOWED_MODULES}
            if results:
                return shell_context(results)
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            pass
    return shell_context(local_fallback())


def temperature(value):
    return color(f"{value:.1f}°C", GREEN) if number(value, -1) > 0 else ''


def usage(data):
    total, used = number(data.get('total')), number(data.get('used'))
    if total <= 0:
        return 'Unavailable'
    ratio = max(0, min(1, used / total))
    unit, scale = ('TiB', 1024 ** 4) if total >= 1024 ** 4 else ('GiB', 1024 ** 3)
    bar = color('■' * round(ratio * 10), GREEN) + color('·' * (10 - round(ratio * 10)), BLUE)
    return f'[{bar}] {used / scale:.2f} / {total / scale:.2f} {unit} ({ratio:.0%})'


def named(data):
    if not isinstance(data, dict):
        return 'Unavailable'
    return ' '.join(clean(data.get(key, '')) for key in ('prettyName', 'version')).strip() or clean(data.get('name', 'Unavailable'))


def sections(data, now):
    cpu = data.get('cpu', {})
    cpu_text = clean(cpu.get('cpu', 'Unavailable'))
    cores = number(cpu.get('cores', {}).get('online'))
    if cores:
        cpu_text += f' ({cores})'
    frequency = cpu.get('frequency', {})
    mhz = number(frequency.get('max')) or number(frequency.get('base'))
    if mhz:
        cpu_text += f' @ {mhz / 1000:.2f} GHz'
    cpu_text += (' - ' + temperature(cpu['temperature'])) if temperature(cpu.get('temperature')) else ''
    hardware = [('CPU', cpu_text)]
    for gpu in data.get('gpu') or [{}]:
        text = clean(gpu.get('name', 'Unavailable'))
        temp = temperature(gpu.get('temperature'))
        if temp:
            text += f' ({temp})'
        if gpu.get('type') and gpu['type'] != 'Unknown':
            text += ' [' + clean(gpu['type']) + ']'
        hardware.append(('GPU', text))
    hardware.append(('RAM', usage(data.get('memory', {}))))
    for disk in data.get('disk') or [{}]:
        hardware.append(('ROM ' + clean(disk.get('mountpoint', '')),
                         usage(disk.get('bytes', {}))))
    for display in data.get('display') or [{}]:
        if not display.get('width'):
            hardware.append(('Display', 'Unavailable'))
            continue
        text = f"{display['width']}x{display.get('height', '?')}"
        scale = number(display.get('scaleFactor'))
        if scale and scale != 1:
            text += f' @ {scale:g}x'
        rate = number(display.get('refreshRate'))
        w, h = number(display.get('physicalWidth')), number(display.get('physicalHeight'))
        if w and h:
            text += f' in {math.hypot(w, h) / 25.4:.1f}"'
        if rate:
            text += f', {rate:g} Hz'
        if display.get('type'):
            text += ' [' + clean(display['type']) + ']'
        hardware.append(('Display', text))

    host = data.get('host', {})
    kernel = data.get('kernel', {})
    architecture = clean(kernel.get('architecture', ''))
    distro = clean(data.get('os', {}).get('prettyName') or data.get('os', {}).get('name', 'Unavailable'))
    if architecture:
        distro += ' ' + architecture
    uptime = number(data.get('uptime', {}).get('uptime')) / 1000
    hours, minutes = int(uptime // 3600), int(uptime % 3600 // 60)
    uptime_text = f'{hours // 24} days, {hours % 24} hours, {minutes} mins' if hours >= 24 else f'{hours} hours, {minutes} mins'
    packages = data.get('packages', {})
    managers = [name for name in ('pacman', 'dpkg', 'rpm', 'flatpakSystem', 'flatpakUser', 'nixSystem', 'brew')
                if number(packages.get(name)) > 0]
    package_text = str(packages.get('all', 'Unavailable'))
    if managers:
        package_text += ' (' + ', '.join(managers) + ')'
    wm = data.get('wm', {})
    wm_text = named(wm)
    if wm.get('protocolName'):
        wm_text += ' (' + clean(wm['protocolName']) + ')'
    system = [
        ('Host', ' '.join(clean(host.get(k, '')) for k in ('name', 'version')).strip() or 'Unavailable'),
        ('Distribution', distro),
        ('Kernel', ' '.join(clean(kernel.get(k, '')) for k in ('name', 'release')).strip() or 'Unavailable'),
        ('Uptime', uptime_text if 'uptime' in data else 'Unavailable'),
        ('Packages', package_text), ('Desktop', named(data.get('de'))),
        ('Window-Manager', wm_text), ('Shell', named(data.get('shell'))),
        ('Terminal', named(data.get('terminal'))),
    ]
    date_rows = [('Date', now.strftime('%a, %d %b %Y - %H:%M') + f' (W{now.isocalendar().week:02d})'),
                 ('Days', color('Mo Tu We Th Fr Sa Su', CYAN))]
    for index, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(now.year, now.month), 1):
        days = []
        for day in week:
            value = f'{day:2}' if day else '  '
            if day == now.day:
                value = '\033[7m' + color(value, CYAN)
            days.append(value)
        date_rows.append((f'{index}. Week', ' '.join(days)))
    return [('HARDWARE', TEAL, hardware), ('SYSTEM & SOFTWARE', BLUE, system),
            ('DATE & CALENDAR', PURPLE, date_rows)]


def dashboard(data, width=76, now=None):
    now = now or datetime.now().astimezone()
    width = max(32, width)
    inside = width - 2
    label_width = 14
    value_width = inside - label_width - 4
    rows = []
    for index, (title, accent, entries) in enumerate(sections(data, now)):
        middle = ' ' + title + ' '
        remaining = inside - len(middle)
        border = ('┌' if index == 0 else '├') + '─' * (remaining // 2) + middle + '─' * (remaining - remaining // 2) + ('┐' if index == 0 else '┤')
        rows.append(color(border, accent))
        for label, value in entries:
            label = clip(clean(label), label_width)
            value = clip(str(value), value_width)
            line = (color('│ ', accent) + color(label, accent)
                    + ' ' * (label_width - visible_width(label)) + color(' → ', CYAN)
                    + color(value, WHITE) + ' ' * (value_width - visible_width(value))
                    + color('│', accent))
            rows.append(line)
    rows.append(color('└' + '─' * inside + '┘', TEAL))
    rows.append(' ' + ' '.join(color('●', shade) for shade in
                              (WHITE, TEAL, CYAN, BLUE, PURPLE, GREEN, '#f3c969', '#ed6a73')))
    return rows


def system_info(width=76):
    return dashboard(collect(), width)

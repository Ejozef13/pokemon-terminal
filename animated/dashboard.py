"""CachyOS-colored local dashboard, built from explicitly selected Fastfetch modules."""
import calendar
from concurrent.futures import ThreadPoolExecutor
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
import hardware

CSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
RESET = '\033[0m'
CACHY_GREEN, BLUE = '#00e6a0', '#5b9dff'
TEAL = GREEN = WHITE = CACHY_GREEN
CYAN = BLUE
MODULES = ('CPU', 'GPU', 'Memory', 'Disk', 'Display', 'Host', 'OS', 'Kernel',
           'Uptime', 'Packages', 'DE', 'WM', 'Shell', 'Terminal')
ALLOWED_MODULES = {name.upper() for name in MODULES}


def color(text, hex_color):
    rgb = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    prefix = '\033[38;2;' + ';'.join(map(str, rgb)) + 'm'
    return prefix + str(text).replace(RESET, RESET + prefix) + RESET


def terminal_color(text, code):
    """Use the terminal palette, so Konsole's selected scheme defines the RGB."""
    prefix = f'\033[{code}m'
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


def fastfetch_probe(executable, thermal=False):
    modules = ('CPU', 'GPU') if thermal else MODULES
    args = [executable, '--config', 'none', '--structure', ':'.join(modules),
            '--format', 'json']
    if thermal:
        args += ['--cpu-temp', 'true', '--gpu-temp', 'true']
    try:
        response = subprocess.run(args, capture_output=True, text=True,
                                  timeout=2 if thermal else 4, check=True)
        entries = json.loads(response.stdout)
        if not isinstance(entries, list):
            raise ValueError('Expected a module list')
        values, errors = {}, []
        for entry in entries:
            if not isinstance(entry, dict) or str(entry.get('type', '')).upper() not in ALLOWED_MODULES:
                continue
            name = entry['type'].lower()
            expected = list if name in ('gpu', 'disk', 'display') else dict
            if 'result' in entry and isinstance(entry['result'], expected):
                value = entry['result']
                values[name] = [item for item in value if isinstance(item, dict)] if expected is list else value
            elif entry.get('error'):
                errors.append(name + ': ' + clean(entry['error']))
            else:
                errors.append(name + ': unsupported result format')
        return values, errors
    except subprocess.CalledProcessError as error:
        return {}, ['Fastfetch rejected ' + ('temperature options: ' if thermal else 'base query: ')
                    + clean((error.stderr or str(error)).strip())[:300]]
    except subprocess.TimeoutExpired:
        return {}, ['Fastfetch ' + ('temperature' if thermal else 'base') + ' query timed out']
    except (OSError, ValueError, KeyError) as error:
        return {}, ['Fastfetch: ' + clean(error)]


def collect():
    # Optional thermal/version options must never discard otherwise valid data.
    data, errors = local_fallback(), []
    executable = shutil.which('fastfetch')
    primary, thermal = {}, {}
    if executable:
        with ThreadPoolExecutor(max_workers=2) as pool:
            base_future = pool.submit(fastfetch_probe, executable)
            thermal_future = pool.submit(fastfetch_probe, executable, True)
            primary, base_errors = base_future.result()
            thermal, thermal_errors = thermal_future.result()
        errors.extend(base_errors + thermal_errors)
        data.update(primary)
    else:
        errors.append('Fastfetch is not installed or not on PATH')
    local = hardware.extra_info()
    for name, value in local.items():
        # Use direct system probes only where Fastfetch could not supply data.
        if name not in primary or not primary[name]:
            data[name] = value
        elif isinstance(value, dict) and isinstance(data.get(name), dict):
            for field, fallback in value.items():
                if not data[name].get(field):
                    data[name][field] = fallback
    if not data.get('display'):
        displays = hardware.display_info()
        if displays:
            data['display'] = displays
    if isinstance(thermal.get('cpu'), dict) and thermal['cpu'].get('temperature') is not None:
        data.setdefault('cpu', {}).update(thermal['cpu'])
    # Match thermal GPU entries by name, never by enumeration order.
    for gpu in data.get('gpu', []):
        measured = next((item for item in thermal.get('gpu', [])
                         if item.get('name') == gpu.get('name') and item.get('temperature') is not None), None)
        if measured:
            gpu['temperature'] = measured['temperature']
    data['disk'] = hardware.refresh_disk_usage(data.get('disk', []))
    data = hardware.enrich(data)
    data['diagnostics'] = {'fastfetch': executable or 'not found', 'errors': errors,
                           'modules': sorted(primary),
                           'sensor_count': len(hardware.sensors())}
    return shell_context(data)


def temperature(value):
    return color(f"{value:.1f}°C", GREEN) if isinstance(value, (int, float)) and math.isfinite(value) and -20 <= value <= 125 else ''


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


def compact_disks(disks):
    """Show each backing filesystem once, preferring its shortest mount path."""
    selected, seen = [], set()
    for disk in sorted(disks, key=lambda item: (item.get('mountpoint') != '/', len(item.get('mountpoint', '')))):
        mount = disk.get('mountpoint', '')
        source = disk.get('mountFrom', '')
        # Btrfs subvolume suffixes are not separate storage devices.
        identity = re.sub(r'\[.*\]$', '', source) if source else ''
        if not identity:
            try:
                identity = ('device', os.stat(mount).st_dev)
            except OSError:
                identity = ('mount', mount)
        if identity in seen:
            continue
        seen.add(identity)
        selected.append(disk)
    return selected


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
    for disk in compact_disks(data.get('disk', [])) or [{}]:
        hardware.append(('ROM ' + clean(disk.get('mountpoint', '')),
                         usage(disk.get('bytes', {}))))
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
                 ('Days', 'Mo Tu We Th Fr Sa Su')]
    for index, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(now.year, now.month), 1):
        days = []
        for day in week:
            value = f'{day:2}' if day else '  '
            if day == now.day:
                value = '\033[48;2;0;230;160m' + color(value, '#000000')
            days.append(value)
        date_rows.append((f'{index}. Week', ' '.join(days)))
    return [('HARDWARE', TEAL, hardware), ('SYSTEM & SOFTWARE', BLUE, system),
            ('DATE & CALENDAR', CACHY_GREEN, date_rows)]


def dashboard(data, width=76, now=None):
    now = now or datetime.now().astimezone()
    width = max(32, width)
    label_width = 14
    groups = sections(data, now)
    # Fit the top hardware section, then share its width across every rule.
    content_width = max((visible_width(str(value)) for _, value in groups[0][2]), default=0)
    frame_width = min(width, max(32, label_width + 7 + content_width))
    inside = frame_width - 2
    value_width = inside - label_width - 5
    rows = []
    for index, (title, accent, entries) in enumerate(groups):
        middle = ' ' + title + ' '
        remaining = inside - len(middle)
        border = ('┌' if index == 0 else '├') + '─' * (remaining // 2) + middle + '─' * (remaining - remaining // 2) + ('┐' if index == 0 else '┤')
        rows.append(color(border, accent))
        for label, value in entries:
            icons = {'CPU': '▣', 'GPU': '▧', 'RAM': '▤',
                     'Host': '◆', 'Distribution': '◈', 'Kernel': '⚙', 'Uptime': '◷',
                     'Packages': '▦', 'Desktop': '▱', 'Window-Manager': '▧',
                     'Shell': '›', 'Terminal': '▣', 'Date': '◷', 'Days': '▦'}
            icon = '▰' if label.startswith('ROM') else icons.get(label, '▦')
            label = clip(clean(label), label_width)
            value = clip(str(value), value_width)
            # Calendar numbers are white, except black text on the green current day.
            if title == 'DATE & CALENDAR' and label.startswith(('Date', 'Days')):
                styled_value = color(value, BLUE)
            elif title == 'DATE & CALENDAR':
                styled_value = terminal_color(value, 97)
            else:
                styled_value = color(value, WHITE)
            line = (color(' ' + icon + ' ', accent) + color(label, accent)
                    + ' ' * (label_width - visible_width(label)) + color(' → ', CYAN)
                    + styled_value + ' ' * (value_width - visible_width(value))
                    + ' ')
            rows.append(line)
    rows.append(color('└' + '─' * inside + '┘', TEAL))
    rows.append(' ' + ' '.join(terminal_color('●', code) for code in range(30, 38)))
    return rows


def system_info(width=76):
    return dashboard(collect(), width)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Read-only local hardware diagnostics')
    parser.add_argument('--diagnose', action='store_true')
    args = parser.parse_args()
    data = collect()
    if args.diagnose:
        print(json.dumps({'detection': data['diagnostics'], 'sensor_access': hardware.sensor_access(), 'cpu': data.get('cpu'),
                          'gpu': data.get('gpu'), 'sensors': data.get('sensors'),
                          'desktop': data.get('de'), 'window_manager': data.get('wm'),
                          'display': data.get('display'), 'packages': data.get('packages')},
                         indent=2))
    else:
        print('\n'.join(dashboard(data)))

"""Read-only local Linux probes. Never loads drivers, changes permissions, or uses sudo."""
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return ''


def command(args, timeout=2):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def sensors(sys=Path('/sys')):
    """Keep chip/device identity; never assign one GPU's temperature to another."""
    cards = {}
    for card in (sys / 'class/drm').glob('card[0-9]*'):
        if re.fullmatch(r'card\d+', card.name):
            for hwmon in (card / 'device/hwmon').glob('hwmon*'):
                cards[str(hwmon.resolve())] = card.name
    values = []
    for hwmon in sorted((sys / 'class/hwmon').glob('hwmon*')):
        chip = read(hwmon / 'name') or hwmon.name
        device = cards.get(str(hwmon.resolve()), '')
        if not device and chip == 'nvme':
            device = (hwmon / 'device').resolve().name
        for path in sorted(hwmon.glob('temp*_input')):
            label = read(path.with_name(path.name.replace('_input', '_label'))) or path.stem.replace('_input', '')
            try:
                value = int(read(path)) / 1000
            except ValueError:
                continue
            if not -20 <= value <= 125:
                continue  # Common disconnected sensor sentinels are not temperatures.
            values.append({'chip': chip, 'device': device, 'label': label,
                           'temperature': value})
    return values


def cpu_info(proc=Path('/proc'), sys=Path('/sys')):
    cpu = {}
    for line in read(proc / 'cpuinfo').splitlines():
        if line.lower().startswith(('model name', 'hardware')) and ':' in line:
            cpu['cpu'] = line.split(':', 1)[1].strip()
            break
    if cpu:
        cpu['cores'] = {'online': os.cpu_count() or 1}
        try:
            mhz = int(read(sys / 'devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq')) / 1000
            cpu['frequency'] = {'max': mhz}
        except ValueError:
            pass
    return cpu


def pci_gpus():
    executable = shutil.which('lspci')
    if not executable:
        return []
    gpus = []
    for line in command([executable, '-Dmm']).splitlines():
        try:
            parts = shlex.split(line)
        except ValueError:
            continue
        if len(parts) < 4 or not any(name in parts[1].lower() for name in
                                     ('vga compatible', '3d controller', 'display controller')):
            continue
        gpus.append({'name': parts[3], 'vendor': parts[2], 'pciAddress': parts[0]})
    return gpus


def display_info():
    # KDE's read-only output query, useful when Fastfetch cannot load display libraries.
    executable = shutil.which('kscreen-doctor')
    if not executable:
        return []
    try:
        data = json.loads(command([executable, '-j']))
    except ValueError:
        return []
    displays = []
    for output in data.get('outputs', []):
        if not output.get('connected') or not output.get('enabled'):
            continue
        mode_id = output.get('currentModeId')
        mode = next((mode for mode in output.get('modes', []) if str(mode.get('id')) == str(mode_id)), {})
        size = mode.get('size', {})
        if not size.get('width'):
            continue
        displays.append({'width': size['width'], 'height': size['height'],
                         'refreshRate': mode.get('refreshRate', 0),
                         'scaleFactor': output.get('scale', 1),
                         'name': output.get('name', '')})
    return displays


def extra_info(sys=Path('/sys'), proc=Path('/proc')):
    result = {}
    cpu = cpu_info(proc, sys)
    if cpu:
        result['cpu'] = cpu
    board = read(sys / 'devices/virtual/dmi/id/board_name')
    product = read(sys / 'devices/virtual/dmi/id/product_name')
    if board or product:
        result['host'] = {'name': board or product}
    gpus = pci_gpus()
    if gpus:
        result['gpu'] = gpus
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').split(':')[0]
    if desktop:
        name = {'KDE': 'KDE Plasma', 'GNOME': 'GNOME'}.get(desktop.upper(), desktop)
        result['de'] = {'prettyName': name}
        if desktop.upper() == 'KDE' and shutil.which('plasmashell'):
            version = command(['plasmashell', '--version']).strip()
            match = re.search(r'\b\d+\.\d+(?:\.\d+)?\b', version)
            if match:
                result['de']['version'] = match[0]
    process_names = {read(path) for path in proc.glob('[0-9]*/comm')}
    for process, name, protocol in [('kwin_wayland', 'KWin', 'Wayland'),
                                     ('kwin_x11', 'KWin', 'X11'),
                                     ('Hyprland', 'Hyprland', 'Wayland'),
                                     ('sway', 'Sway', 'Wayland'),
                                     ('gnome-shell', 'Mutter', os.environ.get('XDG_SESSION_TYPE', ''))]:
        if process in process_names:
            result['wm'] = {'prettyName': name, 'protocolName': protocol}
            break
    pacman = shutil.which('pacman')
    if pacman:
        packages = command([pacman, '-Qq'])
        if packages:
            count = len(packages.splitlines())
            result['packages'] = {'all': count, 'pacman': count}
    return result


def gpu_name_matches(name, pci_name):
    def words(value):
        value = re.sub(r'\b(?:amd|ati|nvidia|inc|corporation)\b', '', value.lower())
        return re.findall(r'[a-z]+|[0-9]+', value)
    left, right = words(name), words(pci_name)
    if not left or not right:
        return False
    if ''.join(left) in ''.join(right) or ''.join(right) in ''.join(left):
        return True
    # PCI descriptions can list both RX 9070 / 9070 XT variants.
    return any(token.isdigit() and len(token) >= 3 for token in left) and set(left) <= set(right)


def enrich(data, sys=Path('/sys')):
    readings = sensors()
    cpu = data.setdefault('cpu', {})
    cpu_sensor = next((item for item in readings if item['chip'] in ('k10temp', 'zenpower', 'coretemp')
                       and item['label'] in ('Tctl', 'Tdie', 'Package id 0')), None)
    if cpu_sensor and (not isinstance(cpu.get('temperature'), (int, float)) or not math.isfinite(cpu['temperature'])):
        cpu['temperature'] = cpu_sensor['temperature']
    # Use PCI identity/name matching, then a unique one-to-one remainder.
    # Never assume that Fastfetch order equals DRM card numbering.
    inventory = pci_gpus()
    cards = {}
    for sensor in readings:
        if sensor['chip'] == 'amdgpu' and sensor.get('device') and sensor['label'] == 'edge':
            address = (sys / 'class/drm' / sensor['device'] / 'device').resolve().name
            name = next((gpu['name'] for gpu in inventory if gpu.get('pciAddress') == address), '')
            cards[sensor['device']] = {'name': name, 'temperature': sensor['temperature']}
    gpus = data.get('gpu', [])
    matched_cards, matched_gpu = set(), set()
    for index, gpu in enumerate(gpus):
        name = gpu.get('name', '')
        candidates = [card for card, value in cards.items()
                      if card not in matched_cards and name and
                      gpu_name_matches(name, value['name'])
                      and value['name']]
        if len(candidates) == 1:
            card = candidates[0]
            if not isinstance(gpu.get('temperature'), (int, float)) or not math.isfinite(gpu['temperature']):
                gpu['temperature'] = cards[card]['temperature']
            matched_cards.add(card)
            matched_gpu.add(index)
    remaining_cards = set(cards) - matched_cards
    remaining_gpu = set(range(len(gpus))) - matched_gpu
    if len(gpus) == len(inventory) == len(cards) and len(remaining_cards) == len(remaining_gpu) == 1:
        gpu = gpus[remaining_gpu.pop()]
        if not isinstance(gpu.get('temperature'), (int, float)):
            gpu['temperature'] = cards[remaining_cards.pop()]['temperature']
    # Raw readings stay available to --diagnose, not the compact dashboard.
    data['sensors'] = [item for item in readings if item is not cpu_sensor]
    return data


def sensor_access(sys=Path('/sys')):
    files, denied = 0, []
    for path in (sys / 'class/hwmon').glob('hwmon*/temp*_input'):
        try:
            path.read_text()
            files += 1
        except OSError as error:
            denied.append({'path': str(path), 'reason': str(error)})
    return {'readable_temperature_files': files, 'read_errors': denied,
            'loaded_sensor_drivers': [name for name in ('k10temp', 'coretemp', 'amdgpu', 'nvidia')
                                      if (sys / 'module' / name).exists()]}



def refresh_disk_usage(disks):
    for disk in disks:
        mount = disk.get('mountpoint', '')
        filesystem = disk.get('filesystem', '').lower()
        if not mount.startswith('/') or filesystem in ('nfs', 'nfs4', 'cifs', 'smbfs', 'fuse.sshfs'):
            continue
        try:
            usage = shutil.disk_usage(mount)
        except OSError:
            continue
        values = dict(disk.get('bytes', {}))
        values.update(total=usage.total, used=usage.used, free=usage.free)
        disk['bytes'] = values
    return disks

from datetime import datetime
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'animated'))
import dashboard


class DashboardTests(unittest.TestCase):
    def sample(self):
        return {
            'cpu': {'cpu': 'AMD Ryzen 7 9700X', 'cores': {'online': 16},
                    'frequency': {'max': 5500}, 'temperature': 45.1},
            'gpu': [{'name': 'AMD Radeon RX 9070 XT', 'type': 'Discrete',
                     'temperature': 49},
                    {'name': 'AMD Radeon Graphics', 'type': 'Integrated',
                     'temperature': 41}],
            'memory': {'total': 32 * 1024**3, 'used': 8 * 1024**3},
            'disk': [{'mountpoint': '/', 'bytes': {'total': 1024**4, 'used': 200 * 1024**3}}],
            'display': [{'width': 3840, 'height': 2160, 'refreshRate': 120,
                         'scaleFactor': 2, 'type': 'External'}],
            'host': {'name': 'B650 GAMING X AX V2'},
            'os': {'prettyName': 'CachyOS'},
            'kernel': {'name': 'Linux', 'release': '6.18.1', 'architecture': 'x86_64'},
            'uptime': {'uptime': 3_660_000},
            'packages': {'all': 1933, 'pacman': 1933},
            'de': {'prettyName': 'KDE Plasma', 'version': '6.5'},
            'wm': {'prettyName': 'KWin', 'protocolName': 'Wayland'},
            'shell': {'prettyName': 'fish', 'version': '4.3'},
            'terminal': {'prettyName': 'konsole', 'version': '26.04'},
            # Even unexpected network entries must never enter the view.
            'localip': {'address': '192.0.2.123'}, 'publicip': {'ip': '198.51.100.7'}
        }

    def test_sections_values_width_and_no_network(self):
        rows = dashboard.dashboard(self.sample(), 76, datetime(2026, 10, 28, 12))
        plain = '\n'.join(dashboard.CSI.sub('', line) for line in rows)
        for text in ('HARDWARE', 'SYSTEM & SOFTWARE', 'DATE & CALENDAR', 'GPU',
                     'AMD Ryzen 7 9700X', '5.50 GHz', '45.1°C', 'RAM', 'ROM /',
                     'Display', '3840x2160 @ 2x', 'Distribution', 'CachyOS x86_64',
                     'KDE Plasma', 'KWin (Wayland)', 'konsole', '1933 (pacman)',
                     'Mo Tu We Th Fr Sa Su', 'Oct 2026', 'W44'):
            self.assertIn(text, plain)
        for text in ('NETWORK', 'LAN', 'DNS', 'WAN', '192.0.2', '198.51.100'):
            self.assertNotIn(text, plain)
        self.assertTrue(all(dashboard.visible_width(row) == 76 for row in rows[:-1]))
        self.assertIn('\033[7m', '\n'.join(rows))
        for shade in (dashboard.TEAL, dashboard.BLUE, dashboard.CACHY_GREEN):
            self.assertIn(dashboard.color('', shade).split('m')[0] + 'm', '\n'.join(rows))

    def test_narrow_panel_keeps_borders_and_color_sequences(self):
        rows = dashboard.dashboard(self.sample(), 38, datetime(2026, 2, 28))
        self.assertTrue(all(dashboard.visible_width(row) == 38 for row in rows[:-1]))
        clipped = dashboard.clip(dashboard.color('ABCD', dashboard.TEAL), 2)
        self.assertEqual(dashboard.CSI.sub('', clipped), 'AB')
        self.assertEqual(dashboard.visible_width(dashboard.clip('中AB', 3)), 3)

    def test_collector_explicitly_excludes_network_and_user_config(self):
        payload = [{'type': 'OS', 'result': {'prettyName': 'CachyOS'}},
                   {'type': 'Memory', 'result': {'total': 100, 'used': 25}},
                   {'type': 'Kernel', 'result': {'release': '6.18.1'}},
                   {'type': 'LocalIp', 'result': {'address': '192.0.2.123'}}]
        result = subprocess.CompletedProcess([], 0, json.dumps(payload), '')
        with patch.object(dashboard.shutil, 'which', return_value='/usr/bin/fastfetch'), \
             patch.object(dashboard.subprocess, 'run', return_value=result) as run, \
             patch.object(dashboard.hardware, 'extra_info', return_value={}), \
             patch.object(dashboard.hardware, 'display_info', return_value=[]), \
             patch.object(dashboard.hardware, 'enrich', side_effect=lambda data: data):
            collected = dashboard.collect()
            self.assertEqual(collected['os']['prettyName'], 'CachyOS')
            self.assertEqual(collected['memory']['used'], 25)
            self.assertEqual(collected['kernel']['release'], '6.18.1')
            self.assertNotIn('localip', collected)
        args = next(call.args[0] for call in run.call_args_list if '--cpu-temp' not in call.args[0])
        self.assertEqual(args[args.index('--config') + 1], 'none')
        requested = args[args.index('--structure') + 1].lower().split(':')
        self.assertNotIn('localip', requested)
        self.assertNotIn('publicip', requested)
        self.assertNotIn('netio', requested)
        self.assertNotIn('dns', requested)
        self.assertIn('display', requested)

    def test_unavailable_fields_do_not_become_invented_stats(self):
        text = '\n'.join(dashboard.dashboard({}, 76, datetime(2026, 2, 28)))
        self.assertIn('Unavailable', text)
        self.assertNotIn('AMD Ryzen', text)
        self.assertIn('DATE & CALENDAR', text)

    def test_real_shell_and_konsole_context_override_python_wrapper(self):
        with patch.dict(dashboard.os.environ, {'POKEMON_SHELL_VERSION': '4.3.0',
                                              'KONSOLE_VERSION': '260401'}):
            data = dashboard.shell_context({'shell': {'prettyName': 'python3'}})
        self.assertEqual(data['shell'], {'prettyName': 'fish', 'version': '4.3.0'})
        self.assertEqual(data['terminal'], {'prettyName': 'Konsole', 'version': '26.04.1'})

    def test_failed_temperature_options_do_not_discard_base_hardware(self):
        def execute(args, **kwargs):
            if '--cpu-temp' in args:
                raise subprocess.CalledProcessError(1, args, stderr='Unknown optional argument')
            payload = [{'type': 'CPU', 'result': {'cpu': 'Real CPU'}},
                       {'type': 'GPU', 'result': [{'name': 'Real GPU'}]},
                       {'type': 'Packages', 'result': {'all': 1933}}]
            return subprocess.CompletedProcess(args, 0, json.dumps(payload), '')
        with patch.object(dashboard.shutil, 'which', return_value='/usr/bin/fastfetch'), \
             patch.object(dashboard.subprocess, 'run', side_effect=execute), \
             patch.object(dashboard.hardware, 'extra_info', return_value={}), \
             patch.object(dashboard.hardware, 'display_info', return_value=[]), \
             patch.object(dashboard.hardware, 'enrich', side_effect=lambda data: data):
            data = dashboard.collect()
        self.assertEqual(data['cpu']['cpu'], 'Real CPU')
        self.assertEqual(data['gpu'][0]['name'], 'Real GPU')
        self.assertEqual(data['packages']['all'], 1933)
        self.assertIn('Unknown optional argument', str(data['diagnostics']['errors']))

    def test_failed_fastfetch_keeps_direct_cpu_gpu_and_package_probes(self):
        direct = {'cpu': {'cpu': 'AMD Ryzen 7 9700X'},
                  'gpu': [{'name': 'Radeon RX 9070 XT'}],
                  'packages': {'all': 1933, 'pacman': 1933},
                  'de': {'prettyName': 'KDE Plasma'}}
        with patch.object(dashboard.shutil, 'which', return_value='/usr/bin/fastfetch'), \
             patch.object(dashboard.subprocess, 'run', side_effect=subprocess.CalledProcessError(
                 1, 'fastfetch', stderr='Unsupported argument')), \
             patch.object(dashboard.hardware, 'extra_info', return_value=direct), \
             patch.object(dashboard.hardware, 'display_info', return_value=[]), \
             patch.object(dashboard.hardware, 'enrich', side_effect=lambda data: data):
            data = dashboard.collect()
        self.assertEqual(data['cpu']['cpu'], 'AMD Ryzen 7 9700X')
        self.assertEqual(data['gpu'][0]['name'], 'Radeon RX 9070 XT')
        self.assertEqual(data['packages']['all'], 1933)
        self.assertEqual(data['de']['prettyName'], 'KDE Plasma')
        self.assertIn('Unsupported argument', str(data['diagnostics']['errors']))

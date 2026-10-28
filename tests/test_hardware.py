import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'animated'))
import hardware


class HardwareTests(unittest.TestCase):
    def test_cpu_and_readable_sensor_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'proc').mkdir()
            (root / 'proc/cpuinfo').write_text('model name : AMD Ryzen 7 9700X 8-Core Processor\n')
            cpufreq = root / 'sys/devices/system/cpu/cpu0/cpufreq'
            cpufreq.mkdir(parents=True)
            (cpufreq / 'cpuinfo_max_freq').write_text('5500000')
            for index, chip, label, value in [(0, 'k10temp', 'Tctl', '45125'),
                                               (1, 'amdgpu', 'junction', '67000'),
                                               (2, 'nvme', 'Composite', '39000'),
                                               (3, 'unknown', 'disconnected', '255000')]:
                hwmon = root / f'sys/class/hwmon/hwmon{index}'
                hwmon.mkdir(parents=True)
                (hwmon / 'name').write_text(chip)
                (hwmon / 'temp1_label').write_text(label)
                (hwmon / 'temp1_input').write_text(value)
            cpu = hardware.cpu_info(root / 'proc', root / 'sys')
            self.assertEqual(cpu['cpu'], 'AMD Ryzen 7 9700X 8-Core Processor')
            self.assertEqual(cpu['frequency']['max'], 5500)
            readings = hardware.sensors(root / 'sys')
            self.assertEqual(len(readings), 3)
            self.assertEqual(readings[0]['temperature'], 45.125)
            self.assertIn(67, [reading['temperature'] for reading in readings])
            self.assertEqual(hardware.sensor_access(root / 'sys')['readable_temperature_files'], 4)
            with patch.object(hardware, 'sensors', return_value=readings):
                data = hardware.enrich({'cpu': cpu})
            self.assertEqual(data['cpu']['temperature'], 45.125)
            self.assertEqual(len(data['sensors']), 2)

    def test_gpu_names_come_from_local_pci_inventory(self):
        listing = '0000:03:00.0 "VGA compatible controller" "Advanced Micro Devices, Inc. [AMD/ATI]" "Navi 48 [Radeon RX 9070 XT]"\n'
        with patch.object(hardware.shutil, 'which', return_value='/usr/bin/lspci'), \
             patch.object(hardware, 'command', return_value=listing):
            gpus = hardware.pci_gpus()
        self.assertEqual(gpus[0]['pciAddress'], '0000:03:00.0')
        self.assertIn('9070 XT', gpus[0]['name'])

    def test_kde_display_query_uses_current_enabled_mode(self):
        payload = {'outputs': [{'connected': True, 'enabled': True,
                                'currentModeId': '1', 'scale': 2,
                                'modes': [{'id': '1', 'size': {'width': 3840, 'height': 2160},
                                           'refreshRate': 120}]}]}
        with patch.object(hardware.shutil, 'which', return_value='/usr/bin/kscreen-doctor'), \
             patch.object(hardware, 'command', return_value=json.dumps(payload)):
            displays = hardware.display_info()
        self.assertEqual(displays[0]['width'], 3840)
        self.assertEqual(displays[0]['refreshRate'], 120)
        self.assertEqual(displays[0]['scaleFactor'], 2)

    def test_missing_hardware_data_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(hardware.sensors(Path(directory)), [])
            self.assertEqual(hardware.cpu_info(Path(directory), Path(directory)), {})

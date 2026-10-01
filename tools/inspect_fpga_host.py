#!/usr/bin/env python3
"""Read USB descriptors and PCI sysfs state without opening device interfaces.

No serial numbers, MACs, network names, BAR reads, driver changes or programming.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def read(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return None


def inspect():
    usb = []
    for path in sorted(Path('/sys/bus/usb/devices').glob('*')):
        if not (path / 'idVendor').exists() or path.name.startswith('usb'):
            continue
        usb.append({key: value for key in ['idVendor', 'idProduct', 'manufacturer', 'product', 'speed']
                    if (value := read(path / key)) is not None})
    pci = []
    for path in sorted(Path('/sys/bus/pci/devices').glob('*')):
        if read(path / 'vendor') != '0xdabc' or read(path / 'device') != '0x1017':
            continue
        record = {key: read(path / key) for key in ['vendor', 'device', 'subsystem_vendor',
            'subsystem_device', 'class', 'enable', 'current_link_speed', 'current_link_width',
            'max_link_speed', 'max_link_width']}
        record['slot'] = path.name
        record['driver'] = (path / 'driver').resolve().name if (path / 'driver').exists() else None
        resources = read(path / 'resource')
        record['bar_aperture_bytes'] = []
        for index, line in enumerate((resources or '').splitlines()[:6]):
            start, end, flags = (int(item, 16) for item in line.split())
            if start or end:
                record['bar_aperture_bytes'].append({'bar': index, 'bytes': end - start + 1})
        pci.append(record)
    commands = ['openFPGALoader', 'efx_run', 'vivado', 'litex_server', 'picotool', 'openocd', 'mpremote']
    return {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
            'evidence_class': 'read-only host enumeration', 'usb': usb, 'pci_candidates': pci,
            'software_on_path': {command: shutil.which(command) is not None for command in commands},
            'limits': ['USB descriptors cannot prove absence of a board with custom firmware.',
                       'PATH lookup is not an exhaustive filesystem software search.',
                       'PCI identity is configurable; it does not prove silicon or board markings.',
                       'BAR aperture size is not physical memory capacity.']}


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2))

#!/usr/bin/env python3
"""Bounded Nix dumpcap monitor in one owned, capability-scoped container."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

from ble_dumpcap_monitor import capture_command, dumpcap_command


def container_command(name, image_id, executable, seconds):
    if not re.fullmatch(r'esp-sdr-ble-monitor-[0-9a-f]{32}', name):
        raise ValueError('invalid owned container name')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
        raise ValueError('immutable local image ID required')
    if not Path(executable).resolve().is_relative_to('/nix/store') or not executable.endswith('/bin/dumpcap'):
        raise ValueError('Nix dumpcap executable required')
    if not .1 <= seconds <= 3600:
        raise ValueError('bounded monitor duration required')
    # The image contains the executable's Nix closure. No host files/devices
    # are mounted; stdout is sanitized immediately by the unprivileged parent.
    with_executable = [executable, '-i', 'bluetooth-monitor', '-P', '-Q',
                       '-s', '65539', '-a', f'duration:{seconds:g}', '-w', '-']
    return ['docker', 'run', '--name', name, '--rm', '--pull', 'never',
            '--network', 'host', '--cap-drop', 'ALL', '--cap-add', 'NET_RAW',
            '--security-opt', 'no-new-privileges', '--read-only', '--user', '0:0',
            '--entrypoint', executable, image_id, *with_executable[1:]]


def remove_owned_container(name):
    # Killing only the docker client can leave dumpcap's socket alive. Remove
    # our exact random name, then distinguish an already-removed container from
    # a daemon/permission error by a successful, empty exact-name listing.
    if not re.fullmatch(r'esp-sdr-ble-monitor-[0-9a-f]{32}', name):
        raise ValueError('invalid owned container name')
    result = subprocess.run(['docker', 'rm', '--force', name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode == 0:
        return True
    remaining = subprocess.run(['docker', 'ps', '--all', '--filter', f'name=^{name}$',
                                '--format', '{{.ID}}'], capture_output=True, timeout=10)
    return remaining.returncode == 0 and not remaining.stdout.strip()


def resolve_image():
    archive = Path(os.environ.get('BLE_MONITOR_IMAGE', '')).resolve()
    tag = os.environ.get('BLE_MONITOR_IMAGE_TAG')
    if not archive.is_relative_to('/nix/store') or not archive.is_file() or not tag:
        raise ValueError('enter the Nix development shell for the pinned Bluetooth monitor image')
    subprocess.run(['docker', 'load', '--input', str(archive)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
    images = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], timeout=10))
    if len(images) != 1 or not re.fullmatch(r'sha256:[0-9a-f]{64}', images[0]['Id']):
        raise ValueError('cannot resolve one immutable local monitor image')
    return images[0]['Id']


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--seconds', type=float, default=60)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    if not .1 <= args.seconds <= 3600 or args.output.exists():
        cli.error('bounded seconds and a fresh output path required')
    name = 'esp-sdr-ble-monitor-'+uuid.uuid4().hex
    try:
        # dumpcap_command resolves only the flake's executable; no socket opens.
        executable = str(Path(dumpcap_command(args.seconds)[0]).resolve())
        image_id = resolve_image()
        command = container_command(name, image_id, executable, args.seconds)
    except (ValueError, OSError, subprocess.SubprocessError):
        cli.error('pinned monitor image or Docker unavailable; no capture started')
    record = capture_command(command, args.seconds,
                             producer_cleanup=lambda: remove_owned_container(name))
    record['transport'] = 'Nix dumpcap owned NET_RAW container stdout pipe'
    record['container_image_id'] = image_id
    record['container_host_mounts'] = []
    record['container_capabilities'] = ['NET_RAW']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as sink:
        json.dump(record, sink, indent=2)
        sink.write('\n')
    print(f'MONITOR_CLOSED status={record["status"]} sanitized_records={len(record["records"])}', flush=True)
    return 0 if record['status'] == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())

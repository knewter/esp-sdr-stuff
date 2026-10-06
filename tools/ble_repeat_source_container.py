#!/usr/bin/env python3
"""Run the repeated counted HCI source in the pinned Nix source image."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from ble_repeat_counted_source import EVENTS_PER_CYCLE, INTERVAL_MS, validate_cycles
from ble_source_container import container_absent, resolve_source_image, stop_owned_source, validate_name

TOOLS = Path(__file__).resolve().parent
MOUNTED = ('ble_repeat_counted_source.py', 'ble_direct_hci_source.py')


def parse(argv):
    import argparse
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--cycles', type=int, required=True)
    cli.add_argument('--start-delay', type=float, default=1)
    cli.add_argument('--channel', type=int, choices=(37, 38, 39), default=37)
    args = cli.parse_args(argv)
    try:
        validate_cycles(args.cycles)
    except ValueError as error:
        cli.error(str(error))
    if not 0 <= args.start_delay <= 60:
        cli.error('start delay must be 0..60s')
    return args


def source_command(name, image_id, executable, argv):
    validate_name(name)
    parse(argv)
    if not Path(executable).is_relative_to('/nix/store'):
        raise ValueError('Nix Python executable required')
    mounts = []
    for file in MOUNTED:
        mounts += ['--mount', f'type=bind,src={TOOLS/file},dst=/app/{file},readonly']
    return ['docker', 'run', '--rm', '--name', name, '--pull', 'never',
            '--network', 'host', '--cap-drop', 'ALL', '--cap-add', 'NET_ADMIN',
            '--cap-add', 'NET_RAW', '--security-opt', 'no-new-privileges',
            '--read-only', '--user', '0:0', '--env', 'PYTHONDONTWRITEBYTECODE=1',
            *mounts, '--entrypoint', executable, image_id,
            '/app/ble_repeat_counted_source.py', *argv]


def main():
    argv = sys.argv[1:]
    args = parse(argv)
    image_id, reused = resolve_source_image(os.environ['BLE_SOURCE_IMAGE'], os.environ['BLE_SOURCE_IMAGE_TAG'],
                                            os.environ.get('BLE_SOURCE_PRELOADED_IMAGE_ID'))
    name = 'esp-sdr-ble-source-'+uuid.uuid4().hex
    interrupted = False

    def requested(signum, frame):
        nonlocal interrupted
        interrupted = True
    previous = {sig: signal.signal(sig, requested) for sig in (signal.SIGINT, signal.SIGTERM)}
    proc = subprocess.Popen(source_command(name, image_id, os.environ['BLE_SOURCE_PYTHON'], argv),
                            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    code = 2
    try:
        deadline = time.monotonic()+args.start_delay+args.cycles*(EVENTS_PER_CYCLE*(INTERVAL_MS/1000+.010)+1)+30
        while proc.poll() is None and not interrupted and time.monotonic() < deadline:
            time.sleep(.1)
        if proc.poll() is not None:
            code = proc.returncode
    finally:
        cleanup = ({'owned_container_removed': True, 'force_removal_required': False}
                   if container_absent(name) else stop_owned_source(name))
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        print(json.dumps({'kind': 'source_container_closed', **cleanup, 'interrupted': interrupted,
                          'image_id': image_id, 'preloaded_image_reused': reused}), flush=True)
    return code if cleanup['owned_container_removed'] and not interrupted else 2


if __name__ == '__main__':
    raise SystemExit(main())

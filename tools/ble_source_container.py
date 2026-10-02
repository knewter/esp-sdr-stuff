#!/usr/bin/env python3
"""Run the fixed owned HCI source in one Nix Python container; sanitized stdout."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

from ble_direct_hci_source import enable

SOURCE = Path(__file__).with_name('ble_direct_hci_source.py').resolve()


def validate_options(argv):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--handle', type=int, choices=[1, 239], default=239)
    cli.add_argument('--interval-ms', type=int, choices=[20, 100], default=20)
    cli.add_argument('--events', type=int, default=100)
    cli.add_argument('--duration-ms', type=int, default=0)
    cli.add_argument('--start-delay', type=float, default=1)
    cli.add_argument('--unlimited-events', action='store_true')
    args = cli.parse_args(argv)
    if not 0 <= args.start_delay <= 60:
        cli.error('start delay must be 0..60s')
    try:
        enable(True, args.events, args.duration_ms, args.handle, args.unlimited_events)
    except ValueError as error:
        cli.error(str(error))
    return args


def validate_name(name):
    if not re.fullmatch(r'esp-sdr-ble-source-[0-9a-f]{32}', name):
        raise ValueError('invalid owned source container name')


def source_command(name, image_id, executable, argv):
    validate_name(name)
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
        raise ValueError('immutable source image required')
    if not Path(executable).resolve().is_relative_to('/nix/store') or Path(executable).name not in ('python3', 'python3.13'):
        raise ValueError('Nix Python executable required')
    validate_options(argv)
    return ['docker', 'run', '--rm', '--name', name, '--pull', 'never',
            '--network', 'host', '--cap-drop', 'ALL', '--cap-add', 'NET_ADMIN',
            '--cap-add', 'NET_RAW', '--security-opt', 'no-new-privileges',
            '--read-only', '--user', '0:0', '--env', 'PYTHONDONTWRITEBYTECODE=1',
            '--mount', f'type=bind,src={SOURCE},dst=/source.py,readonly',
            '--entrypoint', executable, image_id, '/source.py', *argv]


def container_absent(name):
    validate_name(name)
    result = subprocess.run(['docker', 'ps', '--all', '--filter', f'name=^{name}$',
                             '--format', '{{.ID}}'], capture_output=True, timeout=10)
    return result.returncode == 0 and not result.stdout.strip()


def stop_owned_source(name):
    validate_name(name)
    # SIGINT reaches Python PID1; its finally disables/removes its own handle.
    # Eight seconds permits both bounded command acknowledgements and closure.
    stopped = subprocess.run(['docker', 'stop', '--signal', 'SIGINT', '--timeout', '8', name],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12)
    if container_absent(name):
        return {'owned_container_removed': True,
                'force_removal_required': False, 'stop_command_accepted': stopped.returncode == 0}
    subprocess.run(['docker', 'rm', '--force', name], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=10)
    return {'owned_container_removed': container_absent(name),
            'force_removal_required': True, 'stop_command_accepted': stopped.returncode == 0}


def resolve_source_image(archive, tag, preloaded_id=None):
    """Load by default; explicit preload must match the current tag, with no fallback."""
    archive = Path(archive).resolve()
    if (not archive.is_relative_to('/nix/store') or not archive.is_file() or
            type(tag) is not str or not tag or tag.startswith('-')):
        raise ValueError('pinned Nix source archive and tag required')
    if preloaded_id is not None and (type(preloaded_id) is not str or
            re.fullmatch(r'sha256:[0-9a-f]{64}', preloaded_id) is None):
        raise ValueError('strict immutable preloaded source image ID required')
    if preloaded_id is None:
        subprocess.run(['docker', 'load', '--input', str(archive)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60, check=True)
    images = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], timeout=10))
    if (type(images) is not list or len(images) != 1 or type(images[0]) is not dict or
            type(images[0].get('Id')) is not str or re.fullmatch(r'sha256:[0-9a-f]{64}',images[0]['Id']) is None):
        raise ValueError('one immutable source image required')
    image_id = images[0]['Id']
    if preloaded_id is not None and image_id != preloaded_id:
        raise ValueError('current tag does not match the explicit preloaded source image')
    return image_id, preloaded_id is not None


def main():
    argv = sys.argv[1:]
    if not argv or any(arg in ('-h', '--help') for arg in argv):
        return subprocess.run([sys.executable, str(SOURCE), '--help']).returncode
    args = validate_options(argv)  # No Docker/HCI access for invalid requests.
    archive = Path(os.environ.get('BLE_SOURCE_IMAGE', '')).resolve()
    tag = os.environ.get('BLE_SOURCE_IMAGE_TAG')
    executable = os.environ.get('BLE_SOURCE_PYTHON', '')
    try:
        image_id, reused = resolve_source_image(archive, tag, os.environ.get('BLE_SOURCE_PRELOADED_IMAGE_ID'))
    except (ValueError, OSError, subprocess.SubprocessError):
        raise SystemExit('pinned source image unavailable or preloaded identity mismatch; no source started')
    name = 'esp-sdr-ble-source-'+uuid.uuid4().hex
    command = source_command(name, image_id, executable, argv)
    interrupted = False
    def requested_interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True
    previous = {sig: signal.signal(sig, requested_interrupt) for sig in (signal.SIGINT, signal.SIGTERM)}
    proc = None
    cleanup = {'owned_container_removed': False, 'force_removal_required': False}
    code = 2
    try:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait = (args.duration_ms/1000 if args.duration_ms else args.events*(args.interval_ms/1000+.010))
        deadline = time.monotonic()+args.start_delay+wait+20
        while proc.poll() is None and not interrupted and time.monotonic() < deadline:
            time.sleep(.1)
        if proc.poll() is not None:
            code = proc.returncode
    finally:
        try:
            cleanup = (dict(owned_container_removed=True, force_removal_required=False)
                       if container_absent(name) else stop_owned_source(name))
        except (OSError, subprocess.SubprocessError):
            cleanup['cleanup_error'] = 'owned_container_state_unverified'
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=3)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        print(json.dumps({'kind': 'source_container_closed', **cleanup,
                          'source_controller_cleanup_verified_by_wrapper': False,
                          'interrupted': interrupted, 'image_id': image_id,
                          'preloaded_image_reused': reused}), flush=True)
    # Container absence proves socket release, not controller command success.
    # The source's native source_closed cleanup receipt remains authoritative.
    return code if cleanup['owned_container_removed'] and not cleanup['force_removal_required'] and not interrupted else 2


if __name__ == '__main__':
    raise SystemExit(main())

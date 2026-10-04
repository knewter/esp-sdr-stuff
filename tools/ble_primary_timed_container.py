#!/usr/bin/env python3
"""Explicit preloaded timed-v2 image; local Docker, fixed source, no archive load.

The caller owns controller admission and the inclusive 45-second episode clock.
This wrapper adds its own 45-second ceiling before image/runtime admission and
never makes forced process/container closure qualify normal completion.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

from ble_primary_timed_source import PROFILE, parent_deadline, validate_options

ROOT = Path(__file__).resolve().parents[1]
SOCKET = 'unix:///run/docker.sock'
BOUND = 45.0


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_name(name):
    require(type(name) is str and re.fullmatch('esp-sdr-ble-primary-timed-source-[0-9a-f]{32}', name),
            'exact owned timed-v2 name required')


def immutable_file(value, basename):
    require(type(value) is str and Path(value).is_absolute(), 'absolute Nix file required')
    path = Path(value).resolve(strict=True)
    require(path.is_relative_to('/nix/store') and path.name == basename and path.is_file(),
            'exact Nix file required')
    return str(path)


def python_executable(value):
    require(type(value) is str and Path(value).is_absolute(), 'absolute Nix Python required')
    path = Path(value).resolve(strict=True)
    require(path.is_relative_to('/nix/store') and path.name in ('python3', 'python3.13') and
            path.is_file() and os.access(path, os.X_OK), 'Nix Python required')
    return str(path)


def archive_labels(native_sha, v1_sha, entrypoint):
    for digest in (native_sha, v1_sha):
        require(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'exact source hash required')
    require(type(entrypoint) is str and Path(entrypoint).is_absolute() and
            Path(entrypoint).is_relative_to('/nix/store') and Path(entrypoint).name == 'ble_primary_timed_source.py',
            'archive-resident timed entrypoint required')
    return {'org.esp-sdr.source-profile': PROFILE,
            'org.esp-sdr.native-sha256': native_sha,
            'org.esp-sdr.v1-primitives-sha256': v1_sha,
            'org.esp-sdr.entrypoint': entrypoint}


def runtime():
    env = dict(os.environ)
    require(env.get('DOCKER_HOST') in (None, SOCKET) and env.get('DOCKER_CONTEXT') in (None, ''),
            'local Docker endpoint required')
    require(not env.get('DOCKER_TLS_VERIFY') and not env.get('DOCKER_CERT_PATH'), 'Docker TLS override refused')
    env.update(DOCKER_HOST=SOCKET, DOCKER_CONTEXT='')
    selected = shutil.which('docker', path=env.get('PATH', ''))
    require(selected is not None, 'Nix Docker executable required')
    docker = immutable_file(selected, 'docker')
    require(os.access(docker, os.X_OK), 'executable Docker required')
    return docker, env


def validate_cidfile(value):
    require(type(value) is str and Path(value).is_absolute(), 'absolute private CID path required')
    path = Path(value)
    require(path.parent.resolve(strict=True) == path.parent and
            path.parent.is_relative_to(ROOT / '.scratch'), 'private CID directory required')
    info = path.parent.stat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid(),
            'owned0700 CID directory required')
    try:
        path.lstat()
    except FileNotFoundError:
        return path
    raise ValueError('fresh CID path required')


def source_command(name, image_id, executable, entrypoint, argv, *, docker, cidfile=None):
    validate_name(name)
    require(type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}', image_id), 'immutable v2 image required')
    python = python_executable(executable)
    entrypoint = immutable_file(entrypoint, 'ble_primary_timed_source.py')
    docker = immutable_file(docker, 'docker')
    validate_options(argv)
    command = [docker, 'run', '--rm', '--name', name, '--pull', 'never', '--network', 'host',
               '--cap-drop', 'ALL', '--cap-add', 'NET_ADMIN', '--cap-add', 'NET_RAW',
               '--security-opt', 'no-new-privileges', '--read-only', '--user', '0:0',
               '--env', 'PYTHONDONTWRITEBYTECODE=1']
    if cidfile is not None:
        command += ['--cidfile', str(validate_cidfile(str(cidfile)))]
    return command + ['--entrypoint', python, image_id, entrypoint, *argv]


def remaining(deadline, cap):
    value = deadline - time.monotonic()
    require(value > 0, 'timed wrapper deadline')
    return min(cap, value)


def query(docker, env, args, deadline, cap=10):
    value = subprocess.run([docker, *args], env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=remaining(deadline, cap), check=True)
    remaining(deadline, cap)  # Includes return/deserialization boundaries.
    return value.stdout


def resolve_source_image(archive, tag, preloaded_id, executable, entrypoint, *, docker, env, deadline):
    require(type(archive) is str and Path(archive).resolve(strict=True).is_relative_to('/nix/store') and
            Path(archive).is_file(), 'pinned timed archive required')
    require(type(tag) is str and re.fullmatch('esp-sdr-ble-primary-timed-source:[0-9a-f]{16}', tag),
            'distinct fixed timed archive tag required')
    require(type(preloaded_id) is str and re.fullmatch('sha256:[0-9a-f]{64}', preloaded_id),
            'explicit immutable preloaded timed image required')
    executable = python_executable(executable)
    script = Path(immutable_file(entrypoint, 'ble_primary_timed_source.py'))
    old = script.with_name('ble_direct_hci_source.py')
    immutable_file(str(old), 'ble_direct_hci_source.py')
    import hashlib
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (script, old)}
    data = json.loads(query(docker, env, ['image', 'inspect', tag], deadline))
    require(type(data) is list and len(data) == 1 and type(data[0]) is dict, 'one timed image required')
    image = data[0]
    require(image.get('Id') == preloaded_id, 'timed image identity mismatch')
    config = image.get('Config')
    require(type(config) is dict and config.get('Cmd') == [executable, str(script)],
            'archive-resident timed command required')
    labels = config.get('Labels')
    expected = archive_labels(hashes[script.name], hashes[old.name], str(script))
    require(type(labels) is dict and all(labels.get(k) == v for k,v in expected.items()), 'timed archive labels mismatch')
    remaining(deadline, 10)
    return preloaded_id


def container_absent(name, docker, env, deadline):
    validate_name(name)
    return not query(docker, env, ['ps', '--all', '--filter', f'name=^{name}$', '--format', '{{.ID}}'], deadline).strip()


def group_alive(proc):
    try:
        os.killpg(proc.pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_natural(proc, deadline, cancelled):
    """Leader exit is insufficient; reap it and wait for whole group absence."""
    while True:
        remaining(deadline, 1)
        if cancelled():
            return False
        code = proc.poll()
        if code is not None:
            proc.wait(timeout=remaining(deadline, 1))
            if not group_alive(proc):
                remaining(deadline, 1)
                return True
        time.sleep(min(.02, remaining(deadline, .02)))


def cleanup_owned(name, proc, docker, env):
    """Bounded failure cleanup only; no cleanup action can turn failure into PASS."""
    receipt = {'forced_cleanup_required': True, 'owned_container_removed': False, 'owned_group_closed': False}
    cleanup_deadline = time.monotonic() + 25
    try:
        if not container_absent(name, docker, env, cleanup_deadline):
            subprocess.run([docker, 'stop', '--signal', 'SIGINT', '--timeout', '8', name], env=env,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=remaining(cleanup_deadline, 12))
        if not container_absent(name, docker, env, cleanup_deadline):
            subprocess.run([docker, 'rm', '--force', name], env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=remaining(cleanup_deadline, 10))
        receipt['owned_container_removed'] = container_absent(name, docker, env, cleanup_deadline)
    except (OSError, ValueError, subprocess.SubprocessError):
        receipt['container_closure_uncertain'] = True
    if proc is not None:
        try:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                if group_alive(proc):
                    try:
                        os.killpg(proc.pid, sig)
                    except ProcessLookupError:
                        pass
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    continue
                if not group_alive(proc):
                    break
            receipt['owned_group_closed'] = proc.poll() is not None and not group_alive(proc)
        except OSError:
            receipt['process_closure_uncertain'] = True
    return receipt


def main(argv=None):
    began_ns = time.monotonic_ns()
    began = began_ns / 1e9
    deadline_ns = began_ns + int(BOUND*1e9)
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--owned-name')
    parser.add_argument('--cidfile')
    parser.add_argument('--episode-deadline-monotonic-ns', type=int)
    args, native = parser.parse_known_args(argv)
    if args.episode_deadline_monotonic_ns is not None:
        parent_deadline(args.episode_deadline_monotonic_ns)
        deadline_ns = min(deadline_ns, args.episode_deadline_monotonic_ns)
    deadline = deadline_ns / 1e9
    validate_options(native)  # Before any Docker action.
    require((args.owned_name is None) == (args.cidfile is None), 'owned name and CID required together')
    name = args.owned_name or 'esp-sdr-ble-primary-timed-source-' + uuid.uuid4().hex
    validate_name(name)
    if args.cidfile is not None:
        validate_cidfile(args.cidfile)
    cancelled = False
    def cancel(*_):
        nonlocal cancelled
        cancelled = True
    previous = {s: signal.signal(s, cancel) for s in (signal.SIGINT, signal.SIGTERM)}
    proc = None
    docker = env = None
    image_id = None
    code = 2
    receipt = {'kind': 'source_container_closed', 'source_profile': PROFILE,
               'owned_container_name': name, 'preloaded_image_reused': True,
               'source_controller_cleanup_verified_by_wrapper': False,
               'owned_container_removed': False, 'owned_group_closed': False,
               'force_removal_required': False, 'forced_cleanup_required': False,
               'wrapper_started_monotonic_ns': int(began * 1e9),
               'wrapper_deadline_monotonic_ns': deadline_ns}
    try:
        docker, env = runtime()
        archive = env.get('BLE_PRIMARY_TIMED_IMAGE')
        tag = env.get('BLE_PRIMARY_TIMED_IMAGE_TAG')
        executable = env.get('BLE_PRIMARY_TIMED_PYTHON')
        entrypoint = env.get('BLE_PRIMARY_TIMED_ENTRYPOINT')
        image_id = resolve_source_image(archive, tag, env.get('BLE_PRIMARY_TIMED_PRELOADED_IMAGE_ID'),
                                       executable, entrypoint, docker=docker, env=env, deadline=deadline)
        require(container_absent(name, docker, env, deadline), 'owned name already exists')
        # Last parser value is the exact inherited minimum, never an argv override.
        native = [*native, '--parent-deadline-monotonic-ns', str(deadline_ns)]
        command = source_command(name, image_id, executable, entrypoint, native, docker=docker, cidfile=args.cidfile)
        remaining(deadline, 1)
        require(not cancelled, 'cancelled before source spawn')
        proc = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        receipt.update(owned_pid=proc.pid, owned_pgid=proc.pid)
        natural = wait_natural(proc, deadline, lambda: cancelled)
        require(natural and not cancelled, 'owned source did not close naturally')
        receipt['owned_group_closed'] = True
        receipt['owned_container_removed'] = container_absent(name, docker, env, deadline)
        require(receipt['owned_container_removed'], 'owned container remains after normal exit')
        if args.cidfile is not None:
            path = Path(args.cidfile)
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600 and
                    info.st_uid == os.getuid(), 'private actual CID missing')
            raw = path.read_bytes()
            require(re.fullmatch(b'[0-9a-f]{64}\n?', raw) is not None, 'actual CID malformed')
            receipt['owned_container_id'] = raw.decode().strip()
        remaining(deadline, 1)
        require(not cancelled, 'cancelled after source closure')
        code = proc.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        receipt['failure_kind'] = type(error).__name__
    finally:
        # Never touch an existing container when refusal happened before Popen.
        try:
            if proc is not None and (not receipt['owned_group_closed'] or not receipt['owned_container_removed']):
                receipt.update(cleanup_owned(name, proc, docker, env))
                receipt['force_removal_required'] = True
                code = 2
            receipt.update(interrupted=cancelled, image_id=image_id, wrapper_terminal_monotonic_ns=time.monotonic_ns())
            if cancelled or receipt['forced_cleanup_required'] or time.monotonic_ns() >= deadline_ns:
                code = 2
            receipt['wrapper_exit_code'] = code
            print(json.dumps(receipt, sort_keys=True), flush=True)
            if time.monotonic_ns() >= deadline_ns or cancelled:
                code = 2
                receipt.update(wrapper_exit_code=2, interrupted=cancelled,
                               failure_kind='terminal_output_deadline_or_cancel',
                               wrapper_terminal_monotonic_ns=time.monotonic_ns())
                print(json.dumps(receipt, sort_keys=True), flush=True)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    return code


if __name__ == '__main__':
    raise SystemExit(main())

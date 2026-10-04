#!/usr/bin/env python3
"""One guarded RAM-only synthetic USB trial; recovery verifies unchanged flash.

Only the exclusive hardware operator runs run/recover. Help/tests are inert.
No flash, OTP or FPGA write is admitted. All identity/raw/log data stays private.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import uuid

import preserve_forgix as preserve
from forgix_usb_ram_capture import reject_pending_finalization
from demo_esp_sdr import Cancelled, OwnedHardwareClosureError, defer_spawn_cancellation, stop_process
from forgix_usb_ram_artifact import inspect_elf

ROOT = Path(__file__).resolve().parents[1]
FLASH_BYTES = 2097152
BASELINE = '72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4'
ELF_SHA = '6808b8145aada14b53cb0f46bb7379ecc80cb59181c3dd381555f8b934b58784'
MANIFEST_SHA = '832086100c1256eef53ec7ca15a10b5414c5e57e1847af4fcbe7f8ea4c1b1da3'
PROFILE_SOURCE_SHA = 'd560280bd4c12f2dda3a7312314a0abc968ac2cc4309793709aa4da584bac7ce'
PROTOCOL = 'docs/research/forgix-usb-ram-trial-protocol.md'
RATES = (65536, 262144, 786432)


def requested_rate(args):
    rate = getattr(args, 'rate', 65536)
    require(type(rate) is int and rate in RATES, 'Unsupported payload rate')
    return rate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise preserve.PreservationError(message)


def no_symlinks(path):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlinked private/input path refused')
    return path


def private_file(path, area):
    path = no_symlinks(path)
    require(path.is_relative_to(ROOT/area), 'Private input escaped its ignored repository area')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == os.getuid(), 'Private input must be owned regular0600')
    return path


def original_binding(binding, first, second):
    binding = private_file(binding, '.scratch')
    record = json.loads(binding.read_text())
    entries = record.get('entries')
    require(type(record.get('matching_recent_enumerations')) is int and record['matching_recent_enumerations'] == 3 and record.get('same_serial_across_application_rom_application') is True and type(entries) is list and len(entries) == 3, 'Prior factory/ROM/factory continuity receipt required')
    ids = [e.get('normalized_serial_sha256') for e in entries]
    require(all(type(x) is str and re.fullmatch('[0-9a-f]{64}', x) for x in ids) and len(set(ids)) == 1, 'Prior USB continuity does not bind one identity')
    paths = [private_file(p, 'backups') for p in (first, second)]
    require(paths[0] != paths[1], 'Independent preserved copies required')
    for p in paths:
        require(p.stat().st_size == FLASH_BYTES and sha(p) == BASELINE, 'Original full flash backup does not match preserved baseline')
    return {'uid_sha256': ids[0], 'binding_path': str(binding), 'binding_sha256': sha(binding), 'baseline_paths': [str(p) for p in paths], 'baseline_sha256': BASELINE}


def artifact_check(directory):
    folder = no_symlinks(directory)
    require(folder.is_dir(), 'Artifact directory required')
    elf, manifest_path = folder/'forgix_usb_ram.elf', folder/'manifest.json'
    require(not elf.is_symlink() and not manifest_path.is_symlink(), 'Artifact symlink refused')
    require(stat.S_ISREG(elf.stat().st_mode) and 0 < elf.stat().st_size <= 4*1024*1024 and stat.S_ISREG(manifest_path.stat().st_mode) and manifest_path.stat().st_size <= 1024*1024, 'Bounded regular artifact inputs required')
    require(sha(elf) == ELF_SHA and sha(manifest_path) == MANIFEST_SHA, 'Only independently reviewed historical build004 is admitted')
    manifest = json.loads(manifest_path.read_text())
    require(manifest['status'] == 'built_layout_guard_passed' and manifest['inputs_unchanged_after_build'] is True and manifest['build_source_sha256'] == PROFILE_SOURCE_SHA, 'Artifact build provenance invalid')
    for name, digest in manifest['source_sha256'].items():
        require(type(name) is str and '..' not in Path(name).parts and not Path(name).is_absolute(), 'Invalid committed source path')
        committed = subprocess.check_output(['git', 'show', manifest['source_commit']+':'+name], cwd=ROOT)
        require(hashlib.sha256(committed).hexdigest() == digest, 'Historical committed source differs')
        if name.startswith('firmware/') or name in ('tools/forgix_usb_ram_artifact.py', 'tools/build_forgix_usb_ram.py'):
            require(sha(ROOT/name) == digest, 'Current firmware/guard differs from reviewed artifact')
    for name, digest in manifest['artifact_sha256'].items():
        require(Path(name).name == name and not (folder/name).is_symlink() and sha(folder/name) == digest, 'Artifact export hash mismatch')
    layout = inspect_elf(elf.read_bytes())
    require(layout['allocated_load_bytes'] == manifest['layout']['allocated_load_bytes'], 'ELF layout mismatch')
    return {'elf': str(elf), 'elf_sha256': ELF_SHA, 'manifest_sha256': MANIFEST_SHA, 'source_commit': manifest['source_commit'], 'build_source_sha256': PROFILE_SOURCE_SHA, 'layout_bytes': layout['allocated_load_bytes']}


def archive_image_id(archive, tag):
    with tarfile.open(archive, 'r:*') as data:
        member = data.getmember('manifest.json')
        require(member.isfile() and member.size <= 65536, 'Bounded image manifest required')
        rows = json.loads(data.extractfile(member).read())
        require(len(rows) == 1 and tag in rows[0].get('RepoTags', []), 'Nix archive tag mismatch')
        require(type(rows[0]['Config']) is str and not Path(rows[0]['Config']).is_absolute() and '..' not in Path(rows[0]['Config']).parts, 'Invalid image config path')
        config = data.getmember(rows[0]['Config'])
        require(config.isfile() and config.size <= 1024*1024, 'Bounded image config required')
        expected_id = 'sha256:'+hashlib.sha256(data.extractfile(config).read()).hexdigest()
    return expected_id


def pinned_picotool_version(tool):
    result = subprocess.run([str(tool), 'version'], capture_output=True,
                            text=True, check=True, timeout=10)
    banner = (result.stdout + '\n' + result.stderr).strip()
    require(re.fullmatch(r'picotool v2\.3\.1(?: \([^\r\n]*\))?', banner),
            'Pinned picotool v2.3.1 banner required')
    return banner


def image_check(tool, image_id):
    tool = Path(tool).resolve()
    require(tool.is_relative_to('/nix/store') and tool.name == 'picotool', 'Nix picotool required')
    archive = Path(os.environ.get('PICOTOOL_USB_IMAGE', '')).resolve()
    tag = os.environ.get('PICOTOOL_USB_IMAGE_TAG')
    require(archive.is_relative_to('/nix/store') and archive.is_file() and tag, 'Locked Nix image archive/tag required')
    require(type(image_id) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', image_id), 'Explicit loaded immutable image ID required')
    expected_id = archive_image_id(archive, tag)
    require(expected_id == image_id, 'Image ID does not belong to Nix archive')
    inspected = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], timeout=10))
    require(len(inspected) == 1 and inspected[0].get('Id') == image_id, 'Loaded local tag/immutable image mismatch; no load or fallback')
    python = Path(sys.executable).resolve()
    require(python.is_relative_to('/nix/store'), 'Nix Python required')
    sdk = Path('/nix/store/zzdqq5jiwbislr6v99spq09vmc9yiib1-pico-sdk-2.2.0-tinyusb-pinned')
    require(subprocess.check_output(['nix', 'hash', 'path', str(sdk)], timeout=60, text=True).strip() == 'sha256-X9mPMzmeJzuhHp7VbTc8BLoF1LE41YOLxK0dAwgYEds=', 'Reviewed actual SDK NAR mismatch')
    compiler = Path('/nix/store/8im8fi1g72flhxjqarv43ykdcdjcl5sw-gcc-arm-embedded-15.3.rel1/bin/arm-none-eabi-gcc')
    require(sha(compiler) == '9a5dafde9b51f5f733a4a95616f0eff681f2b90c6323eabe91c6d140142eac04', 'Historical compiler binary mismatch')
    closure = json.loads(subprocess.check_output(['nix', 'path-info', '--json', '--recursive', str(tool.parent.parent), str(python.parent.parent), str(sdk), str(compiler.parent.parent)], timeout=60))
    paths = list(closure) if type(closure) is dict else [row['path'] for row in closure]
    subprocess.run(['nix-store', '--verify-path', *paths], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=120)
    version = pinned_picotool_version(tool)
    return {'image_id': image_id, 'image_archive_sha256': sha(archive), 'image_tag': tag, 'picotool_executable': str(tool), 'picotool_executable_sha256': sha(tool), 'python_executable': str(python), 'python_executable_sha256': sha(python), 'nix_recursive_closure': closure, 'closure_contents_verified': True,
            'sdk_nar_verified': True, 'sdk_file_sha256': {name: sha(sdk/name) for name in ('src/rp2_common/pico_runtime_init/runtime_init.c', 'src/rp2_common/pico_crt0/rp2350/memmap_no_flash.ld', 'lib/tinyusb/src/tusb.c')}, 'compiler_executable_sha256': sha(compiler), 'picotool_version_banner': version}


def freeze_inputs():
    names = {'tools/forgix_usb_ram_trial.py', 'tools/forgix_usb_ram_capture.py', 'Taskfile.yml', 'flake.nix', 'flake.lock', '.gitignore', PROTOCOL}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            p = Path(filename).resolve()
            if p.is_relative_to(ROOT/'tools'):
                names.add(str(p.relative_to(ROOT)))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    result = {}
    for name in sorted(names):
        p = ROOT/name
        recorded = subprocess.check_output(['git', 'show', head+':'+name], cwd=ROOT)
        require(p.read_bytes() == recorded, 'Execution inputs must be committed and unchanged')
        result[name] = sha(p)
    return {'source_commit': head, 'inputs': result}


def check_inputs(frozen):
    require(all(sha(ROOT/name) == digest for name, digest in frozen['inputs'].items()), 'Frozen execution input changed')


def ram_load_args(target, path):
    require(target.pid == preserve.BOOT_PID and Path(path).name == 'ram-diagnostic.elf', 'Load requires selected ROM and dedicated verified ELF')
    return ['load', '-v', '-x', str(path), '-t', 'elf', '--bus', str(target.bus), '--address', str(target.address)]


def remove_container(name):
    require(re.fullmatch(r'esp-sdr-forgix-[0-9a-f]{32}', name), 'Owned container name required')
    result = subprocess.run(['docker', 'rm', '--force', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    if result.returncode == 0:
        return True
    check = subprocess.run(['docker', 'ps', '--all', '--filter', 'name=^'+name+'$', '--format', '{{.ID}}'], capture_output=True, timeout=10)
    return check.returncode == 0 and not check.stdout.strip()


def remaining(deadline, maximum):
    value = min(maximum, deadline-time.monotonic())
    require(value > 0, 'Absolute600-second hardware-session budget exhausted')
    return value


def mark_unclosed(resources):
    folder = no_symlinks(ROOT/'.scratch')
    folder.mkdir(mode=0o700, exist_ok=True)
    path = folder/'forgix-usb-ram-unclosed.json'
    if not path.exists():
        fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'owned_hardware_processes_closed': False, 'resources_private': resources}, stream)


def recovery_admission(prior, binding):
    reject_pending_finalization(ROOT)
    require(prior.get('binding') == binding, 'Recovery must use persisted original binding')
    require(prior.get('owned_hardware_processes_closed') is True, 'Prior owned closure must be verified before recovery; inspect exact retained resources first')
    require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(), 'Unverified owned resource marker blocks further device access')


def owned_worker(command, log, lockfd, timeout):
    reject_pending_finalization(ROOT)
    proc = None
    try:
        fd = os.open(log, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            with defer_spawn_cancellation():
                proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lockfd,))
            return proc.wait(timeout=timeout)
    finally:
        try:
            stop_process(proc, grace_seconds=3)
        except BaseException as error:
            try:
                mark_unclosed({'process_group': proc.pid if proc else None, 'private_log': str(log)})
            except BaseException:
                pass
            raise OwnedHardwareClosureError('Owned worker closure unverified; persistence may also have failed') from error


def bounded_query(inspector, target, store, label, lockfd, deadline, runner):
    reject_pending_finalization(ROOT)
    query_deadline = time.monotonic() + remaining(deadline, 15)
    check_inputs(runner.frozen)
    while True:
        remaining(query_deadline, 1)
        inspector.confirm(target)
        inspector.port = Path(fresh_tty('3-3', '2e8a', preserve.FACTORY_PID))
        if os.access(inspector.port, os.R_OK | os.W_OK, effective_ids=True):
            break
        time.sleep(min(.05, remaining(query_deadline, .05)))
    check_inputs(runner.frozen)
    inspector.confirm(target)
    request = {'topology': inspector.topology, 'port': str(inspector.port), 'target': target.__dict__, 'label': label, 'lockfd': lockfd}
    path = store.json(label+'-query-request.json', request)
    try:
        code = owned_worker([sys.executable, str(Path(__file__).resolve()), '_query', '--request', str(path)], store.path/(label+'-query.log'), lockfd, remaining(query_deadline, 15))
    except OwnedHardwareClosureError:
        runner.hardware_process_closed = False
        raise
    remaining(query_deadline, 1)
    require(code == 0, 'Bounded factory query failed; private transcript retained')
    return json.loads((store.path/(label+'-query-result.json')).read_text())


def query_worker():
    reject_pending_finalization(ROOT)
    cli = argparse.ArgumentParser(description='Internal bounded factory query; inherited lock required')
    cli.add_argument('--request', type=Path, required=True)
    a = cli.parse_args(sys.argv[2:])
    os.umask(0o077)
    request_path = private_file(a.request, 'backups')
    request = json.loads(request_path.read_text())
    from forgix_usb_ram_capture import inherited_operator_lock
    inherited_operator_lock(request['lockfd'], ROOT/'.scratch/esp-demo.lock')
    target = preserve.USBTarget(**request['target'])
    require(target.topology == request['topology'] == '3-3' and target.pid == preserve.FACTORY_PID, 'Exact factory target required')
    require(request['label'] in ('initial', 'returned', 'returned-after-ram'), 'Internal query label invalid')
    inspector = preserve.Inspector('3-3', request['port'])
    inspector.identity_hash = target.serial_sha256
    store = object.__new__(preserve.PrivateStore)
    store.path = request_path.parent
    def cancel(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, cancel)
    result = preserve.query_factory(inspector, target, store, request['label'])
    store.json(request['label']+'-query-result.json', result)
    return 0


class OwnedPicotool:
    """New exact RAM-load admission; upstream preservation whitelist unchanged."""
    def __init__(self, tool, inspector, store, image, frozen, deadline=None):
        self.tool, self.inspector, self.store, self.image, self.frozen = tool, inspector, store, image, frozen
        self.steps = []
        self.hardware_process_closed = True
        self.provenance = {'image_id': image, 'picotool_executable_sha256': sha(tool)}
        self.deadline = deadline if deadline is not None else time.monotonic()+600

    def load_args(self, target, backup, path):
        require(sha(backup) == ELF_SHA, 'RAM image changed before load')
        return ram_load_args(target, path)

    def run(self, operation, target, backup=None):
        reject_pending_finalization(ROOT)
        require(self.hardware_process_closed, 'Unverified owned closure blocks device access')
        check_inputs(self.frozen)
        if backup is not None:
            backup = Path(backup)
            require(backup.parent == self.store.path and not backup.is_symlink() and stat.S_ISREG(backup.stat().st_mode) and stat.S_IMODE(backup.stat().st_mode) == 0o600, 'Operation file escaped private regular0600 store')
        path = Path('/private')/backup.name if backup is not None else None
        if operation == 'load':
            args = self.load_args(target, backup, path)
        else:
            args = preserve.picotool_args(operation, target, path)
        name = 'esp-sdr-forgix-'+uuid.uuid4().hex
        command = preserve.docker_command(self.tool, self.image, target, self.store.path, args, name, os.getuid())
        self.inspector.confirm(target)
        timeout = remaining(self.deadline, 180)
        record = {'operation': operation, 'started_at_utc': preserve.utc(), 'command': command}
        proc, code, failure = None, None, None
        self.hardware_process_closed = False
        try:
            with (self.store.path/f'command-{len(self.steps):02d}.log').open('xb') as log:
                with defer_spawn_cancellation():
                    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                code = proc.wait(timeout=timeout)
                remaining(self.deadline, 1)
        except BaseException as error:
            failure = error
        finally:
            removed = False
            try:
                removed = remove_container(name)
            except BaseException as error:
                failure = failure or error
            finally:
                try:
                    stop_process(proc, grace_seconds=3)
                    self.hardware_process_closed = removed
                except BaseException as error:
                    failure = failure or error
                    self.hardware_process_closed = False
            record.update(exit_code=code, finished_at_utc=preserve.utc(), hardware_process_closed=self.hardware_process_closed)
            record.update(owned_container=name, owned_process_group=proc.pid if proc else None)
            if not self.hardware_process_closed:
                try:
                    mark_unclosed({'container': name, 'process_group': proc.pid if proc else None, 'private_store': str(self.store.path)})
                except BaseException:
                    record['unclosed_marker_persistence_failed'] = True
            if failure:
                record['error_type'] = type(failure).__name__
            try:
                self.store.json(f'step-{len(self.steps)+1:02d}.json', record)
            except BaseException:
                if not self.hardware_process_closed:
                    raise OwnedHardwareClosureError('Owned container/group closure unverified and receipt persistence failed')
                raise
            self.steps.append({k: record[k] for k in ('operation', 'exit_code', 'started_at_utc', 'finished_at_utc', 'hardware_process_closed')})
        if not self.hardware_process_closed:
            raise OwnedHardwareClosureError('Owned group/container closure remains unverified')
        if failure:
            raise failure
        require(code == 0, 'Picotool operation failed; private logs retained')
        return (self.store.path/f'command-{len(self.steps)-1:02d}.log').read_text(errors='replace')


def watched_factory(inspector, bus, until, runner=None):
    next_log = time.monotonic()
    while time.monotonic() < until:
        try:
            return inspector.target(preserve.FACTORY_PID, bus)
        except (OSError, preserve.PreservationError):
            if runner is not None:
                try:
                    rom = inspector.target(preserve.BOOT_PID, bus)
                except (OSError, preserve.PreservationError):
                    pass
                else:
                    runner.run('return', rom)
                    return inspector.wait(preserve.FACTORY_PID, bus)
            if time.monotonic() >= next_log:
                print('Waiting for the finite RAM image to return to the preserved factory application.', flush=True)
                next_log = time.monotonic()+10
            time.sleep(.1)
    raise preserve.PreservationError('Factory return not observed; unplug/replug USB, then use recover. No image rewrite attempted')


def fresh_tty(topology, vid, pid, product=None, sys_root=Path('/sys'), dev_root=Path('/dev'), wait_missing=False):
    reject_pending_finalization(ROOT)
    usb = (sys_root/'bus/usb/devices'/topology).resolve(strict=True)
    require((usb/'idVendor').read_text().strip().lower() == vid and (usb/'idProduct').read_text().strip().lower() == pid, 'TTY selection requires expected selected USB mode')
    if product is not None:
        require((usb/'product').read_text().strip() == product, 'Diagnostic product mismatch')
    matches = []
    for tty in (sys_root/'class/tty').glob('ttyACM*'):
        try:
            node = (tty/'device').resolve(strict=True)
            ancestors = [p for p in (node, *node.parents) if (p/'idVendor').exists()]
            if ancestors and ancestors[0] == usb:
                matches.append(dev_root/tty.name)
        except OSError:
            continue
    if not matches and wait_missing:
        raise FileNotFoundError('Selected CDC interface is not ready')
    require(len(matches) == 1, 'Fresh unique CDC tty on exact selected USB node required')
    require(stat.S_ISCHR(matches[0].stat().st_mode), 'Selected tty must be a character device')
    return str(matches[0])


class BudgetInspector(preserve.Inspector):
    def __init__(self, topology, port, deadline):
        super().__init__(topology, port)
        self.deadline = deadline

    def wait(self, pid, bus, seconds=30):
        return super().wait(pid, bus, remaining(self.deadline, seconds))


def ready_diagnostic_tty(deadline):
    while True:
        remaining(deadline, 1)
        try:
            port = fresh_tty('3-3', 'cafe', '4011', 'Forgix USB RAM diagnostic v1')
            require(os.access(port, os.R_OK | os.W_OK, effective_ids=True), 'Diagnostic tty permissions not ready')
        except (OSError, preserve.PreservationError):
            time.sleep(remaining(deadline, .1))
        else:
            remaining(deadline, 1)
            return port


def full_preservation(inspector, tool, store, image, frozen, lockfd, deadline):
    reject_pending_finalization(ROOT)
    runner = OwnedPicotool(tool, inspector, store, image, frozen, deadline)
    try:
        receipt, error = preserve.preserve(inspector, runner, store, FLASH_BYTES,
            query=lambda i, t, s, label: bounded_query(i, t, s, label, lockfd, deadline, runner))
    except BaseException as error:
        if not runner.hardware_process_closed:
            raise OwnedHardwareClosureError('Preservation closure unverified despite receipt failure') from error
        raise
    if not runner.hardware_process_closed:
        raise OwnedHardwareClosureError('Preservation owned closure unverified')
    if error:
        raise error
    require(receipt['backups']['sha256'] == BASELINE and receipt['independent_device_verify'] is True and receipt['status'] == 'preserved_and_returned', 'Current full flash differs from preserved original')
    remaining(deadline, 1)
    return receipt, runner


def spawn_collector(args, private, lockfd, source_sha, deadline):
    rate = requested_rate(args)
    command = [sys.executable, str(ROOT/'tools/forgix_usb_ram_capture.py'), '--usb-topology', '3-3', '--port', args.diagnostic_port, '--operator-lock-fd', str(lockfd), '--operator-lock-path', str(ROOT/'.scratch/esp-demo.lock'), '--build-source-sha256', source_sha, '--rate', str(rate), '--output', str(private/'capture')]
    code = owned_worker(command, private/'collector.log', lockfd, remaining(deadline, 100))
    remaining(deadline, 1)
    require(code == 0, 'Collector failed; retained private prefix')
    capture = json.loads((private/'capture/manifest.json').read_text())
    echoed = capture.get('requested_payload_Bps')
    require(type(echoed) is int and echoed == rate, 'Collector requested rate differs')
    require(capture.get('status') == 'complete_integrity_verified' and capture.get('raw_persistence_verified') is True and capture.get('raw_saved_matches_received_length') is True and capture.get('loss_accounted') is True and capture.get('verified_no_record_loss') is True, 'Zero-loss collector terminal receipt not verified; drops retained as failed qualification')
    return capture


def run_session(args, lockfd, record, frozen, binding, artifact, image):
    """Injectable through module helpers in synthetic lifecycle tests."""
    record['requested_payload_Bps'] = requested_rate(args)
    deadline = time.monotonic()+600
    initial_port = fresh_tty('3-3', '2e8a', preserve.FACTORY_PID)
    require(args.factory_port is None or str(Path(args.factory_port).resolve()) == initial_port, 'Initial explicit factory port does not match fresh identity-selected tty')
    args.factory_port = initial_port
    inspector = BudgetInspector('3-3', args.factory_port, deadline)
    inspector.identity_hash = binding['uid_sha256']
    tool = image['picotool_executable']
    private = Path(args.private_dir)
    load_runner = None
    load_attempted = False
    factory_bus = None
    load_started = None
    error = None
    factory_until = deadline
    record['absolute_hardware_session_seconds'] = 600
    record['owned_hardware_processes_closed'] = True
    try:
        target = inspector.target(preserve.FACTORY_PID)
        factory_bus = target.bus
        pre = preserve.PrivateStore(private/'before', ROOT/'backups')
        record['before'], _ = full_preservation(inspector, tool, pre, image['image_id'], frozen, lockfd, deadline)
        loading = preserve.PrivateStore(private/'load', ROOT/'backups')
        loading.create('ram-diagnostic.elf', Path(artifact['elf']).read_bytes())
        load_runner = OwnedPicotool(tool, inspector, loading, image['image_id'], frozen, deadline)
        # Lost acknowledgement can still have changed mode; set before request.
        load_attempted = True
        load_started = time.monotonic()
        load_runner.run('boot', inspector.target(preserve.FACTORY_PID, factory_bus))
        rom = inspector.wait(preserve.BOOT_PID, factory_bus, remaining(deadline, 30))
        factory_until = min(deadline, time.monotonic()+320)
        # Anchor finite return allowance to actual load attempt/completion.
        load_runner.run('load', rom, loading.path/'ram-diagnostic.elf')
        record['load_completed_monotonic_ns'] = time.monotonic_ns()
        factory_until = min(deadline, time.monotonic()+140)
        diag_until = time.monotonic()+min(20, remaining(deadline, 20))
        args.diagnostic_port = ready_diagnostic_tty(diag_until)
        record['capture'] = spawn_collector(args, private, lockfd, artifact['build_source_sha256'], deadline)
        record['collector_group_closed'] = True
    except BaseException as exc:
        error = exc
        record['failure_type'] = type(exc).__name__
        if isinstance(exc, OwnedHardwareClosureError):
            record['collector_group_closed'] = False
            record['owned_hardware_processes_closed'] = False
    finally:
        args.cleaning = True
        if load_attempted:
            try:
                require(record.get('collector_group_closed', True) and load_runner.hardware_process_closed, 'Unknown hardware closure blocks recovery')
                # A failed load may still leave ROM active. Admit only normal reboot.
                try:
                    factory = inspector.target(preserve.FACTORY_PID, factory_bus)
                except (OSError, preserve.PreservationError):
                    try:
                        rom = inspector.target(preserve.BOOT_PID, factory_bus)
                    except (OSError, preserve.PreservationError):
                        factory = watched_factory(inspector, factory_bus, factory_until, load_runner)
                    else:
                        load_runner.run('return', rom)
                        factory = inspector.wait(preserve.FACTORY_PID, factory_bus, remaining(deadline, 30))
                bounded_query(inspector, factory, load_runner.store, 'returned-after-ram', lockfd, deadline, load_runner)
                post = preserve.PrivateStore(private/'after', ROOT/'backups')
                record['after'], _ = full_preservation(inspector, tool, post, image['image_id'], frozen, lockfd, deadline)
                record['original_flash_and_factory_verified'] = True
            except BaseException as exc:
                record['recovery_failure_type'] = type(exc).__name__
                record['manual_usb_power_cycle_required'] = True
                if isinstance(exc, OwnedHardwareClosureError):
                    record['owned_hardware_processes_closed'] = False
                error = error or exc
        record['status'] = 'complete' if error is None else 'failed'
        try:
            check_inputs(frozen)
        except BaseException as exc:
            record['status'] = 'failed'
            error = error or exc
        if time.monotonic() >= deadline:
            record['status'] = 'failed'
            error = error or preserve.PreservationError('Final session acceptance exceeded absolute budget')
        record['actual_hardware_session_seconds'] = time.monotonic()-(deadline-600)
        record['flash_writes'] = 0
        record['fpga_programming_requested'] = False
    if error:
        raise error
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('run', 'recover'), default='run')
    parser.add_argument('--rate', type=int, choices=RATES, default=65536, help='Payload bytes/s for one run')
    parser.add_argument('--factory-port', help='Optional constraint on initial factory tty only; future tty is identity-derived')
    parser.add_argument('--private-dir', required=True, type=Path)
    parser.add_argument('--prior-session', type=Path)
    parser.add_argument('--binding', required=True, type=Path)
    parser.add_argument('--baseline-a', required=True, type=Path)
    parser.add_argument('--baseline-b', required=True, type=Path)
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--image-id', default=os.environ.get('PICOTOOL_CONTAINER_IMAGE_ID'))
    a = parser.parse_args()
    if a.action == 'run' and not a.artifact:
        parser.error('run requires reviewed artifact')
    if a.action == 'recover' and not a.prior_session:
        parser.error('recover requires original private session receipt')
    os.umask(0o077)
    a.cleaning = False
    def cancel(signum, frame):
        if a.cleaning:
            print('Cancellation deferred during bounded factory/full-flash verification.', flush=True)
        else:
            raise Cancelled('Trial cancelled')
    handlers = {s: signal.signal(s, cancel) for s in (signal.SIGINT, signal.SIGTERM)}
    private = None
    record = {'kind': 'RAM-only synthetic USB trial', 'status': 'failed', 'flash_writes': 0, 'fpga_programming_requested': False}
    if a.action == 'run':
        record['requested_payload_Bps'] = a.rate
    code = 2
    try:
        require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(), 'Unverified owned resource marker blocks all device access')
        reject_pending_finalization(ROOT)
        require(not (ROOT/'.scratch/forgix-spi-active.json').exists(), 'Unresolved register session lease blocks all device access')
        binding = original_binding(a.binding, a.baseline_a, a.baseline_b)
        artifact = artifact_check(a.artifact) if a.action == 'run' else None
        image = image_check(shutil.which('picotool') or '', a.image_id)
        frozen = freeze_inputs()
        path = no_symlinks(a.private_dir)
        require(path.is_relative_to(ROOT/'backups') and path != ROOT/'backups', 'Fresh ignored backups child required')
        require(subprocess.run(['git', 'check-ignore', '--quiet', str(path)], cwd=ROOT).returncode == 0, 'Private output must be Git ignored')
        private = preserve.PrivateStore(path, ROOT/'backups')
        record.update(binding=binding, artifact=artifact, image=image, execution=frozen)
        private.json('preflight.json', record)
        lockpath = no_symlinks(ROOT/'.scratch/esp-demo.lock')
        lockpath.parent.mkdir(exist_ok=True, mode=0o700)
        with os.fdopen(os.open(lockpath, os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW, 0o600), 'a+b') as lock:
            lockstat = os.fstat(lock.fileno())
            require(stat.S_ISREG(lockstat.st_mode) and stat.S_IMODE(lockstat.st_mode) == 0o600 and lockstat.st_uid == os.getuid(), 'Shared operator lock must be owned private regular0600')
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            # Another operator can fail while our offline preflight runs. The
            # shared lock serializes this final admission with its marker write.
            require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(), 'Unverified owned resource marker blocks all device access')
            reject_pending_finalization(ROOT)
            require(not (ROOT/'.scratch/forgix-spi-active.json').exists(), 'Unresolved register session lease blocks all device access')
            check_inputs(frozen)
            if a.action == 'recover':
                prior = json.loads(private_file(a.prior_session, 'backups').read_text())
                recovery_admission(prior, binding)
                a.cleaning = True
                recovery_deadline = time.monotonic()+600
                inspector = BudgetInspector('3-3', fresh_tty('3-3', '2e8a', preserve.FACTORY_PID), recovery_deadline)
                inspector.identity_hash = binding['uid_sha256']
                record['after'], _ = full_preservation(inspector, image['picotool_executable'], preserve.PrivateStore(path/'after', ROOT/'backups'), image['image_id'], frozen, lock.fileno(), recovery_deadline)
                record.update(status='recovered_and_verified', original_flash_and_factory_verified=True, owned_hardware_processes_closed=True)
            else:
                run_session(a, lock.fileno(), record, frozen, binding, artifact, image)
        code = 0
    except BaseException as exc:
        record.update(status='failed', failure_type=type(exc).__name__)
        if isinstance(exc, OwnedHardwareClosureError) or (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists():
            record['owned_hardware_processes_closed'] = False
    finally:
        for s, handler in handlers.items():
            signal.signal(s, handler)
        if private:
            private.json('session.json', record)
    print(json.dumps({k: record.get(k) for k in ('status', 'failure_type', 'original_flash_and_factory_verified', 'manual_usb_power_cycle_required', 'flash_writes', 'fpga_programming_requested')}))
    return code


if __name__ == '__main__':
    raise SystemExit(query_worker() if len(sys.argv)>1 and sys.argv[1]=='_query' else main())

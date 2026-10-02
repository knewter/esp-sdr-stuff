#!/usr/bin/env python3
"""Fixed hardware-free vendor compiler fixture; never programs a device."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
import xml.etree.ElementTree as ET

import efinity_bootstrap as b

VERSION = '2026.1.132'
ARCHIVE_SHA = '8b09bf853cb4c586ef166ae0fc07e8753f58288f7d640b94a236f708f7a069e9'
RUNNER_SHA = 'f1d437afeb0b905b957ea0076698b3715888f6ae5ce1b2b1370f280102d21f03'
INPUTS = {
    'pt_demo.xml': ('b2f59888c88f97e415532d4b4ec0524dc07440a74b34ad6375c9e0bb395f8124', 1917),
    'pt_demo.peri.xml': ('c60daad8ee4d191abb70ffb887777897852c66dc0d3d7dc7aee14efedffb5e28', 8536),
    'pt_demo.v': ('54a9ca2898c6047020813c7f269fd0bbac24e2837ec258e186403d82528bd733', 3573),
    'pt_demo.sdc': ('4873e59057740a0553bccadd2a9092b55316899731f1b007de2ad4c8d7149f00', 2927),
}
STAGES = ('map', 'interface', 'pnr', 'pgm')
FLOW = ['pt_demo.xml', '--flow', 'compile', '--timeout', '300']
MAX_LOG = 64 * 1024**2
NS = '{http://www.efinixinc.com/enf_proj}'


def validate_xml(path):
    data = path.read_bytes()
    b.require(len(data) <= 16384 and b'<!DOCTYPE' not in data and b'<!ENTITY' not in data, 'Unexpected fixture XML metadata')
    root = ET.fromstring(data)
    b.require(root.tag == NS + 'project' and root.get('name') == 'pt_demo', 'Unexpected fixture project identity')
    info = root.find(NS + 'device_info')
    b.require(info is not None and [(x.tag.removeprefix(NS), x.get('name')) for x in info] ==
              [('family', 'Trion'), ('device', 'T8F81'), ('timing_model', 'C2')], 'Fixture target must be generic Trion T8F81/C2')
    expected_files = {'design_file': 'pt_demo.v', 'sdc_file': 'pt_demo.sdc', 'inter_file': ''}
    found = {}
    for node in root.iter():
        tag = node.tag.removeprefix(NS)
        if tag.endswith('_file'):
            b.require(tag in expected_files and node.get('name') == expected_files[tag] and tag not in found, 'Unsafe or unexpected fixture input path')
            found[tag] = node.get('name')
        if tag == 'param' and node.get('name') == 'work_dir':
            value = node.get('value', '')
            relative = b.member_path(value)
            b.require(relative.as_posix() in ('work_syn', 'work_pnr'), 'Unsafe fixture work output path')
    b.require(found == expected_files, 'Missing fixed fixture input paths')
    # The factory location/cache attributes are not operational paths: the
    # pinned runner uses the current project XML path and relative filenames.
    # Its clean-project routine prunes location only in the private copied XML.


def private_path(store, value):
    raw = value if value.is_absolute() else store.root / value
    b.require('..' not in raw.parts and raw.is_relative_to(store.root), 'Compiler work path must stay inside this repository')
    for ancestor in (raw, *raw.parents):
        b.require(not ancestor.is_symlink(), 'Compiler private path ancestors must not be symlinks')
        if ancestor == store.root:break
    b.require(not raw.exists(), 'Compiler fixture directory must be fresh; cached outputs cannot be reused')
    path = raw.resolve()
    roots = (store.path / 'compiler-smoke', store.root / '.scratch')
    b.require(any(path.is_relative_to(root) and path != root for root in roots), 'Compiler work must stay in ignored private storage')
    ignored = subprocess.run(['git', '-C', str(store.root), 'check-ignore', '--quiet', str(path)], capture_output=True)
    b.require(ignored.returncode == 0, 'Compiler work must be ignored by Git')
    return path


def prepare(store, private):
    installation, metadata = store.installed()
    b.require(metadata['version'] == VERSION and metadata['software_sha256'] == ARCHIVE_SHA, 'Compiler smoke requires the exact staged full release 2026.1.132')
    runner = installation / 'scripts/efx_run.py'
    b.require(not runner.is_symlink() and b.sha(runner) == RUNNER_SHA, 'Vendor compiler runner bytes differ from the reviewed fixed flow')
    source = installation / 'project/pt_demo'
    b.require(not source.is_symlink(), 'Fixture source directory must not be a symlink')
    for name, (digest, size) in INPUTS.items():
        f = source / name
        b.require(not f.is_symlink() and f.stat().st_size == size and b.sha(f) == digest, 'Shipped fixture input hash or size mismatch')
    validate_xml(source / 'pt_demo.xml')
    b.private_dir(private)
    work = private / 'work'; b.private_dir(work)
    for name, (digest, _) in INPUTS.items():
        b.copy_frozen(source / name, work / name, 16384)
        b.require(b.sha(work / name) == digest, 'Fixture changed while copying')
    b.require(set(x.name for x in work.iterdir()) == set(INPUTS), 'Cached compiler output is present before launch')
    return installation, runner, work


def verify_outputs(work, console, started_ns):
    b.require(console.stat().st_size <= MAX_LOG, 'Compiler console log exceeds verification bound')
    text = re.sub(r'\x1b\[[0-9;]*m', '', console.read_text(errors='replace'))
    markers = re.findall(r'^\s*(map|interface|pnr|pgm|export_bitstream)\s*:\s*(PASS|SKIP|FAIL)\s*$', text, re.M)
    b.require(markers == [(s, 'PASS') for s in STAGES], 'Compiler stages were missing, skipped, repeated or failed')
    stage_log = work / 'outflow/pt_demo.log'
    b.require(stage_log.is_file() and not stage_log.is_symlink() and stage_log.resolve().is_relative_to(work.resolve()) and stage_log.stat().st_nlink == 1 and stage_log.stat().st_size <= MAX_LOG, 'Fresh compiler stage log missing or invalid')
    completed = re.findall(r'^Stage completed: (\S+)\s*$', stage_log.read_text(errors='replace'), re.M)
    b.require(completed == list(STAGES), 'Compiler stage completion log does not match full fixed flow')
    image = work / 'outflow/pt_demo.hex'
    b.require(image.is_file() and not image.is_symlink() and image.stat().st_nlink == 1 and image.resolve().is_relative_to(work.resolve()), 'Fresh fixture bitstream missing or unsafe')
    b.require(0 < image.stat().st_size <= 16 * 1024**2 and image.stat().st_mtime_ns >= started_ns, 'Fixture bitstream is empty, oversized or stale')
    return {'stages': {s: 'passed' for s in STAGES},
            'bitstream': {'file': 'pt_demo.hex', 'bytes': image.stat().st_size, 'sha256': b.sha(image)},
            'optional_binary_export_requested': False}


def harden_outputs(private):
    safe = True
    for parent, dirs, files in os.walk(private, followlinks=False):
        for name in dirs + files:
            f = Path(parent) / name
            mode = f.lstat()
            if stat.S_ISDIR(mode.st_mode):f.chmod(0o700)
            elif stat.S_ISREG(mode.st_mode) and mode.st_nlink == 1:f.chmod(0o600)
            else:safe = False # never chmod external inode via hardlink/symlink
    return safe


def compile_smoke(store, requested):
    b.require(not (store.path / 'runtime-unclosed.json').exists(), 'Inspect unverified vendor group closure before compilation')
    private = private_path(store, requested)
    b.require(shutil.disk_usage(store.path).free >= 1024**3, 'Compiler fixture requires at least 1 GiB free storage')
    receipt = {'kind': 'efinity-offline-compiler-smoke', 'schema': 1, 'status': 'failed',
               'scope': 'Generic shipped software fixture, not connected Forgix gateware',
               'device': 'T8F81', 'timing_model': 'C2', 'version': VERSION,
               'software_sha256': ARCHIVE_SHA, 'runner_sha256': RUNNER_SHA,
               'fixture_sha256': {k: v[0] for k, v in INPUTS.items()},
               'flow': FLOW, 'hardware_opened': False, 'connected_forgix_compile_verified': False,
               'compiler_execution_verified': False, 'license_compile_verified': False,
               'owned_process_group_closed': False, 'vendor_output_private': True}
    try:
        installation, runner, work = prepare(store, private)
        wrapper = shutil.which('forgix-efinity')
        b.require(wrapper is not None, 'Enter the Forgix Nix shell to compile the fixed fixture')
        env = os.environ.copy(); env['LITEX_ENV_EFINITY'] = str(installation)
        console = private / 'console.log'; started_ns = time.time_ns()
        receipt['started_at_unix_ns'] = started_ns
        with console.open('xb') as output:
            os.fchmod(output.fileno(), 0o600)
            code = b.run_owned([wrapper, str(installation / 'bin/python3'), str(runner), *FLOW], env, output, 330, store, cwd=work)
        receipt['owned_process_group_closed'] = True
        receipt['exit_code'] = code
        b.require(code == 0, 'Vendor compiler returned failure; private outputs retained')
        receipt.update(verify_outputs(work, console, started_ns))
        receipt.update(status='passed', compiler_execution_verified=True, license_compile_verified=True)
    except Exception as error:
        receipt['failure_kind'] = type(error).__name__
        receipt['reason'] = str(error) if isinstance(error, b.Refusal) else 'Compiler fixture failed; inspect private outputs'
        receipt['owned_process_group_closed'] = not (store.path / 'runtime-unclosed.json').exists()
        raise
    finally:
        receipt['finished_at_unix_ns'] = time.time_ns()
        if private.exists() and not private.is_symlink():
            # All copied/generated bytes stay inside a private enclosing dir;
            # also remove group/other access from each generated nonlink file.
            safe = harden_outputs(private) if receipt['owned_process_group_closed'] else False
            receipt['private_generated_files_verified'] = safe
            unsafe_success = receipt['status'] == 'passed' and not safe
            if unsafe_success:
                receipt.update(status='failed', compiler_execution_verified=False, license_compile_verified=False,
                               failure_kind='Refusal', reason='Unsafe generated file links or types; private outputs retained')
            b.save(private / 'result.json', receipt)
            if unsafe_success:raise b.Refusal(receipt['reason'])
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private', type=Path, required=True, help='Fresh ignored .scratch or .vendor/efinity/compiler-smoke directory')
    args = parser.parse_args(argv); os.umask(0o077)
    try:
        store = b.Store()
        with store.locked(): receipt = compile_smoke(store, args.private)
        print(json.dumps(receipt)); return 0
    except Exception as error:
        print(json.dumps({'status': 'failed', 'scope': 'Generic software fixture only',
                          'reason': str(error) if isinstance(error, b.Refusal) else 'Offline compiler check failed; private outputs retained',
                          'hardware_opened': False, 'connected_forgix_compile_verified': False}))
        return 2


if __name__ == '__main__': raise SystemExit(main())

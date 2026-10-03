#!/usr/bin/env python3
"""Compile a provisional T8F49/I2 candidate privately; never loads or programs it."""
import argparse
import ast
import inspect
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

import efinity_bootstrap as b
import efinity_compile_smoke as smoke

NAME = 'forgix_candidate'
CLOCK = 'create_clock -name clk32 -period 31.25 [get_ports {clk32}]'
PINS = {'clk32': ['B4'], 'spibone_cs_n': ['G3'], 'spibone_clk': ['F3'], 'spibone_mosi': ['F2']}
GPIO = {'clk32': ('input', 'B4'), 'spibone_cs_n': ('input', 'G3'),
        'spibone_clk': ('input', 'F3'), 'spibone0_mosi0': ('inout', 'F2')}
GENERATED = (NAME + '.v', NAME + '.sdc', 'iface.py', NAME + '_mem.init')
REVISIONS = {'boards': '10debf146d433ce8ac8aedcac84e97d252ff4d5b', 'litex': '8c01073afb71aa0a0709f02f8e24247589e8f5e4'}
PROFILE = {'device': 'T8F49', 'timing_model': 'I2', 'requested_clock_hz': 32000000,
           'configuration_mode': 'passive', 'physical_confirmation': False,
           'programming_admitted': False, 'spi_turnaround_verified': False}


def provenance():
    value = json.loads(os.environ.get('FORGIX_TOOLCHAIN_PROVENANCE', '{}'))
    b.require(all(value.get(k) == v for k, v in REVISIONS.items()), 'Enter the locked Forgix Nix shell')
    return value


def source_hashes():
    root = b.ROOT
    files = ('tools/forgix_fpga_candidate.py', 'tools/efinity_bootstrap.py', 'tools/efinity_compile_smoke.py',
             'Taskfile.yml', 'flake.nix', 'flake.lock', 'nix/forgix-toolchain.nix')
    result = {}
    for name in files:
        data = subprocess.run(['git', '-C', str(root), 'show', 'HEAD:' + name], check=True, capture_output=True).stdout
        import hashlib
        digest = hashlib.sha256(data).hexdigest()
        b.require(b.sha(root / name) == digest, 'Commit candidate source before compilation')
        result[name] = digest
    return result


def validate_project(work):
    path = work / (NAME + '.xml')
    for ancestor in (path, work, *work.parents):
        b.require(not ancestor.is_symlink(), 'Symlinked generated project')
    b.require(path.is_file() and path.stat().st_nlink == 1 and 0 < path.stat().st_size <= 1024**2, 'Invalid generated project')
    root = ET.parse(path).getroot()
    ns = smoke.NS
    info = root.find(ns + 'device_info')
    b.require(info is not None and [(x.tag.removeprefix(ns), x.get('name')) for x in info] ==
              [('family', 'Trion'), ('device', 'T8F49'), ('timing_model', 'I2')], 'Candidate target changed')
    b.require(root.get('name') == NAME, 'Candidate project name changed')
    found = {}
    for node in root.iter():
        tag = node.tag.removeprefix(ns)
        if tag.endswith('_file'):
            expected = {'design_file': NAME + '.v', 'sdc_file': NAME + '_merged.sdc'}
            permitted = {expected.get(tag)}
            if tag == 'design_file':permitted.add(str(work / (NAME + '.v')))
            b.require(tag in expected and tag not in found and node.get('name') in permitted, 'Unexpected compiler input path')
            found[tag] = node.get('name')
    sections = root.findall(ns + 'bitstream_generation')
    b.require(len(sections) == 1, 'Missing or duplicate bitstream configuration')
    for node in sections[0]:
        if node.tag == ns + 'param' and node.get('name') in ('mode', 'width'):
            key = node.get('name')
            b.require(key not in found and node.get('value') == {'mode': 'passive', 'width': '1'}[key], 'Configuration mode changed')
            found[key] = node.get('value')
    b.require(set(found) == {'design_file', 'sdc_file', 'mode', 'width'}, 'Missing candidate project constraints')
    sdc = work / (NAME + '.sdc')
    b.require(sdc.is_file() and not sdc.is_symlink() and sdc.stat().st_size < 4096 and sdc.read_text().strip() == CLOCK, 'Candidate clock constraint changed')


def validate_interface(work):
    path = work / 'iface.py'
    b.require(path.is_file() and not path.is_symlink() and path.stat().st_size < 65536, 'Invalid interface script')
    tree = ast.parse(path.read_text())
    top_calls = {id(n.value) for n in tree.body if isinstance(n, ast.Expr)}
    created, assigned = {}, {}
    allowed = {'create', 'set_iobank_voltage', 'set_property', 'create_input_gpio',
               'create_inout_gpio', 'assign_pkg_pin', 'generate', 'save'}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != 'design':continue
        method = node.func.attr
        b.require(method in allowed and id(node) in top_calls, 'Unexpected interface operation')
        if method not in ('create_input_gpio', 'create_inout_gpio', 'assign_pkg_pin'):continue
        b.require(not node.keywords and all(isinstance(x, ast.Constant) and type(x.value) is str for x in node.args), 'Dynamic GPIO definition')
        args = [x.value for x in node.args]
        if method == 'assign_pkg_pin':
            b.require(len(args) == 2 and args[0] not in assigned, 'Duplicate pin assignment')
            assigned[args[0]] = args[1]
        else:
            b.require(len(args) == 1 and args[0] not in created, 'Duplicate GPIO definition')
            created[args[0]] = method.removeprefix('create_').removesuffix('_gpio')
    b.require({k: (v, assigned.get(k)) for k, v in created.items()} == GPIO and set(assigned) == set(GPIO), 'Unexpected physical GPIO map')
    peri = work / (NAME + '.peri.xml')
    b.require(peri.is_file() and not peri.is_symlink() and peri.stat().st_size < 1024**2, 'Invalid peripheral XML')
    root = ET.parse(peri).getroot(); ns = '{http://www.efinixinc.com/peri_design_db}'
    b.require(root.get('name') == NAME and root.get('device_def') == 'T8F49', 'Wrong peripheral project')
    nodes = list(root.iter(ns + 'gpio'))
    b.require(len(nodes) == 4 and {x.get('name'): x.get('mode') for x in nodes} == created, 'Peripheral GPIO modes changed')
    return PINS


def generated_hashes(work):
    result = {}
    for name in GENERATED:
        f = work / name
        b.require(f.is_file() and not f.is_symlink() and f.stat().st_nlink == 1 and 0 < f.stat().st_size <= 1024**2, 'Invalid generated input')
        result[name] = b.sha(f)
    text = (work / (NAME + '.v')).read_text()
    b.require(re.findall(r'\$readmemh\("([^"\n]+)"', text) == [NAME + '_mem.init'], 'Unexpected RTL memory input')
    return result


def make_soc(platform_class):
    from migen import Signal
    from litex.soc.interconnect.csr import AutoCSR, CSRStatus, CSRStorage
    from litex.gen import LiteXModule
    from litex_boards.platforms import adiuvo_forgix as board
    from litex_boards.targets.adiuvo_forgix import BaseSoC
    class Registers(LiteXModule, AutoCSR):
        def __init__(self):
            self.counter = CSRStatus(32, name='counter')
            self.scratch = CSRStorage(32, name='scratch')
            count = Signal(32)
            self.sync += count.eq(count + 1)
            self.comb += self.counter.status.eq(count)
    original = board.Platform
    try:
        board.Platform = platform_class
        soc = BaseSoC(sys_clk_freq=32000000, with_spibone=True, with_led_chaser=False,
                      with_demo_leds=False, with_demo_io=False, with_demo_scope=False)
        soc.registers = Registers()
        return soc
    finally:
        board.Platform = original


def worker(private):
    b.require(os.environ.get('FORGIX_INSIDE_EFINITY') == '1', 'Candidate worker requires the Nix FHS wrapper')
    provenance()
    from litex.build.efinix.platform import EfinixPlatform
    from litex_boards.platforms import adiuvo_forgix as board
    from litex.soc.integration.builder import Builder
    from litex.build import tools
    class Candidate(board.Platform):
        default_clk_freq = 32000000
        default_clk_period = 31.25
        def __init__(self):
            EfinixPlatform.__init__(self, 'T8F49I2', board._io, board._connectors,
                iobank_info=board._bank_info, toolchain='efinity', spi_mode='passive', spi_width='1')
    soc = make_soc(Candidate)
    sources = {str(i): {'sha256': b.sha(Path(inspect.getfile(module)))} for i, module in
               enumerate((board, __import__('litex_boards.targets.adiuvo_forgix', fromlist=['BaseSoC']),
                          __import__('litex.build.efinix.efinity', fromlist=['EfinityToolchain']),
                          __import__('litex.soc.cores.spi.spi_bone', fromlist=['SPIBone'])))}
    Builder(soc, output_dir=str(private / 'work'), compile_software=False, csr_csv=str(private / 'csr.csv')).build(build_name=NAME, run=False)
    work = private / 'work/gateware'
    resolved = validate_interface(work)
    validate_project(work)
    fixed = generated_hashes(work)
    project = b.sha(work / (NAME + '.xml'))
    original_call = tools.subprocess_call_filtered
    def compile_only(command, *args, **kwargs):
        expected = [soc.platform.efinity_path + '/bin/python3', soc.platform.efinity_path + '/scripts/efx_run.py', NAME + '.xml', '--flow', 'compile']
        b.require(command == expected, 'Unexpected vendor command')
        return original_call(command + ['--timeout', '300'], *args, **kwargs)
    tools.subprocess_call_filtered = compile_only
    cwd = Path.cwd()
    try:
        os.chdir(work)
        soc.platform.toolchain.run_script('')
    finally:
        os.chdir(cwd)
        tools.subprocess_call_filtered = original_call
    b.require(fixed == generated_hashes(work), 'Generated RTL, constraints or memory changed during compile')
    validate_interface(work)
    validate_project(work)
    b.save(private / 'generated.json', {'pins': resolved, 'upstream_files': sources, 'generated_sha256': fixed,
           'project_before_sha256': project, 'project_after_sha256': b.sha(work / (NAME + '.xml'))})


def compile_candidate(store, requested):
    provenance()
    frozen = source_hashes()
    b.require(not (store.path / 'runtime-unclosed.json').exists(), 'Inspect unverified vendor group closure first')
    private = smoke.private_path(store, requested)
    installation, metadata = store.installed()
    b.require(metadata['version'] == smoke.VERSION and metadata['software_sha256'] == smoke.ARCHIVE_SHA,
              'Candidate requires the reviewed Efinity full release')
    b.require(b.sha(installation / 'scripts/efx_run.py') == smoke.RUNNER_SHA, 'Vendor runner changed')
    wrapper = shutil.which('forgix-efinity'); python = os.environ.get('FORGIX_PYTHON'); envbin = shutil.which('env')
    b.require(wrapper and python and envbin and python.startswith('/nix/store/'), 'Locked Forgix runtime missing')
    b.require(shutil.disk_usage(store.path).free >= 1024**3, 'Candidate needs 1 GiB free storage')
    b.private_dir(private)
    receipt = dict(PROFILE, kind='forgix-offline-candidate', status='failed', source_sha256=frozen,
                   source_commit=subprocess.check_output(['git', '-C', str(store.root), 'rev-parse', 'HEAD'], text=True).strip(),
                   toolchain=provenance(), version=smoke.VERSION, software_sha256=smoke.ARCHIVE_SHA,
                   hardware_opened=False, owned_process_group_closed=False)
    started_ns = time.time_ns(); started_mono = time.monotonic()
    receipt['started_at_unix_ns'] = started_ns
    try:
        env = os.environ.copy(); env['LITEX_ENV_EFINITY'] = str(installation)
        console = private / 'console.log'; started = time.time_ns()
        with console.open('xb') as output:
            os.fchmod(output.fileno(), 0o600)
            code = b.run_owned([wrapper, envbin, '-u', 'PYTHONHOME', '-u', 'PYTHONPATH', python, '-E', '-s',
                str(store.root / 'tools/forgix_fpga_candidate.py'), '_worker', '--private', str(private)], env, output, 330, store, cwd=private)
        receipt['owned_process_group_closed'] = True
        receipt['exit_code'] = code
        b.require(code == 0, 'Candidate compiler failed; inspect private logs')
        # Reuse reviewed full-flow gates by presenting only the fixed build-name paths.
        receipt.update(verify_outputs(private, started))
        b.require(frozen == source_hashes(), 'Repository inputs changed during compilation')
        receipt.update(status='passed', compiler_execution_verified=True)
    except Exception as error:
        receipt['failure_kind'] = type(error).__name__
        if isinstance(error, b.Refusal):receipt['reason'] = str(error)
        # Only a normal run_owned return proves group closure here. Exceptions
        # before/inside that boundary remain conservative unknown outcomes.
        raise
    finally:
        receipt.update(finished_at_unix_ns=time.time_ns(), duration_seconds=time.monotonic()-started_mono)
        unsafe_success = False
        if receipt['owned_process_group_closed']:
            safe = smoke.harden_outputs(private)
            unsafe_success = receipt['status'] == 'passed' and not safe
            if not safe:receipt['status'] = 'failed'
        else:safe = False
        receipt['private_generated_files_verified'] = safe
        b.save(private / 'result.json', receipt)
        if unsafe_success:raise b.Refusal('Unsafe generated files')
    return receipt


def verify_outputs(private, started):
    work = private / 'work/gateware'
    validate_project(work)
    console = private / 'console.log'
    import re
    b.require(console.stat().st_size <= smoke.MAX_LOG, 'Console oversized')
    markers = re.findall(r'^\s*(map|interface|pnr|pgm|export_bitstream)\s*:\s*(PASS|SKIP|FAIL)\s*$', re.sub(r'\x1b\[[0-9;]*m', '', console.read_text(errors='replace')), re.M)
    b.require(markers == [(s, 'PASS') for s in smoke.STAGES], 'Missing or failed compiler stage')
    log = work / 'outflow' / (NAME + '.log'); image = work / 'outflow' / (NAME + '.hex')
    for f in (log, image):
        b.require(f.is_file() and not f.is_symlink() and f.stat().st_nlink == 1 and f.resolve().is_relative_to(work.resolve()), 'Unsafe or missing output')
        b.require(0 < f.stat().st_size <= smoke.MAX_LOG and f.stat().st_mtime_ns >= started, 'Stale or oversized output')
    b.require(re.findall(r'^Stage completed: (\S+)\s*$', log.read_text(errors='replace'), re.M) == list(smoke.STAGES), 'Incomplete stage log')
    meta = private / 'generated.json'
    b.require(meta.is_file() and not meta.is_symlink() and meta.stat().st_nlink == 1 and meta.stat().st_size <= 65536, 'Invalid generated provenance')
    generated = json.loads(meta.read_text())
    b.require(generated['pins'] == validate_interface(work), 'Unexpected candidate pins')
    b.require(generated.get('generated_sha256') == generated_hashes(work), 'Generated source hashes changed')
    return {'stages': list(smoke.STAGES), 'bitstream_sha256': b.sha(image), 'bitstream_bytes': image.stat().st_size, 'generated': generated}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', nargs='?', choices=['compile', '_worker'], default='compile')
    p.add_argument('--private', type=Path, required=True); a = p.parse_args(); os.umask(0o077)
    try:
        store = b.Store()
        if a.action == '_worker':
            # Parent created this private directory under its held vendor lock.
            path = a.private.absolute()
            b.require(path.is_relative_to(store.root / '.scratch') and path != store.root / '.scratch' and '..' not in path.parts, 'Invalid worker directory')
            for ancestor in (path, *path.parents):
                b.require(not ancestor.is_symlink(), 'Invalid worker directory')
                if ancestor == store.root:break
            b.require(not (path / 'work').exists(), 'Worker requires fresh generated output')
            worker(path); return 0
        with store.locked(): receipt = compile_candidate(store, a.private)
        print(json.dumps(receipt)); return 0
    except Exception as error:
        print(json.dumps(dict(PROFILE, status='failed', failure_kind=type(error).__name__,
              reason=str(error) if isinstance(error, b.Refusal) else 'Inspect private compiler logs', hardware_opened=False))); return 2


if __name__ == '__main__': raise SystemExit(main())

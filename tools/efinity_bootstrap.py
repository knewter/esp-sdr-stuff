#!/usr/bin/env python3
"""Private Efinity install manager. No downloads or automatic hardware commands; license data stays private."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE = 12 * 1024**3
MAX_EXPANDED = 24 * 1024**3
MAX_MEMBERS = 200000
MAX_PATH_BYTES = 4096
MAX_METADATA = 16 * 1024**2
RESERVE = 256 * 1024**2
VERSION = re.compile(r'\d{4}\.\d+(?:\.\d+){0,2}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')

class Refusal(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise Refusal(message)

def file_chunks(path, limit=MAX_ARCHIVE, expected=None):
    before = path.stat()
    require(expected is None or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == expected, "Input changed before copying")
    require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit, 'File exceeds its size/type bound')
    with path.open('rb') as source:
        opened = os.fstat(source.fileno())
        require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) == (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns), 'Input changed before opening')
        remaining = before.st_size
        while remaining:
            block = source.read(min(1024**2, remaining))
            require(block, 'Input shrank while reading')
            remaining -= len(block)
            yield block
        require(not source.read(1), 'Input grew while reading; partial retained')
        after = path.stat()
        require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) == (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns), 'Input changed while reading; partial retained')

def sha(path):
    h = hashlib.sha256()
    for block in file_chunks(path):
        h.update(block)
    return h.hexdigest()

def opaque(path):
    return b''.join(file_chunks(path, 1024**2))

def copy_frozen(path, destination, limit=MAX_ARCHIVE, expected=None):
    with destination.open('xb') as output:
        os.fchmod(output.fileno(), 0o600)
        for block in file_chunks(path, limit, expected):output.write(block)
    destination.chmod(0o600)


def private_dir(path):
    require(not path.is_symlink(), 'Private storage must not be a symlink')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(path.is_dir() and path.stat().st_uid == os.getuid(), 'Private storage must be owned by this user')
    path.chmod(0o700)

def save(path, data):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    with temporary.open('x', encoding='utf-8') as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(data, output, indent=2)
        output.write('\n')
    temporary.chmod(0o600)
    temporary.replace(path)

def input_file(path, limit=MAX_ARCHIVE):
    require(not path.is_symlink() and path.is_file(), 'Input must be a regular completed file')
    require(not path.name.lower().endswith(('.crdownload', '.part', '.tmp')), 'Download is incomplete; wait for completion')
    require(0 < path.stat().st_size <= limit, 'Input size is empty or exceeds the bound')

class Store:
    def __init__(self, root=ROOT):
        self.root = root.resolve()
        self.path = self.root / '.vendor/efinity'
        require(not (self.root / '.vendor').is_symlink() and not self.path.is_symlink(), 'Private vendor parent must not be a symlink')

    @contextlib.contextmanager
    def locked(self):
        private_dir(self.root / '.vendor')
        private_dir(self.path)
        require(not (self.path / '.lock').is_symlink(), 'Private lock must not be a symlink')
        with (self.path / '.lock').open('a') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            require(not (self.path / 'runtime-unclosed.json').exists(), 'Unverified vendor process closure must be inspected before modifying private storage')
            yield

    def catalog(self):
        p = self.path / 'catalog.json'
        require(not p.is_symlink(), 'Private catalog must not be a symlink')
        return json.loads(p.read_text()) if p.exists() else {'schema': 1, 'archives': {}, 'license_staged': False}

    def stage(self, path, role):
        input_file(path, 1024**2 if role == 'license' else MAX_ARCHIVE)
        initial = path.stat()
        frozen = (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
        if role == 'license':
            private_dir(self.path / 'licenses')
            destination = self.path / 'licenses/vendor-license'
            require(not destination.is_symlink(), 'Staged license must not be a symlink')
            if destination.exists():
                # Opaque byte comparison; no license hash, identity or contents in a receipt.
                require(opaque(destination) == opaque(path), 'A different private license is already staged')
                return {'role': 'license', 'reused': True}
            partial = destination.with_suffix('.partial')
            require(not partial.exists() and not partial.is_symlink(), 'A partial license import exists; inspect it before retrying')
            copy_frozen(path, partial, 1024**2, frozen)
            require(opaque(partial) == opaque(path), 'License changed while copying; partial retained')
            partial.replace(destination)
            catalog = self.catalog(); catalog['license_staged'] = True
        else:
            digest = sha(path)
            private_dir(self.path / 'archives')
            directory = self.path / 'archives' / digest
            private_dir(directory)
            destination = directory / 'download'
            require(not destination.is_symlink(), 'Staged software must not be a symlink')
            if destination.exists():
                require(sha(destination) == digest, 'Staged software bytes were changed')
                require(self.catalog()['archives'].get(digest, {}).get('role') == role, 'Staged role conflicts')
                return {'role': role, 'software_sha256': digest, 'reused': True}
            require(shutil.disk_usage(self.path).free >= initial.st_size + RESERVE, 'Insufficient staging space')
            partial = directory / 'download.partial'
            require(not partial.exists() and not partial.is_symlink(), 'A partial import exists; inspect it before retrying')
            copy_frozen(path, partial, expected=frozen)
            require(sha(partial) == digest, 'Download changed while copying; partial retained')
            partial.replace(destination)
            catalog = self.catalog()
            catalog['archives'][digest] = {'role': role, 'software_filename': path.name,
                                          'bytes': destination.stat().st_size}
        save(self.path / 'catalog.json', catalog)
        return {'role': role, **({'software_sha256': digest} if role != 'license' else {}), 'reused': False}

    def installed(self):
        selected = self.path / 'current.json'
        require(selected.is_file() and not selected.is_symlink(), 'No selected Efinity installation; import a completed full Linux release and install it')
        value = json.loads(selected.read_text())
        return self.candidate(value)

    def candidate(self, value):
        require(VERSION.fullmatch(value.get('version', '')) and DIGEST.fullmatch(value.get('software_sha256', '')), 'Invalid selection metadata')
        require(not (self.path / 'installs').is_symlink(), 'Install parent must not be a symlink')
        directory = self.path / 'installs' / value['version']
        require(not directory.is_symlink(), 'Install must not be a symlink')
        require(not (directory / 'install.json').is_symlink(), 'Install metadata must not be a symlink')
        metadata = json.loads((directory / 'install.json').read_text())
        require(metadata['software_sha256'] == value['software_sha256'] and metadata['version'] == value['version'], 'Selection/install provenance differs')
        relative = member_path(metadata['installation_relative'])
        installation = directory / relative
        require(installation.resolve().is_relative_to(directory.resolve()), 'Selected installation escapes private storage')
        for key in ('bin/setup.sh', 'bin/python3', 'scripts/efx_run.py', 'scripts/sw_version.txt'):
            actual = installation / key
            require(actual.resolve().is_relative_to(directory.resolve()) and sha(actual) == metadata['required_file_sha256'][key], 'Installed required software bytes were changed')
        validate_layout(installation, value['version'])
        return installation, metadata

    def install(self, digest, version, license_relative=None):
        require(VERSION.fullmatch(version), 'Use the exact numeric release version')
        catalog = self.catalog()
        if digest is None:
            candidates = [h for h, record in catalog['archives'].items() if record['role'] == 'full']
            require(len(candidates) == 1, 'Exactly one staged full release is required; otherwise pass --archive SHA256')
            digest = candidates[0]
        require(DIGEST.fullmatch(digest), 'Archive must be a staged software SHA256')
        require(catalog['archives'].get(digest, {}).get('role') == 'full', 'Selected input is not a full Linux release; patches/tools are staged separately')
        require(not (self.path / 'archives').is_symlink(), 'Archive parent must not be a symlink')
        archive = self.path / 'archives' / digest / 'download'
        require(not archive.parent.is_symlink() and not archive.is_symlink(), 'Staged archive must not be a symlink')
        require(sha(archive) == digest, 'Staged archive hash differs')
        private_dir(self.path / 'installs')
        final = self.path / 'installs' / version
        if final.exists():
            require(not final.is_symlink() and (final / 'install.json').is_file(), 'Existing version directory has unknown ownership')
            require(not (final / 'install.json').is_symlink(), 'Install metadata must not be a symlink')
            info = json.loads((final / 'install.json').read_text())
            require(info['software_sha256'] == digest and info['version'] == version, 'This release version already has different archive bytes')
            selection = {'version': version, 'software_sha256': digest}
            installation, info = self.candidate(selection)
            if license_relative is not None:
                self.place_license(installation, license_relative)
            save(self.path / 'current.json', selection)
            return {'version': version, 'software_sha256': digest, 'reused': True}
        partial = Path(tempfile.mkdtemp(prefix='.partial-' + version + '-', dir=self.path / 'installs'))
        try:
            extract(archive, partial)
            candidates = [p.parent.parent for p in partial.glob('**/bin/setup.sh') if p.is_file()]
            require(len(candidates) == 1, 'Archive must contain exactly one complete Efinity installation')
            installation = candidates[0]
            validate_layout(installation, version)
            if license_relative is not None:
                self.place_license(installation, license_relative)
            info = {'schema': 1, 'version': version, 'software_sha256': digest,
                    'installation_relative': installation.relative_to(partial).as_posix(),
                    'required_file_sha256': {k: sha(installation / k) for k in ('bin/setup.sh', 'bin/python3', 'scripts/efx_run.py', 'scripts/sw_version.txt')},
                    'patches_applied': [], 'license_compile_verified': False}
            save(partial / 'install.json', info)
            partial.rename(final)
            save(self.path / 'current.json', {'version': version, 'software_sha256': digest})
            return {'version': version, 'software_sha256': digest, 'reused': False}
        except Exception:
            # No incomplete installation is selected. Failed bytes remain private for inspection.
            if partial.exists():
                partial.rename(partial.with_name('.failed-' + partial.name.removeprefix('.partial-')))
            raise

    def place_license(self, installation, relative):
        target = member_path(relative)
        require(target != Path('.') and target.parts[0] not in ('bin', 'scripts'), 'License must not overwrite executable software')
        source = self.path / 'licenses/vendor-license'
        require(source.is_file() and not source.is_symlink(), 'Import the vendor license before selecting its documented location')
        destination = installation / target
        require(destination.parent.resolve().is_relative_to(installation.resolve()) and not destination.is_symlink(), 'License location escapes the installation')
        if destination.exists():
            require(destination.is_file() and opaque(destination) == opaque(source), 'License location conflicts')
        else:
            private_dir(destination.parent)
            copy_frozen(source, destination, 1024**2)
        destination.chmod(0o600)


def member_path(name):
    require(isinstance(name, str) and len(name.encode('utf-8')) <= MAX_PATH_BYTES and '\\' not in name and '\x00' not in name, 'Unsafe archive path')
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and not any(':' in p for p in path.parts), 'Unsafe archive traversal')
    return Path(*path.parts)

def safe_link(name, target):
    require(target and len(target.encode('utf-8')) <= MAX_PATH_BYTES and '\\' not in target and not PurePosixPath(target).is_absolute(), 'Unsafe archive symlink')
    parts = list(member_path(name).parent.parts)
    for piece in PurePosixPath(target).parts:
        if piece == '..':
            require(parts, 'Archive symlink escapes extraction')
            parts.pop()
        elif piece != '.':
            require(':' not in piece, 'Unsafe archive symlink')
            parts.append(piece)
    return Path(*parts)

class BoundedTarInfo(tarfile.TarInfo):
    def metadata_bound(self, archive, per_header):
        require(0 <= self.size <= per_header, 'TAR extended metadata bound exceeded')
        total = getattr(archive, '_efinity_metadata_bytes', 0) + self.size
        require(total <= MAX_METADATA, 'TAR cumulative metadata bound exceeded')
        archive._efinity_metadata_bytes = total
    def _proc_pax(self, archive):
        self.metadata_bound(archive, 65536)
        return super()._proc_pax(archive)
    def _proc_gnulong(self, archive):
        self.metadata_bound(archive, MAX_PATH_BYTES)
        return super()._proc_gnulong(archive)


@contextlib.contextmanager
def archive_entries(archive):
    input_file(archive)
    container = zipfile.ZipFile(archive) if zipfile.is_zipfile(archive) else None
    if container is None:
        try:
            container = tarfile.open(archive, 'r:*', tarinfo=BoundedTarInfo)
        except tarfile.TarError:
            raise Refusal('Use a completed Linux tar or ZIP full release; Windows MSI and standalone tool bits are not a full installation')
    try:
        members = []; total = 0
        if isinstance(container, zipfile.ZipFile):
            opening = container.open
            source = container.infolist()
        else:
            opening = container.extractfile
            source = container
        for m in source:
            require(len(members) < MAX_MEMBERS, 'Archive member bound exceeded')
            if isinstance(m, zipfile.ZipInfo):
                mode = m.external_attr >> 16
                filetype = stat.S_IFMT(mode)
                require(filetype in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK), 'Archive special files are unsupported')
                require(not m.flag_bits & 1, 'Encrypted archive is unsupported')
                kind = 'dir' if m.is_dir() else 'link' if filetype == stat.S_IFLNK else 'file'
                require(filetype != stat.S_IFDIR or kind == 'dir', 'Conflicting ZIP directory metadata')
                name, size = m.filename, m.file_size
            else:
                require(m.isdir() or m.isfile() or m.issym(), 'Archive special files/hardlinks are unsupported')
                name, kind, size, mode = m.name, 'dir' if m.isdir() else 'link' if m.issym() else 'file', m.size, m.mode
            require(type(size) is int and size >= 0, 'Invalid archive member size')
            require(kind != 'link' or size <= MAX_PATH_BYTES, 'Archive symlink metadata bound exceeded')
            total += size if kind != 'dir' else 0
            # Check before TAR iteration advances and decompresses/skips this member.
            require(total <= MAX_EXPANDED, 'Expanded archive bound exceeded')
            member_path(name)
            members.append((name, kind, size, mode, m))
        require(total > 0, 'Archive has no file content')
        yield container, members, opening, total
    finally:
        container.close()


def extract(archive, destination):
    with archive_entries(archive) as (container, members, opening, total):
        require(shutil.disk_usage(destination).free >= total + RESERVE, 'Insufficient extraction space')
        paths = {}; links = []
        for name, kind, size, mode, m in members:
            relative = member_path(name)
            if relative == Path('.'):
                require(kind == 'dir', 'Invalid root entry'); continue
            require(relative not in paths, 'Duplicate archive path')
            paths[relative] = kind
        for path in paths:
            require(all(paths.get(parent) in (None, 'dir') for parent in path.parents if parent != Path('.')), 'Archive parent is a file or symlink')
        for name, kind, size, mode, m in members:
            relative = member_path(name)
            if relative == Path('.'): continue
            out = destination / relative
            private_dir(out.parent)
            if kind == 'dir':private_dir(out)
            elif kind == 'link':
                if isinstance(m, tarfile.TarInfo):target = m.linkname
                else:
                    with opening(m) as inp:target = inp.read(MAX_PATH_BYTES + 1).decode('utf-8')
                safe_link(name, target)
                links.append((out, target))
            else:
                with opening(m) as inp, out.open('xb') as dst:
                    shutil.copyfileobj(inp, dst, 1024**2)
                require(out.stat().st_size == size, 'Archive file length differs')
                out.chmod(0o700 if mode & 0o111 else 0o600)
        for out, target in links:out.symlink_to(target)
        for out, _ in links:
            try:
                contained = out.resolve().is_relative_to(destination.resolve()) and out.exists()
            except (OSError, RuntimeError):
                contained = False
            require(contained, 'Archive symlink target is missing/cyclic/outside')


def validate_layout(root, version):
    for key in ('bin/setup.sh', 'bin/python3', 'scripts/efx_run.py', 'scripts/sw_version.txt'):
        require((root / key).is_file(), 'Full release layout is incomplete')
    actual = (root / 'scripts/sw_version.txt').read_text().strip()
    require(actual == version, 'Archive release version differs from --version; no patch/version fallback')

def discover(directories):
    candidates = []; partial = 0; seen = set()
    for folder in directories:
        folder = folder.expanduser().resolve()
        if folder in seen or not folder.is_dir():continue
        seen.add(folder)
        for index, p in enumerate(folder.iterdir()):
            require(index < 10000, 'Downloads directory entry bound exceeded')
            if not p.is_file() or p.is_symlink():continue
            name = p.name.lower()
            if name.endswith(('.crdownload', '.part')):partial += 1; continue
            if name.startswith(('efinity', 'efinix')):
                if 'license' in name or name.endswith('.lic'):
                    candidates.append({'role': 'license', 'filename_omitted': True})
                else:candidates.append({'software_filename': p.name, 'bytes': p.stat().st_size})
    return {'status': 'completed_inputs_found' if candidates else 'downloads_incomplete' if partial else 'missing_inputs',
            'candidates': candidates, 'partial_downloads_not_opened': partial, 'recursive_search': False}

def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(proc, grace=2):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if group_exists(proc.pid):
            try:os.killpg(proc.pid, sig)
            except ProcessLookupError:pass
        try:proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:pass
        deadline = time.monotonic() + grace
        while group_exists(proc.pid) and time.monotonic() < deadline:time.sleep(.02)
        if not group_exists(proc.pid):return
    raise Refusal('Vendor process group closure is unverified; inspect private runtime state before reuse')


def run_owned(command, env, output, timeout, store, cwd=None):
    # Deferral spans Popen and ownership registration; children inherit normal
    # signal dispositions, not a blocked signal mask. Cleanup ignores repeated
    # cancellation until the whole owned group is proven gone.
    proc = None;pending = [];handlers = {}
    def cancel(*_):raise Refusal('Vendor command cancelled; private output retained')
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            handlers[number] = signal.signal(number, lambda n, _:pending.append(n))
        spawn_options = {'cwd': cwd} if cwd is not None else {}
        proc = subprocess.Popen(command, env=env, stdout=output,
                                stderr=subprocess.STDOUT, start_new_session=True, **spawn_options)
        for number in handlers:signal.signal(number, cancel)
        if pending:cancel()
        returncode = proc.wait(timeout=timeout)
        return returncode
    finally:
        for number in handlers:signal.signal(number, lambda *_:None)
        try:
            if proc is not None:
                try:stop_group(proc)
                except Refusal:
                    save(store.path / 'runtime-unclosed.json', {'owned_process_group': proc.pid, 'closure_verified': False})
                    raise
        finally:
            for number, handler in handlers.items():signal.signal(number, handler)


def runtime(store, action, command):
    require(not (store.path / 'runtime-unclosed.json').exists(), 'Unverified vendor process closure must be inspected before runtime reuse')
    installation, metadata = store.installed()
    wrapper = shutil.which('forgix-efinity')
    require(wrapper is not None, 'Enter nix develop .#forgix for the Efinity runtime')
    env = os.environ.copy();env['LITEX_ENV_EFINITY'] = str(installation)
    if action == 'check':
        command = [str(installation / 'bin/python3'), str(installation / 'scripts/efx_run.py'), '--help']
    require(command, 'Supply an explicit command after --; no hardware command is started automatically')
    if command[0] == '@forgix-python':
        require(bool(env.get('FORGIX_PYTHON')), 'The pinned Forgix Python is unavailable; enter the Forgix shell')
        env_tool = shutil.which('env')
        require(env_tool is not None and Path(env_tool).resolve().is_relative_to('/nix/store'), 'The pinned environment helper is unavailable; enter the Forgix Nix shell')
        # setup.sh runs first inside FHS. Remove its Python variables only
        # for the explicit host process and descendants; other vendor settings stay.
        command = [env_tool, '-u', 'PYTHONHOME', '-u', 'PYTHONPATH', env['FORGIX_PYTHON'], '-E', '-s', *command[1:]]
    private_dir(store.path / 'logs')
    log = store.path / 'logs' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex + '.log')
    try:
        with log.open('xb') as output:
            os.fchmod(output.fileno(), 0o600)
            returncode = run_owned([wrapper, *command], env, output,
                                   60 if action == 'check' else 3600, store)
    finally:
        if log.exists():log.chmod(0o600)
    return {'status': 'vendor_cli_ready' if returncode == 0 and action == 'check' else 'command_completed' if returncode == 0 else 'vendor_command_failed',
            'exit_code': returncode, 'version': metadata['version'], 'software_sha256': metadata['software_sha256'],
            'vendor_output_private': True, 'license_compile_verified': False}, returncode

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('discover');p.add_argument('--source-dir', type=Path, action='append')
    p = sub.add_parser('import');p.add_argument('--full', type=Path, action='append', default=[]);p.add_argument('--patch', type=Path, action='append', default=[]);p.add_argument('--tool', type=Path, action='append', default=[]);p.add_argument('--license', type=Path)
    p = sub.add_parser('install');p.add_argument('--archive');p.add_argument('--version', required=True);p.add_argument('--license-relative', help='Relative destination explicitly specified by your vendor license instructions')
    sub.add_parser('check')
    p = sub.add_parser('run');p.add_argument('command', nargs=argparse.REMAINDER)
    p = sub.add_parser('host-check');p.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv);os.umask(0o077)
    try:
        store = Store()
        if args.action == 'discover':report = discover(args.source_dir or [Path.home() / 'Downloads'])
        elif args.action == 'host-check':
            forwarded = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
            require(not any(arg == '--build-dir' or arg.startswith('--build-dir=') for arg in forwarded), 'Run compilation explicitly through forgix:efinity:run for private vendor output')
            with store.locked():
                env = os.environ.copy()
                if not env.get('LITEX_ENV_EFINITY') and (store.path / 'current.json').exists():
                    installation, _ = store.installed();env['LITEX_ENV_EFINITY'] = str(installation)
                return run_owned([os.environ.get('FORGIX_PYTHON', 'python3'), str(ROOT / 'tools/forgix_toolchain_check.py'), *forwarded], env, sys.stdout, 180, store)
        else:
            with store.locked():
                if args.action == 'import':
                    files = [(p, role) for role in ('full', 'patch', 'tool') for p in getattr(args, role)]
                    if args.license:files.append((args.license, 'license'))
                    require(files, 'Pass completed inputs explicitly with --full, --patch, --tool or --license; run discover first')
                    report = {'status': 'staged', 'inputs': [store.stage(p.expanduser(), role) for p, role in files]}
                elif args.action == 'install':report = {'status': 'installed', **store.install(args.archive, args.version, args.license_relative)}
                else:
                    command = getattr(args, 'command', [])
                    if command[:1] == ['--']:command = command[1:]
                    report, code = runtime(store, args.action, command)
                    print(json.dumps(report));return code
        print(json.dumps(report));return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError, RuntimeError, tarfile.TarError, zipfile.BadZipFile, subprocess.TimeoutExpired):
        # Exceptions/vendor output can contain private paths/license identifiers.
        # Only deliberate static Refusal messages are safe for user-facing output.
        error = sys.exc_info()[1]
        print(json.dumps({'status': 'incomplete_or_refused', 'reason': str(error) if isinstance(error, Refusal) else 'Private installation operation failed; no new installation was selected', 'automatic_hardware_operation': False}))
        return 2

if __name__ == '__main__':raise SystemExit(main())

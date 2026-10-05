"""Provision only the locked source004 Nix dependency; never run a measurement.

Root operator must first qualify recovery independently. A failed/cancelled
client does not prove daemon cancellation. Persistent roots are never removed.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from urllib.parse import quote

BOOTSTRAP = '/nix/store/3vd56d4l3ih231ci008zyvrjjs199zz5-nix-2.34.8/bin/nix'
BOOTSTRAP_SHA = '05c4fbc073d68c5d09f5254eebb3fd92594a5f1c10bd9e01a50c6136a76caee4'
GIT = '/nix/store/msr1v91ybfw6j12rs5mfl8ghb2rqsnsr-git-2.55.0/bin/git'
GIT_SHA = 'd324045fccf930f1b1f174e0ad94e49a50d4d1df1175322e41338c25a2239d13'
PYTHON_SHA = '877a94ff86033558bfe359c1a235f27a135f86db165fe46a8247a592505d41c5'
BOOTSTRAP_OUTPUT = str(Path(BOOTSTRAP).parent.parent)
PROVIDER = '/nix/store/qfwk7cyvb885l2mc06ac3a7nmv19nigi-nix-2.34.8'
STORE = 'unix:///nix/var/nix/daemon-socket/socket'
SELECTOR = 'nixpkgs.legacyPackages.x86_64-linux.nix'
LIMIT = 16 * 1024 * 1024
STORE_RE = r'/nix/store/[0-9abcdfghijklmnpqrsvwxyz]{32}-[^/\s]+'
# Separate provisioning policy; this does not alter measurement's no-build policy.
SETTINGS = {
    'experimental-features': 'nix-command flakes', 'plugin-files': '',
    'pure-eval': 'true', 'allow-import-from-derivation': 'false',
    'allow-unsafe-native-code-during-evaluation': 'false',
    'accept-flake-config': 'false', 'flake-registry': '', 'use-registries': 'false',
    'nix-path': '', 'builders': '', 'max-jobs': '1', 'substitute': 'true',
    'substituters': 'https://cache.nixos.org/', 'extra-substituters': '',
    'trusted-public-keys': 'cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY=',
    'require-sigs': 'true',
}
CONFIG = ''.join(f'{k} = {v}\n' for k, v in SETTINGS.items()).encode()
SOURCES = ('flake.nix', 'flake.lock', 'Taskfile.yml', 'tools/source004_provider_retain.py',
           'tests/test_source004_provider_retain.py')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_receipt(path):
    path = Path(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= 256 * 1024**2, 'bounded regular input')
    return {'path': str(path), 'bytes': info.st_size, 'sha256': digest(path.read_bytes())}


def write_new(path, raw):
    require(len(raw) <= LIMIT, 'receipt limit')
    with Path(path).open('xb') as stream:
        os.chmod(path, 0o400)
        require(stream.write(raw) == len(raw), 'short receipt write')
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(path, value):
    write_new(path, canonical(value) + b'\n')


def private_tree(path, anchor, final_private=True):
    """Create only missing private directories; reject symlinks at every level."""
    path, anchor = Path(path), Path(anchor)
    parts = path.relative_to(anchor).parts
    require(all(part not in ('.', '..') for part in parts), 'canonical private path')
    cursor = anchor
    for part in parts:
        cursor = cursor / part
        if not cursor.exists() and not cursor.is_symlink():
            cursor.mkdir(mode=0o700)
        info = cursor.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) & 0o022 == 0
                and (not final_private or cursor != path or stat.S_IMODE(info.st_mode) == 0o700),
                'private directory ownership/mode')
    return path


def controlled_environment(output):
    base = output / 'environment'
    base.mkdir(mode=0o700)
    for name in ('system', 'user', 'home', 'cache', 'temp'):
        (base / name).mkdir(mode=0o700)
    write_new(base / 'system/nix.conf', CONFIG)
    write_new(base / 'user/nix.conf', b'')
    return {'PATH': ':'.join((str(Path(BOOTSTRAP).parent), str(Path(GIT).parent))),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'NIX_CONF_DIR': str(base / 'system'),
            'NIX_USER_CONF_FILES': str(base / 'user/nix.conf'), 'NIX_CONFIG': '', 'NIX_PATH': '',
            'HOME': str(base / 'home'), 'XDG_CONFIG_HOME': str(base / 'user'),
            'XDG_CONFIG_DIRS': str(base / 'system'), 'XDG_CACHE_HOME': str(base / 'cache'),
            'TMPDIR': str(base / 'temp'), 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


class Commands:
    """Bounded direct CLI receipts. No numeric signal or automatic retry.

    Deadline/cancellation signals only the retained original client pidfd. This
    cannot qualify daemon descendants or prove the daemon stopped a build.
    """
    def __init__(self, output, env, seconds, deadline=None):
        self.output, self.env = output, env
        self.deadline = time.monotonic() + seconds if deadline is None else deadline
        self.records = []

    def __call__(self, name, argv):
        require(time.monotonic() < self.deadline, 'dependency deadline')
        require(len(self.records) < 32 and re.fullmatch(r'[a-z0-9-]+', name), 'command bound')
        prefix = self.output / f'{len(self.records):02d}-{name}'
        request = {'name': name, 'argv': argv, 'environment': self.env,
                   'deadline_monotonic': self.deadline, 'start_monotonic': time.monotonic(),
                   'executable': file_receipt(argv[0])}
        save(prefix.with_suffix('.request.json'), request)
        proc = None
        pidfd = None
        status = None
        error = None
        buffers = [bytearray(), bytearray()]
        with selectors.DefaultSelector() as selector:
            try:
                proc = subprocess.Popen(argv, env=self.env, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        close_fds=True, start_new_session=True)
                pidfd = os.pidfd_open(proc.pid)
                for index, stream in enumerate((proc.stdout, proc.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, index)
                while selector.get_map() or proc.poll() is None:
                    require(time.monotonic() < self.deadline, 'dependency deadline')
                    for key, _ in selector.select(min(0.1, self.deadline - time.monotonic())):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        require(len(buffers[key.data]) + len(chunk) <= LIMIT, 'command log overflow')
                        buffers[key.data].extend(chunk)
                status = proc.wait()
                require(status == 0, 'command failed')
            except BaseException as exc:
                error = f'{type(exc).__name__}: {exc}'
                if proc is not None and pidfd is not None and proc.poll() is None:
                    try:
                        signal.pidfd_send_signal(pidfd, signal.SIGKILL)
                        status = proc.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
            finally:
                if pidfd is not None:
                    os.close(pidfd)
                if proc is not None:
                    for stream in (proc.stdout, proc.stderr):
                        if stream is not None:
                            stream.close()
        write_new(prefix.with_suffix('.stdout'), bytes(buffers[0]))
        write_new(prefix.with_suffix('.stderr'), bytes(buffers[1]))
        record = {'name': name, 'request': file_receipt(prefix.with_suffix('.request.json')),
                  'stdout': file_receipt_allow_empty(prefix.with_suffix('.stdout')),
                  'stderr': file_receipt_allow_empty(prefix.with_suffix('.stderr')),
                  'end_monotonic': time.monotonic(), 'returncode': status, 'error': error,
                  'daemon_cancellation_proven': False}
        save(prefix.with_suffix('.terminal.json'), record)
        self.records.append(record)
        require(error is None, error or 'command failure')
        require(time.monotonic() < self.deadline, 'late command persistence')
        return bytes(buffers[0])


def file_receipt_allow_empty(path):
    raw = Path(path).read_bytes()
    require(len(raw) <= LIMIT, 'bounded log')
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def nix_args(executable=BOOTSTRAP, registration_only=False):
    settings = dict(SETTINGS)
    if registration_only:
        settings.update({'substitute': 'false', 'substituters': '', 'extra-substituters': '',
                         'builders': '', 'max-jobs': '0'})
    return [executable, '--store', STORE,
            *[arg for key, value in settings.items() for arg in ('--option', key, value)]]


def expression(root, revision):
    url = 'git+file://' + quote(str(root), safe='/') + '?rev=' + revision
    return 'let f = builtins.getFlake ' + json.dumps(url) + '; p = f.inputs.' + SELECTOR + '; in '


def validate_config(raw):
    data = json.loads(raw)
    wanted = {'plugin-files': [], 'pure-eval': True, 'allow-import-from-derivation': False,
              'allow-unsafe-native-code-during-evaluation': False, 'accept-flake-config': False,
              'flake-registry': '', 'use-registries': False, 'nix-path': [], 'builders': '',
              'max-jobs': 1, 'substitute': True, 'substituters': ['https://cache.nixos.org/'],
              'trusted-public-keys': [SETTINGS['trusted-public-keys']], 'require-sigs': True}
    for key, expected in wanted.items():
        value = data.get(key, {}).get('value')
        require(type(value) is type(expected) and value == expected, 'effective config mismatch: ' + key)
    features = data.get('experimental-features', {}).get('value')
    require(type(features) is list and len(features) == 3
            and set(features) == {'nix-command', 'flakes', 'fetch-tree'}, 'effective features')
    return dict(wanted, **{'experimental-features': sorted(features)})


def validate_selection(raw):
    value = json.loads(raw)
    require(type(value) is dict and set(value) == {'provider', 'derivation', 'selected_sources'}, 'selection fields')
    require(value['provider'] == PROVIDER, 'exact selected provider mismatch')
    require(type(value['derivation']) is str and re.fullmatch(STORE_RE, value['derivation'])
            and value['derivation'].endswith('-nix-2.34.8.drv'), 'exact derivation shape')
    sources = value['selected_sources']
    require(type(sources) is dict and set(sources) == {'project', 'nixpkgs'}, 'selected source fields')
    require(all(type(p) is str and re.fullmatch(STORE_RE, p) for p in sources.values()), 'selected source paths')
    return value


def validate_closure(raw, requisites):
    value = json.loads(raw)
    require(type(value) is dict and 0 < len(value) <= 4096 and PROVIDER in value, 'whole closure object')
    listed = requisites.decode().splitlines()
    require(len(listed) == len(set(listed)) and set(listed) == set(value), 'closure conservation')
    for path, row in value.items():
        require(re.fullmatch(STORE_RE, path) and type(row) is dict
                and row.get('version') == 1 and row.get('storeDir') == '/nix/store', 'closure path row')
        refs = row.get('references')
        require(type(refs) is list and len(refs) == len(set(refs))
                and all(type(ref) is str and ref in value for ref in refs), 'closure references')
        require(type(row.get('narSize')) is int and row['narSize'] > 0
                and type(row.get('narHash')) is str
                and re.fullmatch(r'sha256-[A-Za-z0-9+/]{43}=', row['narHash']), 'closure NAR identity')
    visited, pending = set(), [PROVIDER]
    while pending:
        path = pending.pop()
        if path not in visited:
            visited.add(path)
            pending.extend(value[path]['references'])
    require(visited == set(value), 'no unrelated closure member')
    return value


def verify_root(root, selected, roots_raw):
    require(root.is_symlink() and os.readlink(root) == selected, 'persistent root exact target')
    require(root.resolve(strict=True) == Path(selected) and Path(selected).is_dir(), 'stale provider root')
    roots = roots_raw.decode().splitlines()
    # Nix 2.34.8 qRoots prints each registered link and its target, including
    # referrer roots. A bare path or another target is not this root's authority.
    own = [line for line in roots if line.startswith(str(root) + ' -> ')]
    require(own == [str(root) + ' -> ' + selected], 'Nix registered exact indirect root required')
    return {'path': str(root), 'target': os.readlink(root), 'registered_roots': roots}


def retain(root, revision, output, command):
    """Fixed protocol; command injection is Python fixture-only, never a CLI option."""
    require(re.fullmatch('[0-9a-f]{40}', revision) is not None, 'explicit immutable revision')
    git = lambda name, args: command(name, [GIT, '-C', str(root), *args])
    require(git('head-initial', ['rev-parse', 'HEAD']).decode().strip() == revision, 'revision mismatch')
    require(not git('clean-initial', ['status', '--porcelain']).strip(), 'dirty checkout')
    inputs = {}
    for index, name in enumerate(SOURCES):
        raw = git('source-' + str(index), ['show', revision + ':' + name])
        require((root / name).read_bytes() == raw, 'source not committed: ' + name)
        inputs[name] = {'bytes': len(raw), 'sha256': digest(raw)}
    config = validate_config(command('bootstrap-config', nix_args() + ['config', 'show', '--json']))
    base = expression(root, revision)
    frozen = base + '{ provider = p.outPath; derivation = p.drvPath; selected_sources = { project = toString f.outPath; nixpkgs = toString f.inputs.nixpkgs.outPath; }; }'
    selection = validate_selection(command('select', nix_args() + ['eval', '--json', '--no-update-lock-file',
                                                                  '--no-write-lock-file', '--expr', frozen]))
    binding = {'schema': 1, 'revision': revision, 'inputs': inputs, 'selector': SELECTOR,
               'selection': selection, 'bootstrap_sha256': BOOTSTRAP_SHA, 'store_uri': STORE}
    key = digest(canonical(binding))
    persistent = private_tree(root / '.vendor/source004-nix-roots' / key, root)
    link = persistent / 'provider'
    tuple_file = persistent / 'tuple.json'
    save(output / 'tuple.json', dict(binding, tuple_digest=key, persistent_root=str(link)))
    if tuple_file.exists() or tuple_file.is_symlink():
        require(not tuple_file.is_symlink() and tuple_file.read_bytes() == canonical(binding) + b'\n', 'root tuple mismatch')
    else:
        require(not link.exists() and not link.is_symlink(), 'root without original tuple')
        save(tuple_file, binding)
    # Locked source inputs and the distinct existing bootstrap need their own roots;
    # they are not necessarily references in the selected provider's runtime graph.
    input_targets = dict(selection['selected_sources'], bootstrap=BOOTSTRAP_OUTPUT)
    input_info = json.loads(command('retained-input-paths', nix_args(registration_only=True)
                           + ['path-info', '--json', '--json-format', '1', *input_targets.values()]))
    require(type(input_info) is dict and set(input_info) == set(input_targets.values()), 'exact retained input paths')
    for path, row in input_info.items():
        require(type(row) is dict and row.get('version') == 1 and row.get('storeDir') == '/nix/store'
                and type(row.get('narSize')) is int and row['narSize'] > 0
                and type(row.get('narHash')) is str
                and re.fullmatch(r'sha256-[A-Za-z0-9+/]{43}=', row['narHash']), 'valid existing retained input')
    input_roots = {}
    no_realise_cli = nix_args(str(Path(BOOTSTRAP).with_name('nix-store')), registration_only=True)
    for role, target in sorted(input_targets.items()):
        input_link = persistent / ('input-' + role)
        if not input_link.exists() and not input_link.is_symlink():
            registered_output = command('root-register-' + role, no_realise_cli
                              + ['--add-root', str(input_link), '--indirect', '--realise', target])
            require(registered_output.decode().splitlines() == [str(input_link)], 'registration returned exact root path')
        input_roots[role] = verify_root(input_link, target, command('root-verify-' + role,
                              no_realise_cli + ['--query', '--roots', target]))
    save(output / 'retained-input-roots.json', {'paths': input_info, 'roots': input_roots})
    # Existing roots may be re-verified, never overwritten/re-registered implicitly.
    existed = link.exists() or link.is_symlink()
    if existed:
        initial_roots = command('roots-initial', nix_args(str(Path(BOOTSTRAP).with_name('nix-store'))) + ['--query', '--roots', PROVIDER])
        verify_root(link, PROVIDER, initial_roots)
    else:
        built = json.loads(command('build-provider', nix_args() + ['build', '--json', '--print-build-logs', '--no-update-lock-file',
                           '--no-write-lock-file', '--expr', base + 'p', '^out', '--out-link', str(link)]))
        require(type(built) is list and len(built) == 1 and type(built[0]) is dict
                and built[0].get('drvPath') == selection['derivation']
                and built[0].get('outputs') == {'out': PROVIDER}, 'exact realized output/derivation')
    store_cli = nix_args(str(Path(BOOTSTRAP).with_name('nix-store')))
    registered = verify_root(link, PROVIDER, command('roots-final', store_cli + ['--query', '--roots', PROVIDER]))
    closure_raw = command('runtime-closure', nix_args() + ['path-info', '--recursive', '--json', '--json-format', '1', PROVIDER])
    requisites = command('runtime-requisites', store_cli + ['--query', '--requisites', PROVIDER])
    closure = validate_closure(closure_raw, requisites)
    executables = {name: file_receipt(Path(PROVIDER) / 'bin' / name) for name in ('nix', 'nix-store')}
    provider_config = validate_config(command('provider-config', nix_args(str(Path(PROVIDER) / 'bin/nix')) + ['config', 'show', '--json']))
    require(provider_config == config, 'provider/bootstrap effective config differs')
    require(git('head-final', ['rev-parse', 'HEAD']).decode().strip() == revision, 'final revision mismatch')
    require(not git('clean-final', ['status', '--porcelain']).strip(), 'final dirty checkout')
    for name in SOURCES:
        require(digest((root / name).read_bytes()) == inputs[name]['sha256'], 'final source changed')
    verify_root(link, PROVIDER, command('roots-terminal', store_cli + ['--query', '--roots', PROVIDER]))
    for role, target in sorted(input_targets.items()):
        verify_root(persistent / ('input-' + role), target, command('root-terminal-' + role,
                    no_realise_cli + ['--query', '--roots', target]))
    result = {'schema': 1, 'dependency_retained': True, 'measurement_admitted': False,
              'recovery_performed': False, 'daemon_cancellation_proven': False,
              'tuple_digest': key, 'binding': binding, 'root': registered,
              'closure': closure, 'executables': executables, 'input_paths': input_info, 'input_roots': input_roots, 'existing_root_verified': existed}
    return result


def main(argv=None):
    started = time.monotonic()
    previous_handlers = {}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='persistent main repository, outside scratch/worktree cleanup')
    parser.add_argument('--revision', required=True, help='full committed HEAD SHA; no implicit HEAD')
    parser.add_argument('--output', type=Path, required=True, help='NEW ignored directory under .scratch/')
    parser.add_argument('--seconds', type=int, required=True, help='separate dependency budget, 1..3600; never measurement clocks')
    args = parser.parse_args(argv)
    require(1 <= args.seconds <= 3600, 'dependency budget bound')
    deadline = started + args.seconds
    root = args.root.resolve(strict=True)
    require(root == args.root.absolute() and '.scratch' not in root.parts and '.git' not in root.parts,
            'persistent repository outside worktree cleanup')
    require((root / '.git').is_dir(), 'persistent main checkout required')
    output = args.output.absolute()
    require(output == output.resolve(strict=False), 'canonical ignored output required')
    output.relative_to(root / '.scratch')
    require(not output.exists() and not output.is_symlink(), 'new output required; no retry')
    private_tree(output.parent, root, final_private=False)
    output.mkdir(mode=0o700)
    command = None
    lock = None
    try:
        save(output / 'invocation.json', {'argv': sys.argv if argv is None else argv,
             'root': str(root), 'revision': args.revision, 'output': str(output), 'seconds': args.seconds,
             'start_monotonic': started, 'deadline_monotonic': deadline,
             'scope': 'dependency-only; independently qualified recovery required before operator admission'})
        tools = {'bootstrap': file_receipt(BOOTSTRAP), 'git': file_receipt(GIT),
                 'python': file_receipt(sys.executable), 'bootstrap_nix_store': file_receipt(Path(BOOTSTRAP).with_name('nix-store'))}
        require(tools['bootstrap']['sha256'] == BOOTSTRAP_SHA and tools['git']['sha256'] == GIT_SHA
                and tools['python']['sha256'] == PYTHON_SHA, 'pinned tool mismatch')
        require(Path(__file__).resolve() == root / 'tools/source004_provider_retain.py', 'current helper location')
        save(output / 'tools.json', tools)
        imports = {name: file_receipt_allow_empty(module.__file__) for name, module in sorted(sys.modules.items())
                   if getattr(module, '__file__', None) and Path(module.__file__).is_file()}
        save(output / 'imports.json', imports)
        base = private_tree(root / '.vendor/source004-nix-roots', root)
        lock = os.open(base / 'retain.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        info = os.fstat(lock)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1, 'own provisioning lock')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        env = controlled_environment(output)
        save(output / 'environment.json', env)
        require(time.monotonic() < deadline, 'dependency setup deadline')
        command = Commands(output, env, args.seconds, deadline=deadline)
        def cancelled(signum, frame):
            raise InterruptedError('operator cancellation ' + str(signum))
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, cancelled)
        result = retain(root, args.revision, output, command)
        result['commands'] = command.records
        result['requires_actual_cli0_and_no_failed_receipt'] = True
        result['deadline_monotonic'] = deadline
        require(time.monotonic() < deadline, 'dependency finalization deadline')
        save(output / 'retained.json', result)
        require(time.monotonic() < deadline, 'late dependency receipt')
        print('Exact dependency retained; recovery and measurement remain separate.')
        return 0
    except BaseException as exc:
        save(output / 'failed.json', {'schema': 1, 'dependency_retained': False,
             'measurement_admitted': False, 'daemon_cancellation_proven': False,
             'error': f'{type(exc).__name__}: {exc}', 'commands': [] if command is None else command.records,
             'persistent_roots_removed': False})
        print('Dependency provisioning refused; private failure retained.', file=sys.stderr)
        return 1
    finally:
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)
        if lock is not None:
            os.close(lock)


if __name__ == '__main__':
    raise SystemExit(main())

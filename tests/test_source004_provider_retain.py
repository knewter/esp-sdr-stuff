"""Protocol/host fixtures only. No Nix, store, daemon or hardware operation."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('provider', Path(__file__).parents[1] / 'tools/source004_provider_retain.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
REVISION = '1' * 40
DERIVATION = '/nix/store/' + '0' * 32 + '-nix-2.34.8.drv'
DEP = '/nix/store/' + '1' * 32 + '-runtime'
SOURCES = {'project': '/nix/store/' + '2' * 32 + '-source', 'nixpkgs': '/nix/store/' + '3' * 32 + '-source'}
NAR = 'sha256-' + 'A' * 43 + '='


def effective():
    wanted = {'plugin-files': [], 'pure-eval': True, 'allow-import-from-derivation': False,
              'allow-unsafe-native-code-during-evaluation': False, 'accept-flake-config': False,
              'flake-registry': '', 'use-registries': False, 'nix-path': [], 'builders': '',
              'max-jobs': 1, 'substitute': True, 'substituters': ['https://cache.nixos.org/'],
              'trusted-public-keys': [p.SETTINGS['trusted-public-keys']], 'require-sigs': True,
              'experimental-features': ['nix-command', 'flakes', 'fetch-tree']}
    return {key: {'value': value} for key, value in wanted.items()}


def closure():
    return {p.PROVIDER: {'version': 1, 'storeDir': '/nix/store', 'narHash': NAR, 'narSize': 1, 'references': [DEP]},
            DEP: {'version': 1, 'storeDir': '/nix/store', 'narHash': NAR, 'narSize': 2, 'references': []}}


class Fixture:
    """Model CLI results at a captured command boundary; never fabricate OS reads."""
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.records = []
        self.fail_at = None
        self.mutate = {}
        self.link = None
        self.selection = {'provider': p.PROVIDER, 'derivation': DERIVATION, 'selected_sources': SOURCES}

    def __call__(self, name, argv):
        self.calls.append((name, argv))
        self.records.append({'modeled': True, 'name': name, 'argv': argv})
        if name == self.fail_at:
            raise RuntimeError('injected CLI failure')
        if name in self.mutate:
            return self.mutate[name]
        if name.startswith('head-'):
            return (REVISION + '\n').encode()
        if name.startswith('clean-'):
            return b''
        if name.startswith('source-'):
            return (self.root / argv[-1].split(':', 1)[1]).read_bytes()
        if name.endswith('-config'):
            return json.dumps(effective()).encode()
        if name == 'select':
            return json.dumps(self.selection).encode()
        if name == 'retained-input-paths':
            return json.dumps({path: {'version': 1, 'storeDir': '/nix/store', 'narHash': NAR, 'narSize': 1, 'references': []}
                               for path in (*SOURCES.values(), p.BOOTSTRAP_OUTPUT)}).encode()
        if name.startswith('root-register-'):
            Path(argv[argv.index('--add-root') + 1]).symlink_to(argv[-1])
            return (str(Path(argv[argv.index('--add-root') + 1])) + '\n').encode()
        if name.startswith(('root-verify-', 'root-terminal-')):
            role = name.rsplit('-', 1)[1]
            link = next(self.root.glob('.vendor/source004-nix-roots/*/input-' + role))
            return (str(link) + ' -> ' + argv[-1] + '\n').encode()
        if name == 'build-provider':
            # Local harmless synthetic root. Runtime target validation is separately
            # covered with an actual local symlink, never /nix/store writes.
            self.link = Path(argv[-1])
            self.link.symlink_to(p.PROVIDER)
            return json.dumps([{'drvPath': DERIVATION, 'outputs': {'out': p.PROVIDER}}]).encode()
        if name.startswith('roots-'):
            link = self.link or next(self.root.glob('.vendor/source004-nix-roots/*/provider'))
            return (str(link) + ' -> ' + argv[-1] + '\n').encode()
        if name == 'runtime-closure':
            return json.dumps(closure()).encode()
        if name == 'runtime-requisites':
            return (p.PROVIDER + '\n' + DEP + '\n').encode()
        raise AssertionError((name, argv))


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in p.SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('fixture source ' + name).encode())
        self.out = self.root / '.scratch/attempt001'
        self.out.mkdir(parents=True, mode=0o700)
        self.fixture = Fixture(self.root)
        self.mock_root = patch.object(p, 'verify_root', side_effect=lambda link, selected, raw:
                                     {'path': str(link), 'target': selected, 'registered_roots': raw.decode().splitlines()})
        self.mock_receipt = patch.object(p, 'file_receipt', return_value={'path': 'modeled executable', 'bytes': 1, 'sha256': '0' * 64})
        self.mock_root.start()
        self.mock_receipt.start()
        self.addCleanup(self.mock_root.stop)
        self.addCleanup(self.mock_receipt.stop)

    def run_protocol(self):
        return p.retain(self.root, REVISION, self.out, self.fixture)

    def test_complete_exact_selection_build_root_and_closure(self):
        result = self.run_protocol()
        self.assertTrue(result['dependency_retained'])
        self.assertFalse(result['measurement_admitted'])
        self.assertFalse(result['recovery_performed'])
        self.assertEqual(set(result['closure']), {p.PROVIDER, DEP})
        calls = dict(self.fixture.calls)
        self.assertEqual(len(calls), len(self.fixture.calls))
        self.assertEqual([name for name, _ in self.fixture.calls],
                         ['head-initial', 'clean-initial', *['source-' + str(i) for i in range(5)],
                          'bootstrap-config', 'select', 'retained-input-paths',
                          *[name + role for role in ('bootstrap', 'nixpkgs', 'project')
                            for name in ('root-register-', 'root-verify-')],
                          'build-provider', 'roots-final',
                          'runtime-closure', 'runtime-requisites', 'provider-config',
                          'head-final', 'clean-final', 'roots-terminal',
                          *['root-terminal-' + role for role in ('bootstrap', 'nixpkgs', 'project')]])
        build = calls['build-provider']
        self.assertEqual(build[0], p.BOOTSTRAP)
        self.assertIn('--no-write-lock-file', build)
        self.assertIn('--no-update-lock-file', build)
        self.assertEqual(build[build.index('--expr') + 1], p.expression(self.root, REVISION) + 'p')
        self.assertEqual(build[build.index('--expr') + 2], '^out')
        self.assertEqual(build[-2], '--out-link')
        self.assertTrue(build[-1].endswith('/' + result['tuple_digest'] + '/provider'))
        self.assertEqual(calls['runtime-closure'][-4:], ['--json', '--json-format', '1', p.PROVIDER])
        self.assertTrue(all('root:prepare' not in arg for _, argv in self.fixture.calls for arg in argv))

    def test_equal_version_different_provider_refused_before_root_build(self):
        self.fixture.selection['provider'] = '/nix/store/' + '4' * 32 + '-nix-2.34.8'
        with self.assertRaisesRegex(ValueError, 'selected provider'):
            self.run_protocol()
        self.assertNotIn('build-provider', dict(self.fixture.calls))
        self.assertFalse((self.root / '.vendor').exists())

    def test_revision_mismatch_stops_before_selection(self):
        self.fixture.mutate['head-initial'] = b'2' * 40
        with self.assertRaisesRegex(ValueError, 'revision mismatch'):
            self.run_protocol()
        self.assertEqual(len(self.fixture.calls), 1)

    def test_dirty_checkout_stops(self):
        self.fixture.mutate['clean-initial'] = b' M flake.lock\n'
        with self.assertRaisesRegex(ValueError, 'dirty'):
            self.run_protocol()
        self.assertEqual(len(self.fixture.calls), 2)

    def test_committed_source_mismatch_stops_before_selection(self):
        self.fixture.mutate['source-2'] = b'other Task bytes'
        with self.assertRaisesRegex(ValueError, 'not committed'):
            self.run_protocol()
        self.assertNotIn('select', dict(self.fixture.calls))

    def test_exact_tuple_mismatch_never_overwrites(self):
        result = self.run_protocol()
        tuple_file = Path(result['root']['path']).parent / 'tuple.json'
        tuple_file.chmod(0o600)
        tuple_file.write_bytes(b'foreign tuple')
        self.out = self.root / '.scratch/attempt002'
        self.out.mkdir()
        self.fixture.calls.clear()
        with self.assertRaisesRegex(ValueError, 'tuple mismatch'):
            self.run_protocol()
        self.assertEqual(tuple_file.read_bytes(), b'foreign tuple')
        self.assertNotIn('build-provider', dict(self.fixture.calls))

    def test_existing_root_verified_without_build(self):
        self.run_protocol()
        self.out = self.root / '.scratch/attempt002'
        self.out.mkdir()
        self.fixture.calls.clear()
        result = self.run_protocol()
        self.assertTrue(result['existing_root_verified'])
        self.assertIn('roots-initial', dict(self.fixture.calls))
        self.assertNotIn('build-provider', dict(self.fixture.calls))

    def test_stale_root_failure_no_build_or_overwrite(self):
        result = self.run_protocol()
        link = Path(result['root']['path'])
        self.out = self.root / '.scratch/attempt002'
        self.out.mkdir()
        self.fixture.calls.clear()
        with patch.object(p, 'verify_root', side_effect=ValueError('stale provider root')):
            with self.assertRaisesRegex(ValueError, 'stale'):
                self.run_protocol()
        self.assertEqual(os.readlink(link), p.PROVIDER)
        self.assertNotIn('build-provider', dict(self.fixture.calls))

    def test_failed_build_is_not_retried_tuple_kept(self):
        self.fixture.fail_at = 'build-provider'
        with self.assertRaisesRegex(RuntimeError, 'CLI failure'):
            self.run_protocol()
        self.assertEqual([n for n, _ in self.fixture.calls].count('build-provider'), 1)
        self.assertEqual(len(list(self.root.glob('.vendor/source004-nix-roots/*/tuple.json'))), 1)
        self.assertFalse(list(self.root.glob('.vendor/source004-nix-roots/*/provider')))

    def test_source_derived_registration_requires_root_path_not_target(self):
        # opRealise prints realisePath's addPermRoot result (root), not target.
        self.fixture.mutate['root-register-bootstrap'] = (p.BOOTSTRAP_OUTPUT + '\n').encode()
        with self.assertRaisesRegex(ValueError, 'exact root path'):
            self.run_protocol()
        self.assertNotIn('root-register-nixpkgs', dict(self.fixture.calls))
        self.assertNotIn('build-provider', dict(self.fixture.calls))

    def test_retained_input_missing_denies_before_registration_or_build(self):
        self.fixture.mutate['retained-input-paths'] = json.dumps({p.BOOTSTRAP_OUTPUT: None}).encode()
        with self.assertRaisesRegex(ValueError, 'input paths'):
            self.run_protocol()
        self.assertNotIn('build-provider', dict(self.fixture.calls))
        self.assertFalse(any(name.startswith('root-register-') for name, _ in self.fixture.calls))

    def test_input_registration_failure_keeps_prefix_without_provider_build(self):
        self.fixture.fail_at = 'root-register-nixpkgs'
        with self.assertRaisesRegex(RuntimeError, 'CLI failure'):
            self.run_protocol()
        self.assertEqual([name for name, _ in self.fixture.calls].count('root-register-nixpkgs'), 1)
        self.assertTrue(list(self.root.glob('.vendor/source004-nix-roots/*/input-bootstrap')))
        self.assertNotIn('build-provider', dict(self.fixture.calls))

    def test_registration_only_settings_never_realize_missing_outputs(self):
        self.run_protocol()
        call = dict(self.fixture.calls)['root-register-project']
        options = {call[i + 1]: call[i + 2] for i, arg in enumerate(call) if arg == '--option'}
        self.assertEqual(options['substitute'], 'false')
        self.assertEqual(options['max-jobs'], '0')
        self.assertEqual(options['substituters'], '')
        self.assertEqual(call[-1], SOURCES['project'])

    def test_unexpected_build_output_refused(self):
        self.fixture.mutate['build-provider'] = json.dumps([{'drvPath': DERIVATION, 'outputs': {'out': p.PROVIDER, 'extra': DEP}}]).encode()
        with self.assertRaisesRegex(ValueError, 'realized'):
            self.run_protocol()
        self.assertNotIn('runtime-closure', dict(self.fixture.calls))

    def test_changed_final_source_refused(self):
        orig = self.fixture.__call__
        def command(name, argv):
            raw = orig(name, argv)
            if name == 'head-final':
                (self.root / 'Taskfile.yml').write_bytes(b'changed')
            return raw
        with self.assertRaisesRegex(ValueError, 'source changed'):
            p.retain(self.root, REVISION, self.out, command)

    def test_terminal_registration_failure_denies_result_keeps_root(self):
        self.fixture.fail_at = 'roots-terminal'
        with self.assertRaisesRegex(RuntimeError, 'CLI failure'):
            self.run_protocol()
        self.assertTrue(self.fixture.link.is_symlink())


    def test_main_fixture_success_and_same_output_refusal_no_extra_commands(self):
        (self.root / '.git').mkdir()
        self.out.rmdir()
        args = ['--root', str(self.root), '--revision', REVISION, '--output', str(self.out), '--seconds', '5']
        def tool(path):
            sha = p.BOOTSTRAP_SHA if str(path) == p.BOOTSTRAP else p.GIT_SHA if str(path) == p.GIT else p.PYTHON_SHA
            return {'path': str(path), 'bytes': 1, 'sha256': sha}
        with patch.object(p, '__file__', str(self.root / 'tools/source004_provider_retain.py')), \
             patch.object(p, 'file_receipt', side_effect=tool), \
             patch.object(p, 'Commands', return_value=self.fixture):
            self.assertEqual(p.main(args), 0)
            saved = json.loads((self.out / 'retained.json').read_bytes())
            self.assertTrue(saved['requires_actual_cli0_and_no_failed_receipt'])
            self.assertEqual(len(saved['commands']), 27)
            self.assertTrue((self.out / 'imports.json').exists())
            before = list(self.fixture.calls)
            with self.assertRaisesRegex(ValueError, 'new output'):
                p.main(args)
            self.assertEqual(before, self.fixture.calls)

    def test_main_fixture_failed_build_retains_terminal_no_success(self):
        (self.root / '.git').mkdir()
        self.out.rmdir()
        self.fixture.fail_at = 'build-provider'
        def tool(path):
            sha = p.BOOTSTRAP_SHA if str(path) == p.BOOTSTRAP else p.GIT_SHA if str(path) == p.GIT else p.PYTHON_SHA
            return {'path': str(path), 'bytes': 1, 'sha256': sha}
        with patch.object(p, '__file__', str(self.root / 'tools/source004_provider_retain.py')), \
             patch.object(p, 'file_receipt', side_effect=tool), \
             patch.object(p, 'Commands', return_value=self.fixture):
            status = p.main(['--root', str(self.root), '--revision', REVISION, '--output', str(self.out), '--seconds', '5'])
        self.assertEqual(status, 1)
        self.assertFalse((self.out / 'retained.json').exists())
        failed = json.loads((self.out / 'failed.json').read_bytes())
        self.assertFalse(failed['dependency_retained'])
        self.assertFalse(failed['persistent_roots_removed'])
        self.assertEqual([r['name'] for r in failed['commands']].count('build-provider'), 1)


class ValidationTests(unittest.TestCase):
    def test_whole_closure_reference_and_count_conservation(self):
        original = closure()
        variants = []
        dropped = copy.deepcopy(original); del dropped[DEP]; variants.append(dropped)
        duplicate = copy.deepcopy(original); duplicate[p.PROVIDER]['references'].append(DEP); variants.append(duplicate)
        unrelated = copy.deepcopy(original); unrelated['/nix/store/' + '4' * 32 + '-other'] = copy.deepcopy(original[DEP]); variants.append(unrelated)
        wrong_format = copy.deepcopy(original); wrong_format[DEP]['version'] = 2; variants.append(wrong_format)
        malformed = copy.deepcopy(original); malformed[DEP]['narSize'] = True; variants.append(malformed)
        for value in variants:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    p.validate_closure(json.dumps(value).encode(), ('\n'.join(value) + '\n').encode())
        with self.assertRaisesRegex(ValueError, 'conservation'):
            p.validate_closure(json.dumps(original).encode(), (p.PROVIDER + '\n' + DEP + '\n' + DEP).encode())

    def test_config_plugin_registry_fallback_and_build_policy(self):
        for key, value in [('plugin-files', ['foreign.so']), ('use-registries', True), ('max-jobs', 0),
                           ('substituters', ['https://foreign.example/']), ('allow-import-from-derivation', True)]:
            config = effective(); config[key]['value'] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'config mismatch'):
                p.validate_config(json.dumps(config).encode())
        config = effective(); config['nix-bin-dir'] = {'value': 'bootstrap dependent default'}
        self.assertNotIn('nix-bin-dir', p.validate_config(json.dumps(config).encode()))

    def test_actual_local_symlink_requires_actual_reported_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'provider-fixture'; target.mkdir()
            link = Path(tmp) / 'root'; link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'registered'):
                p.verify_root(link, str(target), b'other root\n')
            p.verify_root(link, str(target), (str(link) + ' -> ' + str(target) + '\n').encode())
            link.unlink(); link.symlink_to(Path(tmp) / 'missing')
            with self.assertRaises((ValueError, FileNotFoundError)):
                p.verify_root(link, str(Path(tmp) / 'missing'), (str(link) + ' -> ' + str(Path(tmp) / 'missing') + '\n').encode())

    def test_source_derived_qroots_rejects_bare_wrong_duplicate_or_missing_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'provider-fixture'; target.mkdir()
            link = Path(tmp) / 'root'; link.symlink_to(target)
            actual = str(link) + ' -> ' + str(target) + '\n'
            p.verify_root(link, str(target), actual.encode())
            for raw in (str(link) + '\n', str(link) + ' -> other\n', actual + actual,
                        'other-root -> ' + str(target) + '\n'):
                with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'registered'):
                    p.verify_root(link, str(target), raw.encode())
            # Valid referrer roots may accompany the exact own pair.
            p.verify_root(link, str(target), (actual + 'other-root -> other-referrer\n').encode())

    def test_private_tree_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / 'outside'; target.mkdir()
            (root / '.vendor').symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'directory'):
                p.private_tree(root / '.vendor/roots', root)
            self.assertFalse((target / 'roots').exists())

    def test_private_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'canonical'):
                p.private_tree(root / '.scratch/../outside', root, final_private=False)
            self.assertFalse((root / 'outside').exists())

    def test_environment_does_not_inherit_ambient_variables(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'NIX_CONFIG': 'plugin-files = poison', 'LD_PRELOAD': 'poison'}):
            env = p.controlled_environment(Path(tmp))
            self.assertNotIn('LD_PRELOAD', env)
            self.assertEqual(env['NIX_CONFIG'], '')
            self.assertEqual((Path(env['NIX_CONF_DIR']) / 'nix.conf').read_bytes(), p.CONFIG)

    def test_output_is_exclusive_and_durable_failure_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'receipt'; p.save(output, {'failed': True})
            with self.assertRaises(FileExistsError):
                p.save(output, {'retained': True})
            self.assertEqual(json.loads(output.read_bytes()), {'failed': True})


class ActualCommandFixtures(unittest.TestCase):
    def test_actual_harmless_cli_logs_terminal_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command = p.Commands(root, {'LC_ALL': 'C'}, 5)
            self.assertEqual(command('positive', [sys.executable, '-B', '-c', 'print("fixture")']), b'fixture\n')
            with self.assertRaisesRegex(ValueError, 'command failed'):
                command('negative', [sys.executable, '-B', '-c', 'import sys; print("failed fixture"); sys.exit(7)'])
            self.assertEqual([r['returncode'] for r in command.records], [0, 7])
            self.assertEqual((root / '01-negative.stdout').read_bytes(), b'failed fixture\n')
            self.assertFalse(command.records[1]['daemon_cancellation_proven'])
            self.assertEqual(len(list(root.glob('*.terminal.json'))), 2)

    def test_actual_log_overflow_refuses_and_retains_prefix(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'LIMIT', 4096):
            command = p.Commands(Path(tmp), {'LC_ALL': 'C'}, 5)
            with self.assertRaisesRegex(ValueError, 'overflow'):
                command('overflow', [sys.executable, '-B', '-c', 'print("x"*10000)'])
            self.assertIsNotNone(command.records[0]['error'])
            self.assertFalse((Path(tmp) / 'retained.json').exists())

    def test_actual_owned_client_timeout_pidfd_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = p.Commands(Path(tmp), {'LC_ALL': 'C'}, 0.15)
            with self.assertRaisesRegex(ValueError, 'deadline'):
                command('deadline', [sys.executable, '-B', '-c', 'import time; time.sleep(2)'])
            self.assertEqual(command.records[0]['returncode'], -9)
            self.assertFalse(command.records[0]['daemon_cancellation_proven'])


if __name__ == '__main__':
    unittest.main()

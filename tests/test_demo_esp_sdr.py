"""Synthetic lifecycle and provenance tests; no USB/serial/radio operation."""
import contextlib
import copy
import hashlib
import zlib
from http.server import ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import demo_esp_sdr as demo
import esp_sdr_spectrum_bridge as spectrum_bridge
import test_spectrum_trial_integrity as spectrum_fixture


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = SimpleNamespace(action='run', output=self.root / 'docs/evidence/fresh',
            private=self.root / '.scratch/fresh', artifact=self.root / 'artifact',
            manifest=self.root / 'artifact/manifest.json', baud=921600,
            port=demo.STABLE_PORT, http_port=0, seconds=60, bins=512,
            frequency=2412, rate=80000000, bandwidth=20, gain='hardware',
            headless=True, start_timeout=120)
        self.a.ffts_per_frame = 8
        self.baseline = {'bytes': demo.SIZE, 'sha256': 'a' * 64, 'read_hashes_equal': True}

    def make_artifact(self):
        (self.a.artifact / 'esp32').mkdir(parents=True)
        parts = []
        for i, (name, offset) in enumerate([('0-bootloader.bin', 4096),
            ('1-partition-table.bin', 32768), ('2-esp_sdr.bin', 65536)]):
            data = bytes([i]) * 64
            (self.a.artifact / 'esp32' / name).write_bytes(data)
            parts.append({'name': name, 'offset': offset, 'size': len(data),
                          'sha256': hashlib.sha256(data).hexdigest()})
        self.manifest = {'version': '550fade-uart921600', 'variants': {'esp32':
            {'target': 'esp32', 'version': '550fade-uart921600', 'parts': parts}}}
        self.build = {'source_commit': demo.SOURCE_REVISION, 'idf_commit': demo.flash_trial.SDK_REVISION,
            'target': 'esp32', 'app_version': '550fade-uart921600', 'source_code_patch': None,
            'configuration_difference_from_upstream_defaults': {'CONFIG_ESP_SDR_UART_BAUD': 921600}}
        self.save_artifact()

    def save_artifact(self):
        demo.write_json(self.a.manifest, self.manifest)
        demo.write_json(self.a.manifest.with_name('build-info.json'), self.build)


class ProvenanceTests(Fixtures):
    def test_help_is_hardware_free_and_defaults_are_the_proven_512_profile(self):
        with patch.object(demo, 'identity_check') as device, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                demo.parser().parse_args(['--help'])
        self.assertEqual(result.exception.code, 0); device.assert_not_called()
        args = demo.parser().parse_args(['--output', 'docs/evidence/x', '--private', '.scratch/x'])
        self.assertEqual((args.seconds, args.baud, args.bins), (60, 921600, 512))
        self.assertEqual(args.ffts_per_frame, 8)

    def test_pinned_clean_uart_variant_and_payload_hashes_are_required(self):
        self.make_artifact()
        self.assertEqual(demo.receiver_profile(self.a.artifact, self.a.manifest, 921600), '550fade-uart921600')
        original = copy.deepcopy(self.build)
        for key, value in [('source_commit', 'unreviewed'), ('idf_commit', 'unreviewed'),
                           ('source_code_patch', 'unreviewed.patch'), ('target', 'esp32s3')]:
            with self.subTest(key=key):
                self.build = copy.deepcopy(original); self.build[key] = value; self.save_artifact()
                with self.assertRaises(RuntimeError):
                    demo.receiver_profile(self.a.artifact, self.a.manifest, 921600)
        self.build = original; self.save_artifact()
        with self.assertRaises(RuntimeError):
            demo.receiver_profile(self.a.artifact, self.a.manifest, 1000000)
        (self.a.artifact / 'esp32/2-esp_sdr.bin').write_bytes(b'wrong')
        with self.assertRaisesRegex(RuntimeError, 'hash or size'):
            demo.receiver_profile(self.a.artifact, self.a.manifest, 921600)

    def test_part_traversal_overlap_and_missing_parts_are_rejected(self):
        self.make_artifact(); original = copy.deepcopy(self.manifest)
        for field, value in [('name', '../wrong.bin'), ('offset', 0), ('size', 0x7001)]:
            self.manifest = copy.deepcopy(original)
            self.manifest['variants']['esp32']['parts'][0][field] = value; self.save_artifact()
            with self.assertRaises(RuntimeError):
                demo.receiver_profile(self.a.artifact, self.a.manifest, 921600)
        self.manifest = copy.deepcopy(original)
        self.manifest['variants']['esp32']['parts'].pop(); self.save_artifact()
        with self.assertRaisesRegex(RuntimeError, 'part count'):
            demo.receiver_profile(self.a.artifact, self.a.manifest, 921600)

    def test_public_paths_private_paths_and_freshness_are_checked(self):
        with patch.object(demo, 'ROOT', self.root), patch.object(demo.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
            self.assertEqual(demo.validate_paths(self.a.output, self.a.private), (self.a.output, self.a.private))
            for public, private in [(self.root / 'site/x', self.a.private),
                                    (self.a.output, self.root / 'docs/evidence/.scratch/x'),
                                    (self.a.output, self.root / '.scratch/../../elsewhere')]:
                with self.assertRaises(RuntimeError):
                    demo.validate_paths(public, private)
            self.a.private.mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, 'fresh'):
                demo.validate_paths(self.a.output, self.a.private)

    def test_git_tracked_private_path_is_rejected(self):
        with patch.object(demo, 'ROOT', self.root), patch.object(demo.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(RuntimeError, 'ignored'):
                demo.validate_paths(self.a.output, self.a.private)

    def test_second_private_preservation_image_is_independently_hash_checked(self):
        folder = self.root / 'backups'; folder.mkdir()
        data = b'\xff' * demo.SIZE
        for name in ('original.bin', 'readback.bin'):
            (folder / name).write_bytes(data)
        self.baseline['sha256'] = hashlib.sha256(data).hexdigest()
        self.baseline['independent_reads'] = 2
        manifest = self.root / 'docs/evidence/firmware-preservation/manifest.json'
        manifest.parent.mkdir(parents=True); demo.write_json(manifest, self.baseline)
        with patch.object(demo, 'ROOT', self.root):
            self.assertEqual(demo.baseline_check()['sha256'], self.baseline['sha256'])
            (folder / 'readback.bin').write_bytes(b'x' * demo.SIZE)
            with self.assertRaisesRegex(RuntimeError, 'Second preserved'):
                demo.baseline_check()


class LifecycleTests(Fixtures):
    def run_fixture(self, flash_error=None, capture_error=None, restore_error=None, unexpected_current=False):
        self.events = []
        def flash(action, args):
            self.events.append(action)
            if flash_error:
                raise flash_error
        def capture(args, listener):
            try:
                self.events.append('capture')
                if capture_error:
                    raise capture_error
                return copy.deepcopy(getattr(self, 'capture_result', {'status': 'completed',
                    'elapsed_seconds': 60.01, 'end_report': [0, 0, 1, 512, 60000001]}))
            finally:
                if isinstance(capture_error, demo.OwnedHardwareClosureError):
                    args.owned_worker_closed = False
                    self.events.append('owned_worker_unconfirmed')
                else:
                    self.events.append('owned_worker_closed')
                listener.close()
        def restore(args, baseline):
            self.events.append('restore')
            if restore_error:
                raise restore_error
            return {'verified': True}
        def current(args, baseline):
            self.events.append('current_read')
            if unexpected_current:
                raise RuntimeError('Unknown image; do not overwrite')
        with patch.object(demo, 'validate_paths', return_value=(self.a.output, self.a.private)), \
            patch.object(demo, 'baseline_check', return_value=self.baseline), \
            patch.object(demo, 'receiver_profile', return_value='550fade-uart921600'), \
            patch.object(demo, 'identity_check'), patch.object(demo, 'flash', side_effect=flash), \
            patch.object(demo, 'live_view', side_effect=capture), \
            patch.object(demo, 'installed_provenance', return_value={'parts': []}), \
            patch.object(demo, 'current_baseline_check', side_effect=current), \
            patch.object(demo, 'restore_verified', side_effect=restore), \
            patch.dict(os.environ, {'CHROMIUM_EXECUTABLE': '/nix/store/synthetic/bin/chromium'}), \
            contextlib.redirect_stdout(io.StringIO()):
            code = demo.lifecycle(self.a)
        self.record = json.loads((self.a.output / 'demo.json').read_text())
        return code

    def test_success_reads_current_state_closes_capture_then_restores(self):
        self.assertEqual(self.run_fixture(), 0)
        self.assertEqual(self.events, ['current_read', 'install', 'capture', 'owned_worker_closed', 'restore'])
        self.assertEqual(self.record['restoration_status'], 'verified')
        self.assertEqual(self.a.private.stat().st_mode & 0o777, 0o700)

    def test_partial_failed_install_still_attempts_restoration(self):
        self.assertEqual(self.run_fixture(flash_error=RuntimeError('partial write')), 2)
        self.assertEqual(self.events, ['current_read', 'install', 'restore'])
        self.assertEqual(self.record['restoration_status'], 'verified')

    def test_unclosed_flash_subprocess_blocks_competing_restoration(self):
        self.assertEqual(self.run_fixture(flash_error=demo.OwnedHardwareClosureError('unkillable esptool')), 2)
        self.assertEqual(self.events, ['current_read', 'install'])
        self.assertEqual(self.record['restoration_status'], 'blocked_owned_worker_not_closed')

    def test_signal_cancellation_closes_capture_before_restore_and_remains_failed(self):
        self.assertEqual(self.run_fixture(capture_error=demo.Cancelled('cancel')), 2)
        self.assertEqual(self.events[-2:], ['owned_worker_closed', 'restore'])
        self.assertEqual(self.record['error_kind'], 'Cancelled')

    def test_failed_capture_and_failed_restoration_are_both_recorded(self):
        self.assertEqual(self.run_fixture(capture_error=RuntimeError('/private/path device-address'),
            restore_error=RuntimeError('restore failure')), 2)
        self.assertEqual(self.record['restoration_status'], 'failed')
        public = (self.a.output / 'demo.json').read_text()
        self.assertNotIn('/private/path', public)
        self.assertNotIn(demo.STABLE_PORT, public)
        self.assertTrue((self.a.private / 'restore-failure.json').exists())

    def test_unconfirmed_owned_worker_exit_blocks_restoration(self):
        self.assertEqual(self.run_fixture(capture_error=demo.OwnedHardwareClosureError('unkillable')), 2)
        self.assertNotIn('restore', self.events)
        self.assertFalse(self.record['owned_uart_worker_exit_confirmed'])
        self.assertEqual(self.record['restoration_status'], 'blocked_owned_worker_not_closed')

    def test_strict_host_duration_failure_is_public_without_discarding_bridge_outcome(self):
        self.capture_result = {'status': 'completed', 'elapsed_seconds': 59.99,
                              'end_report': [0, 0, 1, 512, 60000001], 'frames': 42}
        self.assertEqual(self.run_fixture(), 2)
        spectrum = json.loads((self.a.output / 'spectrum.json').read_text())
        self.assertEqual((spectrum['status'], spectrum['bridge_status'], spectrum['frames']), ('failed', 'completed', 42))
        self.assertFalse(spectrum['demo_duration_check']['host_reached_requested_duration'])
        self.assertEqual(self.record['capture_status'], 'failed')
        self.assertEqual(self.record['restoration_status'], 'verified')

    def test_strict_firmware_duration_failure_is_public_without_discarding_bridge_outcome(self):
        self.capture_result = {'status': 'completed', 'elapsed_seconds': 60.01,
                              'end_report': [0, 0, 1, 512, 59999999], 'frames': 42}
        self.assertEqual(self.run_fixture(), 2)
        spectrum = json.loads((self.a.output / 'spectrum.json').read_text())
        self.assertEqual(spectrum['status'], 'failed')
        self.assertFalse(spectrum['demo_duration_check']['firmware_reached_requested_duration'])

    def test_installed_part_hashes_and_source_provenance_are_published(self):
        self.make_artifact()
        self.a.firmware_revision = '550fade-uart921600'
        folder = self.a.private / 'install'; folder.mkdir(parents=True)
        parts = self.manifest['variants']['esp32']['parts']
        demo.write_json(folder / 'manifest.json', {'exit_code': 0,
            'firmware_variant': self.a.firmware_revision, 'parts': parts})
        result = demo.installed_provenance(self.a)
        self.assertEqual(result['parts'], parts)
        self.assertEqual(result['sdk_commit'], demo.flash_trial.SDK_REVISION)
        self.assertEqual(result['receiver_manifest_sha256'], demo.flash_trial.sha(self.a.manifest))

    def test_unexpected_current_firmware_is_retained_without_any_write(self):
        self.assertEqual(self.run_fixture(unexpected_current=True), 2)
        self.assertEqual(self.events, ['current_read'])
        self.assertEqual(self.record['restoration_status'], 'not_attempted')

    def test_restore_action_can_recover_an_arbitrary_current_image(self):
        self.a.action = 'restore'
        self.assertEqual(self.run_fixture(unexpected_current=True), 0)
        self.assertEqual(self.events, ['restore'])

    def test_restore_full_readback_mismatch_fails_before_boot(self):
        self.a.output.mkdir(parents=True)
        with patch.object(demo, 'flash') as flash, patch.object(demo, 'read_full_flash',
            return_value={'bytes': demo.SIZE, 'sha256': 'b' * 64}), patch.object(demo, 'observe_baseline_boot') as boot:
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                demo.restore_verified(self.a, self.baseline)
        boot.assert_not_called(); flash.assert_called_once_with('restore', self.a)
        self.assertFalse(json.loads((self.a.output / 'restoration.json').read_text())['full_readback_matches_baseline'])

    def test_byte_match_without_expected_baseline_boot_is_not_verified(self):
        self.a.output.mkdir(parents=True)
        with patch.object(demo, 'flash'), patch.object(demo, 'read_full_flash',
            return_value={'bytes': demo.SIZE, 'sha256': self.baseline['sha256']}), patch.object(demo, 'observe_baseline_boot',
            return_value={'application_identity_observed': False, 'sdk_observed': False,
                'gpio_high_observed': True, 'gpio_low_observed': True}):
            with self.assertRaisesRegex(RuntimeError, 'boot not observed'):
                demo.restore_verified(self.a, self.baseline)

    def test_cancelled_external_command_terminates_and_waits_before_return(self):
        self.a.private.mkdir(parents=True)
        proc = Mock(pid=123); proc.poll.return_value = None
        proc.wait.side_effect = [demo.Cancelled('operator'), None]
        with patch.object(demo.subprocess, 'Popen', return_value=proc), patch.object(demo.os, 'killpg') as kill, \
            patch.object(demo, 'group_exists', return_value=True), patch.object(demo, 'wait_group_gone', return_value=True):
            with self.assertRaises(demo.Cancelled):
                demo.execute(['synthetic-not-hardware'], self.a.private / 'log')
        kill.assert_called_once_with(123, signal.SIGTERM)
        self.assertEqual(proc.wait.call_count, 2)

    def test_unkillable_external_command_reports_typed_hardware_closure_failure(self):
        self.a.private.mkdir(parents=True)
        proc = Mock(pid=123); proc.poll.return_value = None
        proc.wait.side_effect = [2, subprocess.TimeoutExpired('synthetic', 8),
                                subprocess.TimeoutExpired('synthetic', 8)]
        with patch.object(demo.subprocess, 'Popen', return_value=proc), patch.object(demo.os, 'killpg') as kill, \
            patch.object(demo, 'group_exists', return_value=True), patch.object(demo, 'wait_group_gone', return_value=False):
            with self.assertRaises(demo.OwnedHardwareClosureError):
                demo.execute(['synthetic-not-hardware'], self.a.private / 'log')
        self.assertEqual([call.args for call in kill.call_args_list],
                         [(123, signal.SIGTERM), (123, signal.SIGKILL)])

    def test_cancellation_inside_hardware_spawn_is_deferred_until_cleanup_can_own_child(self):
        self.a.private.mkdir(parents=True)
        proc = Mock(pid=123); proc.wait.return_value = 0
        def spawn(*_, **__):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return proc
        with patch.object(demo.subprocess, 'Popen', side_effect=spawn), patch.object(demo.os, 'killpg') as kill, \
            patch.object(demo, 'group_exists', return_value=True), patch.object(demo, 'wait_group_gone', return_value=True):
            with self.assertRaises(demo.Cancelled):
                demo.execute(['synthetic-no-hardware'], self.a.private / 'spawn.log')
        kill.assert_called_once_with(123, signal.SIGTERM)
        proc.wait.assert_called_once()

    def test_cancellation_inside_viewer_spawn_registers_worker_then_closes_it(self):
        self.a.private.mkdir(parents=True); self.a.firmware_revision = 'synthetic'
        executable = self.root / 'synthetic-chromium'; executable.write_text('fixture')
        listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1)
        proc = Mock(pid=123); proc.wait.return_value = 0
        def spawn(*_, **__):
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
            return proc
        with patch.dict(os.environ, {'CHROMIUM_EXECUTABLE': str(executable)}), \
            patch.object(demo.subprocess, 'Popen', side_effect=spawn), patch.object(demo.os, 'killpg') as kill, \
            patch.object(demo, 'group_exists', return_value=True), patch.object(demo, 'wait_group_gone', return_value=True):
            with self.assertRaises((demo.Cancelled, KeyboardInterrupt)):
                demo.live_view(self.a, listener)
        self.assertTrue(self.a.owned_worker_closed)
        self.assertEqual(listener.fileno(), -1)
        kill.assert_called_once_with(123, signal.SIGTERM)

    def test_signal_during_restore_spawn_preserves_full_verification(self):
        proc = Mock(pid=123); proc.wait.return_value = 0
        def spawn(*_, **__):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return proc
        def flash(action, args):
            if action == 'restore':
                demo.execute(['synthetic-restoration-only'], args.private / 'synthetic-restore.log')
        def view(args, listener):
            listener.close()
            return {'status': 'completed', 'elapsed_seconds': 60.01,
                    'end_report': [0, 0, 1, 512, 60000001]}
        boot_result = {key: True for key in ('application_identity_observed', 'sdk_observed',
                                           'gpio_high_observed', 'gpio_low_observed')}
        with patch.object(demo, 'validate_paths', return_value=(self.a.output, self.a.private)), \
            patch.object(demo, 'baseline_check', return_value=self.baseline), patch.object(demo, 'identity_check'), \
            patch.object(demo, 'receiver_profile', return_value='550fade-uart921600'), \
            patch.object(demo, 'current_baseline_check'), patch.object(demo, 'installed_provenance', return_value={}), \
            patch.object(demo, 'live_view', side_effect=view), patch.object(demo, 'flash', side_effect=flash), \
            patch.object(demo, 'read_full_flash', return_value={'bytes': demo.SIZE, 'sha256': self.baseline['sha256']}) as read, \
            patch.object(demo, 'observe_baseline_boot', return_value=boot_result) as boot, \
            patch.object(demo.subprocess, 'Popen', side_effect=spawn), patch.object(demo.os, 'killpg'), \
            patch.object(demo, 'group_exists', return_value=True), patch.object(demo, 'wait_group_gone', return_value=True), \
            patch.dict(os.environ, {'CHROMIUM_EXECUTABLE': '/nix/store/fixture/bin/chromium'}), \
            contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(demo.lifecycle(self.a), 0)
        read.assert_called_once(); boot.assert_called_once()
        self.assertEqual(json.loads((self.a.output / 'demo.json').read_text())['restoration_status'], 'verified')

    def test_exited_leader_does_not_hide_a_surviving_group(self):
        proc = Mock(pid=123); proc.poll.return_value = 0; proc.wait.return_value = 0
        with patch.object(demo.os, 'killpg') as kill, patch.object(demo, 'group_exists', return_value=True), \
            patch.object(demo, 'wait_group_gone', side_effect=[False, True]):
            demo.stop_process(proc)
        self.assertEqual([call.args for call in kill.call_args_list],
                         [(123, signal.SIGTERM), (123, signal.SIGKILL)])

    def test_surviving_group_after_kill_is_a_typed_failure_even_when_leader_exited(self):
        proc = Mock(pid=123); proc.wait.return_value = 0
        with patch.object(demo.os, 'killpg'), patch.object(demo, 'group_exists', return_value=True), \
            patch.object(demo, 'wait_group_gone', return_value=False):
            with self.assertRaises(demo.OwnedHardwareClosureError):
                demo.stop_process(proc)

    def test_real_exited_leader_and_term_ignoring_descendant_release_fake_file(self):
        # A disposable supervisor becomes a subreaper so this test can reap its
        # own orphaned grandchild. The only held descriptor is a regular file.
        # No adapter/device paths or privileges are involved.
        code = r'''
import ctypes,json,os,signal,subprocess,sys,threading,time
sys.path.insert(0,sys.argv[1])
import demo_esp_sdr as demo
assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
child_code="import signal,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); f=open(sys.argv[1],'w'); f.write('held'); f.flush(); time.sleep(600)"
leader_code="import subprocess,sys; p=subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)"
leader=subprocess.Popen([sys.executable,'-c',leader_code,child_code,sys.argv[2]],stdout=subprocess.PIPE,text=True,start_new_session=True)
try:
 child=int(leader.stdout.readline()); leader.wait(timeout=3)
 deadline=time.monotonic()+3
 while not os.path.exists(sys.argv[2]) and time.monotonic()<deadline: time.sleep(.01)
 assert os.path.exists(sys.argv[2])
 assert demo.group_exists(leader.pid)
 reaped=[]
 def reap():
  reaped.append(os.waitpid(child,0)[0]==child)
 thread=threading.Thread(target=reap,daemon=True);thread.start()
 demo.stop_process(leader,grace_seconds=.3)
 thread.join(timeout=2)
 print(json.dumps({'leader_already_exited':True,'descendant_reaped':reaped==[True], 'group_gone':not demo.group_exists(leader.pid),'fake_descriptor_owner_gone':not os.path.exists(f'/proc/{child}/fd')}))
finally:
 try: os.killpg(leader.pid,signal.SIGKILL)
 except ProcessLookupError: pass
 leader.wait(timeout=2)
 leader.stdout.close()
'''
        result = subprocess.run([sys.executable, '-c', code, str(Path(demo.__file__).parent),
                                 str(self.root / 'synthetic-regular-file')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(json.loads(result.stdout).values()))

    def test_public_capture_removes_private_errors_protocol_strings(self):
        folder = self.a.private / 'capture-metadata'; folder.mkdir(parents=True)
        self.a.output.mkdir(parents=True)
        demo.write_json(folder / 'results.json', {'status': 'failed', 'frames': 2,
            'error': '/private/user/path 12:34:56:78:90:ab', 'error_kind': 'TimeoutError',
            'queries': {'untrusted': 'network name'}, 'setting_replies': {'x': 'unknown'},
            'private_frames_sha256': 'f' * 64})
        public = demo.publish_capture(self.a)
        self.assertNotIn('error', public); self.assertNotIn('queries', public)
        self.assertEqual(public['frames'], 2)


class ViewerBoundaryTests(unittest.TestCase):
    def test_local_server_displays_gaps_and_rejects_foreign_origin_and_wrong_token(self):
        trial = SimpleNamespace(lock=threading.Lock(), state={'status': 'Ready', 'frames': 0,
            'error': '/private/path'}, start=Mock(return_value=True))
        server = ThreadingHTTPServer(('127.0.0.1', 0), demo.viewer_handler(trial, 'synthetic-token'))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        url = f'http://127.0.0.1:{server.server_address[1]}'
        try:
            with urlopen(url) as response:
                html = response.read().decode()
            self.assertIn('separately acquired FFT snapshots', html)
            self.assertIn('reception gaps', html)
            self.assertIn('/start/synthetic-token', html)
            with urlopen(url + '/state') as response:
                self.assertNotIn('error', json.load(response))
            for path, origin in [('/start/wrong', url), ('/start/synthetic-token', 'https://foreign.invalid')]:
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url + path, data=b'{}', headers={'Origin': origin}))
                self.assertEqual(error.exception.code, 403)
            trial.start.assert_not_called()
            with urlopen(Request(url + '/start/synthetic-token', data=b'{}', headers={'Origin': url})) as response:
                self.assertEqual(response.status, 202)
            trial.start.assert_called_once()
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)


class CompletionFenceTests(unittest.TestCase):
    def test_atomic_terminal_publication_happens_after_all_csv_rows_close(self):
        original_replace = Path.replace
        observations = []
        def publish(source, target):
            if source.name == 'results.json.tmp':
                self.assertFalse(target.exists())
                self.assertEqual(json.loads(source.read_text())['frames'], 2)
                rows = source.with_name('spectra.csv').read_text().splitlines()
                self.assertEqual(len(rows), 3)
                observations.append(True)
            return original_replace(source, target)
        with patch.object(Path, 'replace', publish):
            result = spectrum_fixture.SpectrumTrialIntegrity().trial()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(observations, [True])

    def test_failed_csv_write_never_exposes_a_terminal_json_record(self):
        with patch.object(spectrum_bridge.csv.DictWriter, 'writerows', side_effect=OSError('synthetic storage failure')), \
            patch.object(Path, 'write_text') as publish:
            with self.assertRaisesRegex(OSError, 'storage failure'):
                spectrum_fixture.SpectrumTrialIntegrity().trial()
        publish.assert_not_called()

    def grouped_trial(self, frames, report, requested=8):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        wire = spectrum_fixture.Wire(b''.join(frames) + ('SPECEND ' + ' '.join(map(str, report)) + '\n').encode())
        args = SimpleNamespace(output=root/'metadata', private=root/'private', port='SYNTHETIC', baud=921600,
            frequency=2412, bandwidth=20, gain='hardware', seconds=60, rate=80000000, bins=256,
            ffts_per_frame=requested)
        requests = []
        def request(port, command):
            requests.append(command)
            return 'SPEC 256 80000000 256 2412' if command.startswith('SPEC ') else 'OK'
        tick = iter(range(0, 1000, 30))
        with patch.object(spectrum_bridge, 'open_board', return_value=wire), \
            patch.object(spectrum_bridge, 'synchronize'), patch.object(spectrum_bridge, 'queries', return_value={}), \
            patch.object(spectrum_bridge, 'settings', return_value={}), \
            patch.object(spectrum_bridge, 'command', side_effect=request), \
            patch.object(spectrum_bridge.time, 'monotonic', side_effect=lambda: next(tick)), \
            contextlib.redirect_stdout(io.StringIO()):
            trial = spectrum_bridge.Trial(args)
            trial.run()
            self.grouped_state = dict(trial.state)
        self.assertTrue(wire.closed)
        return args, json.loads((args.output/'results.json').read_text()), requests

    def grouped_frame(self, sequence, index, ffts=8):
        raw = spectrum_fixture.fft_frame(sequence, index, pairs=256*ffts)
        raw[20:22] = ffts.to_bytes(2, 'little')
        raw[-4:] = zlib.crc32(raw[:-4]).to_bytes(4, 'little')
        return bytes(raw)

    def test_eight_fft_command_frames_and_terminal_totals_match(self):
        frames = [self.grouped_frame(0, 0), self.grouped_frame(1, 80000000)]
        args, record, requests = self.grouped_trial(frames, [0,0,16,4096,60000000,0,0,2,0,0,16,0])
        self.assertIn('SPEC 60000 1 8 0 0 256 1', requests)
        self.assertEqual(record['status'], 'completed')
        self.assertEqual((record['frames'], record['accepted_ffts'], record['accepted_sample_pairs']), (2,16,4096))
        self.assertEqual(record['settings']['ffts_per_frame'], 8)
        self.assertEqual(record['nominal_sampled_seconds'], 4096/80000000)

    def test_completed_viewer_uses_terminal_elapsed_and_coverage(self):
        frames = [self.grouped_frame(0, 0), self.grouped_frame(1, 80000000)]
        _, record, _ = self.grouped_trial(frames, [0,0,16,4096,60000000,0,0,2,0,0,16,0])
        self.assertTrue(self.grouped_state['status'].startswith('Completed'))
        self.assertEqual(self.grouped_state['elapsed_seconds'], record['elapsed_seconds'])
        self.assertEqual(self.grouped_state['nominal_coverage_fraction'], record['nominal_coverage_fraction'])
        self.assertEqual(self.grouped_state['last_frame_received_seconds'], 60)
        self.assertGreater(self.grouped_state['elapsed_seconds'], self.grouped_state['last_frame_received_seconds'])

    def test_crc_rejection_retains_exact_bad_bytes_and_valid_prefix(self):
        first = self.grouped_frame(0, 0)
        bad = bytearray(self.grouped_frame(1, 80000000)); bad[40] ^= 1
        args, record, _ = self.grouped_trial([first, bytes(bad)], [0,0,16,4096,60000000,0,0,2,0,0,16,0])
        self.assertEqual(record['status'], 'failed')
        self.assertEqual((record['frames'], record['accepted_ffts'], record['accepted_sample_pairs']), (1,8,2048))
        self.assertEqual((args.private/'rejected-frame.bin').read_bytes(), bytes(bad))
        self.assertEqual((args.private/'spectrum-frames.bin').read_bytes(), first)
        self.assertFalse(record['rejected_frame']['crc_ok'])
        self.assertEqual(record['rejected_frame']['sha256'], hashlib.sha256(bad).hexdigest())
        self.assertEqual(record['private_frames_sha256'], hashlib.sha256(first).hexdigest())
        self.assertGreater(record['elapsed_seconds'], 0)

    def test_partial_group_is_rejected_even_with_valid_crc(self):
        raw = self.grouped_frame(0, 0, ffts=7)
        args, record, _ = self.grouped_trial([raw], [0,0,7,1792,60000000,0,0,1,0,0,7,0])
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['frames'], 0)
        self.assertEqual((args.private/'rejected-frame.bin').read_bytes(), raw)
        self.assertTrue(record['rejected_frame']['crc_ok'])

    def test_peak_detector_is_rejected_in_a_requested_mean_profile(self):
        raw = bytearray(self.grouped_frame(0, 0)); raw[22] |= 1
        raw[-4:] = zlib.crc32(raw[:-4]).to_bytes(4, 'little')
        args, record, _ = self.grouped_trial([bytes(raw)], [0,0,8,2048,60000000,0,0,1,0,0,8,0])
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['frames'], 0)
        self.assertIn('peak detector', record['error'])
        self.assertTrue(record['rejected_frame']['crc_ok'])

    def test_failed_acquisition_elapsed_excludes_delayed_release_cleanup(self):
        raw = bytearray(self.grouped_frame(0, 0)); raw[40] ^= 1
        clock = [1.0]
        original_run = spectrum_bridge.Trial.run
        # grouped_trial's request function is overridden only to model a very
        # delayed RELEASE. No serial object or physical device is created.
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); wire = spectrum_fixture.Wire(raw)
        args = SimpleNamespace(output=root/'metadata', private=root/'private', port='SYNTHETIC', baud=921600,
            frequency=2412, bandwidth=20, gain='hardware', seconds=60, rate=80000000, bins=256, ffts_per_frame=8)
        def request(port, command):
            if command.startswith('SPEC '):
                return 'SPEC 256 80000000 256 2412'
            clock[0] = 1000.0
            return 'OK'
        def frame(port, bins):
            clock[0] = 2.0
            raise spectrum_bridge.RejectedFrame('synthetic spectrum CRC mismatch', bytes(raw), 'spectrum', False)
        with patch.object(spectrum_bridge, 'open_board', return_value=wire), patch.object(spectrum_bridge, 'synchronize'), \
            patch.object(spectrum_bridge, 'queries', return_value={}), patch.object(spectrum_bridge, 'settings', return_value={}), \
            patch.object(spectrum_bridge, 'command', side_effect=request), patch.object(spectrum_bridge, 'spectrum_frame', side_effect=frame), \
            patch.object(spectrum_bridge.time, 'monotonic', side_effect=lambda: clock[0]), contextlib.redirect_stdout(io.StringIO()):
            original_run(spectrum_bridge.Trial(args))
        self.assertTrue(wire.closed)
        self.assertEqual(json.loads((args.output/'results.json').read_text())['elapsed_seconds'], 1.0)

    def test_standalone_bridge_profile_stays_one_fft_without_explicit_grouping(self):
        record = spectrum_fixture.SpectrumTrialIntegrity().trial()
        self.assertEqual(record['settings']['ffts_per_frame'], 1)
        self.assertEqual(record['status'], 'completed')

    @unittest.skipUnless(os.environ.get('CHROMIUM_EXECUTABLE'), 'Nix Chromium is required for browser fixture')
    def test_nix_browser_draws_synthetic_live_frame_and_observes_completion(self):
        # Only synthetic state is served. No Trial or device-opening code runs.
        from playwright.sync_api import sync_playwright, expect
        state = {'status': 'Synthetic fixture ready', 'frames': 0, 'crc_failures': 0,
            'elapsed_seconds': 0, 'frequency_mhz': 2412, 'rate_hz': 80000000,
            'bins': 512, 'duration_seconds': 60, 'snapshot_gap_flag': True,
            'ffts_per_frame': 8,
            'nominal_coverage_fraction': .0001}
        trial = SimpleNamespace(lock=threading.Lock(), state=state)
        def start():
            with trial.lock:
                state.update(status='Synthetic fixture running', frames=42, elapsed_seconds=5,
                    power_codes=[20 + (i % 200) for i in range(512)])
            return True
        trial.start = start
        server = ThreadingHTTPServer(('127.0.0.1', 0), demo.viewer_handler(trial, 'fixture'))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=os.environ['CHROMIUM_EXECUTABLE'], headless=True)
                try:
                    page = browser.new_page(); errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(f'http://127.0.0.1:{server.server_address[1]}')
                    expect(page.locator('#settings')).to_contain_text('512 FFT bins')
                    expect(page.locator('#settings')).to_contain_text('8 FFT windows averaged per update')
                    before = page.locator('canvas').screenshot()
                    page.locator('#start').click()
                    expect(page.locator('#stats')).to_contain_text('42')
                    self.assertNotEqual(before, page.locator('canvas').screenshot())
                    self.assertIn('snapshot_gap_flag', page.locator('#stats').inner_text())
                    with trial.lock:
                        state.update(status='Completed synthetic fixture', elapsed_seconds=60)
                    expect(page.locator('#status')).to_contain_text('Completed')
                    with trial.lock:
                        state.update(status='Failed', error='/private/untrusted/data')
                    expect(page.locator('#status')).to_have_text('Failed')
                    self.assertNotIn('/private/untrusted/data', page.locator('#stats').inner_text())
                    self.assertEqual(errors, [])
                finally:
                    browser.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()

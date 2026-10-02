"""Register lifecycle faults and real subprocess output ownership, without hardware."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import esp_register_observation as supervisor
import esp_register_receipts as protocol
import test_esp_register_probe as worker_tests


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.args = SimpleNamespace(action='run',artifact=root/'artifact',manifest=root/'manifest',
                                    port=supervisor.lifecycle.STABLE_PORT,output=root/'public',private=root/'private')
        self.args.manifest.write_text('{}')
        self.events = []
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.patches = {}
        def hook(owner,name,fn):
            self.patches[name] = self.stack.enter_context(patch.object(owner,name,side_effect=fn))
        hook(supervisor,'committed_callers',lambda:dict(revision='0'*40,files={}))
        hook(supervisor.artifact_guard,'validate_artifact',lambda *a: (dict(parts=[],build_info_sha256='1'*64),
             dict(source_commit='0'*40,source_tree_sha256='2'*64,idf_commit='3'*40)))
        hook(supervisor.lifecycle,'baseline_check',lambda:dict(sha256='4'*64))
        hook(supervisor,'security_check',lambda:None)
        hook(supervisor.lifecycle,'identity_check',lambda *a:self.events.append('identity'))
        hook(supervisor.lifecycle,'validate_paths',lambda *a:a)
        hook(supervisor.lifecycle,'current_baseline_check',lambda *a:self.events.append('baseline_read'))
        hook(supervisor,'install',lambda *a:self.events.append('install'))
        hook(supervisor,'collect',lambda *a:dict(status='completed'))
        hook(supervisor.lifecycle,'restore_verified',lambda *a:self.events.append('restore'))

    def run_trial(self):
        with patch('builtins.print'):
            code = supervisor.run(self.args)
        return code,json.loads((self.args.output/'register-observation.json').read_text())

    def test_invalid_artifact_refused_before_identity_or_flash(self):
        self.patches['validate_artifact'].side_effect = supervisor.artifact_guard.ArtifactError('synthetic')
        with self.assertRaises(supervisor.artifact_guard.ArtifactError):self.run_trial()
        self.assertEqual(self.events,[])
        self.assertFalse(self.args.private.exists())

    def test_baseline_read_failure_never_installs_or_restores(self):
        self.patches['current_baseline_check'].side_effect=RuntimeError('synthetic')
        code,result=self.run_trial()
        self.assertEqual(code,2)
        self.assertEqual(result['restoration_status'],'not_attempted')
        self.assertNotIn('install',self.events)
        self.assertNotIn('restore',self.events)

    def test_install_failure_or_cancellation_restores_exactly_once(self):
        for error in (RuntimeError('synthetic'),supervisor.lifecycle.Cancelled('synthetic')):
            with self.subTest(error=type(error).__name__):
                self.patches['install'].side_effect=error
                code,result=self.run_trial()
                self.assertEqual(code,2)
                self.assertTrue(result['installation_attempted'])
                self.assertEqual(result['restoration_status'],'verified')
                self.assertEqual(self.events.count('restore'),1)
                # Separate fresh output/private directories for the next trial.
                self.args.private=self.args.private.with_name(self.args.private.name+'2')
                self.args.output=self.args.output.with_name(self.args.output.name+'2')
                self.events.clear()

    def test_capture_failure_restores_and_retains_failed_public_result(self):
        self.patches['collect'].side_effect=lambda *a:dict(status='failed',verified_capture_count=3)
        code,result=self.run_trial()
        self.assertEqual(code,2)
        self.assertEqual(result['capture_status'],'failed')
        self.assertEqual(result['restoration_status'],'verified')
        self.assertEqual(self.events.count('restore'),1)
        self.assertEqual(json.loads((self.args.output/'capture.json').read_text())['verified_capture_count'],3)

    def test_unknown_owned_group_prevents_competing_restore(self):
        self.patches['collect'].side_effect=supervisor.lifecycle.OwnedHardwareClosureError('synthetic')
        code,result=self.run_trial()
        self.assertEqual(code,2)
        self.assertFalse(result['owned_uart_worker_exit_confirmed'])
        self.assertEqual(result['restoration_status'],'blocked_owned_worker_not_closed')
        self.assertNotIn('restore',self.events)

    def test_success_needs_restoration_and_restore_mode_skips_artifact(self):
        self.patches['restore_verified'].side_effect=RuntimeError('synthetic')
        code,result=self.run_trial()
        self.assertEqual(code,2)
        self.assertEqual(result['capture_status'],'completed')
        self.assertEqual(result['restoration_status'],'failed')
        self.args.action='restore'
        self.args.output=self.args.output.with_name('restore-public')
        self.args.private=self.args.private.with_name('restore-private')
        self.patches['restore_verified'].side_effect=lambda *a:self.events.append('restore')
        self.patches['validate_artifact'].side_effect=AssertionError('restore must not require artifact')
        self.patches['current_baseline_check'].side_effect=AssertionError('restore must not require matching current image')
        self.events.clear()
        code,result=self.run_trial()
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.events,['identity','restore'])


class ActualProcesses(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private=Path(self.temp.name)
        self.old=os.umask(0o077)
        self.addCleanup(os.umask,self.old)

    def test_real_pipes_both_drained_before_persist_after_group_exit(self):
        # More than ordinary pipe capacity on both streams would deadlock a
        # sequential read. The real group must be gone before any persisted log.
        command=[sys.executable,'-c',"import os; os.write(1,b'x'*100000); os.write(2,b'y'*100000)"]
        real_persist=supervisor.persist
        real_popen=supervisor.subprocess.Popen
        owned=[]
        def launch(*a,**k):
            proc=real_popen(*a,**k);owned.append(proc);return proc
        def save(path,raw):
            self.assertFalse(supervisor.lifecycle.group_exists(owned[0].pid))
            return real_persist(path,raw)
        with patch.object(supervisor.subprocess,'Popen',side_effect=launch), \
             patch.object(supervisor,'persist',side_effect=save):
            code,raw=supervisor.worker_process(command,self.private,seconds=2)
        self.assertEqual(code,0)
        self.assertEqual(raw,b'x'*100000)
        self.assertEqual((self.private/'worker-stderr.bin').read_bytes(),b'y'*100000)
        self.assertEqual((self.private/'worker-stdout.bin').stat().st_mode&0o777,0o600)

    def test_real_output_overflow_stops_group_and_retains_bounded_prefix(self):
        command=[sys.executable,'-c',"import os,time; os.write(1,b'x'*2000000); time.sleep(20)"]
        with self.assertRaises(protocol.ProtocolError):
            supervisor.worker_process(command,self.private,seconds=2)
        self.assertEqual((self.private/'worker-stdout.bin').stat().st_size,supervisor.PIPE_LIMIT)

    def test_real_worker_deadline_closes_group_before_saving_prefix(self):
        command=[sys.executable,'-c',"import os,time; os.write(1,b'prefix'); time.sleep(20)"]
        before=time.monotonic()
        with self.assertRaises(protocol.ProtocolError):
            supervisor.worker_process(command,self.private,seconds=.1)
        self.assertLess(time.monotonic()-before,2)
        self.assertEqual((self.private/'worker-stdout.bin').read_bytes(),b'prefix')

    def test_unconfirmed_process_group_cannot_persist_parent_buffers(self):
        command=[sys.executable,'-c',"print('bounded receipt',flush=True)"]
        with patch.object(supervisor.lifecycle,'stop_process',
                          side_effect=supervisor.lifecycle.OwnedHardwareClosureError('synthetic')):
            with self.assertRaises(supervisor.lifecycle.OwnedHardwareClosureError):
                supervisor.worker_process(command,self.private,seconds=2)
        self.assertEqual(list(self.private.iterdir()),[])

    def test_cancel_during_process_assignment_still_reaps_owner(self):
        command=[sys.executable,'-c','import time; time.sleep(20)']
        real_popen=supervisor.subprocess.Popen
        owned=[]
        def launch(*a,**k):
            proc=real_popen(*a,**k);owned.append(proc)
            os.kill(os.getpid(),signal.SIGTERM)
            return proc
        previous=signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(supervisor.lifecycle.Cancelled('synthetic')))
        try:
            with patch.object(supervisor.subprocess,'Popen',side_effect=launch):
                with self.assertRaises(supervisor.lifecycle.Cancelled):
                    supervisor.worker_process(command,self.private,seconds=2)
        finally:signal.signal(signal.SIGTERM,previous)
        self.assertFalse(supervisor.lifecycle.group_exists(owned[0].pid))


class ActualCReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):worker_tests.WorkerActualC.setUpClass()
    @classmethod
    def tearDownClass(cls):worker_tests.WorkerActualC.tearDownClass()

    def result(self,wire=None):
        case=worker_tests.WorkerActualC(methodName='test_actual_twenty_frames_all_stages_single_settings_and_real_sync')
        self.addCleanup(case.doCleanups)
        return case.trial(wire or worker_tests.Wire(worker_tests.WorkerActualC.rows))

    def test_real_C_worker_output_and_saved_bytes_independently_replayed(self):
        result,_,private=self.result()
        summary=supervisor.capture_summary(result,private,0)
        self.assertEqual(summary['status'],'completed')
        self.assertEqual(summary['verified_capture_count'],20)
        self.assertEqual(len(summary['records']),81)
        (private/'iq-07.bin').write_bytes(b'bad')
        with self.assertRaises(protocol.ProtocolError):supervisor.capture_summary(result,private,0)

    def test_actual_C_failed_prefix_is_not_promoted_or_dropped(self):
        result,_,private=self.result(worker_tests.Wire(worker_tests.WorkerActualC.rows,bad_crc=3))
        summary=supervisor.capture_summary(result,private,2)
        self.assertEqual(summary['status'],'failed')
        self.assertEqual(summary['verified_capture_count'],3)
        self.assertEqual(len(summary['records']),13)
        self.assertEqual(len(summary['payloads']),4)
        self.assertFalse(summary['payloads'][-1]['crc_ok'])

    def test_terminal_fields_or_brackets_cannot_bypass_independent_replay(self):
        result,_,private=self.result()
        result['verified_capture_count']=19
        with self.assertRaises(protocol.ProtocolError):supervisor.capture_summary(result,private,0)
        result['verified_capture_count']=20
        result['receipts'][-1]['host_end_ns']=result['acquisition_start_ns']+30000000001
        with self.assertRaises(protocol.ProtocolError):supervisor.capture_summary(result,private,0)

    def test_rehashed_wire_with_bad_metadata_crc_is_rejected(self):
        import hashlib
        result,_,private=self.result()
        path=private/'wire.bin'
        raw=bytearray(path.read_bytes())
        offset=raw.index(b'\nREGOBS1 ')+9
        raw[offset]=ord('1') if raw[offset]!=ord('1') else ord('2')
        path.write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest()
        result['retained_wire_sha256']=digest
        result['wire_persistence']['saved_sha256']=digest
        with self.assertRaises(protocol.ProtocolError):supervisor.capture_summary(result,private,0)

    def test_declared_record_cannot_disagree_with_crc_valid_wire(self):
        result,_,private=self.result()
        # Deliberately keep the worker's two metadata copies coherent. Only
        # independently consuming original UART bytes exposes this difference.
        result['records'][0]['selector']=42
        result['receipts'][0]['receipt']['records'][0]['selector']=42
        with self.assertRaises(protocol.ProtocolError):supervisor.capture_summary(result,private,0)


class InstallIsolation(unittest.TestCase):
    def test_unknown_fuser_failure_never_opens_flash_writer(self):
        args=SimpleNamespace(artifact=Path('/private/artifact'),manifest=Path('/private/manifest'),
                             port=supervisor.lifecycle.STABLE_PORT,private=Path('/private'))
        for code in (0,2,127):
            with self.subTest(code=code), \
                 patch.object(supervisor.artifact_guard,'validate_artifact',return_value=({'parts':[]},{})), \
                 patch.object(supervisor.lifecycle,'identity_check'), \
                 patch.object(supervisor,'security_check'), \
                 patch.object(supervisor.subprocess,'run',return_value=SimpleNamespace(returncode=code)), \
                 patch.object(supervisor.lifecycle,'execute') as execute:
                with self.assertRaises(protocol.ProtocolError):supervisor.install(args)
                execute.assert_not_called()


if __name__=='__main__':unittest.main()

"""Real private files/flocks; no Nix, daemon, compiler or device operations."""
import contextlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import run_forgix_synthetic_trial as coordinator
import forgix_synthetic_backend as backend
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
from demo_esp_sdr import Cancelled


class Finalization(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'.scratch').mkdir(mode=0o700)
        (self.root/'backups').mkdir(mode=0o700);self.folder=self.root/'backups'/'episode'
        self.folder.mkdir(mode=0o700)
        stack=contextlib.ExitStack();self.addCleanup(stack.close)
        for module in (coordinator,backend,trial):stack.enter_context(patch.object(module,'ROOT',self.root))
        self.profile={'uid_sha256':'a'*64,'nonce':'ab'*16}
        self.lease=coordinator.SessionLease(self.profile,self.folder)
        self.store=coordinator.ReceiptStore(self.folder)
        self.now=1.0
        self.record={'status':'synthetic_episode_observed',
                     'original_flash_and_factory_verified':True,'owned_processes_closed':True}
        capture.save(self.store,'session.json',self.record)
    def clock(self):return self.now
    def saved(self):return json.loads((self.folder/'session.json').read_bytes())
    def finalize(self,**kwargs):
        return coordinator.release_lease(self.lease,self.store,self.record,0,self.clock,**kwargs)
    def assert_blocked(self):
        self.assertTrue(self.lease.pending_path.exists())
        with self.assertRaisesRegex(ValueError,'Unresolved register finalization'):
            with coordinator.operator_lock():self.fail('new operator admitted')
    def test_normal_stream_is_staged_and_output_occurs_behind_shared_blocker(self):
        def output(value):
            self.assertEqual(value['status'],'pending_external_cli_exit')
            self.assert_blocked();self.assertFalse(self.lease.path.exists())
        result=self.finalize(terminal_output=output)
        self.assertEqual(result['finalization_candidate_status'],'synthetic_episode_completed')
        self.assertTrue(result['finalization_effects_returned'])
        self.assertFalse(self.saved()['invocation_qualification'])
        self.assertTrue(self.saved()['external_cli_exit_required'])
        self.assertFalse(self.lease.path.exists() or self.lease.pending_path.exists())
        with coordinator.operator_lock():pass
    def test_normal_recovery_and_failed_transport_keep_distinct_outcomes(self):
        self.record['status']='recovery_observed';self.finalize()
        self.assertEqual(self.saved()['finalization_candidate_status'],'recovered_and_verified')
    def test_failed_transport_can_close_after_verified_recovery_without_qualifying(self):
        self.record.update(status='failed',failure_kind='CaptureError');self.finalize()
        self.assertEqual(self.saved()['status'],'failed');self.assertIsNone(self.saved()['finalization_candidate_status'])
        self.assertFalse(self.lease.path.exists() or self.lease.pending_path.exists())
    def test_missing_recovery_or_owned_closure_keeps_active_lease_and_pending(self):
        self.record['owned_processes_closed']=False;self.finalize()
        self.assertEqual(self.saved()['status'],'failed');self.assertTrue(self.lease.path.exists());self.assert_blocked()
    def test_original_late_actual_release_plus_failed_corrective_write_stays_blocked(self):
        sync=capture.sync_directory;save=capture.save
        def late(path):
            sync(path)
            if Path(path)==self.root/'.scratch' and not self.lease.path.exists():self.now=600
        def fail_correction(store,name,value):
            if name=='synthetic-finalization-failed.json':raise OSError('corrective storage')
            save(store,name,value)
        with patch.object(capture,'sync_directory',side_effect=late),patch.object(capture,'save',side_effect=fail_correction):
            with self.assertRaises(TimeoutError):self.finalize()
        self.assertEqual(self.record['status'],'failed');self.assertEqual(self.saved()['status'],'pending_finalization')
        self.assert_blocked()
    def test_original_actual_unlink_sync_error_and_correction_failure_stays_blocked(self):
        sync=capture.sync_directory;save=capture.save
        def failed_release(path):
            sync(path)
            if Path(path)==self.root/'.scratch' and not self.lease.path.exists():raise OSError('release fsync')
        def fail_correction(store,name,value):
            if name=='synthetic-finalization-failed.json':raise OSError('corrective storage')
            save(store,name,value)
        with patch.object(capture,'sync_directory',side_effect=failed_release),patch.object(capture,'save',side_effect=fail_correction):
            with self.assertRaisesRegex(OSError,'release fsync'):self.finalize()
        self.assertEqual(self.saved()['status'],'pending_finalization');self.assert_blocked()
    def test_terminal_stdout_and_corrective_fsync_failure_never_save_invocation_success(self):
        failed=False;fsync=os.fsync
        def output(value):
            nonlocal failed
            failed=True;raise OSError('stdout')
        def persist(fd):
            if failed:raise OSError('corrective fsync')
            fsync(fd)
        with patch.object(capture.os,'fsync',side_effect=persist),self.assertRaisesRegex(OSError,'stdout'):
            self.finalize(terminal_output=output)
        self.assertEqual(self.saved()['status'],'pending_external_cli_exit')
        self.assertFalse(self.saved()['invocation_qualification']);self.assert_blocked()
    def test_late_and_exact_deadline_at_output_both_fail_original_clock(self):
        def output(value):self.now=600
        with self.assertRaises(TimeoutError):self.finalize(terminal_output=output)
        self.assertTrue(self.saved()['deadline_exceeded']);self.assert_blocked()
    def test_late_terminal_persistence_rejects_before_stdout(self):
        save=capture.save;outputs=[]
        def late(store,name,value):
            save(store,name,value)
            if name=='synthetic-finalization-saved.json':self.now=600
        with patch.object(capture,'save',side_effect=late),self.assertRaises(TimeoutError):
            self.finalize(terminal_output=outputs.append)
        self.assertFalse(outputs);self.assert_blocked()
    def test_actual_post_stdout_receipt_fd_fsync_failure_retains_pending(self):
        fsync=os.fsync;outputs=[]
        def persist(fd):
            try:name=Path(os.readlink('/proc/self/fd/'+str(fd))).name
            except OSError:name=''
            if name=='synthetic-finalization-returned.json':raise OSError('final fd fsync')
            return fsync(fd)
        with patch.object(capture.os,'fsync',side_effect=persist),self.assertRaisesRegex(OSError,'final fd fsync'):
            self.finalize(terminal_output=lambda value:outputs.append(value['status']))
        self.assertEqual(outputs,['pending_external_cli_exit'])
        self.assertEqual(self.saved()['status'],'failed');self.assert_blocked()
    def test_post_output_persistence_at_deadline_cannot_close_shared_blocker(self):
        save=capture.save
        def late(store,name,value):
            save(store,name,value)
            if name=='synthetic-finalization-returned.json':self.now=600
        with patch.object(capture,'save',side_effect=late),self.assertRaises(TimeoutError):self.finalize()
        self.assertEqual(self.saved()['status'],'failed');self.assert_blocked()
    def test_initial_pending_storage_failure_never_releases_the_active_lease(self):
        with patch.object(capture,'durable',side_effect=OSError('disk')),self.assertRaises(OSError):self.finalize()
        self.assertTrue(self.lease.path.exists());self.assert_blocked()
    def test_cancellation_before_release_and_during_output_keeps_shared_blocker(self):
        cancelled=False
        def output(value):
            nonlocal cancelled
            cancelled=True
        with self.assertRaises(Cancelled):self.finalize(terminal_output=output,cancelled=lambda:cancelled)
        self.assertEqual(self.saved()['finalization_failure_kind'],'Cancelled');self.assert_blocked()
    def test_initial_cancellation_does_not_unlink_active_lease(self):
        with self.assertRaises(Cancelled):self.finalize(cancelled=lambda:True)
        self.assertTrue(self.lease.path.exists());self.assert_blocked()
    def test_wrong_marker_bytes_and_inode_are_never_removed(self):
        self.lease.pending();foreign=self.root/'.scratch'/'foreign-marker'
        foreign.write_bytes(self.lease.data);foreign.chmod(0o600)
        os.replace(foreign,self.lease.pending_path)
        with self.assertRaisesRegex(ValueError,'inode differs'):self.lease.clear_pending()
        self.assertTrue(self.lease.pending_path.exists())
        self.lease.pending_path.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError,'owner differs'):self.lease.clear_pending()
        self.assertEqual(self.lease.pending_path.read_bytes(),b'foreign')
    def test_hardlink_and_unsafe_marker_modes_are_not_owned_cleanup(self):
        self.lease.pending();os.link(self.lease.pending_path,self.root/'alias')
        with self.assertRaises(ValueError):self.lease.clear_pending()
        (self.root/'alias').unlink();self.lease.pending_path.chmod(0o644)
        with self.assertRaises(ValueError):self.lease.clear_pending()
        self.assertTrue(self.lease.pending_path.exists())
    def test_partial_or_foreign_active_lease_is_not_overwritten_by_failure(self):
        self.lease.path.write_bytes(b'foreign-active')
        with self.assertRaises(ValueError):self.finalize()
        self.assertEqual(self.lease.path.read_bytes(),b'foreign-active');self.assert_blocked()
    def test_late_marker_clear_retains_blocker_and_cannot_qualify(self):
        clear=self.lease.clear_pending
        def late():clear();self.now=600
        with patch.object(self.lease,'clear_pending',side_effect=late),self.assertRaises(TimeoutError):self.finalize()
        self.assert_blocked();self.assertEqual(self.record['status'],'failed')
    def test_shared_guard_refuses_all_entry_routes_without_any_hardware_query(self):
        import run_forgix_spi_trial as register
        import run_forgix_clock_trial as observer
        import forgix_usb_ram_capture as usb
        self.lease.pending()
        with patch.object(register,'ROOT',self.root),patch.object(observer,'ROOT',self.root):
            for module in (coordinator,register,observer):
                with self.subTest(module=module.__name__),self.assertRaisesRegex(ValueError,'finalization'):
                    module.prepare(SimpleNamespace())
            for module in (coordinator,register,observer):
                with self.subTest(lock=module.__name__),self.assertRaisesRegex(ValueError,'finalization'):
                    with module.operator_lock():self.fail('admitted')
        with self.assertRaisesRegex(ValueError,'finalization'):usb.reject_pending_finalization(self.root)
    def test_recovery_rotation_retains_exact_new_marker_owner(self):
        new=self.root/'backups'/'recovery';new.mkdir(mode=0o700)
        lease=coordinator.SessionLease.rotate(self.profile,new)
        self.assertNotEqual(lease.data,self.lease.data);lease.pending()
        self.assertEqual(lease.pending_path.read_bytes(),lease.data)
        with self.assertRaises(ValueError):self.lease.clear_pending()
        lease.clear_pending()


class ActualMain(unittest.TestCase):
    def run_case(self,*,output_fault=None,lock_fault=None,status='synthetic_episode_observed'):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700)
            folder=root/'backups'/'episode';folder.mkdir(mode=0o700)
            profile={'uid_sha256':'a'*64,'nonce':'ab'*16};now=SimpleNamespace(value=10.0)
            adapter=SimpleNamespace(cleaning=False,owner=SimpleNamespace(closed=True))
            args=SimpleNamespace(action='run')
            def execute(_adapter,store,preflight,*,began):
                adapter.cleaning=True
                record={'status':status,'original_flash_and_factory_verified':True,'owned_processes_closed':True}
                capture.save(store,'session.json',record);return record
            actual_lock=coordinator.operator_lock
            @contextlib.contextmanager
            def lock(recovery_profile=None):
                with actual_lock() as fd:yield fd
                if lock_fault=='late':now.value=610.0
                if lock_fault=='error':raise OSError('close boundary')
            cancel_sent=False
            def output(*items,**kwargs):
                nonlocal cancel_sent
                self.assertTrue((root/'.scratch/forgix-spi-finalization-pending.json').exists())
                if output_fault=='late':now.value=610.0
                if output_fault=='error':raise OSError('stdout')
                if output_fault=='cancel' and not cancel_sent:
                    cancel_sent=True
                    signal.raise_signal(signal.SIGTERM) # self, never a group
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root), \
                 patch.object(coordinator,'parser',return_value=SimpleNamespace(parse_args=lambda:args)), \
                 patch.object(coordinator,'prepare',return_value=(profile,{}, {},folder)), \
                 patch.object(backend,'frozen_inputs'),patch.object(backend,'qualified'),patch.object(coordinator.runtime,'check'), \
                 patch.object(backend,'Backend',return_value=adapter),patch.object(coordinator,'execute',side_effect=execute), \
                 patch.object(coordinator,'operator_lock',side_effect=lock),patch.object(coordinator.time,'monotonic',side_effect=lambda:now.value), \
                 patch.object(coordinator,'print',side_effect=output,create=True):
                code=coordinator.main()
            return {'code':code,'saved':json.loads((folder/'session.json').read_bytes()),
                    'pending':(root/'.scratch/forgix-spi-finalization-pending.json').exists(),
                    'active':(root/backend.LEASE).exists()}
    def test_normal_main_cli0_is_distinct_from_saved_pending_external_facts(self):
        result=self.run_case();self.assertEqual(result['code'],0)
        self.assertEqual(result['saved']['status'],'pending_external_cli_exit')
        self.assertTrue(result['saved']['operator_lock_close_returned'])
        self.assertEqual(result['saved']['session_began_monotonic'],10.0)
        self.assertEqual(result['saved']['session_deadline_monotonic'],610.0)
        self.assertFalse(result['saved']['invocation_qualification'])
        self.assertFalse(result['pending'] or result['active'])
    def test_real_main_output_late_and_actual_self_cancel_fail_not_cli0(self):
        for fault in ('late','cancel'):
            with self.subTest(fault=fault):
                result=self.run_case(output_fault=fault);self.assertEqual(result['code'],2)
                self.assertEqual(result['saved']['status'],'failed');self.assertTrue(result['pending'])
    def test_root_fd_close_late_or_error_is_refused_before_finalization_output(self):
        for fault in ('late','error'):
            with self.subTest(fault=fault):
                result=self.run_case(lock_fault=fault);self.assertEqual(result['code'],2)
                self.assertEqual(result['saved']['status'],'failed');self.assertTrue(result['pending'])
    def test_normal_failed_transport_cli2_can_release_only_after_verified_recovery(self):
        result=self.run_case(status='failed');self.assertEqual(result['code'],2)
        self.assertEqual(result['saved']['status'],'failed');self.assertFalse(result['pending'] or result['active'])


if __name__=='__main__':unittest.main(verbosity=2)

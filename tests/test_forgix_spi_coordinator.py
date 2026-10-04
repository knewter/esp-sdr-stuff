"""Actual Git/flock/durable files plus injected lifecycle; no hardware."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import run_forgix_spi_trial as coordinator
import forgix_spi_backend as backend
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
from test_forgix_spi_lifecycle import Adapter

class Preflight(unittest.TestCase):
    def test_empty_registry_refuses_before_any_artifact_or_device_access(self):
        with patch.object(backend,'artifact',side_effect=AssertionError('artifact reached')):
            with self.assertRaisesRegex(ValueError,'No committed qualification'):coordinator.prepare(SimpleNamespace())
    def test_cli_has_no_qualification_bypass(self):
        with patch.object(backend,'QUALIFIED',()):
            r=subprocess.run([sys.executable,str(ROOT/'tools/run_forgix_spi_trial.py'),'run',
                '--artifact','missing','--binding','missing','--baseline-a','missing','--baseline-b','missing',
                '--qualification','missing','--private-dir','missing'],capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['status'],'refused')
    def test_freeze_uses_real_committed_blobs_and_rejects_changed_execution_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in backend.EXECUTION_FILES:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('controlled fixture\n')
            def git(*args):return subprocess.run(['git',*args],cwd=root,check=True,capture_output=True,timeout=10)
            git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            git('add','.');git('commit','-m','Fixture inputs')
            with patch.object(coordinator,'ROOT',root),patch.object(trial,'ROOT',root):
                frozen=coordinator.freeze();self.assertEqual(set(frozen['inputs']),backend.EXECUTION_FILES)
                (root/'tools/forgix_spi_capture.py').write_text('modified\n')
                with self.assertRaisesRegex(ValueError,'committed and unchanged'):coordinator.freeze()

class Locks(unittest.TestCase):
    def test_real_exclusive_lock_inheritance_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir()
            with patch.object(coordinator,'ROOT',root):
                with coordinator.operator_lock() as fd:
                    path=root/'.scratch/esp-demo.lock'
                    capture.inherited_operator_lock(fd,path)
                    probe='import fcntl,sys; f=open(sys.argv[1],"a+b"); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)'
                    r=subprocess.run([sys.executable,'-c',probe,str(path)],capture_output=True,timeout=10)
                    self.assertNotEqual(r.returncode,0)
                with path.open('a+b') as stream:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def test_unknown_marker_and_unsafe_lock_are_refused(self):
        for fault in ('marker','permissions','symlink'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'.scratch').mkdir();path=root/'.scratch/esp-demo.lock'
                if fault=='marker':(root/'.scratch/forgix-usb-ram-unclosed.json').write_text('{}')
                elif fault=='permissions':path.touch(mode=0o644)
                else:path.symlink_to(root/'elsewhere')
                with patch.object(coordinator,'ROOT',root):
                    with self.assertRaises((ValueError,trial.preserve.PreservationError)):
                        with coordinator.operator_lock():self.fail('unsafe lock yielded')

class Episode(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'backups').mkdir()
        self.path=self.root/'backups/episode';self.path.mkdir(mode=0o700)
        with patch.object(coordinator,'ROOT',self.root):self.store=coordinator.ReceiptStore(self.path)
        self.adapter=Adapter()
    def run_episode(self):
        return coordinator.execute(self.adapter,self.store,{'fixture_only':True,'physical_execution_requested':False},lambda:self.adapter.now)
    def test_durable_full_policy_order_does_not_promote_physical_acceptance(self):
        r=self.run_episode();self.assertEqual(r['status'],'backend_episode_completed')
        self.assertEqual(r['physical_measurement_acceptance'],'pending independent result review')
        self.assertTrue(r['event_persistence_verified'] and r['owned_processes_closed'])
        self.assertTrue(r['lifecycle_policy']['model_policy_only']);self.assertFalse(r['lifecycle_policy']['physical_execution_admitted'])
        self.assertFalse(r['physical_execution_requested'])
        saved=json.loads((self.path/'session.json').read_text());self.assertEqual(saved,r)
        for p in self.path.iterdir():self.assertEqual(p.stat().st_mode&0o777,0o600)
        stages=[x['stage'] for x in map(json.loads,(self.path/'lifecycle.jsonl').read_text().splitlines()) if x.get('phase')=='intent']
        self.assertEqual(stages,['admit','preserve-before','enter-rom','load-ram','configure','transition','collect','return-factory','preserve-after'])
    def test_lost_rom_ack_still_recovers_and_retains_failure(self):
        self.adapter.faults['rom']=TimeoutError()
        r=self.run_episode();self.assertEqual(r['status'],'failed');self.assertTrue(r['original_flash_and_factory_verified'])
        self.assertEqual([x[0] for x in self.adapter.calls][-2:],['return','after'])
    def test_unknown_worker_closure_blocks_all_recovery(self):
        def fault(until):self.adapter.owner.closed=False;raise RuntimeError()
        self.adapter.faults['collect']=fault
        r=self.run_episode();self.assertEqual(r['status'],'failed');self.assertFalse(r['owned_processes_closed'])
        self.assertTrue(r['manual_recovery_required']);self.assertNotIn('return',[x[0] for x in self.adapter.calls])
    def test_cancellation_propagates_after_persisted_recovery(self):
        self.adapter.faults['collect']=KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.run_episode()
        r=json.loads((self.path/'session.json').read_text());self.assertEqual(r['status'],'failed')
        self.assertTrue(r['original_flash_and_factory_verified']);self.assertEqual(self.adapter.calls[-1][0],'after')
    def test_journal_corruption_cannot_report_completed(self):
        save=capture.save
        def corrupt(store,name,record):
            save(store,name,record)
            if name=='preflight.json':
                original=self.adapter.check_inputs
                def changed():
                    original()
                    p=self.path/'lifecycle.jsonl'
                    if p.exists() and self.adapter.cleaning:p.write_bytes(p.read_bytes()[:-1])
                self.adapter.check_inputs=changed
        with patch.object(capture,'save',corrupt):r=self.run_episode()
        self.assertEqual(r['status'],'failed');self.assertIn('final_check_kind',r)
    def test_final_receipt_crossing_deadline_records_failure(self):
        save=capture.save
        def delayed(store,name,record):
            save(store,name,record)
            if name=='session.json':self.adapter.now=600
        with patch.object(capture,'save',delayed):r=self.run_episode()
        self.assertEqual(r['status'],'failed');self.assertTrue(r['deadline_exceeded'])
        self.assertGreaterEqual(r['host_elapsed_seconds'],600)
        self.assertEqual(json.loads((self.path/'session.json').read_text())['status'],'failed')
    def test_initial_persistence_cannot_restart_hardware_budget(self):
        save=capture.save
        def delayed(store,name,record):
            save(store,name,record)
            if name=='preflight.json':self.adapter.now=600
        with patch.object(capture,'save',delayed):r=self.run_episode()
        self.assertEqual(r['status'],'failed');self.assertFalse(self.adapter.calls)
    def test_storage_time_is_included_in_stage_and_recovery_deadline(self):
        save=capture.save
        def delayed(store,name,record):
            save(store,name,record)
            if name=='preflight.json':self.adapter.now=100
        with patch.object(capture,'save',delayed):r=self.run_episode()
        events=[json.loads(line) for line in (self.path/'lifecycle.jsonl').read_text().splitlines()]
        self.assertEqual(events[0]['deadline'],130)
        self.assertTrue(all(e.get('deadline',0)<=600 for e in events))
        self.assertEqual(r['status'],'backend_episode_completed')
    def test_receipt_path_traversal_and_nonprivate_directory_refused(self):
        with self.assertRaisesRegex(ValueError,'basename'):self.store.open('../escape')
        self.path.chmod(0o755)
        with patch.object(coordinator,'ROOT',self.root),self.assertRaisesRegex(ValueError,'Owned direct private'):
            coordinator.ReceiptStore(self.path)

class DurableLease(unittest.TestCase):
    def test_lease_survives_process_exit_and_blocks_another_operator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700)
            profile={'uid_sha256':'a'*64};private=root/'backups/episode'
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                with coordinator.operator_lock():lease=coordinator.SessionLease(profile,private)
                self.assertEqual(lease.path.stat().st_mode&0o777,0o600)
                self.assertEqual(backend.session_lease(profile,private),lease.path)
                with self.assertRaisesRegex(ValueError,'Unresolved register'):
                    with coordinator.operator_lock():self.fail('new operator admitted')
                for record in ({'original_flash_and_factory_verified':False,'owned_processes_closed':True},
                               {'original_flash_and_factory_verified':True,'owned_processes_closed':False}):
                    with self.assertRaisesRegex(ValueError,'Incomplete recovery'):lease.release(record)
                    self.assertTrue(lease.path.exists())
                lease.release({'original_flash_and_factory_verified':True,'owned_processes_closed':True})
                with coordinator.operator_lock():pass
    def test_failed_initial_persistence_retains_blocker_before_any_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700)
            with patch.object(coordinator,'ROOT',root),patch.object(capture,'durable',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):coordinator.SessionLease({'uid_sha256':'a'*64},root/'backups/episode')
                with self.assertRaisesRegex(ValueError,'Unresolved register'):
                    with coordinator.operator_lock():self.fail('partial lease admitted')
    def test_changed_lease_or_owner_cannot_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);profile={'uid_sha256':'a'*64}
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                lease=coordinator.SessionLease(profile,root/'backups/episode')
                with self.assertRaisesRegex(ValueError,'owner differs'):backend.session_lease(profile,root/'backups/other')
                lease.path.write_text('{}')
                with self.assertRaisesRegex(ValueError,'lease changed'):lease.release({'original_flash_and_factory_verified':True,'owned_processes_closed':True})
                self.assertTrue(lease.path.exists())

class Recovery(unittest.TestCase):
    def test_legacy_preservation_cli_refuses_before_device_inspection(self):
        with patch.object(trial.preserve,'Inspector',side_effect=AssertionError('device reached')):
            with self.assertRaises(SystemExit) as refused:
                trial.preserve.main(['--usb-topology','3-3','--serial-port','unopened','--private-dir','unused'])
        self.assertEqual(refused.exception.code,2)
    def test_recovery_owner_exists_after_enter_rom_store_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'backups').mkdir();private=root/'backups/episode';private.mkdir(mode=0o700)
            tool=root/'tool';tool.write_bytes(b'fixture executable')
            b=object.__new__(backend.Backend);b.loader=None;b.hardware_gate=lambda until:None
            b.inspector=SimpleNamespace(deadline=0);b.bus=3;b.private=private;b.profile={}
            b.environment={'picotool_executable':str(tool),'image_id':'fixture'};b.frozen={};b.lockfd=1
            b.owner=backend.AggregateOwner(SimpleNamespace(closed=True))
            with patch.object(backend,'ROOT',root),patch.object(trial,'watched_factory',return_value='fixture target'),patch.object(trial,'bounded_query') as query:
                r=b.return_factory(140)
            self.assertTrue(r['factory_application_verified']);self.assertIsNotNone(b.loader)
            self.assertEqual(b.owner.runners,[b.loader]);self.assertEqual(b.loader.store.path,private/'factory-return')
            query.assert_called_once()

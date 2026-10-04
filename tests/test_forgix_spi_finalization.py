"""Actual temporary lease/session and production finalization; no hardware."""
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
sys.path[:0]=[str(ROOT/'tools')]
import forgix_spi_backend as backend
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
import forgix_synthetic_runtime as runtime
import run_forgix_spi_trial as coordinator
from demo_esp_sdr import Cancelled

class Finalization(unittest.TestCase):
    def exercise(self,fault=None):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700)
            private=root/'backups/session';private.mkdir(mode=0o700);profile={'uid_sha256':'a'*64};now=[0.0]
            args=SimpleNamespace(action='run');original_release=coordinator.SessionLease.release;original_save=capture.save;original_retain=coordinator.SessionLease.retain;original_clear=coordinator.SessionLease.clear_pending
            def execute(adapter,store,preflight):
                self.assertEqual(preflight['session_began_monotonic'],0)
                now[0]=599
                record={'status':'backend_episode_observed','original_flash_and_factory_verified':True,'owned_processes_closed':True,'host_elapsed_seconds':599.0}
                original_save(store,'session.json',record);return record
            def release(lease,record):
                original_release(lease,record)
                if fault=='late-release':now[0]=601
                if fault in ('release-error','corrective-error','retain-error','retain-before-error'):raise OSError('primary release error')
                if fault=='cancel-release':raise Cancelled('primary finalization cancellation')
                if fault=='repeated-signals':
                    os.kill(os.getpid(),signal.SIGINT);os.kill(os.getpid(),signal.SIGTERM)
            def save(store,name,record):
                if fault=='intent-error'and name=='finalization-intent.json':raise OSError('intent storage error')
                if fault=='corrective-error'and name=='failed-final-session.json':raise RuntimeError('secondary corrective error')
                original_save(store,name,record)
                if fault in ('late-terminal','terminal-error')and name=='final-session.json':
                    if fault=='late-terminal':now[0]=601
                    else:raise OSError('terminal storage acknowledgement error')
                if fault in ('late-ack','ack-error')and name=='acknowledged-final-session.json':
                    if fault=='late-ack':now[0]=601
                    else:raise OSError('completion storage acknowledgement error')
            def clear(lease):
                original_clear(lease)
                if fault=='late-marker-clear':now[0]=601
                if fault=='marker-clear-error':raise OSError('pending marker fsync error')
            def retain(lease):
                if fault=='retain-before-error':raise RuntimeError('retention unavailable before create')
                original_retain(lease)
                if fault=='retain-error':raise RuntimeError('secondary retain acknowledgement error')
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root),patch.object(coordinator,'parser',return_value=SimpleNamespace(parse_args=lambda:args)),patch.object(coordinator,'prepare',return_value=(profile,{}, {},private)),patch.object(backend,'frozen_inputs'),patch.object(backend,'qualified'),patch.object(runtime,'check'),patch.object(backend,'Backend',return_value=SimpleNamespace(cleaning=False)),patch.object(coordinator,'execute',side_effect=execute),patch.object(coordinator.SessionLease,'release',release),patch.object(coordinator.SessionLease,'retain',retain),patch.object(coordinator.SessionLease,'clear_pending',clear),patch.object(coordinator.time,'monotonic',side_effect=lambda:now[0]),patch.object(capture,'save',save):
                code=coordinator.main()
                saved=json.loads((private/'session.json').read_text())
                pending=json.loads((private/'finalization-intent.json').read_text())if(private/'finalization-intent.json').exists()else None
                blocker=(root/'.scratch/forgix-spi-active.json').exists()or(root/'.scratch/forgix-spi-finalization-pending.json').exists()
                if blocker:
                    with self.assertRaisesRegex(ValueError,'Unresolved register'):
                        with coordinator.operator_lock():self.fail('uncertain finalization released next operator')
            return code,saved,pending,blocker

    def test_normal_acknowledgement_completes_and_releases_actual_lease(self):
        code,saved,pending,blocker=self.exercise();self.assertEqual(code,0);self.assertFalse(blocker)
        self.assertEqual(saved['status'],'backend_episode_completed');self.assertEqual(saved['finalization_status'],'acknowledged')
        self.assertEqual(pending['status'],'pending_finalization')
    def test_real_release_crossing_same_clock_retains_failure_and_blocker(self):
        code,saved,pending,blocker=self.exercise('late-release');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertEqual(saved['status'],'failed');self.assertTrue(saved['deadline_exceeded'])
        self.assertEqual(saved['finalization_failure_kind'],'TimeoutError')
    def test_real_release_error_corrects_authoritative_session_and_restores_lease(self):
        code,saved,pending,blocker=self.exercise('release-error');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertEqual(saved['status'],'failed');self.assertEqual(saved['failure_kind'],'OSError')
    def test_both_terminal_acknowledgements_and_late_returns_fail(self):
        for fault in ('late-terminal','terminal-error','late-ack','ack-error'):
            with self.subTest(fault=fault):
                code,saved,pending,blocker=self.exercise(fault);self.assertEqual(code,2);self.assertTrue(blocker)
                self.assertEqual(saved['status'],'failed');self.assertEqual(pending['status'],'pending_finalization')
    def test_intent_failure_preserves_existing_lease_before_release(self):
        code,saved,pending,blocker=self.exercise('intent-error');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertIsNone(pending);self.assertEqual(saved['status'],'failed');self.assertEqual(saved['failure_kind'],'OSError')
    def test_cancellation_after_actual_release_is_failed_and_lease_retained(self):
        code,saved,pending,blocker=self.exercise('cancel-release');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertEqual(saved['status'],'failed');self.assertEqual(saved['failure_kind'],'Cancelled')
    def test_corrective_journal_failure_keeps_durable_pending_and_actual_blocker(self):
        code,saved,pending,blocker=self.exercise('corrective-error');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertEqual(pending['status'],'pending_finalization');self.assertEqual(saved['status'],'backend_episode_observed')
    def test_retention_ack_error_does_not_replace_primary_release_error(self):
        code,saved,pending,blocker=self.exercise('retain-error');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertEqual(saved['failure_kind'],'OSError');self.assertEqual(saved['lease_retention_failure_kind'],'RuntimeError')
    def test_final_pending_marker_closure_clock_and_storage_errors_cannot_complete(self):
        for fault in ('late-marker-clear','marker-clear-error'):
            with self.subTest(fault=fault):
                code,saved,pending,blocker=self.exercise(fault);self.assertEqual(code,2);self.assertTrue(blocker)
                self.assertEqual(saved['status'],'failed');self.assertEqual(pending['status'],'pending_finalization')

    def test_independent_pending_blocker_retains_admission_when_active_lease_recreate_fails(self):
        code,saved,pending,blocker=self.exercise('retain-before-error');self.assertEqual(code,2);self.assertTrue(blocker)
        self.assertEqual(saved['status'],'failed');self.assertEqual(saved['failure_kind'],'OSError')
        self.assertEqual(saved['lease_retention_failure_kind'],'RuntimeError');self.assertEqual(pending['status'],'pending_finalization')

    def test_repeated_actual_cancellation_is_deferred_during_final_cleanup(self):
        code,saved,pending,blocker=self.exercise('repeated-signals');self.assertEqual(code,0);self.assertFalse(blocker)
        self.assertEqual(saved['status'],'backend_episode_completed')

if __name__=='__main__':unittest.main()

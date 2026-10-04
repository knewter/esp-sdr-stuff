"""Shared pending-only admission/access refusal with actual harmless locks/processes."""
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools')]
import forgix_usb_ram_capture as usb
import forgix_spi_capture as spi
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve
import forgix_spi_backend as reg_backend
import forgix_synthetic_backend as stream_backend
import run_forgix_spi_trial as register
import run_forgix_synthetic_trial as stream
import forgix_synthetic_runtime as runtime
import test_forgix_usb_ram_trial as usb_fixtures

class PendingFinalization(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'.scratch').mkdir(mode=0o700);(self.root/'backups').mkdir(mode=0o700)
        self.marker=self.root/usb.PENDING_FINALIZATION;self.marker.write_text('{"fixture":"pending"}');self.marker.chmod(0o600)
        self.patches=ExitStack();self.addCleanup(self.patches.close)
        for module,name in [(usb,'REPO'),(spi,'REPO'),(preserve,'REPO'),(trial,'ROOT'),(reg_backend,'ROOT'),(stream_backend,'ROOT'),(register,'ROOT'),(stream,'ROOT')]:
            self.patches.enter_context(patch.object(module,name,self.root))
    def refuses(self,fn):
        with self.assertRaisesRegex(ValueError,'finalization'):fn()
    def test_all_marker_presence_is_blocking_without_content_or_symlink_override(self):
        for kind in ('malformed','directory','dangling-symlink'):
            with self.subTest(kind=kind):
                self.marker.unlink()
                if kind=='malformed':self.marker.write_bytes(b'partial invalid JSON')
                elif kind=='directory':self.marker.mkdir()
                else:self.marker.symlink_to(self.root/'absent')
                self.refuses(lambda:usb.reject_pending_finalization(self.root))
                if kind=='directory':self.marker.rmdir();self.marker.touch()
        self.marker.unlink();usb.reject_pending_finalization(self.root)
    def test_marker_inspection_error_is_not_treated_as_absence(self):
        with patch.object(Path,'lstat',side_effect=PermissionError('fixture denied')):
            self.refuses(lambda:usb.reject_pending_finalization(self.root))
        with patch.object(Path,'lstat',side_effect=OSError('fixture storage error')):
            self.refuses(lambda:usb.reject_pending_finalization(self.root))

    def test_actual_coordinator_locks_refuse_normal_and_matching_recovery_and_close_fds(self):
        for coordinator,args in ((register,()),(stream,()),(stream,({'fixture':'matching recovery'},))):
            with self.subTest(coordinator=coordinator.__name__,args=args):
                with self.assertRaisesRegex(ValueError,'finalization'):
                    with coordinator.operator_lock(*args):self.fail('pending state admitted')
        fd=os.open(self.root/'.scratch/esp-demo.lock',os.O_RDWR)
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally:os.close(fd)
    def test_actual_inherited_flock_refusal_keeps_existing_owner(self):
        self.marker.unlink();path=self.root/'.scratch/esp-demo.lock';fd=os.open(path,os.O_CREAT|os.O_RDWR,0o600)
        other=os.open(path,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX);usb.inherited_operator_lock(fd,path)
            self.marker.touch();self.refuses(lambda:usb.inherited_operator_lock(fd,path))
            with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally:os.close(other);os.close(fd)
    def test_preflight_and_recovery_refuse_before_tools_or_prior_session_reads(self):
        with patch.object(runtime,'select',side_effect=AssertionError('tool selection reached')):
            self.refuses(lambda:register.prepare(SimpleNamespace()))
            self.refuses(lambda:stream.prepare(SimpleNamespace()))
            self.refuses(lambda:stream.recovery_admission(None,None,None,None))
        self.refuses(lambda:trial.recovery_admission({},{}))
    def test_identity_selection_and_serial_open_refuse_before_any_device_path(self):
        selectors=[lambda:trial.fresh_tty('3-3','2e8a','0009'),lambda:usb.select_diagnostic('3-3','/unopened'),
            lambda:spi.select_bridge('3-3','/unopened'),lambda:stream_backend.select_stream({},1),
            lambda:preserve.Inspector('3-3','/unopened').target(preserve.FACTORY_PID),lambda:usb.open_retaining_serial('/unopened')]
        with patch.object(Path,'resolve',side_effect=AssertionError('device path reached')):
            for fn in selectors:self.refuses(fn)
    def test_workers_query_preservation_and_picotool_dispatch_refuse_before_requests_or_spawn(self):
        entries=[lambda:trial.query_worker(),lambda:reg_backend.factory_query_worker(Path('/unread')),
            lambda:reg_backend.serial_worker(Path('/unread')),lambda:stream_backend.serial_worker(Path('/unread')),
            lambda:trial.bounded_query(None,None,None,None,None,None,None),
            lambda:reg_backend.bounded_factory_query(*([None]*10)),lambda:trial.full_preservation(*([None]*7)),
            lambda:trial.OwnedPicotool.run(object.__new__(trial.OwnedPicotool),'save',None),
            lambda:preserve.Picotool.run(object.__new__(preserve.Picotool),'save',None),
            lambda:trial.owned_worker([],self.root/'not-created.log',0,1)]
        with patch.object(subprocess,'Popen',side_effect=AssertionError('spawn reached')):
            for fn in entries:self.refuses(fn)
        self.assertFalse((self.root/'not-created.log').exists())
    def test_serial_operation_entry_refuses_before_injected_selection_or_open(self):
        fail=lambda *a:(_ for _ in ()).throw(AssertionError('transport reached'))
        self.refuses(lambda:reg_backend.serial_operation({},None,fail,fail))
        self.refuses(lambda:stream_backend.serial_operation({},None,fail,fail,fail))
    def test_standalone_usb_both_actions_refuse_before_preflight_and_when_marker_appears_under_real_lock(self):
        fixture=usb_fixtures.LockedAdmission()
        for action in ('run','recover'):
            with self.subTest(action=action,phase='initial'):
                code,check,run,tty,store=fixture.invoke_main(self.root,action)
                self.assertEqual(code,2);check.assert_not_called();run.assert_not_called();tty.assert_not_called();store.assert_not_called()
            self.marker.unlink();original_flock=fcntl.flock
            def acquired(fd,mode):
                original_flock(fd,mode);self.marker.touch()
            with self.subTest(action=action,phase='under-flock'):
                code,check,run,tty,store=fixture.invoke_main(self.root,action,flock_effect=acquired)
                self.assertEqual(code,2);check.assert_not_called();run.assert_not_called();tty.assert_not_called()
    def test_pending_refusal_keeps_owned_process_cleanup_available(self):
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            self.refuses(lambda:trial.owned_worker([],self.root/'not-created.log',0,1))
            trial.stop_process(process,grace_seconds=.5)
            self.assertIsNotNone(process.poll())
        finally:trial.stop_process(process,grace_seconds=.5)

if __name__=='__main__':unittest.main()

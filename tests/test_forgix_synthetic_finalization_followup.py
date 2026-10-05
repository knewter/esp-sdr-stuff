"""Exact owned-marker fallback and original-FD quarantine; no device operations."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_forgix_synthetic_finalization as original
ROOT=original.ROOT
import run_forgix_synthetic_trial as c
import forgix_synthetic_backend as b
import forgix_usb_ram_trial as t
import forgix_usb_ram_capture as u
import forgix_spi_capture as capture

class Followup(unittest.TestCase):
    def fixture(self):
        fixture=original.Finalization();fixture.setUp();self.addCleanup(fixture.doCleanups);return fixture
    def test_actual_pending_open_failure_uses_owned_link_and_normal_cleanup(self):
        f=self.fixture();opened=os.open;observed=[]
        def failure(path,*args,**kw):
            if Path(path)==f.lease.pending_path:raise OSError('pending open')
            return opened(path,*args,**kw)
        def output(record):
            observed.append(f.lease.pending_path.stat().st_nlink)
            self.assertFalse(f.lease.path.exists());f.assert_blocked()
        with patch.object(c.os,'open',side_effect=failure):f.finalize(terminal_output=output)
        self.assertEqual(observed,[1]);self.assertFalse(f.lease.pending_path.exists())
        self.assertEqual(f.saved()['status'],'pending_external_cli_exit')
    def test_link_fallback_never_uses_changed_or_foreign_active_inode(self):
        for kind in ('bytes','inode','mode','alias'):
            with self.subTest(kind=kind):
                f=self.fixture();opened=os.open
                if kind=='bytes':f.lease.path.write_bytes(b'foreign')
                elif kind=='inode':
                    replacement=f.root/'.scratch/replacement';replacement.write_bytes(f.lease.data)
                    replacement.chmod(0o600);os.replace(replacement,f.lease.path)
                elif kind=='mode':f.lease.path.chmod(0o640)
                else:os.link(f.lease.path,f.root/'foreign-alias')
                def failure(path,*args,**kw):
                    if Path(path)==f.lease.pending_path:raise OSError('pending open')
                    return opened(path,*args,**kw)
                with patch.object(c.os,'open',side_effect=failure),self.assertRaises((ValueError,t.preserve.PreservationError)):f.lease.pending()
                self.assertFalse(f.lease.pending_path.exists())
    def test_only_exact_active_pending_link_pair_is_allowed(self):
        f=self.fixture();opened=os.open
        def failure(path,*args,**kw):
            if Path(path)==f.lease.pending_path:raise OSError('pending open')
            return opened(path,*args,**kw)
        with patch.object(c.os,'open',side_effect=failure):f.lease.pending()
        self.assertEqual(f.lease.pending_path.stat().st_nlink,2)
        alias=f.root/'unowned-third-link';os.link(f.lease.path,alias)
        with self.assertRaises(ValueError):f.lease.clear_pending()
        alias.unlink();f.lease.pending();self.assertTrue(f.lease.pending_path.exists())

    def main_case(self,*,closed=True,pending_failure=False,post_stdout_cancel=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700)
            folder=root/'backups/episode';folder.mkdir(mode=0o700)
            profile={'uid_sha256':'a'*64,'nonce':'ab'*16}
            adapter=SimpleNamespace(cleaning=False,owner=SimpleNamespace(closed=closed));events=[]
            def execute(_adapter,store,preflight,*,began):
                adapter.cleaning=True
                record={'status':'synthetic_episode_observed' if closed else 'failed',
                        'original_flash_and_factory_verified':True,'owned_processes_closed':closed}
                capture.save(store,'session.json',record);return record
            opened=os.open;sync=capture.sync_directory
            def failure(path,*args,**kw):
                if pending_failure and Path(path)==root/'.scratch/forgix-spi-finalization-pending.json':raise OSError('pending open')
                return opened(path,*args,**kw)
            def synced(path):
                value=sync(path)
                if post_stdout_cancel and Path(path)==root/'.scratch' and not (root/u.PENDING_FINALIZATION).exists() and not (root/b.LEASE).exists():
                    events.append('actual self SIGINT during final sync');signal.raise_signal(signal.SIGINT)
                return value
            previous=signal.signal(signal.SIGINT,signal.SIG_IGN)
            try:
                with patch.object(c,'ROOT',root),patch.object(b,'ROOT',root),patch.object(t,'ROOT',root), \
                     patch.object(c,'parser',return_value=SimpleNamespace(parse_args=lambda:SimpleNamespace(action='run'))), \
                     patch.object(c,'prepare',return_value=(profile,{}, {},folder)),patch.object(b,'frozen_inputs'), \
                     patch.object(b,'qualified'),patch.object(c.runtime,'check'),patch.object(b,'Backend',return_value=adapter), \
                     patch.object(c,'execute',side_effect=execute),patch.object(c.time,'monotonic',return_value=10.), \
                     patch.object(c,'print',return_value=None,create=True),patch.object(c.os,'open',side_effect=failure), \
                     patch.object(capture,'sync_directory',side_effect=synced):code=c.main()
            finally:signal.signal(signal.SIGINT,previous)
            admitted=False;fd=opened(root/'.scratch/esp-demo.lock',os.O_RDWR)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                try:u.inherited_operator_lock(fd,root/'.scratch/esp-demo.lock');admitted=True
                except ValueError:pass
            finally:os.close(fd)
            return {'code':code,'saved':json.loads((folder/'session.json').read_bytes()),'events':events,
                    'active':(root/b.LEASE).exists(),'pending':(root/u.PENDING_FINALIZATION).exists(),'shared_admitted':admitted}
    def test_exact_unknown_closure_open_failure_blocks_shared_usb_access(self):
        value=self.main_case(closed=False,pending_failure=True)
        self.assertEqual(value['code'],2);self.assertTrue(value['active'] and value['pending'])
        self.assertFalse(value['shared_admitted']);self.assertFalse(value['saved']['owned_processes_closed'])
    def test_prior_ignored_sigint_does_not_ignore_actual_final_sync_cancellation(self):
        value=self.main_case(post_stdout_cancel=True)
        self.assertTrue(value['events']);self.assertEqual(value['code'],2)
        self.assertEqual(value['saved']['status'],'failed');self.assertTrue(value['pending'])
        self.assertFalse(value['shared_admitted'])
    def test_known_closed_control_still_finishes_without_blockers(self):
        value=self.main_case();self.assertEqual(value['code'],0)
        self.assertEqual(value['saved']['status'],'pending_external_cli_exit')
        self.assertFalse(value['active'] or value['pending']);self.assertTrue(value['shared_admitted'])

class Quarantine(unittest.TestCase):
    def test_real_owner_keeps_exact_flock_under_double_storage_fault_and_cancel(self):
        for extra_failure in ('none','receipt','identity'):
            with self.subTest(extra_failure=extra_failure),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700)
                script=r'''
import json,os,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,sys.argv[1]);import run_forgix_synthetic_trial as c
import forgix_synthetic_backend as b;import forgix_usb_ram_trial as t
import forgix_spi_capture as capture
root=Path(sys.argv[2]);folder=root/'backups/episode';folder.mkdir(mode=0o700)
profile={'uid_sha256':'a'*64,'nonce':'ab'*16};adapter=SimpleNamespace(cleaning=False,owner=SimpleNamespace(closed=False))
opened=os.open;linked=os.link;fstat=os.fstat;save=capture.save;link_failed=False;first_clock=True

def failure(path,*a,**kw):
 if Path(path)==root/'.scratch/forgix-spi-finalization-pending.json':raise OSError('pending open')
 return opened(path,*a,**kw)
def link(*a,**kw):
 global link_failed
 link_failed=True;print('OWNED_QUARANTINE_EDGE',flush=True);raise OSError('owned link storage')
def identity(fd):
 if link_failed and sys.argv[3]=='identity':raise OSError('identity observation')
 return fstat(fd)
def saved(store,name,value):
 if name=='synthetic-quarantine.json'and sys.argv[3]=='receipt':raise OSError('quarantine receipt')
 return save(store,name,value)
def clock():
 global first_clock
 if first_clock:first_clock=False;return 10.
 return 610.
def execute(_adapter,store,preflight,*,began):
 adapter.cleaning=True;value={'status':'failed','original_flash_and_factory_verified':False,'owned_processes_closed':False}
 capture.save(store,'session.json',value);return value
with patch.object(c,'ROOT',root),patch.object(b,'ROOT',root),patch.object(t,'ROOT',root),patch.object(c,'parser',return_value=SimpleNamespace(parse_args=lambda:SimpleNamespace(action='run'))),patch.object(c,'prepare',return_value=(profile,{}, {},folder)),patch.object(b,'frozen_inputs'),patch.object(b,'qualified'),patch.object(c.runtime,'check'),patch.object(b,'Backend',return_value=adapter),patch.object(c,'execute',side_effect=execute),patch.object(c.os,'open',side_effect=failure),patch.object(c.os,'link',side_effect=link),patch.object(c.os,'fstat',side_effect=identity),patch.object(capture,'save',side_effect=saved),patch.object(c.time,'monotonic',side_effect=clock):
 raise SystemExit(c.main())
'''
                p=subprocess.Popen([sys.executable,'-B','-c',script,str(ROOT/'tools'),str(root),extra_failure],
                                   start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    ready,_,_=select.select([p.stdout],[],[],5)
                    self.assertTrue(ready,'owned child did not reach fault boundary')
                    self.assertEqual(p.stdout.readline().strip(),'OWNED_QUARANTINE_EDGE')
                    fd=os.open(root/'.scratch/esp-demo.lock',os.O_RDWR)
                    try:
                        with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        p.send_signal(signal.SIGTERM) # exact unreaped owned direct child, never a group
                        time.sleep(.03);self.assertIsNone(p.poll())
                        with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        self.assertTrue((root/b.LEASE).exists());self.assertFalse((root/u.PENDING_FINALIZATION).exists())
                        if extra_failure=='none':
                            until=time.monotonic()+3
                            while not (root/'backups/episode/synthetic-quarantine.json').exists() and time.monotonic()<until:time.sleep(.005)
                            result=json.loads((root/'backups/episode/session.json').read_bytes())
                            self.assertEqual(result['status'],'failed');self.assertTrue(result['deadline_exceeded'])
                            self.assertEqual(result['finalization_status'],'quarantined_unknown_closure')
                            self.assertEqual(result['quarantine_owner_pid'],p.pid)
                            actual=os.fstat(fd);self.assertEqual(result['quarantine_operator_identity'],{'device':actual.st_dev,'inode':actual.st_ino})
                    finally:os.close(fd)
                finally:
                    # Every resource is this harmless fixture; there are no child descendants/devices.
                    if p.poll() is None:p.kill()
                    p.wait(timeout=5);p.stdout.close();p.stderr.close()

if __name__=='__main__':unittest.main()

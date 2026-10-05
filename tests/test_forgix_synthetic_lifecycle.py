"""Distinct stream integration: real private files/flocks/processes, injected USB only."""
import copy
import errno
import fcntl
import hashlib
import json
import os
import pty
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_synthetic_backend as backend
import forgix_synthetic_lifecycle as lifecycle
import run_forgix_synthetic_trial as coordinator
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
from forgix_spi_lifecycle import WorkerOwner
from demo_esp_sdr import OwnedHardwareClosureError
from test_forgix_spi_lifecycle import Adapter as RegisterAdapter

class Adapter(RegisterAdapter):
    def __init__(self):
        super().__init__();self.profile.update(nonce='ab'*16,period=2000000,target=960)
    def stream(self,until):
        return self.take('stream',until,{'status':'lossless','replay':{'lossless':True},
            'transport_closed':True,'persistence_verified':True,'build_sha256':'d'*64,'image_sha256':'e'*64,
            'nonce':'ab'*16,'period':2000000,'target':960})

class Policy(unittest.TestCase):
    def run_policy(self,a,event=lambda x:None):return lifecycle.Lifecycle(a,event,lambda:a.now).run()
    def test_stream_has_one_stage_no_register_path_and_full_recovery(self):
        a=Adapter();r=self.run_policy(a)
        self.assertEqual([n for n,_ in a.calls],['admit','before','rom','ram','stream','return','after'])
        self.assertEqual(r['status'],'synthetic_completed');self.assertTrue(r['original_flash_and_factory_verified'])
        self.assertFalse(r['physical_qualification_proved'])
    def test_failed_initial_preservation_is_mutating_and_requires_recovery(self):
        a=Adapter();a.faults['before']=OSError('partial preservation')
        r=self.run_policy(a);self.assertEqual(r['status'],'failed')
        self.assertEqual([n for n,_ in a.calls],['admit','before','return','after'])
        self.assertTrue(r['recovery_required'] and r['original_flash_and_factory_verified'])
    def test_load_or_config_start_failure_never_retries_and_recovers(self):
        for step in ('rom','ram','stream'):
            with self.subTest(step=step):
                a=Adapter();a.faults[step]=TimeoutError('possibly consumed request')
                r=self.run_policy(a);self.assertEqual(r['status'],'failed')
                self.assertEqual([n for n,_ in a.calls].count(step),1)
                self.assertEqual([n for n,_ in a.calls][-2:],['return','after'])
    def test_wrong_nonce_image_build_profile_or_forensic_prefix_fails(self):
        for change in ({'nonce':'ac'*16},{'image_sha256':'f'*64},{'build_sha256':'f'*64},
                       {'period':2000000.0},{'target':True},{'status':'forensic_failed'},
                       {'replay':{'lossless':False}},{'transport_closed':False},{'persistence_verified':False}):
            a=Adapter();base=a.stream(0);a.calls=[];a.overrides['stream']={**base,**change}
            r=self.run_policy(a);self.assertEqual(r['status'],'failed');self.assertTrue(r['original_flash_and_factory_verified'])
    def test_unknown_closure_blocks_recovery_even_if_receipt_io_fails(self):
        a=Adapter()
        def bad(until):a.owner.closed=False;raise OwnedHardwareClosureError('unknown process')
        a.faults['stream']=bad
        def event(v):
            if v.get('phase')=='failed':raise OSError('disk failure')
        r=self.run_policy(a,event);self.assertFalse(r['owned_processes_closed']);self.assertEqual(r['status'],'failed')
        self.assertNotIn('return',[n for n,_ in a.calls])
    def test_cancel_rethrows_only_after_full_original_recovery(self):
        a=Adapter();a.faults['stream']=KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.run_policy(a)
        self.assertEqual([n for n,_ in a.calls][-2:],['return','after'])
    def test_final_persistence_and_stage_io_cannot_reset_deadline(self):
        a=Adapter()
        def late(v):
            if v.get('phase')=='terminal':a.now=600
        r=self.run_policy(a,late);self.assertEqual(r['status'],'failed')
        a=Adapter()
        def late_intent(v):
            if v.get('stage')=='preserve-before' and v['phase']=='intent':a.now=275
        r=self.run_policy(a,late_intent);self.assertNotIn('before',[n for n,_ in a.calls])
    def test_after_preservation_unknown_cannot_be_masked_by_earlier_failure(self):
        a=Adapter();a.faults['stream']=RuntimeError('capture')
        def bad(until):a.owner.closed=False;raise OwnedHardwareClosureError('post-read orphan')
        a.faults['after']=bad;r=self.run_policy(a)
        self.assertFalse(r['owned_processes_closed']);self.assertTrue(r['manual_recovery_required'])

class Coordinator(unittest.TestCase):
    def test_registry_refuses_before_any_artifact_environment_or_device(self):
        with patch.object(backend,'artifact',side_effect=AssertionError('access')):
            with self.assertRaisesRegex(ValueError,'No committed qualification'):coordinator.prepare(SimpleNamespace())
        r=subprocess.run([sys.executable,str(ROOT/'tools/run_forgix_synthetic_trial.py'),'run',
           '--artifact','missing','--binding','missing','--baseline-a','missing','--baseline-b','missing',
           '--qualification','missing','--private-dir','missing'],capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['status'],'refused')
    def test_fresh_interpreter_all_transitive_tools_are_explicitly_frozen(self):
        code='''import sys,json;from pathlib import Path
sys.path.insert(0,sys.argv[1]);import run_forgix_synthetic_trial as c
root=Path(sys.argv[1]).parent
files={str(Path(m.__file__).resolve().relative_to(root)) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(root/'tools')}
print(json.dumps(sorted(files-set(c.backend.EXECUTION_FILES))))'''
        r=subprocess.run([sys.executable,'-c',code,str(ROOT/'tools')],capture_output=True,text=True,check=True,timeout=20)
        self.assertEqual(json.loads(r.stdout),[])
    def test_real_git_freeze_refuses_dirty_input_and_preserves_registry_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for n in backend.EXECUTION_FILES:
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture\n')
            def git(*a):subprocess.run(['git',*a],cwd=root,check=True,capture_output=True,timeout=10)
            git('init');git('config','user.email','test@example.invalid');git('config','user.name','Test');git('add','.');git('commit','-m','fixture')
            with patch.object(coordinator,'ROOT',root),patch.object(trial,'ROOT',root):
                frozen=coordinator.freeze();self.assertIn(backend.REGISTRY,frozen['inputs'])
                (root/'tools/forgix_synthetic_collect.py').write_text('changed')
                with self.assertRaisesRegex(ValueError,'committed and unchanged'):coordinator.freeze()
    def test_global_clock_includes_final_receipt_and_initial_storage(self):
        for name in ('session.json','preflight.json'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'backups').mkdir();p=root/'backups/test';p.mkdir(mode=0o700)
                with patch.object(coordinator,'ROOT',root):store=coordinator.ReceiptStore(p)
                a=Adapter();save=capture.save
                def slow(s,n,value):
                    save(s,n,value)
                    if n==name:a.now=600
                with patch.object(capture,'save',slow):r=coordinator.execute(a,store,{'fixture_only':True},lambda:a.now)
                self.assertEqual(r['status'],'failed')
                if name=='preflight.json':self.assertFalse(a.calls)
                self.assertEqual(json.loads((p/'session.json').read_text())['status'],'failed')

class Ownership(unittest.TestCase):
    def test_real_lease_owner_death_releases_flock_but_retains_admission_blocker(self):
        for terminate in (False,True):
            with self.subTest(kill=terminate),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'.scratch').mkdir(mode=0o700)
                script='''import sys,os,time
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import run_forgix_synthetic_trial as c;import forgix_usb_ram_trial as t
c.ROOT=t.ROOT=Path(sys.argv[2])
with c.operator_lock():
 c.SessionLease({'uid_sha256':'a'*64},c.ROOT/'backups/child')
 if sys.argv[3]=='kill':
  print('READY',flush=True);time.sleep(20)
 else:os._exit(0)
'''
                p=subprocess.Popen([sys.executable,'-c',script,str(ROOT/'tools'),str(root),'kill' if terminate else 'exit'],stdout=subprocess.PIPE,text=True)
                try:
                    if terminate:self.assertEqual(p.stdout.readline().strip(),'READY');p.kill()
                    p.wait(timeout=10)
                finally:
                    if p.poll() is None:p.kill();p.wait()
                    p.stdout.close()
                lease=root/backend.LEASE;self.assertTrue(lease.exists());self.assertEqual(lease.stat().st_mode&0o777,0o600)
                with patch.object(coordinator,'ROOT',root):
                    with self.assertRaisesRegex(ValueError,'Unresolved synthetic'):
                        with coordinator.operator_lock():self.fail('lease bypass')
    def test_shared_unknown_and_old_register_lease_refuse_under_real_lock(self):
        for marker in ('forgix-usb-ram-unclosed.json','forgix-spi-active.json'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'.scratch').mkdir();(root/'.scratch'/marker).write_text('{}')
                with patch.object(coordinator,'ROOT',root),self.assertRaises(ValueError):
                    with coordinator.operator_lock():self.fail('admitted')
    def test_real_worker_inherits_lock_and_timeout_reaps_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);lock=root/'lock';fd=os.open(lock,os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
            workers=root/'workers';workers.mkdir(mode=0o700);owner=WorkerOwner(workers,fd,lock)
            try:
                code='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from forgix_usb_ram_capture import inherited_operator_lock;inherited_operator_lock(int(sys.argv[2]),sys.argv[3])'
                r=owner.run([sys.executable,'-c',code,str(ROOT/'tools'),str(fd),str(lock)],'lock',time.monotonic()+10)
                self.assertTrue(r['owned_processes_closed'])
                child=root/'child'
                code='import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c","import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)"]);open(sys.argv[1],"w").write(str(p.pid));time.sleep(20)'
                with self.assertRaises(subprocess.TimeoutExpired):owner.run([sys.executable,'-c',code,str(child)],'blocked',time.monotonic()+.6)
                self.assertTrue(owner.closed)
                if child.exists():
                    pid=int(child.read_text());statfile=Path('/proc')/str(pid)/'stat'
                    self.assertTrue(not statfile.exists() or statfile.read_text().split()[2]=='Z')
            finally:os.close(fd)

class Selection(unittest.TestCase):
    def test_pid_product_uid_and_bus_strict_before_tty_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);usb=root/'bus/usb/devices/3-3';usb.mkdir(parents=True)
            values={'serial':'0123456789abcdef','busnum':'3','devnum':'9','idVendor':'cafe','idProduct':'4013','product':'Forgix Synthetic RAM stream v1'}
            for n,v in values.items():(usb/n).write_text(v)
            p={'uid_sha256':hashlib.sha256(values['serial'].encode()).hexdigest()}
            with patch.object(trial,'fresh_tty',return_value='/dev/fixture') as tty:
                r=backend.select_stream(p,3,sys_root=root);self.assertEqual(r['pid'],'4013');tty.assert_called_once()
                for name,value in [('idProduct','4012'),('product','Forgix SPI RAM bridge v1'),('serial','ffffffffffffffff'),('busnum','4')]:
                    (usb/name).write_text(value)
                    with self.assertRaises(ValueError):backend.select_stream(p,3,sys_root=root)
                    (usb/name).write_text(values[name])
    def test_only_explicit_synthetic_elf_rom_load_no_flash_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'elf';f.write_bytes(b'fixture')
            p=object.__new__(backend.SyntheticPicotool);p.profile={'elf_sha256':trial.sha(f)}
            with patch.object(backend,'inspect_elf') as inspect:
                args=p.load_args(SimpleNamespace(pid=trial.preserve.BOOT_PID,bus=3,address=4),f,'/private/ram-synthetic-stream.elf')
                inspect.assert_called_once_with(b'fixture',application='synthetic-stream')
                self.assertEqual(args,['load','-v','-x','/private/ram-synthetic-stream.elf','-t','elf','--bus','3','--address','4'])
                with self.assertRaises(ValueError):p.load_args(SimpleNamespace(pid='0009'),f,'/private/ram-synthetic-stream.elf')

class QualifiedReceipt(unittest.TestCase):
    def test_full_uid_execution_environment_and_profile_binding_with_actual_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir();path=root/'.scratch/q.json'
            env={'fixture':'immutable runtime'};frozen={'inputs':{}}
            p={n:'a'*64 for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','startup_audit_sha256')}
            p.update(configuration={'exact':'image'},artifact_exports={'elf':'hash'},period=2000000,target=960,rp_pause=False,host_pause=True,
                     qualification_path=str(path),execution_sha256=backend.digest({}),environment_sha256=backend.digest(env))
            q={**p,'kind':'Forgix physical synthetic stream episode qualification','contract_sha256':backend.CONTRACT_SHA256,
               'environment':env,'reviewed_execution_sha256':{},'admission_registry_binding':'separately frozen committed registry',
               **{n:True for n in ('fpga_grade_verified','clock_verified','spi_handoff_verified','whole_loading_recovery_reviewed','startup_uid_reviewed')}}
            def write(value):path.write_text(json.dumps(value));path.chmod(0o600);p['qualification_sha256']=trial.sha(path)
            with patch.object(trial,'ROOT',root),patch.object(backend,'EXECUTION_FILES',frozenset()):
                write(q);self.assertEqual(backend.qualification_receipt(p,env,frozen)['uid_sha256'],p['uid_sha256'])
                for key,value in [('uid_sha256','b'*64),('baseline_sha256','b'*64),('target',960.0),('rp_pause',0),('environment',{}),('clock_verified',False)]:
                    write({**q,key:value})
                    with self.subTest(key=key),self.assertRaises(ValueError):backend.qualification_receipt(p,env,frozen)
                write(q);p['execution_sha256']='f'*64
                with self.assertRaisesRegex(ValueError,'tuple differs'):backend.qualification_receipt(p,env,frozen)
    def test_worker_never_uses_register_routes_and_late_boot_refuses_spawn(self):
        for name in ('configure','collect','transition'):
            b=object.__new__(backend.Backend)
            with self.assertRaisesRegex(ValueError,'exclusively'):getattr(b,name)(0)
        b=object.__new__(backend.Backend);b.hardware_gate=lambda x:None;b.boot_host_ns=0
        with patch.object(time,'monotonic_ns',return_value=30_000_000_000):
            with self.assertRaisesRegex(ValueError,'budget exhausted'):b.stream(120)

class ActualWireIntegration(unittest.TestCase):
    def test_one_worker_operation_uses_actual_c_frames_single_config_start_and_replay(self):
        from test_forgix_synthetic_collect import Collection
        Collection.setUpClass();case=Collection();case.setUp()
        try:
            b=case.binding;p={'nonce':b.nonce.hex(),'period':b.period,'target':b.target,
                 'bridge_source_sha256':b.build.hex(),'bitstream_sha256':b.image.hex(),'rp_pause':False,'host_pause':True}
            request={'profile':p,'lockfd':case.fd,'lockpath':str(case.lockpath),'boot_host_ns':1_000_000_000}
            result=backend.serial_operation(request,case.root/'worker',lambda:case.identity.copy(),case.open,
                                            case.admission,case.clock.now,case.clock.pause)
            self.assertEqual(result['status'],'lossless');self.assertTrue(result['transport_closed'])
            self.assertEqual(case.tx.writes,[b.command(1),b.command(2)])
            self.assertTrue(backend.collector.replay(case.root/'worker',b)['lossless'])
            self.assertEqual(len(bytes.fromhex(p['nonce'])),16)
        finally:case.tearDown();Collection.tearDownClass()
    def test_actual_partial_transport_prefix_does_not_retry_and_is_saved_after_close(self):
        from test_forgix_synthetic_collect import Collection
        Collection.setUpClass();case=Collection();case.setUp()
        try:
            b=case.binding;p={'nonce':b.nonce.hex(),'period':b.period,'target':b.target,
                 'bridge_source_sha256':b.build.hex(),'bitstream_sha256':b.image.hex(),'rp_pause':False,'host_pause':True}
            error=OSError('transport');error.consumed_prefix=case.frames[0][:31];case.tx.error=error
            request={'profile':p,'lockfd':case.fd,'lockpath':str(case.lockpath),'boot_host_ns':1_000_000_000}
            with self.assertRaises(OSError):backend.serial_operation(request,case.root/'failed',lambda:case.identity.copy(),case.open,
                                             case.admission,case.clock.now,case.clock.pause)
            self.assertTrue(case.tx.closed);self.assertEqual(case.tx.writes,[b.command(1)])
            self.assertEqual((case.root/'failed/raw.bin').read_bytes(),error.consumed_prefix)
            saved=json.loads((case.root/'failed/result.json').read_bytes());self.assertEqual(saved['status'],'failed')
            self.assertEqual(saved['raw_bytes'],31);self.assertTrue(saved['transport_closed'])
        finally:case.tearDown();Collection.tearDownClass()

class PosixPrefix(unittest.TestCase):
    """Actual pyserial POSIX reads on PTYs; only faulting os.read is injected."""
    def exercise(self,factory,operation,payload=b'private-prefix-and-tail'):
        import serial
        import serial.serialposix as posix
        master,slave=pty.openpty();handle=None
        try:
            with patch.object(serial.Serial,'_update_dtr_state',return_value=None):
                handle=backend.open_retaining_serial(os.ttyname(slave))
            os.write(master,payload)
            native_read=os.read;observed=bytearray()
            def fault(fd,size):
                if fd!=handle.fd:return native_read(fd,size)
                if len(observed)>=7:raise OSError(errno.EIO,'injected POSIX read')
                raw=native_read(fd,min(size,7-len(observed)));observed.extend(raw);return raw
            with patch.object(posix.os,'read',fault):return operation(factory(handle),observed)
        finally:
            if handle is not None:
                handle.close();self.assertFalse(handle.is_open)
            os.close(master);os.close(slave)
    def test_real_posix_eio_baseline_loses_prefix_new_adapter_exposes_it(self):
        import serial
        for factory,expected in ((capture.SerialDeadlineTransport,b''),(backend.SyntheticTransport,b'private')):
            def check(tx,observed):
                with self.assertRaises(serial.SerialException) as failed:tx.read(512,time.monotonic()+1)
                self.assertEqual(bytes(observed),b'private')
                self.assertEqual(getattr(failed.exception,'consumed_prefix',b''),expected)
                tx.close();self.assertFalse(tx.serial.is_open)
            self.exercise(factory,check)
    def test_real_posix_interrupt_retains_each_returned_byte(self):
        import serial.serialposix as posix
        def check(tx,observed):
            previous=posix.os.read
            def interrupted(fd,size):
                if fd==tx.serial.fd and len(observed)>=7:raise KeyboardInterrupt()
                return previous(fd,size)
            with patch.object(posix.os,'read',interrupted),self.assertRaises(KeyboardInterrupt) as failed:
                tx.read(512,time.monotonic()+1)
            self.assertEqual(failed.exception.consumed_prefix,b'private')
            self.assertEqual(bytes(observed),b'private')
        self.exercise(backend.SyntheticTransport,check)
    def test_real_posix_late_byte_is_retained_and_size_is_bounded(self):
        import serial.serialposix as posix
        def check(tx,observed):
            clock=SimpleNamespace(now=0);tx.clock=lambda:clock.now;previous=posix.os.read
            def late(fd,size):
                raw=previous(fd,size)
                if fd==tx.serial.fd:clock.now=2
                return raw
            with patch.object(posix.os,'read',late):self.assertEqual(tx.read(1,1),b'p')
            with self.assertRaises(TimeoutError) as failed:tx.read(2,1)
            self.assertEqual(failed.exception.consumed_prefix,b'')
            clock.now=0
            with patch.object(posix.os,'read',late),self.assertRaises(TimeoutError) as failed:tx.read(2,1)
            self.assertEqual(failed.exception.consumed_prefix,b'r')
            for size in (0,513,True,1.0):
                with self.assertRaises(ValueError):tx.read(size,3)
        self.exercise(backend.SyntheticTransport,check)
    def test_real_posix_prefix_is_saved_by_collector_after_serial_closure(self):
        from test_forgix_synthetic_collect import Collection
        Collection.setUpClass();case=Collection();case.setUp()
        try:
            b=case.binding;p={'nonce':b.nonce.hex(),'period':b.period,'target':b.target,
                'bridge_source_sha256':b.build.hex(),'bitstream_sha256':b.image.hex(),'rp_pause':False,'host_pause':True}
            request={'profile':p,'lockfd':case.fd,'lockpath':str(case.lockpath),'boot_host_ns':1_000_000_000}
            def check(tx,observed):
                with self.assertRaises(OSError):backend.serial_operation(request,case.root/'posix',lambda:case.identity.copy(),
                    lambda identity,until:tx,case.admission,case.clock.now,case.clock.pause)
                self.assertFalse(tx.serial.is_open)
                self.assertEqual((case.root/'posix/raw.bin').read_bytes(),b'private')
                saved=json.loads((case.root/'posix/result.json').read_bytes())
                self.assertEqual(saved['status'],'failed');self.assertTrue(saved['transport_closed'])
                self.assertEqual(saved['raw_bytes'],7);self.assertEqual(bytes(observed),b'private')
            self.exercise(lambda handle:backend.SyntheticTransport(handle,lambda:case.clock.now()/1e9),check)
        finally:case.tearDown();Collection.tearDownClass()

class TerminalWrites(unittest.TestCase):
    def test_late_lease_release_rewrites_authoritative_saved_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir();p=root/'backups/run';p.mkdir(mode=0o700)
            with patch.object(coordinator,'ROOT',root):store=coordinator.ReceiptStore(p)
            r={'status':'synthetic_episode_completed','original_flash_and_factory_verified':True,'owned_processes_closed':True}
            capture.save(store,'session.json',r);clock=SimpleNamespace(value=1)
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                lease=coordinator.SessionLease({'uid_sha256':'a'*64},p);release=lease.release
                def delayed(record):release(record);clock.value=600
                with patch.object(lease,'release',side_effect=delayed),self.assertRaises(TimeoutError):
                    coordinator.release_lease(lease,store,r,0,lambda:clock.value)
                self.assertTrue(lease.pending_path.exists())
            saved=json.loads((p/'session.json').read_bytes());self.assertEqual(saved['status'],'failed')
            self.assertEqual(saved['host_elapsed_seconds'],600);self.assertTrue(saved['deadline_exceeded'])
    def test_partial_lease_and_storage_failure_block_both_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir()
            with patch.object(coordinator,'ROOT',root),patch.object(capture,'durable',side_effect=OSError('disk')):
                with self.assertRaises(OSError):coordinator.SessionLease({'uid_sha256':'a'*64},root/'backups/run')
            with patch.object(coordinator,'ROOT',root),self.assertRaisesRegex(ValueError,'Unresolved synthetic'):
                with coordinator.operator_lock():self.fail('partial admission')
            import run_forgix_spi_trial as old
            with patch.object(old,'ROOT',root),self.assertRaisesRegex(ValueError,'Unresolved register'):
                with old.operator_lock():self.fail('cross-route bypass')

class LeaseBinding(unittest.TestCase):
    def test_nonce_or_qualified_tuple_substitution_cannot_reuse_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir();p={'uid_sha256':'a'*64,'nonce':'a1'*16,'execution_sha256':'b'*64}
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                lease=coordinator.SessionLease(p,root/'backups/run')
                self.assertEqual(backend.session_lease(p),lease.path)
                for key,value in [('nonce','a2'*16),('execution_sha256','c'*64)]:
                    with self.assertRaisesRegex(ValueError,'owner differs'):backend.session_lease({**p,key:value})

class ReleaseFailure(unittest.TestCase):
    def test_failed_release_durability_cannot_leave_successful_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir();p=root/'backups/run';p.mkdir(mode=0o700)
            with patch.object(coordinator,'ROOT',root):store=coordinator.ReceiptStore(p)
            r={'status':'synthetic_episode_completed','original_flash_and_factory_verified':True,'owned_processes_closed':True}
            capture.save(store,'session.json',r)
            def failed(record):raise OSError('release fsync')
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                lease=coordinator.SessionLease({'uid_sha256':'a'*64},p)
                with patch.object(lease,'release',side_effect=failed),self.assertRaisesRegex(OSError,'release fsync'):
                    coordinator.release_lease(lease,store,r,0,lambda:1)
                self.assertTrue(lease.pending_path.exists())
            saved=json.loads((p/'session.json').read_bytes());self.assertEqual(saved['status'],'failed')
            self.assertEqual(saved['lease_release_failure_kind'],'OSError')

class ExplicitRecovery(unittest.TestCase):
    def test_only_factory_and_full_original_readback_never_install_or_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'backups').mkdir();p=root/'backups/recover';p.mkdir(mode=0o700)
            with patch.object(coordinator,'ROOT',root):store=coordinator.ReceiptStore(p)
            a=Adapter();r=coordinator.execute_recovery(a,store,{'physical_execution_requested':False},lambda:a.now)
            self.assertEqual([n for n,_ in a.calls],['admit','return','after'])
            self.assertEqual(r['status'],'recovery_observed')
            self.assertEqual(r['finalization_status'],'pending')
            self.assertTrue(r['original_flash_and_factory_verified'] and r['owned_processes_closed'])
            self.assertEqual(r['ram_load_operations'],0);self.assertEqual(r['configuration_start_operations'],0)
    def test_unknown_recovery_closure_or_late_write_never_accepts(self):
        for fault in ('unknown','late'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'backups').mkdir();p=root/'backups/recover';p.mkdir(mode=0o700)
                with patch.object(coordinator,'ROOT',root):store=coordinator.ReceiptStore(p)
                a=Adapter();save=capture.save
                if fault=='unknown':
                    def bad(until):a.owner.closed=False;raise OwnedHardwareClosureError('unknown')
                    a.faults['return']=bad
                def persist(s,n,r):
                    save(s,n,r)
                    if n=='session.json' and fault=='late':a.now=600
                with patch.object(capture,'save',persist):r=coordinator.execute_recovery(a,store,{},lambda:a.now)
                self.assertEqual(r['status'],'failed');self.assertEqual(json.loads((p/'session.json').read_bytes())['status'],'failed')
                if fault=='unknown':self.assertNotIn('after',[n for n,_ in a.calls]);self.assertFalse(r['owned_processes_closed'])
    def test_lease_rotation_blocks_old_receipt_and_crashed_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir();(root/'backups').mkdir()
            original=root/'backups/old';new=root/'backups/new';profile={'uid_sha256':'a'*64,'nonce':'a1'*16}
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                initial=coordinator.SessionLease(profile,original);old=profile.copy()
                replacement=coordinator.SessionLease.rotate(profile,new)
                self.assertEqual(backend.session_lease(profile,new),replacement.path)
                with self.assertRaisesRegex(ValueError,'lease changed'):backend.session_lease(old,original)
                with self.assertRaisesRegex(ValueError,'Unresolved synthetic'):
                    with coordinator.operator_lock():self.fail('crashed recovery bypass')
                with coordinator.operator_lock(profile):pass
    def test_changed_lease_cannot_rotate_and_does_not_mutate_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir();p={'uid_sha256':'a'*64}
            with patch.object(coordinator,'ROOT',root),patch.object(backend,'ROOT',root),patch.object(trial,'ROOT',root):
                lease=coordinator.SessionLease(p,root/'backups/old');before=p.copy();lease.path.write_text('{}')
                with self.assertRaisesRegex(ValueError,'lease changed'):coordinator.SessionLease.rotate(p,root/'backups/new')
                self.assertEqual(p,before);self.assertEqual(lease.path.read_text(),'{}')
    def test_unknown_or_missing_saved_closure_refuses_before_lease_or_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'backups/old';p.mkdir(parents=True,mode=0o700);file=p/'session.json'
            for closure in (False,None,1):
                file.write_text(json.dumps({'owned_processes_closed':closure,'physical_execution_requested':True}));file.chmod(0o600)
                with patch.object(coordinator,'ROOT',root),patch.object(trial,'ROOT',root),patch.object(backend,'session_lease',side_effect=AssertionError('lease reached')):
                    with self.assertRaisesRegex(ValueError,'Known aggregate'):coordinator.recovery_admission(file,{}, {},{'inputs':{}})
    def test_recovery_backend_cannot_load_configure_or_collect(self):
        b=object.__new__(backend.RecoveryBackend)
        for method in ('enter_rom','load_ram','stream','configure','collect','transition'):
            with self.assertRaises(ValueError):getattr(b,method)(0)

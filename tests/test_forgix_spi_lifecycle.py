"""Lifecycle faults plus real regular-file/lock process tests; no devices."""
import copy
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import forgix_spi_lifecycle as lifecycle
import demo_esp_sdr as processes


class Adapter:
    def __init__(self, strategy='after_ram_startup'):
        self.now = 0.
        self.owner = SimpleNamespace(closed=True)
        self.cleaning = False
        self.calls, self.faults, self.overrides = [], {}, {}
        self.profile = {'uid_sha256':'a'*64,'baseline_sha256':'b'*64,
                        'elf_sha256':'c'*64,'bridge_source_sha256':'d'*64,
                        'bitstream_sha256':'e'*64,'qualification_verified':True,
                        'configuration_strategy':strategy}
        self.preserved = {'uid_sha256':'a'*64,'flash_bytes':2097152,
                          'read_sha256':['b'*64]*2,'independent_device_verify':True,
                          'factory_application_verified':True}

    def take(self, name, until, receipt):
        self.calls.append((name,until))
        self.now += .1
        fault = self.faults.get(name)
        if callable(fault):
            fault(until)
        elif fault:
            raise fault
        return copy.deepcopy(self.overrides.get(name,receipt))

    def check_inputs(self):
        if self.faults.get('inputs'):
            raise self.faults['inputs']

    def admit(self, until): return self.take('admit',until,self.profile)
    def preserve_before(self, until): return self.take('before',until,self.preserved)
    def configure(self, until): return self.take('configure',until,{'bitstream_sha256':'e'*64})
    def enter_rom(self, until): return self.take('rom',until,{})
    def load_ram(self, until): return self.take('ram',until,{'elf_sha256':'c'*64})
    def transition(self, until):
        return self.take('transition',until,{'bitstream_sha256':'e'*64,
                                           'configuration_continuity_verified':True})
    def collect(self, until):
        return self.take('collect',until,{'status':'registers_verified',
             'build_source_sha256':'d'*64,'persistence_verified':True,'transport_closed':True,
             'register_run':{'result':'passed','scratch_restore_verified':True,'finish_reply_verified':True}})
    def return_factory(self, until): return self.take('return',until,{})
    def preserve_after(self, until): return self.take('after',until,self.preserved)


class Policy(unittest.TestCase):
    def setUp(self):
        self.adapter = Adapter()
        self.saved = []
        self.engine = lifecycle.Lifecycle(self.adapter,lambda e:self.saved.append(copy.deepcopy(e)),
                                           lambda:self.adapter.now)

    def names(self): return [name for name,_ in self.adapter.calls]

    def test_both_configuration_strategies_order_preservation_and_recovery(self):
        for strategy,expected in [
          ('after_ram_startup',['admit','before','rom','ram','configure','transition','collect','return','after']),
          ('qualified_retention',['admit','before','configure','rom','ram','transition','collect','return','after'])]:
            with self.subTest(strategy=strategy):
                adapter = Adapter(strategy)
                engine = lifecycle.Lifecycle(adapter,lambda e:None,lambda:adapter.now)
                result = engine.run()
                self.assertEqual([n for n,_ in adapter.calls],expected)
                self.assertEqual(result['status'],'model_completed')
                self.assertTrue(result['original_flash_and_factory_verified'])
                self.assertFalse(result['physical_execution_admitted'] or result['physical_qualification_proved'])
                with self.assertRaises(lifecycle.LifecycleError): engine.run()

    def test_incomplete_admission_refuses_preservation_or_load(self):
        self.adapter.profile['qualification_verified'] = False
        result = self.engine.run()
        self.assertEqual(result['status'],'failed')
        self.assertEqual(self.names(),['admit'])
        self.assertFalse(result['recovery_required'])

    def test_bad_preservation_never_loads_or_configures_and_recovers_factory(self):
        for fields in [{'uid_sha256':'f'*64},{'flash_bytes':2097152.0},
                       {'read_sha256':['b'*64]},{'independent_device_verify':False},
                       {'factory_application_verified':False}]:
            with self.subTest(fields=fields):
                adapter=Adapter();adapter.overrides['before']={**adapter.preserved,**fields}
                engine=lifecycle.Lifecycle(adapter,lambda e:None,lambda:adapter.now)
                result=engine.run()
                self.assertEqual(result['status'],'failed')
                self.assertEqual([n for n,_ in adapter.calls],['admit','before','return','after'])
                self.assertTrue(result['original_flash_and_factory_verified'])

    def test_lost_rom_ack_still_returns_and_verifies_full_original(self):
        self.adapter.faults['rom'] = TimeoutError('ACK lost after possible mode change')
        result=self.engine.run()
        self.assertEqual(result['status'],'failed')
        self.assertEqual(self.names(),['admit','before','rom','return','after'])
        self.assertTrue(result['original_flash_and_factory_verified'])
        intent=next(e for e in self.saved if e.get('stage')=='enter-rom' and e['phase']=='intent')
        self.assertTrue(intent['may_change_mode_or_fpga'])

    def test_wrong_loaded_image_and_cdone_only_transition_never_collect(self):
        for stage,receipt in [('ram',{'elf_sha256':'f'*64}),
                              ('configure',{'bitstream_sha256':'f'*64}),
                              ('transition',{'cdone':True})]:
            with self.subTest(stage=stage):
                adapter=Adapter();adapter.overrides[stage]=receipt
                engine=lifecycle.Lifecycle(adapter,lambda e:None,lambda:adapter.now)
                result=engine.run();names=[n for n,_ in adapter.calls]
                self.assertEqual(result['status'],'failed')
                self.assertNotIn('collect',names)
                self.assertEqual(names[-2:],['return','after'])
                self.assertTrue(result['original_flash_and_factory_verified'])

    def test_scratch_or_collector_integrity_failure_still_recovers(self):
        normal=self.adapter.collect(45)
        for field,value in [('build_source_sha256','f'*64),('persistence_verified',False),
                            ('transport_closed',False),('scratch_restore_verified',False),
                            ('finish_reply_verified',False)]:
            with self.subTest(field=field):
                adapter=Adapter();receipt=copy.deepcopy(normal)
                (receipt['register_run'] if field in ('scratch_restore_verified','finish_reply_verified') else receipt)[field]=value
                adapter.overrides['collect']=receipt
                result=lifecycle.Lifecycle(adapter,lambda e:None,lambda:adapter.now).run()
                self.assertEqual(result['status'],'failed')
                self.assertTrue(result['original_flash_and_factory_verified'])

    def test_unknown_collector_group_blocks_all_recovery_access(self):
        def unclosed(until):
            self.adapter.owner.closed=False
            raise RuntimeError('original exception does not override closure uncertainty')
        self.adapter.faults['collect']=unclosed
        result=self.engine.run()
        self.assertEqual(result['error_kind'],'OwnedHardwareClosureError')
        self.assertFalse(result['owned_processes_closed'])
        self.assertNotIn('return',self.names())
        self.assertNotIn('after',self.names())
        self.assertTrue(result['manual_recovery_required'])

    def test_cancel_propagates_after_verified_cleanup(self):
        self.adapter.faults['collect']=KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.engine.run()
        self.assertEqual(self.names()[-2:],['return','after'])
        self.assertTrue(self.engine.summary['original_flash_and_factory_verified'])
        self.assertTrue(self.adapter.cleaning)
        self.assertEqual(self.saved[-1]['phase'],'terminal')

    def test_bad_post_preservation_cannot_report_completed(self):
        self.adapter.overrides['after']={**self.adapter.preserved,'read_sha256':['f'*64]*2}
        result=self.engine.run()
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['original_flash_and_factory_verified'])
        self.assertTrue(result['manual_recovery_required'])

    def test_frozen_input_change_blocks_later_access_and_retains_failed_state(self):
        def changed(until):self.adapter.faults['inputs']=ValueError('frozen input changed')
        self.adapter.faults['collect']=changed
        result=self.engine.run()
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['manual_recovery_required'])
        self.assertNotIn('return',self.names())
        self.assertNotIn('after',self.names())

    def test_operation_deadline_reserves_cleanup_allowance(self):
        def stalled(until):self.adapter.now=self.engine.work_deadline
        self.adapter.faults['ram']=stalled
        result=self.engine.run()
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['original_flash_and_factory_verified'])
        self.assertLess(self.adapter.now,600)
        self.assertEqual(self.engine.work_deadline,275)
        self.assertEqual(self.names()[-2:],['return','after'])

    def test_intent_persistence_failure_prevents_first_mutation(self):
        def fail(event):
            if event.get('stage')=='preserve-before' and event['phase']=='intent':raise OSError('disk failed')
        self.engine.write_event=fail
        result=self.engine.run()
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['recovery_required'])
        self.assertEqual(self.names(),['admit'])

    def test_late_terminal_receipt_and_unpersisted_terminal_cannot_pass(self):
        def late(event):
            self.saved.append(copy.deepcopy(event))
            if event['phase']=='terminal':self.adapter.now=600
        self.engine.write_event=late
        self.assertEqual(self.engine.run()['status'],'failed')
        self.assertEqual(self.saved[-1]['phase'],'late-terminal')
        adapter=Adapter()
        def failed(event):
            if event['phase']=='terminal':raise OSError('disk failed')
        engine=lifecycle.Lifecycle(adapter,failed,lambda:adapter.now)
        with self.assertRaises(OSError):engine.run()
        self.assertEqual(engine.summary['status'],'failed')


class Workers(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.lockpath=self.root/'operator.lock'
        self.fd=os.open(self.lockpath,os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.owner=lifecycle.WorkerOwner(self.root,self.fd,self.lockpath)

    def tearDown(self):
        os.close(self.fd)
        self.temp.cleanup()

    def test_real_worker_inherits_lock_closes_group_and_keeps_private_log(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);from forgix_usb_ram_capture import inherited_operator_lock;inherited_operator_lock(int(sys.argv[2]),sys.argv[3]);print('fixture-lock-verified')"
        result=self.owner.run([sys.executable,'-c',code,str(Path(lifecycle.__file__).parent),
                               str(self.fd),str(self.lockpath)],'fixture',time.monotonic()+10)
        self.assertTrue(result['owned_processes_closed'] and self.owner.closed)
        log=self.root/'00-fixture.log'
        self.assertIn('fixture-lock-verified',log.read_text())
        self.assertEqual(log.stat().st_mode & 0o777,0o600)
        other=os.open(self.lockpath,os.O_RDWR)
        try:
            with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally:os.close(other)

    def test_real_timeout_reaps_regular_file_owner_before_returning(self):
        pidfile=self.root/'fixture.pid'
        code="import os,sys,time;f=open(sys.argv[1],'w');f.write(str(os.getpid()));f.flush();time.sleep(600)"
        with self.assertRaises(subprocess.TimeoutExpired):
            self.owner.run([sys.executable,'-c',code,str(pidfile)],'timeout',time.monotonic()+.4)
        self.assertTrue(self.owner.closed)
        pid=int(pidfile.read_text())
        self.assertFalse(Path('/proc',str(pid)).exists())
        self.assertFalse(processes.group_exists(pid))

    def test_unknown_closure_blocks_later_spawn_even_when_marker_failed(self):
        with patch.object(lifecycle,'owned_worker',side_effect=processes.OwnedHardwareClosureError('unknown')):
            with self.assertRaises(processes.OwnedHardwareClosureError):
                self.owner.run(['fixture'],'unknown',time.monotonic()+1)
        self.assertFalse(self.owner.closed)
        with patch.object(lifecycle,'owned_worker') as spawn:
            with self.assertRaises(processes.OwnedHardwareClosureError):
                self.owner.run(['fixture'],'later',time.monotonic()+1)
            spawn.assert_not_called()

    def test_spawn_cancellation_is_cleaned_up_by_existing_owner(self):
        proc=SimpleNamespace(pid=999,wait=lambda **kw:0)
        import forgix_usb_ram_trial as original
        def spawn(*args,**kwargs):
            os.kill(os.getpid(),signal.SIGINT)
            return proc
        with patch.object(original.subprocess,'Popen',side_effect=spawn),patch.object(original,'stop_process') as close:
            with self.assertRaises(KeyboardInterrupt):
                self.owner.run(['fixture'],'cancel',time.monotonic()+1)
            close.assert_called_once_with(proc,grace_seconds=3)
        self.assertTrue(self.owner.closed)

    def test_unheld_lock_or_expired_deadline_never_spawns(self):
        with patch.object(lifecycle,'owned_worker') as spawn:
            with self.assertRaises(lifecycle.LifecycleError):
                self.owner.run(['fixture'],'expired',time.monotonic())
            fcntl.flock(self.fd,fcntl.LOCK_UN)
            with self.assertRaises(Exception):
                self.owner.run(['fixture'],'unheld',time.monotonic()+1)
            spawn.assert_not_called()

    def test_late_worker_success_is_rejected_after_verified_closure(self):
        now=[0.]
        self.owner.clock=lambda:now[0]
        def late(*args):
            now[0]=10
            return 0
        with patch.object(lifecycle,'owned_worker',side_effect=late):
            with self.assertRaises(lifecycle.LifecycleError):
                self.owner.run(['fixture'],'late',10)
        self.assertTrue(self.owner.closed)

    def test_real_exited_leader_does_not_leave_descriptor_owning_descendant(self):
        # A disposable subreaper owns/reaps only this fixture's orphaned child.
        # The held descriptor is a regular file; no serial/USB path is opened.
        code=r'''
import ctypes,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import forgix_spi_lifecycle as m
import demo_esp_sdr as processes
import fcntl
assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
root=Path(sys.argv[2]);lockpath=root/'lock'
fd=os.open(lockpath,os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
child_code="import os,signal,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);f=open(sys.argv[1],'w');f.write(str(os.getpid()));f.flush();time.sleep(600)"
leader_code="import subprocess,sys,time;p=subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]);print(p.pid,flush=True);time.sleep(.2)"
held=root/'held';reaped=[];child_ids=[]
def reap():
 until=time.monotonic()+10
 text=''
 while time.monotonic()<until:
  try:text=held.read_text()
  except FileNotFoundError:pass
  if text.isdigit():break
  time.sleep(.01)
 assert text.isdigit()
 child=int(text);child_ids.append(child)
 while time.monotonic()<until:
  try:status=Path('/proc',str(child),'status').read_text()
  except FileNotFoundError:break
  if '\nPPid:\t'+str(os.getpid())+'\n' in status:
   reaped.append(os.waitpid(child,0)[0]==child);return
  time.sleep(.01)
thread=threading.Thread(target=reap,daemon=True);thread.start()
try:
 owner=m.WorkerOwner(root,fd,lockpath)
 result=owner.run([sys.executable,'-c',leader_code,child_code,str(held)],'descendant',time.monotonic()+15)
 thread.join(timeout=3)
 assert reaped==[True] and child_ids
 child=child_ids[0]
 print(json.dumps({'group_closed':result['owned_processes_closed'],'descendant_reaped':reaped==[True],
                   'fake_descriptor_owner_gone':not Path('/proc',str(child),'fd').exists()}))
finally:
 os.close(fd)
 if child_ids:
  try:os.kill(child_ids[0],signal.SIGKILL)
  except ProcessLookupError:pass
'''
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run([sys.executable,'-c',code,str(Path(lifecycle.__file__).parent),tmp],
                                  capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(all(json.loads(result.stdout).values()))


if __name__=='__main__':unittest.main()

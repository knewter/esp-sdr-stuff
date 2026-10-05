"""Registry/lease/lifecycle integration with harmless actual OS resources."""
import contextlib,fcntl,hashlib,io,json,os,signal,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import forgix_clock_backend as b
import run_forgix_clock_trial as c
from forgix_clock_lifecycle import Lifecycle
from forgix_spi_lifecycle import WorkerOwner
from demo_esp_sdr import OwnedHardwareClosureError

class Model:
 def __init__(self,mode=None):
  self.mode=mode;self.calls=[];self.owner=types.SimpleNamespace(closed=True);self.cleaning=False
  self.profile={n:'1'*64 for n in ('uid_sha256','baseline_sha256','elf_sha256','bridge_source_sha256','bitstream_sha256')};self.profile['nonce']='2'*32
 def check_inputs(self):pass
 def admit(self,d):self.calls.append('admit');return dict(self.profile,qualification_verified=True)
 def preservation(self,d):return {'uid_sha256':self.profile['uid_sha256'],'flash_bytes':2097152,'read_sha256':[self.profile['baseline_sha256']]*2,'independent_device_verify':True,'factory_application_verified':True}
 def preserve_before(self,d):self.calls.append('before');return self.preservation(d)
 def preserve_after(self,d):self.calls.append('after');return self.preservation(d)
 def enter_rom(self,d):self.calls.append('rom');return {}
 def load_ram(self,d):self.calls.append('load');return {'elf_sha256':self.profile['elf_sha256']}
 def observe(self,d):
  self.calls.append('observe')
  if self.mode=='unknown':self.owner.closed=False;raise OwnedHardwareClosureError('fixture')
  if self.mode=='failure':raise OSError('fixture')
  return {'status':'digital_ratio_observed','transport_closed':True,'persistence_verified':True,'replay':{'observer_status':0},'build_sha256':self.profile['bridge_source_sha256'],'image_sha256':self.profile['bitstream_sha256'],'nonce':self.profile['nonce']}
 def return_factory(self,d):self.calls.append('factory');return {}

class Production(unittest.TestCase):
 def test_model_full_path_does_not_claim_physical_acceptance(self):
  a=Model();r=Lifecycle(a,lambda x:None,lambda:0).run();self.assertEqual(r['status'],'clock_completed');self.assertTrue(r['model_policy_only']);self.assertFalse(r['physical_execution_admitted']);self.assertEqual(a.calls,['admit','before','rom','load','observe','factory','after'])
 def test_known_failed_observation_still_recovers_without_retry(self):
  a=Model('failure');r=Lifecycle(a,lambda x:None,lambda:0).run();self.assertEqual(r['status'],'failed');self.assertTrue(r['original_flash_and_factory_verified']);self.assertEqual(a.calls.count('observe'),1)
 def test_unknown_owned_closure_prevents_further_device_access(self):
  a=Model('unknown');r=Lifecycle(a,lambda x:None,lambda:0).run();self.assertFalse(r['owned_processes_closed']);self.assertNotIn('factory',a.calls);self.assertNotIn('after',a.calls)
 def test_empty_registry_refuses_before_runtime_artifact_or_output(self):
  self.assertEqual(b.QUALIFIED,())
  with patch.object(c.runtime,'select',side_effect=AssertionError('must not query')),patch.object(c.backend,'artifact',side_effect=AssertionError('must not inspect')):
   with self.assertRaisesRegex(ValueError,'No committed'):c.prepare(types.SimpleNamespace())
 def test_registry_tuple_and_nonce_substitutions_refuse(self):
  temp,root,private,p=self.fixture()
  try:
   key=b.qualification_key(p)
   with patch.object(b,'QUALIFIED',(key,)):
    b.qualified(p)
    for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','qualification_sha256','execution_sha256','environment_sha256','contract_sha256'):
     with self.subTest(field=n),self.assertRaises(ValueError):b.qualified(dict(p,**{n:'3'*64}))
    for nonce in ('0'*32,'2'*31,None,False):
     with self.subTest(nonce=nonce),self.assertRaises(ValueError):b.qualified(dict(p,nonce=nonce))
  finally:temp.cleanup()
 def test_coherent_qualification_binds_board_artifact_map_and_runtime(self):
  temp,root,private,p=self.fixture()
  try:
   inputs={n:'1'*64 for n in b.EXECUTION_FILES};frozen={'inputs':inputs};environment={'fixture':'no hardware'}
   execution={n:h for n,h in inputs.items() if n!=b.REGISTRY};p.update(execution_sha256=b.digest(execution),environment_sha256=b.digest(environment),configuration={'fixed':True},artifact_exports={'fixture':'4'*64},startup_audit_sha256='5'*64)
   q=dict(p,kind='Forgix reversible clock measurement safety qualification',reviewed_execution_sha256=execution,environment=environment,admission_registry_binding='separately frozen committed registry')
   flags=('fpga_identity_assumptions_reviewed','pin_mapping_reviewed','electrical_safety_reviewed','reset_pin_ownership_reviewed','whole_loading_recovery_reviewed','startup_uid_reviewed')
   q.update({n:True for n in flags});path=root/'.scratch/qualification.json';p['qualification_path']=str(path)
   def check(value):
    path.write_text(json.dumps(value));os.chmod(path,0o600);p['qualification_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    with patch.object(b.trial,'ROOT',root),patch.object(b.trial,'check_inputs'):
     return b.qualification_receipt(p,environment,frozen)
   check(q)
   for n in ('uid_sha256','baseline_sha256','elf_sha256','configuration','artifact_exports','startup_audit_sha256',*flags):
    with self.subTest(field=n),self.assertRaises(ValueError):check(dict(q,**{n:False}))
   changed=dict(frozen,inputs=dict(inputs));changed['inputs']['tools/forgix_clock_backend.py']='9'*64
   with patch.object(b.trial,'check_inputs'),self.assertRaises(ValueError):b.qualification_receipt(p,environment,changed)
  finally:temp.cleanup()
 def test_typed_replay_status_and_cancelled_observation_do_not_qualify(self):
  model=Model();original=model.observe
  def boolean(d):r=original(d);r['replay']['observer_status']=False;return r
  model.observe=boolean;r=Lifecycle(model,lambda x:None,lambda:0).run();self.assertEqual(r['status'],'failed');self.assertTrue(r['original_flash_and_factory_verified'])
  model=Model()
  def cancelled(d):model.calls.append('observe');raise KeyboardInterrupt('fixture')
  model.observe=cancelled
  with self.assertRaises(KeyboardInterrupt):Lifecycle(model,lambda x:None,lambda:0).run()
  self.assertEqual(model.calls[-2:],['factory','after'])
 def test_complete_production_import_chain_is_frozen(self):
  script="import sys,json;from pathlib import Path;r=Path(sys.argv[1]);sys.path.insert(0,str(r/'tools'));import run_forgix_clock_trial;print(json.dumps([str(Path(m.__file__).resolve().relative_to(r)) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(r/'tools')]))"
  actual=set(json.loads(subprocess.check_output([sys.executable,'-c',script,str(ROOT)],text=True,timeout=20)));self.assertLessEqual(actual,b.EXECUTION_FILES)
 def fixture(self):
  temp=tempfile.TemporaryDirectory();root=Path(temp.name);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700);private=root/'backups/run';private.mkdir(mode=0o700)
  p={n:'1'*64 for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','qualification_sha256','execution_sha256','environment_sha256','contract_sha256')};p['nonce']='2'*32
  return temp,root,private,p
 def test_actual_dead_lease_owner_blocks_fresh_operator(self):
  temp,root,private,p=self.fixture()
  try:
   script="import sys,json,os,fcntl;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import run_forgix_clock_trial as c;import forgix_clock_backend as b;import forgix_usb_ram_trial as t;r=Path(sys.argv[2]);c.ROOT=b.ROOT=t.ROOT=r;p=json.loads(sys.argv[3]);fd=os.open(r/'.scratch/esp-demo.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX);c.SessionLease(p,r/'backups/run');os._exit(0)"
   subprocess.run([sys.executable,'-c',script,str(ROOT/'tools'),str(root),json.dumps(p)],check=True,timeout=15)
   self.assertTrue((root/b.LEASE).exists())
   with patch.object(c,'ROOT',root),patch.object(b,'ROOT',root),patch.object(c.trial,'ROOT',root):
    with self.assertRaises(ValueError):
     with c.operator_lock():self.fail('lease must block')
  finally:temp.cleanup()
 def finalize_fixture(self,mode):
  temp,root,private,p=self.fixture();clock=[0.0];fd=None
  try:
   with patch.object(c,'ROOT',root),patch.object(b,'ROOT',root),patch.object(c.trial,'ROOT',root):
    store=c.ReceiptStore(private);lease=c.SessionLease(p,private);fd=os.open(root/'.scratch/esp-demo.lock',os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(fd,fcntl.LOCK_EX);lock=c.LockHandle(fd)
    record={'status':'clock_episode_observed','original_flash_and_factory_verified':True,'owned_processes_closed':True}
    c.capture.save(store,'session.json',record);originalsync=c.capture.sync_directory;realfsync=os.fsync
    def sync(path):
     if mode=='release-error' and Path(path)==root/'.scratch' and not lease.path.exists():raise OSError('fixture release fsync')
     return originalsync(path)
    def fsync(number):
     if mode=='result-error' and os.readlink('/proc/self/fd/'+str(number)).endswith('/terminal-staged-session.json'):raise OSError('fixture terminal fsync')
     return realfsync(number)
    def printing(*a,**kw):
     if mode=='late-output':clock[0]=600.0
    with patch.object(c.capture,'sync_directory',side_effect=sync),patch.object(os,'fsync',side_effect=fsync),patch('builtins.print',side_effect=printing):
     c.finalize(lease,store,record,0,lock,lambda:clock[0])
     c.terminal_output(lease,store,record,0,{'requested':False},lambda:clock[0],lock=lock)
    saved=json.loads((private/'session.json').read_bytes());self.assertEqual(saved['status'],record['status'])
    self.assertFalse(lock.closed);self.assertTrue(lock.kernel_release);lock.check()
    if mode=='normal':
     self.assertEqual(saved['status'],'clock_episode_completed');self.assertEqual(saved['finalization_status'],'staged_kernel_exit');self.assertFalse(saved['invocation_qualification']);self.assertFalse(lease.path.exists());self.assertFalse(lease.pending_path.exists())
    else:self.assertEqual(saved['status'],'failed');self.assertTrue(lease.pending_path.exists());self.assertTrue(lease.path.exists())
  finally:
   if fd is not None:os.close(fd) # Explicit fixture teardown after held-FD assertions.
   temp.cleanup()
 def test_whole_deadline_includes_terminal_output(self):self.finalize_fixture('late-output')
 def test_actual_lease_release_fsync_failure_blocks_and_saves_failed(self):self.finalize_fixture('release-error')
 def test_terminal_file_fsync_failure_blocks_and_saves_failed(self):self.finalize_fixture('result-error')
 def test_successful_finalization_stages_kernel_release_and_clears_owned_markers(self):self.finalize_fixture('normal')
 def test_actual_worker_timeout_reaps_group_and_retains_lock(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t);workers=path/'workers';workers.mkdir(mode=0o700);lock=path/'lock';fd=os.open(lock,os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
   try:
    owner=WorkerOwner(workers,fd,lock)
    with self.assertRaises(Exception):owner.run([sys.executable,'-c','import time;time.sleep(10)'],'owned-timeout',__import__('time').monotonic()+.15)
    self.assertTrue(owner.closed);self.assertEqual(len(list(workers.glob('*.log'))),1);self.assertTrue(__import__('forgix_usb_ram_capture').inherited_operator_lock(fd,lock))
   finally:os.close(fd)

class MainBoundaries(unittest.TestCase):
 def exercise(self,mode):
  # The prior in-process callable observations did not prove actual CLI exit.
  # Keep the same fault controls but independently join a real child process.
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);began=__import__('time').monotonic()
   proc=subprocess.run([sys.executable,str(ROOT/'tests/test_forgix_clock_finalization.py'),'--fixture',str(root),mode],capture_output=True,text=True,timeout=15,start_new_session=True)
   self.assertLess(__import__('time').monotonic()-began,600)
   saved=json.loads((root/'backups/run/session.json').read_bytes())
   fd=os.open(root/'.scratch/esp-demo.lock',os.O_RDWR)
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   finally:os.close(fd)
   return {'mode':mode,'CLI':proc.returncode,'saved':saved['status'],'pending':(root/'.scratch/forgix-spi-finalization-pending.json').exists(),'lease':(root/b.LEASE).exists()}
 def test_actual_main_session_fsync_failure_cannot_leave_completed(self):
  o=self.exercise('session-fsync');self.assertEqual(o['CLI'],2);self.assertNotEqual(o['saved'],'clock_episode_completed')
 def test_actual_main_terminal_stdout_at_deadline_cannot_qualify(self):
  o=self.exercise('late-stdout');self.assertEqual(o['CLI'],2);self.assertNotEqual(o['saved'],'clock_episode_completed')
 def test_actual_main_cleanup_cancellation_cannot_qualify(self):
  o=self.exercise('cleanup-cancel');self.assertEqual(o['CLI'],2);self.assertNotEqual(o['saved'],'clock_episode_completed')
 def test_normal_actual_main_still_completes(self):
  o=self.exercise('normal');self.assertEqual(o['CLI'],0);self.assertEqual(o['saved'],'clock_episode_completed');self.assertFalse(o['pending']);self.assertFalse(o['lease'])
 def test_terminal_stdout_failure_retains_blocker_and_failed_receipt(self):
  o=self.exercise('stdout-error');self.assertEqual(o['CLI'],2);self.assertEqual(o['saved'],'failed');self.assertTrue(o['pending']);self.assertTrue(o['lease'])

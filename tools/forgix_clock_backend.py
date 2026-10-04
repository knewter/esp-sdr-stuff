#!/usr/bin/env python3
"""Distinct PID4014 preserved observer backend; empty registry blocks access."""
import argparse,hashlib,json,os,re,struct,sys,time,zlib
from pathlib import Path
import forgix_spi_backend as common
import forgix_synthetic_backend as primitives
import forgix_synthetic_runtime as runtime
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve
import forgix_clock_collect as collector
from forgix_clock_artifact import inspect_elf
from build_forgix_clock_observer import FILES
from audit_forgix_clock_startup import audit
from forgix_clock_qualifications import QUALIFIED
from forgix_usb_ram_capture import inherited_operator_lock,open_retaining_serial
from demo_esp_sdr import OwnedHardwareClosureError
ROOT=Path(__file__).resolve().parents[1]
REGISTRY='tools/forgix_clock_qualifications.py'
PROTOCOL='docs/research/forgix-clock-observer-protocol.md'
LEASE='.scratch/forgix-spi-active.json'
EXECUTION_FILES=frozenset(primitives.EXECUTION_FILES|set(FILES)|{REGISTRY,PROTOCOL,
 'tools/forgix_clock_backend.py','tools/forgix_clock_collect.py','tools/forgix_clock_wire.py',
 'tools/forgix_clock_lifecycle.py','tools/run_forgix_clock_trial.py','tools/audit_forgix_clock_startup.py'})
require=common.require
digest=primitives.digest
CONTRACT='firmware/forgix-clock-observer/PROTOCOL.md'

def artifact(folder):
 folder=trial.no_symlinks(folder);require(folder.is_relative_to(ROOT/'.scratch'),'Private observer artifact required')
 manifest=trial.private_file(folder/'manifest.json','.scratch');elf=trial.private_file(folder/'forgix_clock_observer.elf','.scratch')
 reviewed=audit(folder);m=json.loads(manifest.read_bytes());data=elf.read_bytes();layout=inspect_elf(data)
 def loaded(name,length):
  address=layout['symbols'][name];r=next(r for r in layout['load_segments'] if r['vaddr']<=address and address+length<=r['vaddr']+r['filesz']);off=r['offset']+address-r['vaddr'];return data[off:off+length]
 image=m['configuration'];count=struct.unpack('<I',loaded('bridge_fpga_image_bytes',4))[0];payload=loaded('bridge_fpga_image',count)
 require(count==image['decoded_bytes'] and hashlib.sha256(payload).hexdigest()==image['decoded_sha256'] and loaded('bridge_fpga_sha256',32)==bytes.fromhex(image['decoded_sha256']) and zlib.crc32(payload)==image['decoded_crc32']==struct.unpack('<I',loaded('bridge_fpga_crc32',4))[0],'Embedded observer identity differs')
 identity=hashlib.sha256(json.dumps({'sources':m['source_sha256'],'configuration':image},sort_keys=True).encode()).hexdigest()
 require(identity==m['build_source_sha256'] and any(bytes.fromhex(identity) in data[r['offset']:r['offset']+r['filesz']] for r in layout['load_segments']),'Compiled observer build identity differs')
 for n,h in m['source_sha256'].items():
  if n.startswith('firmware/') or n in ('tools/forgix_clock_artifact.py','tools/forgix_clock_image.py'):
   require(trial.sha(ROOT/n)==h,'Current observer firmware/image guard differs')
 return {'elf':str(elf),'elf_sha256':trial.sha(elf),'manifest_sha256':trial.sha(manifest),
  'source_commit':m['source_commit'],'bridge_source_sha256':identity,'bitstream_sha256':image['decoded_sha256'],
  'configuration':image,'artifact_exports':m['artifact_sha256'],'layout_bytes':layout['allocated_load_bytes'],
  'startup_audit_sha256':digest(reviewed),'contract_sha256':trial.sha(ROOT/CONTRACT)}

def frozen_inputs(frozen):
 require(type(frozen.get('inputs')) is dict and set(frozen['inputs'])==EXECUTION_FILES,'Exact observer execution map required');trial.check_inputs(frozen)

def qualification_key(p):
 require(type(p.get('nonce')) is str and re.fullmatch('[0-9a-f]{32}',p['nonce']) and int(p['nonce'],16)!=0,'Fresh nonzero observer nonce required')
 values=tuple(p.get(n) for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','contract_sha256','qualification_sha256','execution_sha256','environment_sha256'))
 require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in values),'Complete measurement safety tuple required');return values

def qualified(p):require(qualification_key(p) in QUALIFIED,'No committed safety qualification admits clock measurement')

def lease_binding(p):return digest({n:p.get(n) for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','qualification_sha256','execution_sha256','environment_sha256','contract_sha256','nonce')})

def session_lease(p,private=None):
 path=trial.private_file(ROOT/LEASE,'.scratch');require(trial.sha(path)==p.get('session_lease_sha256'),'Observer lease changed');record=json.loads(path.read_bytes())
 require(record.get('uid_sha256')==p['uid_sha256'] and record.get('private_dir')==p['session_private_dir'] and record.get('run_binding_sha256')==lease_binding(p) and (private is None or record['private_dir']==str(private)),'Observer lease owner differs');return path

def qualification_receipt(p,environment,frozen):
 frozen_inputs(frozen);execution={n:h for n,h in frozen['inputs'].items() if n!=REGISTRY}
 require(digest(execution)==p['execution_sha256'] and digest(environment)==p['environment_sha256'],'Clock execution/environment tuple differs')
 path=trial.private_file(p['qualification_path'],'.scratch');require(0<path.stat().st_size<=1024**2 and trial.sha(path)==p['qualification_sha256'],'Safety receipt differs');q=json.loads(path.read_bytes())
 require(q.get('kind')=='Forgix reversible clock measurement safety qualification' and q.get('reviewed_execution_sha256')==execution and q.get('environment')==environment and q.get('admission_registry_binding')=='separately frozen committed registry','Complete independently reviewed clock tuple required')
 for n in ('fpga_identity_assumptions_reviewed','pin_mapping_reviewed','electrical_safety_reviewed','reset_pin_ownership_reviewed','whole_loading_recovery_reviewed','startup_uid_reviewed'):
  require(q.get(n) is True,'Measurement safety qualification missing: '+n)
 for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','contract_sha256','configuration','artifact_exports','startup_audit_sha256'):
  require(type(q.get(n)) is type(p[n]) and q[n]==p[n],'Measurement safety binding differs: '+n)
 return q

class ClockPicotool(trial.OwnedPicotool):
 def __init__(self,*a,profile,environment,**kw):super().__init__(*a,**kw);self.profile=profile;self.environment=environment
 def run(self,*a,**kw):runtime.check(self.environment);return super().run(*a,**kw)
 def load_args(self,target,backup,path):
  require(target.pid==preserve.BOOT_PID and Path(path)==Path('/private/ram-clock-observer.elf'),'Exact ROM/observer load required')
  require(trial.sha(backup)==self.profile['elf_sha256'],'Staged observer ELF differs');inspect_elf(Path(backup).read_bytes())
  return ['load','-v','-x',str(path),'-t','elf','--bus',str(target.bus),'--address',str(target.address)]

class Backend(common.Backend):
 def check_inputs(self):
  trial.reject_pending_finalization(ROOT);require(self.owner.closed,'Unknown owned closure blocks access');inherited_operator_lock(self.lockfd,self.lockpath)
  require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(),'Shared unknown closure blocks access')
  session_lease(self.profile,getattr(self,'lease_private',self.private));frozen_inputs(self.frozen);qualification_receipt(self.profile,self.environment,self.frozen)
  runtime.check(self.environment)
  sdk=Path('/nix/store/zzdqq5jiwbislr6v99spq09vmc9yiib1-pico-sdk-2.2.0-tinyusb-pinned')
  require(all(trial.sha(sdk/n)==h for n,h in self.environment['sdk_file_sha256'].items()),'SDK critical bytes changed')
  original=trial.original_binding(self.profile['binding_path'],*self.profile['baseline_paths'])
  require(all(self.profile[n]==v for n,v in original.items()),'Original UID/baseline binding changed')
  require(trial.sha(self.profile['elf'])==self.profile['elf_sha256'] and trial.sha(Path(self.profile['elf']).parent/'manifest.json')==self.profile['manifest_sha256'],'Observer artifact changed')
  require(all(trial.sha(Path(self.profile['elf']).parent/n)==h for n,h in self.profile['artifact_exports'].items()),'Observer export changed')
 def hardware_gate(self,until):
  require(self.admitted,'Unadmitted observer');qualified(self.profile);self.check_inputs();require(self.clock()<until,'Observer stage deadline expired')
 def admit(self,until):
  require(not self.used,'One observer session');self.used=True;qualified(self.profile);self.check_inputs()
  require(self.environment.get('closure_contents_verified') is True and self.environment.get('sdk_nar_verified') is True,'Content-verified runtime required')
  current=artifact(Path(self.profile['elf']).parent);require(all(self.profile[n]==v for n,v in current.items()),'Observer artifact tuple differs')
  require(self.clock()<until,'Admission expired');self.bus=self.inspector.target(preserve.FACTORY_PID).bus;require(self.clock()<until,'Identity selection late');self.admitted=True
  return dict(self.profile,qualification_verified=True)
 def preservation(self,name,until):
  self.hardware_gate(until);self.inspector.deadline=until;store=preserve.PrivateStore(self.private/name,ROOT/'backups')
  runner=ClockPicotool(self.environment['picotool_executable'],self.inspector,store,self.environment['image_id'],self.frozen,until,profile=self.profile,environment=self.environment);self.owner.runners.append(runner)
  def query(i,t,s,label):
   self.hardware_gate(until);runtime.check(self.environment)
   return trial.bounded_query(i,t,s,label,self.lockfd,until,runner)
  try:receipt,error=preserve.preserve(self.inspector,runner,store,trial.FLASH_BYTES,query=query)
  except BaseException as exc:
   if not runner.hardware_process_closed:self.owner.unknown=True;raise OwnedHardwareClosureError('Observer preservation closure unverified') from exc
   raise
  if not runner.hardware_process_closed:self.owner.unknown=True;raise OwnedHardwareClosureError('Observer preservation closure unverified')
  if error:raise error
  copies=receipt['backups'];require(copies['sha256']==self.profile['baseline_sha256']==trial.BASELINE and copies['bytes_per_read']==trial.FLASH_BYTES and copies['reads']==2 and copies['matching'] is True and receipt['independent_device_verify'] is True and receipt['status']=='preserved_and_returned','Original complete flash/factory proof differs');require(self.clock()<until,'Preservation late')
  return {'uid_sha256':self.profile['uid_sha256'],'flash_bytes':copies['bytes_per_read'],'read_sha256':[copies['sha256']]*2,'independent_device_verify':True,'factory_application_verified':True}
 def enter_rom(self,until):
  self.hardware_gate(until);self.inspector.deadline=until;store=preserve.PrivateStore(self.private/'load',ROOT/'backups')
  self.loader=ClockPicotool(self.environment['picotool_executable'],self.inspector,store,self.environment['image_id'],self.frozen,until,profile=self.profile,environment=self.environment);self.owner.runners.append(self.loader)
  store.create('ram-clock-observer.elf',Path(self.profile['elf']).read_bytes());self.loader.run('boot',self.inspector.target(preserve.FACTORY_PID,self.bus));self.inspector.wait(preserve.BOOT_PID,self.bus);require(self.clock()<until,'ROM selection late');return {'rom_selected':True}
 def load_ram(self,until):
  self.hardware_gate(until);self.inspector.deadline=self.loader.deadline=until;self.boot_host_ns=time.monotonic_ns()
  self.loader.run('load',self.inspector.target(preserve.BOOT_PID,self.bus),self.loader.store.path/'ram-clock-observer.elf');require(self.clock()<until,'Load late')
  return {'elf_sha256':self.profile['elf_sha256'],'boot_host_ns':self.boot_host_ns}
 def observe(self,until):
  self.hardware_gate(until);require(time.monotonic_ns()<self.boot_host_ns+30_000_000_000,'Observation command clock exhausted')
  request={'profile':self.profile,'environment':self.environment,'frozen':self.frozen,'lockfd':self.lockfd,'lockpath':str(self.lockpath),'bus':self.bus,'until':until,'boot_host_ns':self.boot_host_ns}
  store=preserve.PrivateStore(self.private/'observation',ROOT/'backups');path=store.json('request.json',request);runtime.check(self.environment)
  self.workers.run([self.environment['python_executable'],str(ROOT/'tools/forgix_clock_backend.py'),'_serial-worker','--request',str(path)],'clock-observation',until)
  r=json.loads((store.path/'capture/result.json').read_bytes());require(r.get('status')=='digital_ratio_observed' and r.get('transport_closed') is True and r.get('persistence_verified') is True,'Observation failed; prefix retained')
  request['action']='replay';replay_path=store.json('replay-request.json',request);runtime.check(self.environment)
  self.workers.run([self.environment['python_executable'],str(ROOT/'tools/forgix_clock_backend.py'),'_serial-worker','--request',str(replay_path)],'clock-saved-replay',until)
  replay=json.loads((store.path/'replay.json').read_bytes());require(replay==r['validation'] and replay.get('observer_status')==0,'Independent full raw replay differs')
  return {'status':'digital_ratio_observed','transport_closed':True,'persistence_verified':True,'replay':replay,'nonce':self.profile['nonce'],'build_sha256':self.profile['bridge_source_sha256'],'image_sha256':self.profile['bitstream_sha256']}
 def return_factory(self,until):
  self.hardware_gate(until);self.inspector.deadline=until
  if self.loader is None:
   store=preserve.PrivateStore(self.private/'factory-return',ROOT/'backups');self.loader=ClockPicotool(self.environment['picotool_executable'],self.inspector,store,self.environment['image_id'],self.frozen,until,profile=self.profile,environment=self.environment);self.owner.runners.append(self.loader)
  self.loader.deadline=until;factory=trial.watched_factory(self.inspector,self.bus,until,self.loader);runtime.check(self.environment)
  trial.bounded_query(self.inspector,factory,self.loader.store,'returned-after-ram',self.lockfd,until,self.loader);require(self.clock()<until,'Factory query late');return {'factory_application_verified':True}
 def configure(self,until):raise ValueError('Only observation worker configures the clock image')
 transition=configure
 collect=configure

class RecoveryBackend(Backend):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.lease_private=Path(self.profile['session_private_dir'])
 def admit(self,until):
  require(not self.used,'One observer recovery');self.used=True;qualified(self.profile);self.check_inputs();require(self.clock()<until,'Recovery admission late')
  usb=Path('/sys/bus/usb/devices/3-3').resolve(strict=True);serial=(usb/'serial').read_text().strip().casefold()
  require(re.fullmatch('[0-9a-f]{16}',serial) and hashlib.sha256(serial.encode()).hexdigest()==self.profile['uid_sha256'],'Recovery UID differs')
  mode=((usb/'idVendor').read_text().strip().lower(),(usb/'idProduct').read_text().strip().lower());require(mode in (('2e8a',preserve.FACTORY_PID),('2e8a',preserve.BOOT_PID),('cafe','4014')),'Recovery mode differs')
  self.bus=int((usb/'busnum').read_text());require(self.clock()<until,'Recovery identity late');self.admitted=True;return dict(self.profile,qualification_verified=True)
 def enter_rom(self,until):raise ValueError('Recovery never reloads or starts an observation')
 load_ram=enter_rom
 observe=enter_rom

def select_clock(p,bus,ready=False,sys_root=Path('/sys'),dev_root=Path('/dev')):
 trial.reject_pending_finalization(ROOT);usb=(sys_root/'bus/usb/devices/3-3').resolve(strict=True);read=lambda n:(usb/n).read_text().strip();serial=read('serial').casefold()
 require(re.fullmatch('[0-9a-f]{16}',serial) and hashlib.sha256(serial.encode()).hexdigest()==p['uid_sha256'] and int(read('busnum'))==bus,'Original observer UID/bus differs');mode=(read('idVendor').lower(),read('idProduct').lower())
 if ready and mode in (('2e8a',preserve.FACTORY_PID),('2e8a',preserve.BOOT_PID)):raise FileNotFoundError('Original not in observer mode')
 require(mode==('cafe','4014') and read('product')=='Forgix Clock RAM observer v1','Distinct PID4014 required')
 port=trial.fresh_tty('3-3','cafe','4014','Forgix Clock RAM observer v1',sys_root,dev_root,wait_missing=ready)
 return {'port':port,'usb_node':str(usb),'bus':read('busnum'),'enumeration':read('devnum'),'uid_sha256':p['uid_sha256'],'vid':'cafe','pid':'4014'}

def serial_worker(path):
 trial.reject_pending_finalization(ROOT);path=trial.private_file(path,'backups');r=json.loads(path.read_bytes());p=r['profile']
 qualified(p);session_lease(p);frozen_inputs(r['frozen']);qualification_receipt(p,r['environment'],r['frozen']);runtime.check(r['environment'])
 require(str(Path(sys.executable).resolve())==r['environment']['python_executable'] and trial.sha(sys.executable)==r['environment']['python_executable_sha256'],'Worker interpreter differs')
 require(r['lockpath']==str(ROOT/'.scratch/esp-demo.lock'),'Shared lock required');inherited_operator_lock(r['lockfd'],r['lockpath'])
 require(path.parent.parent==Path(p['session_private_dir']),'Worker request outside lease');original=trial.original_binding(p['binding_path'],*p['baseline_paths']);require(all(p[n]==v for n,v in original.items()),'Worker original binding differs')
 def admission():
  trial.reject_pending_finalization(ROOT);qualified(p);session_lease(p);frozen_inputs(r['frozen']);qualification_receipt(p,r['environment'],r['frozen']);runtime.check(r['environment'],verify_bytes=False);require(time.monotonic()<r['until'],'Worker deadline expired')
  require(trial.sha(p['elf'])==p['elf_sha256'] and trial.sha(Path(p['elf']).parent/'manifest.json')==p['manifest_sha256'],'Worker artifact changed')
  return {'clock_measurement_qualified':True,'lifecycle_admitted':True,'build_sha256':p['bridge_source_sha256'],'image_sha256':p['bitstream_sha256']}
 if r.get('action')=='replay':
  admission();saved=collector.replay(path.parent/'capture',bytes.fromhex(p['nonce']),bytes.fromhex(p['bridge_source_sha256']),bytes.fromhex(p['bitstream_sha256']))
  with os.fdopen(os.open(path.parent/'replay.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600),'wb') as out:capture.durable(out,(json.dumps(saved,sort_keys=True)+'\n').encode())
  capture.sync_directory(path.parent);admission();return
 require(r.get('action') is None,'Unknown clock worker action');cutoff=min(r['until'],r['boot_host_ns']/1e9+30)
 common.ready_bridge(lambda:select_clock(p,r['bus'],ready=True),cutoff)
 def select():admission();return select_clock(p,r['bus'])
 def opened(identity,until):
  admission();serial=open_retaining_serial(identity['port'])
  try:return primitives.SyntheticTransport(serial)
  except BaseException:serial.close();raise
 try:
  result=collector.collect(path.parent/'capture',bytes.fromhex(p['nonce']),bytes.fromhex(p['bridge_source_sha256']),bytes.fromhex(p['bitstream_sha256']),opened,admission,select,r['lockfd'],r['lockpath'],r['boot_host_ns']);require(result['status']=='digital_ratio_observed','Observation did not complete');admission()
 finally:require(time.monotonic()<r['until'],'Worker terminal clock expired')

if __name__=='__main__':
 os.umask(0o077);p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('_serial-worker',));p.add_argument('--request',type=Path,required=True);serial_worker(p.parse_args().request)

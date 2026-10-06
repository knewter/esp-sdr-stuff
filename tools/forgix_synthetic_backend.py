#!/usr/bin/env python3
"""Distinct synthetic stream backend. The empty registry forbids device access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import time
import struct
import zlib

import forgix_spi_backend as common
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve
import forgix_synthetic_collect as collector
import forgix_synthetic_runtime as runtime
from forgix_synthetic_stream import Binding, CONTRACT_SHA256
from forgix_synthetic_codec import PROFILES
from forgix_synthetic_qualifications import QUALIFIED
from build_forgix_synthetic_stream import FILES
from audit_forgix_synthetic_startup import audit
from forgix_usb_ram_artifact import inspect_elf
from forgix_usb_ram_capture import inherited_operator_lock, open_retaining_serial
from demo_esp_sdr import OwnedHardwareClosureError

ROOT=Path(__file__).resolve().parents[1]
REGISTRY='tools/forgix_synthetic_qualifications.py'
PROTOCOL='docs/research/forgix-synthetic-lifecycle.md'
LEASE='.scratch/forgix-spi-active.json' # Shared lease blocks register and stream routes alike.
EXECUTION_FILES=frozenset(common.EXECUTION_FILES | set(FILES) | {REGISTRY,PROTOCOL,
 'tools/forgix_synthetic_backend.py','tools/forgix_synthetic_lifecycle.py',
 'tools/run_forgix_synthetic_trial.py','tools/forgix_synthetic_collect.py',
 'tools/forgix_synthetic_stream.py','tools/forgix_synthetic_codec.py',
 'tools/audit_forgix_synthetic_startup.py','tools/build_forgix_usb_ram.py',
 'tools/forgix_toolchain_check.py','tools/forgix_fpga_candidate.py',
 'tools/forgix_synthetic_runtime.py'})
require=common.require

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def artifact(folder):
    folder=trial.no_symlinks(folder)
    require(folder.is_relative_to(ROOT/'.scratch'),'Private synthetic artifact required')
    manifest=trial.private_file(folder/'manifest.json','.scratch')
    elf=trial.private_file(folder/'forgix_synthetic_stream.elf','.scratch')
    reviewed=audit(folder);m=json.loads(manifest.read_bytes())
    require(type(m.get('rp_pause')) is bool,'Build pause policy required')
    layout=inspect_elf(elf.read_bytes(),application='synthetic-stream')
    data=elf.read_bytes()
    def loaded(name,size):
        address=layout['symbols'][name]
        p=next(p for p in layout['load_segments'] if p['vaddr']<=address and address+size<=p['vaddr']+p['filesz'])
        offset=p['offset']+address-p['vaddr'];return data[offset:offset+size]
    image=m['configuration']
    require(0<image['decoded_bytes']<=196608 and hashlib.sha256(loaded('bridge_fpga_image',image['decoded_bytes'])).hexdigest()==image['decoded_sha256']
            and loaded('bridge_fpga_sha256',32)==bytes.fromhex(image['decoded_sha256']),'Linked stream image differs')
    require(struct.unpack('<I',loaded('bridge_fpga_image_bytes',4))[0]==image['decoded_bytes']
            and struct.unpack('<I',loaded('bridge_fpga_crc32',4))[0]==image['decoded_crc32']
            and zlib.crc32(loaded('bridge_fpga_image',image['decoded_bytes']))==image['decoded_crc32'],
            'Linked image length/CRC differs')
    identity=hashlib.sha256(json.dumps({'sources':m['source_sha256'],'configuration':image,
                                      'rp_pause':m['rp_pause']},sort_keys=True).encode()).hexdigest()
    require(identity==m['build_source_sha256'] and any(bytes.fromhex(identity) in data[p['offset']:p['offset']+p['filesz']]
            for p in layout['load_segments']),'Compiled build identity differs')
    # Historical committed bytes are verified by audit; current firmware/guard
    # must still match. Task/docs may advance independently of that old build.
    for name,h in m['source_sha256'].items():
        if name.startswith('firmware/') or name in ('tools/forgix_usb_ram_artifact.py','tools/forgix_synthetic_image.py'):
            require(trial.sha(ROOT/name)==h,'Current stream firmware/guard differs')
    return {'elf':str(elf),'elf_sha256':trial.sha(elf),'manifest_sha256':trial.sha(manifest),
            'source_commit':m['source_commit'],'bridge_source_sha256':m['build_source_sha256'],
            'bitstream_sha256':image['decoded_sha256'],'configuration':image,
            'artifact_exports':m['artifact_sha256'],'rp_pause':m['rp_pause'],
            'layout_bytes':layout['allocated_load_bytes'],'startup_audit_sha256':digest(reviewed)}

def frozen_inputs(frozen):
    require(set(frozen['inputs'])==EXECUTION_FILES,'Exact full synthetic execution set required')
    trial.check_inputs(frozen)

def qualification_key(p):
    names=('elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256',
           'qualification_sha256','execution_sha256','environment_sha256')
    values=tuple(p.get(n) for n in names)
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in values),'Complete synthetic tuple required')
    require(type(p.get('period')) is int and PROFILES.get(p['period'])==p.get('target') and type(p['target']) is int,
            'Fixed synthetic profile required')
    require(type(p.get('rp_pause')) is bool and type(p.get('host_pause')) is bool,'Exact pause policies required')
    return values+(p['period'],p['target'],p['rp_pause'],p['host_pause'])

def qualified(profile):
    require(qualification_key(profile) in QUALIFIED,'No committed physical qualification admits synthetic streaming')

def lease_binding(profile):
    return digest({n:profile.get(n) for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256',
        'bridge_source_sha256','bitstream_sha256','qualification_sha256','execution_sha256','environment_sha256',
        'nonce','period','target','rp_pause','host_pause')})

def session_lease(profile,private=None):
    path=trial.private_file(ROOT/LEASE,'.scratch')
    require(trial.sha(path)==profile.get('session_lease_sha256'),'Synthetic session lease changed')
    record=json.loads(path.read_bytes())
    require(record.get('uid_sha256')==profile['uid_sha256'] and record.get('private_dir')==profile.get('session_private_dir')
            and record.get('run_binding_sha256')==lease_binding(profile)
            and (private is None or record['private_dir']==str(private)),'Synthetic lease owner differs')
    return path

def binding(p):
    return Binding(bytes.fromhex(p['nonce']),p['period'],p['target'],
                   bytes.fromhex(p['bridge_source_sha256']),bytes.fromhex(p['bitstream_sha256']),p['rp_pause'])

def qualification_receipt(p,environment,frozen):
    frozen_inputs(frozen)
    execution={n:h for n,h in frozen['inputs'].items() if n!=REGISTRY}
    require(digest(execution)==p['execution_sha256'] and digest(environment)==p['environment_sha256'],
            'Reviewed execution/runtime tuple differs')
    path=trial.private_file(p['qualification_path'],'.scratch')
    require(0<path.stat().st_size<=1024*1024 and trial.sha(path)==p['qualification_sha256'],'Qualification receipt differs')
    q=json.loads(path.read_bytes())
    require(q.get('kind')=='Forgix physical synthetic stream episode qualification'
            and q.get('contract_sha256')==CONTRACT_SHA256 and digest(q.get('environment'))==digest(environment)
            and q.get('reviewed_execution_sha256')==execution
            and q.get('admission_registry_binding')=='separately frozen committed registry',
            'Complete independently reviewed execution/environment required')
    for name in ('fpga_grade_verified','clock_verified','spi_handoff_verified',
                 'whole_loading_recovery_reviewed','startup_uid_reviewed'):
        require(q.get(name) is True,'Physical/review qualification missing: '+name)
    for name in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256',
                 'bitstream_sha256','configuration','artifact_exports','startup_audit_sha256',
                 'period','target','rp_pause','host_pause'):
        require(type(q.get(name)) is type(p[name]) and q[name]==p[name],'Qualified profile differs: '+name)
    return q

class SyntheticPicotool(trial.OwnedPicotool):
    def __init__(self,*args,profile,environment,**kwargs):
        super().__init__(*args,**kwargs);self.profile=profile;self.environment=environment
    def run(self,*args,**kwargs):
        runtime.check(self.environment)
        return super().run(*args,**kwargs)
    def load_args(self,target,backup,path):
        require(target.pid==preserve.BOOT_PID and Path(path)==Path('/private/ram-synthetic-stream.elf'),'Exact ROM/synthetic load required')
        require(trial.sha(backup)==self.profile['elf_sha256'],'Staged synthetic ELF differs')
        inspect_elf(Path(backup).read_bytes(),application='synthetic-stream')
        return ['load','-v','-x',str(path),'-t','elf','--bus',str(target.bus),'--address',str(target.address)]

class Backend(common.Backend):
    """Reuse preservation/return primitives only, never RegisterRun/FGSC."""
    def check_inputs(self):
        require(self.owner.closed,'Unknown owned closure blocks access')
        inherited_operator_lock(self.lockfd,self.lockpath)
        require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(),'Shared unknown-closure marker blocks access')
        session_lease(self.profile,getattr(self,'lease_private',self.private));frozen_inputs(self.frozen)
        qualification_receipt(self.profile,self.environment,self.frozen)
        require(digest(self.environment)==self.profile['environment_sha256'],'Runtime tuple differs')
        runtime.check(self.environment)
        for name in ('python_executable','picotool_executable'):
            require(trial.sha(self.environment[name])==self.environment[name+'_sha256'],'Frozen executable differs')
        sdk=Path('/nix/store/zzdqq5jiwbislr6v99spq09vmc9yiib1-pico-sdk-2.2.0-tinyusb-pinned')
        require(all(trial.sha(sdk/n)==h for n,h in self.environment['sdk_file_sha256'].items()),'Runtime SDK files differ')
        require(trial.sha(self.profile['elf'])==self.profile['elf_sha256'] and
                trial.sha(Path(self.profile['elf']).parent/'manifest.json')==self.profile['manifest_sha256'],'Frozen artifact differs')
        require(all(trial.sha(Path(self.profile['elf']).parent/n)==h for n,h in self.profile['artifact_exports'].items()),'Artifact export differs')
        bound=trial.original_binding(self.profile['binding_path'],*self.profile['baseline_paths'])
        require(all(self.profile[k]==v for k,v in bound.items()),'Original binding differs')
        require(trial.sha(trial.private_file(self.profile['qualification_path'],'.scratch'))==self.profile['qualification_sha256'],'Qualification differs')
    def preservation(self,name,until):
        self.hardware_gate(until);self.inspector.deadline=until
        store=preserve.PrivateStore(self.private/name,ROOT/'backups')
        runner=SyntheticPicotool(self.environment['picotool_executable'],self.inspector,store,
                    self.environment['image_id'],self.frozen,until,profile=self.profile,environment=self.environment)
        self.owner.runners.append(runner) # Retain cleanup ownership even on storage failure.
        def query(i,t,s,label):
            runtime.check(self.environment)
            return trial.bounded_query(i,t,s,label,self.lockfd,until,runner)
        try:
            receipt,error=preserve.preserve(self.inspector,runner,store,trial.FLASH_BYTES,query=query)
        except BaseException as exc:
            if not runner.hardware_process_closed:
                self.owner.unknown=True
                raise OwnedHardwareClosureError('Synthetic preservation closure unverified') from exc
            raise
        if not runner.hardware_process_closed:
            self.owner.unknown=True
            raise OwnedHardwareClosureError('Synthetic preservation closure unverified')
        if error:raise error
        copies=receipt['backups']
        require(copies['sha256']==self.profile['baseline_sha256']==trial.BASELINE and
                copies['bytes_per_read']==trial.FLASH_BYTES and copies['reads']==2 and copies['matching'] is True
                and receipt['independent_device_verify'] is True and receipt['status']=='preserved_and_returned',
                'Fresh original flash/factory proof differs')
        require(self.clock()<until,'Preservation deadline expired')
        return {'uid_sha256':self.profile['uid_sha256'],'flash_bytes':copies['bytes_per_read'],
                'read_sha256':[copies['sha256']]*2,'independent_device_verify':True,'factory_application_verified':True}
    def hardware_gate(self,until):
        require(self.admitted,'Unadmitted synthetic backend');qualified(self.profile);self.check_inputs()
        require(self.clock()<until,'Synthetic stage deadline expired')
    def admit(self,until):
        require(not self.used,'One synthetic backend session');self.used=True
        qualified(self.profile);self.check_inputs()
        require(self.environment.get('closure_contents_verified') is True and self.environment.get('sdk_nar_verified') is True,'Verified Nix runtime required')
        current=artifact(Path(self.profile['elf']).parent)
        require(all(self.profile[k]==v for k,v in current.items()),'Synthetic artifact tuple differs')
        require(self.clock()<until,'Admission expired')
        self.bus=self.inspector.target(preserve.FACTORY_PID).bus;self.admitted=True
        return dict(self.profile,qualification_verified=True)
    def enter_rom(self,until):
        self.hardware_gate(until);self.inspector.deadline=until
        store=preserve.PrivateStore(self.private/'load',ROOT/'backups')
        self.loader=SyntheticPicotool(self.environment['picotool_executable'],self.inspector,store,
                    self.environment['image_id'],self.frozen,until,profile=self.profile,environment=self.environment)
        self.owner.runners.append(self.loader)
        store.create('ram-synthetic-stream.elf',Path(self.profile['elf']).read_bytes())
        self.loader.run('boot',self.inspector.target(preserve.FACTORY_PID,self.bus))
        self.inspector.wait(preserve.BOOT_PID,self.bus)
        return {'rom_selected':True}
    def load_ram(self,until):
        self.hardware_gate(until);self.inspector.deadline=self.loader.deadline=until
        self.boot_host_ns=time.monotonic_ns() # conservative: precedes potentially executing load
        self.loader.run('load',self.inspector.target(preserve.BOOT_PID,self.bus),self.loader.store.path/'ram-synthetic-stream.elf')
        return {'elf_sha256':self.profile['elf_sha256'],'boot_host_ns':self.boot_host_ns}
    def stream(self,until):
        self.hardware_gate(until)
        require(time.monotonic_ns()<self.boot_host_ns+30_000_000_000,'Load/start budget exhausted')
        request={'profile':self.profile,'environment':self.environment,'frozen':self.frozen,'lockfd':self.lockfd,
                 'lockpath':str(self.lockpath),'bus':self.bus,'until':until,'boot_host_ns':self.boot_host_ns}
        store=preserve.PrivateStore(self.private/'stream',ROOT/'backups');path=store.json('request.json',request)
        runtime.check(self.environment)
        self.workers.run([self.environment['python_executable'],str(ROOT/'tools/forgix_synthetic_backend.py'),
                          '_serial-worker','--request',str(path)],'synthetic-stream',until)
        result=json.loads((store.path/'capture/result.json').read_bytes())
        # Full saved-byte replay can block on storage too: independently contain
        # that call, without opening serial or issuing another command.
        request['action']='replay'
        replay_path=store.json('replay-request.json',request)
        runtime.check(self.environment)
        self.workers.run([self.environment['python_executable'],str(ROOT/'tools/forgix_synthetic_backend.py'),
                          '_serial-worker','--request',str(replay_path)],'saved-replay',until)
        replay=json.loads((store.path/'replay.json').read_bytes())
        require(result.get('status')=='lossless' and result.get('transport_closed') is True
                and result.get('persistence_verified') is True and replay['lossless'] is True,'Stream failed; prefix/forensics retained')
        return {'status':'lossless','replay':replay,'transport_closed':True,'persistence_verified':True,
                'build_sha256':self.profile['bridge_source_sha256'],'image_sha256':self.profile['bitstream_sha256'],
                'nonce':self.profile['nonce'],'period':self.profile['period'],'target':self.profile['target']}
    def return_factory(self,until):
        self.hardware_gate(until);self.inspector.deadline=until
        if self.loader is None:
            store=preserve.PrivateStore(self.private/'factory-return',ROOT/'backups')
            self.loader=SyntheticPicotool(self.environment['picotool_executable'],self.inspector,store,
                         self.environment['image_id'],self.frozen,until,profile=self.profile,environment=self.environment)
            self.owner.runners.append(self.loader)
        self.loader.deadline=until
        factory=trial.watched_factory(self.inspector,self.bus,until,self.loader)
        runtime.check(self.environment)
        trial.bounded_query(self.inspector,factory,self.loader.store,'returned-after-ram',self.lockfd,until,self.loader)
        return {'factory_application_verified':True}
    def configure(self,until):raise ValueError('Synthetic configuration belongs exclusively to stream worker')
    transition=configure
    collect=configure

class RecoveryBackend(Backend):
    """Same qualified original tuple; no ROM entry/load or stream command."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.lease_private=Path(self.profile['session_private_dir'])
    def admit(self,until):
        require(not self.used,'One recovery');self.used=True
        qualified(self.profile);self.check_inputs()
        require(self.clock()<until,'Recovery admission expired')
        # Select only the bound physical node, without opening a tty. A finite
        # RAM application may still be active; return_factory waits for it.
        usb=Path('/sys/bus/usb/devices/3-3').resolve(strict=True)
        serial=(usb/'serial').read_text().strip().casefold()
        require(re.fullmatch('[0-9a-f]{16}',serial) and hashlib.sha256(serial.encode()).hexdigest()==self.profile['uid_sha256'],
                'Recovery original identity differs')
        mode=((usb/'idVendor').read_text().strip().lower(),(usb/'idProduct').read_text().strip().lower())
        require(mode in (('2e8a',preserve.FACTORY_PID),('2e8a',preserve.BOOT_PID),('cafe','4013')),'Unexpected recovery mode')
        self.bus=int((usb/'busnum').read_text());require(self.clock()<until,'Recovery identity check late')
        self.admitted=True
        return dict(self.profile,qualification_verified=True)
    def enter_rom(self,until):raise ValueError('Recovery cannot install or start')
    load_ram=enter_rom
    stream=enter_rom

def select_stream(profile,bus,ready=False,sys_root=Path('/sys'),dev_root=Path('/dev')):
    trial.reject_pending_finalization(ROOT)
    usb=(sys_root/'bus/usb/devices/3-3').resolve(strict=True)
    read=lambda n:(usb/n).read_text().strip()
    serial=read('serial').casefold()
    require(re.fullmatch('[0-9a-f]{16}',serial) and hashlib.sha256(serial.encode()).hexdigest()==profile['uid_sha256']
            and int(read('busnum'))==bus,'Original UID/bus changed')
    mode=(read('idVendor').lower(),read('idProduct').lower())
    if ready and mode in (('2e8a',preserve.FACTORY_PID),('2e8a',preserve.BOOT_PID)):
        raise FileNotFoundError('Original has not entered stream mode')
    require(mode==('cafe','4013') and read('product')=='Forgix Synthetic RAM stream v1','Distinct PID4013 stream required')
    port=trial.fresh_tty('3-3','cafe','4013','Forgix Synthetic RAM stream v1',sys_root,dev_root,wait_missing=ready)
    return {'port':port,'usb_node':str(usb),'bus':read('busnum'),'enumeration':read('devnum'),
            'uid_sha256':profile['uid_sha256'],'vid':'cafe','pid':'4013'}

def serial_operation(request,path,select,opened,admission,clock_ns=time.monotonic_ns,pause=time.sleep):
    trial.reject_pending_finalization(ROOT)
    p=request['profile']
    return collector.collect(path,binding(p),opened,admission,select,request['lockfd'],request['lockpath'],
        request['boot_host_ns'],clock_ns,pause,host_pause=p['host_pause'])

class SyntheticTransport(capture.SerialDeadlineTransport):
    """Expose each consumed byte before POSIX pyserial can hide a failed prefix.

    A read(1) cannot retain an earlier internal chunk when its next syscall
    fails. Accumulate only here, where the collector can retain the prefix on
    timeout, interruption or read failure. The owned worker bounds kernel calls.
    """
    def read(self,size,deadline):
        require(type(size) is int and 1<=size<=512,'Bounded stream read required')
        prefix=bytearray()
        try:
            while len(prefix)<size:
                timeout=self.allowance(deadline,.05)
                if self.serial.timeout!=timeout:self.serial.timeout=timeout
                self.allowance(deadline,.05) # Configuration may itself block.
                chunk=self.serial.read(1)
                require(type(chunk) is bytes and len(chunk)<=1,'Single-byte read required')
                if chunk:prefix.extend(chunk)
                elif prefix:break
            return bytes(prefix) # Retain even a final byte returned too late.
        except BaseException as exc:
            exc.consumed_prefix=bytes(prefix)
            raise

def serial_worker(path):
    trial.reject_pending_finalization(ROOT)
    path=trial.private_file(path,'backups');r=json.loads(path.read_bytes());p=r['profile']
    qualified(p);session_lease(p);frozen_inputs(r['frozen'])
    qualification_receipt(p,r['environment'],r['frozen'])
    require(str(Path(sys.executable).resolve())==r['environment']['python_executable']
            and trial.sha(sys.executable)==r['environment']['python_executable_sha256'],'Worker interpreter differs')
    require(r['lockpath']==str(ROOT/'.scratch/esp-demo.lock'),'Shared lock required')
    require(digest(r['environment'])==p['environment_sha256'],'Worker environment differs')
    runtime.check(r['environment'])
    inherited_operator_lock(r['lockfd'],r['lockpath'])
    require(Path(path).parent.parent==Path(p['session_private_dir']),'Worker path differs from lease')
    def admission():
        trial.reject_pending_finalization(ROOT)
        qualified(p);session_lease(p);frozen_inputs(r['frozen'])
        qualification_receipt(p,r['environment'],r['frozen'])
        # No executable is dispatched here: retain selection checks without
        # hashing host binaries/archive repeatedly for every512-byte frame.
        runtime.check(r['environment'],verify_bytes=False)
        require(time.monotonic()<r['until'],'Worker stage deadline expired')
        require(trial.sha(p['elf'])==p['elf_sha256'] and trial.sha(Path(p['elf']).parent/'manifest.json')==p['manifest_sha256']
                and trial.sha(trial.private_file(p['qualification_path'],'.scratch'))==p['qualification_sha256'],'Worker artifact/qualification changed')
        return {'synthetic_stream_qualified':True,'lifecycle_admitted':True,'contract_sha256':CONTRACT_SHA256,
                'build_sha256':p['bridge_source_sha256'],'image_sha256':p['bitstream_sha256'],'rp_drain_pause_enabled':p['rp_pause']}
    # The collector's check() owns (rate-limited) admission; selection itself
    # only re-reads the identity-bound sysfs/tty state on every call.
    def select():return select_stream(p,r['bus'])
    if r.get('action')=='replay':
        admission()
        replay=collector.replay(path.parent/'capture',binding(p))
        require(replay['lossless'],'Saved replay failed qualification')
        with os.fdopen(os.open(path.parent/'replay.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600),'wb') as output:
            capture.durable(output,(json.dumps(replay,sort_keys=True)+'\n').encode())
        capture.sync_directory(path.parent);admission()
        return
    require(r.get('action') is None,'Unknown worker action')
    cutoff=min(r['until'],r['boot_host_ns']/1e9+30)
    common.ready_bridge(lambda:select_stream(p,r['bus'],ready=True),cutoff)
    def opened(identity,until):
        admission();serial=open_retaining_serial(identity['port'])
        try:return SyntheticTransport(serial)
        except BaseException:serial.close();raise
    try:
        result=serial_operation(r,path.parent/'capture',select,opened,admission)
        require(result['status']=='lossless','Forensic stream is failed qualification')
        replay=collector.replay(path.parent/'capture',binding(p))
        require(replay['lossless'],'Worker replay failed')
        admission()
    finally:
        require(time.monotonic()<r['until'],'Worker acceptance deadline expired')

if __name__=='__main__':
    os.umask(0o077);cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action',choices=('_serial-worker',));cli.add_argument('--request',type=Path,required=True)
    serial_worker(cli.parse_args().request)

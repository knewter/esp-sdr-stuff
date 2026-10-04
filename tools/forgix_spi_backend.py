#!/usr/bin/env python3
"""Prepared identity-selected backend. Empty qualification registry blocks hardware.

Only --plan is exposed here. The production coordinator separately checks the
committed registry before any run/load; that registry is empty. Qualification
and physical acceptance remain open. Raw identity/journals stay private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

import forgix_synthetic_runtime as runtime
from build_forgix_spi_bridge import FILES as ARTIFACT_FILES

import forgix_config as config
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve
from forgix_spi_lifecycle import WorkerOwner
from forgix_spi_qualifications import QUALIFIED
from forgix_usb_ram_artifact import inspect_elf
from forgix_usb_ram_capture import PrivateCapture,inherited_operator_lock,open_retaining_serial
from demo_esp_sdr import OwnedHardwareClosureError

ROOT=Path(__file__).resolve().parents[1]
EXECUTION_FILES=frozenset({
    '.gitignore','Taskfile.yml','flake.nix','flake.lock',trial.PROTOCOL,
    'docs/research/forgix-spi-register-trial-protocol.md',
    *('tools/'+name+'.py' for name in (
        'run_forgix_spi_trial','forgix_spi_backend','forgix_spi_qualifications',
        'forgix_spi_lifecycle','forgix_spi_capture','forgix_spi_bridge',
        'forgix_config','forgix_usb_ram_trial','forgix_usb_ram_capture',
        'forgix_usb_ram_artifact','preserve_forgix','demo_esp_sdr','flash_trial',
        'esp_sdr_capture','esp_sdr_spectrum_bridge','forgix_synthetic_runtime'))} | set(ARTIFACT_FILES))

def require(value,message):
    if not value:raise ValueError(message)

def artifact(folder):
    folder=trial.no_symlinks(folder)
    require(folder.is_relative_to(ROOT/'.scratch'),'Private bridge artifact required')
    manifest=trial.private_file(folder/'manifest.json','.scratch')
    elf=trial.private_file(folder/'forgix_spi_bridge.elf','.scratch')
    require(manifest.stat().st_size<=1024*1024 and 0<elf.stat().st_size<=4*1024*1024,'Artifact bounds')
    m=json.loads(manifest.read_text())
    require(set(m.get('source_sha256',{}))==set(ARTIFACT_FILES),'Complete bridge build-source map required')
    require(m.get('status')=='built_layout_guard_passed' and m.get('inputs_unchanged_after_build') is True
            and m.get('fpga_configuration_writer') is True and m.get('linked_embedded_image_verified') is True,
            'Exact-image configuration variant required')
    for name,digest in m['source_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Source path escaped repository')
        recorded=subprocess.check_output(['git','show',m['source_commit']+':'+name],cwd=ROOT,timeout=10)
        require(hashlib.sha256(recorded).hexdigest()==digest and trial.sha(ROOT/name)==digest,'Bridge build source differs')
    for name,digest in m['artifact_sha256'].items():
        require(Path(name).name==name and not (folder/name).is_symlink() and trial.sha(folder/name)==digest,'Exported artifact differs')
    layout=inspect_elf(elf.read_bytes(),application='spi-config-bridge')
    require(layout==m['layout'] and 'pico_get_unique_board_id_string' in layout['symbols'],'UID-enabled configuration ELF required')
    data=elf.read_bytes();image=m['configuration'];address=layout['symbols']['bridge_fpga_image'];size=image['decoded_bytes']
    segment=next(p for p in layout['load_segments'] if p['vaddr']<=address<address+size<=p['vaddr']+p['filesz'])
    offset=segment['offset']+address-segment['vaddr']
    require(hashlib.sha256(data[offset:offset+size]).hexdigest()==image['decoded_sha256'],'Linked image hash differs')
    return {'elf':str(elf),'elf_sha256':trial.sha(elf),'manifest_sha256':trial.sha(manifest),
            'source_commit':m['source_commit'],'bridge_source_sha256':m['build_source_sha256'],
            'bitstream_sha256':image['decoded_sha256'],'layout_bytes':layout['allocated_load_bytes']}

def qualification_key(profile):
    names=('elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256',
           'qualification_sha256','backend_source_sha256','coordinator_source_sha256',
           'execution_sha256','environment_sha256','uid_sha256','baseline_sha256')
    values=tuple(profile.get(n) for n in names)
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in values),'Complete qualification binding required')
    return values

def qualified(profile):
    require(qualification_key(profile) in QUALIFIED,'No committed physical qualification/loading review admits this backend')

def frozen_inputs(frozen):
    require(set(frozen['inputs'])==EXECUTION_FILES,'Complete exact execution input set required')
    trial.check_inputs(frozen)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def qualification_receipt(profile,environment,frozen):
    require(digest(environment)==profile['environment_sha256'],'Register runtime tuple differs')
    expected={n:h for n,h in frozen['inputs'].items() if n!='tools/forgix_spi_qualifications.py'}
    require(digest(expected)==profile['execution_sha256'],'Register execution tuple differs')
    path=trial.private_file(profile['qualification_path'],'.scratch')
    require(trial.sha(path)==profile['qualification_sha256'],'Qualification receipt differs')
    q=json.loads(path.read_text())
    for name in ('uid_sha256','baseline_sha256'):
        value=profile.get(name)
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
                and q.get(name)==value,'Qualification original board binding differs: '+name)
    require(q.get('kind')=='Forgix physical register episode qualification' and
            q.get('configuration_strategy')=='after_ram_startup' and
            q.get('reviewed_execution_sha256')==expected and
            q.get('reviewed_environment_sha256')==profile['environment_sha256'] and
            q.get('admission_registry_binding')=='separately frozen committed registry',
            'Qualification must bind complete execution and runtime')
    for name in ('fpga_grade_verified','clock_verified','spi_handoff_verified',
                 'whole_loading_recovery_reviewed','startup_uid_reviewed'):
        require(q.get(name) is True,'Physical/review qualification missing: '+name)
    require(q.get('elf_sha256')==profile['elf_sha256'] and
            q.get('bitstream_sha256')==profile['bitstream_sha256'],'Qualification artifact identity differs')
    return q

def original_profile(profile):
    binding=trial.original_binding(profile['binding_path'],*profile['baseline_paths'])
    require(all(profile[k]==v for k,v in binding.items()),'Original preservation binding differs')


def session_lease(profile,private=None):
    """A durable pre-access lease survives operator/process failure."""
    path=trial.private_file(ROOT/'.scratch/forgix-spi-active.json','.scratch')
    require(trial.sha(path)==profile.get('session_lease_sha256'),'Session lease changed or missing')
    record=json.loads(path.read_text())
    require(record.get('uid_sha256')==profile['uid_sha256'] and
            record.get('private_dir')==profile.get('session_private_dir') and
            (private is None or record['private_dir']==str(private)),
            'Session lease owner differs')
    return path

class AggregateOwner:
    def __init__(self,workers):self.workers=workers;self.runners=[];self.unknown=False
    @property
    def closed(self):
        return not self.unknown and self.workers.closed is True and all(r.hardware_process_closed is True for r in self.runners)

class RegisterPicotool(trial.OwnedPicotool):
    """Exact SRAM-only bridge load; the USB diagnostic whitelist stays fixed."""
    def __init__(self,*args,bridge,environment,**kwargs):
        super().__init__(*args,**kwargs);self.bridge=bridge;self.environment=environment
    def run(self,*args,**kwargs):
        runtime.check(self.environment)
        return super().run(*args,**kwargs)
    def load_args(self,target,backup,path):
        require(target.pid==preserve.BOOT_PID and Path(path)==Path('/private/ram-spi-bridge.elf'),'Selected ROM/dedicated bridge ELF required')
        require(trial.sha(backup)==self.bridge['elf_sha256'],'Staged bridge changed')
        inspect_elf(Path(backup).read_bytes(),application='spi-config-bridge')
        return ['load','-v','-x',str(path),'-t','elf','--bus',str(target.bus),'--address',str(target.address)]

class Backend:
    """Lifecycle adapter preparation; registry refusal precedes device selection.

    The caller holds the operator flock and supplies independently verified
    immutable environment/frozen inputs. Controller results remain model-only.
    The production coordinator cannot admit this object while the registry is empty.
    """
    def __init__(self,profile,private,lockfd,environment,frozen,clock=time.monotonic):
        self.profile,self.private,self.lockfd=profile,trial.no_symlinks(private),lockfd
        require(self.private.parent==ROOT/'backups','Fresh direct private backup directory required')
        self.environment,self.frozen,self.clock=environment,frozen,clock
        self.cleaning=False;self.used=False;self.admitted=False;self.bus=None;self.configuration=None;self.loader=None
        self.lockpath=ROOT/'.scratch/esp-demo.lock'
        self.private.mkdir(mode=0o700);(self.private/'workers').mkdir(mode=0o700)
        self.workers=WorkerOwner(self.private/'workers',lockfd,self.lockpath,clock)
        self.owner=AggregateOwner(self.workers)
        self.inspector=trial.BudgetInspector('3-3','/dev/null',float('inf'))
        self.inspector.identity_hash=profile['uid_sha256']

    def check_inputs(self):
        require(self.owner.closed,'Unknown owned worker/container closure blocks access')
        inherited_operator_lock(self.lockfd,self.lockpath)
        require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(),'Unclosed-resource marker blocks access')
        session_lease(self.profile,self.private)
        frozen_inputs(self.frozen)
        qualification_receipt(self.profile,self.environment,self.frozen)
        runtime.check(self.environment)
        for name in ('picotool_executable','python_executable'):
            require(trial.sha(self.environment[name])==self.environment[name+'_sha256'],'Frozen tool executable differs')
        require(trial.sha(self.profile['elf'])==self.profile['elf_sha256'],'Frozen ELF differs')
        require(trial.sha(Path(self.profile['elf']).parent/'manifest.json')==self.profile['manifest_sha256'],'Frozen artifact manifest differs')
        original_profile(self.profile)
        require(trial.sha(ROOT/'tools/forgix_spi_backend.py')==self.profile['backend_source_sha256'],'Backend source differs')
        require(trial.sha(ROOT/'tools/run_forgix_spi_trial.py')==self.profile['coordinator_source_sha256'],'Coordinator source differs')
        qualification=trial.private_file(self.profile['qualification_path'],'.scratch')
        require(trial.sha(qualification)==self.profile['qualification_sha256'],'Qualification receipt differs')

    def hardware_gate(self,until):
        require(self.admitted is True,'Backend session has not been admitted')
        qualified(self.profile)
        self.check_inputs()
        require(self.clock()<until,'Hardware stage deadline expired')

    def admit(self,until):
        require(not self.used,'One backend session');self.used=True
        qualified(self.profile)  # No sysfs/device query before the registry gate.
        self.check_inputs()
        require(self.environment.get('closure_contents_verified') is True and self.environment.get('sdk_nar_verified') is True,
                'Verified immutable Nix environment required')
        current=artifact(Path(self.profile['elf']).parent)
        require(all(self.profile[k]==v for k,v in current.items()),'Artifact/profile binding differs')
        require(self.clock()<until,'Admission deadline expired')
        factory=self.inspector.target(preserve.FACTORY_PID);self.bus=factory.bus
        self.admitted=True
        return dict(self.profile,qualification_verified=True,configuration_strategy='after_ram_startup')

    def preservation(self,name,until):
        self.hardware_gate(until)
        self.inspector.deadline=until
        store=preserve.PrivateStore(self.private/name,ROOT/'backups')
        runner=RegisterPicotool(self.environment['picotool_executable'],self.inspector,store,
            self.environment['image_id'],self.frozen,until,bridge=self.profile,environment=self.environment)
        self.owner.runners.append(runner) # Own cleanup before any possible storage failure.
        try:
            receipt,error=preserve.preserve(self.inspector,runner,store,trial.FLASH_BYTES,
                query=lambda i,t,s,label:bounded_factory_query(i,t,s,label,self.lockfd,until,runner,self.profile,self.environment,self.frozen))
        except BaseException as exc:
            if not runner.hardware_process_closed:
                self.owner.unknown=True
                raise OwnedHardwareClosureError('Register preservation closure unverified') from exc
            raise
        if not runner.hardware_process_closed:
            self.owner.unknown=True
            raise OwnedHardwareClosureError('Register preservation owned closure unverified')
        if error:raise error
        require(receipt['independent_device_verify'] is True and receipt['status']=='preserved_and_returned',
                'Fresh original factory/verification proof differs')
        trial.remaining(until,1)
        copies=receipt['backups']
        require(copies['sha256']==self.profile['baseline_sha256'] and copies['bytes_per_read']==trial.FLASH_BYTES
                and copies['reads']==2 and copies['matching'] is True,'Fresh original flash differs')
        return {'uid_sha256':self.profile['uid_sha256'],'flash_bytes':copies['bytes_per_read'],
                'read_sha256':[copies['sha256']]*2,'independent_device_verify':receipt['independent_device_verify'],
                'factory_application_verified':receipt['status']=='preserved_and_returned'}
    def preserve_before(self,until):return self.preservation('before',until)
    def preserve_after(self,until):return self.preservation('after',until)

    def enter_rom(self,until):
        self.hardware_gate(until)
        self.inspector.deadline=until
        store=preserve.PrivateStore(self.private/'load',ROOT/'backups')
        self.loader=RegisterPicotool(self.environment['picotool_executable'],self.inspector,store,
            self.environment['image_id'],self.frozen,until,bridge=self.profile,environment=self.environment)
        self.owner.runners.append(self.loader)
        store.create('ram-spi-bridge.elf',Path(self.profile['elf']).read_bytes())
        self.loader.run('boot',self.inspector.target(preserve.FACTORY_PID,self.bus))
        self.inspector.wait(preserve.BOOT_PID,self.bus)
        return {'rom_selected':True}

    def load_ram(self,until):
        self.hardware_gate(until)
        self.inspector.deadline=self.loader.deadline=until
        self.loader.run('load',self.inspector.target(preserve.BOOT_PID,self.bus),self.loader.store.path/'ram-spi-bridge.elf')
        return {'elf_sha256':self.profile['elf_sha256']}

    def serial_stage(self,action,until):
        self.hardware_gate(until)
        request={'action':action,'profile':self.profile,'environment':self.environment,'frozen':self.frozen,'lockfd':self.lockfd,
                 'lockpath':str(self.lockpath),'bus':self.bus,'until':until}
        if action=='collect':request['expected_identity']=self.configuration['identity_private']
        store=preserve.PrivateStore(self.private/action,ROOT/'backups')
        path=store.json('request.json',request)
        runtime.check(self.environment)
        self.workers.run([self.environment['python_executable'],str(ROOT/'tools/forgix_spi_backend.py'),
                          '_serial-worker','--request',str(path)],action,until)
        result=json.loads((store.path/'capture/result.json').read_text())
        require(result.get('transport_closed') is True and result.get('persistence_verified') is True,'Serial worker did not verify closure/persistence')
        return result
    def configure(self,until):
        self.configuration=self.serial_stage('configure',until)
        require(self.configuration.get('configuration_indication') is True,'Configuration indication missing')
        return self.configuration
    def transition(self,until):
        self.hardware_gate(until)
        require(self.configuration is not None,'No matching configuration receipt')
        require(self.configuration.get('bitstream_sha256')==self.profile['bitstream_sha256'] and
                self.configuration.get('source_sha256')==self.profile['bridge_source_sha256'],
                'Configuration reply does not bind the selected image/source')
        port=trial.fresh_tty('3-3','cafe','4012','Forgix SPI RAM bridge v1')
        identity=capture.select_bridge('3-3',port,uid_sha256=self.profile['uid_sha256'])
        require(identity==self.configuration['identity_private'] and self.clock()<until,'Enumeration changed after configuration')
        # Only a future registered physical transition review may admit this.
        qualified(self.profile)
        return {'bitstream_sha256':self.profile['bitstream_sha256'],'configuration_continuity_verified':True,
                'basis':'Registered transition review plus matching image/source reply and unchanged UID/enumeration; not CDONE alone'}
    def collect(self,until):return self.serial_stage('collect',until)

    def return_factory(self,until):
        self.hardware_gate(until)
        self.inspector.deadline=until
        if self.loader is None:
            # An enter-ROM intent may have been persisted before store creation
            # failed. Recovery must not depend on that stage having a loader.
            store=preserve.PrivateStore(self.private/'factory-return',ROOT/'backups')
            self.loader=RegisterPicotool(self.environment['picotool_executable'],self.inspector,store,
                self.environment['image_id'],self.frozen,until,bridge=self.profile,environment=self.environment)
            self.owner.runners.append(self.loader)
        self.loader.deadline=until
        factory=trial.watched_factory(self.inspector,self.bus,until,self.loader)
        bounded_factory_query(self.inspector,factory,self.loader.store,'returned-after-ram',self.lockfd,until,self.loader,self.profile,self.environment,self.frozen)
        return {'factory_application_verified':True}

def bounded_factory_query(inspector,target,store,label,lockfd,deadline,runner,profile,environment,frozen):
    """Same shared15-second query policy with register runtime admission at entry."""
    trial.reject_pending_finalization(ROOT)
    query_deadline=time.monotonic()+trial.remaining(deadline,15)
    runtime.check(environment);frozen_inputs(frozen);qualification_receipt(profile,environment,frozen)
    while True:
        trial.remaining(query_deadline,1);inspector.confirm(target)
        inspector.port=Path(trial.fresh_tty('3-3','2e8a',preserve.FACTORY_PID))
        if os.access(inspector.port,os.R_OK|os.W_OK,effective_ids=True):break
        time.sleep(min(.05,trial.remaining(query_deadline,.05)))
    runtime.check(environment);frozen_inputs(frozen);inspector.confirm(target)
    request={'topology':inspector.topology,'port':str(inspector.port),'target':target.__dict__,
             'label':label,'lockfd':lockfd,'profile':profile,'environment':environment,'frozen':frozen}
    path=store.json(label+'-query-request.json',request)
    runtime.check(environment);trial.remaining(query_deadline,1)
    try:
        code=trial.owned_worker([environment['python_executable'],str(Path(__file__).resolve()),
              '_factory-query-worker','--request',str(path)],store.path/(label+'-query.log'),lockfd,
              trial.remaining(query_deadline,15))
    except OwnedHardwareClosureError:
        runner.hardware_process_closed=False;raise
    trial.remaining(query_deadline,1)
    require(code==0,'Bounded register factory query failed; private transcript retained')
    return json.loads((store.path/(label+'-query-result.json')).read_text())

def factory_query_worker(path):
    trial.reject_pending_finalization(ROOT)
    path=trial.private_file(path,'backups');request=json.loads(path.read_text())
    qualified(request['profile']);session_lease(request['profile']);frozen_inputs(request['frozen'])
    qualification_receipt(request['profile'],request['environment'],request['frozen'])
    original_profile(request['profile'])
    runtime.check(request['environment'])
    inherited_operator_lock(request['lockfd'],ROOT/'.scratch/esp-demo.lock')
    # Reuse actual shared parsing/target/label/serial admission unchanged.
    original=sys.argv
    try:
        sys.argv=[str(Path(trial.__file__)), '_query','--request',str(path)]
        return trial.query_worker()
    finally:sys.argv=original


def serial_operation(request,store,select,open_transport,clock=time.monotonic):
    """Injectable real serial logic. Production worker also checks registry/lock.

    Neither this function nor its tests performs mode selection/RAM loading.
    The owning caller must contain blocked opens/close in a bounded process.
    """
    trial.reject_pending_finalization(ROOT)
    profile=request['profile'];until=request['until'];action=request['action']
    require(action in ('configure','collect'),'Unknown serial action')
    require(clock()<until,'Serial stage deadline expired')
    identity=select();transport=None;result={'status':'failed'};events=[];pending=None
    require(request.get('expected_identity',identity)==identity,'Prior configuration enumeration differs')
    original_lock=inherited_operator_lock(request['lockfd'],request['lockpath'])
    def check():
        require(clock()<until and select()==identity,'Selected identity changed or deadline expired')
        require(inherited_operator_lock(request['lockfd'],request['lockpath'])==original_lock,'Inherited operator lock changed')
    def factory(port,deadline):
        nonlocal transport
        check();transport=open_transport(port,min(deadline,until));check();return transport
    def lock():return inherited_operator_lock(request['lockfd'],request['lockpath'])
    try:
        if action=='collect':
            def selected():check();return identity
            result=capture.collect(store,profile['bridge_source_sha256'],secrets.token_bytes(16),factory,selected,lock,clock)
            require(result['status']=='registers_verified','Register collection failed; private prefix retained')
        else:
            with store.open('journal.jsonl') as journal:
                capture.durable(journal,b'')
                def event(record):
                    nonlocal pending
                    pending=record
                    capture.durable(journal,(json.dumps(record,sort_keys=True)+'\n').encode())
                    # exchange's validated receipt is returned and extended
                    # below; retain the exact on-disk event snapshot.
                    events.append(json.loads(json.dumps(record)));pending=None
                serial=factory(identity['port'],until)
                class Selected:
                    def read(self,n,deadline):check();return serial.read(n,min(deadline,until))
                    def write(self,data,deadline):check();return serial.write(data,min(deadline,until))
                result=config.exchange(Selected(),image_hash=profile['bitstream_sha256'],source_hash=profile['bridge_source_sha256'],
                    nonce=secrets.randbelow(0xffffffff)+1,until=until,write_event=event,clock=clock)
                result['persistence_verified']=True
                result['source_sha256']=profile['bridge_source_sha256']
                result['status']='configuration_indicated'
    finally:
        try:
            if action=='configure':
                retained=pending if pending and pending.get('phase')=='prefix' else next((e for e in reversed(events) if e.get('phase')=='prefix'),None)
                capture.save(store,'retained-prefix.json',retained)
                # Independently compare closed journal bytes, including failed prefixes.
                records=[json.loads(line) for line in (store.path/'journal.jsonl').read_bytes().splitlines()] if (store.path/'journal.jsonl').exists() else []
                if records!=events or pending is not None:result['persistence_verified']=False
        finally:
            # The collector owns successful closure. Failed open/check or receipt
            # persistence still reaches this independent fallback.
            if transport is not None and result.get('transport_closed') is not True:
                transport.close();result['transport_closed']=True
            result['identity_private']=identity
    check();require(result.get('persistence_verified') is True and result.get('transport_closed') is True,'Serial receipt incomplete')
    return result

def ready_bridge(select,until,clock=time.monotonic,pause=time.sleep):
    """Only wait for enumeration/permissions; identity failures stay fatal."""
    while clock()<until:
        try:
            identity=select()
        except FileNotFoundError:
            pass
        else:
            if os.access(identity['port'],os.R_OK|os.W_OK,effective_ids=True) and clock()<until:return identity
        left=until-clock()
        if left>0:pause(min(.05,left))
    raise TimeoutError('Selected bridge did not become ready before stage deadline')

def serial_worker(path):
    trial.reject_pending_finalization(ROOT)
    path=trial.private_file(path,'backups');request=json.loads(path.read_text());profile=request['profile']
    qualified(profile)
    session_lease(profile)
    frozen_inputs(request['frozen']);qualification_receipt(profile,request['environment'],request['frozen'])
    original_profile(profile)
    runtime.check(request['environment']);inherited_operator_lock(request['lockfd'],request['lockpath'])
    require(request['lockpath']==str(ROOT/'.scratch/esp-demo.lock'),'Original lifecycle lock required')
    current=artifact(Path(profile['elf']).parent)
    require(all(profile[k]==v for k,v in current.items()),'Worker artifact binding differs')
    bound_files={profile['elf']:profile['elf_sha256'],
                 profile['qualification_path']:profile['qualification_sha256'],
                 str(Path(profile['elf']).parent/'manifest.json'):profile['manifest_sha256'],
                 str(ROOT/'tools/forgix_spi_backend.py'):profile['backend_source_sha256']}
    def selected(ready=False):
        session_lease(profile)
        qualification_receipt(profile,request['environment'],request['frozen'])
        runtime.check(request['environment'],verify_bytes=False)
        frozen_inputs(request['frozen']);inherited_operator_lock(request['lockfd'],request['lockpath'])
        require(all(trial.sha(Path(name))==digest for name,digest in bound_files.items()),'Worker bound artifact/source changed')
        if ready:
            usb=Path('/sys/bus/usb/devices/3-3')
            mode=((usb/'idVendor').read_text().strip().lower(),(usb/'idProduct').read_text().strip().lower())
            if mode in (('2e8a',preserve.FACTORY_PID),('2e8a',preserve.BOOT_PID)):
                serial=(usb/'serial').read_text().strip().casefold()
                require(hashlib.sha256(serial.encode()).hexdigest()==profile['uid_sha256'] and
                        int((usb/'busnum').read_text())==request['bus'],'Original device changed during mode transition')
                raise FileNotFoundError('Original device has not enumerated its RAM bridge yet')
        port=trial.fresh_tty('3-3','cafe','4012','Forgix SPI RAM bridge v1',wait_missing=ready)
        result=capture.select_bridge('3-3',port,uid_sha256=profile['uid_sha256'])
        require(int(result['bus'])==request['bus'],'Bridge changed physical bus')
        return result
    def opened(port,until):
        serial=open_retaining_serial(port)
        return capture.SerialDeadlineTransport(serial)
    store=PrivateCapture(path.parent/'capture',ROOT/'backups')
    ready_bridge(lambda:selected(ready=True),request['until'])
    result=serial_operation(request,store,selected,opened)
    capture.save(store,'result.json',result)
    require(time.monotonic()<request['until'],'Worker result persistence exceeded deadline')

def main():
    os.umask(0o077)
    if len(sys.argv)>1 and sys.argv[1] in ('_serial-worker','_factory-query-worker'):
        cli=argparse.ArgumentParser();cli.add_argument('--request',type=Path,required=True)
        path=cli.parse_args(sys.argv[2:]).request
        return factory_query_worker(path) if sys.argv[1]=='_factory-query-worker' else serial_worker(path)
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--plan',required=True,type=Path)
    args=cli.parse_args()
    from build_forgix_usb_ram import fresh
    out=fresh(args.plan)
    (out/'plan.json').write_text(json.dumps({'kind':'backend preparation only','hardware_opened':False,
        'loading_admitted':False,'qualified_profiles':len(QUALIFIED),'physical_backend_reviewed':False,
        'implemented':['UID-required bridge selection','exact SRAM-only load arguments','root-owned USB container recovery',
                       'bounded inherited-lock serial workers','configuration prefix persistence','private register collection'],
        'remaining':['board/timing qualification','independent whole-backend load/recovery review',
                     'production coordinator admission','fresh preservation and physical register proof']},indent=2)+'\n')
    print('Private backend plan saved; hardware loading remains unadmitted.')

if __name__=='__main__':raise SystemExit(main())

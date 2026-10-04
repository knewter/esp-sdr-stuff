#!/usr/bin/env python3
"""Registry-gated, preserved Forgix synthetic stream episode; no qualification bypass.

Preflight is device-free. Run requires an exact committed qualification tuple,
the exclusive operator lock, private original backups and frozen Nix inputs.
The registry is currently empty. Successful execution still requires independent
physical-result review before any OpenSpec hardware acceptance.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time

import forgix_synthetic_backend as backend
import forgix_synthetic_runtime as runtime
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
from forgix_synthetic_lifecycle import Lifecycle
from demo_esp_sdr import Cancelled,OwnedHardwareClosureError

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=backend.REGISTRY

def require(value,message):
    if not value:raise ValueError(message)

class SessionLease:
    """Created before access; kept unless final factory/flash/closure proof passes."""
    def __init__(self,profile,private):
        self.path=trial.no_symlinks(ROOT/backend.LEASE)
        self.profile=profile
        profile['session_private_dir']=str(private)
        data=(json.dumps({'kind':'Forgix synthetic stream session lease','private_dir':str(private),
                         'uid_sha256':profile['uid_sha256'],'run_binding_sha256':backend.lease_binding(profile),'owner_pid':os.getpid(),
                         'token':os.urandom(16).hex()},sort_keys=True)+'\n').encode()
        # O_EXCL retains even a partial failed write as an admission blocker.
        with os.fdopen(os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
            capture.durable(stream,data)
        capture.sync_directory(self.path.parent)
        profile['session_lease_sha256']=hashlib.sha256(data).hexdigest()
        self.identity=(self.path.stat().st_dev,self.path.stat().st_ino)
    @classmethod
    def rotate(cls,profile,private):
        old=backend.session_lease(profile)
        info=old.stat();identity=(info.st_dev,info.st_ino)
        updated=dict(profile,session_private_dir=str(private))
        data=(json.dumps({'kind':'Forgix synthetic recovery session lease','private_dir':str(private),
            'uid_sha256':profile['uid_sha256'],'run_binding_sha256':backend.lease_binding(profile),
            'owner_pid':os.getpid(),'token':os.urandom(16).hex()},sort_keys=True)+'\n').encode()
        temporary=old.parent/('forgix-lease-update-'+os.urandom(8).hex()+'.json')
        try:
            with os.fdopen(os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as out:
                capture.durable(out,data)
            backend.session_lease(profile)
            now=old.stat();require((now.st_dev,now.st_ino)==identity,'Lease changed during recovery rotation')
            os.replace(temporary,old);capture.sync_directory(old.parent)
        finally:
            if temporary.exists():temporary.unlink()
        profile.update(updated,session_lease_sha256=hashlib.sha256(data).hexdigest())
        lease=object.__new__(cls);lease.profile=profile;lease.path=old
        lease.identity=(old.stat().st_dev,old.stat().st_ino)
        return lease
    def release(self,record):
        require(record.get('original_flash_and_factory_verified') is True and
                record.get('owned_processes_closed') is True,'Incomplete recovery retains the session lease')
        backend.session_lease(self.profile)
        info=self.path.stat()
        require((info.st_dev,info.st_ino)==self.identity,'Session lease inode changed')
        self.path.unlink();capture.sync_directory(self.path.parent)

class ReceiptStore:
    """Attach durable receipt operations to the backend-created private directory."""
    def __init__(self,path):
        self.path=trial.no_symlinks(path)
        info=self.path.stat()
        require(self.path.parent==ROOT/'backups' and stat.S_ISDIR(info.st_mode)
                and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),
                'Owned direct private backend directory required')
    def open(self,name):
        require(Path(name).name==name,'Receipt name must be a basename')
        return os.fdopen(os.open(self.path/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')

def freeze():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=10).strip()
    inputs={}
    for name in sorted(backend.EXECUTION_FILES):
        path=trial.no_symlinks(ROOT/name)
        recorded=subprocess.check_output(['git','show',head+':'+name],cwd=ROOT,timeout=10)
        require(path.read_bytes()==recorded,'Execution input must be committed and unchanged')
        inputs[name]=hashlib.sha256(recorded).hexdigest()
    frozen={'source_commit':head,'inputs':inputs}
    backend.frozen_inputs(frozen)
    return frozen

def prepare(args):
    trial.reject_pending_finalization(ROOT)
    # No file flags or CLI switches can create an entry in this source registry.
    require(bool(backend.QUALIFIED),'No committed qualification admits a physical synthetic stream episode')
    tools=runtime.select();runtime.activate(tools)
    profile=backend.artifact(args.artifact)
    profile.update(period=args.period,target=backend.PROFILES[args.period],host_pause=True,nonce=os.urandom(16).hex())
    profile.update(trial.original_binding(args.binding,args.baseline_a,args.baseline_b))
    qualification=trial.private_file(args.qualification,'.scratch')
    require(0<qualification.stat().st_size<=1024*1024,'Bounded qualification receipt required')
    profile.update(qualification_path=str(qualification),qualification_sha256=trial.sha(qualification),
                   backend_source_sha256=trial.sha(ROOT/'tools/forgix_synthetic_backend.py'),
                   coordinator_source_sha256=trial.sha(ROOT/'tools/run_forgix_synthetic_trial.py'))
    frozen=freeze()
    environment=runtime.image_check(args.image_id,tools)
    profile.update(execution_sha256=backend.digest({n:h for n,h in frozen['inputs'].items() if n!=REGISTRY}),
                   environment_sha256=backend.digest(environment))
    backend.qualified(profile)
    backend.binding(profile)
    backend.qualification_receipt(profile,environment,frozen)
    private=trial.no_symlinks(args.private_dir)
    require(private.parent==ROOT/'backups' and not private.exists(),'Fresh direct backups child required')
    require(subprocess.run(['git','check-ignore','--quiet',str(private)],cwd=ROOT,timeout=10).returncode==0,
            'Private output must be Git ignored')
    return profile,environment,frozen,private

@contextmanager
def operator_lock(recovery_profile=None):
    path=trial.no_symlinks(ROOT/'.scratch/esp-demo.lock')
    path.parent.mkdir(exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and
                stat.S_IMODE(info.st_mode)==0o600,'Operator lock must be owned regular0600')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        capture.inherited_operator_lock(fd,path)
        trial.reject_pending_finalization(ROOT)
        require(not (ROOT/'.scratch/forgix-usb-ram-unclosed.json').exists(),'Unknown resource closure blocks device access')
        if recovery_profile is None:
            require(not (ROOT/backend.LEASE).exists(),'Unresolved synthetic session lease blocks device access')
        else:backend.session_lease(recovery_profile)
        yield fd
    finally:
        os.close(fd)

def execute(adapter,store,preflight,clock=time.monotonic,began=None):
    """Persist policy events without promoting its model receipts to RF proof."""
    began=clock() if began is None else began;events=[];pending=None;failure=None;summary=None
    record=dict(preflight,status='failed',physical_measurement_acceptance='pending independent result review',
                session_deadline_policy_seconds=600,flash_write_operations=0,
                deadline_scope='Cooperative stage/acceptance deadline. Existing owned container cleanup may add up to 42 seconds after an operation timeout; OS responsiveness and physical recovery remain separately qualified.',
                original_flash_and_factory_verified=False)
    capture.save(store,'preflight.json',record)
    try:
        require(clock()<began+600,'Initial persistence exceeded session deadline')
        with store.open('lifecycle.jsonl') as journal:
            capture.durable(journal,b'');capture.sync_directory(store.path)
            require(clock()<began+600,'Journal persistence exceeded session deadline')
            def event(value):
                nonlocal pending
                pending=json.loads(json.dumps(value))
                capture.durable(journal,(json.dumps(pending,sort_keys=True)+'\n').encode())
                events.append(pending);pending=None
            engine=Lifecycle(adapter,event,clock)
            try:
                summary=engine.run(began=began)
            finally:
                record['lifecycle_policy']=dict(engine.summary)
                if summary is None:summary=dict(engine.summary)
    except BaseException as exc:
        failure=exc;record['failure_kind']=type(exc).__name__
    finally:
        adapter.cleaning=True
        record['owned_processes_closed']=adapter.owner.closed is True
        if not record['owned_processes_closed']:
            record['manual_recovery_required']=True
            failure=failure or OwnedHardwareClosureError('Owned closure remains unknown')
        try:
            retained=[json.loads(line) for line in (store.path/'lifecycle.jsonl').read_bytes().splitlines()]
            require(retained==events and pending is None,'Private lifecycle journal persistence differs')
            record['event_persistence_verified']=True
            adapter.check_inputs()
        except BaseException as exc:
            failure=failure or exc;record['final_check_kind']=type(exc).__name__
        if summary is not None:
            record['original_flash_and_factory_verified']=summary.get('original_flash_and_factory_verified') is True
        record['host_elapsed_seconds']=clock()-began
        if record['host_elapsed_seconds']>=600:
            record['deadline_exceeded']=True;failure=failure or TimeoutError('Session acceptance deadline exceeded')
        if failure is None and summary and summary.get('status')=='synthetic_completed' and record['original_flash_and_factory_verified']:
            record['status']='synthetic_episode_completed'
        if failure is not None:record['failure_kind']=type(failure).__name__
        capture.save(store,'session.json',record)
        # Final durable receipt is inside the acceptance bound too. If its I/O
        # crosses the deadline, atomically retain an authoritative failure.
        if clock()-began>=600 and record['status']=='synthetic_episode_completed':
            record.update(status='failed',deadline_exceeded=True,failure_kind='TimeoutError',host_elapsed_seconds=clock()-began)
            capture.save(store,'late-session.json',record)
            os.replace(store.path/'late-session.json',store.path/'session.json')
            capture.sync_directory(store.path)
            failure=failure or TimeoutError('Terminal receipt exceeded deadline')
    if failure is not None and not isinstance(failure,Exception):raise failure
    return record

def recovery_admission(path,profile,environment,frozen):
    trial.reject_pending_finalization(ROOT)
    path=trial.private_file(path,'backups')
    require(path.name=='session.json' and path.parent.parent==ROOT/'backups' and path.stat().st_size<=4*1024*1024,
            'Original direct private session receipt required')
    prior=json.loads(path.read_bytes())
    require(prior.get('owned_processes_closed') is True and prior.get('physical_execution_requested') is True,
            'Known aggregate owned closure and actual original session required')
    require(prior.get('status') in ('failed','synthetic_episode_completed'),'Unexpected original terminal status')
    old=prior['profile_private']
    require(old.get('session_private_dir')==str(path.parent),'Prior lease directory differs')
    require(prior['execution']['inputs']==frozen['inputs'] and backend.digest(prior['environment_private'])==backend.digest(environment),
            'Recovery must use identical frozen execution/runtime')
    for name in ('elf','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','qualification_sha256',
                 'execution_sha256','environment_sha256','uid_sha256','baseline_sha256','baseline_paths','binding_sha256',
                 'configuration','artifact_exports','period','target','rp_pause','host_pause'):
        require(type(old.get(name)) is type(profile[name]) and old[name]==profile[name],'Original recovery tuple differs: '+name)
    profile.update({n:old[n] for n in ('nonce','session_private_dir','session_lease_sha256')})
    backend.binding(profile);backend.session_lease(profile,path.parent)
    return prior

def execute_recovery(adapter,store,preflight,clock=time.monotonic,began=None):
    began=clock() if began is None else began;deadline=began+600
    record=dict(preflight,status='failed',flash_write_operations=0,ram_load_operations=0,
                configuration_start_operations=0,original_flash_and_factory_verified=False,
                owned_processes_closed=False,physical_measurement_acceptance='failed stream remains failed')
    error=None;events=[]
    try:
        capture.save(store,'preflight.json',record)
        require(clock()<deadline,'Recovery persistence exceeded deadline')
        with store.open('recovery.jsonl') as journal:
            def event(v):capture.durable(journal,(json.dumps(v,sort_keys=True)+'\n').encode());events.append(v)
            adapter.cleaning=True
            for name,fn,budget in [('admit-recovery',adapter.admit,30),('return-factory',adapter.return_factory,140),('preserve-after',adapter.preserve_after,180)]:
                require(adapter.owner.closed is True,'Unknown closure blocks recovery');adapter.check_inputs()
                until=min(deadline,clock()+budget);require(clock()<until,'Recovery stage deadline expired')
                event({'stage':name,'phase':'intent','deadline':until});require(clock()<until,'Recovery intent crossed deadline')
                r=fn(until)
                require(adapter.owner.closed is True and clock()<until,'Recovery closure or deadline failed')
                event({'stage':name,'phase':'returned','receipt':r});require(clock()<until,'Recovery receipt crossed deadline')
                if name=='preserve-after':
                    policy=Lifecycle(adapter,lambda v:None,clock);policy.profile=adapter.profile;policy.preservation(r)
                    record['original_flash_and_factory_verified']=True
        require([json.loads(line) for line in (store.path/'recovery.jsonl').read_bytes().splitlines()]==events,
                'Recovery journal readback differs')
        adapter.check_inputs();require(clock()<deadline,'Recovery final deadline expired')
        record.update(status='recovered_and_verified',event_persistence_verified=True)
    except BaseException as exc:error=exc;record['failure_kind']=type(exc).__name__
    finally:
        record['owned_processes_closed']=adapter.owner.closed is True
        if not record['owned_processes_closed']:record.update(status='failed',manual_recovery_required=True)
        record['host_elapsed_seconds']=clock()-began
        if clock()>=deadline:record.update(status='failed',deadline_exceeded=True)
        capture.save(store,'session.json',record)
        if clock()>=deadline and record['status']=='recovered_and_verified':
            record.update(status='failed',deadline_exceeded=True,host_elapsed_seconds=clock()-began)
            capture.save(store,'recovery-late.json',record);os.replace(store.path/'recovery-late.json',store.path/'session.json');capture.sync_directory(store.path)
    if error is not None and not isinstance(error,Exception):raise error
    return record

def release_lease(lease,store,record,began,clock=time.monotonic):
    error=None
    try:lease.release(record)
    except BaseException as exc:
        error=exc;record.update(status='failed',failure_kind=type(exc).__name__,lease_release_failure_kind=type(exc).__name__)
    if clock()>=began+600:
        record.update(status='failed',deadline_exceeded=True,failure_kind='TimeoutError',
                      host_elapsed_seconds=clock()-began)
    if error is not None or record.get('deadline_exceeded') is True:
        try:
            capture.save(store,'lease-release-failed.json',record)
            os.replace(store.path/'lease-release-failed.json',store.path/'session.json')
            capture.sync_directory(store.path)
        except BaseException as persistence:
            record['terminal_persistence_failure_kind']=type(persistence).__name__
            if error is None:raise
    if error is not None:raise error
    return record

def parser():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action',choices=('preflight','run','recover'))
    cli.add_argument('--prior-session',type=Path)
    cli.add_argument('--period',type=int,choices=tuple(backend.PROFILES),default=2000000)
    cli.add_argument('--artifact',required=True,type=Path)
    cli.add_argument('--binding',required=True,type=Path)
    cli.add_argument('--baseline-a',required=True,type=Path)
    cli.add_argument('--baseline-b',required=True,type=Path)
    cli.add_argument('--qualification',required=True,type=Path)
    cli.add_argument('--private-dir',required=True,type=Path)
    cli.add_argument('--image-id',default=os.environ.get('PICOTOOL_CONTAINER_IMAGE_ID'))
    return cli

def main():
    os.umask(0o077);args=parser().parse_args();adapter=None;record={'status':'refused'}
    def cancel(signum,frame):
        if adapter is not None and adapter.cleaning:
            print('Cancellation deferred during bounded factory/full-flash cleanup.',flush=True)
        else:raise Cancelled('Synthetic episode cancelled')
    handlers={s:signal.signal(s,cancel) for s in (signal.SIGINT,signal.SIGTERM)}
    try:
        profile,environment,frozen,private=prepare(args)
        if args.action=='preflight':
            record={'status':'preflight_passed','physical_execution_requested':False}
            print('Qualified immutable preflight passed; no hardware opened.');return 0
        prior=None
        if args.action=='recover':
            require(args.prior_session is not None,'Recovery requires original terminal receipt')
            prior=recovery_admission(args.prior_session,profile,environment,frozen)
        with operator_lock(profile if prior is not None else None) as lockfd:
            backend.frozen_inputs(frozen);backend.qualified(profile);runtime.check(environment)
            began=time.monotonic()
            if prior is not None:recovery_admission(args.prior_session,profile,environment,frozen)
            adapter=(backend.RecoveryBackend if prior is not None else backend.Backend)(profile,private,lockfd,environment,frozen)
            store=ReceiptStore(private)
            if prior is None:lease=SessionLease(profile,private)
            else:
                # Atomically hand the unresolved lease to the fresh recovery
                # receipt BEFORE access. Crash/unknown closure cannot reuse an
                # older known-closed receipt even if marker persistence fails.
                lease=SessionLease.rotate(profile,private)
                adapter.lease_private=private
            try:
                record=(execute_recovery if prior is not None else execute)(adapter,store,{'kind':'identity-selected Forgix synthetic stream episode',
                    'profile_private':profile,'environment_private':environment,'execution':frozen,
                    'physical_execution_requested':True,'recovery_only':prior is not None,
                    'prior_session_sha256':trial.sha(args.prior_session) if prior is not None else None},began=began)
            finally:
                # Cancellation may propagate only after the terminal receipt.
                terminal=private/'session.json'
                if terminal.exists():
                    saved=json.loads(terminal.read_text())
                    if saved.get('original_flash_and_factory_verified') is True and saved.get('owned_processes_closed') is True:
                        release_lease(lease,store,saved,began)
                        record=saved
        return 0 if record['status'] in ('synthetic_episode_completed','recovered_and_verified') else 2
    except BaseException as exc:
        record.update(status='refused' if adapter is None else 'failed',failure_kind=type(exc).__name__)
        return 2
    finally:
        for s,handler in handlers.items():signal.signal(s,handler)
        print(json.dumps({k:record.get(k) for k in ('status','failure_kind','original_flash_and_factory_verified','owned_processes_closed')}))

if __name__=='__main__':raise SystemExit(main())

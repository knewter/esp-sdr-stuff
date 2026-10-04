#!/usr/bin/env python3
"""Registry-gated, preserved Forgix register episode; no qualification bypass.

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
import signal
import stat
import subprocess
import sys
import time

import forgix_spi_backend as backend
import forgix_synthetic_runtime as runtime
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
from forgix_spi_lifecycle import Lifecycle
from demo_esp_sdr import Cancelled,OwnedHardwareClosureError

ROOT=Path(__file__).resolve().parents[1]
REGISTRY='tools/forgix_spi_qualifications.py'

def require(value,message):
    if not value:raise ValueError(message)

class SessionLease:
    """Created before access; kept unless final factory/flash/closure proof passes."""
    def __init__(self,profile,private):
        self.path=trial.no_symlinks(ROOT/'.scratch/forgix-spi-active.json')
        self.pending_path=trial.no_symlinks(ROOT/'.scratch/forgix-spi-finalization-pending.json')
        self.profile=profile
        profile['session_private_dir']=str(private)
        data=(json.dumps({'kind':'Forgix register session lease','private_dir':str(private),
                         'uid_sha256':profile['uid_sha256'],'owner_pid':os.getpid(),
                         'token':os.urandom(16).hex()},sort_keys=True)+'\n').encode()
        self.data=data
        # O_EXCL retains even a partial failed write as an admission blocker.
        with os.fdopen(os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
            capture.durable(stream,data)
        capture.sync_directory(self.path.parent)
        profile['session_lease_sha256']=hashlib.sha256(data).hexdigest()
        self.identity=(self.path.stat().st_dev,self.path.stat().st_ino)
    def pending(self):
        """Separate durable blocker survives a failed active-lease recreation."""
        if self.pending_path.exists():
            require(self.pending_path.read_bytes()==self.data,'Finalization blocker owner changed')
            return
        with os.fdopen(os.open(self.pending_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
            capture.durable(stream,self.data)
        capture.sync_directory(self.pending_path.parent)
    def clear_pending(self):
        require(self.pending_path.read_bytes()==self.data,'Finalization blocker owner changed')
        self.pending_path.unlink();capture.sync_directory(self.pending_path.parent)
    def release(self,record):
        require(record.get('original_flash_and_factory_verified') is True and
                record.get('owned_processes_closed') is True,'Incomplete recovery retains the session lease')
        backend.session_lease(self.profile)
        info=self.path.stat()
        require((info.st_dev,info.st_ino)==self.identity,'Session lease inode changed')
        self.path.unlink();capture.sync_directory(self.path.parent)
    def retain(self):
        """Restore the exact conservative blocker after uncertain final release."""
        if self.path.exists():
            require(self.path.read_bytes()==self.data,'Finalization lease owner changed')
            return
        # A partial write is itself retained as a blocker; never remove on error.
        with os.fdopen(os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
            capture.durable(stream,self.data)
        capture.sync_directory(self.path.parent)
        info=self.path.stat();self.identity=(info.st_dev,info.st_ino)

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
    require(bool(backend.QUALIFIED),'No committed qualification admits a physical register episode')
    tools=runtime.select();runtime.activate(tools)
    profile=backend.artifact(args.artifact)
    profile.update(trial.original_binding(args.binding,args.baseline_a,args.baseline_b))
    qualification=trial.private_file(args.qualification,'.scratch')
    require(0<qualification.stat().st_size<=1024*1024,'Bounded qualification receipt required')
    profile.update(qualification_path=str(qualification),qualification_sha256=trial.sha(qualification),
                   backend_source_sha256=trial.sha(ROOT/'tools/forgix_spi_backend.py'),
                   coordinator_source_sha256=trial.sha(ROOT/'tools/run_forgix_spi_trial.py'))
    frozen=freeze()
    environment=runtime.image_check(args.image_id,tools)
    profile.update(execution_sha256=backend.digest({n:h for n,h in frozen['inputs'].items() if n!=REGISTRY}),
                   environment_sha256=backend.digest(environment))
    backend.qualified(profile)
    backend.qualification_receipt(profile,environment,frozen)
    backend.frozen_inputs(frozen)
    require(trial.sha(qualification)==profile['qualification_sha256'],'Qualification changed during preflight')
    private=trial.no_symlinks(args.private_dir)
    require(private.parent==ROOT/'backups' and not private.exists(),'Fresh direct backups child required')
    require(subprocess.run(['git','check-ignore','--quiet',str(private)],cwd=ROOT,timeout=10).returncode==0,
            'Private output must be Git ignored')
    return profile,environment,frozen,private

@contextmanager
def operator_lock():
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
        require(not (ROOT/'.scratch/forgix-spi-active.json').exists(),'Unresolved register session lease blocks device access')
        yield fd
    finally:
        os.close(fd)

def execute(adapter,store,preflight,clock=time.monotonic):
    """Persist policy events without promoting its model receipts to RF proof."""
    began=preflight.get('session_began_monotonic',clock());events=[];pending=None;failure=None;summary=None
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
        if failure is None and summary and summary.get('status')=='model_completed' and record['original_flash_and_factory_verified']:
            record['status']='backend_episode_observed'
            record['finalization_status']='pending'
        if failure is not None:record['failure_kind']=type(failure).__name__
        capture.save(store,'session.json',record)
        # Final durable receipt is inside the acceptance bound too. If its I/O
        # crosses the deadline, atomically retain an authoritative failure.
        if clock()-began>=600 and record['status']=='backend_episode_observed':
            record.update(status='failed',deadline_exceeded=True,failure_kind='TimeoutError',host_elapsed_seconds=clock()-began)
            capture.save(store,'late-session.json',record)
            os.replace(store.path/'late-session.json',store.path/'session.json')
            capture.sync_directory(store.path)
            failure=failure or TimeoutError('Terminal receipt exceeded deadline')
    if failure is not None and not isinstance(failure,Exception):raise failure
    return record

def finalize_session(lease,store,record,began,clock=time.monotonic):
    """One clock includes release and durable terminal acknowledgement.

    Pending intent is retained independently of session replacement. Any known
    finalization failure restores the conservative lease before corrective I/O.
    """
    candidate=record.get('status') in ('backend_episode_observed','backend_episode_completed')
    record.update(status='pending_finalization' if candidate else 'failed',finalization_status='pending')
    def within(message):
        if clock()>=began+600:raise TimeoutError(message)
    def replace(name):
        capture.save(store,name,record)
        os.replace(store.path/name,store.path/'session.json')
        capture.sync_directory(store.path)
    try:
        capture.save(store,'finalization-intent.json',record)
        lease.pending()
        within('Finalization acceptance deadline expired')
        if record.get('original_flash_and_factory_verified') is True and record.get('owned_processes_closed') is True:
            lease.release(record)
            record['lease_release_status']='released'
        else:
            record['lease_release_status']='retained'
            candidate=False
        within('Lease release exceeded acceptance deadline')
        record.update(status='pending_finalization' if candidate else 'failed',finalization_status='pending',host_elapsed_seconds=clock()-began)
        replace('final-session.json')
        within('Final terminal persistence exceeded acceptance deadline')
        record.update(status='backend_episode_completed' if candidate else 'failed',finalization_status='acknowledged',host_elapsed_seconds=clock()-began)
        replace('acknowledged-final-session.json')
        within('Acknowledged terminal persistence exceeded acceptance deadline')
        lease.clear_pending()
        within('Finalization blocker closure exceeded acceptance deadline')
    except BaseException as primary:
        record.update(status='failed',finalization_status='failed',finalization_failure_kind=type(primary).__name__,host_elapsed_seconds=clock()-began)
        record.setdefault('failure_kind',type(primary).__name__)
        if clock()>=began+600:record['deadline_exceeded']=True
        try:
            lease.retain();record['lease_release_status']='retained'
        except BaseException as error:
            record.update(lease_retention_failure_kind=type(error).__name__,lease_release_status='uncertain')
            # The independent pending marker normally already exists. If final
            # marker closure itself failed, re-establish it before returning.
            try:
                lease.pending();record['admission_blocked_by_pending_finalization']=True
            except BaseException as blocked:record['pending_retention_failure_kind']=type(blocked).__name__
        try:replace('failed-final-session.json')
        except BaseException as error:
            record['corrective_journal_failure_kind']=type(error).__name__
        # Preserve primary cancellation/error even if corrective persistence fails.
        if not isinstance(primary,Exception):raise primary
    return record

def parser():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action',choices=('preflight','run'))
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
        else:raise Cancelled('Register episode cancelled')
    handlers={s:signal.signal(s,cancel) for s in (signal.SIGINT,signal.SIGTERM)}
    try:
        profile,environment,frozen,private=prepare(args)
        if args.action=='preflight':
            record={'status':'preflight_passed','physical_execution_requested':False}
            print('Qualified immutable preflight passed; no hardware opened.');return 0
        with operator_lock() as lockfd:
            backend.frozen_inputs(frozen);backend.qualified(profile);runtime.check(environment)
            adapter=backend.Backend(profile,private,lockfd,environment,frozen)
            store=ReceiptStore(private)
            began=time.monotonic()
            lease=SessionLease(profile,private)
            try:
                record=execute(adapter,store,{'kind':'identity-selected Forgix register episode',
                    'profile_private':profile,'environment_private':environment,'execution':frozen,
                    'physical_execution_requested':True,'session_began_monotonic':began})
            finally:
                # Cancellation may propagate only after the terminal receipt.
                terminal=private/'session.json'
                if terminal.exists():
                    adapter.cleaning=True
                    saved=json.loads(terminal.read_text())
                    # The returned saved lifecycle duration must never restart
                    # the acceptance clock (including injected host fixtures).
                    elapsed=saved.get('host_elapsed_seconds',0)
                    original_began=min(began,time.monotonic()-elapsed)
                    record=finalize_session(lease,store,saved,original_began,time.monotonic)
        return 0 if record['status']=='backend_episode_completed' else 2
    except BaseException as exc:
        record.update(status='refused' if adapter is None else 'failed',failure_kind=type(exc).__name__)
        return 2
    finally:
        for s,handler in handlers.items():signal.signal(s,handler)
        print(json.dumps({k:record.get(k) for k in ('status','failure_kind','original_flash_and_factory_verified','owned_processes_closed')}))

if __name__=='__main__':raise SystemExit(main())

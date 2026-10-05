#!/usr/bin/env python3
"""Registry-gated, preserved Forgix clock measurement episode; no qualification bypass.

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
import re
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time

import forgix_clock_backend as backend
import forgix_synthetic_runtime as runtime
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
from forgix_clock_lifecycle import Lifecycle
from demo_esp_sdr import Cancelled,OwnedHardwareClosureError

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=backend.REGISTRY

def require(value,message):
    if not value:raise ValueError(message)

def owned_file(path,data,identity,links,label):
    """Check a privately retained inode after all fallible read/close effects.

    The global operator and trusted filesystem remain the original boundaries;
    byte equality alone never creates ownership of an existing pathname.
    """
    def valid(info):
        require((info.st_dev,info.st_ino)==identity,label+' inode differs')
        require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600
                and info.st_uid==os.getuid() and info.st_nlink in links
                and info.st_size==len(data),label+' owner differs')
    initial=path.lstat();valid(initial)
    def unchanged(info):
        valid(info)
        require((info.st_mtime_ns,info.st_ctime_ns)==(initial.st_mtime_ns,initial.st_ctime_ns),
                label+' changed during validation')
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        unchanged(os.fstat(stream.fileno()))
        require(stream.read(len(data)+1)==data,label+' bytes differ')
        unchanged(os.fstat(stream.fileno()))
    info=path.lstat();unchanged(info)
    return info

class SessionLease:
    """Created before access; exact authority never comes from matching bytes."""
    def __init__(self,profile,private):
        self.path=trial.no_symlinks(ROOT/backend.LEASE)
        self.pending_path=trial.no_symlinks(ROOT/'.scratch/forgix-spi-finalization-pending.json')
        self.profile=profile;profile['session_private_dir']=str(private)
        self.data=(json.dumps({'kind':'Forgix clock measurement session lease','private_dir':str(private),
            'uid_sha256':profile['uid_sha256'],'run_binding_sha256':backend.lease_binding(profile),
            'owner_pid':os.getpid(),'token':os.urandom(16).hex()},sort_keys=True)+'\n').encode()
        with os.fdopen(os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
            info=os.fstat(stream.fileno());self.identity=(info.st_dev,info.st_ino)
            capture.durable(stream,self.data)
        capture.sync_directory(self.path.parent)
        owned_file(self.path,self.data,self.identity,(1,),'Clock active lease')
        profile['session_lease_sha256']=hashlib.sha256(self.data).hexdigest()
    @classmethod
    def rotate(cls,profile,private):
        old=backend.session_lease(profile);info=old.lstat();identity=(info.st_dev,info.st_ino)
        original=old.read_bytes()
        require(hashlib.sha256(original).hexdigest()==profile['session_lease_sha256'],'Recovery lease bytes differ')
        owned_file(old,original,identity,(1,),'Clock recovery lease')
        updated=dict(profile,session_private_dir=str(private))
        data=(json.dumps({'kind':'Forgix clock recovery session lease','private_dir':str(private),
            'uid_sha256':profile['uid_sha256'],'run_binding_sha256':backend.lease_binding(profile),
            'owner_pid':os.getpid(),'token':os.urandom(16).hex()},sort_keys=True)+'\n').encode()
        temporary=old.parent/('forgix-lease-update-'+os.urandom(8).hex()+'.json');created=None
        try:
            with os.fdopen(os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb') as stream:
                info=os.fstat(stream.fileno());created=(info.st_dev,info.st_ino)
                capture.durable(stream,data)
            owned_file(temporary,data,created,(1,),'Clock recovery temporary lease')
            backend.session_lease(profile)
            owned_file(old,original,identity,(1,),'Clock recovery lease')
            # No fallible validation effect intervenes before replacing the
            # exact old lease; creation identity follows the new inode.
            os.replace(temporary,old);capture.sync_directory(old.parent)
            owned_file(old,data,created,(1,),'Clock rotated lease')
        finally:
            if temporary.exists() and created is not None:
                # Failed rotation cannot unlink an unrelated temporary inode.
                owned_file(temporary,data,created,(1,),'Clock recovery temporary lease')
                temporary.unlink();capture.sync_directory(temporary.parent)
        profile.update(updated,session_lease_sha256=hashlib.sha256(data).hexdigest())
        lease=object.__new__(cls);lease.profile=profile;lease.path=old;lease.identity=created
        lease.data=data;lease.pending_path=trial.no_symlinks(ROOT/'.scratch/forgix-spi-finalization-pending.json')
        return lease
    def check_pending(self):
        require(hasattr(self,'pending_identity'),'Clock pending marker has no retained creation authority')
        path=self.pending_path
        info=owned_file(path,self.data,self.pending_identity,(1,2),'Clock pending marker')
        if info.st_nlink==2:
            require(getattr(self,'pending_linked_identity',None)==self.pending_identity==self.identity,
                    'Clock pending link authority differs')
            owned_file(self.path,self.data,self.identity,(2,),'Clock linked active lease')
            # Reading/closing the second link is fallible too.
            info=owned_file(path,self.data,self.pending_identity,(2,),'Clock pending marker')
        return info
    def check_active(self):
        info=owned_file(self.path,self.data,self.identity,(1,2),'Clock active lease')
        if info.st_nlink==2:
            self.check_pending()
            info=owned_file(self.path,self.data,self.identity,(2,),'Clock linked active lease')
        return info
    def release(self,record):
        require(record.get('original_flash_and_factory_verified') is True and
                record.get('owned_processes_closed') is True,'Incomplete recovery retains the session lease')
        backend.session_lease(self.profile);self.check_active()
        self.path.unlink();capture.sync_directory(self.path.parent)
    def pending(self):
        """Persist, then requalify this exact created/linked shared refusal."""
        path=self.pending_path
        try:path.lstat()
        except FileNotFoundError:
            try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            except OSError:
                backend.session_lease(self.profile)
                require(self.path.parent==path.parent,'Clock pending link directory differs')
                owned_file(self.path,self.data,self.identity,(1,),'Clock pending link source')
                os.link(self.path,path,follow_symlinks=False)
                self.pending_linked_identity=self.identity;self.pending_identity=self.identity
            else:
                with os.fdopen(fd,'wb') as stream:
                    info=os.fstat(stream.fileno());self.pending_identity=(info.st_dev,info.st_ino)
                    capture.durable(stream,self.data)
        # An existing same-byte file without original inode authority refuses.
        self.check_pending()
        capture.sync_directory(path.parent)
        self.check_pending() # The last sync may have changed the path.
    def clear_pending(self):
        self.pending()
        # No directory sync or other fallible effect follows this fresh check
        # before unlinking only our exact marker.
        self.check_pending();self.pending_path.unlink()
        del self.pending_identity
        if hasattr(self,'pending_linked_identity'):del self.pending_linked_identity
        capture.sync_directory(self.pending_path.parent)
    def retain(self):
        try:
            backend.session_lease(self.profile);self.check_active()
        except FileNotFoundError:
            with os.fdopen(os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600),'wb') as stream:
                info=os.fstat(stream.fileno());self.identity=(info.st_dev,info.st_ino)
                capture.durable(stream,self.data)
        capture.sync_directory(self.path.parent);self.check_active()

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
    require(bool(backend.QUALIFIED),'No committed qualification admits a physical clock measurement episode')
    tools=runtime.select();runtime.activate(tools)
    profile=backend.artifact(args.artifact)
    profile.update(nonce=os.urandom(16).hex())
    profile.update(trial.original_binding(args.binding,args.baseline_a,args.baseline_b))
    qualification=trial.private_file(args.qualification,'.scratch')
    require(0<qualification.stat().st_size<=1024*1024,'Bounded qualification receipt required')
    profile.update(qualification_path=str(qualification),qualification_sha256=trial.sha(qualification),
                   backend_source_sha256=trial.sha(ROOT/'tools/forgix_clock_backend.py'),
                   coordinator_source_sha256=trial.sha(ROOT/'tools/run_forgix_clock_trial.py'))
    frozen=freeze()
    environment=runtime.image_check(args.image_id,tools)
    profile.update(execution_sha256=backend.digest({n:h for n,h in frozen['inputs'].items() if n!=REGISTRY}),
                   environment_sha256=backend.digest(environment))
    backend.qualified(profile)
    backend.qualification_receipt(profile,environment,frozen)
    private=trial.no_symlinks(args.private_dir)
    require(private.parent==ROOT/'backups' and not private.exists(),'Fresh direct backups child required')
    require(subprocess.run(['git','check-ignore','--quiet',str(private)],cwd=ROOT,timeout=10).returncode==0,
            'Private output must be Git ignored')
    return profile,environment,frozen,private

class LockHandle:
    def __init__(self,fd):
        self.fd=fd;self.closed=False;self.kernel_release=False
        info=os.fstat(fd);self.identity=(info.st_dev,info.st_ino)
        self.flock_line=self._flock_line()
    def _flock_line(self):
        lines=[line for line in Path(f'/proc/self/fdinfo/{self.fd}').read_text().splitlines()
               if re.match(r'^lock:\s+\S+\s+FLOCK\s+ADVISORY\s+WRITE\s+',line)]
        require(len(lines)==1,'Original operator FD lacks exact exclusive flock')
        return lines[0]
    def check(self):
        require(not self.closed,'Original operator FD was closed')
        info=os.fstat(self.fd)
        require((info.st_dev,info.st_ino)==self.identity and self._flock_line()==self.flock_line,
                'Original operator FD identity or flock differs')
    def stage_kernel_release(self):
        self.check();self.kernel_release=True
    def close(self):
        # Only pre-finalization owners use explicit close. Never retry or act on
        # a numeric descriptor after a possibly consumed close.
        if not self.closed and not self.kernel_release:
            self.check();self.closed=True;os.close(self.fd)

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
            require(not (ROOT/backend.LEASE).exists(),'Unresolved clock session lease blocks device access')
        else:backend.session_lease(recovery_profile)
        holder=LockHandle(fd)
        try:yield holder
        finally:holder.close()
    except BaseException:
        # Ownership before constructing holder remains local.
        if 'holder' not in locals():os.close(fd)
        raise

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
        if failure is None and summary and summary.get('status')=='clock_completed' and record['original_flash_and_factory_verified']:
            record['status']='clock_episode_observed'
        if failure is not None:record['failure_kind']=type(failure).__name__
        capture.save(store,'session.json',record)
        # Final durable receipt is inside the acceptance bound too. If its I/O
        # crosses the deadline, atomically retain an authoritative failure.
        if clock()-began>=600 and record['status']=='clock_episode_observed':
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
    require(prior.get('status') in ('failed','clock_episode_completed'),'Unexpected original terminal status')
    old=prior['profile_private']
    require(old.get('session_private_dir')==str(path.parent),'Prior lease directory differs')
    require(prior['execution']['inputs']==frozen['inputs'] and backend.digest(prior['environment_private'])==backend.digest(environment),
            'Recovery must use identical frozen execution/runtime')
    for name in ('elf','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','qualification_sha256',
                 'execution_sha256','environment_sha256','uid_sha256','baseline_sha256','baseline_paths','binding_sha256',
                 'configuration','artifact_exports','contract_sha256','startup_audit_sha256'):
        require(type(old.get(name)) is type(profile[name]) and old[name]==profile[name],'Original recovery tuple differs: '+name)
    profile.update({n:old[n] for n in ('nonce','session_private_dir','session_lease_sha256')})
    backend.session_lease(profile,path.parent)
    return prior

def execute_recovery(adapter,store,preflight,clock=time.monotonic,began=None):
    began=clock() if began is None else began;deadline=began+600
    record=dict(preflight,status='failed',flash_write_operations=0,ram_load_operations=0,
                configuration_start_operations=0,original_flash_and_factory_verified=False,
                owned_processes_closed=False,physical_measurement_acceptance='failed observation remains failed')
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

def replace_session(store,name,record):
    capture.save(store,name,record)
    os.replace(store.path/name,store.path/'session.json');capture.sync_directory(store.path)

def terminal_failure(lease,store,record,error,began,clock=time.monotonic):
    """Failed storage cannot qualify earlier staged normal facts."""
    record.update(status='failed',finalization_status='failed',invocation_qualification=False,
                  terminal_failure_kind=type(error).__name__,
                  shared_refusal_retained=False)
    record.setdefault('failure_kind',type(error).__name__)
    try:
        elapsed=clock()-began;record['host_elapsed_seconds']=elapsed
        if elapsed>=600:record['deadline_exceeded']=True
    except BaseException as failure:record['terminal_clock_failure_kind']=type(failure).__name__
    retained=False
    try:lease.pending();retained=True
    except BaseException as failure:record['pending_retention_failure_kind']=type(failure).__name__
    try:lease.retain();record['lease_release_status']='retained'
    except BaseException as failure:record['lease_retention_failure_kind']=type(failure).__name__
    try:replace_session(store,'terminal-failed-session.json',record)
    except BaseException as failure:record['corrective_persistence_failure_kind']=type(failure).__name__
    try:
        lease.check_pending();record['shared_refusal_retained']=retained
    except BaseException as failure:
        record['shared_refusal_retained']=False;record['pending_revalidation_failure_kind']=type(failure).__name__

def finalize(lease,store,record,began,lock,clock=time.monotonic,defer_pending=False):
    """Stage normal facts while retaining the original FD for kernel teardown.

    This callable cannot attest to its future process exit. The pending marker
    stays through every fallible terminal effect; only terminal_output clears it.
    The legacy defer_pending argument never permits an early release.
    """
    candidate=record.get('status') in ('clock_episode_observed','recovered_and_verified')
    success='recovered_and_verified' if record.get('recovery_only') else 'clock_episode_completed'
    record.update(status='pending_finalization' if candidate else 'failed',finalization_status='pending',
                  finalization_candidate_status=success if candidate else None,
                  invocation_qualification=False,external_cli_exit_required=True,
                  operator_lock_release='staged final kernel process teardown')
    def within():lock.check();require(clock()<began+600,'Whole clock acceptance deadline expired')
    lock.stage_kernel_release()
    try:
        # Establish refusal before receipt I/O, not after its possible failure.
        lease.pending();record['shared_refusal_retained']=True;within()
        capture.save(store,'finalization-intent.json',record);within()
        if record.get('original_flash_and_factory_verified') is True and record.get('owned_processes_closed') is True:
            lease.release(record);record['lease_release_status']='released'
        else:
            candidate=False;record['finalization_candidate_status']=None;record['lease_release_status']='retained'
        within();replace_session(store,'final-session-pending.json',record);within()
    except BaseException as primary:
        terminal_failure(lease,store,record,primary,began,clock)
        if not isinstance(primary,Exception):raise
    return record

def terminal_output(lease,store,record,began,cancelled,clock=time.monotonic,lock=None):
    """All user-space effects precede the final original-FD kernel release."""
    def within():
        require(lock is not None,'Original held clock operator required')
        lock.check()
        require(clock()<began+600 and not cancelled['requested'],'Terminal cancelled or expired')
    try:
        within()
        print(json.dumps({k:record.get(k) for k in ('status','failure_kind','original_flash_and_factory_verified','owned_processes_closed')}),flush=True)
        within();record['terminal_output_returned_s']=clock()
        if record.get('finalization_candidate_status') and record.get('status')=='pending_finalization':
            record.update(status=record['finalization_candidate_status'],finalization_status='staged_kernel_exit')
        replace_session(store,'terminal-staged-session.json',record);within()
        if record.get('status') in ('clock_episode_completed','recovered_and_verified'):
            lease.clear_pending();within()
    except BaseException as error:terminal_failure(lease,store,record,error,began,clock)
    return record

def quarantine(lock,lease,store,record,began,clock=time.monotonic):
    """No new keeper or clock: the exact existing owner refuses handoff."""
    verified=False
    try:lock.check();verified=True
    except BaseException as error:
        # Inspection failure must not unwind this owner. Do not claim that
        # uncertain/consumed descriptor authority is an exact held flock.
        record['quarantine_operator_check_failure_kind']=type(error).__name__
    record.update(status='failed',finalization_status='quarantined_held_operator' if verified else 'quarantined_unverified_operator',
                  invocation_qualification=False,operator_lock_retained=verified,
                  quarantine_owner_pid=os.getpid(),quarantine_operator_fd=lock.fd,
                  quarantine_operator_identity={'device':lock.identity[0],'inode':lock.identity[1]})
    try:replace_session(store,'clock-quarantine.json',record)
    except BaseException:pass
    try:print(json.dumps({'status':'failed','operator_lock_retained':verified,'quarantine':True}),flush=True)
    except BaseException:pass
    while True:
        try:time.sleep(1)
        except BaseException:pass # Only explicit operator investigation may end it.

def parser():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action',choices=('preflight','run','recover'))
    cli.add_argument('--prior-session',type=Path)
    cli.add_argument('--artifact',required=True,type=Path)
    cli.add_argument('--binding',required=True,type=Path)
    cli.add_argument('--baseline-a',required=True,type=Path)
    cli.add_argument('--baseline-b',required=True,type=Path)
    cli.add_argument('--qualification',required=True,type=Path)
    cli.add_argument('--private-dir',required=True,type=Path)
    cli.add_argument('--image-id',default=os.environ.get('PICOTOOL_CONTAINER_IMAGE_ID'))
    return cli

def main(*,kernel_exit=False):
    os.umask(0o077);args=parser().parse_args();adapter=None;record={'status':'refused'}
    lease=store=None;began=None;cancelled={'requested':False,'terminal':False}
    def cancel(signum,frame):
        cancelled['requested']=True
        if cancelled['terminal']:return
        if adapter is not None and adapter.cleaning:
            print('Cancellation deferred during bounded factory/full-flash cleanup.',flush=True)
        else:raise Cancelled('Clock episode cancelled')
    handlers={s:signal.signal(s,cancel) for s in (signal.SIGINT,signal.SIGTERM)}
    try:
        profile,environment,frozen,private=prepare(args)
        if args.action=='preflight':
            record={'status':'preflight_passed','physical_execution_requested':False}
        else:
            prior=None
            if args.action=='recover':
                require(args.prior_session is not None,'Recovery requires original terminal receipt')
                prior=recovery_admission(args.prior_session,profile,environment,frozen)
            with operator_lock(profile if prior is not None else None) as lock:
                backend.frozen_inputs(frozen);backend.qualified(profile);runtime.check(environment)
                began=time.monotonic()
                if prior is not None:recovery_admission(args.prior_session,profile,environment,frozen)
                # From the first fallible pre-access construction onward, the
                # original FD stays here through failure settlement and exit.
                lock.stage_kernel_release()
                try:
                    adapter=(backend.RecoveryBackend if prior is not None else backend.Backend)(profile,private,lock.fd,environment,frozen)
                    store=ReceiptStore(private)
                    if prior is None:
                        # Retain creation authority even if initial durability
                        # fails after the exclusive file creation.
                        lease=object.__new__(SessionLease)
                        SessionLease.__init__(lease,profile,private)
                    else:
                        lease=SessionLease.rotate(profile,private)
                        adapter.lease_private=private
                    execution_error=None
                    try:
                        produced=(execute_recovery if prior is not None else execute)(adapter,store,{
                            'kind':'identity-selected Forgix clock measurement episode',
                            'profile_private':profile,'environment_private':environment,'execution':frozen,
                            'physical_execution_requested':True,'recovery_only':prior is not None,
                            'prior_session_sha256':trial.sha(args.prior_session) if prior is not None else None},began=began)
                        require(type(produced) is dict,'Clock execution returned an invalid record')
                        record=produced
                    except BaseException as error:
                        execution_error=error;record.update(status='failed',failure_kind=type(error).__name__)
                    cancelled['terminal']=True
                    terminal=trial.no_symlinks(private/'session.json')
                    require(terminal.is_file() and terminal.stat().st_size<=4*1024*1024,
                            'Bounded saved clock session required')
                    saved=json.loads(terminal.read_bytes())
                    require(type(saved) is dict,'Saved clock session must be a record')
                    require(saved.get('status') in ('failed','clock_episode_observed','recovered_and_verified')
                            and type(saved.get('owned_processes_closed')) is bool
                            and type(saved.get('original_flash_and_factory_verified')) is bool
                            and saved.get('physical_execution_requested') is True
                            and type(saved.get('recovery_only')) is bool
                            and all(type(saved.get(name)) is dict for name in
                                    ('profile_private','environment_private','execution')),
                            'Saved clock session schema differs')
                    if execution_error is None:
                        require(saved==record,'Saved clock session differs from live execution facts')
                    # Parsed storage never replaces the live failure state.
                    if execution_error is not None or cancelled['requested']:
                        record.update(status='failed',failure_kind=type(execution_error).__name__ if execution_error is not None else 'Cancelled')
                    finalize(lease,store,record,began,lock,defer_pending=True)
                    record['cancellation_requested']=cancelled['requested']
                    terminal_output(lease,store,record,began,cancelled,clock=time.monotonic,lock=lock)
                    lock.check()
                    if record['status'] in ('clock_episode_completed','recovered_and_verified'):
                        trial.reject_pending_finalization(ROOT)
                        require(not lease.path.exists(),'Clock active lease remains before final exit')
                    else:
                        # Never trust a flag from earlier fallible receipt I/O.
                        lease.check_pending()
                        require(record.get('shared_refusal_retained') is True,'Exact durable shared refusal required')
                    require(time.monotonic()<began+600 and not cancelled['requested'],
                            'Final kernel exit cancelled or expired')
                except BaseException as error:
                    cancelled['terminal']=True
                    try:terminal_failure(lease,store,record,error,began)
                    except BaseException as secondary:
                        # A secondary handler fault cannot turn unknown closure
                        # into an ordinary unguarded exception exit.
                        record.update(status='failed',shared_refusal_retained=False,
                                      failure_settlement_kind=type(secondary).__name__)
                        record.setdefault('failure_kind',type(error).__name__)
                    if not record.get('shared_refusal_retained'):
                        quarantine(lock,lease,store,record,began)
                    # Revalidate after all failure persistence effects. Any
                    # further exception stays with the same original owner.
                    try:lease.check_pending()
                    except BaseException:
                        record['shared_refusal_retained']=False
                        quarantine(lock,lease,store,record,began)
                # No handler restoration, receipt or explicit last-FD close
                # follows the terminal ownership/deadline/cancellation checks.
                if kernel_exit:os._exit(0 if record['status'] in ('clock_episode_completed','recovered_and_verified') else 2)
                return 2 # A callable return does not observe kernel teardown.
    except BaseException as exc:
        record.update(status='refused' if adapter is None else 'failed',failure_kind=type(exc).__name__)
    finally:
        if not cancelled['terminal']:
            record['cancellation_requested']=cancelled['requested']
            try:print(json.dumps({k:record.get(k) for k in ('status','failure_kind','original_flash_and_factory_verified','owned_processes_closed')}),flush=True)
            except BaseException as error:record.update(status='failed',failure_kind=type(error).__name__)
            for signum,handler in handlers.items():signal.signal(signum,handler)
    return 0 if record['status']=='preflight_passed' else 2

if __name__=='__main__':raise SystemExit(main(kernel_exit=True))

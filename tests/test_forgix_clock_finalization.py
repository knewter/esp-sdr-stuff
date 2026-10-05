"""Clock terminal staging with actual owned files/flocks/processes, no hardware.

Only fixture lifecycle/registry/runtime and named failure boundaries are modeled.
Actual subprocess join supplies exit/deadline/group/FD/refusal/flock observations.
"""
import contextlib,fcntl,json,os,selectors,signal,subprocess,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import run_forgix_clock_trial as c
import forgix_clock_backend as b
from test_forgix_clock_production import Model


def fixture(root,mode):
    (root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700)
    private=root/'backups/run';private.mkdir(mode=0o700)
    profile={n:'1'*64 for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256',
        'bridge_source_sha256','bitstream_sha256','qualification_sha256','execution_sha256',
        'environment_sha256','contract_sha256')};profile['nonce']='2'*32
    action='recover' if mode.startswith('recovery') else 'run'
    args=types.SimpleNamespace(action=action,prior_session=None)
    model=Model('unknown' if mode.startswith('unknown') else 'failure' if mode=='known-failure' else None)
    model.profile.update(profile)
    realopen=os.open;realsync=c.capture.sync_directory;realsave=c.capture.save
    realprint=print;realclose=os.close;realfsync=os.fsync;actualexecute=c.execute;actualfinalize=c.finalize;actualclear=c.SessionLease.clear_pending;clearing=[False]
    pending=root/'.scratch/forgix-spi-finalization-pending.json';fault=[False];delta=[0.0];realmonotonic=time.monotonic;start=realmonotonic()
    def now():
        # Real original clock in ordinary controls. Exact-boundary failures use
        # the separately declared controlled clock, not a fresh acceptance cap.
        return start+delta[0] if mode in ('late-marker','late-stdout') else realmonotonic()
    if mode=='cleanup-cancel':
        original=model.return_factory
        def factory(until):signal.raise_signal(signal.SIGTERM);return original(until)
        model.return_factory=factory
    def fsync(fd):
        if mode=='session-fsync' and os.readlink(f'/proc/self/fd/{fd}').endswith('/session.json'):
            raise OSError('explicit initial session fsync failure')
        return realfsync(fd)
    def opened(path,*a,**kw):
        if Path(path)==pending and (mode.startswith('unknown') or fault[0]) and a and a[0]&os.O_CREAT:
            raise OSError('explicit pending creation failure; validation reads remain available')
        if Path(path)==root/b.LEASE and fault[0]:raise OSError('fixture corrective lease open fails')
        return realopen(path,*a,**kw)
    def synced(path):
        if mode in ('substitution','recovery-substitution') and clearing[0] and Path(path)==pending.parent and pending.exists() and not fault[0]:
            pending.rename(root/'.scratch/original-marker');pending.write_bytes((root/'.scratch/original-marker').read_bytes());os.chmod(pending,0o600);fault[0]=True
        if mode=='initial-active-substitution' and Path(path)==pending.parent and (root/b.LEASE).exists() and not fault[0]:
            active=root/b.LEASE;active.rename(root/'.scratch/original-active');active.write_bytes((root/'.scratch/original-active').read_bytes());os.chmod(active,0o600);fault[0]=True
        if mode in ('last-sync','last-sync-restorable') and Path(path)==root/'.scratch' and not pending.exists() and not(root/b.LEASE).exists():
            fault[0]=mode=='last-sync';raise OSError('fixture post-marker-unlink sync fails')
        if mode=='sync-cancel' and Path(path)==root/'.scratch' and not pending.exists() and not(root/b.LEASE).exists():
            signal.raise_signal(signal.SIGINT)
        if mode=='late-marker' and Path(path)==root/'.scratch' and not pending.exists() and not(root/b.LEASE).exists():delta[0]=600.0
        return realsync(path)
    def saved(store,name,value):
        if fault[0] or mode=='all-storage' and name!='preflight.json':raise OSError('fixture terminal storage fails')
        result=realsave(store,name,value)
        if name=='session.json' and mode.startswith('malformed-'):
            values={'list':[],'null':None,'scalar':1,'dict':{},'status':dict(value,status='clock_episode_completed')}
            (store.path/name).write_text(json.dumps(values[mode.removeprefix('malformed-')]))
        if name=='session.json' and mode=='first-foreign':
            pending.write_bytes((root/b.LEASE).read_bytes());os.chmod(pending,0o600)
        return result
    def clear(lease):
        clearing[0]=True
        try:return actualclear(lease)
        finally:clearing[0]=False
    def printing(*args,**kwargs):
        if mode=='fd-reuse':
            owned=[p for p in Path('/proc/self/fd').iterdir() if p.exists() and p.resolve()==root/'.scratch/esp-demo.lock']
            assert len(owned)==1
            number=int(owned[0].name);realclose(number)
            replacement=realopen(root/'foreign-descriptor',os.O_CREAT|os.O_RDWR,0o600)
            assert replacement==number
            os.write(replacement,b'foreign descriptor remains untouched')
        if mode=='stdout-error':raise OSError('fixture stdout fails')
        if mode=='stdout-cancel':signal.raise_signal(signal.SIGTERM)
        if mode=='late-stdout':delta[0]=600.0
        return realprint(*args,**kwargs)
    def make_backend(*args,**kwargs):
        # One actual inherited-flock worker joins before terminal finalization.
        fd=args[2];lock=root/'.scratch/esp-demo.lock'
        from forgix_spi_lifecycle import WorkerOwner
        workers=private/'workers';workers.mkdir(mode=0o700)
        owner=WorkerOwner(workers,fd,lock);model.owner=owner
        original=model.observe
        def observe(until):
            owner.run([sys.executable,'-c',"import os,sys;from pathlib import Path;Path(sys.argv[1]).write_text(str(os.getpid()))",str(root/'worker.pid')],
                      'host-owned',time.monotonic()+5)
            return original(until)
        model.observe=observe
        return model
    with contextlib.ExitStack() as stack:
        for module in (c,b,c.trial):stack.enter_context(patch.object(module,'ROOT',root))
        if action=='recover':
            prior=root/'backups/prior';prior.mkdir(mode=0o700)
            c.SessionLease(profile,prior);args.prior_session=prior/'session.json';args.prior_session.write_text('{}');os.chmod(args.prior_session,0o600)
            stack.enter_context(patch.object(c,'recovery_admission',return_value={'explicit_fixture':'no physical qualification'}))
        stack.enter_context(patch.object(c,'parser',return_value=types.SimpleNamespace(parse_args=lambda:args)))
        stack.enter_context(patch.object(c,'prepare',return_value=(profile,{}, {'inputs':{}},private)))
        stack.enter_context(patch.object(b,'Backend',side_effect=make_backend));stack.enter_context(patch.object(b,'RecoveryBackend',side_effect=make_backend))
        stack.enter_context(patch.object(b,'frozen_inputs'));stack.enter_context(patch.object(b,'qualified'));stack.enter_context(patch.object(c.runtime,'check'))
        stack.enter_context(patch.object(c.time,'monotonic',side_effect=now))
        stack.enter_context(patch.object(c,'execute',side_effect=lambda *a,**kw:actualexecute(*a,clock=now,**kw)))
        stack.enter_context(patch.object(c.SessionLease,'clear_pending',autospec=True,side_effect=clear))
        if mode=='quarantine-check-error':
            original_check=c.LockHandle.check
            def checking(lock):
                if (private/'terminal-staged-session.json').exists() or (private/'session.json').exists():raise OSError('explicit fdinfo inspection failure; original FD stays live')
                return original_check(lock)
            stack.enter_context(patch.object(c.LockHandle,'check',new=checking))
            stack.enter_context(patch.object(c.SessionLease,'pending',side_effect=OSError('explicit marker retention failure')))
        if mode=='settlement-error':
            stack.enter_context(patch.object(c,'terminal_failure',side_effect=OSError('explicit secondary failure-handler fault')))
            stack.enter_context(patch.object(c,'terminal_output',side_effect=OSError('explicit primary terminal fault')))
        if mode=='store-error':stack.enter_context(patch.object(c,'ReceiptStore',side_effect=OSError('explicit pre-access store fault')))
        stack.enter_context(patch.object(c,'finalize',side_effect=lambda *a,**kw:actualfinalize(*a,clock=now,**kw)))
        stack.enter_context(patch.object(os,'fsync',side_effect=fsync));stack.enter_context(patch.object(os,'open',side_effect=opened));stack.enter_context(patch.object(c.capture,'sync_directory',side_effect=synced))
        stack.enter_context(patch.object(c.capture,'save',side_effect=saved));stack.enter_context(patch('builtins.print',side_effect=printing))
        if mode=='unknown-double':stack.enter_context(patch.object(os,'link',side_effect=OSError('fixture link fails')))
        # Original-FD final close is forbidden: any call is an explicit fixture failure.
        stack.enter_context(patch.object(c.LockHandle,'close',side_effect=AssertionError('explicit original-FD final close forbidden')))
        c.main(kernel_exit=True)
    raise AssertionError('Actual kernel exit did not happen')


class Finalization(unittest.TestCase):
    def subprocess_control(self,mode,quarantine=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);began=time.monotonic()
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--fixture',str(root),mode],
                                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
            try:
                if quarantine:
                    # Terminal storage itself is faulted: stdout and actual
                    # /proc/flock ownership, not a pretend journal, observe it.
                    selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
                    until=time.monotonic()+8;quarantined=False
                    try:
                        while time.monotonic()<until:
                            for key,events in selector.select(.05):
                                line=key.fileobj.readline()
                                if line:
                                    try:observed=json.loads(line)
                                    except ValueError:continue
                                    if observed.get('quarantine') is True:quarantined=True;break
                            if quarantined:break
                            if proc.poll() is not None:self.fail('Quarantine exited before explicit fixture cleanup')
                    finally:selector.close()
                    self.assertTrue(quarantined,'Quarantine did not emit retained-owner observation')
                    self.assertIsNone(proc.poll());self.assertEqual(observed['status'],'failed')
                    fd=os.open(root/'.scratch/esp-demo.lock',os.O_RDWR)
                    try:
                        with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        owned=[p for p in Path(f'/proc/{proc.pid}/fd').iterdir()
                               if p.resolve()==root/'.scratch/esp-demo.lock']
                        self.assertEqual(len(owned),1)
                        self.assertIn('FLOCK',Path(f'/proc/{proc.pid}/fdinfo/{owned[0].name}').read_text())
                    finally:os.close(fd)
                    # Explicit fixture teardown, never automatic recovery.
                    proc.kill()
            except BaseException:
                if proc.poll() is None:proc.kill()
                proc.communicate(timeout=10)
                raise
            try:out,err=proc.communicate(timeout=10)
            except BaseException:
                if proc.poll() is None:proc.kill()
                proc.communicate(timeout=10)
                raise
            self.assertLess(time.monotonic()-began,600)
            self.assertFalse(Path('/proc',str(proc.pid)).exists())
            with self.assertRaises(ProcessLookupError):os.killpg(proc.pid,0)
            worker=root/'worker.pid'
            if worker.exists():self.assertFalse(Path('/proc',worker.read_text()).exists())
            session=root/'backups/run/session.json'
            r=json.loads(session.read_bytes()) if session.exists() else {'status':'failed','fixture_receipt_absent':True}
            pending=root/'.scratch/forgix-spi-finalization-pending.json'
            fd=os.open(root/'.scratch/esp-demo.lock',os.O_RDWR)
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            finally:os.close(fd)
            if mode in ('normal','recovery'):
                self.assertEqual(proc.returncode,0,err);self.assertFalse(pending.exists());self.assertFalse((root/b.LEASE).exists())
                self.assertEqual(r['status'],'recovered_and_verified' if mode=='recovery' else 'clock_episode_completed')
                self.assertEqual(r['finalization_status'],'staged_kernel_exit');self.assertFalse(r['invocation_qualification']);self.assertTrue(r['external_cli_exit_required'])
                self.assertNotIn('root_lock_fd_close_returned_s',r)
            elif quarantine:
                self.assertEqual(proc.returncode,-signal.SIGKILL)
                self.assertFalse(r.get('invocation_qualification',False))
                if mode in ('substitution','recovery-substitution','first-foreign'):self.assertTrue(pending.exists())
            else:
                self.assertEqual(proc.returncode,2,err);self.assertEqual(r['status'],'failed');self.assertTrue(pending.exists())
                with self.assertRaises(ValueError):c.trial.reject_pending_finalization(root)
            joined={'mode':mode,'actual_child_exit':proc.returncode,'actual_join_elapsed_seconds':time.monotonic()-began,
                    'within_original_600_seconds':time.monotonic()-began<600,'coordinator_proc_absent':True,
                    'original_group_absent':True,'worker_proc_absent':not worker.exists() or not Path('/proc',worker.read_text()).exists(),
                    'actual_flock_reacquired_after_join':True,'shared_marker_present':pending.exists(),
                    'saved_status':r['status'],'saved_finalization_status':r.get('finalization_status'),
                    'saved_invocation_qualification':r.get('invocation_qualification'),
                    'ordinary_control_uses_real_original_monotonic_clock':mode not in ('late-marker','late-stdout'),
                    'quarantine_ended_only_by_explicit_fixture_SIGKILL':quarantine,
                    'lifecycle_artifact_registry_runtime_boundary':'explicit injected no-hardware model'}
            print(json.dumps({'actual_clock_kernel_join':joined},sort_keys=True))
            destination=os.environ.get('CLOCK_HOST_JOIN_OUTPUT')
            if destination:
                folder=Path(destination);self.assertTrue(folder.resolve().is_relative_to(ROOT/'.scratch'))
                folder.mkdir(parents=True,exist_ok=True,mode=0o700)
                (folder/(mode+'.json')).write_text(json.dumps({'join':joined,'saved_session':r,'stdout':out,'stderr':err},indent=2)+'\n')
            return r
    def test_full_run_foreign_last_sync_inode_quarantines(self):self.subprocess_control('substitution',True)
    def test_full_recovery_foreign_last_sync_inode_quarantines(self):self.subprocess_control('recovery-substitution',True)
    def test_existing_same_bytes_first_marker_is_not_adopted(self):self.subprocess_control('first-foreign',True)
    def test_malformed_saved_record_never_overwrites_live_state(self):
        for kind in ('list','null','scalar','dict','status'):
            with self.subTest(kind=kind):self.subprocess_control('malformed-'+kind)
    def test_quarantine_inspection_fault_never_unwinds_original_owner(self):self.subprocess_control('quarantine-check-error',True)
    def test_secondary_failure_handler_fault_retains_original_owner(self):self.subprocess_control('settlement-error',True)
    def test_pre_access_store_fault_quarantines_original_owner(self):self.subprocess_control('store-error',True)
    def test_initial_active_inode_substitution_refuses_without_adoption(self):self.subprocess_control('initial-active-substitution',True)

    def test_actual_kernel_teardown_run_join(self):self.subprocess_control('normal')
    def test_actual_kernel_teardown_recovery_join(self):self.subprocess_control('recovery')
    def test_known_failed_observation_exits_failed_with_refusal(self):self.subprocess_control('known-failure')
    def test_unknown_marker_open_uses_actual_owned_lease_hardlink(self):self.subprocess_control('unknown-marker')
    def test_unknown_double_fault_retains_original_fd_until_explicit_fixture_cleanup(self):self.subprocess_control('unknown-double',True)
    def test_known_closed_post_unlink_double_fault_retains_original_fd(self):self.subprocess_control('last-sync',True)
    def test_post_unlink_sync_failure_restores_durable_marker(self):self.subprocess_control('last-sync-restorable')
    def test_terminal_fd_reuse_retains_refusal_and_exits_failed(self):self.subprocess_control('fd-reuse')
    def test_terminal_stdout_fault(self):self.subprocess_control('stdout-error')
    def test_terminal_stdout_cancellation(self):self.subprocess_control('stdout-cancel')
    def test_last_marker_sync_cancellation_latched(self):self.subprocess_control('sync-cancel')
    def test_terminal_stdout_exact_deadline(self):self.subprocess_control('late-stdout')
    def test_last_marker_exact_deadline(self):self.subprocess_control('late-marker')

    @contextlib.contextmanager
    def owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir(mode=0o700);(root/'backups').mkdir(mode=0o700);private=root/'backups/run';private.mkdir(mode=0o700)
            profile={n:'1'*64 for n in ('uid_sha256','baseline_sha256','elf_sha256','manifest_sha256','bridge_source_sha256','bitstream_sha256','qualification_sha256','execution_sha256','environment_sha256','contract_sha256')};profile['nonce']='2'*32
            with patch.object(c,'ROOT',root),patch.object(b,'ROOT',root),patch.object(c.trial,'ROOT',root):
                lease=c.SessionLease(profile,private);fd=os.open(root/'.scratch/esp-demo.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX);lock=c.LockHandle(fd)
                try:yield root,private,lease,lock
                finally:
                    # Only this explicit fixture owns this FD, after its assertions.
                    if not lock.closed:
                        try:os.close(fd)
                        except OSError:pass
    def test_pending_owner_mode_inode_symlink_and_link_substitution_refuse(self):
        for mode in ('bytes','inode','symlink','links','permissions'):
            with self.subTest(mode=mode),self.owned() as (root,private,lease,lock):
                lease.pending();p=lease.pending_path
                if mode=='bytes':p.write_bytes(b'foreign')
                elif mode=='inode':p.rename(root/'.scratch/original-marker');p.write_bytes(lease.data);os.chmod(p,0o600)
                elif mode=='symlink':p.unlink();p.symlink_to(lease.path)
                elif mode=='links':os.link(p,root/'.scratch/foreign')
                else:os.chmod(p,0o644)
                with self.assertRaises(ValueError):lease.clear_pending()
                self.assertTrue(p.exists());lock.check()
    def test_created_inode_is_revalidated_after_retain_sync(self):
        with self.owned() as (root,private,lease,lock):
            lease.path.unlink();original=c.capture.sync_directory
            def synced(path):
                lease.path.rename(root/'.scratch/retained-original');lease.path.write_bytes(lease.data);os.chmod(lease.path,0o600)
                return original(path)
            with patch.object(c.capture,'sync_directory',side_effect=synced),self.assertRaisesRegex(ValueError,'inode differs'):lease.retain()
            self.assertTrue(lease.path.exists());lock.check()
    def test_rotated_inode_is_revalidated_after_directory_sync(self):
        with self.owned() as (root,private,lease,lock):
            original=c.capture.sync_directory
            def synced(path):
                lease.path.rename(root/'.scratch/rotated-original');lease.path.write_bytes((root/'.scratch/rotated-original').read_bytes());os.chmod(lease.path,0o600)
                return original(path)
            with patch.object(c.capture,'sync_directory',side_effect=synced),self.assertRaisesRegex(ValueError,'inode differs'):c.SessionLease.rotate(lease.profile,private)
            self.assertTrue(lease.path.exists());lock.check()
    def test_release_revalidates_after_backend_fallible_check(self):
        with self.owned() as (root,private,lease,lock):
            original=b.session_lease
            def checked(profile):
                result=original(profile);lease.path.rename(root/'.scratch/released-original');lease.path.write_bytes(lease.data);os.chmod(lease.path,0o600);return result
            with patch.object(b,'session_lease',side_effect=checked),self.assertRaisesRegex(ValueError,'inode differs'):
                lease.release({'original_flash_and_factory_verified':True,'owned_processes_closed':True})
            self.assertTrue(lease.path.exists());lock.check()
    def test_first_foreign_same_bytes_marker_has_no_creation_authority(self):
        with self.owned() as (root,private,lease,lock):
            lease.pending_path.write_bytes(lease.data);os.chmod(lease.pending_path,0o600);before=lease.pending_path.stat()
            with self.assertRaisesRegex(ValueError,'creation authority'):lease.pending()
            self.assertEqual(lease.pending_path.stat().st_ino,before.st_ino);lock.check()
    def test_pending_bytes_changed_during_validation_refuse(self):
        with self.owned() as (root,private,lease,lock):
            lease.pending();original=Path.lstat;calls=[0]
            def checked(path,*args,**kwargs):
                if path==lease.pending_path:
                    calls[0]+=1
                    if calls[0]==2:path.write_bytes(b'x'*len(lease.data))
                return original(path,*args,**kwargs)
            with patch.object(Path,'lstat',new=checked),self.assertRaisesRegex(ValueError,'changed during validation'):lease.check_pending()
            lock.check()

    def test_clock_owned_marker_refuses_all_existing_shared_routes(self):
        import run_forgix_spi_trial as register,run_forgix_synthetic_trial as stream
        import forgix_usb_ram_capture as usb,preserve_forgix as preserve
        with self.owned() as (root,private,lease,lock):
            lease.pending();os.close(lock.fd);lock.closed=True
            with contextlib.ExitStack() as stack:
                for module,name in ((register,'ROOT'),(stream,'ROOT'),(usb,'REPO'),(preserve,'REPO')):
                    stack.enter_context(patch.object(module,name,root))
                entries=[lambda:c.prepare(types.SimpleNamespace()),lambda:c.recovery_admission(None,None,None,None),
                         lambda:register.prepare(types.SimpleNamespace()),lambda:stream.prepare(types.SimpleNamespace()),
                         lambda:stream.recovery_admission(None,None,None,None),lambda:c.trial.recovery_admission({},{}),
                         lambda:usb.open_retaining_serial('/unopened'),lambda:preserve.Inspector('3-3','/unopened').target(preserve.FACTORY_PID)]
                for entry in entries:
                    with self.assertRaisesRegex(ValueError,'finalization'):entry()
                for coordinator in (c,register,stream):
                    with self.assertRaisesRegex(ValueError,'finalization'):
                        with coordinator.operator_lock():self.fail('Clock marker admitted shared owner')
                with self.assertRaisesRegex(ValueError,'finalization'):
                    with c.operator_lock({'explicit_fixture':'matching recovery'}):self.fail('Clock marker admitted recovery')
    def test_marker_inode_substitution_during_initial_sync_refuses(self):
        with self.owned() as (root,private,lease,lock):
            original=c.capture.sync_directory;substituted=[False]
            def synced(path):
                if Path(path)==lease.pending_path.parent and not substituted[0]:
                    substituted[0]=True;p=lease.pending_path;p.rename(root/'.scratch/original-marker');p.write_bytes(lease.data);os.chmod(p,0o600)
                return original(path)
            with patch.object(c.capture,'sync_directory',side_effect=synced),self.assertRaisesRegex(ValueError,'inode differs'):lease.pending()
            lock.check();self.assertTrue(lease.pending_path.exists())
    def test_link_fallback_refuses_substituted_active_inode_and_extra_links(self):
        for mode in ('inode','links','bytes'):
            with self.subTest(mode=mode),self.owned() as (root,private,lease,lock):
                if mode=='inode':lease.path.rename(root/'.scratch/original-active');lease.path.write_bytes(lease.data);os.chmod(lease.path,0o600)
                elif mode=='links':os.link(lease.path,root/'.scratch/extra')
                else:lease.path.write_bytes(b'foreign')
                real=os.open
                def opened(path,*a,**kw):
                    if Path(path)==lease.pending_path:raise OSError('explicit pending open failure')
                    return real(path,*a,**kw)
                with patch.object(os,'open',side_effect=opened),self.assertRaises(ValueError):lease.pending()
                self.assertFalse(lease.pending_path.exists());lock.check()
    def test_descriptor_reuse_refuses_without_closing_reused_numeric_fd(self):
        with self.owned() as (root,private,lease,lock):
            old=lock.fd;os.close(old);foreign=root/'foreign';replacement=os.open(foreign,os.O_CREAT|os.O_RDWR,0o600)
            self.assertEqual(old,replacement)
            try:
                with self.assertRaises(ValueError):lock.stage_kernel_release()
                with self.assertRaises(ValueError):lock.close()
                os.write(replacement,b'unchanged ownership');self.assertEqual(foreign.read_bytes(),b'unchanged ownership')
            finally:os.close(replacement);lock.closed=True
    def test_reopened_same_inode_without_original_flock_refuses(self):
        with self.owned() as (root,private,lease,lock):
            old=lock.fd;os.close(old);replacement=os.open(root/'.scratch/esp-demo.lock',os.O_RDWR)
            self.assertEqual(old,replacement)
            try:
                with self.assertRaises(ValueError):lock.stage_kernel_release()
                os.fstat(replacement)
            finally:os.close(replacement);lock.closed=True

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--fixture':fixture(Path(sys.argv[2]),sys.argv[3])
    else:unittest.main(verbosity=2)

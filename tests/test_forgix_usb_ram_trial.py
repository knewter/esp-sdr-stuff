"""Lifecycle/identity/closure failures through synthetic dependencies only."""
import hashlib,io,json,os,stat,sys,tarfile,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import forgix_usb_ram_trial as m

class Guards(unittest.TestCase):
    def test_exact_ram_load_and_preservation_whitelist_unchanged(self):
        target=m.preserve.USBTarget('3-3',3,7,m.preserve.BOOT_PID,'synthetic')
        args=m.ram_load_args(target,Path('/private/ram-diagnostic.elf'))
        self.assertEqual(args,['load','-v','-x','/private/ram-diagnostic.elf','-t','elf','--bus','3','--address','7'])
        with self.assertRaises(m.preserve.PreservationError):m.preserve.picotool_args('load',target)
        with self.assertRaises(m.preserve.PreservationError):m.ram_load_args(target,Path('different.elf'))
        with self.assertRaises(m.preserve.PreservationError):m.ram_load_args(m.preserve.USBTarget('3-3',3,7,m.preserve.FACTORY_PID,'synthetic'),Path('ram-diagnostic.elf'))
    def test_original_binding_three_equal_prior_ids_and_two_full_copies(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'.scratch').mkdir();(root/'backups').mkdir()
            uid='a'*64;binding=root/'.scratch/binding.json'
            record={'matching_recent_enumerations':3,'same_serial_across_application_rom_application':True,'entries':[{'normalized_serial_sha256':uid} for _ in range(3)]}
            binding.write_text(json.dumps(record));binding.chmod(0o600)
            paths=[root/'backups'/name for name in ('a.bin','b.bin')]
            for p in paths:p.write_bytes(b'fixture');p.chmod(0o600)
            with patch.object(m,'ROOT',root),patch.object(m,'FLASH_BYTES',7),patch.object(m,'BASELINE',hashlib.sha256(b'fixture').hexdigest()):
                self.assertEqual(m.original_binding(binding,*paths)['uid_sha256'],uid)
                record['entries'][1]['normalized_serial_sha256']='b'*64;binding.write_text(json.dumps(record))
                with self.assertRaises(m.preserve.PreservationError):m.original_binding(binding,*paths)
                record['entries'][1]['normalized_serial_sha256']=uid;record['matching_recent_enumerations']=True;binding.write_text(json.dumps(record))
                with self.assertRaises(m.preserve.PreservationError):m.original_binding(binding,*paths)
    def test_private_ancestor_symlink_refused_without_external_changes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'real').mkdir();(root/'alias').symlink_to(root/'real')
            with self.assertRaises(m.preserve.PreservationError):m.no_symlinks(root/'alias/output')
            self.assertEqual(list((root/'real').iterdir()),[])
    def test_unknown_container_removal_blocks_later_access(self):
        inspector=Mock();store=Mock();store.path=Path('/private')
        runner=object.__new__(m.OwnedPicotool);runner.hardware_process_closed=False
        with patch.object(m,'check_inputs') as check,self.assertRaises(m.preserve.PreservationError):runner.run('boot',Mock())
        check.assert_not_called()
    def test_absolute_budget_refuses_expired(self):
        with patch.object(m.time,'monotonic',return_value=100):
            with self.assertRaises(m.preserve.PreservationError):m.remaining(100,15)
            self.assertEqual(m.remaining(103,15),3)
    def test_factory_wait_failure_bounded_and_no_mutation(self):
        inspector=Mock();inspector.target.side_effect=OSError()
        with patch.object(m.time,'monotonic',side_effect=[0,0,0,0,1]),patch.object(m.time,'sleep') as wait,self.assertRaises(m.preserve.PreservationError):m.watched_factory(inspector,3,.5)
        inspector.run.assert_not_called();wait.assert_called_once_with(.1)
    def test_owned_worker_always_whole_group_closure(self):
        with tempfile.TemporaryDirectory() as t:
            p=Mock();p.wait.side_effect=TimeoutError()
            with patch.object(m.subprocess,'Popen',return_value=p),patch.object(m,'stop_process') as close,self.assertRaises(TimeoutError):m.owned_worker(['synthetic'],Path(t)/'log',9,.1)
            close.assert_called_once_with(p,grace_seconds=3)
    def test_unknown_worker_closure_survives_marker_storage_failure(self):
        with tempfile.TemporaryDirectory() as t:
            p=Mock();p.wait.return_value=0
            with patch.object(m.subprocess,'Popen',return_value=p),patch.object(m,'stop_process',side_effect=OSError('synthetic')),patch.object(m,'mark_unclosed',side_effect=OSError('synthetic')),self.assertRaises(m.OwnedHardwareClosureError):m.owned_worker(['synthetic'],Path(t)/'log',9,.1)
    def test_unknown_container_closure_survives_all_storage_failures(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);tool=root/'picotool';tool.write_bytes(b'synthetic')
            store=Mock();store.path=root;store.json.side_effect=OSError('synthetic')
            inspector=Mock();p=Mock();p.wait.return_value=0
            runner=m.OwnedPicotool(str(tool),inspector,store,'sha256:'+'c'*64,{})
            target=m.preserve.USBTarget('3-3',3,7,m.preserve.FACTORY_PID,'synthetic')
            with patch.object(m,'check_inputs'),patch.object(m.preserve,'docker_command',return_value=['synthetic']),patch.object(m.subprocess,'Popen',return_value=p),patch.object(m,'stop_process'),patch.object(m,'remove_container',return_value=False),patch.object(m,'mark_unclosed',side_effect=OSError('synthetic')),self.assertRaises(m.OwnedHardwareClosureError):runner.run('boot',target)
            self.assertFalse(runner.hardware_process_closed)
    def test_spawn_window_cancellation_reaches_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            p=Mock()
            def spawn(*a,**k):
                os.kill(os.getpid(),m.signal.SIGINT)
                return p
            with patch.object(m.subprocess,'Popen',side_effect=spawn),patch.object(m,'stop_process') as close,self.assertRaises(KeyboardInterrupt):m.owned_worker(['synthetic'],Path(t)/'log',9,.1)
            close.assert_called_once_with(p,grace_seconds=3)
    def test_recovery_unknown_closure_refuses_before_any_device_operation(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m,'ROOT',Path(t)):
            for prior in ({'binding':{}},{'binding':{},'owned_hardware_processes_closed':False}):
                with self.assertRaises(m.preserve.PreservationError):m.recovery_admission(prior,{})
            m.recovery_admission({'binding':{},'owned_hardware_processes_closed':True},{})
            m.mark_unclosed({'container':'synthetic-only'})
            with self.assertRaises(m.preserve.PreservationError):m.recovery_admission({'binding':{},'owned_hardware_processes_closed':True},{})
    def test_factory_tty_renumbering_and_foreign_ancestry(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);usb=root/'bus/usb/devices/3-3';usb.mkdir(parents=True)
            for key,value in {'idVendor':'2e8a','idProduct':'0009'}.items():(usb/key).write_text(value)
            interface=usb/'3-3:1.0';interface.mkdir()
            ttys=root/'class/tty';ttys.mkdir(parents=True)
            dev=root/'dev';dev.mkdir()
            tty=ttys/'ttyACM8';tty.mkdir();(tty/'device').symlink_to(interface);(dev/'ttyACM8').touch()
            with patch.object(m.stat,'S_ISCHR',return_value=True):
                self.assertEqual(m.fresh_tty('3-3','2e8a','0009',sys_root=root,dev_root=dev),str(dev/'ttyACM8'))
                second=ttys/'ttyACM9';second.mkdir();(second/'device').symlink_to(interface);(dev/'ttyACM9').touch()
                with self.assertRaises(m.preserve.PreservationError):m.fresh_tty('3-3','2e8a','0009',sys_root=root,dev_root=dev)
    def test_image_archive_digest_and_tag_bound_without_docker(self):
        with tempfile.TemporaryDirectory() as t:
            archive=Path(t)/'image.tar';config=b'{"synthetic":true}'
            with tarfile.open(archive,'w') as tar:
                for name,data in [('manifest.json',json.dumps([{'RepoTags':['test:pinned'],'Config':'config.json'}]).encode()),('config.json',config)]:
                    info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
            self.assertEqual(m.archive_image_id(archive,'test:pinned'),'sha256:'+hashlib.sha256(config).hexdigest())
            with self.assertRaises(m.preserve.PreservationError):m.archive_image_id(archive,'test:other')
    def test_preservation_unknown_closure_survives_outer_receipt_failure(self):
        runner=Mock();runner.hardware_process_closed=True
        def broken(*args,**kwargs):runner.hardware_process_closed=False;raise OSError('synthetic receipt failure')
        with patch.object(m,'OwnedPicotool',return_value=runner),patch.object(m.preserve,'preserve',side_effect=broken),self.assertRaises(m.OwnedHardwareClosureError):m.full_preservation(Mock(),'synthetic',Mock(),'synthetic',{},9,time.monotonic()+1)

class LockedAdmission(unittest.TestCase):
    def invoke_main(self, root, action, flock_effect=None, input_effect=None):
        argv=['trial','--action',action,'--private-dir',str(root/'backups/new'),
              '--binding','synthetic','--baseline-a','synthetic','--baseline-b','synthetic']
        argv+=['--artifact','synthetic'] if action=='run' else ['--prior-session','synthetic']
        with patch.object(m,'ROOT',root),patch.object(m.sys,'argv',argv),\
             patch.object(m,'original_binding',return_value={}),patch.object(m,'artifact_check'),\
             patch.object(m,'image_check'),patch.object(m,'freeze_inputs',return_value={'inputs':{}}),\
             patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)),\
             patch.object(m.preserve,'PrivateStore',return_value=Mock()) as store,\
             patch.object(m.fcntl,'flock',side_effect=flock_effect),\
             patch.object(m,'check_inputs',side_effect=input_effect) as check,\
             patch.object(m,'run_session') as run,patch.object(m,'fresh_tty') as tty,\
             patch('builtins.print'):
            code=m.main()
            return code,check,run,tty,store
    def test_marker_published_during_preflight_blocks_run_and_recover_under_lock(self):
        for action in ('run','recover'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as t:
                root=Path(t);(root/'backups').mkdir()
                def acquired(*args):
                    (root/'.scratch/forgix-usb-ram-unclosed.json').write_text('{}')
                code,check,run,tty,_=self.invoke_main(root,action,flock_effect=acquired)
                self.assertEqual(code,2);check.assert_not_called();run.assert_not_called();tty.assert_not_called()
    def test_changed_frozen_input_blocks_both_actions_after_lock(self):
        for action in ('run','recover'):
            with self.subTest(action=action),tempfile.TemporaryDirectory() as t:
                root=Path(t);(root/'backups').mkdir();events=[]
                def acquired(*args):events.append('lock')
                def changed(*args):
                    events.append('inputs');raise m.preserve.PreservationError('synthetic changed input')
                code,check,run,tty,_=self.invoke_main(root,action,acquired,changed)
                self.assertEqual(code,2);self.assertEqual(events,['lock','inputs'])
                check.assert_called_once();run.assert_not_called();tty.assert_not_called()

class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'backups').mkdir()
        self.private=self.root/'backups/session';self.private.mkdir();self.elf=self.root/'sample.elf';self.elf.write_bytes(b'fixture')
        self.args=SimpleNamespace(factory_port=None,private_dir=self.private,cleaning=False)
        self.inspector=Mock();self.inspector.target.return_value=m.preserve.USBTarget('3-3',3,7,m.preserve.FACTORY_PID,'synthetic')
        self.inspector.wait.return_value=m.preserve.USBTarget('3-3',3,8,m.preserve.BOOT_PID,'synthetic')
        self.runner=Mock();self.runner.hardware_process_closed=True
        self.record={};self.binding={'uid_sha256':'a'*64};self.artifact={'elf':str(self.elf),'build_source_sha256':'b'*64};self.image={'picotool_executable':'synthetic','image_id':'sha256:'+'c'*64}
    def tearDown(self):self.tmp.cleanup()
    def invoke(self,capture_error=None,load_error=None,pre_error=None,post_error=None):
        stack=__import__('contextlib').ExitStack()
        with stack:
            stack.enter_context(patch.object(m,'ROOT',self.root))
            stack.enter_context(patch.object(m,'check_inputs'))
            stack.enter_context(patch.object(m,'fresh_tty',return_value='/synthetic/ttyACM4'))
            stack.enter_context(patch.object(m,'BudgetInspector',return_value=self.inspector))
            stack.enter_context(patch.object(m,'OwnedPicotool',return_value=self.runner))
            full=stack.enter_context(patch.object(m,'full_preservation',side_effect=pre_error if pre_error else [({'status':'before'},Mock()),post_error if post_error else ({'status':'after'},Mock())]))
            query=stack.enter_context(patch.object(m,'bounded_query'))
            cap=stack.enter_context(patch.object(m,'spawn_collector',side_effect=capture_error,return_value={'verified_no_record_loss':True}))
            if load_error:self.runner.run.side_effect=load_error
            if capture_error or load_error or pre_error or post_error:
                with self.assertRaises(type(capture_error or load_error or pre_error or post_error)):m.run_session(self.args,9,self.record,{},self.binding,self.artifact,self.image)
            else:m.run_session(self.args,9,self.record,{},self.binding,self.artifact,self.image)
            return full,query,cap
    def test_clean_run_two_full_preservations_and_bounded_query(self):
        full,query,cap=self.invoke();self.assertEqual(full.call_count,2);query.assert_called_once();cap.assert_called_once()
        self.assertTrue(self.record['original_flash_and_factory_verified']);self.assertEqual(self.record['flash_writes'],0)
        self.assertEqual([c.args[0] for c in self.runner.run.call_args_list],['boot','load'])
    def test_capture_failure_still_verifies_original(self):
        full,query,_=self.invoke(capture_error=RuntimeError('synthetic'))
        self.assertEqual(full.call_count,2);query.assert_called_once();self.assertTrue(self.record['original_flash_and_factory_verified']);self.assertEqual(self.record['status'],'failed')
    def test_cancel_still_verifies_original(self):
        full,query,_=self.invoke(capture_error=m.Cancelled('synthetic'))
        self.assertEqual(full.call_count,2);query.assert_called_once();self.assertTrue(self.args.cleaning)
    def test_unclosed_collector_refuses_all_recovery_access(self):
        full,query,_=self.invoke(capture_error=m.OwnedHardwareClosureError('synthetic'))
        self.assertEqual(full.call_count,1);query.assert_not_called();self.assertFalse(self.record['collector_group_closed']);self.assertTrue(self.record['manual_usb_power_cycle_required'])
    def test_load_failure_ack_uncertainty_still_checks_factory_and_flash(self):
        full,query,cap=self.invoke(load_error=RuntimeError('synthetic'))
        self.assertEqual(full.call_count,2);query.assert_called_once();cap.assert_not_called();self.assertTrue(self.record['original_flash_and_factory_verified'])
    def test_precondition_failure_never_loads_or_captures(self):
        full,query,cap=self.invoke(pre_error=RuntimeError('synthetic'))
        self.runner.run.assert_not_called();query.assert_not_called();cap.assert_not_called();self.assertEqual(full.call_count,1)
    def test_pre_preservation_unknown_closure_explicit_and_no_load(self):
        full,query,cap=self.invoke(pre_error=m.OwnedHardwareClosureError('synthetic'))
        self.runner.run.assert_not_called();query.assert_not_called();cap.assert_not_called()
        self.assertFalse(self.record['owned_hardware_processes_closed'])
    def test_capture_failure_plus_recovery_unknown_closure_stays_unknown(self):
        self.invoke(capture_error=RuntimeError('synthetic'),post_error=m.OwnedHardwareClosureError('synthetic'))
        self.assertFalse(self.record['owned_hardware_processes_closed'])
        with self.assertRaises(m.preserve.PreservationError):m.recovery_admission(self.record,{})
    def test_changed_initial_port_refuses_preservation(self):
        self.args.factory_port='/wrong/tty'
        with patch.object(m,'fresh_tty',return_value='/synthetic/ttyACM4'),patch.object(m,'full_preservation') as full,self.assertRaises(m.preserve.PreservationError):m.run_session(self.args,9,self.record,{},self.binding,self.artifact,self.image)
        full.assert_not_called()

if __name__=='__main__':unittest.main()

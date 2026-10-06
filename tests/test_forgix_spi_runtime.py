"""Register production dispatch and actual shared-worker admission; no hardware."""
import copy
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_spi_backend as backend
import run_forgix_spi_trial as coordinator
import forgix_synthetic_runtime as runtime
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve
import test_forgix_synthetic_runtime as fixtures
from demo_esp_sdr import OwnedHardwareClosureError

class RegisterRuntime(unittest.TestCase):
    setUp=fixtures.Runtime.setUp
    tearDown=fixtures.Runtime.tearDown
    closure=fixtures.Runtime.closure
    image=fixtures.Runtime.image

    def qualification(self,env):
        frozen={'inputs':dict.fromkeys(backend.EXECUTION_FILES,'a'*64)}
        profile={n:'b'*64 for n in ('elf_sha256','manifest_sha256','bridge_source_sha256',
             'bitstream_sha256','backend_source_sha256','coordinator_source_sha256')}
        profile.update(uid_sha256='a'*64,baseline_sha256='b'*64,environment_sha256=backend.digest(env),execution_sha256=backend.digest(
            {n:h for n,h in frozen['inputs'].items()if n!='tools/forgix_spi_qualifications.py'}))
        q={'kind':'Forgix physical register episode qualification','configuration_strategy':'after_ram_startup',
           'admission_registry_binding':'separately frozen committed registry',
           'reviewed_execution_sha256':{n:h for n,h in frozen['inputs'].items()if n!='tools/forgix_spi_qualifications.py'},
           'reviewed_environment_sha256':profile['environment_sha256'],
           'elf_sha256':profile['elf_sha256'],'bitstream_sha256':profile['bitstream_sha256'],
           'uid_sha256':profile['uid_sha256'],'baseline_sha256':profile['baseline_sha256']}
        q.update(dict.fromkeys(('fpga_grade_verified','clock_verified','spi_handoff_verified',
                              'whole_loading_recovery_reviewed','startup_uid_reviewed'),True))
        path=self.root/'qualification.json';path.write_text(json.dumps(q))
        profile.update(qualification_path=str(path),qualification_sha256=trial.sha(path))
        return profile,frozen,q,path

    def test_empty_registry_blocks_tool_selection_and_complete_build_source_map_is_frozen(self):
        with patch.object(backend,'QUALIFIED',()),patch.object(runtime,'select')as select,self.assertRaisesRegex(ValueError,'No committed qualification'):
            coordinator.prepare(SimpleNamespace())
        select.assert_not_called()
        self.assertTrue(set(backend.ARTIFACT_FILES)<=backend.EXECUTION_FILES)
        self.assertIn('tools/forgix_synthetic_runtime.py',backend.EXECUTION_FILES)
        self.assertIn('tools/build_forgix_spi_bridge.py',backend.EXECUTION_FILES)

    def test_qualification_binds_environment_execution_and_all_physical_review_flags(self):
        env=self.image();profile,frozen,q,path=self.qualification(env)
        with patch.object(trial,'private_file',return_value=path):
            backend.qualification_receipt(profile,env,frozen)
            for field in ('reviewed_environment_sha256','reviewed_execution_sha256','clock_verified',
                          'fpga_grade_verified','spi_handoff_verified','startup_uid_reviewed',
                          'whole_loading_recovery_reviewed'):
                changed=copy.deepcopy(q);changed.pop(field);path.write_text(json.dumps(changed))
                profile['qualification_sha256']=trial.sha(path)
                with self.subTest(field=field),self.assertRaises(ValueError):
                    backend.qualification_receipt(profile,env,frozen)
            path.write_text(json.dumps(q));profile['qualification_sha256']=trial.sha(path)
            changed=copy.deepcopy(env);changed['docker_endpoint']='tcp://foreign'
            with self.assertRaisesRegex(ValueError,'runtime tuple'):backend.qualification_receipt(profile,changed,frozen)
            changed=copy.deepcopy(frozen);changed['inputs']['tools/forgix_spi_backend.py']='0'*64
            with self.assertRaisesRegex(ValueError,'execution tuple'):backend.qualification_receipt(profile,env,changed)
        with patch.object(backend,'QUALIFIED',(backend.qualification_key(profile),)):
            backend.qualified(profile)
            profile['environment_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'No committed physical'):backend.qualified(profile)

    def test_original_uid_and_flash_baseline_are_exact_qualification_and_registry_inputs(self):
        env=self.image();profile,frozen,q,path=self.qualification(env)
        original_key=backend.qualification_key(profile)
        with patch.object(trial,'private_file',return_value=path):
            for field in ('uid_sha256','baseline_sha256'):
                for value in (None,False,'invalid','c'*64):
                    changed=dict(q);changed[field]=value;path.write_text(json.dumps(changed))
                    profile['qualification_sha256']=trial.sha(path)
                    with self.subTest(field=field,value=value),self.assertRaisesRegex(ValueError,'original board binding'):
                        backend.qualification_receipt(profile,env,frozen)
                path.write_text(json.dumps(q));profile['qualification_sha256']=trial.sha(path)
                with patch.object(backend,'QUALIFIED',(backend.qualification_key(profile),)):
                    changed=dict(profile);changed[field]='c'*64
                    with self.assertRaisesRegex(ValueError,'No committed physical'):backend.qualified(changed)
                changed=dict(profile);changed[field]=True
                with self.assertRaisesRegex(ValueError,'Complete qualification'):backend.qualification_key(changed)
        self.assertEqual(backend.qualification_key(profile),original_key)

    def test_actual_original_binding_recheck_refuses_worker_before_shared_query(self):
        env=self.image();profile,frozen,q,qpath=self.qualification(env)
        profile.update(binding_path='fixture-binding',baseline_paths=['fixture-a','fixture-b'])
        path=self.root/'request.json';path.write_text(json.dumps({'profile':profile,'environment':env,'frozen':frozen}))
        binding={'uid_sha256':profile['uid_sha256'],'baseline_sha256':profile['baseline_sha256']}
        with patch.object(trial,'private_file',side_effect=lambda p,*a:Path(p)),patch.object(backend,'qualified'),patch.object(backend,'session_lease'),patch.object(backend,'frozen_inputs'),patch.object(trial,'original_binding',return_value=dict(binding,baseline_sha256='c'*64)),patch.object(trial,'query_worker')as query:
            with self.assertRaisesRegex(ValueError,'Original preservation'):backend.factory_query_worker(path)
            query.assert_not_called()
        with patch.object(trial,'original_binding',return_value=binding):backend.original_profile(profile)

    def test_coordinator_activates_dispatch_before_artifact_queries(self):
        calls=[]
        def artifact(*args):
            runtime.check_dispatch(self.tools);calls.append('artifact');raise RuntimeError('fixture stop after dispatch')
        with patch.object(backend,'QUALIFIED',('fixture',)),patch.object(backend,'artifact',side_effect=artifact):
            with self.assertRaisesRegex(RuntimeError,'fixture stop'):coordinator.prepare(SimpleNamespace(artifact='fixture'))
        self.assertEqual(calls,['artifact'])
        with patch.object(backend,'QUALIFIED',('fixture',)),patch.dict(os.environ,{'DOCKER_HOST':'tcp://foreign'}),patch.object(backend,'artifact')as artifact:
            with self.assertRaises(ValueError):coordinator.prepare(SimpleNamespace(artifact='fixture'))
        artifact.assert_not_called()

    def test_every_tool_archive_and_endpoint_mutation_blocks_picotool_before_dispatch(self):
        env=self.image();runner=object.__new__(backend.RegisterPicotool);runner.environment=env
        for name in runtime.TOOLS:
            changed=copy.deepcopy(env);changed['host_tools'][name]['sha256']='0'*64;runner.environment=changed
            with self.subTest(tool=name),patch.object(trial.OwnedPicotool,'run')as operation,self.assertRaises(ValueError):
                runner.run('return','fixture')
            operation.assert_not_called()
        runner.environment=env
        for field,value in [('DOCKER_HOST','tcp://foreign'),('DOCKER_CONTEXT','foreign'),('PATH','/usr/bin')]:
            with patch.dict(os.environ,{field:value}),patch.object(trial.OwnedPicotool,'run')as operation,self.assertRaises(ValueError):runner.run('return','fixture')
            operation.assert_not_called()
        self.archive.write_bytes(b'changed')
        with patch.object(trial.OwnedPicotool,'run')as operation,self.assertRaisesRegex(ValueError,'archive'):runner.run('return','fixture')
        operation.assert_not_called()

    def test_factory_worker_checks_runtime_before_actual_shared_query_and_preserves_identity_refusals(self):
        env=self.image();profile,frozen,q,qpath=self.qualification(env)
        target=preserve.USBTarget('3-3',1,2,preserve.FACTORY_PID,'/fixture/usb','a'*64)
        path=self.root/'request.json';request={'profile':profile,'environment':env,'frozen':frozen,
          'topology':'3-3','port':'/fixture/tty','target':target.__dict__,'label':'returned-after-ram','lockfd':17}
        path.write_text(json.dumps(request))
        def private_file(value,*args):return Path(value)
        original=list(sys.argv)
        with patch.object(trial,'private_file',side_effect=private_file),patch.object(backend,'qualified'),patch.object(backend,'session_lease'),patch.object(backend,'original_profile'),patch.object(backend,'frozen_inputs'),patch.object(backend,'inherited_operator_lock'),patch('forgix_usb_ram_capture.inherited_operator_lock'),patch.object(trial.signal,'signal'),patch.object(preserve,'query_factory',return_value={'fixture':True})as query,patch.object(preserve.PrivateStore,'json')as save:
            self.assertEqual(backend.factory_query_worker(path),0);self.assertEqual(sys.argv,original)
            self.assertEqual(query.call_args.args[3],'returned-after-ram');save.assert_called_once()
            request['environment']=copy.deepcopy(env);request['environment']['host_tools']['docker']['sha256']='0'*64
            # Match the receipt digest to prove runtime bytes, independently of tuple binding, refuse.
            request['profile']=copy.deepcopy(profile);request['profile']['environment_sha256']=backend.digest(request['environment'])
            q['reviewed_environment_sha256']=request['profile']['environment_sha256'];qpath.write_text(json.dumps(q));request['profile']['qualification_sha256']=trial.sha(qpath)
            path.write_text(json.dumps(request));query.reset_mock()
            with self.assertRaisesRegex(ValueError,'differs'):backend.factory_query_worker(path)
            query.assert_not_called()
        path.write_text(json.dumps({'profile':profile}))
        with patch.object(trial,'private_file',return_value=path),patch.object(trial,'query_worker')as query,self.assertRaisesRegex(ValueError,'No committed physical'):backend.factory_query_worker(path)
        query.assert_not_called()

    def test_serial_worker_rejects_runtime_before_artifact_or_serial(self):
        env=self.image();profile,frozen,q,qpath=self.qualification(env);path=self.root/'request.json'
        path.write_text(json.dumps({'profile':profile,'environment':env,'frozen':frozen,'lockfd':17,'lockpath':'fixture'}))
        with patch.object(trial,'private_file',side_effect=lambda p,*a:Path(p)),patch.object(backend,'qualified'),patch.object(backend,'session_lease'),patch.object(backend,'original_profile'),patch.object(backend,'frozen_inputs'),patch.dict(os.environ,{'DOCKER_CONTEXT':'foreign'}),patch.object(backend,'artifact')as artifact,patch.object(backend,'open_retaining_serial')as opened,self.assertRaises(ValueError):backend.serial_worker(path)
        artifact.assert_not_called();opened.assert_not_called()

    def test_serial_stage_rechecks_tools_after_durable_request_before_worker_spawn(self):
        env=self.image();b=object.__new__(backend.Backend);b.hardware_gate=lambda until:None
        b.environment=env;b.profile={};b.frozen={};b.lockfd=17;b.lockpath=self.root/'lock';b.bus=1
        b.private=self.root/'session';b.workers=SimpleNamespace(run=Mock())
        def persisted(name,value):
            self.files['docker'].write_bytes(b'changed after request persistence')
            return self.root/'request.json'
        with patch.object(preserve,'PrivateStore',return_value=SimpleNamespace(json=persisted)),self.assertRaisesRegex(ValueError,'differs'):
            b.serial_stage('configure',200)
        b.workers.run.assert_not_called()

    def bounded(self,env,delay=False):
        folder=self.root/'store';folder.mkdir();port=self.root/'port';port.touch()
        now=[100.0]
        def save(name,value):
            path=folder/name;path.write_text(json.dumps(value))
            if delay:now[0]=116.0
            return path
        store=SimpleNamespace(path=folder,json=save)
        inspector=SimpleNamespace(topology='3-3',confirm=Mock())
        target=preserve.USBTarget('3-3',1,2,preserve.FACTORY_PID,'/fixture/usb','a'*64)
        runner=SimpleNamespace(hardware_process_closed=True)
        return store,inspector,target,runner,now,port

    def test_factory_parent_spawns_exact_interpreter_and_admitted_entry_request(self):
        env=self.image();profile,frozen,q,qpath=self.qualification(env);store,inspector,target,runner,now,port=self.bounded(env)
        def worker(command,log,fd,timeout):
            self.assertEqual(command[:2],[env['python_executable'],str(Path(backend.__file__).resolve())])
            self.assertEqual(command[2],'_factory-query-worker');self.assertEqual(fd,17);self.assertEqual(timeout,15)
            request=json.loads(Path(command[-1]).read_text());self.assertEqual(request['environment'],env);self.assertEqual(request['frozen'],frozen)
            (store.path/'returned-after-ram-query-result.json').write_text('{"fixture":true}');return 0
        with patch.object(trial,'private_file',side_effect=lambda p,*a:Path(p)),patch.object(backend,'frozen_inputs'),patch.object(trial,'fresh_tty',return_value=str(port)),patch.object(backend.time,'monotonic',side_effect=lambda:now[0]),patch.object(trial,'owned_worker',side_effect=worker)as child:
            self.assertEqual(backend.bounded_factory_query(inspector,target,store,'returned-after-ram',17,200,runner,profile,env,frozen),{'fixture':True})
        child.assert_called_once();self.assertTrue(runner.hardware_process_closed)

    def test_factory_storage_deadline_and_unknown_worker_closure_refuse_without_retry(self):
        for delay in (False,True):
            with self.subTest(late_storage=delay):
                env=self.image();profile,frozen,q,qpath=self.qualification(env)
                folder=self.root/'store'
                if folder.exists():
                    for p in folder.iterdir():p.unlink()
                    folder.rmdir()
                store,inspector,target,runner,now,port=self.bounded(env,delay)
                with patch.object(trial,'private_file',side_effect=lambda p,*a:Path(p)),patch.object(backend,'frozen_inputs'),patch.object(trial,'fresh_tty',return_value=str(port)),patch.object(backend.time,'monotonic',side_effect=lambda:now[0]),patch.object(trial,'owned_worker',side_effect=OwnedHardwareClosureError('fixture'))as child:
                    if delay:
                        with self.assertRaises(preserve.PreservationError):backend.bounded_factory_query(inspector,target,store,'returned-after-ram',17,200,runner,profile,env,frozen)
                        child.assert_not_called()
                    else:
                        with self.assertRaises(OwnedHardwareClosureError):backend.bounded_factory_query(inspector,target,store,'returned-after-ram',17,200,runner,profile,env,frozen)
                        child.assert_called_once();self.assertFalse(runner.hardware_process_closed)

    def test_preservation_retains_runner_before_storage_failure_and_blocks_unknown_closure(self):
        env=self.image()
        for closed in (True,False):
            with self.subTest(closed=closed):
                b=object.__new__(backend.Backend);b.hardware_gate=lambda until:None;b.private=self.root/'session'
                b.inspector=SimpleNamespace(deadline=0);b.environment=env;b.environment['image_id']='fixture';b.frozen={};b.lockfd=17;b.profile={}
                b.owner=backend.AggregateOwner(SimpleNamespace(closed=True));runner=SimpleNamespace(hardware_process_closed=closed)
                store=SimpleNamespace(path=self.root/'store')
                with patch.object(preserve,'PrivateStore',return_value=store),patch.object(backend,'RegisterPicotool',return_value=runner),patch.object(preserve,'preserve',side_effect=OSError('fixture storage')):
                    with self.assertRaises(OSError if closed else OwnedHardwareClosureError):b.preservation('before',200)
                self.assertEqual(b.owner.runners,[runner]);self.assertEqual(b.owner.unknown,not closed)

if __name__=='__main__':unittest.main()

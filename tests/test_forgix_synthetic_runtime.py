"""Hardware-free host dispatch/closure mutations and preservation ownership."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_synthetic_runtime as runtime
import forgix_synthetic_backend as backend
from demo_esp_sdr import OwnedHardwareClosureError

class Runtime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.files={}
        for n in runtime.TOOLS:
            p=self.root/n/'bin'/n;p.parent.mkdir(parents=True);p.write_text('fixture '+n);p.chmod(0o700);self.files[n]=p
        self.archive=self.root/'archive';self.archive.mkdir();self.archive=self.archive/'image.tar';self.archive.write_bytes(b'archive')
        def root(p):
            p=Path(p).resolve(strict=True)
            if not p.is_relative_to(self.root):raise ValueError('Fixture path escape')
            return self.root/p.relative_to(self.root).parts[0]
        self.patches=[patch.object(runtime,'store_root',side_effect=root),patch.object(runtime.sys,'executable',str(self.files['python'])),
                      patch.object(runtime,'SDK',self.root/'sdk'),patch.object(runtime,'COMPILER',self.root/'compiler'),
                      patch.dict(os.environ,{'PATH':os.pathsep.join(str(p.parent) for p in self.files.values()),
                          'DOCKER_HOST':runtime.SOCKET,'DOCKER_CONTEXT':'','DOCKER_TLS_VERIFY':'','DOCKER_CERT_PATH':'',
                          'PICOTOOL_USB_IMAGE':str(self.archive)})]
        (self.root/'sdk').mkdir();(self.root/'compiler').mkdir()
        for p in self.patches:p.start()
        self.tools=runtime.select();runtime.activate(self.tools)
        self.base={'python_executable':str(self.files['python']),'python_executable_sha256':runtime.sha(self.files['python']),
            'picotool_executable':str(self.files['picotool']),'picotool_executable_sha256':runtime.sha(self.files['picotool']),
            'image_archive_sha256':runtime.sha(self.archive),'nix_recursive_closure':self.closure([str(self.root/'sdk')])}
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def closure(self,paths):return {p:{'narHash':'sha256-'+'A'*43+'=','references':[]} for p in paths}
    def image(self,closure=None):
        closure=closure or self.closure(runtime.roots(self.tools,self.archive))
        with patch('forgix_usb_ram_trial.image_check',return_value=self.base),patch.object(runtime.subprocess,'check_output',return_value=json.dumps(closure).encode()) as query,patch.object(runtime.subprocess,'run') as verify:
            env=runtime.image_check('fixture',self.tools)
        self.assertEqual(query.call_args.args[0][0],str(self.files['nix']))
        self.assertEqual(verify.call_args.args[0][0],str(self.files['nix-store']))
        self.assertTrue(verify.call_args.kwargs['check']);self.assertEqual(verify.call_args.kwargs['timeout'],120)
        return env
    def test_complete_tools_closures_and_explicit_dispatch(self):
        env=self.image();runtime.check(env)
        self.assertEqual(len(env['host_tools']),7)
        self.assertIn(str(self.root/'task'),env['host_closure_roots'])
        self.assertIn(str(self.root/'docker'),env['host_closure_roots'])
        self.assertEqual(os.environ['DOCKER_HOST'],runtime.SOCKET)
    def test_multicall_alias_keeps_invocation_and_binds_target(self):
        self.files['nix-store'].unlink();self.files['nix-store'].symlink_to(self.files['nix'])
        tools=runtime.select();runtime.activate(tools)
        self.assertEqual(tools['nix-store']['path'],str(self.files['nix-store']))
        self.assertEqual(tools['nix-store']['resolved_path'],str(self.files['nix']))
        self.tools=tools;self.image()
        self.files['nix-store'].unlink();self.files['nix-store'].symlink_to(self.files['git'])
        with self.assertRaisesRegex(ValueError,'differs'):runtime.check_dispatch(tools)
    def test_missing_changed_executable_and_interpreter_refuse(self):
        for name in runtime.TOOLS:
            with self.subTest(name=name):
                original=self.files[name].read_bytes();self.files[name].write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'differs'):runtime.check_dispatch(self.tools)
                self.files[name].write_bytes(original)
        tools=copy.deepcopy(self.tools);tools.pop('task')
        with self.assertRaisesRegex(ValueError,'Complete'):runtime.activate(tools)
        with patch.object(runtime.sys,'executable',str(self.files['git'])):
            with self.assertRaisesRegex(ValueError,'interpreter'):runtime.check_dispatch(self.tools)
    def test_shadowed_or_reordered_path_refuses_before_operation(self):
        for value in ('/usr/bin:'+os.environ['PATH'],os.environ['PATH']+':/usr/bin',''):
            with patch.dict(os.environ,{'PATH':value}),self.assertRaisesRegex(ValueError,'dispatch'):runtime.check_dispatch(self.tools)
        with patch.object(runtime.shutil,'which',return_value=str(self.files['git'])):
            with self.assertRaisesRegex(ValueError,'shadowed'):runtime.check_dispatch(self.tools)
    def test_foreign_docker_selection_refuses_without_command(self):
        for name,value in [('DOCKER_HOST','tcp://foreign:2375'),('DOCKER_CONTEXT','foreign'),('DOCKER_TLS_VERIFY','1'),('DOCKER_CERT_PATH','foreign'),('GIT_DIR','foreign'),('GIT_CONFIG_COUNT','1')]:
            with patch.dict(os.environ,{name:value}),patch.object(runtime.subprocess,'run') as run:
                with self.assertRaises(ValueError):runtime.activate(self.tools)
                run.assert_not_called()
    def test_incomplete_false_malformed_closure_refuses(self):
        env=self.image()
        for mutation in ({'host_closure_contents_verified':False},{'host_closure_contents_verified':1},
                         {'host_closure_roots':[]},{'host_nix_recursive_closure':{}},
                         {'host_dispatch_path':'/usr/bin'},{'docker_endpoint':'foreign'},
                         {'python_executable_sha256':'f'*64}):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):runtime.check({**env,**mutation})
        incomplete=self.closure([str(self.root/'sdk')])
        with patch('forgix_usb_ram_trial.image_check',return_value=self.base),patch.object(runtime.subprocess,'check_output',return_value=json.dumps(incomplete).encode()),patch.object(runtime.subprocess,'run') as verify:
            with self.assertRaisesRegex(ValueError,'Incomplete'):runtime.image_check('fixture',self.tools)
            verify.assert_not_called()
    def test_omitted_transitive_leaf_and_reference_metadata_refuse(self):
        leaf=self.root/'lib';leaf.mkdir()
        closure=self.closure([*runtime.roots(self.tools,self.archive),str(leaf)])
        closure[str(self.root/'git')]['references']=[str(leaf)]
        env=self.image(closure);runtime.check(env)
        bad=copy.deepcopy(env);del bad['host_nix_recursive_closure'][str(leaf)]
        with self.assertRaisesRegex(ValueError,'Incomplete transitive'):runtime.check(bad)
        malformed=[None,False,{},str(leaf),[str(leaf),str(leaf)],[str(leaf/'nested')],[True]]
        for refs in malformed:
            bad=copy.deepcopy(env);bad['host_nix_recursive_closure'][str(self.root/'git')]['references']=refs
            with self.subTest(refs=refs),self.assertRaises(ValueError):runtime.check(bad)
        bad=copy.deepcopy(env);del bad['host_nix_recursive_closure'][str(self.root/'git')]['references']
        with self.assertRaisesRegex(ValueError,'metadata'):runtime.check(bad)
        omitted=copy.deepcopy(closure);del omitted[str(leaf)]
        with patch('forgix_usb_ram_trial.image_check',return_value=self.base),patch.object(runtime.subprocess,'check_output',return_value=json.dumps(omitted).encode()),patch.object(runtime.subprocess,'run') as verify:
            with self.assertRaisesRegex(ValueError,'Incomplete transitive'):runtime.image_check('fixture',self.tools)
            verify.assert_not_called()
    def test_verify_failure_never_marks_receipt_verified(self):
        with patch('forgix_usb_ram_trial.image_check',return_value=self.base),patch.object(runtime.subprocess,'check_output',return_value=json.dumps(self.closure(runtime.roots(self.tools,self.archive))).encode()),patch.object(runtime.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'verify')):
            with self.assertRaises(subprocess.CalledProcessError):runtime.image_check('fixture',self.tools)
        self.assertNotIn('host_closure_contents_verified',self.base)
    def test_archive_and_host_path_mutations_reject_saved_environment(self):
        env=self.image();self.archive.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'archive'):runtime.check(env)
        self.archive.write_bytes(b'archive');tools=copy.deepcopy(env['host_tools']);tools['docker']['path']=str(self.files['git'])
        with self.assertRaises(ValueError):runtime.check({**env,'host_tools':tools})
    def test_child_inherits_exact_dispatch_without_ambient_suffix(self):
        # Real process with an explicit interpreter, not a simulated env copy.
        with patch.object(runtime.sys,'executable',sys.__dict__.get('_base_executable',sys.executable)):
            python=runtime.sys.executable
        r=subprocess.run([python,'-c','import os,json;print(json.dumps([os.environ["PATH"],os.environ["DOCKER_HOST"]]))'],capture_output=True,text=True,check=True,timeout=10)
        self.assertEqual(json.loads(r.stdout),[runtime.search_path(self.tools),runtime.SOCKET])

class Boundaries(unittest.TestCase):
    def test_non_store_and_noncanonical_inputs_reject(self):
        with self.assertRaisesRegex(ValueError,'Nix-store'):runtime.store_root(Path('/etc/hosts').resolve())
        with self.assertRaises(ValueError):runtime.store_root('relative')
    def test_per_picotool_operation_checks_before_any_shared_operation(self):
        runner=object.__new__(backend.SyntheticPicotool);runner.environment={'fixture':'environment'}
        with patch.object(runtime,'check',side_effect=ValueError('changed docker')),patch.object(backend.trial.OwnedPicotool,'run') as operation:
            with self.assertRaisesRegex(ValueError,'changed docker'):runner.run('boot',object())
            operation.assert_not_called()
    def test_preservation_same_full_original_proof_and_per_query_guard(self):
        b=object.__new__(backend.Backend);b.environment={'picotool_executable':'fixture','image_id':'fixture'}
        b.profile={'baseline_sha256':backend.trial.BASELINE,'uid_sha256':'u'};b.private=Path('/private');b.frozen={};b.lockfd=0
        b.owner=SimpleNamespace(runners=[],unknown=False);b.inspector=SimpleNamespace();b.clock=lambda:1
        runner=SimpleNamespace(hardware_process_closed=True)
        receipt={'backups':{'sha256':backend.trial.BASELINE,'bytes_per_read':backend.trial.FLASH_BYTES,'reads':2,'matching':True},
                 'independent_device_verify':True,'status':'preserved_and_returned'}
        def preserve(i,r,s,n,query):
            query(i,object(),s,'before');return receipt,None
        with patch.object(b,'hardware_gate'),patch.object(backend.preserve,'PrivateStore'),patch.object(backend,'SyntheticPicotool',return_value=runner),patch.object(backend.preserve,'preserve',side_effect=preserve),patch.object(runtime,'check') as check,patch.object(backend.trial,'bounded_query') as query:
            result=b.preservation('before',10)
            check.assert_called_once_with(b.environment);query.assert_called_once()
        self.assertEqual(result['read_sha256'],[backend.trial.BASELINE]*2)
        self.assertTrue(result['independent_device_verify'] and result['factory_application_verified'])
    def test_preservation_retains_unknown_runner_despite_storage_exception(self):
        b=object.__new__(backend.Backend);b.environment={'picotool_executable':'fixture','image_id':'fixture'}
        b.profile={};b.private=Path('/private');b.frozen={};b.lockfd=0
        b.owner=SimpleNamespace(runners=[],unknown=False);b.inspector=SimpleNamespace();runner=SimpleNamespace(hardware_process_closed=False)
        with patch.object(b,'hardware_gate'),patch.object(backend.preserve,'PrivateStore'),patch.object(backend,'SyntheticPicotool',return_value=runner),patch.object(backend.preserve,'preserve',side_effect=OSError('storage')):
            with self.assertRaises(OwnedHardwareClosureError):b.preservation('before',10)
        self.assertTrue(b.owner.unknown);self.assertEqual(b.owner.runners,[runner])

if __name__=='__main__':unittest.main()

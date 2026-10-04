"""V2 archive/endpoint/process boundaries with Docker queries always injected."""
import contextlib
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ble_primary_timed_container as wrapper

NAME = 'esp-sdr-ble-primary-timed-source-' + 'a' * 32
IMAGE = 'sha256:' + 'b' * 64
SCRIPT = '/nix/store/fixture-source/lib/esp-sdr-ble-primary-timed-source/ble_primary_timed_source.py'
PYTHON = str(Path(sys.executable).resolve())
DOCKER = '/nix/store/fixture-docker/bin/docker'
TAG = 'esp-sdr-ble-primary-timed-source:' + 'c' * 16
ARGS = ['--profile', wrapper.PROFILE, '--handle', '1', '--interval-ms', '20', '--events', '0',
        '--duration-ms', '25000', '--start-delay', '0']


def fake_file(value, basename):
    if type(value) is not str or not value.startswith('/nix/store/') or Path(value).name != basename:
        raise ValueError('fixture immutable file refused')
    return value


def image_fixture():
    data = b'fixture module'
    digest = hashlib.sha256(data).hexdigest()
    return [{'Id':IMAGE, 'Config':{'Cmd':[PYTHON,SCRIPT], 'Labels':wrapper.archive_labels(digest,digest,SCRIPT)}}]


class Producer:
    pid = 123456
    returncode = 0
    def poll(self): return self.returncode
    def wait(self, timeout=None): return self.returncode


class ContainerTests(unittest.TestCase):
    def setUp(self):
        self.env = {'PATH':str(Path(PYTHON).parent), 'BLE_PRIMARY_TIMED_IMAGE':'/nix/store/fixture-image.tar.gz',
                    'BLE_PRIMARY_TIMED_IMAGE_TAG':TAG, 'BLE_PRIMARY_TIMED_PRELOADED_IMAGE_ID':IMAGE,
                    'BLE_PRIMARY_TIMED_PYTHON':PYTHON, 'BLE_PRIMARY_TIMED_ENTRYPOINT':SCRIPT}

    def resolve(self, data=None, **changes):
        opts={'archive':'/nix/store/fixture-image.tar.gz','tag':TAG,'preloaded_id':IMAGE,
              'executable':PYTHON,'entrypoint':SCRIPT};opts.update(changes)
        with patch.object(wrapper,'immutable_file',side_effect=fake_file),\
             patch.object(Path,'resolve',lambda self,strict=False:self),patch.object(Path,'is_file',return_value=True),\
             patch.object(Path,'read_bytes',return_value=b'fixture module'),\
             patch.object(wrapper,'query',return_value=json.dumps(image_fixture()if data is None else data).encode()) as query:
            out=wrapper.resolve_source_image(**opts,docker=DOCKER,env={},deadline=time.monotonic()+2)
        return out,query

    def run_main(self, *, natural=True, absent=(True,True), proc=None, late=None, argv=None):
        clock=[100.0];output=io.StringIO();producer=proc or Producer()
        def now():return clock[0]
        def start(*args,**kwargs):
            if late=='spawn':clock[0]+=45
            if late=='cancel-spawn':signal.getsignal(signal.SIGTERM)(signal.SIGTERM,None)
            return producer
        def finish(*args,**kwargs):
            if late=='finish':clock[0]+=45
            return natural
        def resolve(*args,**kwargs):
            if late=='image':clock[0]+=45
            return IMAGE
        with patch.dict(os.environ,self.env,clear=True),patch.object(wrapper,'runtime',return_value=(DOCKER,dict(self.env,DOCKER_HOST=wrapper.SOCKET,DOCKER_CONTEXT=''))),\
             patch.object(wrapper,'resolve_source_image',side_effect=resolve),patch.object(wrapper,'immutable_file',side_effect=fake_file),\
             patch.object(wrapper,'container_absent',side_effect=absent),patch.object(wrapper.subprocess,'Popen',side_effect=start) as spawn,\
             patch.object(wrapper,'wait_natural',side_effect=finish),\
             patch.object(wrapper,'cleanup_owned',return_value={'forced_cleanup_required':True,'owned_container_removed':True,'owned_group_closed':True}) as cleanup,\
             patch.object(wrapper.time,'monotonic',now),patch.object(wrapper.time,'monotonic_ns',lambda:round(clock[0]*1e9)),\
             contextlib.redirect_stdout(output):
            code=wrapper.main(ARGS if argv is None else argv)
        return code,[json.loads(line)for line in output.getvalue().splitlines()],spawn,cleanup

    def test_exact_immutable_source_command_no_host_mount(self):
        with patch.object(wrapper,'immutable_file',side_effect=fake_file):
            command=wrapper.source_command(NAME,IMAGE,PYTHON,SCRIPT,ARGS,docker=DOCKER)
        self.assertEqual(command[:2],[DOCKER,'run']);self.assertEqual(command[-len(ARGS)-1:],[SCRIPT,*ARGS])
        self.assertIn(IMAGE,command);self.assertEqual(command[command.index('--pull')+1],'never')
        self.assertIn('--read-only',command);self.assertIn('no-new-privileges',command)
        self.assertNotIn('--mount',command);self.assertNotIn('--privileged',command);self.assertNotIn('--device',command)
        self.assertEqual(command.count('--cap-add'),2)

    def test_fixed_options_invalid_before_any_docker(self):
        for options in ([],['--profile','extended-primary-zero-data-v1'],ARGS+['--duration-ms','5000']):
            with patch.object(wrapper,'runtime') as runtime,patch.object(wrapper.subprocess,'Popen') as spawn,\
                 contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):wrapper.main(options)
            runtime.assert_not_called();spawn.assert_not_called()

    def test_owned_name_and_cid_required_together(self):
        for options in (ARGS+['--owned-name',NAME],ARGS+['--cidfile','/tmp/test.cid']):
            with patch.object(wrapper,'runtime') as runtime,self.assertRaises(ValueError):wrapper.main(options)
            runtime.assert_not_called()

    def test_wrong_namespace_image_and_host_entrypoint_refused(self):
        for name,image,script in ((NAME.replace('primary-timed-',''),IMAGE,SCRIPT),(NAME,'latest',SCRIPT),(NAME,IMAGE,'/tmp/ble_primary_timed_source.py')):
            with patch.object(wrapper,'immutable_file',side_effect=fake_file),self.assertRaises(ValueError):
                wrapper.source_command(name,image,PYTHON,script,ARGS,docker=DOCKER)

    def test_pure_archive_labels_bind_both_modules_and_entrypoint(self):
        labels=wrapper.archive_labels('1'*64,'2'*64,SCRIPT)
        self.assertEqual(set(labels),{'org.esp-sdr.source-profile','org.esp-sdr.native-sha256','org.esp-sdr.v1-primitives-sha256','org.esp-sdr.entrypoint'})
        for a,b,p in ((True,'2'*64,SCRIPT),('1'*64,'latest',SCRIPT),('1'*64,'2'*64,'/tmp/source.py')):
            with self.assertRaises(ValueError):wrapper.archive_labels(a,b,p)

    def test_exact_preloaded_archive_only_inspects_never_loads(self):
        out,query=self.resolve();self.assertEqual(out,IMAGE)
        self.assertEqual(query.call_args.args[2],['image','inspect',TAG])

    def test_mutated_id_command_each_label_and_inspect_shape_refused(self):
        mutations=[]
        for key,value in (('Id','sha256:'+'d'*64),):
            x=image_fixture();x[0][key]=value;mutations.append(x)
        x=image_fixture();x[0]['Config']['Cmd']=[PYTHON,'/source.py'];mutations.append(x)
        for key in image_fixture()[0]['Config']['Labels']:
            x=image_fixture();x[0]['Config']['Labels'][key]='changed';mutations.append(x)
        mutations += [[],{},[None],True]
        for value in mutations:
            with self.subTest(value=value),self.assertRaises((ValueError,TypeError)):self.resolve(value)

    def test_missing_or_mutable_preload_archive_tag_refuses(self):
        for changes in ({'preloaded_id':None},{'preloaded_id':'latest'},{'tag':'esp-sdr-ble-source:'+'c'*16},{'archive':'/tmp/image.tar'}):
            with self.assertRaises(ValueError):self.resolve(**changes)

    def test_nonlocal_context_tls_and_ambient_docker_refuse_before_query(self):
        for change in ({'DOCKER_HOST':'tcp://remote:2375'},{'DOCKER_CONTEXT':'remote'},
                       {'DOCKER_TLS_VERIFY':'1'},{'DOCKER_CERT_PATH':'/tmp/certs'}):
            with patch.dict(os.environ,change,clear=True),patch.object(wrapper.subprocess,'run') as run,self.assertRaises(ValueError):wrapper.runtime()
            run.assert_not_called()
        with patch.dict(os.environ,{},clear=True),patch.object(wrapper.shutil,'which',return_value='/usr/bin/docker'),\
             self.assertRaises(ValueError):wrapper.runtime()

    def test_query_uses_local_env_remaining_cap_and_postreturn_clock(self):
        clock=[100.0]
        def delayed(*args,**kwargs):clock[0]=101.0;return subprocess.CompletedProcess(args,0,b'[]',b'')
        with patch.object(wrapper.time,'monotonic',lambda:clock[0]),patch.object(wrapper.subprocess,'run',side_effect=delayed) as run,\
             self.assertRaises(ValueError):wrapper.query(DOCKER,{'DOCKER_HOST':wrapper.SOCKET},['image','inspect',TAG],101)
        self.assertEqual(run.call_args.kwargs['timeout'],1);self.assertEqual(run.call_args.kwargs['env']['DOCKER_HOST'],wrapper.SOCKET)

    def test_private_cid_path_fresh_regular_or_dangling_presence(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);directory=root/'.scratch/trial';directory.mkdir(parents=True,mode=0o700);cid=directory/'owned.cid'
            with patch.object(wrapper,'ROOT',root):
                self.assertEqual(wrapper.validate_cidfile(str(cid)),cid)
                cid.write_text('old')
                with self.assertRaises(ValueError):wrapper.validate_cidfile(str(cid))
                cid.unlink();cid.symlink_to(directory/'missing')
                with self.assertRaises(ValueError):wrapper.validate_cidfile(str(cid))
                cid.unlink();directory.chmod(0o755)
                with self.assertRaises(ValueError):wrapper.validate_cidfile(str(cid))

    def test_normal_completion_records_natural_group_and_container_absence(self):
        code,rows,spawn,cleanup=self.run_main();self.assertEqual(code,0);cleanup.assert_not_called()
        self.assertTrue(rows[-1]['owned_group_closed']);self.assertTrue(rows[-1]['owned_container_removed'])
        self.assertFalse(rows[-1]['forced_cleanup_required']);self.assertTrue(spawn.call_args.kwargs['start_new_session'])
        self.assertEqual(spawn.call_args.kwargs['env']['DOCKER_HOST'],wrapper.SOCKET)

    def test_exact_parent_minimum_forwarded_and_cannot_renew_clock(self):
        for cap,expected in ((132000000001,132000000001),(200000000000,145000000000)):
            code,rows,spawn,_=self.run_main(argv=ARGS+['--episode-deadline-monotonic-ns',str(cap)])
            self.assertEqual(code,0);self.assertEqual(rows[-1]['wrapper_deadline_monotonic_ns'],expected)
            command=spawn.call_args.args[0]
            self.assertEqual(command[-2:],['--parent-deadline-monotonic-ns',str(expected)])
        code,_,spawn,_=self.run_main(argv=ARGS+['--episode-deadline-monotonic-ns','100000000000'])
        self.assertEqual(code,2);spawn.assert_not_called()

    def test_existing_name_refusal_never_cleans_or_spawns(self):
        code,_,spawn,cleanup=self.run_main(absent=(False,));self.assertEqual(code,2);spawn.assert_not_called();cleanup.assert_not_called()

    def test_slow_admission_never_spawns_or_cleans_existing_container(self):
        code,_,spawn,cleanup=self.run_main(late='image')
        self.assertEqual(code,2);spawn.assert_not_called();cleanup.assert_not_called()

    def test_late_spawn_or_completion_and_cancel_during_assignment_fail(self):
        for phase in ('spawn','finish','cancel-spawn'):
            code,rows,_,_=self.run_main(late=phase);self.assertEqual(code,2)
            self.assertEqual(rows[-1]['wrapper_exit_code'],2)

    def test_forced_cleanup_cannot_turn_failed_group_into_success(self):
        code,rows,_,cleanup=self.run_main(natural=False);self.assertEqual(code,2);cleanup.assert_called_once()
        self.assertTrue(rows[-1]['forced_cleanup_required']);self.assertTrue(rows[-1]['force_removal_required'])

    def test_native_failure_remains_failed_despite_normal_closure(self):
        proc=Producer();proc.returncode=2
        code,rows,_,cleanup=self.run_main(proc=proc);self.assertEqual(code,2);cleanup.assert_not_called()
        self.assertTrue(rows[-1]['owned_group_closed'])

    def test_repeated_cancel_restores_signal_handlers(self):
        old={s:signal.getsignal(s)for s in (signal.SIGINT,signal.SIGTERM)}
        self.run_main(late='cancel-spawn')
        self.assertEqual({s:signal.getsignal(s)for s in old},old)

    def test_actual_harmless_process_normal_closure(self):
        proc=subprocess.Popen([sys.executable,'-c','pass'],start_new_session=True)
        self.assertTrue(wrapper.wait_natural(proc,time.monotonic()+2,lambda:False));self.assertEqual(proc.returncode,0)
        self.assertFalse(wrapper.group_alive(proc))

    def test_actual_leader_exit_live_descendant_refuses_and_natural_descendant_can_close(self):
        libc=ctypes.CDLL(None,use_errno=True);old=ctypes.c_int()
        self.assertEqual(libc.prctl(37,ctypes.byref(old),0,0,0),0);self.assertEqual(libc.prctl(36,1,0,0,0),0)
        try:
            for delay,natural in ((5,False),(.05,True)):
                code=f"import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep({delay})']); print(p.pid,flush=True)"
                proc=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,text=True,start_new_session=True)
                child=int(proc.stdout.readline());proc.wait(timeout=2)
                reaper=threading.Thread(target=lambda:os.waitpid(child,0),daemon=False);reaper.start()
                try:
                    if natural:self.assertTrue(wrapper.wait_natural(proc,time.monotonic()+2,lambda:False))
                    else:
                        with self.assertRaises(ValueError):wrapper.wait_natural(proc,time.monotonic()+.08,lambda:False)
                        self.assertTrue(wrapper.group_alive(proc))
                finally:
                    if wrapper.group_alive(proc):os.killpg(proc.pid,signal.SIGKILL)
                    reaper.join(2);self.assertFalse(reaper.is_alive());proc.stdout.close()
                self.assertFalse(wrapper.group_alive(proc))
        finally:self.assertEqual(libc.prctl(36,old.value,0,0,0),0)


if __name__ == '__main__':unittest.main()

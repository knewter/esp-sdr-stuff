"""Synthetic fixed-flow receipts; these tests never invoke the vendor compiler."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import efinity_bootstrap as b
import efinity_compile_smoke as c

XML = b'''<efx:project xmlns:efx="http://www.efinixinc.com/enf_proj" name="pt_demo" location="/factory/old-path">
<efx:device_info><efx:family name="Trion"/><efx:device name="T8F81"/><efx:timing_model name="C2"/></efx:device_info>
<efx:design_info><efx:design_file name="pt_demo.v"/></efx:design_info>
<efx:constraint_info><efx:sdc_file name="pt_demo.sdc"/><efx:inter_file name=""/></efx:constraint_info>
<efx:synthesis><efx:param name="work_dir" value="work_syn"/></efx:synthesis>
<efx:place_and_route><efx:param name="work_dir" value="work_pnr"/></efx:place_and_route></efx:project>'''


class CompilerSmoke(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.mask = os.umask(0o077)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / '.gitignore').write_text('/.scratch/\n/.vendor/\n')
        self.store = b.Store(self.root)
        with self.store.locked(): pass
        self.install = self.root / 'installed'; self.source = self.install / 'project/pt_demo'
        self.source.mkdir(parents=True); (self.install / 'scripts').mkdir(); (self.install / 'bin').mkdir()
        (self.install / 'scripts/efx_run.py').write_bytes(b'# mock runner\n')
        self.contents = {'pt_demo.xml': XML, 'pt_demo.peri.xml': b'<periphery/>', 'pt_demo.v': b'module fixture; endmodule\n', 'pt_demo.sdc': b'# clock\n'}
        for name, data in self.contents.items(): (self.source / name).write_bytes(data)
        self.pins = {name: (b.sha(self.source / name), len(data)) for name, data in self.contents.items()}
        self.patches = [patch.object(c, 'INPUTS', self.pins), patch.object(c, 'RUNNER_SHA', b.sha(self.install / 'scripts/efx_run.py')),
                        patch.object(self.store, 'installed', return_value=(self.install, {'version': c.VERSION, 'software_sha256': c.ARCHIVE_SHA})),
                        patch.object(b.shutil, 'which', return_value='/nix/store/fhs/bin/forgix-efinity')]
        for p in self.patches: p.start()
        self.private = self.root / '.scratch/compile-001'
    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        os.umask(self.mask); self.tmp.cleanup()
    def successful_vendor(self, command, env, output, timeout, store, cwd):
        self.assertEqual(command[-len(c.FLOW):], c.FLOW); self.assertNotIn('program', command)
        self.assertEqual(timeout,330); self.assertEqual(set(x.name for x in cwd.iterdir()),set(c.INPUTS))
        self.assertEqual(env['LITEX_ENV_EFINITY'], str(self.install))
        output.write(b''.join(('\x1b[92m   '+stage+' :\tPASS \x1b[0m\n').encode() for stage in c.STAGES));output.flush()
        out = cwd / 'outflow';out.mkdir();(out / 'pt_demo.hex').write_bytes(b'0123456789abcdef\n')
        (out / 'pt_demo.log').write_text(''.join('Stage completed: '+stage+'\n' for stage in c.STAGES))
        return 0
    def run_fixture(self, side_effect=None):
        with patch.object(b,'run_owned',side_effect=side_effect or self.successful_vendor):return c.compile_smoke(self.store,self.private)
    def test_success_requires_fresh_full_flow_and_private_bitstream(self):
        # Shipped old output exists but must never be copied.
        (self.source / 'outflow').mkdir();(self.source / 'outflow/pt_demo.hex').write_bytes(b'old')
        r=self.run_fixture();self.assertEqual(r['status'],'passed');self.assertTrue(r['compiler_execution_verified'])
        self.assertFalse(r['connected_forgix_compile_verified']);self.assertFalse(r['hardware_opened'])
        self.assertEqual(r['stages'],{s:'passed' for s in c.STAGES});self.assertFalse(r['optional_binary_export_requested'])
        self.assertEqual((self.private / 'work/outflow/pt_demo.hex').stat().st_mode&0o777,0o600)
        self.assertEqual(json.loads((self.private/'result.json').read_text())['status'],'passed')
    def test_existing_cached_directory_rejected_before_vendor_launch(self):
        self.private.mkdir(parents=True);(self.private/'pt_demo.hex').write_bytes(b'old')
        with patch.object(b,'run_owned',side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(b.Refusal,'fresh'):c.compile_smoke(self.store,self.private)
        self.assertEqual((self.private/'pt_demo.hex').read_bytes(),b'old')
    def test_source_hash_change_rejected_before_launch(self):
        (self.source/'pt_demo.v').write_bytes(b'changed')
        with patch.object(b,'run_owned',side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(b.Refusal,'hash or size'):c.compile_smoke(self.store,self.private)
    def test_runner_hash_change_rejected(self):
        (self.install/'scripts/efx_run.py').write_bytes(b'changed')
        with self.assertRaisesRegex(b.Refusal,'runner bytes'):self.run_fixture()
    def test_xml_unsafe_paths_and_target_refused(self):
        f=self.root/'project.xml'
        for changed in (XML.replace(b'work_syn',b'../escape'),XML.replace(b'work_syn',b'/tmp/out'),
                        XML.replace(b'pt_demo.v',b'../escape.v'),XML.replace(b'T8F81',b'T8F49')):
            f.write_bytes(changed)
            with self.assertRaises(b.Refusal):c.validate_xml(f)
        f.write_bytes(XML);c.validate_xml(f) # factory location metadata is not an operational output path
    def test_public_or_symlink_private_output_refused(self):
        (self.root/'.scratch').mkdir();(self.root/'external').mkdir();(self.root/'.scratch/link').symlink_to(self.root/'external',target_is_directory=True)
        for path in (self.root/'docs/evidence/compile',self.root/'.scratch/link/run'):
            with self.assertRaises(b.Refusal):c.private_path(self.store,path)
    def test_partial_or_skipped_stage_retains_failure(self):
        def partial(*args,**kwargs):
            self.successful_vendor(*args,**kwargs);output=args[2];output.seek(0);output.truncate();output.write(b'map : PASS\ninterface : PASS\npnr : SKIP\npgm : PASS\n');return 0
        with self.assertRaisesRegex(b.Refusal,'stages'):self.run_fixture(partial)
        r=json.loads((self.private/'result.json').read_text());self.assertEqual(r['status'],'failed');self.assertFalse(r['license_compile_verified'])
    def test_missing_stage_completion_log_rejected(self):
        def partial(*args,**kwargs):
            self.successful_vendor(*args,**kwargs);(kwargs['cwd']/'outflow/pt_demo.log').write_text('Stage completed: map\n');return 0
        with self.assertRaisesRegex(b.Refusal,'completion log'):self.run_fixture(partial)
    def test_empty_and_stale_bitstream_rejected(self):
        for kind in ('empty','stale'):
            self.private=self.root/('.scratch/'+kind)
            def bad(*args,**kwargs):
                self.successful_vendor(*args,**kwargs);image=kwargs['cwd']/'outflow/pt_demo.hex'
                if kind=='empty':image.write_bytes(b'')
                else:os.utime(image,ns=(1,1))
                return 0
            with self.assertRaisesRegex(b.Refusal,'empty, oversized or stale'):self.run_fixture(bad)
    def test_symlink_bitstream_refused(self):
        external=self.root/'original';external.write_bytes(b'outside')
        def bad(*args,**kwargs):
            self.successful_vendor(*args,**kwargs);image=kwargs['cwd']/'outflow/pt_demo.hex';image.unlink();image.symlink_to(external);return 0
        with self.assertRaisesRegex(b.Refusal,'unsafe'):self.run_fixture(bad)
        self.assertEqual(external.read_bytes(),b'outside')
    def test_timeout_is_failed_with_private_prefix(self):
        def timeout(*args,**kwargs):args[2].write(b'SECRET VENDOR OUTPUT\n');raise subprocess.TimeoutExpired('vendor',330)
        with self.assertRaises(subprocess.TimeoutExpired):self.run_fixture(timeout)
        r=json.loads((self.private/'result.json').read_text());self.assertEqual(r['status'],'failed');self.assertTrue(r['owned_process_group_closed']);self.assertNotIn('SECRET',json.dumps(r))
    def test_unclosed_owned_group_blocks_success_and_reuse(self):
        def failed(*args,**kwargs):b.save(self.store.path/'runtime-unclosed.json',{'closure_verified':False});raise b.Refusal('Group closure unverified')
        with self.assertRaises(b.Refusal):self.run_fixture(failed)
        r=json.loads((self.private/'result.json').read_text());self.assertFalse(r['owned_process_group_closed'])
        with self.assertRaisesRegex(b.Refusal,'closure'):self.run_fixture()
    def test_vendor_exit_failure_cannot_use_created_output(self):
        def bad(*args,**kwargs):self.successful_vendor(*args,**kwargs);return 7
        with self.assertRaisesRegex(b.Refusal,'returned failure'):self.run_fixture(bad)
        self.assertEqual(json.loads((self.private/'result.json').read_text())['exit_code'],7)


    def test_allowed_private_roots_cannot_be_symlinked_to_ignored_tree(self):
        external=self.root/'.vendor/other';external.mkdir()
        (self.root/'.scratch').symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(b.Refusal,'symlinks'):c.private_path(self.store,self.root/'.scratch/new')
        (self.root/'.scratch').unlink()
        (self.store.path/'compiler-smoke').symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(b.Refusal,'symlinks'):c.private_path(self.store,self.store.path/'compiler-smoke/new')
    def test_stage_log_ancestor_escape_is_rejected_before_read(self):
        work=self.root/'work';work.mkdir();external=self.root/'external';external.mkdir()
        console=self.root/'console';console.write_text(''.join(stage+' : PASS\n' for stage in c.STAGES))
        (external/'pt_demo.log').write_text('Stage completed: map\n')
        (work/'outflow').symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(b.Refusal,'log missing or invalid'):c.verify_outputs(work,console,0)
    def test_unclosed_group_does_not_walk_active_output_tree(self):
        def failed(*args,**kwargs):b.save(self.store.path/'runtime-unclosed.json',{'closure_verified':False});raise b.Refusal('Group closure unverified')
        with patch.object(c.os,'walk',side_effect=AssertionError('must not traverse active outputs')):
            with self.assertRaisesRegex(b.Refusal,'closure'):self.run_fixture(failed)
        self.assertFalse(json.loads((self.private/'result.json').read_text())['owned_process_group_closed'])

    def test_generated_hardlink_preserves_external_inode_permissions(self):
        external=self.root/'original';external.write_bytes(b'original');external.chmod(0o644)
        def bad(*args,**kwargs):
            self.successful_vendor(*args,**kwargs);os.link(external,kwargs['cwd']/'unexpected-output');return 0
        with self.assertRaisesRegex(b.Refusal,'Unsafe generated'):self.run_fixture(bad)
        self.assertEqual(external.stat().st_mode&0o777,0o644);self.assertEqual(external.read_bytes(),b'original')
        r=json.loads((self.private/'result.json').read_text());self.assertEqual(r['status'],'failed');self.assertFalse(r['compiler_execution_verified'])

if __name__=='__main__':unittest.main()

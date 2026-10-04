"""Offline synthetic compiler guards; no vendor or device operations."""
import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace as S
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import forgix_synthetic_candidate as c


class SyntheticCompiler(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.private=self.root/'.scratch/build';self.work=self.private/'work/gateware'
        self.work.mkdir(parents=True);self.out=self.work/'outflow';self.out.mkdir()
        self.frozen={'fixture':'0'*64}
        self.xml=f'''<project xmlns="http://www.efinixinc.com/enf_proj" name="{c.NAME}"><device_info><family name="Trion"/><device name="T8F49"/><timing_model name="I2"/></device_info><design_info><design_file name="{self.work/(c.NAME+'.v')}"/><design_file name="{self.work/c.CORE_NAME}"/></design_info><constraint_info><sdc_file name="{c.NAME}_merged.sdc"/></constraint_info><synthesis><param name="mode" value="speed"/></synthesis><bitstream_generation><param name="mode" value="passive"/><param name="width" value="1"/></bitstream_generation></project>'''
        iface='\n'.join('design.create_'+mode+'_gpio('+repr(name)+')\ndesign.assign_pkg_pin('+repr(name)+','+repr(pin)+')' for name,(mode,pin) in c.old.GPIO.items())
        peri='<design_db xmlns="http://www.efinixinc.com/peri_design_db" name="'+c.NAME+'" device_def="T8F49"><gpio_info>'+''.join('<gpio name="'+name+'" mode="'+mode+'"/>' for name,(mode,pin) in c.old.GPIO.items())+'</gpio_info></design_db>'
        content={c.NAME+'.xml':self.xml,c.CORE_NAME:(c.b.ROOT/c.g.CORE).read_text(),
                 c.NAME+'.v':f".SYSTEM_HZ(32'h1e84800)\n$readmemh(\"{c.NAME}_mem.init\", mem);",
                 c.NAME+'.sdc':c.old.CLOCK,c.NAME+'_merged.sdc':c.old.CLOCK,
                 c.NAME+'_mem.init':'4c\n69\n00\n','iface.py':iface,c.NAME+'.peri.xml':peri}
        for name,text in content.items():(self.work/name).write_text(text)
        (self.private/'csr.csv').write_text('csr_register,registers_counter,0x00001000,1,ro\ncsr_register,registers_scratch,0x00001004,1,rw\nmemory_region,synthetic_source,0x00010000,4096,io\n')
        (self.private/'console.log').write_text(''.join(s+' : PASS\n' for s in c.smoke.STAGES))
        (self.out/(c.NAME+'.log')).write_text(''.join('Stage completed: '+s+'\n' for s in c.smoke.STAGES))
        self.image=self.out/(c.NAME+'.hex');self.image.write_text('0123abcd\n')
        self.meta={'pins':c.old.PINS,'registers':{k:c.g.BASE+v for k,v in c.g.REGISTERS.items()},'source_sha256':self.frozen,
                   'generated_sha256':c.generated_hashes(self.work),'csr_sha256':c.b.sha(self.private/'csr.csv'),
                   'guard':{'sha256':c.b.sha(c.b.ROOT/'tools/forgix_spi_guard.py'),'idle_cycles':32,'turnaround_cycles':64}}
        self.save()
    def save(self):(self.private/'generated.json').write_text(json.dumps(self.meta))
    def tearDown(self):self.temp.cleanup()
    def test_fixed_profile_two_sources_and_false_physical_flags(self):
        r=c.verify_outputs(self.private,0,self.frozen)
        self.assertEqual(r['bitstream_sha256'],c.b.sha(self.image));self.assertEqual(len(r['outflow_reports']),2)
        for name in ('physical_confirmation','programming_admitted','resource_fit_reviewed','timing_closure_reviewed'):
            self.assertIs(c.PROFILE[name],False)
        self.assertEqual(c.vendor_command(Path('/software'))[-5:],[c.NAME+'.xml','--flow','compile','--timeout','300'])
    @unittest.skipUnless(importlib.util.find_spec('litex'),'Run the actual backend test in locked .#forgix')
    def test_real_pinned_xml_generator_two_design_inputs_and_speed_mode(self):
        from litex.build.efinix import efinity as e
        tool=e.EfinityToolchain.__new__(e.EfinityToolchain)
        install=self.root/'software';(install/'scripts').mkdir(parents=True);(install/'scripts/sw_version.txt').write_text(c.smoke.VERSION)
        tool.efinity_path=str(install);tool._build_name=c.NAME
        tool.platform=S(device='T8F49',family='Trion',timing_model='I2',spi_mode='passive',spi_width='1',
                        sources=[(str(self.work/(c.NAME+'.v')),'verilog','work'),(str(self.work/c.CORE_NAME),'verilog','work')],verilog_include_paths=[])
        tool._efx_map_params=e._default_efx_map_params();tool._efx_pnr_params=e._default_efx_pnr_params();tool._efx_pgm_params=e._default_efx_pgm_params()
        tool._efx_debugger_params={};tool._efx_security_params={};tool.ipmwriter=S(blocks=[]);tool.ifacewriter=S(xml_blocks=[],fix_xml=[])
        previous=Path.cwd()
        try:
            os.chdir(self.work)
            with patch.object(e,'load_efinity_env',return_value={}),patch.object(e.tools,'subprocess_call_filtered',return_value=0) as vendor:
                tool.build_project()
            self.assertEqual(vendor.call_args.args[0],[str(install)+'/bin/python3','iface.py'])
        finally:os.chdir(previous)
        c.validate_project(self.work)
        self.assertIn('value="speed"',(self.work/(c.NAME+'.xml')).read_text())
    @unittest.skipUnless(importlib.util.find_spec('litex'),'Run the actual SoC map test in locked .#forgix')
    def test_actual_soc_export_has_expected_two_registers_and_new_region(self):
        from litex.build.generic_platform import GenericPlatform
        from litex_boards.platforms import adiuvo_forgix as board
        from litex.soc.integration.export import get_csr_csv
        class Platform(GenericPlatform):
            default_clk_freq=32000000
            def __init__(self):super().__init__('T8F49I2',board._io,board._connectors)
            def do_finalize(self,fragment):pass
        soc=c.g.make_soc(Platform);soc.finalize()
        (self.private/'csr.csv').write_text(get_csr_csv(soc,soc.csr_regions,soc.constants,soc.bus.regions))
        c.validate_csr(self.private/'csr.csv')
    def test_foreign_or_duplicate_source_or_project_profile_refused(self):
        path=self.work/(c.NAME+'.xml')
        for bad in (self.xml.replace(str(self.work/c.CORE_NAME),'/foreign/source.v'),self.xml.replace(c.CORE_NAME,c.NAME+'.v'),
                    self.xml.replace('I2','C2'),self.xml.replace('passive','active'),self.xml.replace('value="1"','value="4"')):
            path.write_text(bad)
            with self.assertRaises(c.b.Refusal):c.validate_project(self.work)
        path.write_text(self.xml.replace(str(self.work/c.CORE_NAME),c.CORE_NAME).replace(str(self.work/(c.NAME+'.v')),c.NAME+'.v'))
        c.validate_project(self.work)
    def test_exact_source_redirection_only_no_additional_hdl(self):
        self.assertEqual(c.source_path(self.work,c.b.ROOT/c.g.CORE),self.work/c.CORE_NAME)
        self.assertEqual(c.source_path(self.work,self.work/(c.NAME+'.v')),self.work/(c.NAME+'.v'))
        for p in (self.work/'other.v',self.root/c.CORE_NAME):
            with self.assertRaises(c.b.Refusal):c.source_path(self.work,p)
    def test_core_memory_top_clock_or_project_changed_after_freeze_refused(self):
        for name in (c.CORE_NAME,c.NAME+'_mem.init',c.NAME+'.v',c.NAME+'.xml'):
            path=self.work/name;original=path.read_bytes();path.write_bytes(original+(b'\n<!--change-->\n' if name.endswith('.xml') else b'\n//change\n'))
            with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,0,self.frozen)
            path.write_bytes(original)
        top=self.work/(c.NAME+'.v');top.write_text(top.read_text().replace(c.NAME+'_mem.init','../foreign.init'))
        with self.assertRaises(c.b.Refusal):c.generated_hashes(self.work)
    def test_extra_gpio_guard_policy_or_register_map_refused(self):
        iface=self.work/'iface.py';text=iface.read_text();iface.write_text(text+'\ndesign.create_input_gpio("edge")\ndesign.assign_pkg_pin("edge","A5")\n')
        with self.assertRaises(c.b.Refusal):c.validate_interface(self.work)
        iface.write_text(text);self.meta['guard']['turnaround_cycles']=63;self.save()
        with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,0,self.frozen)
        csv=self.private/'csr.csv';csv.write_text(csv.read_text().replace('0x00010000','0x00020000'))
        with self.assertRaises(c.b.Refusal):c.validate_csr(csv)
    def test_missing_stage_log_or_image_and_stale_image_are_failure(self):
        console=self.private/'console.log';original=console.read_text();console.write_text(original.replace('interface : PASS\n',''))
        with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,0,self.frozen)
        console.write_text(original)
        with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,time.time_ns()+10**9,self.frozen)
        self.image.write_bytes(b'')
        with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,0,self.frozen)
        self.image.unlink()
        with self.assertRaises((c.b.Refusal,OSError)):c.verify_outputs(self.private,0,self.frozen)
    def test_symlink_hardlink_outputs_refused_without_changing_original(self):
        self.image.unlink();outside=self.root/'outside';outside.write_bytes(b'original');outside.chmod(0o644)
        os.link(outside,self.image)
        with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,0,self.frozen)
        self.assertFalse(c.smoke.harden_outputs(self.private));self.assertEqual(outside.stat().st_mode&0o777,0o644)
        self.image.unlink();self.image.symlink_to(outside)
        with self.assertRaises(c.b.Refusal):c.verify_outputs(self.private,0,self.frozen)
    def store(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'.gitignore').write_text('/.scratch/\n/.vendor/\n')
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','fixture'],check=True)
        store=c.b.Store(self.root)
        with store.locked():pass
        return store
    def test_unknown_closure_prevents_launch(self):
        store=self.store();(store.path/'runtime-unclosed.json').write_text('{}')
        with patch.object(c.old,'provenance',return_value=c.old.REVISIONS),patch.object(c,'source_hashes',return_value=self.frozen),patch.object(c.b,'run_owned',side_effect=AssertionError('no launch')):
            with self.assertRaisesRegex(c.b.Refusal,'closure'):c.compile_candidate(store,self.root/'.scratch/fresh')
    def launch(self,callback,hashes=None):
        store=self.store();install=self.root/'installation';(install/'scripts').mkdir(parents=True,exist_ok=True);(install/'scripts/efx_run.py').write_bytes(b'runner')
        target=self.root/'.scratch/new'
        with patch.object(c.old,'provenance',return_value=c.old.REVISIONS),patch.object(c,'source_hashes',side_effect=hashes or [self.frozen,self.frozen]),patch.object(store,'installed',return_value=(install,{'version':c.smoke.VERSION,'software_sha256':c.smoke.ARCHIVE_SHA})),patch.object(c.smoke,'RUNNER_SHA',c.b.sha(install/'scripts/efx_run.py')),patch.object(c.shutil,'which',side_effect=lambda n:'/nix/store/'+n+'/bin/'+n),patch.dict(os.environ,{'FORGIX_PYTHON':'/nix/store/python/bin/python'}),patch.object(c.b,'run_owned',side_effect=callback),patch.object(c,'verify_outputs',return_value={'bitstream_sha256':'1'*64,'bitstream_bytes':10}),patch.object(c.smoke,'harden_outputs',wraps=c.smoke.harden_outputs) as harden:
            try:return c.compile_candidate(store,target),target,harden.call_count
            except BaseException as error:return error,target,harden.call_count
    def test_timeout_retains_prefix_unknown_closure_and_never_traverses_output(self):
        def timeout(command,env,output,budget,owner,cwd):
            self.assertEqual(budget,330);self.assertEqual(command[-3:],['_worker','--private',str(cwd)])
            output.write(b'retained failure prefix');raise subprocess.TimeoutExpired(command,budget)
        error,target,harden=self.launch(timeout)
        self.assertIsInstance(error,subprocess.TimeoutExpired);self.assertEqual(harden,0)
        receipt=json.loads((target/'result.json').read_text())
        self.assertFalse(receipt['owned_process_group_closed']);self.assertFalse(receipt['programming_admitted'])
        self.assertEqual((target/'console.log').read_bytes(),b'retained failure prefix')
    def test_nonzero_vendor_and_postbuild_source_mutation_retained_failed(self):
        error,target,harden=self.launch(lambda *a,**k:7)
        self.assertIsInstance(error,c.b.Refusal);receipt=json.loads((target/'result.json').read_text())
        self.assertEqual(receipt['exit_code'],7);self.assertTrue(receipt['owned_process_group_closed']);self.assertEqual(receipt['status'],'failed')
        # Separate fresh path for a normal child but changed repository inputs.
        shutil.rmtree(target)
        error,target,harden=self.launch(lambda *a,**k:0,[self.frozen,{'fixture':'changed'}])
        self.assertIsInstance(error,c.b.Refusal);self.assertEqual(json.loads((target/'result.json').read_text())['status'],'failed')


if __name__=='__main__':unittest.main()

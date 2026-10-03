"""Offline candidate boundaries; no vendor compiler or device access."""
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
import forgix_fpga_candidate as c

XML = f'''<project xmlns="http://www.efinixinc.com/enf_proj" name="{c.NAME}"><device_info><family name="Trion"/><device name="T8F49"/><timing_model name="I2"/></device_info><design_info><design_file name="{c.NAME}.v"/></design_info><constraint_info><sdc_file name="{c.NAME}_merged.sdc"/></constraint_info><synthesis><param name="mode" value="speed"/></synthesis><bitstream_generation><param name="mode" value="passive"/><param name="width" value="1"/></bitstream_generation></project>'''

# Physical GPIO portion of actual backend-lowered candidate001 iface.py;
# software paths and unrelated vendor header are deliberately omitted.
IFACE = '\n'.join('design.create_'+mode+'_gpio('+repr(name)+')\ndesign.assign_pkg_pin('+repr(name)+','+repr(pin)+')' for name,(mode,pin) in c.GPIO.items())
PERI = '<design_db xmlns="http://www.efinixinc.com/peri_design_db" name="'+c.NAME+'" device_def="T8F49"><gpio_info>'+''.join('<gpio name="'+name+'" mode="'+mode+'"/>' for name,(mode,pin) in c.GPIO.items())+'</gpio_info></design_db>'

class Candidate(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
        self.private = self.root / '.scratch/candidate'; self.work = self.private / 'work/gateware'
        self.work.mkdir(parents=True); self.out = self.work / 'outflow'; self.out.mkdir()
        (self.work / (c.NAME + '.xml')).write_text(XML)
        (self.private / 'console.log').write_text(''.join(s+' : PASS\n' for s in c.smoke.STAGES))
        (self.out / (c.NAME + '.log')).write_text(''.join('Stage completed: '+s+'\n' for s in c.smoke.STAGES))
        self.image = self.out / (c.NAME + '.hex'); self.image.write_bytes(b'0123abcd\n')
        self.generated={'pins':c.PINS,'generated_sha256':{},'guard':{'sha256':b.sha(b.ROOT/'tools/forgix_spi_guard.py'),'idle_cycles':32,'turnaround_cycles':64}}
        content={c.NAME+'.v':'$readmemh("'+c.NAME+'_mem.init", mem);', c.NAME+'.sdc':c.CLOCK,'iface.py':IFACE,c.NAME+'_mem.init':'4c\n69\n'}
        for name,data in content.items():
            (self.work/name).write_text(data);self.generated['generated_sha256'][name]=b.sha(self.work/name)
        (self.work/(c.NAME+'.peri.xml')).write_text(PERI)
        (self.private / 'generated.json').write_text(json.dumps(self.generated))
    def tearDown(self):self.t.cleanup()
    def test_exact_speculative_profile_and_fresh_image(self):
        r=c.verify_outputs(self.private,0)
        self.assertEqual(r['bitstream_sha256'],b.sha(self.image))
        for k in ('physical_confirmation','programming_admitted','spi_turnaround_verified'):self.assertIs(c.PROFILE[k],False)
    def test_wrong_grade_active_config_or_source_escape_rejected(self):
        for old,new in [('I2','C2'),('passive','active'),(c.NAME+'.v','../../source.v')]:
            with self.subTest(new=new):
                (self.work/(c.NAME+'.xml')).write_text(XML.replace(old,new))
                with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
    def test_absolute_exact_private_rtl_only(self):
        xml=self.work/(c.NAME+'.xml')
        xml.write_text(XML.replace('name="'+c.NAME+'.v"','name="'+str(self.work/(c.NAME+'.v'))+'"'))
        c.validate_project(self.work)
        xml.write_text(XML.replace('name="'+c.NAME+'.v"','name="/other/forgix_candidate.v"'))
        with self.assertRaises(b.Refusal):c.validate_project(self.work)
    def test_lowered_physical_pins_and_direction_reject_extra_gpio(self):
        self.assertEqual(c.validate_interface(self.work),c.PINS)
        for bad in (IFACE.replace("'F2'","'G4'"),IFACE.replace('create_inout_gpio','create_output_gpio'),IFACE+'\ndesign.create_input_gpio("edge")\ndesign.assign_pkg_pin("edge","A5")'):
            with self.subTest(bad=bad[-40:]):
                (self.work/'iface.py').write_text(bad)
                with self.assertRaises(b.Refusal):c.validate_interface(self.work)
        (self.work/'iface.py').write_text(IFACE)
        (self.work/(c.NAME+'.peri.xml')).write_text(PERI.replace('mode="inout"','mode="output"'))
        with self.assertRaises(b.Refusal):c.validate_interface(self.work)
    def test_consumed_memory_input_hash_and_path_are_bound(self):
        (self.work/(c.NAME+'_mem.init')).write_text('00\n')
        with self.assertRaisesRegex(b.Refusal,'hashes'):c.verify_outputs(self.private,0)
        (self.work/(c.NAME+'.v')).write_text('$readmemh("../foreign.init", mem);')
        with self.assertRaisesRegex(b.Refusal,'memory'):c.generated_hashes(self.work)
    def test_clock_change_rejected(self):
        (self.work/(c.NAME+'.sdc')).write_text(c.CLOCK.replace('31.25','83.333'))
        with self.assertRaisesRegex(b.Refusal,'clock'):c.verify_outputs(self.private,0)
    def test_guard_source_and_cycle_policy_are_bound(self):
        self.generated['guard']['turnaround_cycles']=63
        (self.private/'generated.json').write_text(json.dumps(self.generated))
        with self.assertRaisesRegex(b.Refusal,'Guard'):c.verify_outputs(self.private,0)
    def test_missing_stage_and_pgmpass_without_image_rejected(self):
        (self.private/'console.log').write_text('map : PASS\npnr : PASS\npgm : PASS\n')
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
        (self.private/'console.log').write_text(''.join(s+' : PASS\n' for s in c.smoke.STAGES));self.image.unlink()
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
    def test_stale_empty_or_linked_output_rejected(self):
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,time.time_ns()+1000000000)
        self.image.write_bytes(b'')
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
        self.image.unlink(); external=self.root/'original';external.write_bytes(b'0123');os.link(external,self.image)
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
        self.assertFalse(c.smoke.harden_outputs(self.private));self.assertEqual(external.stat().st_mode&0o777,0o644)
    def test_outflow_symlink_and_added_edge_pin_rejected(self):
        (self.private/'generated.json').write_text(json.dumps({'pins':dict(c.PINS,user_io=['A5'])}))
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
        self.image.unlink();self.image.symlink_to(self.root/'original')
        with self.assertRaises(b.Refusal):c.verify_outputs(self.private,0)
    def test_fresh_path_and_unknown_closure_gate_before_worker(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'.gitignore').write_text('/.scratch/\n/.vendor/\n');store=b.Store(self.root)
        with self.assertRaisesRegex(b.Refusal,'fresh'):c.smoke.private_path(store,self.private)
        with store.locked():pass
        (store.path/'runtime-unclosed.json').write_text('{}')
        with patch.object(c,'provenance',return_value={}),patch.object(c,'source_hashes',return_value={}),patch.object(b,'run_owned',side_effect=AssertionError('no launch')):
            with self.assertRaisesRegex(b.Refusal,'closure'):c.compile_candidate(store,self.root/'.scratch/new')
    def test_pinned_toolchain_refuses_other_revision(self):
        with patch.dict(os.environ,{'FORGIX_TOOLCHAIN_PROVENANCE':json.dumps(c.REVISIONS)}):self.assertEqual(c.provenance(),c.REVISIONS)
        with patch.dict(os.environ,{'FORGIX_TOOLCHAIN_PROVENANCE':'{}'}):
            with self.assertRaises(b.Refusal):c.provenance()
    def test_owned_command_timeout_and_failure_receipt(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'.gitignore').write_text('/.scratch/\n/.vendor/\n');store=b.Store(self.root)
        with store.locked():pass
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','fixture'],check=True)
        install=self.root/'install';(install/'scripts').mkdir(parents=True);(install/'scripts/efx_run.py').write_bytes(b'runner')
        new=self.root/'.scratch/new'
        def failed(command,env,output,timeout,owner,cwd):
            self.assertEqual(timeout,330);self.assertEqual(command[-3:],['_worker','--private',str(new)])
            self.assertEqual(command[1:6],['/nix/store/env/bin/env','-u','PYTHONHOME','-u','PYTHONPATH'])
            self.assertEqual(env['LITEX_ENV_EFINITY'],str(install));output.write(b'failed prefix')
            raise subprocess.TimeoutExpired(command,timeout)
        with patch.object(c,'provenance',return_value=c.REVISIONS),patch.object(c,'source_hashes',return_value={}),patch.object(store,'installed',return_value=(install,{'version':c.smoke.VERSION,'software_sha256':c.smoke.ARCHIVE_SHA})),patch.object(c.smoke,'RUNNER_SHA',b.sha(install/'scripts/efx_run.py')),patch.object(c.shutil,'which',side_effect=lambda n:'/nix/store/'+n+'/bin/'+n),patch.dict(os.environ,{'FORGIX_PYTHON':'/nix/store/python/bin/python'}),patch.object(b,'run_owned',side_effect=failed):
            with self.assertRaises(subprocess.TimeoutExpired):c.compile_candidate(store,new)
        r=json.loads((new/'result.json').read_text());self.assertEqual(r['status'],'failed');self.assertFalse(r['owned_process_group_closed'])
        self.assertFalse(r['programming_admitted']);self.assertEqual((new/'console.log').read_bytes(),b'failed prefix')

    def test_actual_pinned_project_generator_scopes_configuration_mode(self):
        try:
            from litex.build.efinix import efinity as e
        except ImportError:self.skipTest('Requires locked Forgix shell')
        from types import SimpleNamespace as S
        install=self.root/'software';(install/'scripts').mkdir(parents=True)
        (install/'scripts/sw_version.txt').write_text('2026.1.132')
        tool=e.EfinityToolchain.__new__(e.EfinityToolchain)
        tool.efinity_path=str(install);tool._build_name=c.NAME
        tool.platform=S(device='T8F49',family='Trion',timing_model='I2',spi_mode='passive',spi_width='1',
                        sources=[(c.NAME+'.v','verilog',None)],verilog_include_paths=[])
        tool._efx_map_params=e._default_efx_map_params();tool._efx_pnr_params=e._default_efx_pnr_params()
        tool._efx_pgm_params=e._default_efx_pgm_params();tool._efx_debugger_params={};tool._efx_security_params={}
        tool.ipmwriter=S(blocks=[]);tool.ifacewriter=S(xml_blocks=[],fix_xml=[])
        cwd=Path.cwd()
        try:
            os.chdir(self.work)
            with patch.object(e,'load_efinity_env',return_value={}),patch.object(e.tools,'subprocess_call_filtered',return_value=0) as vendor:
                tool.build_project()
            self.assertEqual(vendor.call_args.args[0], [str(install)+'/bin/python3','iface.py'])
        finally:os.chdir(cwd)
        self.assertIn('value="speed"',(self.work/(c.NAME+'.xml')).read_text())
        c.validate_project(self.work)

    def test_real_soc_only_four_ports_counter_scratch_no_leds(self):
        try:
            from litex.build.generic_platform import GenericPlatform
            from litex_boards.platforms import adiuvo_forgix as board
        except ImportError:self.skipTest('Run in the locked Forgix shell for real RTL')
        class Platform(GenericPlatform):
            default_clk_freq=32000000
            def __init__(self):super().__init__('T8F49I2',board._io,board._connectors)
            def do_finalize(self,fragment):pass
        original=board.Platform
        soc=c.make_soc(Platform);self.assertIs(board.Platform,original)
        soc.finalize(); fragment=soc.get_fragment();v=soc.platform.get_verilog(fragment,name=c.NAME)
        pins={name:pins for name,pins,others,res in soc.platform.resolve_signals(v.ns)[0]}
        self.assertEqual(pins,c.PINS);self.assertFalse(hasattr(soc,'leds'))
        self.assertEqual(soc.registers.counter.size,32);self.assertEqual(soc.registers.scratch.size,32)
        self.assertIn('spibone',str(v));self.assertNotIn('user_led',str(v))

if __name__=='__main__':unittest.main()

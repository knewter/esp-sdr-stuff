"""Fail-closed loaded reset recognizer and private stream artifact admission."""
import hashlib,json,os,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import audit_forgix_synthetic_startup as a

class Startup(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.sdk=self.root/'sdk';self.elf=bytearray(4096)
  self.layout={'load_segments':[{'vaddr':0x20000000,'offset':0,'filesz':4096}],
   'symbols':{'runtime_init_early_resets':0x20000101,'runtime_init_post_clock_resets':0x20000181,
    'runtime_run_initializers':0x20000201,'__pre_init_runtime_init_early_resets':0x20000300,
    '__pre_init_runtime_init_post_clock_resets':0x20000304}}
  self.elf[0x100:0x100+len(a.EARLY)]=a.EARLY
  struct.pack_into('<5I',self.elf,0x11c,0x40022000,0x40023000,7,0x40020000,7)
  self.elf[0x200:0x200+len(a.RUNNER)]=a.RUNNER
  struct.pack_into('<2I',self.elf,0x218,0x20000300,0x20000308)
  struct.pack_into('<2I',self.elf,0x300,0x20000101,0x20000181)
  texts=['/* fixture SDK runtime source */',
   '\n'.join(f'#define RESETS_RESET_{n}_BITS _u(0x{v:x})' for n,v in [('IO_BANK0',1),('PADS_BANK0',2),('PIO0',4)]),
   '\n'.join(f'#define IO_BANK0_GPIO{p}_CTRL_FUNCSEL_RESET _u(0x1f)' for p in (1,2,3,4,5,19)),
   '\n'.join(f'#define PADS_BANK0_GPIO{p}_{n}_RESET _u(0x{v:x})' for p in (1,2,3,4,5,19) for n,v in [('ISO',1),('PDE',1),('PUE',0)])]
  for name,text in zip(a.SDK_FILES,texts):
   p=self.sdk/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 def tearDown(self):self.temp.cleanup()
 def run_reset(self):return a.linked_resets(self.elf,self.layout,self.sdk)
 def test_loaded_fixed_sequence_and_unique_reset_slots(self):
  r=self.run_reset();self.assertEqual(len(r['initializer_bindings']),2)
  self.assertTrue(all(all(x.values()) for x in r['reset_blocks'].values()))
  self.assertEqual(r['documented_gpio_reset_defaults']['3'],{'function_select':31,'pad_isolated':True,'pull_down':True,'pull_up':False})
 def test_each_instruction_literal_mapping_and_mask_mutation_refused(self):
  original=bytes(self.elf)
  for off in list(range(0x100,0x100+len(a.EARLY)))+list(range(0x200,0x200+len(a.RUNNER)))+[0x11c,0x120,0x124,0x128,0x12c]:
   with self.subTest(offset=off):
    self.elf=bytearray(original);self.elf[off]^=1
    with self.assertRaises(ValueError):self.run_reset()
 def test_initializer_range_duplicate_missing_and_changed_slot_refused(self):
  for mode in ('outside','duplicate','missing','changed','huge','unaligned'):
   with self.subTest(mode=mode):
    old=bytes(self.elf);symbols=dict(self.layout['symbols'])
    if mode=='outside':struct.pack_into('<I',self.elf,0x218,0x20000fff)
    elif mode=='duplicate':struct.pack_into('<I',self.elf,0x304,0x20000101)
    elif mode=='missing':del self.layout['symbols']['__pre_init_runtime_init_early_resets']
    elif mode=='changed':struct.pack_into('<I',self.elf,0x300,0x20000181)
    elif mode=='huge':struct.pack_into('<I',self.elf,0x21c,0x20000ffc)
    else:struct.pack_into('<I',self.elf,0x21c,0x20000307)
    with self.assertRaises(ValueError):self.run_reset()
    self.elf=bytearray(old);self.layout['symbols']=symbols
 def test_nonloaded_marker_and_sdk_macro_conflicts_refused(self):
  self.layout['load_segments'][0]['filesz']=0x110
  with self.assertRaises(ValueError):self.run_reset()
  self.layout['load_segments'][0]['filesz']=4096;p=self.sdk/a.SDK_FILES[1]
  p.write_text(p.read_text()+'\n#define RESETS_RESET_PIO0_BITS _u(0x4)')
  with self.assertRaises(ValueError):self.run_reset()
 def test_private_symlink_hardlink_and_empty_inputs_refused(self):
  p=self.root/'input';p.write_bytes(b'x');self.assertEqual(a.regular(p,1),p)
  q=self.root/'alias';q.symlink_to(p)
  with self.assertRaises(ValueError):a.regular(q,2)
  q.unlink();os.link(p,q)
  with self.assertRaises(ValueError):a.regular(p,2)
  q.unlink();p.write_bytes(b'')
  with self.assertRaises(ValueError):a.regular(p,2)
 def test_cli_refusal_is_typed_without_private_path_or_partial_output(self):
  out=self.root/'PRIVATE-output';r=subprocess.run([sys.executable,str(ROOT/'tools/audit_forgix_synthetic_startup.py'),
   '--artifact',str(self.root/'PRIVATE-input'),'--output',str(out)],capture_output=True,text=True,timeout=20)
  self.assertEqual(r.returncode,2);self.assertEqual(r.stderr,'');self.assertNotIn('PRIVATE',r.stdout)
  self.assertEqual(json.loads(r.stdout),{'result':'failed','error_kind':'ValueError','hardware_opened':False,'loading_admitted':False})
  self.assertFalse(out.exists())
 def test_whole_manifest_hash_set_source_and_nar_fail_closed(self):
  folder=self.root/'.scratch/artifact';folder.mkdir(parents=True)
  exports={n:hashlib.sha256(b'x').hexdigest() for n in a.EXPORTS}
  for n in exports:(folder/n).write_bytes(b'x')
  sources={n:hashlib.sha256(b'source').hexdigest() for n in a.FILES}
  m={'kind':'forgix-synthetic-stream-offline-build','status':'built_layout_guard_passed','sdk_revision':a.SDK,
   'tinyusb_revision':a.TINY,'sdk_nar_hash':a.NAR,'linked_embedded_image_verified':True,'inputs_unchanged_after_build':True,
   'hardware_opened':False,'loading_admitted':False,'artifact_sha256':exports,'source_sha256':sources,
   'source_commit':'1'*40,'layout':self.layout,'sdk_path':'/nix/store/fixture-sdk'}
  def call(cmd,**kw):return a.NAR+'\n' if cmd[0]=='nix' else b'source'
  for key,value in [('status','failed'),('hardware_opened',True),('sdk_nar_hash','wrong'),('source_commit','HEAD'),
                    ('artifact_sha256',{}),('source_sha256',{}),('layout',{}),('sdk_path','/tmp/sdk')]:
   with self.subTest(field=key):
    (folder/'manifest.json').write_text(json.dumps({**m,key:value}))
    with patch.object(a,'ROOT',self.root),patch.object(a,'inspect_elf',return_value=self.layout),patch.object(a.subprocess,'check_output',side_effect=call):
     with self.assertRaises(ValueError):a.audit(folder)
  (folder/'manifest.json').write_text(json.dumps(m))
  with patch.object(a,'ROOT',self.root),patch.object(a,'inspect_elf',return_value=self.layout),patch.object(a.subprocess,'check_output',side_effect=call),patch.object(a,'linked_resets',return_value={}):
   r=a.audit(folder);self.assertFalse(r['whole_boot_path_qualified']);self.assertFalse(r['loading_admitted'])
  (folder/'symbols.txt').write_bytes(b'changed')
  with patch.object(a,'ROOT',self.root):
   with self.assertRaises(ValueError):a.audit(folder)

if __name__=='__main__':unittest.main()

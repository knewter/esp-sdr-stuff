"""Distinct project, artifact and builder refusals; no vendor/ARM execution."""
import hashlib,json,os,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import forgix_clock_candidate as fpga
import forgix_clock_artifact as elf
import build_forgix_clock_observer as build
from test_forgix_usb_ram import fixture

def clock_elf():
 d=fixture();d.extend(bytes(0x10000-len(d)));names=d[0x3000:0x3200];entries=[]
 size=struct.unpack_from('<I',d,0x3400+4*40+20)[0]
 for off in range(16,size,16):
  n,v,s,info,other,index=struct.unpack_from('<IIIBBH',d,0x2800+off);entries.append((bytes(names[n:names.index(0,n)]).decode(),v,s,info,index))
 entries.extend((n,0x20000281+4*i,4,0x12,1) for i,n in enumerate(('fc_init','fc_feed','fc_step','fc_crc','observer_capture','observer_rp_io','bridge_configure','bridge_uid_init','pico_get_unique_board_id_string')))
 entries.extend([('clock_layout',0x20000480,28,0x11,1),('clock_engine',0x20001000,1200,0x11,2),('bridge_fpga_image',0x20000500,4,0x11,1),('bridge_fpga_image_bytes',0x20000510,4,0x11,1),('bridge_fpga_sha256',0x20000520,32,0x11,1),('bridge_fpga_crc32',0x20000540,4,0x11,1),('forgix_clock_period_program_instructions',0x20000580,20,0x01,1),('forgix_clock_period_program',0x200005a0,8,0x01,1)])
 names=bytearray(b'\0');symbols=bytearray(16)
 for name,v,s,i,index in entries:
  n=len(names);names.extend(name.encode()+b'\0');symbols.extend(struct.pack('<IIIBBH',n,v,s,i,0,index))
 d[0xe000:0xe000+280]=d[0x3400:0x3400+280];struct.pack_into('<I',d,32,0xe000)
 struct.pack_into('<II',d,0xe000+4*40+16,0x8000,len(symbols));struct.pack_into('<II',d,0xe000+5*40+16,0xa000,len(names));d[0x8000:0x8000+len(symbols)]=symbols;d[0xa000:0xa000+len(names)]=names
 struct.pack_into('<I',d,52+20,0x4000);struct.pack_into('<I',d,0xe000+2*40+20,0x3800)
 from forgix_usb_ram_artifact import PROFILE
 d[0x1300:0x1300+len(PROFILE)]=bytes(len(PROFILE));d[0x1300:0x1300+len(elf.PROFILE)]=elf.PROFILE
 struct.pack_into('<7I',d,0x1480,1200,128,128,256,512,768,96);struct.pack_into('<I',d,0x1510,4)
 struct.pack_into('<10H',d,0x1580,0x2020,0x20a0,0xa02b,0x00c5,0x0006,0x0043,0x00c8,0x0046,0xa0c1,0x8020);struct.pack_into('<IBbBB',d,0x15a0,0x20000580,10,-1,0,0)
 return d

class Guard(unittest.TestCase):
 def test_explicit_new_elf_policy_and_static_layout(self):
  d=clock_elf();r=elf.inspect_elf(d);self.assertEqual(r['application_policy'],'clock-observer')
  from forgix_usb_ram_artifact import inspect_elf
  for policy in ('usb','spi-bridge','spi-config-bridge','synthetic-stream'):
   with self.subTest(policy=policy),self.assertRaises(ValueError):inspect_elf(d,application=policy)
 def test_flash_dynamic_profile_tail_and_engine_layout_refused(self):
  for change in ('flash','dynamic','tail','layout','pio-set','pio-pointer'):
   d=clock_elf()
   if change=='flash':struct.pack_into('<II',d,52+8,0x10000000,0x10000000)
   elif change=='dynamic':struct.pack_into('<I',d,52,2)
   elif change=='tail':d[0x1300:0x1300+len(elf.PROFILE)]=bytes(len(elf.PROFILE));d.extend(elf.PROFILE)
   elif change=='pio-set':struct.pack_into('<H',d,0x1580,0xe081)
   elif change=='pio-pointer':struct.pack_into('<I',d,0x15a0,0x20000582)
   else:struct.pack_into('<I',d,0x1480+4*4,513)
   with self.subTest(change=change),self.assertRaises(ValueError):elf.inspect_elf(d)
 def test_descriptor_is_distinct_and_source_unchanged(self):
  original=(ROOT/build.BRIDGE/'usb_descriptors.c').read_bytes();converted=build.descriptor(original)
  self.assertIn(b'.idProduct=0x4014',converted);self.assertIn(b'Forgix Clock RAM observer v1',converted);self.assertIn(b'.iSerialNumber=3',converted)
  with self.assertRaises(ValueError):build.descriptor(converted)
  self.assertEqual((ROOT/build.BRIDGE/'usb_descriptors.c').read_bytes(),original)
 def test_fresh_import_transitive_tools_are_explicit(self):
  script="import sys,json;from pathlib import Path;r=Path(sys.argv[1]);sys.path.insert(0,str(r/'tools'));import build_forgix_clock_observer;print(json.dumps([str(Path(m.__file__).resolve().relative_to(r)) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(r/'tools')]))"
  actual=json.loads(subprocess.check_output([sys.executable,'-c',script,str(ROOT)],text=True,timeout=20));self.assertLessEqual(set(actual),set(build.FILES))
 def test_exact_clock_project_and_pin_mapping(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);ns=fpga.smoke.NS[1:-1]
   xml=f'<project xmlns="{ns}" name="{fpga.NAME}" location="{p}" sw_version="{fpga.smoke.VERSION}" last_change_date="Date : 2026-10-04 09:00"><device_info><family name="Trion"/><device name="T8F49"/><timing_model name="I2"/></device_info><design><design_file name="{p/(fpga.NAME+".v")}"/></design><constraints><sdc_file name="{fpga.NAME}_merged.sdc"/></constraints><synthesis><param name="mode" value="speed"/></synthesis><bitstream_generation><param name="mode" value="passive"/><param name="width" value="1"/></bitstream_generation></project>'
   (p/(fpga.NAME+'.xml')).write_text(xml);(p/(fpga.NAME+'.v')).write_text('module observer;endmodule\n');(p/(fpga.NAME+'.sdc')).write_text(fpga.old.CLOCK+'\n')
   iface='\n'.join(f'design.create_{mode}_gpio("{n}")\ndesign.assign_pkg_pin("{n}","{pin}")' for n,(mode,pin) in fpga.GPIO.items());(p/'iface.py').write_text(iface)
   (p/(fpga.NAME+'.peri.xml')).write_text(f'<design xmlns="http://www.efinixinc.com/peri_design_db" name="{fpga.NAME}" device_def="T8F49">'+''.join(f'<gpio name="{n}" mode="{m}"/>' for n,(m,pin) in fpga.GPIO.items())+'</design>')
   fpga.project(p);fpga.interface(p);self.assertNotIn(b'location=',fpga.rewrite(xml.encode(),p))
   for bad in (xml.replace('I2','C2'),xml.replace('passive','active'),xml.replace(str(p/(fpga.NAME+'.v')),'/foreign.v')):
    (p/(fpga.NAME+'.xml')).write_text(bad)
    with self.assertRaises(fpga.b.Refusal):fpga.project(p)
   (p/(fpga.NAME+'.xml')).write_text(xml);(p/'iface.py').write_text(iface+'\ndesign.create_input_gpio("edge")\ndesign.assign_pkg_pin("edge","A5")')
   with self.assertRaises(fpga.b.Refusal):fpga.interface(p)
 def test_generated_symlink_hardlink_and_memory_refused(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);f=p/'f';f.write_bytes(b'a');linked=p/'linked';os.link(f,linked)
   with self.assertRaises(fpga.b.Refusal):fpga.regular(linked)
   linked.unlink();linked.symlink_to(f)
   with self.assertRaises(fpga.b.Refusal):fpga.regular(linked)

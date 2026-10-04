"""New profile/map/image/layout refusals; old policies remain separate."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_forgix_synthetic_stream as build
import forgix_synthetic_image as image
from forgix_usb_ram_artifact import inspect_elf,PROFILE,STREAM_PROFILE
from test_forgix_usb_ram import fixture
from test_forgix_synthetic_candidate import SyntheticCompiler

class Request(C.Structure):
    _fields_=[('op',C.c_uint8),('nonce',C.c_uint8*16),('sequence',C.c_uint32),('address',C.c_uint32),('value',C.c_uint32)]

def stream_elf():
    d=fixture();d.extend(bytes(0x10000-len(d)))
    # Rebuild symbol/string tables, retaining actual existing layout symbols.
    oldnames=d[0x3000:0x3200];entries=[]
    size=struct.unpack_from('<I',d,0x3400+4*40+20)[0]
    for off in range(16,size,16):
        n,v,s,info,other,index=struct.unpack_from('<IIIBBH',d,0x2800+off)
        end=oldnames.index(0,n);entries.append((bytes(oldnames[n:end]).decode(),v,s,info,index))
    required=['fs_init','fs_command','fs_step','fs_source_packet','fs_platform_transfer','fs_platform_configure',
        'fs_platform_prepare','fs_platform_safe','fsg_batch_encode','bridge_wire_response','bridge_configure',
        'bridge_uid_init','pico_get_unique_board_id_string']
    entries.extend((n,0x20000281+i*4,4,0x12,1) for i,n in enumerate(required))
    entries.extend([('stream_layout',0x20000480,28,0x11,1),('stream_engine',0x20001000,12000,0x11,2),
        ('bridge_fpga_image',0x20000500,4,0x11,1),('bridge_fpga_image_bytes',0x20000510,4,0x11,1),
        ('bridge_fpga_sha256',0x20000520,32,0x11,1),('bridge_fpga_crc32',0x20000540,4,0x11,1)])
    names=bytearray(b'\0');syms=bytearray(16)
    for n,v,s,info,index in entries:
        pos=len(names);names.extend(n.encode()+b'\0');syms.extend(struct.pack('<IIIBBH',pos,v,s,info,0,index))
    sections=bytes(d[0x3400:0x3400+280]);d[0xe000:0xe000+280]=sections
    struct.pack_into('<I',d,32,0xe000)
    struct.pack_into('<II',d,0xe000+4*40+16,0x8000,len(syms))
    struct.pack_into('<II',d,0xe000+5*40+16,0xa000,len(names))
    d[0x8000:0x8000+len(syms)]=syms;d[0xa000:0xa000+len(names)]=names
    struct.pack_into('<I',d,52+20,0x4000)
    struct.pack_into('<I',d,0xe000+2*40+20,0x3800)
    d[0x1300:0x1300+len(PROFILE)]=bytes(len(PROFILE));d[0x1300:0x1300+len(STREAM_PROFILE)]=STREAM_PROFILE
    struct.pack_into('<7I',d,0x1480,12000,1024,8192,256,464,128,16)
    d[0x1500:0x1504]=b'\x01\x23\xab\xcd';struct.pack_into('<I',d,0x1510,4)
    return d

class StreamBuild(unittest.TestCase):
    def test_actual_tool_import_chain_and_project_are_frozen(self):
        imported={Path(m.__file__).resolve().relative_to(ROOT).as_posix() for m in tuple(sys.modules.values())
            if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(ROOT/'tools')}
        self.assertLessEqual(imported,set(build.FILES))
        self.assertLessEqual(set(build.PROJECT.values()),set(build.FILES))
        self.assertIn('firmware/forgix-synthetic-source/source.v',build.FILES)
        self.assertIn('nix/forgix-toolchain.nix',build.FILES)
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();p=Path(cls.temp.name)/'packet.so'
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
            '-I'+str(ROOT/'firmware/forgix-spi-bridge'),'-I'+str(ROOT/'firmware/forgix-synthetic-stream'),
            str(ROOT/'firmware/forgix-synthetic-stream/wire_packet.c'),str(ROOT/'firmware/forgix-spi-bridge/protocol.c'),'-o',str(p)],check=True,timeout=30)
        cls.lib=C.CDLL(str(p));cls.lib.fs_source_packet.argtypes=[C.POINTER(Request),C.POINTER(C.c_uint8)];cls.lib.fs_source_packet.restype=C.c_uint
        cls.lib.bridge_wire_request.argtypes=cls.lib.fs_source_packet.argtypes;cls.lib.bridge_wire_request.restype=C.c_uint
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_actual_c_exact_new_map_and_old_whitelist_unchanged(self):
        for off in range(0,0x9c,4):
            for write in (False,True):
                values=(0,1,2,4,8,0xffffffff) if write else (0,)
                for value in values:
                    r=Request(op=3 if write else 2,address=0x10000+off,value=value);buf=(C.c_uint8*9)()
                    n=self.lib.fs_source_packet(C.byref(r),buf)
                    allowed=(off not in (12,64)) if not write else (off in range(16,40,4) or off==64 or (off==12 and value in (1,2,4)))
                    self.assertEqual(bool(n),allowed,(off,write,value))
                    if n:self.assertEqual(bytes(buf[:n]),bytes([0 if write else 1])+r.address.to_bytes(4,'big')+(value.to_bytes(4,'big') if write else b''))
                    self.assertEqual(self.lib.bridge_wire_request(C.byref(r),(C.c_uint8*9)()),0)
        for addr in (0,0x1000,0x1004,0x10001,0x1009c,0xffffffff):
            self.assertEqual(self.lib.fs_source_packet(C.byref(Request(op=2,address=addr)),(C.c_uint8*9)()),0)
    def test_staged_wire_body_identical_and_legacy_dispatcher_absent(self):
        original=(ROOT/'firmware/forgix-spi-bridge/main.c').read_bytes();out=image.wire_primitives(original)
        for name,end in [('wire_end','static unsigned wire_prepare'),('wire_prepare','static pio_sm_config wire_config'),('wire_config','unsigned bridge_spi_transaction')]:
            start=original.index(('void '+name if name=='wire_end' else ('unsigned '+name if name=='wire_prepare' else 'pio_sm_config '+name)).encode())
            finish=original.index(end.encode(),start)
            self.assertIn(original[start:finish],out)
        start=original.index(b'unsigned bridge_spi_transaction');stop=original.index(b'int main(void) {')
        self.assertIn(original[start:stop],out)
        self.assertNotIn(b'int main(',out);self.assertNotIn(b'bridge_admit(',out)
        with self.assertRaises(Exception):image.wire_primitives(original.replace(b'int main(void) {',b'int main() {'))
    def test_distinct_usb_identity_and_startup_source_order(self):
        old=(ROOT/'firmware/forgix-spi-bridge/usb_descriptors.c').read_bytes();new=build.descriptor(old)
        self.assertIn(b'.idProduct=0x4013',new);self.assertIn(b'.iSerialNumber=3',new);self.assertIn(b'pico_get_unique_board_id_string',new)
        with self.assertRaises(ValueError):build.descriptor(new)
        main=(ROOT/'firmware/forgix-synthetic-stream/main.c').read_text()
        self.assertLess(main.index('watchdog_enable(2000,false)'),main.index('bridge_uid_init('))
        self.assertLess(main.index('bridge_uid_init('),main.index('tud_init(0)'))
        self.assertLess(main.index('tud_init(0)'),main.index('fs_init('))
        self.assertIn('stream_engine.boot=boot',main);self.assertIn('watchdog_reboot(0,0,1)',main)
        self.assertNotIn('printf(',main);self.assertNotIn('gpio_init(',main)
    def test_separate_real_geometry_policy_and_old_policy_refusals(self):
        d=stream_elf();r=inspect_elf(d,application='synthetic-stream');self.assertEqual(r['allocated_load_bytes'],20480)
        for policy in ('usb','spi-bridge','spi-config-bridge'):
            with self.assertRaises(ValueError):inspect_elf(d,application=policy)
    def test_compiled_queue_batch_pending_and_image_allocation_mutations(self):
        for offset,value in ((0,8192),(4,11999),(8,4096),(12,1024),(16,8192),(20,1000),(24,15)):
            d=stream_elf();struct.pack_into('<I',d,0x1480+offset,value)
            with self.assertRaises(ValueError):inspect_elf(d,application='synthetic-stream')
        for size in (0,196609):
            d=stream_elf();struct.pack_into('<I',d,0x1510,size)
            with self.assertRaises(ValueError):inspect_elf(d,application='synthetic-stream')
    def test_budget_flash_alias_dynamic_marker_and_required_symbols(self):
        for off,value in ((52+8,0x10000000),(52+12,0x10000000),(52+20,256*1024),(84,2)):
            d=stream_elf();struct.pack_into('<I',d,off,value)
            with self.assertRaises(ValueError):inspect_elf(d,application='synthetic-stream')
        d=stream_elf();d[0x1300:0x1300+len(STREAM_PROFILE)]=bytes(len(STREAM_PROFILE));d.extend(STREAM_PROFILE)
        with self.assertRaises(ValueError):inspect_elf(d,application='synthetic-stream')
        d=stream_elf();d[d.index(b'fs_step\0',0xa000)]=ord('x')
        with self.assertRaises(ValueError):inspect_elf(d,application='synthetic-stream')
    def test_exact_synthetic_image_manifest_and_preserved_hex(self):
        case=SyntheticCompiler('test_fixed_profile_two_sources_and_false_physical_flags');case.setUp()
        try:
            original=case.image.read_bytes();case.image.write_bytes(b'01\n23\nab\ncd\n')
            data=b'committed fixture source';digest=hashlib.sha256(data).hexdigest();case.frozen={'fixture':digest};case.meta['source_sha256']=case.frozen;case.save()
            # Copy only known source/guard bytes into the isolated fixture root.
            for n in (image.compiler.g.CORE,'tools/forgix_spi_guard.py'):
                p=case.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
            with patch.object(image.compiler.b,'ROOT',case.root),patch.object(image.compiler,'INPUTS',('fixture',)),patch.object(image.subprocess,'check_output',return_value=data):
                verified=image.compiler.verify_outputs(case.private,1,case.frozen)
                m={**image.compiler.PROFILE,**verified,'status':'passed','exit_code':0,'owned_process_group_closed':True,
                    'private_generated_files_verified':True,'source_commit':'a'*40,'source_sha256':case.frozen,'started_at_unix_ns':1}
                path=case.private/'result.json';path.write_text(json.dumps(m));before=case.image.read_bytes()
                decoded,binding=image.candidate(case.private);self.assertEqual(decoded,bytes.fromhex('0123abcd'));self.assertFalse(binding['loading_admitted'])
                for key,value in [('kind','forgix-offline-fpga-candidate'),('exit_code',False),('synthetic_abi',True),('physical_confirmation',True),('status','failed'),('bitstream_sha256','0'*64)]:
                    path.write_text(json.dumps({**m,key:value}))
                    with self.assertRaises(Exception):image.candidate(case.private)
                self.assertEqual(case.image.read_bytes(),before)
                path.write_text(json.dumps(m));case.image.write_bytes(b'0123abcd\n')
                # Rehashed manifest alone cannot qualify invalid image encoding.
                changed=image.compiler.verify_outputs(case.private,1,case.frozen);path.write_text(json.dumps({**m,**changed}))
                with self.assertRaises(Exception):image.candidate(case.private)
            case.image.write_bytes(original)
        finally:case.tearDown()

if __name__=='__main__':unittest.main()

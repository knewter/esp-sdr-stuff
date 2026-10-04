"""Actual configuration C/fake SDK and host prefix handling. No physical proof."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_config as host
from forgix_usb_ram_artifact import inspect_elf,CONFIG_PROFILE,PROFILE
from test_forgix_usb_ram import fixture
U8=C.c_uint8
IMAGE=bytes.fromhex('a58100fe')
HASH=hashlib.sha256(IMAGE).hexdigest()
SOURCE='a'*64

SDK=r'''
#include <stdbool.h>
#include <stdint.h>
#define GPIO_IN 0
#define GPIO_OUT 1
#define clk_sys 0
uint64_t time_us_64(void);
void busy_wait_us_32(uint32_t delay);
void gpio_init(unsigned pin);
void gpio_put(unsigned pin,bool value);
void gpio_set_dir(unsigned pin,bool value);
void gpio_disable_pulls(unsigned pin);
bool gpio_get(unsigned pin);
uint32_t clock_get_hz(unsigned clk);
void watchdog_update(void);
void tud_task(void);
'''
ADAPTER=r'''
#include "config.h"
#include "pico/stdlib.h"
const uint8_t bridge_fpga_image[]={0xa5,0x81,0,0xfe};
const uint32_t bridge_fpga_image_bytes=4,bridge_fpga_crc32=IMAGE_CRC;
const uint8_t bridge_fpga_sha256[32]={IMAGE_SHA};
static uint64_t now,expire_at;
static unsigned mode,changes,bits,feeds,tasks,reset_low;
static bool levels[32],directions[32],unsafe_release;
static uint8_t wire[36];
uint64_t time_us_64(void){return now;}
void busy_wait_us_32(uint32_t delay){now+=delay;}
void gpio_init(unsigned pin){changes++;directions[pin]=false;}
void gpio_put(unsigned pin,bool value){
 changes++;
 if(pin==2&&!levels[2]&&value&&!levels[1]&&directions[3]){
  if(bits<288)wire[bits/8]|=(uint8_t)(levels[3]<<(7-bits%8));
  bits++;
  if(mode==3&&bits==13)now=expire_at;
 }
 if(pin==4&&!value)reset_low++;
 levels[pin]=value;
}
void gpio_set_dir(unsigned pin,bool value){
 changes++;if(pin==3&&!value&&directions[3]&&!levels[1])unsafe_release=true;
 directions[pin]=value;
}
void gpio_disable_pulls(unsigned pin){(void)pin;changes++;}
bool gpio_get(unsigned pin){
 (void)pin;if(mode==1)return true;
 if(mode==2)return false;
 if(mode==6&&bits==288)now=expire_at-50;
 return levels[4]&&bits==288;
}
uint32_t clock_get_hz(unsigned clk){(void)clk;return mode==4?125000000:150000000;}
void watchdog_update(void){feeds++;}
void tud_task(void){tasks++;if(mode==5)now=expire_at;}
unsigned run(unsigned scenario,uint64_t until){
 mode=scenario;now=0;expire_at=until;changes=bits=feeds=tasks=reset_low=0;unsafe_release=false;
 for(unsigned i=0;i<32;i++)levels[i]=directions[i]=false;
 for(unsigned i=0;i<36;i++)wire[i]=0;
 return bridge_configure(until);
}
unsigned count(unsigned kind){return kind==0?changes:kind==1?bits:kind==2?feeds:kind==3?tasks:reset_low;}
bool safe(void){return levels[1]&&!directions[3]&&levels[4]&&!unsafe_release;}
uint8_t byte(unsigned i){return wire[i];}
'''

class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('cc')
        if not compiler or not str(Path(compiler).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Locked Nix C compiler required')
        cls.temp=tempfile.TemporaryDirectory();d=Path(cls.temp.name)
        for name in ('pico/stdlib.h','hardware/clocks.h','hardware/watchdog.h','tusb.h'):
            p=d/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(SDK)
        adapter=ADAPTER.replace('IMAGE_CRC',str(zlib.crc32(IMAGE))).replace('IMAGE_SHA',','.join(str(x) for x in bytes.fromhex(HASH)))
        (d/'adapter.c').write_text(adapter)
        project=ROOT/'firmware/forgix-spi-bridge'
        def compile_lib(name,body):
            (d/'adapter.c').write_text(body)
            subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                '-I'+str(d),'-I'+str(project),str(project/'config.c'),str(project/'protocol.c'),
                str(d/'adapter.c'),'-o',str(d/name)],check=True,capture_output=True,timeout=30)
            lib=C.CDLL(str(d/name));lib.run.argtypes=[C.c_uint,C.c_uint64];lib.run.restype=C.c_uint
            lib.count.argtypes=[C.c_uint];lib.count.restype=C.c_uint
            lib.safe.restype=C.c_bool;lib.byte.argtypes=[C.c_uint];lib.byte.restype=U8
            return lib
        cls.lib=compile_lib('good.so',adapter)
        cls.bad=compile_lib('bad.so',adapter.replace('bridge_fpga_crc32='+str(zlib.crc32(IMAGE)),'bridge_fpga_crc32=0'))
        cls.lib.bridge_config_match.argtypes=[C.POINTER(U8),C.POINTER(C.c_uint32)];cls.lib.bridge_config_match.restype=C.c_bool
        cls.lib.bridge_config_admit.argtypes=[C.POINTER(C.c_bool),C.c_bool,C.c_uint64];cls.lib.bridge_config_admit.restype=C.c_bool
        cls.lib.bridge_config_reply.argtypes=[C.POINTER(U8),C.c_uint32,C.c_uint,C.c_uint64,C.c_char_p]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def reply(self,status=0,nonce=17):
        out=(U8*128)();self.lib.bridge_config_reply(out,nonce,status,4321,SOURCE.encode());return bytes(out)
    def test_exact_request_and_every_corrupted_byte_are_inert(self):
        p=host.request(HASH,17);n=C.c_uint32()
        self.assertTrue(self.lib.bridge_config_match((U8*48).from_buffer_copy(p),C.byref(n)))
        self.assertEqual(n.value,17)
        for i in range(48):
            damaged=bytearray(p);damaged[i]^=1
            self.assertFalse(self.lib.bridge_config_match((U8*48).from_buffer_copy(damaged),C.byref(n)),i)
        for i in (4,5,6,7,12):
            damaged=bytearray(p);damaged[i]^=1;struct.pack_into('<I',damaged,44,zlib.crc32(damaged[:44]))
            self.assertFalse(self.lib.bridge_config_match((U8*48).from_buffer_copy(damaged),C.byref(n)))
    def test_single_attempt_before_arm_and_within_boot_window(self):
        tried=C.c_bool(False)
        self.assertFalse(self.lib.bridge_config_admit(C.byref(tried),True,0));self.assertFalse(tried.value)
        self.assertFalse(self.lib.bridge_config_admit(C.byref(tried),False,30000000))
        self.assertTrue(self.lib.bridge_config_admit(C.byref(tried),False,29999999))
        self.assertFalse(self.lib.bridge_config_admit(C.byref(tried),False,0))
    def test_actual_c_sends_exact_msb_bytes_extra_clocks_then_releases_data(self):
        self.assertEqual(self.lib.run(0,20000000),0)
        self.assertEqual(bytes(self.lib.byte(i) for i in range(36)),IMAGE+bytes(32))
        self.assertEqual(self.lib.count(1),288);self.assertEqual(self.lib.count(4),1)
        self.assertGreater(self.lib.count(2),0);self.assertGreater(self.lib.count(3),0);self.assertTrue(self.lib.safe())
    def test_initial_done_high_and_never_done_fail_without_claiming_success(self):
        self.assertEqual(self.lib.run(1,20000000),4);self.assertEqual(self.lib.count(1),0);self.assertTrue(self.lib.safe())
        self.assertEqual(self.lib.run(2,20000000),4);self.assertTrue(self.lib.safe())
    def test_crc_clock_and_expired_admission_do_no_gpio_work(self):
        for lib,mode,until,status in ((self.bad,0,20000000,1),(self.lib,4,20000000,5),(self.lib,0,0,2)):
            self.assertEqual(lib.run(mode,until),status);self.assertEqual(lib.count(0),0)
    def test_deadline_at_start_reset_data_usb_service_or_cleanup_is_failure(self):
        for mode,until in ((0,500),(0,1500),(0,4000),(0,7000),(3,20000000),(5,20000000),(6,20000000)):
            self.assertEqual(self.lib.run(mode,until),2,(mode,until));self.assertTrue(self.lib.safe())
    def test_reply_binds_nonce_image_source_reserved_crc_and_status(self):
        raw=self.reply();expected=host.response(raw,image_hash=HASH,source_hash=SOURCE,nonce=17)
        self.assertEqual(expected['device_us'],4321);self.assertFalse(expected['physical_configuration_verified'])
        for i in (0,4,5,6,7,8,20,52,116,124):
            data=bytearray(raw);data[i]^=1
            if i!=124:struct.pack_into('<I',data,124,zlib.crc32(data[:124]))
            with self.assertRaises(ValueError):host.response(data,image_hash=HASH,source_hash=SOURCE,nonce=17)

class Transport:
    def __init__(self,reply):self.raw=reply;self.sent=bytearray();self.writes=0
    def write(self,p,until):self.writes+=1;self.sent.extend(p[:7]);return min(7,len(p))
    def read(self,n,until):p=self.raw[:min(n,11)];self.raw=self.raw[len(p):];return p

class Host(unittest.TestCase):
    def raw(self):
        p=bytearray(128);p[:5]=b'FGSC\x01';struct.pack_into('<I',p,8,17)
        p[20:52]=bytes.fromhex(HASH);p[52:116]=SOURCE.encode();struct.pack_into('<I',p,124,zlib.crc32(p[:124]));return bytes(p)
    def test_partial_transport_and_prefix_persistence(self):
        t=Transport(self.raw());events=[]
        r=host.exchange(t,image_hash=HASH,source_hash=SOURCE,nonce=17,until=30,write_event=events.append,clock=lambda:0)
        self.assertEqual(bytes(t.sent),host.request(HASH,17));self.assertTrue(r['configuration_indication'])
        self.assertEqual(events[0]['phase'],'intent');self.assertEqual(events[-1]['phase'],'validated')
        self.assertEqual(events[-2]['response_hex'],self.raw().hex())
    def test_sink_failure_before_send_and_failed_partial_read_do_not_retry(self):
        t=Transport(self.raw())
        def fail(event):raise OSError('disk')
        with self.assertRaises(OSError):host.exchange(t,image_hash=HASH,source_hash=SOURCE,nonce=17,until=30,write_event=fail,clock=lambda:0)
        self.assertEqual(t.writes,0)
        t=Transport(self.raw()[:23]);events=[]
        with self.assertRaises(ValueError):host.exchange(t,image_hash=HASH,source_hash=SOURCE,nonce=17,until=30,write_event=events.append,clock=lambda:0)
        self.assertEqual(len(t.sent),48);self.assertEqual(events[-1]['response_hex'],self.raw()[:23].hex())
    def test_bad_progress_wrong_identity_and_late_persistence_cannot_pass(self):
        for modify in ('write','reply','late'):
            t=Transport(self.raw());now=[0]
            if modify=='write':t.write=lambda data,until:True
            if modify=='reply':t.raw=bytes(128)
            def sink(event):
                if modify=='late' and event['phase']=='validated':now[0]=30
            with self.assertRaises((ValueError,TimeoutError)):
                host.exchange(t,image_hash=HASH,source_hash=SOURCE,nonce=17,until=30,write_event=sink,clock=lambda:now[0])
    def test_config_profile_is_distinct_from_existing_layout_policies(self):
        d=fixture();d[0x1300:0x1300+len(PROFILE)]=bytes(len(PROFILE));d[0x1300:0x1300+len(CONFIG_PROFILE)]=CONFIG_PROFILE
        for policy in ('usb','spi-bridge'):
            with self.assertRaisesRegex(ValueError,'distinct application profile'):inspect_elf(d,application=policy)
        with self.assertRaisesRegex(ValueError,'bridge implementation symbols'):inspect_elf(d,application='spi-config-bridge')

class Candidate(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.folder=self.root/'.scratch/candidate'
        self.image=self.folder/'work/gateware/outflow/forgix_candidate.hex'
        self.image.parent.mkdir(parents=True)
        self.raw=b'56\n65\n72\n00\n'
        self.image.write_bytes(self.raw)
        self.receipt={'status':'passed','device':'T8F49','timing_model':'I2','configuration_mode':'passive',
                      'stages':['map','interface','pnr','pgm'],'owned_process_group_closed':True,
                      'private_generated_files_verified':True,'source_commit':'a'*40,
                      'bitstream_bytes':len(self.raw),'bitstream_sha256':hashlib.sha256(self.raw).hexdigest()}
        self.save()
    def save(self): (self.folder/'result.json').write_text(json.dumps(self.receipt))
    def read(self):
        with patch('build_forgix_usb_ram.ROOT',self.root):return host.candidate(self.folder)
    def test_entire_decoded_prefix_is_retained_and_both_hashes_bound(self):
        data,r=self.read();self.assertEqual(data,b'Ver\0')
        self.assertEqual(r['decoded_sha256'],hashlib.sha256(data).hexdigest())
        self.assertEqual(r['decoded_crc32'],zlib.crc32(data));self.assertFalse(r['physical_qualification_proved'])
    def test_incomplete_wrong_target_grade_mode_hash_or_closure_rejected(self):
        for key,value in (('status','failed'),('device','T8F81'),('timing_model','C2'),
                          ('configuration_mode','active'),('stages',['map']),
                          ('owned_process_group_closed',False),('private_generated_files_verified',False),
                          ('source_commit','guess'),('bitstream_bytes',1),('bitstream_sha256','0'*64)):
            old=self.receipt[key];self.receipt[key]=value;self.save()
            with self.assertRaises(ValueError):self.read()
            self.receipt[key]=old;self.save()
    def test_altered_image_and_symlinked_file_are_rejected(self):
        self.image.write_bytes(b'01\n')
        with self.assertRaises(ValueError):self.read()
        self.image.unlink();target=self.root/'outside';target.write_bytes(self.raw);self.image.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'Symlinked'):self.read()
    def test_other_hex_formats_and_oversized_decoded_images_are_refused(self):
        for raw in (b'56657200',b':0100000001FE\n',b'GG\n',b'00\n'*196609):
            self.image.write_bytes(raw);self.receipt.update(bitstream_bytes=len(raw),bitstream_sha256=hashlib.sha256(raw).hexdigest());self.save()
            with self.assertRaises(ValueError):self.read()

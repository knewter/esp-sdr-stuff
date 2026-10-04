"""Actual finite C engine and strict wire fault tests; no ARM/device build."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_clock_wire as wire
C=ROOT/'firmware/forgix-clock-observer'
HARNESS=r'''
#include "engine.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t clock_us=100;static unsigned scenario,config_calls,starts,stops,services;
static bool cancel_flag;static fc_engine engine;
static uint64_t now(void *ctx){(void)ctx;return clock_us++;}
static bool cancelled(void *ctx){(void)ctx;return cancel_flag;}
static void service(void *ctx){(void)ctx;services++;}
static unsigned configure(void *ctx,uint64_t until){
 (void)ctx;config_calls++;
 if(scenario==3)clock_us=until;
 if(scenario==4)cancel_flag=true;
 return scenario==5?4:0;
}
static bool prepare(void *ctx,uint64_t until){(void)ctx;(void)until;return true;}
static bool start(void *ctx,uint64_t until){(void)ctx;(void)until;starts++;return true;}
static bool ready(void *ctx){(void)ctx;return true;}
static uint32_t take(void *ctx){(void)ctx;return UINT32_MAX-(scenario==6?8:2400);}
static bool stop(void *ctx){(void)ctx;stops++;return scenario!=7;}
static size_t usb(void *ctx,const uint8_t *p,size_t n){(void)ctx;(void)p;return n>17?17:n;}
int main(int argc,char **argv){
 scenario=argc>1?(unsigned)atoi(argv[1]):0;
 uint8_t build[32],image[32],cmd[128]={0};memset(build,0x22,32);memset(image,0x33,32);
 fc_io io={NULL,now,cancelled,configure,usb,service,
 {NULL,now,cancelled,prepare,start,ready,take,service,stop}};
 if(scenario==8)io.observer.start=NULL;
 bool initialized=fc_init(&engine,io,build,image,100);
 if(scenario==8){if(initialized||engine.phase!=FC_DONE)return 8;return 0;}
 if(!initialized)return 90;
 memcpy(cmd,"FGCQ\1\1",6);memset(cmd+8,0x11,16);memcpy(cmd+24,build,32);memcpy(cmd+56,image,32);
 uint32_t crc=fc_crc(cmd,124);for(unsigned i=0;i<4;i++)cmd[124+i]=(uint8_t)(crc>>(8*i));
 if(scenario==1)cmd[0]='X';
 if(scenario==2){fc_feed(&engine,cmd,64);clock_us=30000100;fc_step(&engine);fc_feed(&engine,cmd+64,64);}
 else {fc_feed(&engine,cmd,63);if(config_calls)return 91;fc_feed(&engine,cmd+63,65);}
 for(unsigned i=0;i<1000&&engine.phase!=FC_DONE;i++)fc_step(&engine);
 if(scenario==1||scenario==2){if(config_calls||starts||engine.reply_offset)return 92;return 0;}
 if(config_calls!=1||engine.phase!=FC_DONE)return 93;
 if(scenario==3||scenario==4||scenario==5){if(starts)return 94;}
 else if(starts!=1||stops!=1)return 95;
 if(scenario==4){if(engine.result.status!=OBSERVER_CANCELLED||engine.reply_offset)return 96;return 0;}
 if(engine.reply_offset!=512)return 97;
 if(fwrite(engine.reply,1,512,stdout)!=512)return 98;
 /* Consumed commands cannot retry after completion. */
 fc_feed(&engine,cmd,128);fc_step(&engine);if(config_calls!=1)return 99;
 return 0;
}
'''
class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();folder=Path(cls.temp.name)
        (folder/'test.c').write_text(HARNESS);cls.binary=folder/'test'
        cc=shutil.which('cc');assert cc and str(Path(cc).resolve()).startswith('/nix/store/')
        subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(C),str(folder/'test.c'),str(C/'engine.c'),str(C/'observer.c'),'-o',str(cls.binary)],check=True,capture_output=True,timeout=30)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def run_c(self,n):return subprocess.run([str(self.binary),str(n)],check=True,capture_output=True,timeout=5).stdout
    def parsed(self,n):return wire.result(self.run_c(n),b'\x11'*16,b'\x22'*32,b'\x33'*32)
    def test_real_c_roundtrip_all_samples_and_partial_usb(self):
        r=self.parsed(0);self.assertEqual((r['observer_status'],r['sample_count']), (0,16));self.assertEqual(r['decrements'],[2400]*16)
    def test_partial_and_invalid_intent_never_configure_or_retry(self):
        self.assertEqual(self.run_c(1),b'');self.assertEqual(self.run_c(2),b'')
    def test_configuration_postreturn_timeout_and_cancel_prevent_input(self):
        self.assertEqual(self.parsed(3)['observer_status'],2);self.assertEqual(self.run_c(4),b'')
    def test_failed_configuration_and_invalid_period_are_retained_failures(self):
        self.assertEqual(self.parsed(5)['configuration_status'],4);self.assertEqual(self.parsed(6)['observer_status'],5)
    def test_cleanup_failure_cannot_emit_success(self):self.assertEqual(self.parsed(7)['observer_status'],3)
    def test_invalid_callback_refuses_before_configuration(self):self.assertEqual(self.run_c(8),b'')
    def test_crc_reserved_identity_and_success_contradictions(self):
        raw=self.run_c(0)
        for offset,value in ((0,0),(4,2),(8,0),(92,1),(96,15),(228,0),(236,1)):
            p=bytearray(raw);p[offset]=value
            if offset==92:continue # Failed result is an honest retained diagnostic.
            struct.pack_into('<I',p,508,zlib.crc32(p[:508]))
            with self.subTest(offset=offset),self.assertRaises(ValueError):wire.result(bytes(p),b'\x11'*16,b'\x22'*32,b'\x33'*32)
        with self.assertRaises(ValueError):wire.result(raw[:-1],b'\x11'*16,b'\x22'*32,b'\x33'*32)
    def test_main_order_one_owner_no_implicit_measurement(self):
        text=(C/'main.c').read_text();self.assertLess(text.index('watchdog_enable(2000'),text.index('bridge_uid_init('));self.assertLess(text.index('bridge_uid_init('),text.index('tud_init('))
        self.assertNotIn('gpio_',text);self.assertNotIn('pico_unique_id',(C/'CMakeLists.txt').read_text())
        self.assertIn('pico_set_binary_type(forgix_clock_observer no_flash)',(C/'CMakeLists.txt').read_text())

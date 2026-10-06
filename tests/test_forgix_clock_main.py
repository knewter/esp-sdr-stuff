"""Compile actual clock main against bounded Pico/USB hooks; no ARM build."""
import os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OWN=ROOT/'firmware/forgix-clock-observer';BRIDGE=ROOT/'firmware/forgix-spi-bridge'
STUB=r'''
#include <stdint.h>
#include <stdbool.h>
uint64_t time_us_64(void);
void tight_loop_contents(void);
void watchdog_enable(unsigned,bool);
void watchdog_update(void);
void watchdog_reboot(unsigned,unsigned,unsigned);
bool tud_init(unsigned);
void tud_task(void);
unsigned tud_cdc_available(void);
unsigned tud_cdc_read(void *,unsigned);
bool tud_cdc_connected(void);
unsigned tud_cdc_write_available(void);
unsigned tud_cdc_write(const void *,unsigned);
unsigned tud_cdc_write_flush(void);
#define CFG_TUD_CDC_TX_BUFSIZE 256
'''
HARNESS=r'''
#include <assert.h>
#include <setjmp.h>
#include <stdlib.h>
#include <string.h>
#include "engine.h"
#include "uid.h"
#include "config.h"
#include "rp_input.h"
static uint64_t ticks=100;static unsigned mode,watchdog,uid,usbinit,configure_count,input_count,write_count;
static jmp_buf finish;static uint8_t cmd[128];static bool sent;
/* 256-byte TX FIFO drained 64 bytes per tud_task, like one full-speed packet. */
static unsigned queued;
uint64_t time_us_64(void){ticks+=1000;return ticks;}
void watchdog_enable(unsigned n,bool p){assert(n==2000&&!p);watchdog++;}
void watchdog_update(void){assert(watchdog);}
void watchdog_reboot(unsigned a,unsigned b,unsigned c){assert(!a&&!b&&c==1);assert(queued==0);}
void tight_loop_contents(void){longjmp(finish,1);}
bool bridge_uid_init(uint64_t until){assert(watchdog&&until>ticks);uid++;return mode!=1;}
void pico_get_unique_board_id_string(char *p,unsigned n){if(n)p[0]=0;}
bool tud_init(unsigned n){assert(uid&&watchdog&&!n);usbinit++;return mode!=2;}
void tud_task(void){queued=queued>64?queued-64:0;}
unsigned tud_cdc_available(void){return !sent&&mode!=3?128:0;}
unsigned tud_cdc_read(void *p,unsigned n){assert(n==128);unsigned amount=mode==4?64:128;memcpy(p,cmd,amount);sent=true;return amount;}
bool tud_cdc_connected(void){return true;}
unsigned tud_cdc_write_available(void){return 256-queued;}
unsigned tud_cdc_write(const void *p,unsigned n){assert(p&&configure_count&&input_count);unsigned amount=n<256-queued?n:256-queued;queued+=amount;write_count+=amount;return amount;}
unsigned tud_cdc_write_flush(void){return 1;}
const uint8_t bridge_fpga_image[]={1},bridge_fpga_sha256[32]={[0 ... 31]=0x33};
const uint32_t bridge_fpga_image_bytes=1,bridge_fpga_crc32=0;
unsigned bridge_configure(uint64_t until){assert(usbinit&&until>ticks);configure_count++;return 0;}
static uint64_t onow(void *p){(void)p;return time_us_64();}
static bool ocancel(void *p){(void)p;return false;}
static bool oprepare(void *p,uint64_t until){(void)p;assert(configure_count&&until>ticks);input_count++;return true;}
static bool ostart(void *p,uint64_t until){(void)p;(void)until;return true;}
static bool oready(void *p){(void)p;return true;}
static uint32_t otake(void *p){(void)p;return UINT32_MAX-2400;}
static void oservice(void *p){(void)p;}
static bool ostop(void *p){(void)p;return true;}
void observer_rp_io(observer_io *io,bool (*cancel)(void *),void *ctx){(void)cancel;(void)ctx;*io=(observer_io){NULL,onow,ocancel,oprepare,ostart,oready,otake,oservice,ostop};}
#define main firmware_main
#include "ACTUAL_MAIN"
#undef main
int main(int argc,char **argv){
 mode=argc>1?(unsigned)atoi(argv[1]):0;memcpy(cmd,"FGCQ\1\1",6);memset(cmd+8,0x11,16);memset(cmd+24,0x22,32);memset(cmd+56,0x33,32);uint32_t crc=fc_crc(cmd,124);for(unsigned i=0;i<4;i++)cmd[124+i]=(uint8_t)(crc>>(8*i));
 if(!setjmp(finish))firmware_main();
 assert(watchdog==1&&uid==1);
 if(mode==1)assert(!usbinit&&!configure_count&&!input_count);
 else if(mode==2||mode==3||mode==4)assert(usbinit==1&&!configure_count&&!input_count&&!write_count);
 else assert(usbinit==1&&configure_count==1&&input_count==1&&write_count==512&&clock_engine.phase==FC_DONE);
 return 0;
}
'''
class Main(unittest.TestCase):
 def test_actual_main_uid_usb_failure_partial_no_command_and_one_complete_run(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'pico').mkdir();(p/'hardware').mkdir()
   for name in ('pico/stdlib.h','hardware/watchdog.h','tusb.h'):(p/name).write_text(STUB)
   (p/'build_identity.h').write_text('static const unsigned char BUILD_SOURCE_BYTES[32]={[0 ... 31]=0x22};\n')
   (p/'test.c').write_text(HARNESS.replace('ACTUAL_MAIN',str(OWN/'main.c')));cc=shutil.which('cc');self.assertTrue(cc and Path(cc).resolve().is_relative_to('/nix/store'))
   subprocess.run([cc,'-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(p),'-I',str(OWN),'-I',str(BRIDGE),str(p/'test.c'),str(OWN/'engine.c'),str(OWN/'observer.c'),'-o',str(p/'test')],check=True,capture_output=True,timeout=30)
   for mode in range(5):
    with self.subTest(mode=mode):subprocess.run([str(p/'test'),str(mode)],check=True,capture_output=True,timeout=5)

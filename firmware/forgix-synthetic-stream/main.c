/* Offline only; complete layout/startup/backend/physical review still required. */
#include "pico/stdlib.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include "uid.h"
#include "config.h"
#include "engine.h"
#include "platform.h"
#include "build_identity.h"
#include <stddef.h>
#include <string.h>
const char diagnostic_profile[]="FORGIX_SYNTHETIC_STREAM_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56";
fs_engine stream_engine;
/* Independent ELF guard reads the actual compiled queue/object offsets. */
const uint32_t stream_layout[]={sizeof(fs_engine),offsetof(fs_engine,queue),8192,
 offsetof(fs_engine,batch),sizeof(fsg_batch),offsetof(fs_engine,pending),sizeof(fsg_record)};
static uint8_t command_bytes[128];
static uint64_t now(void *ctx){(void)ctx;return time_us_64();}
static void service(void *ctx){(void)ctx;tud_task();watchdog_update();}
static bool configure(void *ctx,uint64_t until){(void)ctx;return fs_platform_configure(until);}
static bool prepare(void *ctx,uint64_t until){(void)ctx;return fs_platform_prepare(until);}
static bool transfer(void *ctx,bool write,uint32_t address,uint32_t *value,uint64_t until){(void)ctx;return fs_platform_transfer(write,address,value,until);}
static size_t usb(void *ctx,const uint8_t *data,size_t length){
 (void)ctx;if(!tud_cdc_connected()||!tud_cdc_write_available())return 0;
 unsigned n=tud_cdc_write(data,(uint32_t)length);tud_cdc_write_flush();return n;
}
static void safe(void *ctx){(void)ctx;fs_platform_safe();}
int main(void){
 uint64_t boot=time_us_64();watchdog_enable(2000,false);
 if(!bridge_uid_init(boot+500000)||!tud_init(0))goto reboot;
 fs_io io={.ctx=NULL,.now=now,.service=service,.configure=configure,.prepare=prepare,.xfer=transfer,.usb=usb,.safe=safe};
 if(!fs_init(&stream_engine,io,BUILD_SOURCE_BYTES,bridge_fpga_sha256,FORGIX_RP_PAUSE))goto reboot;
 /* UID/USB initialization time belongs to the same boot clocks. */
 stream_engine.boot=boot;fs_platform_lifetime(boot+UINT64_C(120000000));
 unsigned length=0;
 while(time_us_64()<boot+UINT64_C(120000000)&&stream_engine.phase!=FS_DONE){
  service(NULL);
  if(tud_cdc_available()){
   unsigned n=tud_cdc_read(command_bytes+length,128-length);length+=n;
   if(length==128){fs_command(&stream_engine,command_bytes,128);length=0;}
  }
  fs_step(&stream_engine);
 }
 fs_platform_safe();
reboot:
 watchdog_reboot(0,0,1);while(true)tight_loop_contents();
}

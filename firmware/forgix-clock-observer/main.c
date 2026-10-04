/* Distinct finite clock observer. No old profile or registry is replaced. */
#include "pico/stdlib.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include "uid.h"
#include "config.h"
#include "engine.h"
#include "rp_input.h"
#include "build_identity.h"
#include <stddef.h>
const char diagnostic_profile[]="FORGIX_CLOCK_OBSERVER_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56";
fc_engine clock_engine;
const uint32_t clock_layout[]={sizeof(fc_engine),offsetof(fc_engine,command),128,
 offsetof(fc_engine,reply),512,offsetof(fc_engine,result),sizeof(observer_result)};
static uint64_t boot_us;
static uint64_t now(void *ctx){(void)ctx;return time_us_64();}
static bool cancelled(void *ctx){(void)ctx;return time_us_64()>=boot_us+UINT64_C(120000000);}
static void service(void *ctx){(void)ctx;tud_task();watchdog_update();}
static unsigned configure(void *ctx,uint64_t until){(void)ctx;return bridge_configure(until);}
static size_t usb(void *ctx,const uint8_t *p,size_t n){
 (void)ctx;if(!tud_cdc_connected()||!tud_cdc_write_available())return 0;
 unsigned done=tud_cdc_write(p,(uint32_t)n);tud_cdc_write_flush();return done;
}
int main(void){
 boot_us=time_us_64();watchdog_enable(2000,false);
 if(!bridge_uid_init(boot_us+500000)||!tud_init(0))goto reboot;
 fc_io io={.ctx=NULL,.now=now,.cancelled=cancelled,.configure=configure,.usb=usb,.service=service};
 observer_rp_io(&io.observer,cancelled,NULL);io.observer.service=service;
 if(!fc_init(&clock_engine,io,BUILD_SOURCE_BYTES,bridge_fpga_sha256,boot_us))goto reboot;
 while(time_us_64()<boot_us+UINT64_C(120000000)&&clock_engine.phase!=FC_DONE){
  service(NULL);
  if(tud_cdc_available()){
   uint8_t input[128];unsigned n=tud_cdc_read(input,sizeof(input));
   fc_feed(&clock_engine,input,n);
  }
  fc_step(&clock_engine);
 }
 /* Configuration and observer callbacks own CS-high/DATA-input cleanup. No
  * application GPIO is touched on an untrusted/partial command or UID failure. */
reboot:
 watchdog_reboot(0,0,1);while(true)tight_loop_contents();
}

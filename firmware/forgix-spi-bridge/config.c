/* Offline candidate. Pin/timing qualification and a reviewed loader still required. */
#include "config.h"
#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include <string.h>
#define CONFIG_CS 1u
#define CONFIG_SCK 2u
#define CONFIG_DATA 3u
#define CONFIG_RESET 4u
#define CONFIG_DONE 5u
#define CONFIG_ENABLE 19u
static uint32_t get32(const uint8_t *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void put32(uint8_t *p,uint32_t v) {for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
bool bridge_config_match(const uint8_t p[48],uint32_t *nonce) {
 if(memcmp(p,"FGSC",4)||p[4]!=1||p[5]!=1||p[6]||p[7]||!get32(p+8)||
    memcmp(p+12,bridge_fpga_sha256,32)||get32(p+44)!=bridge_crc(p,44))return false;
 *nonce=get32(p+8);return true;
}
bool bridge_config_admit(bool *attempted,bool register_attempted,uint64_t age_us) {
 if(*attempted||register_attempted||age_us>=UINT64_C(30000000))return false;
 *attempted=true;return true;
}
static bool late(uint64_t until) {return time_us_64()>=until;}
static void output_pin(unsigned pin,bool value) {
 gpio_init(pin);gpio_put(pin,value);gpio_set_dir(pin,GPIO_OUT);
}
static bool pause_us(unsigned delay,uint64_t until) {
 if(late(until))return false;
 busy_wait_us_32(delay);return !late(until);
}
static bool send_byte(uint8_t value,uint64_t until) {
 for(unsigned bit=0;bit<8;bit++){
  if(late(until))return false;
  gpio_put(CONFIG_SCK,0);gpio_put(CONFIG_DATA,(value>>(7-bit))&1);
  if(!pause_us(1,until))return false;
  gpio_put(CONFIG_SCK,1);
  if(!pause_us(1,until))return false;
 }
 return true;
}
unsigned bridge_configure(uint64_t until) {
 /* CRC/range/clock rejection is inert. SHA matching belongs to the handshake. */
 if(late(until))return BRIDGE_TIMEOUT;
 if(!bridge_fpga_image_bytes||bridge_fpga_image_bytes>196608u||
    bridge_crc(bridge_fpga_image,bridge_fpga_image_bytes)!=bridge_fpga_crc32)return BRIDGE_REFUSED;
 if(late(until))return BRIDGE_TIMEOUT;
 if(clock_get_hz(clk_sys)!=150000000u)return BRIDGE_CLOCK_MISMATCH;
 if(late(until))return BRIDGE_TIMEOUT;
 output_pin(CONFIG_CS,1);output_pin(CONFIG_SCK,1); /* Mode-3 idle, as factory source. */
 gpio_init(CONFIG_DATA);gpio_disable_pulls(CONFIG_DATA);gpio_set_dir(CONFIG_DATA,GPIO_IN);
 gpio_init(CONFIG_DONE);gpio_disable_pulls(CONFIG_DONE);gpio_set_dir(CONFIG_DONE,GPIO_IN);
 output_pin(CONFIG_RESET,1);output_pin(CONFIG_ENABLE,1);
 unsigned status=BRIDGE_TIMEOUT;
 if(!pause_us(1000,until))goto finish;
 gpio_put(CONFIG_CS,0);gpio_put(CONFIG_RESET,0);
 if(!pause_us(2000,until))goto finish;
 if(gpio_get(CONFIG_DONE)){status=BRIDGE_NOT_DONE;goto finish;}
 gpio_put(CONFIG_RESET,1);
 if(!pause_us(5000,until))goto finish;
 gpio_put(CONFIG_DATA,0);gpio_set_dir(CONFIG_DATA,GPIO_OUT);
 for(uint32_t i=0;i<bridge_fpga_image_bytes;i++){
  if(!send_byte(bridge_fpga_image[i],until))goto finish;
  watchdog_update();
  if(!(i&255u)){tud_task();if(late(until))goto finish;}
 }
 /* Factory source sends 32 extra zero bytes before CDONE polling. */
 for(unsigned i=0;i<32;i++)if(!send_byte(0,until))goto finish;
 {
  uint64_t done_until=time_us_64()+UINT64_C(500000);
  if(until<done_until)done_until=until;
  while(!late(done_until)){
   if(gpio_get(CONFIG_DONE)){status=BRIDGE_OK;break;}
   watchdog_update();tud_task();
   if(!pause_us(1000,done_until))break;
  }
  if(status!=BRIDGE_OK)status=BRIDGE_NOT_DONE;
 }
finish:
 /* Inhibit FPGA first. No new clock edge while releasing shared DATA. */
 gpio_put(CONFIG_CS,1);busy_wait_us_32(100);
 gpio_set_dir(CONFIG_DATA,GPIO_IN);
 gpio_put(CONFIG_RESET,1);
 return late(until)?BRIDGE_TIMEOUT:status;
}
void bridge_config_reply(uint8_t p[128],uint32_t nonce,unsigned status,
                         uint64_t now,const char source[64]) {
 memset(p,0,128);memcpy(p,"FGSC",4);p[4]=1;p[5]=(uint8_t)status;put32(p+8,nonce);
 for(unsigned i=0;i<8;i++)p[12+i]=(uint8_t)(now>>(8*i));
 memcpy(p+20,bridge_fpga_sha256,32);memcpy(p+52,source,64);
 put32(p+124,bridge_crc(p,124));
}

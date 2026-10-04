/* RP2350 only: read-only ROM CHIP_INFO, called after watchdog startup.
 * Byte ordering matches Pico SDK2.2.0 pico_unique_id/unique_id.c (BSD-3-Clause):
 * https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2_common/pico_unique_id/unique_id.c
 * No constructor, flash access, OTP write, logging, retry or watchdog feeding.
 * Clock checks bound completed calls; a stalled ROM call relies on watchdog.
 */
#include "uid.h"
#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include <string.h>
static char serial[17];
bool bridge_uid_init(uint64_t until) {
 memset(serial,0,sizeof(serial));
 if(time_us_64()>=until)return false;
 rom_get_sys_info_fn read=(rom_get_sys_info_fn)rom_func_lookup(ROM_FUNC_GET_SYS_INFO);
 if(!read||time_us_64()>=until)return false;
 uint32_t words[9]={0};
 int rc=read(words,9,SYS_INFO_CHIP_INFO);
 if(time_us_64()>=until||rc!=4||words[0]!=SYS_INFO_CHIP_INFO||
    !(words[2]|words[3])||(words[2]==UINT32_MAX&&words[3]==UINT32_MAX))return false;
 char candidate[17];
 const char hex[]="0123456789ABCDEF";
 for(unsigned i=0;i<16;i++)candidate[i]=hex[(words[i<8?3:2]>>(28-4*(i%8)))&15];
 candidate[16]=0;
 if(time_us_64()>=until)return false;
 memcpy(serial,candidate,sizeof(serial));
 if(time_us_64()>=until){memset(serial,0,sizeof(serial));return false;}
 return true;
}
void pico_get_unique_board_id_string(char *out,unsigned len) {
 if(!out||!len)return;
 unsigned n=0;
 while(n+1<len&&n<16&&serial[n]){out[n]=serial[n];n++;}
 out[n]=0;
}

/* Synthetic MCU-to-host data only. No FPGA/peripheral/GPIO/persistent writes. */
#include "pico/stdlib.h"
#include "hardware/watchdog.h"
#include "tusb.h"
#include <string.h>
#include "build_identity.h"
#define FRAME_BYTES 512u
#define PAYLOAD_BYTES 460u
#define QUEUE_RECORDS 16u
#define MAX_LIFETIME_US UINT64_C(120000000)
#define RUN_US UINT64_C(60000000)
#define DRAIN_US UINT64_C(2000000)
const char diagnostic_profile[] = "FORGIX_USB_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56";
static uint8_t queue[QUEUE_RECORDS][FRAME_BYTES];
static uint8_t nonce[16], command[32];
static unsigned head, tail, queued, offset, command_length;
static uint32_t sequence, generated, enqueued, dropped, partial_writes, high_water;
static uint64_t accepted_bytes, stall_us;
static uint64_t boot_us, start_us;
static uint32_t rate;
static bool active, ending, end_enqueued;
static uint32_t crc32(const uint8_t *p, unsigned n) {
 uint32_t v=~UINT32_C(0);
 for(unsigned i=0;i<n;i++){v^=p[i];for(unsigned b=0;b<8;b++)v=(v>>1)^((0-(v&1))&UINT32_C(0xedb88320));}
 return ~v;
}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void put64(uint8_t *p,uint64_t v){for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(v>>(i*8));}
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void frame(unsigned type,uint64_t now){
 uint32_t seq=sequence++; generated++;
 if(queued==QUEUE_RECORDS){dropped++;return;}
 uint8_t *p=queue[tail];memset(p,0,FRAME_BYTES);
 memcpy(p,"FRAM",4);p[4]=1;p[6]=(uint8_t)type;put32(p+8,seq);put32(p+12,FRAME_BYTES);put32(p+16,PAYLOAD_BYTES);
 put64(p+20,now);memcpy(p+28,nonce,16);
 if(type==2){for(unsigned i=0;i<PAYLOAD_BYTES;i++)p[48+i]=(uint8_t)((seq*131+i*17)^nonce[i%16]);}
 else {
  put32(p+48,rate);put32(p+52,generated);put32(p+56,enqueued);put32(p+60,dropped);
  put32(p+64,partial_writes);put32(p+68,high_water);put64(p+72,accepted_bytes);put64(p+80,stall_us);
  put64(p+88,boot_us);put64(p+96,start_us);put64(p+104,MAX_LIFETIME_US);
  memcpy(p+112,BUILD_SOURCE_SHA256,64);memcpy(p+176,diagnostic_profile,sizeof(diagnostic_profile));
 }
 put32(p+508,crc32(p,508));tail=(tail+1)%QUEUE_RECORDS;queued++;enqueued++;
 if(queued>high_water)high_water=queued;
 if(type==4)end_enqueued=true;
}
int main(void){
 boot_us=time_us_64();watchdog_enable(2000,false);
 if(diagnostic_profile[0]!='F' || !tud_init(0)){
  watchdog_reboot(0,0,1);while(true)tight_loop_contents();
 }
 bool announced=false;uint64_t previous=time_us_64(),data_records=0,stats_due=0;
 while(true){
  uint64_t now=time_us_64();if(now-boot_us>=MAX_LIFETIME_US)break;
  tud_task();watchdog_update();
  if(tud_cdc_connected()&&!announced){frame(0,now);announced=true;}
  if(!active&&!ending&&tud_cdc_available()){
   unsigned n=tud_cdc_read(command+command_length,sizeof(command)-command_length);command_length+=n;
   if(command_length==sizeof(command)){
    uint32_t r=get32(command+8);
    if(!memcmp(command,"FRAM",4)&&command[4]==1&&command[5]==0&&command[6]==1&&command[7]==0&&
      (r==65536||r==262144||r==786432)&&get32(command+28)==crc32(command,28)&&now-boot_us<UINT64_C(30000000)){
     memcpy(nonce,command+12,16);rate=r;start_us=now;active=true;stats_due=now+1000000;frame(1,now);
    }
    command_length=0; /* Invalid commands are silent and inert; no echo. */
   }
  }
  if(active){
   if(now-start_us>=RUN_US){active=false;ending=true;}
   else {
    for(unsigned budget=0;budget<4&&now>=start_us+(data_records*PAYLOAD_BYTES*1000000)/rate;budget++){
     frame(2,now);data_records++;
    }
    if(now>=stats_due){frame(3,now);stats_due+=1000000;}
   }
  }
  if(ending&&!end_enqueued&&queued<QUEUE_RECORDS)frame(4,now);
  if(queued){
   unsigned available=tud_cdc_write_available();
   if(available){unsigned remain=FRAME_BYTES-offset,n=tud_cdc_write(queue[head]+offset,remain);
    if(n&&n<remain){partial_writes++;}
    offset+=n;accepted_bytes+=n;tud_cdc_write_flush();
    if(offset==FRAME_BYTES){head=(head+1)%QUEUE_RECORDS;queued--;offset=0;}
   }else stall_us+=now-previous;
  }
  previous=now;
  /* Always drain for the fixed grace; callbacks cannot prove END delivery. */
  if(ending&&now-start_us>=RUN_US+DRAIN_US)break;
 }
 watchdog_reboot(0,0,1);while(true)tight_loop_contents();
}

/* One finite command/result engine. No hardware policy or admission here. */
#include "engine.h"
#include <string.h>
#define LIFE UINT64_C(120000000)
#define ARM UINT64_C(30000000)
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v){for(unsigned n=0;n<4;n++)p[n]=(uint8_t)(v>>(8*n));}
static void put64(uint8_t *p,uint64_t v){for(unsigned n=0;n<8;n++)p[n]=(uint8_t)(v>>(8*n));}
/* Keep both active CRC callers bound to one auditable body under Release/GC. */
__attribute__((noinline,noclone))
uint32_t fc_crc(const uint8_t *p,unsigned n){uint32_t c=UINT32_MAX;while(n--){c^=*p++;for(unsigned b=0;b<8;b++)c=(c>>1)^(UINT32_C(0xedb88320)&(0-(c&1)));}return ~c;}
static uint64_t minimum(uint64_t a,uint64_t b){return a<b?a:b;}
static unsigned gate(fc_engine *e,uint64_t until){
 if(e->io.cancelled(e->io.ctx))return OBSERVER_CANCELLED;
 uint64_t now=e->io.now(e->io.ctx);
 if(e->io.cancelled(e->io.ctx))return OBSERVER_CANCELLED;
 return now>=until?OBSERVER_TIMEOUT:OBSERVER_OK;
}
bool fc_init(fc_engine *e,fc_io io,const uint8_t build[32],const uint8_t image[32],uint64_t boot){
 if(!e)return false;
 memset(e,0,sizeof(*e));e->phase=FC_DONE;
 if(!build||!image||!io.now||!io.cancelled||!io.configure||!io.usb||!io.service||!io.observer.now||!io.observer.cancelled||
    !io.observer.prepare_input||!io.observer.start||!io.observer.ready||
    !io.observer.take||!io.observer.service||!io.observer.stop_input||boot>UINT64_MAX-LIFE)return false;
 e->io=io;e->boot=boot;memcpy(e->build,build,32);memcpy(e->image,image,32);
 e->result.status=OBSERVER_REFUSED;e->config_status=1;e->phase=FC_WAIT;return true;
}
void fc_feed(fc_engine *e,const uint8_t *bytes,size_t n){
 if(!e||!n||e->phase>FC_READ)return;
 /* Intent consumed before parsing; damaged/partial input never resets it. */
 e->attempted=true;e->phase=FC_READ;
 if(!bytes||n>128-e->command_length||gate(e,e->boot+ARM)){e->phase=FC_DONE;return;}
 memcpy(e->command+e->command_length,bytes,n);e->command_length+=(unsigned)n;
 if(e->command_length!=128)return;
 uint8_t nonce=0,reserved=0;for(unsigned i=8;i<24;i++)nonce|=e->command[i];
 for(unsigned i=88;i<124;i++)reserved|=e->command[i];
 if(memcmp(e->command,"FGCQ",4)||e->command[4]!=1||e->command[5]!=1||
  e->command[6]||e->command[7]||!nonce||reserved||
  memcmp(e->command+24,e->build,32)||memcmp(e->command+56,e->image,32)||
  get32(e->command+124)!=fc_crc(e->command,124)){e->phase=FC_DONE;return;}
 e->request_us=e->io.now(e->io.ctx);
 if(gate(e,e->boot+ARM)){e->phase=FC_DONE;return;}e->phase=FC_CONFIG;
}
static void encode(fc_engine *e){
 e->encoded=e->io.now(e->io.ctx);
 unsigned late=gate(e,e->boot+LIFE);if(!e->result.status&&late)e->result.status=late;
 e->drain_until=minimum(e->boot+LIFE,e->encoded<=UINT64_MAX-UINT64_C(2000000)?e->encoded+UINT64_C(2000000):UINT64_MAX);
 uint8_t *p=e->reply;memset(p,0,512);memcpy(p,"FGCR",4);p[4]=p[5]=1;
 memcpy(p+8,e->command+8,16);memcpy(p+24,e->build,32);memcpy(p+56,e->image,32);
 put32(p+88,e->config_status);put32(p+92,e->result.status);put32(p+96,e->result.count);
 for(unsigned i=0;i<e->result.count&&i<CLOCK_OBSERVER_SAMPLES;i++)put32(p+100+4*i,e->result.decrements[i]);
 const uint64_t times[]={e->boot,e->request_us,e->config_begin,e->config_end,e->result.began_us,e->result.ended_us,e->encoded,e->drain_until};
 for(unsigned i=0;i<8;i++)put64(p+164+8*i,times[i]);
 put32(p+228,e->result.cleanup_verified);put32(p+232,e->configuration_attempted);
 put32(p+508,fc_crc(p,508));e->phase=FC_SEND;
}
void fc_step(fc_engine *e){
 if(!e||e->phase==FC_DONE)return;
 e->io.service(e->io.ctx);
 if(e->phase<=FC_READ){if(gate(e,e->boot+ARM))e->phase=FC_DONE;return;}
 if(e->phase==FC_CONFIG){
  unsigned g=gate(e,e->boot+ARM);
  if(g){e->result.status=g;encode(e);return;}
  e->config_begin=e->io.now(e->io.ctx);g=gate(e,e->boot+ARM);
  if(g){e->result.status=g;encode(e);return;}
  uint64_t until=minimum(e->boot+ARM,e->config_begin+UINT64_C(20000000));
  e->configuration_attempted=true;e->config_status=e->io.configure(e->io.ctx,until);
  e->config_end=e->io.now(e->io.ctx);g=gate(e,until);
  if(e->config_status||g){e->result.status=g?g:OBSERVER_IO;encode(e);return;}
  e->phase=FC_OBSERVE;
 }
 if(e->phase==FC_OBSERVE){
  unsigned g=gate(e,e->boot+LIFE);if(g){e->result.status=g;encode(e);return;}
  uint64_t now=e->io.now(e->io.ctx);g=gate(e,e->boot+LIFE);
  if(g){e->result.status=g;encode(e);return;}
  observer_capture(&e->io.observer,&e->measurement_attempted,
   minimum(now+CLOCK_OBSERVER_MAX_US,e->boot+LIFE),&e->result);
  encode(e);return;
 }
 if(e->phase==FC_SEND){
  /* Cancellation after encoding fails transport completion, never resend. */
  if(gate(e,e->drain_until)){e->phase=FC_DONE;return;}
  size_t n=e->io.usb(e->io.ctx,e->reply+e->reply_offset,512-e->reply_offset);
  if(n>512-e->reply_offset){e->phase=FC_DONE;return;}
  e->reply_offset+=(unsigned)n;
  if(gate(e,e->drain_until)||e->reply_offset==512)e->phase=FC_DONE;
 }
}

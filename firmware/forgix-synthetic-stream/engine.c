/* Distinct offline stream profile. Never calls the old register whitelist. */
#include "engine.h"
#include <string.h>
#define SECOND UINT64_C(1000000)
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void w32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static void w64(uint8_t *p,uint64_t v){for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(v>>(8*i));}
static bool nonzero(const uint8_t *p,unsigned n){unsigned v=0;for(unsigned i=0;i<n;i++)v|=p[i];return v!=0;}
static bool profile(uint32_t p,uint32_t t){return (p==2000000&&t==960)||(p==500000&&t==3840)||(p==250000&&t==7680);}
static uint64_t clock_now(fs_engine *e){uint64_t n=e->io.now(e->io.ctx);if(n<e->last_now){e->status=FS_DEADLINE;e->trustworthy=false;e->clock_bad=true;return e->last_now;}e->last_now=n;return n;}
static void failed(fs_engine *e,unsigned status){if(e->status==FS_OK||e->status==FS_LOSS)e->status=status;e->phase=FS_FINAL;}
static bool before(fs_engine *e,uint64_t until){return clock_now(e)<until&&!e->clock_bad;}
static bool transfer(fs_engine *e,bool write,unsigned off,uint32_t *v,uint64_t until){
 e->io.service(e->io.ctx);
 if(!before(e,until)){failed(e,FS_DEADLINE);return false;}
 uint64_t cap=clock_now(e)+20000;if(cap>until)cap=until;
 bool ok=e->io.xfer(e->io.ctx,write,UINT32_C(0x10000)+off,v,cap);
 e->io.service(e->io.ctx);
 if(!ok||!before(e,cap)){e->trustworthy=false;failed(e,ok?FS_DEADLINE:FS_SPI);return false;}
 return true;
}
static bool rd(fs_engine *e,unsigned off,uint32_t *v,uint64_t until){return transfer(e,false,off,v,until);}
static bool wr(fs_engine *e,unsigned off,uint32_t v,uint64_t until){return transfer(e,true,off,&v,until);}
static bool snapshot(fs_engine *e,uint64_t until){
 uint32_t v[16];fs_snapshot s={0};e->flags&=~4u;
 static const unsigned offsets[16]={0x4c,0x50,0x54,0x58,0x5c,0x60,0x64,0x68,0x6c,0x70,0x74,0x78,0x7c,0x80,0x84,0x88};
 if(!wr(e,0x0c,4,until))return false;
 for(unsigned i=0;i<16;i++)if(!rd(e,offsets[i],&v[i],until))return false;
 s.id=v[0];s.tick=(uint64_t)v[1]|((uint64_t)v[2]<<32);s.state=v[3];
 s.generated=v[4];s.enqueued=v[5];s.dropped=v[6];s.popped=v[7];s.refused_pop=v[8];s.refused_command=v[9];
 s.remaining=v[10];s.highwater=v[11];s.start=(uint64_t)v[12]|((uint64_t)v[13]<<32);s.stop=(uint64_t)v[14]|((uint64_t)v[15]<<32);
 if((s.state&~127u)||!s.id||s.id<=e->snapshot.id||s.generated>e->target||
    s.enqueued>s.generated||s.dropped!=s.generated-s.enqueued||s.popped>s.enqueued||
    s.remaining!=s.enqueued-s.popped||s.remaining>64||s.highwater>64||s.highwater<s.remaining){failed(e,FS_SOURCE);return false;}
 e->snapshot=s;e->flags|=4;return true;
}
static void queued(fs_engine *e){e->write_slot=(e->write_slot+1)&15;e->queued++;if(e->queued>e->highwater)e->highwater=e->queued;}
static bool control(fs_engine *e,unsigned type){
 if(e->queued==16)return false;
 uint8_t *p=e->queue[e->write_slot];memset(p,0,512);memcpy(p,"FSB1",4);p[4]=1;p[5]=(uint8_t)type;p[6]=64;w32(p+8,type-2);p[13]=2;
 w64(p+20,clock_now(e));memcpy(p+28,e->nonce,16);w32(p+48,e->period);w32(p+52,e->target);
 memcpy(p+64,e->build,32);memcpy(p+96,e->image,32);w32(p+128,e->status);w32(p+132,e->flags);
 w64(p+136,e->last_now-e->boot);w64(p+144,e->start_us);w64(p+152,e->final_us);
 w64(p+160,e->snapshot.start);w64(p+168,e->snapshot.tick);w64(p+176,e->snapshot.stop);
 w32(p+184,e->snapshot.state);w32(p+188,e->snapshot.id);w32(p+192,e->snapshot.generated);w32(p+196,e->snapshot.enqueued);
 w32(p+200,e->snapshot.dropped);w32(p+204,e->snapshot.popped);w32(p+208,e->snapshot.remaining);w32(p+212,e->snapshot.highwater);
 w32(p+216,e->snapshot.refused_pop);w32(p+220,e->snapshot.refused_command);w32(p+224,e->confirmed);w32(p+228,e->staged);
 w32(p+232,e->frames);w32(p+236,e->frames_sent);w64(p+240,e->usb_bytes);w32(p+248,e->partial_writes);w32(p+252,e->stalls);w64(p+256,e->max_stall);
 w32(p+264,e->highwater);if(e->pending_flags){w32(p+268,e->pending.sequence);w32(p+272,e->pending.sequence);w32(p+276,e->pending.tick32);w32(p+280,e->pending.pattern);w32(p+284,e->pending.crc32);}
 uint32_t data_queued=0;for(unsigned i=0;i<e->queued;i++)if(e->queue[(e->read_slot+i)&15][5]==1)data_queued++;
 w32(p+288,e->pending_flags);w32(p+292,data_queued);w32(p+296,e->batch.count);w32(p+300,e->stop_state);
 w64(p+304,e->pause_start);w64(p+312,e->pause_end);w32(p+508,fsg_crc32(p,508));queued(e);return true;
}
static bool flush(fs_engine *e){
 if(!e->batch.count)return true;
 if(e->queued==16)return false;
 e->batch.frame_sequence=e->frames;e->batch.device_time_us=clock_now(e);
 if(fsg_batch_encode(&e->batch,e->queue[e->write_slot])!=FSG_OK){failed(e,FS_RECORD);return false;}
 e->staged+=e->batch.count;e->frames++;e->batch.count=0;queued(e);return true;
}
static void usb(fs_engine *e){
 if(!e->queued)return;
 uint64_t n=clock_now(e);uint8_t *p=e->queue[e->read_slot];size_t left=512u-e->offset;
 size_t count=e->io.usb(e->io.ctx,p+e->offset,left);
 if(count>left){failed(e,FS_USB);return;}
 if(!count){if(!e->stalling){e->stalling=true;e->stall_start=n;e->stalls++;}return;}
 if(e->stalling){uint64_t span=clock_now(e)-e->stall_start;if(span>e->max_stall)e->max_stall=span;e->stalling=false;}
 if(count<left)e->partial_writes++;
 e->usb_bytes+=count;e->offset+=(uint16_t)count;
 if(e->offset==512){if(p[5]==1)e->frames_sent++;e->offset=0;e->read_slot=(e->read_slot+1)&15;e->queued--;}
}
bool fs_init(fs_engine *e,fs_io io,const uint8_t build[32],const uint8_t image[32],bool pause){
 if(!e||!build||!image||!io.now||!io.service||!io.configure||!io.prepare||!io.xfer||!io.usb||!io.safe||!nonzero(build,32)||!nonzero(image,32))return false;
 memset(e,0,sizeof(*e));e->io=io;e->boot=e->last_now=io.now(io.ctx);
 if(e->boot>UINT64_MAX-120*SECOND)return false;
 memcpy(e->build,build,32);memcpy(e->image,image,32);e->trustworthy=true;e->pause_enabled=pause;return true;
}
void fs_command(fs_engine *e,const uint8_t *p,size_t len){
 if(e->phase==FS_DONE||e->phase==FS_TERMINAL)return;
 bool valid=p&&len==128&&!memcmp(p,"FSQ1",4)&&p[4]==1&&(p[5]==1||p[5]==2)&&p[6]==128&&!p[7]&&nonzero(p+8,16)&&
  profile(u32(p+24),u32(p+28))&&!memcmp(p+32,e->build,32)&&!memcmp(p+64,e->image,32)&&!nonzero(p+96,28)&&u32(p+124)==fsg_crc32(p,124);
 uint64_t until=e->boot+30*SECOND;
 if(!valid||!before(e,until)){failed(e,valid?FS_DEADLINE:FS_COMMAND);return;}
 if(p[5]==1){
  if(e->configured_attempt||e->phase!=FS_IDLE){failed(e,FS_COMMAND);return;}
  e->configured_attempt=true;memcpy(e->nonce,p+8,16);e->period=u32(p+24);e->target=u32(p+28);
  uint64_t cap=clock_now(e)+20*SECOND;if(cap>until)cap=until;
  if(!e->io.configure(e->io.ctx,cap)||!before(e,cap)){failed(e,FS_CONFIG);control(e,2);return;}
  e->flags|=1;e->phase=FS_CONFIGURED;control(e,2);return;
 }
 if(e->start_attempt||e->phase!=FS_CONFIGURED||memcmp(p+8,e->nonce,16)||u32(p+24)!=e->period||u32(p+28)!=e->target){failed(e,FS_COMMAND);return;}
 e->start_attempt=true;e->until=until;
 if(!e->io.prepare(e->io.ctx,until)||!before(e,until)){failed(e,FS_SPI);return;}
 uint32_t v;static const unsigned off[5]={0,4,8,0x28,0x2c};static const uint32_t expected[5]={0x46534731,32000000,0x74010,0,0};
 for(unsigned i=0;i<5;i++){if(!rd(e,off[i],&v,until))return;if(v!=expected[i]){failed(e,FS_SOURCE);return;}}
 uint32_t settings[6]={e->period,e->target,u32(e->nonce),u32(e->nonce+4),u32(e->nonce+8),u32(e->nonce+12)};
 for(unsigned i=0;i<6;i++){unsigned addr=0x10+4*i;if(!wr(e,addr,settings[i],until)||!rd(e,addr,&v,until))return;if(v!=settings[i]){failed(e,FS_SOURCE);return;}}
 /* Attempt timestamp precedes potentially consumed START. No retry on error. */
 e->start_us=clock_now(e);
 e->source_start_intent=true;
 if(!wr(e,0x0c,1,until)||!snapshot(e,until))return;
 if((e->snapshot.state&127u)!=67u||e->snapshot.generated||e->snapshot.enqueued||e->snapshot.popped||e->snapshot.remaining||e->snapshot.refused_pop||e->snapshot.refused_command||
    e->snapshot.start>UINT64_MAX-(uint64_t)e->period*e->target){failed(e,FS_SOURCE);return;}
 e->flags|=2;e->until=e->start_us+65*SECOND;e->phase=FS_RUNNING;
 memcpy(e->batch.nonce,e->nonce,16);e->batch.period_cycles=e->period;e->batch.target_records=e->target;control(e,3);
}
static void acquire(fs_engine *e){
 uint32_t state,v,words[4];
 if(e->queued==16||e->batch.count==26)return; /* Reserve first; no POP while full. */
 if(!rd(e,0x28,&state,e->until))return;
 if((state&~127u)||!(state&64u)){failed(e,FS_SOURCE);return;}
 if(!(state&8u)){
  if(state&4u){if(!rd(e,0x2c,&v,e->until))return;if(v>64){failed(e,FS_SOURCE);return;}if(!v)e->phase=FS_FINAL;}
  return;
 }
 unsigned off[4]={0x34,0x38,0x3c,0x44};uint8_t raw[16];
 for(unsigned i=0;i<4;i++){if(!rd(e,off[i],&words[i],e->until))return;w32(raw+4*i,words[i]);}
 fsg_record r;if(fsg_record_decode(raw,16,e->nonce,&r)!=FSG_OK||r.sequence>=e->target||r.sequence<e->next_sequence||
  r.tick32!=(uint32_t)(e->snapshot.start+(uint64_t)(r.sequence+1)*e->period)){failed(e,FS_RECORD);return;}
 if(r.sequence!=e->next_sequence&&e->status==FS_OK)e->status=FS_LOSS;
 if(!rd(e,0x48,&v,e->until))return;
 if(v!=e->confirmed){failed(e,FS_SOURCE);return;}
 e->pending=r;e->pending_flags=1;e->flags|=8;
 if(!wr(e,0x40,r.sequence,e->until)){e->status=FS_AMBIGUOUS;e->phase=FS_FINAL;return;}
 e->pending_flags|=2;
 if(!rd(e,0x48,&v,e->until)||v!=e->confirmed+1){e->status=FS_AMBIGUOUS;e->phase=FS_FINAL;return;}
 e->pending_flags|=4;e->confirmed++;e->next_sequence=r.sequence+1;
 if(!e->batch.count)e->batch_first=clock_now(e);
 e->batch.records[e->batch.count++]=r;e->pending_flags=0;e->flags&=~8u;
 if(e->batch.count==26)flush(e);
}
static void finalize(fs_engine *e){
 if(!e->final_us){
  uint64_t n=clock_now(e),cap=n+SECOND;if(cap>e->boot+120*SECOND)cap=e->boot+120*SECOND;
  if(e->source_start_intent&&e->trustworthy){
   uint32_t state;
   if(rd(e,0x28,&state,cap)){
    if(state&2u){e->stop_state=1;if(wr(e,0x0c,2,cap)&&snapshot(e,cap)){if(e->snapshot.state&2u)failed(e,FS_SOURCE);else e->stop_state=2;}}
    else snapshot(e,cap); /* STOP on an already completed source is refused. */
   }
  }
  e->io.safe(e->io.ctx);e->final_us=clock_now(e);e->terminal_until=e->final_us+2*SECOND;
  if(e->terminal_until>e->boot+120*SECOND)e->terminal_until=e->boot+120*SECOND;
  if(e->status==FS_OK&&e->snapshot.dropped)e->status=FS_LOSS;
  if((e->status==FS_OK||e->status==FS_LOSS)&&(e->snapshot.generated!=e->target||e->snapshot.popped!=e->confirmed||e->snapshot.remaining||e->snapshot.refused_pop||e->snapshot.refused_command||!(e->flags&4u)))e->status=FS_SOURCE;
  if(e->status==FS_OK&&e->confirmed!=e->target)e->status=FS_SOURCE;
 }
 if(!flush(e))return;
 /* END counters cover all DATA acceptance; do not interleave a partial frame. */
 if(e->queued)return;
 if(e->status==FS_OK&&e->staged!=e->confirmed)e->status=FS_USB;
 control(e,4);e->end_queued=true;e->phase=FS_TERMINAL;
}
void fs_step(fs_engine *e){
 if(e->phase==FS_DONE)return;
 e->io.service(e->io.ctx);uint64_t n=clock_now(e);
 if(n>=e->boot+120*SECOND||((e->phase==FS_FINAL||e->phase==FS_TERMINAL)&&e->terminal_until&&n>=e->terminal_until)){
  if(e->status==FS_OK||e->status==FS_LOSS)e->status=FS_USB;
  e->io.safe(e->io.ctx);e->phase=FS_DONE;return;
 }
 usb(e);
 if(e->phase==FS_IDLE||e->phase==FS_CONFIGURED){if(n>=e->boot+30*SECOND)failed(e,FS_DEADLINE);}
 if(e->phase==FS_RUNNING){
  if(n>=e->until)failed(e,FS_DEADLINE);
  else {
   if(e->batch.count&&n-e->batch_first>=100000)flush(e);
   if(e->pause_enabled&&n>=e->start_us+30*SECOND&&!e->pause_start){e->pause_start=n;e->pause_end=n+100000;}
   if(!e->pause_start||n>=e->pause_end)acquire(e);
  }
 }
 if(e->phase==FS_FINAL)finalize(e);
 n=clock_now(e);
 if(e->clock_bad||n>=e->boot+120*SECOND||((e->phase==FS_FINAL||e->phase==FS_TERMINAL)&&e->terminal_until&&n>=e->terminal_until)){
  if(e->status==FS_OK||e->status==FS_LOSS)e->status=FS_USB;
  e->io.safe(e->io.ctx);e->phase=FS_DONE;
 }else if(e->phase==FS_TERMINAL&&!e->queued)e->phase=FS_DONE;
}

#include "protocol.h"
#include <string.h>
static uint32_t get32(const uint8_t *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void put32(uint8_t *p,uint32_t v) { for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i)); }
uint32_t bridge_crc(const uint8_t *p,unsigned n) {
 uint32_t v=~UINT32_C(0);
 for(unsigned i=0;i<n;i++){v^=p[i];for(unsigned b=0;b<8;b++)v=(v>>1)^((0-(v&1))&UINT32_C(0xedb88320));}
 return ~v;
}
bool bridge_parse(const uint8_t p[BRIDGE_REQUEST_BYTES],bridge_request *r) {
 if(memcmp(p,"FGSB",4)||p[4]!=1||p[6]||p[7]||get32(p+44)!=bridge_crc(p,44))return false;
 for(unsigned i=36;i<44;i++)if(p[i])return false;
 r->op=p[5];r->sequence=get32(p+8);memcpy(r->nonce,p+12,16);
 r->address=get32(p+28);r->value=get32(p+32);return true;
}
bool bridge_allowed(const bridge_request *r) {
 unsigned nonce=0;for(unsigned i=0;i<16;i++)nonce|=r->nonce[i];
 if(!nonce||!r->sequence||r->sequence>BRIDGE_MAX_COMMANDS)return false;
 switch(r->op){
 case BRIDGE_ARM:case BRIDGE_FINISH:return !r->address&&!r->value;
 case BRIDGE_READ:return !r->value&&(r->address==BRIDGE_COUNTER_ADDR||r->address==BRIDGE_SCRATCH_ADDR);
 case BRIDGE_WRITE:return r->address==BRIDGE_SCRATCH_ADDR;
 default:return false;
 }
}
unsigned bridge_admit(bridge_session *s,const bridge_request *r,uint64_t age_us) {
 if(!s->attempted){
  if(r->op!=BRIDGE_ARM||r->sequence!=1||!bridge_allowed(r)||age_us>=UINT64_C(30000000))return BRIDGE_INERT;
  s->attempted=true;s->next=2;memcpy(s->nonce,r->nonce,16);return BRIDGE_START;
 }
 if(r->sequence!=s->next||s->next>BRIDGE_MAX_COMMANDS||memcmp(s->nonce,r->nonce,16))return BRIDGE_INERT;
 s->next++;return bridge_allowed(r)?BRIDGE_COMMAND:BRIDGE_REJECT;
}
unsigned bridge_wire_request(const bridge_request *r,uint8_t p[9]) {
 if(!bridge_allowed(r)||(r->op!=BRIDGE_READ&&r->op!=BRIDGE_WRITE))return 0;
 p[0]=r->op==BRIDGE_WRITE?0:1;
 for(unsigned i=0;i<4;i++){p[1+i]=(uint8_t)(r->address>>(24-8*i));p[5+i]=(uint8_t)(r->value>>(24-8*i));}
 return r->op==BRIDGE_WRITE?9:5;
}
unsigned bridge_wire_response(bool write,const uint8_t p[64],uint32_t *value) {
 unsigned i=0;while(i<64&&p[i]==0xff)i++;
 if(i==64)return BRIDGE_TIMEOUT;
 if(p[i]!=(write?0:1)||(!write&&i>59))return BRIDGE_BAD_RESPONSE;
 if(!write)*value=((uint32_t)p[i+1]<<24)|((uint32_t)p[i+2]<<16)|((uint32_t)p[i+3]<<8)|p[i+4];
 return BRIDGE_OK; /* SPIBone's ACK/ERR response is indistinguishable. Readback verifies writes. */
}
void bridge_response(uint8_t p[BRIDGE_RESPONSE_BYTES],const bridge_request *r,
                     unsigned status,uint32_t value,uint64_t now,const char hash[64]) {
 memset(p,0,BRIDGE_RESPONSE_BYTES);memcpy(p,"FGSB",4);p[4]=1;p[5]=r->op;p[6]=(uint8_t)status;
 put32(p+8,r->sequence);memcpy(p+12,r->nonce,16);put32(p+28,r->address);put32(p+32,value);
 for(unsigned i=0;i<8;i++)p[36+i]=(uint8_t)(now>>(8*i));
 memcpy(p+44,hash,64);put32(p+108,32000000);put32(p+112,150000000);
 put32(p+124,bridge_crc(p,124));
}

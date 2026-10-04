#include "platform.h"
/* Explicit new source-only map, not an extension to bridge_allowed(). */
unsigned fs_source_packet(const bridge_request *r,uint8_t out[9]){
 if(!r||!out||r->address<0x10000u||r->address>0x10098u||(r->address&3u))return 0;
 unsigned off=r->address-0x10000u;bool write=r->op==BRIDGE_WRITE;
 if(r->op!=BRIDGE_READ&&!write)return 0;
 bool allowed=false;
 if(write){
  if(off==0x0c)allowed=r->value==1||r->value==2||r->value==4;
  else if(off==0x40)allowed=true;
  else allowed=off>=0x10&&off<=0x24;
 }else allowed=off!=0x0c&&off!=0x40;
 if(!allowed)return 0;
 out[0]=write?0:1;
 for(unsigned i=0;i<4;i++){out[1+i]=(uint8_t)(r->address>>(24-8*i));out[5+i]=(uint8_t)(r->value>>(24-8*i));}
 return write?9:5;
}

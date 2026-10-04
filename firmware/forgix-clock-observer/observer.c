#include "observer.h"
#include <string.h>
static unsigned admission(const observer_io *io,uint64_t until) {
 if(io->cancelled(io->ctx))return OBSERVER_CANCELLED;
 return io->now(io->ctx)>=until?OBSERVER_TIMEOUT:OBSERVER_OK;
}
unsigned observer_capture(const observer_io *io,bool *attempted,uint64_t until,
                          observer_result *out) {
 if(!io||!attempted||!out||!io->now||!io->cancelled||!io->prepare_input||
    !io->start||!io->ready||!io->take||!io->service||!io->stop_input)return OBSERVER_REFUSED;
 memset(out,0,sizeof(*out));out->status=OBSERVER_REFUSED;
 if(*attempted)return out->status;
 *attempted=true;out->began_us=io->now(io->ctx);
 if(until<=out->began_us||until-out->began_us>CLOCK_OBSERVER_MAX_US){
  out->cleanup_verified=true;out->ended_us=out->began_us;return out->status;
 }
 unsigned status=admission(io,until);bool touched=false;
 if(status)goto finish;
 touched=true;
 bool ok=io->prepare_input(io->ctx,until);
 status=admission(io,until);if(status)goto finish;
 if(!ok){status=OBSERVER_IO;goto finish;}
 ok=io->start(io->ctx,until);
 status=admission(io,until);if(status)goto finish;
 if(!ok){status=OBSERVER_IO;goto finish;}
 while(out->count<CLOCK_OBSERVER_SAMPLES){
  status=admission(io,until);if(status)goto finish;
  bool ready=io->ready(io->ctx);
  status=admission(io,until);if(status)goto finish;
  if(ready){
   uint32_t n=UINT32_MAX-io->take(io->ctx);
   /* Retain a returned late/impossible sample before classifying it. */
   out->decrements[out->count++]=n;
   status=admission(io,until);if(status)goto finish;
   if(n<=8||n>=UINT32_C(0x7fffffff)){status=OBSERVER_PERIOD;goto finish;}
  }
  io->service(io->ctx);
  status=admission(io,until);if(status)goto finish;
 }
finish:
 if(touched)out->cleanup_verified=io->stop_input(io->ctx);
 else out->cleanup_verified=true; /* No application pin/PIO callback invoked. */
 if(!out->cleanup_verified&&status==OBSERVER_OK)status=OBSERVER_IO;
 unsigned late=admission(io,until);if(!status&&late)status=late;
 out->ended_us=io->now(io->ctx);
 if(!status&&out->ended_us>=until)status=OBSERVER_TIMEOUT;
 out->status=status;return status;
}

/* Host-only actual-engine accessors; production has no allocator. */
#include "engine.h"
size_t engine_size(void){return sizeof(fs_engine);}
uint64_t engine_field(fs_engine *e,unsigned n){
 const uint64_t v[]={e->phase,e->status,e->flags,e->confirmed,e->staged,e->frames,e->frames_sent,
 e->queued,e->offset,e->pending_flags,e->highwater,e->usb_bytes,e->partial_writes,e->stalls,
 e->max_stall,e->snapshot.generated,e->snapshot.enqueued,e->snapshot.dropped,e->snapshot.popped,
 e->snapshot.remaining,e->stop_state,e->pause_start,e->pause_end,e->start_attempt,e->configured_attempt};
 return n<sizeof(v)/sizeof(v[0])?v[n]:UINT64_MAX;
}

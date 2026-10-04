#pragma once
#include "codec.h"
enum fs_status { FS_OK, FS_COMMAND, FS_DEADLINE, FS_CONFIG, FS_SPI,
 FS_SOURCE, FS_RECORD, FS_AMBIGUOUS, FS_LOSS, FS_USB };
enum fs_phase { FS_IDLE, FS_CONFIGURED, FS_RUNNING, FS_FINAL, FS_TERMINAL, FS_DONE };
/* Platform owns deadlines, one TinyUSB owner and physical pin cleanup. All
 * callbacks are bounded; xfer uses only the explicit source CSR map. */
typedef struct {
 void *ctx;
 uint64_t (*now)(void *);
 void (*service)(void *);
 bool (*configure)(void *, uint64_t);
 bool (*prepare)(void *, uint64_t);
 bool (*xfer)(void *, bool, uint32_t, uint32_t *, uint64_t);
 size_t (*usb)(void *, const uint8_t *, size_t);
 void (*safe)(void *);
} fs_io;
typedef struct {
 uint32_t id,state,generated,enqueued,dropped,popped,remaining,highwater,
 refused_pop,refused_command;
 uint64_t tick,start,stop;
} fs_snapshot;
typedef struct {
 fs_io io;
 uint8_t build[32],image[32],nonce[16];
 uint64_t boot,last_now,start_us,final_us,until,terminal_until,batch_first,
 stall_start,max_stall,pause_start,pause_end;
 uint32_t period,target,status,flags,pending_flags,stop_state,next_sequence,
 confirmed,staged,frames,frames_sent,partial_writes,stalls,highwater;
 uint64_t usb_bytes;
 enum fs_phase phase;
 bool configured_attempt,start_attempt,source_start_intent,trustworthy,stalling,end_queued,pause_enabled,clock_bad;
 fs_snapshot snapshot;
 fsg_record pending;
 fsg_batch batch;
 uint8_t queue[16][512];
 uint8_t read_slot,write_slot,queued;
 uint16_t offset;
} fs_engine;
bool fs_init(fs_engine *, fs_io, const uint8_t build[32],const uint8_t image[32],bool pause);
void fs_command(fs_engine *,const uint8_t *,size_t);
void fs_step(fs_engine *);

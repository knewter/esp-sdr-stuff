#ifndef FORGIX_CLOCK_ENGINE_H
#define FORGIX_CLOCK_ENGINE_H
#include "observer.h"
#include <stddef.h>
enum { FC_WAIT,FC_READ,FC_CONFIG,FC_OBSERVE,FC_SEND,FC_DONE };
typedef struct {
 void *ctx;
 uint64_t (*now)(void *);
 bool (*cancelled)(void *);
 unsigned (*configure)(void *,uint64_t);
 size_t (*usb)(void *,const uint8_t *,size_t);
 void (*service)(void *);
 observer_io observer;
} fc_io;
typedef struct {
 fc_io io; uint64_t boot,request_us,config_begin,config_end,encoded,drain_until;
 uint8_t build[32],image[32],command[128],reply[512];
 unsigned phase,command_length,config_status,reply_offset;
 bool attempted,configuration_attempted,measurement_attempted;
 observer_result result;
} fc_engine;
uint32_t fc_crc(const uint8_t *,unsigned);
bool fc_init(fc_engine *,fc_io,const uint8_t [32],const uint8_t [32],uint64_t);
void fc_feed(fc_engine *,const uint8_t *,size_t);
void fc_step(fc_engine *);
#endif

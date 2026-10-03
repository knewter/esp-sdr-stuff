#pragma once
#include <stdbool.h>
#include <stdint.h>
#define BRIDGE_REQUEST_BYTES 48u
#define BRIDGE_RESPONSE_BYTES 128u
#define BRIDGE_COUNTER_ADDR UINT32_C(0x1000)
#define BRIDGE_SCRATCH_ADDR UINT32_C(0x1004)
#define BRIDGE_MAX_COMMANDS 24u
enum { BRIDGE_ARM=1, BRIDGE_READ=2, BRIDGE_WRITE=3, BRIDGE_FINISH=4 };
enum { BRIDGE_OK=0, BRIDGE_REFUSED=1, BRIDGE_TIMEOUT=2, BRIDGE_BAD_RESPONSE=3,
       BRIDGE_NOT_DONE=4, BRIDGE_CLOCK_MISMATCH=5 };
typedef struct { uint8_t op, nonce[16]; uint32_t sequence, address, value; } bridge_request;
typedef struct { bool attempted; uint8_t nonce[16]; uint32_t next; } bridge_session;
enum { BRIDGE_INERT, BRIDGE_START, BRIDGE_COMMAND, BRIDGE_REJECT };
unsigned bridge_admit(bridge_session *s,const bridge_request *r,uint64_t age_us);
uint32_t bridge_crc(const uint8_t *p, unsigned length);
bool bridge_parse(const uint8_t input[BRIDGE_REQUEST_BYTES], bridge_request *r);
bool bridge_allowed(const bridge_request *r);
unsigned bridge_wire_request(const bridge_request *r, uint8_t output[9]);
unsigned bridge_wire_response(bool write, const uint8_t input[64], uint32_t *value);
void bridge_response(uint8_t output[BRIDGE_RESPONSE_BYTES], const bridge_request *r,
                     unsigned status, uint32_t value, uint64_t now, const char hash[64]);

#ifndef FORGIX_CLOCK_OBSERVER_H
#define FORGIX_CLOCK_OBSERVER_H
#include <stdbool.h>
#include <stdint.h>
#define CLOCK_OBSERVER_SAMPLES 16u
#define CLOCK_OBSERVER_MAX_US UINT64_C(2000000)
enum { OBSERVER_OK, OBSERVER_REFUSED, OBSERVER_TIMEOUT, OBSERVER_IO,
       OBSERVER_CANCELLED, OBSERVER_PERIOD };
typedef struct {
 void *ctx;
 uint64_t (*now)(void *);
 bool (*cancelled)(void *);
 bool (*prepare_input)(void *, uint64_t);
 bool (*start)(void *, uint64_t);
 bool (*ready)(void *);
 uint32_t (*take)(void *);
 void (*service)(void *);
 bool (*stop_input)(void *);
} observer_io;
typedef struct {
 unsigned status, count;
 uint32_t decrements[CLOCK_OBSERVER_SAMPLES];
 uint64_t began_us, ended_us;
 bool cleanup_verified;
} observer_result;
/* Caller owns checked UID/configuration, watchdog, absolute120s lifetime and
 * complete preserved lifecycle. This boundary cannot configure or drive DATA. */
unsigned observer_capture(const observer_io *, bool *, uint64_t, observer_result *);
#endif

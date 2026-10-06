/* CYD on-screen waterfall hooks for the ESP-SDR ESP32 receiver loop. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    /* Fill 16 MS/s IQ words; false on capture failure. */
    bool (*acquire)(unsigned n, const uint32_t **words);
    /* Retune exactly as the FREQ command does; false if out of range. */
    bool (*tune)(unsigned mhz);
    unsigned (*frequency)(void);
    bool (*hardware_agc)(void);
} cyd_radio_t;

void cyd_display_init(const cyd_radio_t *radio);
/* Called when the receiver loop has no host line; draws at most one row. */
void cyd_display_idle(void);
/* Called for every host line; pauses the display until the host is idle. */
void cyd_display_host_activity(void);

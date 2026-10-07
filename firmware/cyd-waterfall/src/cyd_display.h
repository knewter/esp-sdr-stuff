/* CYD on-screen waterfall hooks for the ESP-SDR ESP32 receiver loop. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    /* Fill IQ words at span index 0/1/2 = 16/40/80 MS/s; false on failure. */
    bool (*acquire)(unsigned n, unsigned span_index, const uint32_t **words);
    /* Retune exactly as the FREQ command does; false if out of range. */
    bool (*tune)(unsigned mhz);
    unsigned (*frequency)(void);
    /* As GAIN HARDWARE / GAIN MANUAL <code>. */
    void (*set_gain)(bool hardware_agc, unsigned code);
    bool (*hardware_agc)(void);
    unsigned (*gain_code)(void);
    unsigned (*gain_max)(void);
    /* As BANDWIDTH <mhz>; 0 restores the automatic filter. */
    bool (*set_filter)(unsigned mhz);
} cyd_radio_t;

void cyd_display_init(const cyd_radio_t *radio);
/* Called when the receiver loop has no host line; draws at most one row. */
void cyd_display_idle(void);
/* Host lines starting with CYD are display commands (CYDSHOT, CYDSTAT,
 * CYDSTATRESET, CYDTAP x y ms); they are answered here, return true and do
 * not pause the display. */
bool cyd_display_host_line(const char *line);
/* Called for every other host line; pauses the display until the host is idle. */
void cyd_display_host_activity(void);

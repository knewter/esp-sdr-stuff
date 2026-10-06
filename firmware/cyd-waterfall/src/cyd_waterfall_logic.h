/* Hardware-free waterfall logic for the CYD display build. Compiled into the
 * firmware and, unchanged, into host tests. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define CYD_FFT_SIZE 512
#define CYD_COLUMNS 240
#define CYD_SAMPLE_RATE_HZ 16000000
#define CYD_STATUS_HEIGHT 40
#define CYD_SCREEN_HEIGHT 320
#define CYD_RANGE_DB 30.0f

/* Signed 10-bit I (bits 0..9) and Q (bits 10..19) of one capture word. */
void cyd_unpack(uint32_t word, float *i, float *q);

/* Max-hold power per column, in dB, over every whole FFT_SIZE block of the
 * capture. Column 0 is the lowest frequency (LO - 8 MHz). Returns blocks used. */
unsigned cyd_row_db(const uint32_t *words, unsigned n, float column_db[CYD_COLUMNS]);

/* Running noise floor: a slow IIR on the row's 25th-percentile column. */
float cyd_floor_update(float floor_db, const float column_db[CYD_COLUMNS], bool first);

/* 0..255 intensity above the floor over CYD_RANGE_DB, then RGB565. */
uint8_t cyd_level(float db, float floor_db);
uint16_t cyd_palette(uint8_t level);

/* Column under a tap -> frequency in MHz, rounded to whole MHz. */
int cyd_column_mhz(int lo_mhz, int column);

typedef enum { CYD_TOUCH_NONE, CYD_TOUCH_DOWN, CYD_TOUCH_STEP, CYD_TOUCH_UP,
               CYD_TOUCH_LABEL, CYD_TOUCH_WATERFALL } cyd_touch_t;
/* Screen point (portrait, 240x320) -> control. */
cyd_touch_t cyd_touch_target(int x, int y);
/* XPT2046 raw 12-bit readings -> portrait screen point. */
void cyd_touch_map(int raw_x, int raw_y, int *x, int *y);

extern const int cyd_steps_mhz[3];

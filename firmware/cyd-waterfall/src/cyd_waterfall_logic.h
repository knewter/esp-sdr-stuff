/* Hardware-free waterfall logic for the CYD display build. Compiled into the
 * firmware and, unchanged, into host tests. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define CYD_FFT_SIZE 512
#define CYD_COLUMNS 240
#define CYD_SCREEN_HEIGHT 320

/* Screen regions, top to bottom (portrait 240x320). */
#define CYD_STATUS_Y 0
#define CYD_STATUS_H 32
#define CYD_SCALE_Y 32
#define CYD_SCALE_H 12
#define CYD_SPECTRUM_Y 44
#define CYD_SPECTRUM_H 48
#define CYD_WATERFALL_Y 92
#define CYD_WATERFALL_H 172
#define CYD_CONTROLS_Y 264
#define CYD_CONTROLS_H 56
#define CYD_MENU_ROWS 5
#define CYD_MENU_COLS 3

/* Spans follow the ESP32 hardware sample rates (16/40/80 MS/s). */
#define CYD_SPANS 3
extern const int cyd_span_mhz[CYD_SPANS];
extern const int cyd_steps_mhz[3];
#define CYD_FILTERS 5
extern const int cyd_filter_mhz[CYD_FILTERS]; /* 0 = automatic */
#define CYD_RANGES 4
extern const int cyd_range_db[CYD_RANGES];

/* Signed 10-bit I (bits 0..9) and Q (bits 10..19) of one capture word. */
void cyd_unpack(uint32_t word, float *i, float *q);

/* Max-hold power per column, in dB, over every whole FFT_SIZE block of the
 * capture. Column 0 is the lowest frequency (LO - span/2). Returns blocks used. */
unsigned cyd_row_db(const uint32_t *words, unsigned n, float column_db[CYD_COLUMNS]);

/* Running noise floor: a slow IIR on the row's 25th-percentile column. */
float cyd_floor_update(float floor_db, const float column_db[CYD_COLUMNS], bool first);
/* Peak hold that decays by decay_db per row and never sits below the row. */
void cyd_peak_update(float peak_db[CYD_COLUMNS], const float column_db[CYD_COLUMNS], float decay_db, bool reset);

/* 0..255 intensity above the floor over range_db, then RGB565. */
uint8_t cyd_level(float db, float floor_db, float range_db);
uint16_t cyd_palette(uint8_t level);

/* Column <-> frequency for a span (MHz across CYD_COLUMNS, centred on LO). */
int cyd_column_mhz(int lo_mhz, int column, int span_mhz);
/* Column for an offset from LO in kHz, or -1 when outside the span. */
int cyd_offset_column(int offset_khz, int span_mhz);
/* Strongest column; returns its index. */
int cyd_peak_column(const float column_db[CYD_COLUMNS]);

/* Per-column floor for FLAT mode: falls quickly, rises slowly, so filter
 * roll-off and steady carriers flatten while bursts stand out. */
void cyd_colfloor_update(float floor_db[CYD_COLUMNS], const float column_db[CYD_COLUMNS], bool reset);
/* Replace the LO-leakage columns around the centre by interpolation. */
void cyd_mask_dc(float column_db[CYD_COLUMNS]);
#define CYD_PEAK_MIN_DB 10.0f
/* One spectrum-strip line (row 0 = top of the strip): filled trace with the
 * floor sitting at CYD_BASELINE of the height, bright edge, peak-hold dots
 * (only CYD_PEAK_MIN_DB above the floor), grid, marker and cursor columns. */
#define CYD_BASELINE 0.15f
void cyd_spectrum_line(const float db[CYD_COLUMNS], const float peak[CYD_COLUMNS], const float floor_db[CYD_COLUMNS],
                       float range_db, int row, int marker, int cursor, uint16_t out[CYD_COLUMNS]);

/* Rising-edge burst counter around a marker column. */
typedef struct { bool high; unsigned count; } cyd_burst_t;
bool cyd_burst_update(cyd_burst_t *b, const float db[CYD_COLUMNS], int marker, float floor_db, float threshold_db);

/* Persisted UI settings (NVS key "ui"). */
#define CYD_SETTINGS_VERSION 1
typedef struct {
    uint8_t version, span, filter, range, step, agc, gain, flat;
    int8_t preset;
    uint16_t lo_mhz;
} cyd_settings_t;
bool cyd_settings_valid(const cyd_settings_t *s);

/* Presets: an LO and where this board's measured carrier lands. */
#define CYD_MARKER_NONE (-100000)
typedef struct { const char *label; int lo_mhz; int marker_khz; bool measured; } cyd_preset_t;
#define CYD_PRESETS 7
extern const cyd_preset_t cyd_presets[CYD_PRESETS];

/* Touch targets. Main screen: controls row, or a tune tap on spectrum or
 * waterfall. Menu: a CYD_MENU_ROWS x CYD_MENU_COLS grid over the waterfall. */
typedef enum { CYD_HIT_NONE, CYD_HIT_DOWN, CYD_HIT_STEP, CYD_HIT_UP, CYD_HIT_MENU, CYD_HIT_TUNE } cyd_hit_t;
cyd_hit_t cyd_hit_main(int x, int y);
int cyd_hit_menu(int x, int y); /* item index, or -1 */

/* Touch calibration from three taps on crosses at fixed screen points:
 * top-left (20,20), top-right (220,20) and bottom-left (20,300). It finds
 * which raw channel follows screen x (swap) and each axis direction. */
#define CYD_CAL_MARGIN 20
typedef struct { int swap, u0, u1, v0, v2; } cyd_cal_t;
extern const cyd_cal_t cyd_cal_default;
/* raw[k] = {channel X (0xD0), channel Y (0x90)} for tap k. False if degenerate. */
bool cyd_touch_calibrate(const int raw[3][2], cyd_cal_t *cal);
/* XPT2046 raw 12-bit readings -> portrait screen point. */
void cyd_touch_map(const cyd_cal_t *cal, int raw_x, int raw_y, int *x, int *y);

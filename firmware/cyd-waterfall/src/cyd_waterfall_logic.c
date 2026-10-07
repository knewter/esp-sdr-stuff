/* Hardware-free waterfall logic for the CYD display build (GPLv3, as the
 * ESP-SDR project it extends). */
#include "cyd_waterfall_logic.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

const int cyd_steps_mhz[3] = {1, 5, 10};
const int cyd_span_mhz[CYD_SPANS] = {16, 40, 80};
const int cyd_filter_mhz[CYD_FILTERS] = {0, 12, 20, 40, 67};
const int cyd_range_db[CYD_RANGES] = {20, 30, 40, 50};

/* Measured on the user's CYD2USB (2026-10-06, read back from NVS): raw X
 * runs right-to-left, raw Y top-to-bottom. A calibration saved in NVS wins. */
const cyd_cal_t cyd_cal_default = {0, 3491, 537, 470, 3636};

void cyd_unpack(uint32_t word, float *i, float *q) {
    int32_t a = (int32_t)(word << 22) >> 22;
    int32_t b = (int32_t)((word >> 10) << 22) >> 22;
    *i = (float)a;
    *q = (float)b;
}

static void fft(float *re, float *im, unsigned n) {
    for (unsigned j = 1, k = 0; j < n; j++) {
        unsigned bit = n >> 1;
        for (; k & bit; bit >>= 1) k ^= bit;
        k ^= bit;
        if (j < k) {
            float t = re[j]; re[j] = re[k]; re[k] = t;
            t = im[j]; im[j] = im[k]; im[k] = t;
        }
    }
    for (unsigned len = 2; len <= n; len <<= 1) {
        float angle = -2.0f*(float)M_PI/(float)len;
        float wr = cosf(angle), wi = sinf(angle);
        for (unsigned j = 0; j < n; j += len) {
            float cr = 1.0f, ci = 0.0f;
            for (unsigned k = 0; k < len/2; k++) {
                unsigned a = j+k, b = j+k+len/2;
                float tr = re[b]*cr - im[b]*ci, ti = re[b]*ci + im[b]*cr;
                re[b] = re[a]-tr; im[b] = im[a]-ti;
                re[a] += tr; im[a] += ti;
                float nr = cr*wr - ci*wi;
                ci = cr*wi + ci*wr; cr = nr;
            }
        }
    }
}

unsigned cyd_row_db(const uint32_t *words, unsigned n, float column_db[CYD_COLUMNS]) {
    static float re[CYD_FFT_SIZE], im[CYD_FFT_SIZE], window[CYD_FFT_SIZE];
    static bool ready;
    if (!ready) {
        for (unsigned j = 0; j < CYD_FFT_SIZE; j++)
            window[j] = 0.5f - 0.5f*cosf(2.0f*(float)M_PI*(float)j/(float)CYD_FFT_SIZE);
        ready = true;
    }
    float column[CYD_COLUMNS];
    memset(column, 0, sizeof(column));
    unsigned blocks = n/CYD_FFT_SIZE;
    for (unsigned b = 0; b < blocks; b++) {
        float mi = 0, mq = 0;
        for (unsigned j = 0; j < CYD_FFT_SIZE; j++) {
            cyd_unpack(words[b*CYD_FFT_SIZE+j], &re[j], &im[j]);
            mi += re[j]; mq += im[j];
        }
        mi /= CYD_FFT_SIZE; mq /= CYD_FFT_SIZE;
        for (unsigned j = 0; j < CYD_FFT_SIZE; j++) {
            re[j] = (re[j]-mi)*window[j];
            im[j] = (im[j]-mq)*window[j];
        }
        fft(re, im, CYD_FFT_SIZE);
        for (unsigned j = 0; j < CYD_FFT_SIZE; j++) {
            /* fftshift: bin j holds frequency index (j + N/2) mod N. */
            unsigned bin = (j+CYD_FFT_SIZE/2) % CYD_FFT_SIZE;
            unsigned c = j*CYD_COLUMNS/CYD_FFT_SIZE;
            float p = re[bin]*re[bin] + im[bin]*im[bin];
            if (p > column[c]) column[c] = p;
        }
    }
    for (unsigned c = 0; c < CYD_COLUMNS; c++)
        column_db[c] = 10.0f*log10f(column[c] + 1e-3f);
    return blocks;
}

float cyd_floor_update(float floor_db, const float column_db[CYD_COLUMNS], bool first) {
    float sorted[CYD_COLUMNS];
    memcpy(sorted, column_db, sizeof(sorted));
    for (unsigned j = 1; j < CYD_COLUMNS; j++) {
        float v = sorted[j];
        unsigned k = j;
        for (; k > 0 && sorted[k-1] > v; k--) sorted[k] = sorted[k-1];
        sorted[k] = v;
    }
    float quartile = sorted[CYD_COLUMNS/4];
    return first ? quartile : floor_db + 0.05f*(quartile-floor_db);
}

void cyd_peak_update(float peak_db[CYD_COLUMNS], const float column_db[CYD_COLUMNS], float decay_db, bool reset) {
    for (unsigned c = 0; c < CYD_COLUMNS; c++) {
        float decayed = peak_db[c] - decay_db;
        peak_db[c] = reset || column_db[c] > decayed ? column_db[c] : decayed;
    }
}

uint8_t cyd_level(float db, float floor_db, float range_db) {
    float v = (db-floor_db)/range_db;
    if (v <= 0) return 0;
    if (v >= 1) return 255;
    return (uint8_t)(v*255.0f);
}

uint16_t cyd_palette(uint8_t level) {
    /* Black -> blue -> cyan -> yellow -> red -> white. */
    static const uint8_t stops[6][3] = {{0,0,0},{0,0,200},{0,200,220},{240,230,0},{240,0,0},{255,255,255}};
    unsigned segment = level*5/256, base = segment*256/5;
    unsigned frac = (level-base)*5;
    if (frac > 255) frac = 255;
    const uint8_t *a = stops[segment], *b = stops[segment+1];
    unsigned r = a[0]+((b[0]-a[0])*(int)frac)/255;
    unsigned g = a[1]+((b[1]-a[1])*(int)frac)/255;
    unsigned bl = a[2]+((b[2]-a[2])*(int)frac)/255;
    return (uint16_t)(((r & 0xf8) << 8) | ((g & 0xfc) << 3) | (bl >> 3));
}

int cyd_column_mhz(int lo_mhz, int column, int span_mhz) {
    float offset = ((float)column+0.5f)*(float)span_mhz/(float)CYD_COLUMNS - (float)span_mhz/2.0f;
    return lo_mhz + (int)lroundf(offset);
}

int cyd_offset_column(int offset_khz, int span_mhz) {
    /* Floor, not truncation: column c covers [c, c+1) in offset units. */
    long c = CYD_COLUMNS/2 + (long)floorf((float)offset_khz*CYD_COLUMNS/((float)span_mhz*1000.0f));
    return c < 0 || c >= CYD_COLUMNS ? -1 : (int)c;
}

int cyd_peak_column(const float column_db[CYD_COLUMNS]) {
    int best = 0;
    for (int c = 1; c < CYD_COLUMNS; c++) if (column_db[c] > column_db[best]) best = c;
    return best;
}

static uint16_t dim(uint16_t c) {
    return (uint16_t)((c >> 1) & 0x7bef);
}

void cyd_colfloor_update(float floor_db[CYD_COLUMNS], const float column_db[CYD_COLUMNS], bool reset) {
    /* A quantile tracker settles where half the rows sit above it: the
     * column's median. Device data showed a minimum-tracking floor let
     * ordinary noise peaks count as traffic in every Wi-Fi channel. */
    for (unsigned c = 0; c < CYD_COLUMNS; c++) {
        float d = column_db[c]-floor_db[c];
        floor_db[c] = reset ? column_db[c] : floor_db[c] + (d > 0 ? CYD_FLOOR_STEP_DB : -CYD_FLOOR_STEP_DB);
    }
}

void cyd_mask_dc(float column_db[CYD_COLUMNS]) {
    int lo = CYD_COLUMNS/2-2, hi = CYD_COLUMNS/2+2;
    for (int c = lo+1; c < hi; c++)
        column_db[c] = column_db[lo] + (column_db[hi]-column_db[lo])*(float)(c-lo)/(float)(hi-lo);
}

void cyd_spectrum_line(const float db[CYD_COLUMNS], const float peak[CYD_COLUMNS], const float floor_db[CYD_COLUMNS],
                       float range_db, int row, int marker, int cursor, uint16_t out[CYD_COLUMNS]) {
    int h = CYD_SPECTRUM_H, from_bottom = h-1-row;
    bool grid_row = row == h/4 || row == h/2 || row == 3*h/4;
    float span = range_db/(1.0f-CYD_BASELINE);
    for (int c = 0; c < CYD_COLUMNS; c++) {
        float base = floor_db[c]-CYD_BASELINE*span;
        int bar = cyd_level(db[c], base, span)*(h-1)/255;
        int held = cyd_level(peak[c], base, span)*(h-1)/255;
        uint16_t v = 0x0000;
        if (grid_row && c % 4 == 0) v = 0x2104;
        if (c == marker && row % 3 != 2) v = 0xf81f;
        if (c == cursor && row % 2 == 0) v = 0x07ff;
        if (from_bottom < bar) v = dim(cyd_palette(cyd_level(db[c], floor_db[c], range_db)) | 0x0841);
        if (from_bottom == bar) v = 0xffff;
        if (from_bottom == held && held > bar && peak[c]-floor_db[c] >= CYD_PEAK_MIN_DB) v = 0xffe0;
        out[c] = v;
    }
}

bool cyd_settings_valid(const cyd_settings_t *s) {
    return s->version == CYD_SETTINGS_VERSION && s->span < CYD_SPANS && s->filter < CYD_FILTERS &&
           s->range < CYD_RANGES && s->step < 3 && s->agc <= 1 && s->gain <= 127 && s->flat <= 1 &&
           s->preset >= -1 && s->preset < CYD_PRESETS && s->lo_mhz >= 100 && s->lo_mhz <= 6000;
}

static float side_mean(const float db[CYD_COLUMNS], int from, int to) {
    float sum = 0;
    int n = 0;
    for (int c = from; c <= to; c++)
        if (c >= 0 && c < CYD_COLUMNS) { sum += db[c]; n++; }
    return n ? sum/(float)n : -1e9f;
}

bool cyd_burst_update(cyd_burst_t *b, const float db[CYD_COLUMNS], const float colfloor[CYD_COLUMNS], int marker, int half) {
    if (marker < 0) return false;
    float excess = -1e9f;
    int at = marker;
    for (int c = marker-half; c <= marker+half; c++)
        if (c >= 0 && c < CYD_COLUMNS && db[c]-colfloor[c] > excess) { excess = db[c]-colfloor[c]; at = c; }
    float best = db[at];
    marker = at;
    /* Narrowband: BLE is ~2 MHz wide, Wi-Fi ~20 MHz. Measured on the device,
     * Wi-Fi bursts covering the marker otherwise counted as BLE hits. */
    float side = side_mean(db, marker-CYD_BURST_SIDE_FAR, marker-CYD_BURST_SIDE_NEAR);
    float other = side_mean(db, marker+CYD_BURST_SIDE_NEAR, marker+CYD_BURST_SIDE_FAR);
    if (other > side) side = other;
    bool high = excess >= CYD_BURST_THRESHOLD_DB && best-side >= CYD_BURST_CONTRAST_DB;
    bool rising = high && !b->high;
    b->high = high;
    if (rising) b->count++;
    return rising;
}

/* Board-specific markers from spectrum sessions 004/005 (16 MS/s): ch37 at
 * LO 2401 lands near 2404.3 MHz, ch38 at LO 2425 near 2419.1 MHz. ch39 is
 * unlocated, so its marker is the nominal channel. Wi-Fi markers are nominal. */
const cyd_preset_t cyd_presets[CYD_PRESETS] = {
    {"BLE 37", 2401, 3300, true},
    {"BLE 38", 2425, -5900, true},
    {"BLE 39", 2479, 1000, false},
    {"WIFI 1", 2412, 0, false},
    {"WIFI 6", 2437, 0, false},
    {"WIFI 11", 2462, 0, false},
    {"2.4 BAND", 2442, CYD_MARKER_NONE, false},
};

cyd_hit_t cyd_hit_main(int x, int y) {
    if (x < 0 || x >= CYD_COLUMNS || y < 0 || y >= CYD_SCREEN_HEIGHT) return CYD_HIT_NONE;
    if (y >= CYD_CONTROLS_Y) {
        static const cyd_hit_t row[4] = {CYD_HIT_DOWN, CYD_HIT_STEP, CYD_HIT_UP, CYD_HIT_MENU};
        return row[x*4/CYD_COLUMNS];
    }
    if (y >= CYD_SPECTRUM_Y) return CYD_HIT_TUNE;
    return CYD_HIT_NONE;
}

int cyd_hit_menu(int x, int y) {
    if (x < 0 || x >= CYD_COLUMNS || y < CYD_WATERFALL_Y || y >= CYD_WATERFALL_Y+CYD_WATERFALL_H) return -1;
    int r = (y-CYD_WATERFALL_Y)*CYD_MENU_ROWS/CYD_WATERFALL_H, c = x*CYD_MENU_COLS/CYD_COLUMNS;
    return r*CYD_MENU_COLS + c;
}

static int clamp(int v, int out) {
    return v < 0 ? 0 : v >= out ? out-1 : v;
}

bool cyd_touch_calibrate(const int raw[3][2], cyd_cal_t *cal) {
    /* Top-left -> top-right moves only screen x: the raw channel that
     * changes most there is the x channel. */
    int dx = abs(raw[1][0]-raw[0][0]), dy = abs(raw[1][1]-raw[0][1]);
    int swap = dy > dx;
    int u = swap, v = !swap;
    cyd_cal_t c = {swap, raw[0][u], raw[1][u], raw[0][v], raw[2][v]};
    if (abs(c.u1-c.u0) < 300 || abs(c.v2-c.v0) < 300) return false;
    *cal = c;
    return true;
}

void cyd_touch_map(const cyd_cal_t *cal, int raw_x, int raw_y, int *x, int *y) {
    int raw[2] = {raw_x, raw_y};
    int u = raw[cal->swap], v = raw[!cal->swap];
    int span_x = CYD_COLUMNS-2*CYD_CAL_MARGIN, span_y = CYD_SCREEN_HEIGHT-2*CYD_CAL_MARGIN;
    *x = clamp(CYD_CAL_MARGIN+(u-cal->u0)*span_x/(cal->u1-cal->u0), CYD_COLUMNS);
    *y = clamp(CYD_CAL_MARGIN+(v-cal->v0)*span_y/(cal->v2-cal->v0), CYD_SCREEN_HEIGHT);
}

void cyd_wifi_reset(cyd_wifi_t *w) {
    for (int n = 0; n < CYD_WIFI_CHANNELS; n++) w->busy[n] = -1.0f;
}

void cyd_wifi_update(cyd_wifi_t *w, const float db[CYD_COLUMNS], const float floor_db[CYD_COLUMNS],
                     int lo_mhz, int span_mhz, float threshold_db, float alpha) {
    for (int n = 0; n < CYD_WIFI_CHANNELS; n++) {
        int centre_khz = (2412 + 5*n - lo_mhz)*1000;
        int a = cyd_offset_column(centre_khz-8000, span_mhz), b = cyd_offset_column(centre_khz+8000, span_mhz);
        if (a < 0 || b < 0) continue;
        int above = 0;
        for (int c = a; c <= b; c++) above += db[c]-floor_db[c] >= threshold_db;
        float occupied = (float)above/(float)(b-a+1);
        w->busy[n] = w->busy[n] < 0 ? occupied : w->busy[n] + alpha*(occupied-w->busy[n]);
    }
}

int cyd_wifi_best(const cyd_wifi_t *w) {
    static const int choices[3] = {1, 6, 11};
    int best = 0;
    for (int k = 0; k < 3; k++) {
        float b = w->busy[choices[k]-1];
        if (b >= 0 && (!best || b < w->busy[best-1])) best = choices[k];
    }
    return best;
}

const char *cyd_activity_word(float busy) {
    if (busy < 0) return "WAIT";
    if (busy < 0.05f) return "QUIET";
    if (busy < 0.20f) return "LOW";
    if (busy < 0.50f) return "BUSY";
    return "VERY BUSY";
}

float cyd_ble_per_minute(const cyd_ble_t *b, int index) {
    return b->seconds[index] > 0 ? (float)b->bursts[index]*60.0f/b->seconds[index] : -1.0f;
}

const char *cyd_ble_word(float per_minute) {
    if (per_minute < 0) return "WAIT";
    /* Snapshot hits, not packets. Measured on the device: about 41 rows/s
     * on this screen, a third per channel, so one advertiser every 25 ms
     * (~1.8% of rows) is seen about 15 times a minute. */
    if (per_minute < 5) return "QUIET";
    if (per_minute < 30) return "LOW";
    if (per_minute < 120) return "BUSY";
    return "VERY BUSY";
}

int cyd_filter_for_span(int span_mhz) {
    return span_mhz <= 16 ? 0 : span_mhz <= 40 ? 40 : 67;
}

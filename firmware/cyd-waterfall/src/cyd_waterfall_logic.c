/* Hardware-free waterfall logic for the CYD display build (GPLv3, as the
 * ESP-SDR project it extends). */
#include "cyd_waterfall_logic.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

const int cyd_steps_mhz[3] = {1, 5, 10};

/* Uncalibrated guess (typical CYD spans) until the user calibrates. */
const cyd_cal_t cyd_cal_default = {0, 200, 3700, 240, 3800};

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

uint8_t cyd_level(float db, float floor_db) {
    float v = (db-floor_db)/CYD_RANGE_DB;
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

int cyd_column_mhz(int lo_mhz, int column) {
    /* Column centres span LO-8 .. LO+8 MHz across CYD_COLUMNS. */
    float offset = ((float)column+0.5f)*16.0f/(float)CYD_COLUMNS - 8.0f;
    return lo_mhz + (int)lroundf(offset);
}

cyd_touch_t cyd_touch_target(int x, int y) {
    if (x < 0 || x >= CYD_COLUMNS || y < 0 || y >= CYD_SCREEN_HEIGHT) return CYD_TOUCH_NONE;
    /* Left half of the frequency line toggles inversion; the right half shows
     * the raw touch readout and is not a control. */
    if (y < 20) return x < CYD_COLUMNS/2 ? CYD_TOUCH_LABEL : CYD_TOUCH_NONE;
    if (y < CYD_STATUS_HEIGHT) return x < 80 ? CYD_TOUCH_DOWN : x < 160 ? CYD_TOUCH_STEP : CYD_TOUCH_UP;
    return CYD_TOUCH_WATERFALL;
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
    if (cal == &cyd_cal_default) {
        /* Default spans cover the whole panel, not the cross positions. */
        *x = clamp((u-cal->u0)*CYD_COLUMNS/(cal->u1-cal->u0), CYD_COLUMNS);
        *y = clamp((v-cal->v0)*CYD_SCREEN_HEIGHT/(cal->v2-cal->v0), CYD_SCREEN_HEIGHT);
        return;
    }
    int span_x = CYD_COLUMNS-2*CYD_CAL_MARGIN, span_y = CYD_SCREEN_HEIGHT-2*CYD_CAL_MARGIN;
    *x = clamp(CYD_CAL_MARGIN+(u-cal->u0)*span_x/(cal->u1-cal->u0), CYD_COLUMNS);
    *y = clamp(CYD_CAL_MARGIN+(v-cal->v0)*span_y/(cal->v2-cal->v0), CYD_SCREEN_HEIGHT);
}

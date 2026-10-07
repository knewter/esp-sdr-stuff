/* Beginner-friendly screens for the CYD waterfall build (GPLv3, as the
 * ESP-SDR project it extends).
 *
 * HOME offers four tiles and a guide. LIVE VIEW is the spectrum and
 * waterfall with -/+ and a MORE grid. WI-FI ranks channels 1-13 by how busy
 * they look and names the quietest of 1/6/11. BLUETOOTH cycles the three
 * advertising channels and counts bursts seen. SETTINGS and HOW TO USE
 * complete it. Every screen but HOME has a HOME button top right.
 */
#include "cyd_ui.h"
#include "cyd_gfx.h"
#include "cyd_waterfall_logic.h"
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "nvs.h"

#define CAPTURE_SAMPLES 4096
#define ROW_PERIOD_US 40000
#define STATS_PERIOD_US 300000
#define PANEL_PERIOD_US 700000
#define HOLD_TO_TUNE_US 600000
#define REPEAT_DELAY_US 500000
#define REPEAT_US 250000
#define CURSOR_TIMEOUT_US 15000000
#define SETTINGS_DELAY_US 3000000
#define BLE_DWELL_US 1500000
#define PEAK_DECAY_DB 1.0f
#define WIFI_THRESHOLD_DB 10.0f
#define WIFI_ALPHA 0.01f
#define WIFI_LO 2442
#define WIFI_SPAN_INDEX 2

/* Colours (RGB565). */
#define BLACK 0x0000
#define WHITE 0xffff
#define GREY 0x8410
#define LIGHT 0xbdf7
#define DARK 0x2124
#define PANEL 0x10a6
#define HOT 0x7bef
#define GREEN 0x07e0
#define DEEP_GREEN 0x0320
#define YELLOW 0xffe0
#define ORANGE 0xfd20
#define RED 0xf800
#define CYAN 0x07ff
#define MAGENTA 0xf81f

typedef enum { HOME, LIVE, WIFI, BLE, SETTINGS, HELP } screen_t;

static const cyd_radio_t *radio;
static screen_t screen = HOME;
static bool host_active, frozen, menu_open, flat, settings_dirty, press_acted, reset_armed;
static unsigned step_index, span_index, filter_index, range_index = 1, scroll, help_page;
static int preset = -1, cursor = -1, ble_index;
static unsigned live_lo = 2412;
static int64_t row_at, stats_at, panel_at, press_at, repeat_at, cursor_at, settings_at, ble_at;
static float floor_db, db[CYD_COLUMNS], peak[CYD_COLUMNS], colfloor[CYD_COLUMNS], floors[CYD_COLUMNS];
static bool first_row = true;
static cyd_burst_t bursts, ble_bursts;
static cyd_wifi_t wifi;
static cyd_ble_t ble;
static struct { unsigned rows, retunes; int64_t since, acquire_us, process_us, draw_us, retune_us; } stats;

static void enter(screen_t next);
static void save_settings_soon(void) { settings_dirty = true; settings_at = esp_timer_get_time(); }
static int span(void) { return cyd_span_mhz[span_index]; }

/* --- Radio ------------------------------------------------------------- */

static void apply_filter(void) {
    int mhz = filter_index ? cyd_filter_mhz[filter_index] : cyd_filter_for_span(span());
    radio->set_filter((unsigned)mhz);
}

static void reset_view(void) {
    first_row = true;
    bursts.count = 0;
    bursts.high = false;
    cursor = -1;
}

static bool tune(unsigned mhz) {
    int64_t t0 = esp_timer_get_time();
    if (!radio->tune(mhz)) return false;
    stats.retunes++;
    stats.retune_us += esp_timer_get_time() - t0;
    reset_view();
    return true;
}

/* One capture into db/floors; false if the radio failed. */
static bool capture(void) {
    const uint32_t *words;
    int64_t t0 = esp_timer_get_time();
    if (!radio->acquire(CAPTURE_SAMPLES, span_index, &words)) return false;
    int64_t t1 = esp_timer_get_time();
    cyd_row_db(words, CAPTURE_SAMPLES, db);
    cyd_mask_dc(db);
    floor_db = cyd_floor_update(floor_db, db, first_row);
    cyd_colfloor_update(colfloor, db, first_row);
    bool use_columns = flat || screen == WIFI;
    for (int c = 0; c < CYD_COLUMNS; c++) floors[c] = use_columns ? colfloor[c] : floor_db;
    cyd_peak_update(peak, db, PEAK_DECAY_DB, first_row);
    first_row = false;
    stats.rows++;
    stats.acquire_us += t1 - t0;
    stats.process_us += esp_timer_get_time() - t1;
    return true;
}

/* --- Shared pieces ------------------------------------------------------ */

static void button(int x, int y, int w, int h, const char *small, const char *big, uint16_t bg) {
    gfx_fill(x + 1, y + 1, w - 2, h - 2, bg);
    if (small && big) {
        gfx_text_centered(x + w / 2, y + h / 2 - 12, small, 1, LIGHT, bg);
        gfx_text_centered(x + w / 2, y + h / 2, big, 2, WHITE, bg);
    } else if (big) {
        gfx_text_centered(x + w / 2, y + h / 2 - 8, big, 2, WHITE, bg);
    } else if (small) {
        gfx_text_centered(x + w / 2, y + h / 2 - 4, small, 1, WHITE, bg);
    }
}

static bool inside(int x, int y, int x0, int y0, int w, int h) {
    return x >= x0 && x < x0 + w && y >= y0 && y < y0 + h;
}

/* Title bar with a HOME button, for every screen but HOME and LIVE. */
#define TITLE_H 34
static void title_bar(const char *title) {
    gfx_fill(0, 0, CYD_COLUMNS, TITLE_H, BLACK);
    gfx_text(6, 9, title, 2, WHITE, BLACK);
    button(170, 2, 68, TITLE_H - 4, "HOME", NULL, DARK);
    gfx_fill(0, TITLE_H - 1, CYD_COLUMNS, 1, 0x4208);
}
static bool home_hit(int x, int y) { return inside(x, y, 166, 0, 74, TITLE_H + 4); }

static void host_banner(void) {
    if (screen == LIVE) return;
    gfx_fill(0, 300, CYD_COLUMNS, 20, host_active ? ORANGE : BLACK);
    if (host_active) gfx_text_centered(CYD_COLUMNS / 2, 306, "PC IS USING THE RADIO", 1, BLACK, ORANGE);
}

/* --- HOME --------------------------------------------------------------- */

static const struct { const char *title, *line1, *line2; uint16_t colour; screen_t target; } tiles[4] = {
    {"LIVE", "SEE SIGNALS AS", "A WATERFALL", 0x0193, LIVE},
    {"WI-FI", "FIND THE", "QUIETEST CHANNEL", 0x0260, WIFI},
    {"BLUETOOTH", "NEARBY DEVICES", "ADVERTISING", 0x3010, BLE},
    {"SETTINGS", "GAIN, FILTER,", "TOUCH, RESET", 0x31a6, SETTINGS},
};
#define TILE_W 116
#define TILE_H 100
static void tile_box(int k, int *x, int *y) { *x = 3 + (k % 2) * (TILE_W + 2); *y = 46 + (k / 2) * (TILE_H + 4); }

static void draw_home(void) {
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, BLACK);
    gfx_text(6, 6, "ESP32 SDR", 2, WHITE, BLACK);
    gfx_text(6, 26, "A RADIO EXPLORER FOR 2.4 GHZ", 1, LIGHT, BLACK);
    for (int k = 0; k < 4; k++) {
        int x, y;
        tile_box(k, &x, &y);
        gfx_fill(x, y, TILE_W, TILE_H, tiles[k].colour);
        gfx_text_centered(x + TILE_W / 2, y + 24, tiles[k].title, 2, WHITE, tiles[k].colour);
        gfx_text_centered(x + TILE_W / 2, y + 60, tiles[k].line1, 1, LIGHT, tiles[k].colour);
        gfx_text_centered(x + TILE_W / 2, y + 74, tiles[k].line2, 1, LIGHT, tiles[k].colour);
    }
    button(3, 254, 234, 42, NULL, "HOW TO USE", DARK);
    host_banner();
}

static void touch_home(int x, int y) {
    for (int k = 0; k < 4; k++) {
        int x0, y0;
        tile_box(k, &x0, &y0);
        if (inside(x, y, x0, y0, TILE_W, TILE_H)) { enter(tiles[k].target); return; }
    }
    if (inside(x, y, 3, 254, 234, 42)) enter(HELP);
}

/* --- LIVE VIEW ------------------------------------------------------------ */

static int marker_column(void) {
    if (preset < 0 || cyd_presets[preset].marker_khz == CYD_MARKER_NONE) return -1;
    if ((int)radio->frequency() != cyd_presets[preset].lo_mhz) return -1;
    return cyd_offset_column(cyd_presets[preset].marker_khz, span());
}

static void live_status(void) {
    char s[32];
    gfx_fill(0, CYD_STATUS_Y, CYD_COLUMNS, CYD_STATUS_H, BLACK);
    snprintf(s, sizeof(s), "%u", radio->frequency());
    gfx_text(4, 2, s, 2, WHITE, BLACK);
    gfx_text(4 + 12 * (int)strlen(s) + 4, 9, "MHZ", 1, GREY, BLACK);
    const char *badge = NULL;
    uint16_t colour = GREEN;
    if (host_active) { badge = "PC"; colour = ORANGE; }
    else if (frozen) { badge = "PAUSED"; colour = CYAN; }
    else if (preset >= 0 && (int)radio->frequency() == cyd_presets[preset].lo_mhz) badge = cyd_presets[preset].label;
    if (badge) gfx_text(150, 2, badge, 1, colour, BLACK);
    unsigned f = radio->frequency();
    if (f < 2400 || f > 2500) gfx_text(216, 2, "EXT", 1, RED, BLACK);
    if (radio->hardware_agc()) snprintf(s, sizeof(s), "AUTO %dM", span());
    else snprintf(s, sizeof(s), "G%u %dM", radio->gain_code(), span());
    gfx_text(150, 12, s, 1, LIGHT, BLACK);
}

static long column_khz(int c) {
    return (long)(c * 2 + 1) * span() * 1000 / (2 * CYD_COLUMNS) - (long)span() * 500;
}

static void live_readout(void) {
    char s[44];
    bool inspecting = cursor >= 0;
    int c = inspecting ? cursor : cyd_peak_column(db);
    long f10 = (long)radio->frequency() * 10 + column_khz(c) / 100;
    int n = snprintf(s, sizeof(s), "%s %ld.%ld %+dDB", inspecting ? "HERE" : "STRONGEST", f10 / 10, f10 % 10,
                     (int)(db[c] - floors[c]));
    if (inspecting) snprintf(s + n, sizeof(s) - n, " HOLD=TUNE");
    else if (marker_column() >= 0) snprintf(s + n, sizeof(s) - n, " HITS %u", bursts.count);
    gfx_fill(0, 22, CYD_COLUMNS, 9, BLACK);
    gfx_text(4, 23, s, 1, inspecting ? CYAN : YELLOW, BLACK);
}

static void live_scale(void) {
    char s[8];
    gfx_fill(0, CYD_SCALE_Y, CYD_COLUMNS, CYD_SCALE_H, BLACK);
    static const int ticks[5] = {30, 75, 120, 165, 210};
    for (int k = 0; k < 5; k++) {
        int c = ticks[k];
        gfx_fill(c, CYD_SCALE_Y, 1, k == 2 ? 4 : 2, WHITE);
        snprintf(s, sizeof(s), "%d", cyd_column_mhz((int)radio->frequency(), c, span()));
        gfx_text_centered(c, CYD_SCALE_Y + 4, s, 1, k == 2 ? WHITE : GREY, BLACK);
    }
    int m = marker_column();
    if (m >= 0) {
        /* Where this board's channel is expected: a zone, because the tuning
         * error moves by about a megahertz between retunes. */
        uint16_t colour = cyd_presets[preset].measured ? MAGENTA : 0x8010;
        int z0 = m - CYD_BURST_ZONE < 0 ? 0 : m - CYD_BURST_ZONE;
        int z1 = m + CYD_BURST_ZONE >= CYD_COLUMNS ? CYD_COLUMNS - 1 : m + CYD_BURST_ZONE;
        gfx_fill(z0, CYD_SCALE_Y + CYD_SCALE_H - 2, z1 - z0 + 1, 2, colour);
        if (!cyd_presets[preset].measured) gfx_text(m - 3, CYD_SCALE_Y, "?", 1, colour, BLACK);
    }
}

/* The spectrum strip in batches of CYD_LINE_ROWS rows per SPI transfer. */
static void live_spectrum(void) {
    uint16_t out[CYD_COLUMNS];
    float range = (float)cyd_range_db[range_index];
    gfx_window(0, CYD_SPECTRUM_Y, CYD_COLUMNS - 1, CYD_SPECTRUM_Y + CYD_SPECTRUM_H - 1);
    for (int r0 = 0; r0 < CYD_SPECTRUM_H; r0 += CYD_LINE_ROWS) {
        int rows = CYD_SPECTRUM_H - r0 < CYD_LINE_ROWS ? CYD_SPECTRUM_H - r0 : CYD_LINE_ROWS;
        for (int r = 0; r < rows; r++) {
            cyd_spectrum_line(db, peak, floors, range, r0 + r, -1, cursor, out);
            for (int c = 0; c < CYD_COLUMNS; c++) gfx_line[r * CYD_COLUMNS + c] = gfx_swap(out[c]);
        }
        gfx_push(gfx_line, (size_t)rows * CYD_COLUMNS, r0 == 0);
    }
}

static void live_controls(int pressed) {
    const int w = CYD_COLUMNS / 4, y = CYD_CONTROLS_Y, h = CYD_CONTROLS_H;
    gfx_fill(0, y, CYD_COLUMNS, 1, 0x4208);
    char step[12];
    snprintf(step, sizeof(step), "%d MHZ", cyd_steps_mhz[step_index]);
    button(0, y, w, h, NULL, "HOME", pressed == 0 ? HOT : DARK);
    button(w, y, w, h, step, "-", pressed == 1 ? HOT : DARK);
    button(2 * w, y, w, h, step, "+", pressed == 2 ? HOT : DARK);
    button(3 * w, y, w, h, NULL, menu_open ? "DONE" : "MORE", pressed == 3 ? HOT : menu_open ? DEEP_GREEN : DARK);
}

static const char *more_label(int item, char *buf, size_t size) {
    switch (item) {
    case 0: case 1: case 2: case 3: case 4: case 5: case 6: return cyd_presets[item].label;
    case 7: snprintf(buf, size, "WIDTH %d", span()); return buf;
    case 8: snprintf(buf, size, "STEP %d", cyd_steps_mhz[step_index]); return buf;
    case 9: return radio->hardware_agc() ? "GAIN AUTO" : "GAIN MANUAL";
    case 10: return "GAIN -";
    case 11: return "GAIN +";
    case 12: snprintf(buf, size, "COLOUR %d", cyd_range_db[range_index]); return buf;
    case 13: return flat ? "FLAT ON" : "FLAT OFF";
    default: return frozen ? "RESUME" : "PAUSE";
    }
}

static void live_more(int pressed) {
    char buf[16];
    const int w = CYD_COLUMNS / CYD_MENU_COLS;
    gfx_fill(0, CYD_WATERFALL_Y, CYD_COLUMNS, CYD_WATERFALL_H, BLACK);
    for (int i = 0; i < CYD_MENU_ROWS * CYD_MENU_COLS; i++) {
        int r = i / CYD_MENU_COLS, c = i % CYD_MENU_COLS;
        int y0 = CYD_WATERFALL_Y + r * CYD_WATERFALL_H / CYD_MENU_ROWS;
        int y1 = CYD_WATERFALL_Y + (r + 1) * CYD_WATERFALL_H / CYD_MENU_ROWS;
        uint16_t bg = i == pressed ? HOT : i < CYD_PRESETS && i == preset ? DEEP_GREEN : i < CYD_PRESETS ? PANEL : DARK;
        button(c * w, y0, w, y1 - y0, more_label(i, buf, sizeof(buf)), NULL, bg);
    }
}

static void scroll_reset(void) {
    scroll = 0;
    gfx_scroll_start(CYD_WATERFALL_Y);
}

static void draw_live(void) {
    scroll_reset();
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, BLACK);
    live_status();
    live_scale();
    if (menu_open) live_more(-1);
    live_controls(-1);
}

static void live_retune(int mhz) {
    if (mhz <= 0 || !tune((unsigned)mhz)) return;
    live_lo = radio->frequency();
    if (preset >= 0 && (int)live_lo != cyd_presets[preset].lo_mhz) preset = -1;
    live_status();
    live_scale();
    save_settings_soon();
}

static void open_more(bool open) {
    menu_open = open;
    scroll_reset();
    if (open) live_more(-1);
    else gfx_fill(0, CYD_WATERFALL_Y, CYD_COLUMNS, CYD_WATERFALL_H, BLACK);
    live_controls(-1);
}

static void more_action(int item) {
    if (item < 0) return;
    live_more(item);
    vTaskDelay(pdMS_TO_TICKS(60));
    if (item < CYD_PRESETS) {
        preset = item;
        /* BLE markers come from 16 MS/s sessions; Wi-Fi fits 40 MHz; the whole
         * band needs 80 MHz. The filter follows the width. */
        span_index = item < 3 ? 0 : item < 6 ? 1 : 2;
        apply_filter();
        live_retune(cyd_presets[item].lo_mhz);
        open_more(false);
        return;
    }
    switch (item) {
    case 7: span_index = (span_index + 1) % CYD_SPANS; apply_filter(); reset_view(); break;
    case 8: step_index = (step_index + 1) % 3; live_controls(-1); break;
    case 9: radio->set_gain(!radio->hardware_agc(), radio->gain_code()); reset_view(); break;
    case 10: case 11: {
        int g = (int)radio->gain_code() + (item == 10 ? -4 : 4);
        g = g < 0 ? 0 : g > (int)radio->gain_max() ? (int)radio->gain_max() : g;
        radio->set_gain(false, (unsigned)g);
        reset_view();
        break;
    }
    case 12: range_index = (range_index + 1) % CYD_RANGES; break;
    case 13: flat = !flat; reset_view(); break;
    default: frozen = !frozen; break;
    }
    save_settings_soon();
    live_more(-1);
    live_status();
    live_scale();
}

static void live_waterfall_row(void) {
    float range = (float)cyd_range_db[range_index];
    for (int c = 0; c < CYD_COLUMNS; c++) {
        uint16_t v = cyd_palette(cyd_level(db[c], floors[c], range));
        gfx_line[c] = gfx_swap(v);
    }
    /* Newest row on top: move the scroll start up one line, then draw it. */
    scroll = (scroll + CYD_WATERFALL_H - 1) % CYD_WATERFALL_H;
    int y = CYD_WATERFALL_Y + (int)scroll;
    gfx_window(0, y, CYD_COLUMNS - 1, y);
    gfx_push(gfx_line, CYD_COLUMNS, true);
    gfx_scroll_start(y);
}

static void tick_live(int64_t now) {
    if (now - stats_at >= STATS_PERIOD_US && !first_row) { stats_at = now; live_readout(); }
    if (frozen || now - row_at < ROW_PERIOD_US) return;
    row_at = now;
    if (!capture()) return;
    cyd_burst_update(&bursts, db, colfloor, marker_column(), CYD_BURST_ZONE);
    int64_t t0 = esp_timer_get_time();
    live_spectrum();
    if (!menu_open) live_waterfall_row();
    stats.draw_us += esp_timer_get_time() - t0;
}

/* Buttons act on press (-/+ repeat while held). On the graph or waterfall a
 * tap places a cursor that reads out frequency and level; holding tunes. */
static void touch_live(int x, int y, bool fresh, int64_t now) {
    if (menu_open && y >= CYD_WATERFALL_Y && y < CYD_CONTROLS_Y) {
        if (fresh) { press_acted = true; more_action(cyd_hit_menu(x, y)); }
        return;
    }
    if (y >= CYD_CONTROLS_Y) {
        int k = x * 4 / CYD_COLUMNS;
        bool repeat = k == 1 || k == 2;
        if (!fresh && (!repeat || press_acted || now - press_at < REPEAT_DELAY_US || now - repeat_at < REPEAT_US)) return;
        press_acted = !repeat;
        repeat_at = now;
        live_controls(k);
        vTaskDelay(pdMS_TO_TICKS(50));
        int step = cyd_steps_mhz[step_index];
        if (k == 0) { enter(HOME); return; }
        if (k == 1) live_retune((int)radio->frequency() - step);
        else if (k == 2) live_retune((int)radio->frequency() + step);
        else { open_more(!menu_open); return; }
        live_controls(-1);
        return;
    }
    if (y < CYD_SPECTRUM_Y || menu_open || press_acted) return;
    if (fresh || x != cursor) { cursor = x; cursor_at = now; live_readout(); }
    if (now - press_at >= HOLD_TO_TUNE_US) {
        press_acted = true;
        live_retune(cyd_column_mhz((int)radio->frequency(), cursor, span()));
    }
}

/* --- WI-FI -------------------------------------------------------------- */

#define BARS_Y 64
#define BARS_H 150
static uint16_t busy_colour(float b) { return b < 0.05f ? GREEN : b < 0.2f ? 0x9fe0 : b < 0.5f ? YELLOW : RED; }

static void wifi_panel(void) {
    char s[32];
    gfx_fill(0, BARS_Y - 14, CYD_COLUMNS, BARS_H + 14, BLACK);
    for (int n = 0; n < CYD_WIFI_CHANNELS; n++) {
        int x = 3 + n * 18;
        float b = wifi.busy[n];
        bool main_channel = n == 0 || n == 5 || n == 10;
        gfx_fill(x, BARS_Y, 16, BARS_H, 0x18c3);
        if (b >= 0) {
            int h = (int)(b * (BARS_H - 2)) + 2;
            if (h > BARS_H) h = BARS_H;
            gfx_fill(x, BARS_Y + BARS_H - h, 16, h, busy_colour(b));
        }
        if (main_channel) gfx_fill(x, BARS_Y - 6, 16, 3, WHITE);
    }
    gfx_fill(0, 216, CYD_COLUMNS, 10, BLACK);
    for (int n = 0; n < CYD_WIFI_CHANNELS; n++) {
        snprintf(s, sizeof(s), "%d", n + 1);
        bool main_channel = n == 0 || n == 5 || n == 10;
        gfx_text_centered(3 + n * 18 + 8, 218, s, 1, main_channel ? WHITE : GREY, BLACK);
    }
    int best = cyd_wifi_best(&wifi);
    gfx_fill(0, 232, CYD_COLUMNS, 40, BLACK);
    if (best) {
        snprintf(s, sizeof(s), "BEST: CHANNEL %d", best);
        gfx_text_centered(CYD_COLUMNS / 2, 234, s, 2, WHITE, BLACK);
        const char *word = cyd_activity_word(wifi.busy[best - 1]);
        gfx_text_centered(CYD_COLUMNS / 2, 254, word, 2, busy_colour(wifi.busy[best - 1]), BLACK);
    } else {
        gfx_text_centered(CYD_COLUMNS / 2, 240, "LISTENING...", 2, GREY, BLACK);
    }
}

static void draw_wifi(void) {
    scroll_reset();
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, BLACK);
    title_bar("WI-FI");
    gfx_text(4, 38, "TALLER BAR = BUSIER CHANNEL", 1, LIGHT, BLACK);
    gfx_text(4, 278, "PICK 1, 6 OR 11 FOR YOUR ROUTER", 1, LIGHT, BLACK);
    gfx_text(4, 290, "CHANNEL EDGES ARE APPROXIMATE", 1, GREY, BLACK);
    wifi_panel();
    host_banner();
}

static void tick_wifi(int64_t now) {
    if (now - row_at >= ROW_PERIOD_US / 2) {
        row_at = now;
        if (capture()) cyd_wifi_update(&wifi, db, floors, (int)radio->frequency(), span(), WIFI_THRESHOLD_DB, WIFI_ALPHA);
    }
    if (now - panel_at >= PANEL_PERIOD_US) {
        int64_t t0 = esp_timer_get_time();
        panel_at = now;
        wifi_panel();
        stats.draw_us += esp_timer_get_time() - t0;
    }
}

/* --- BLUETOOTH ------------------------------------------------------------ */

#define BLE_Y 40
#define BLE_H 62
static void ble_panel(void) {
    char s[32];
    for (int k = 0; k < 3; k++) {
        int y = BLE_Y + k * (BLE_H + 4);
        bool listening = k == ble_index;
        float rate = cyd_ble_per_minute(&ble, k);
        uint16_t bg = listening ? 0x0109 : PANEL;
        gfx_fill(2, y, CYD_COLUMNS - 4, BLE_H, bg);
        snprintf(s, sizeof(s), "%d", 37 + k);
        gfx_text(10, y + 18, s, 3, WHITE, bg);
        gfx_text(60, y + 8, k == 0 ? "2402 MHZ" : k == 1 ? "2426 MHZ" : "2480 MHZ", 1, LIGHT, bg);
        const char *word = cyd_ble_word(rate);
        gfx_text(60, y + 22, word, 2, rate < 0 ? GREY : rate < 5 ? GREEN : rate < 30 ? 0x9fe0 : rate < 120 ? YELLOW : RED, bg);
        if (rate >= 0) snprintf(s, sizeof(s), "%.0f HITS/MIN", rate);
        else snprintf(s, sizeof(s), "LISTENING...");
        gfx_text(60, y + 44, s, 1, LIGHT, bg);
        if (listening) gfx_text(178, y + 8, "LISTEN", 1, CYAN, bg);
        if (k == 2) gfx_text(178, y + 44, "APPROX", 1, GREY, bg);
    }
}

static void ble_tune(void) {
    const cyd_preset_t *p = &cyd_presets[ble_index];
    preset = ble_index;
    tune((unsigned)p->lo_mhz);
    ble_bursts.high = false;
}

static void draw_ble(void) {
    scroll_reset();
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, BLACK);
    title_bar("BLUETOOTH");
    gfx_text(4, 246, "PHONES, WATCHES AND TAGS ANNOUNCE", 1, LIGHT, BLACK);
    gfx_text(4, 258, "THEMSELVES ON CHANNELS 37-39.", 1, LIGHT, BLACK);
    gfx_text(4, 274, "HITS = BURSTS SEEN IN SHORT", 1, GREY, BLACK);
    gfx_text(4, 286, "SNAPSHOTS, NOT EVERY PACKET.", 1, GREY, BLACK);
    ble_panel();
    host_banner();
}

static void tick_ble(int64_t now) {
    if (now - ble_at >= BLE_DWELL_US) {
        ble_at = now;
        ble_index = (ble_index + 1) % 3;
        ble_tune();
    }
    if (now - row_at >= ROW_PERIOD_US / 2) {
        int64_t last = row_at;
        row_at = now;
        if (capture()) {
            /* ch37/38 search +-2 MHz around this board's measured carrier;
             * ch39 is unlocated, so the whole view counts. */
            bool known = cyd_presets[ble_index].measured;
            int m = known ? marker_column() : CYD_COLUMNS / 2;
            if (m >= 0 && cyd_burst_update(&ble_bursts, db, colfloor, m, known ? CYD_BURST_ZONE : CYD_COLUMNS / 2))
                ble.bursts[ble_index]++;
            if (last) ble.seconds[ble_index] += (float)(now - last) * 1e-6f;
        }
    }
    if (now - panel_at >= PANEL_PERIOD_US) {
        int64_t t0 = esp_timer_get_time();
        panel_at = now;
        ble_panel();
        stats.draw_us += esp_timer_get_time() - t0;
    }
}

/* --- SETTINGS --------------------------------------------------------------- */

#define SET_Y 42
#define SET_H 50
static const char *setting_label(int k, char *buf, size_t size) {
    switch (k) {
    case 0:
        if (filter_index) snprintf(buf, size, "FILTER %d", cyd_filter_mhz[filter_index]);
        else snprintf(buf, size, "FILTER AUTO");
        return buf;
    case 1: snprintf(buf, size, "COLOUR %d DB", cyd_range_db[range_index]); return buf;
    case 2: return radio->hardware_agc() ? "GAIN AUTO" : "GAIN MANUAL";
    case 3: snprintf(buf, size, "GAIN %u", radio->gain_code()); return buf;
    case 4: return "GAIN -";
    case 5: return "GAIN +";
    case 6: return flat ? "FLAT ON" : "FLAT OFF";
    case 7: return "TOUCH SETUP";
    case 8: return reset_armed ? "TAP AGAIN" : "RESET ALL";
    default: return "HOW TO USE";
    }
}

static void settings_panel(int pressed) {
    char buf[20];
    for (int k = 0; k < 10; k++) {
        int x = 3 + (k % 2) * 118, y = SET_Y + (k / 2) * SET_H;
        uint16_t bg = k == pressed ? HOT : k == 8 && reset_armed ? RED : k == 3 ? BLACK : DARK;
        button(x, y, 116, SET_H - 2, setting_label(k, buf, sizeof(buf)), NULL, bg);
    }
}

static void draw_settings(void) {
    scroll_reset();
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, BLACK);
    title_bar("SETTINGS");
    settings_panel(-1);
    host_banner();
}

static void touch_settings(int x, int y) {
    if (y < SET_Y || y >= SET_Y + 5 * SET_H) return;
    int k = (y - SET_Y) / SET_H * 2 + (x >= 120);
    if (k != 8) reset_armed = false;
    settings_panel(k);
    vTaskDelay(pdMS_TO_TICKS(60));
    switch (k) {
    case 0: filter_index = (filter_index + 1) % CYD_FILTERS; apply_filter(); break;
    case 1: range_index = (range_index + 1) % CYD_RANGES; break;
    case 2: radio->set_gain(!radio->hardware_agc(), radio->gain_code()); break;
    case 4: case 5: {
        int g = (int)radio->gain_code() + (k == 4 ? -4 : 4);
        g = g < 0 ? 0 : g > (int)radio->gain_max() ? (int)radio->gain_max() : g;
        radio->set_gain(false, (unsigned)g);
        break;
    }
    case 6: flat = !flat; break;
    case 7: cyd_display_calibrate(); return;
    case 8:
        if (!reset_armed) { reset_armed = true; break; }
        reset_armed = false;
        span_index = filter_index = step_index = 0;
        range_index = 1;
        flat = frozen = false;
        preset = -1;
        live_lo = 2412;
        radio->set_gain(true, 40);
        apply_filter();
        break;
    case 9: enter(HELP); return;
    default: break;
    }
    save_settings_soon();
    settings_panel(-1);
}

/* --- HOW TO USE ------------------------------------------------------------ */

static const char *const help[][8] = {
    {"WHAT IS THIS?", "THIS BOARD IS A SMALL RADIO", "RECEIVER FOR THE 2.4 GHZ BAND.", "WI-FI, BLUETOOTH, MICROWAVE",
     "OVENS AND MANY GADGETS USE IT.", "", "IT SHOWS WHERE RADIO ENERGY IS", "AND HOW BUSY EACH PART IS."},
    {"READING THE SCREEN", "TOP GRAPH: SIGNAL STRENGTH NOW.", "WATERFALL: HISTORY, NEWEST ON", "TOP. BLUE IS WEAK, YELLOW AND",
     "RED ARE STRONG, WHITE IS VERY", "STRONG. SHORT DASHES ARE BURSTS", "LIKE BLUETOOTH; WIDE BLOCKS ARE", "WI-FI."},
    {"USING TOUCH", "PRESS FIRMLY WITH A FINGERNAIL.", "TAP THE GRAPH OR WATERFALL TO", "MEASURE THAT SPOT.",
     "HOLD FOR A SECOND TO TUNE THERE.", "- AND + MOVE THE FREQUENCY.", "MORE HAS PRESETS AND OPTIONS.", ""},
    {"GOOD TO KNOW", "IT TAKES SHORT SNAPSHOTS, SO IT", "SEES SOME BURSTS, NOT ALL.", "FREQUENCIES ARE APPROXIMATE ON",
     "THIS BOARD. ORANGE PC MEANS A", "COMPUTER IS USING THE RADIO.", "HOLD A FINGER ON THE SCREEN AT", "POWER-UP TO REDO TOUCH SETUP."},
};
#define HELP_PAGES (sizeof(help) / sizeof(help[0]))

static void draw_help(void) {
    char s[16];
    scroll_reset();
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, BLACK);
    title_bar("HOW TO USE");
    gfx_text(6, 48, help[help_page][0], 2, YELLOW, BLACK);
    for (int k = 1; k < 8; k++) gfx_text(6, 80 + (k - 1) * 18, help[help_page][k], 1, WHITE, BLACK);
    snprintf(s, sizeof(s), "%u / %u", help_page + 1, (unsigned)HELP_PAGES);
    gfx_text_centered(CYD_COLUMNS / 2, 222, s, 1, GREY, BLACK);
    button(3, 240, 116, 52, NULL, "BACK", help_page ? DARK : BLACK);
    button(121, 240, 116, 52, NULL, help_page + 1 < HELP_PAGES ? "NEXT" : "DONE", DEEP_GREEN);
    host_banner();
}

static void touch_help(int x, int y) {
    if (!inside(x, y, 0, 240, CYD_COLUMNS, 54)) return;
    if (x < 120) { if (help_page) { help_page--; draw_help(); } return; }
    if (help_page + 1 < HELP_PAGES) { help_page++; draw_help(); } else enter(HOME);
}

/* --- Screens, settings, entry points ------------------------------------------ */

static void enter(screen_t next) {
    if (screen == BLE || screen == WIFI) {
        /* Leave the live view where the user left it. */
        preset = -1;
    }
    screen = next;
    menu_open = false;
    cursor = -1;
    reset_armed = false;
    if (next == LIVE) {
        span_index = span_index < CYD_SPANS ? span_index : 0;
        apply_filter();
        tune(live_lo);
    } else if (next == WIFI) {
        cyd_wifi_reset(&wifi);
        span_index = WIFI_SPAN_INDEX;
        apply_filter();
        tune(WIFI_LO);
    } else if (next == BLE) {
        memset(&ble, 0, sizeof(ble));
        span_index = 0;
        apply_filter();
        ble_index = 0;
        ble_at = esp_timer_get_time();
        ble_tune();
    } else if (next == HELP) {
        help_page = 0;
    }
    row_at = 0;
    cyd_ui_redraw();
}

void cyd_ui_redraw(void) {
    switch (screen) {
    case HOME: draw_home(); break;
    case LIVE: draw_live(); break;
    case WIFI: draw_wifi(); break;
    case BLE: draw_ble(); break;
    case SETTINGS: draw_settings(); break;
    default: draw_help(); break;
    }
}

static unsigned live_span_saved;
static void save_settings(void) {
    unsigned s = screen == LIVE ? span_index : live_span_saved;
    cyd_settings_t v = {CYD_SETTINGS_VERSION, (uint8_t)s, (uint8_t)filter_index, (uint8_t)range_index,
                        (uint8_t)step_index, radio->hardware_agc(), (uint8_t)radio->gain_code(), flat,
                        (int8_t)(screen == LIVE ? preset : -1), (uint16_t)live_lo};
    nvs_handle_t h;
    if (nvs_open("cyd", NVS_READWRITE, &h) != ESP_OK) return;
    nvs_set_blob(h, "ui", &v, sizeof(v));
    nvs_commit(h);
    nvs_close(h);
    settings_dirty = false;
}

static void load_settings(void) {
    cyd_settings_t v;
    size_t length = sizeof(v);
    nvs_handle_t h;
    if (nvs_open("cyd", NVS_READONLY, &h) != ESP_OK) return;
    bool ok = nvs_get_blob(h, "ui", &v, &length) == ESP_OK && length == sizeof(v) && cyd_settings_valid(&v);
    nvs_close(h);
    if (!ok) return;
    span_index = live_span_saved = v.span;
    filter_index = v.filter;
    range_index = v.range;
    step_index = v.step;
    flat = v.flat;
    preset = v.preset;
    live_lo = v.lo_mhz;
    radio->set_gain(v.agc, v.gain);
}

void cyd_ui_init(const cyd_radio_t *ops) {
    radio = ops;
    load_settings();
    stats.since = esp_timer_get_time();
    screen = HOME;
    cyd_ui_redraw();
}

void cyd_ui_press(int x, int y, bool fresh, int64_t now) {
    if (fresh) { press_at = now; press_acted = false; }
    if (screen != HOME && screen != LIVE && fresh && home_hit(x, y)) { enter(HOME); press_acted = true; return; }
    if (!fresh && screen != LIVE) return;
    switch (screen) {
    case HOME: press_acted = true; touch_home(x, y); break;
    case LIVE: touch_live(x, y, fresh, now); break;
    case SETTINGS: touch_settings(x, y); break;
    case HELP: touch_help(x, y); break;
    default: break;
    }
}

void cyd_ui_release(void) {}

void cyd_ui_tick(int64_t now) {
    if (screen == LIVE) live_span_saved = span_index;
    if (settings_dirty && now - settings_at >= SETTINGS_DELAY_US) save_settings();
    if (cursor >= 0 && now - cursor_at >= CURSOR_TIMEOUT_US) cursor = -1;
    switch (screen) {
    case LIVE: tick_live(now); break;
    case WIFI: tick_wifi(now); break;
    case BLE: tick_ble(now); break;
    default: break;
    }
}

void cyd_ui_host(bool active) {
    host_active = active;
    if (screen == LIVE) live_status();
    else host_banner();
    if (!active) {
        /* The host may have retuned or changed gain and filter. */
        if (screen == LIVE) {
            if (radio->frequency() != live_lo) { live_lo = radio->frequency(); preset = -1; }
            reset_view();
            live_status();
            live_scale();
        } else if (screen == WIFI || screen == BLE) {
            enter(screen);
        }
    }
}

int cyd_ui_scroll(void) { return (int)scroll; }

void cyd_ui_reset_stats(void) {
    memset(&stats, 0, sizeof(stats));
    stats.since = esp_timer_get_time();
}

void cyd_ui_report(char *out, size_t size) {
    static const char *names[] = {"home", "live", "wifi", "bluetooth", "settings", "help"};
    int64_t elapsed = esp_timer_get_time() - stats.since;
    unsigned rows = stats.rows ? stats.rows : 1, retunes = stats.retunes ? stats.retunes : 1;
    int c = cyd_peak_column(db);
    snprintf(out, size, "{\"screen\":\"%s\",\"freq\":%u,\"span\":%d,\"filter_index\":%u,\"agc\":%d,\"gain\":%u,"
             "\"rows\":%u,\"rows_per_s\":%.2f,\"acquire_us\":%lld,\"process_us\":%lld,\"draw_us\":%lld,"
             "\"retune_us\":%lld,\"floor_db\":%.1f,\"peak_col\":%d,\"peak_above_floor_db\":%.1f,"
             "\"live_hits\":%u,\"wifi_best\":%d,\"wifi_busy\":[%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f],"
             "\"ble_hits\":[%u,%u,%u],\"ble_s\":[%.1f,%.1f,%.1f],\"free_heap\":%u}",
             names[screen], radio->frequency(), span(), filter_index, radio->hardware_agc(), radio->gain_code(),
             stats.rows, elapsed > 0 ? stats.rows * 1e6 / (double)elapsed : 0.0,
             (long long)(stats.acquire_us / rows), (long long)(stats.process_us / rows),
             (long long)(stats.draw_us / rows), (long long)(stats.retune_us / retunes), floor_db, c,
             db[c] - floor_db, bursts.count, cyd_wifi_best(&wifi), wifi.busy[0], wifi.busy[1], wifi.busy[2],
             wifi.busy[3], wifi.busy[4], wifi.busy[5], wifi.busy[6], wifi.busy[7], wifi.busy[8], wifi.busy[9],
             wifi.busy[10], wifi.busy[11], wifi.busy[12], ble.bursts[0], ble.bursts[1], ble.bursts[2],
             ble.seconds[0], ble.seconds[1], ble.seconds[2], (unsigned)heap_caps_get_free_size(0));
}

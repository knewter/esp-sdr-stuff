/* CYD on-screen waterfall for the ESP-SDR ESP32 receiver (GPLv3, as the
 * ESP-SDR project it extends).
 *
 * Panel: ILI9341 or ST7789 (CYD2USB), 240x320 portrait, HSPI. Layout, top to
 * bottom: status, frequency scale, live spectrum, waterfall, controls. The
 * waterfall scrolls with the panel's own vertical-scroll registers, so no
 * framebuffer is kept. MENU swaps the waterfall for a grid of presets and
 * receiver settings (span 16/40/80 MHz, RF filter, gain, colour range).
 * Touch: XPT2046 on its own pins, bit-banged. Everything runs inside the
 * receiver loop between host commands; the radio is never used concurrently.
 */
#include "cyd_display.h"
#include "cyd_waterfall_logic.h"
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_heap_caps.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "nvs.h"

#define PIN_SCLK 14
#define PIN_MOSI 13
#define PIN_MISO 12
#define PIN_CS 15
#define PIN_DC 2
#define PIN_BACKLIGHT 21
#define PIN_T_CLK 25
#define PIN_T_MOSI 32
#define PIN_T_MISO 39
#define PIN_T_CS 33
#define PIN_T_IRQ 36

#define HOST_IDLE_US 5000000
#define ROW_PERIOD_US 40000
#define TOUCH_REPEAT_US 300000
#define CAPTURE_SAMPLES 4096
#define BURST_THRESHOLD_DB 12.0f
#define PEAK_DECAY_DB 0.4f
#define STATS_PERIOD_US 300000

static const cyd_radio_t *radio;
static esp_lcd_panel_io_handle_t io;
static SemaphoreHandle_t flushed;
static uint16_t *line;
static int64_t host_at, row_at, touch_at, stats_at;
static bool active, inverted, st7789, first_row = true, host_shown, frozen, menu_open, touch_down;
static unsigned step_index, span_index, filter_index, range_index = 1, scroll;
static int preset = -1;
static float floor_db, db[CYD_COLUMNS], peak[CYD_COLUMNS];
static cyd_burst_t bursts;
static void finish_screen(void);
static void scroll_identity(void);
static cyd_cal_t cal;
static const cyd_cal_t *calibration = &cyd_cal_default;

static const uint8_t font[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, {0x08,0x08,0x3e,0x08,0x08}, {0x08,0x08,0x08,0x08,0x08},
    {0x00,0x60,0x60,0x00,0x00}, {0x3e,0x51,0x49,0x45,0x3e}, {0x00,0x42,0x7f,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46}, {0x21,0x41,0x45,0x4b,0x31}, {0x18,0x14,0x12,0x7f,0x10},
    {0x27,0x45,0x45,0x45,0x39}, {0x3c,0x4a,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1e}, {0x00,0x36,0x36,0x00,0x00},
    {0x7e,0x11,0x11,0x11,0x7e}, {0x7f,0x49,0x49,0x49,0x36}, {0x3e,0x41,0x41,0x41,0x22},
    {0x7f,0x41,0x41,0x22,0x1c}, {0x7f,0x49,0x49,0x49,0x41}, {0x7f,0x09,0x09,0x09,0x01},
    {0x3e,0x41,0x49,0x49,0x7a}, {0x7f,0x08,0x08,0x08,0x7f}, {0x00,0x41,0x7f,0x41,0x00},
    {0x20,0x40,0x41,0x3f,0x01}, {0x7f,0x08,0x14,0x22,0x41}, {0x7f,0x40,0x40,0x40,0x40},
    {0x7f,0x02,0x0c,0x02,0x7f}, {0x7f,0x04,0x08,0x10,0x7f}, {0x3e,0x41,0x41,0x41,0x3e},
    {0x7f,0x09,0x09,0x09,0x06}, {0x3e,0x41,0x51,0x21,0x5e}, {0x7f,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31}, {0x01,0x01,0x7f,0x01,0x01}, {0x3f,0x40,0x40,0x40,0x3f},
    {0x1f,0x20,0x40,0x20,0x1f}, {0x3f,0x40,0x38,0x40,0x3f}, {0x63,0x14,0x08,0x14,0x63},
    {0x07,0x08,0x70,0x08,0x07}, {0x61,0x51,0x49,0x45,0x43}, {0x02,0x01,0x51,0x09,0x06},
    {0x20,0x10,0x08,0x04,0x02},
};

static const uint8_t *glyph(char c) {
    if (c >= 'a' && c <= 'z') c -= 32;
    if (c == '+') return font[1];
    if (c == '-') return font[2];
    if (c == '.') return font[3];
    if (c >= '0' && c <= '9') return font[4 + c - '0'];
    if (c == ':') return font[14];
    if (c >= 'A' && c <= 'Z') return font[15 + c - 'A'];
    if (c == '?') return font[41];
    if (c == '/') return font[42];
    return font[0];
}

static bool IRAM_ATTR on_flushed(esp_lcd_panel_io_handle_t panel, esp_lcd_panel_io_event_data_t *data, void *ctx) {
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(flushed, &woken);
    return woken == pdTRUE;
}

static void command(uint8_t cmd, const uint8_t *data, size_t length) {
    esp_lcd_panel_io_tx_param(io, cmd, data, length);
}

static void window(int x0, int y0, int x1, int y1) {
    uint8_t col[4] = {x0 >> 8, x0, x1 >> 8, x1}, row[4] = {y0 >> 8, y0, y1 >> 8, y1};
    command(0x2a, col, 4);
    command(0x2b, row, 4);
}

/* RAMWR (0x2c) restarts at the window origin; later chunks of the same
 * window must use Memory Write Continue (0x3c). */
static void push(const uint16_t *pixels, size_t count, bool first) {
    esp_lcd_panel_io_tx_color(io, first ? 0x2c : 0x3c, pixels, count * 2);
    xSemaphoreTake(flushed, portMAX_DELAY);
}

static void fill(int x, int y, int w, int h, uint16_t colour) {
    for (int j = 0; j < w; j++) line[j] = colour >> 8 | colour << 8;
    window(x, y, x + w - 1, y + h - 1);
    for (int r = 0; r < h; r++) push(line, w, r == 0);
}

static void text(int x, int y, const char *s, int size, uint16_t fg, uint16_t bg) {
    for (; *s; s++, x += 6 * size) {
        const uint8_t *g = glyph(*s);
        int w = 6 * size, h = 8 * size;
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                int gc = c / size, gr = r / size;
                bool on = gc < 5 && gr < 7 && (g[gc] >> gr & 1);
                uint16_t v = on ? fg : bg;
                line[c] = v >> 8 | v << 8;
            }
            window(x, y + r, x + w - 1, y + r);
            push(line, w, true);
        }
    }
}

static void panel_init(void) {
    gpio_set_direction(PIN_BACKLIGHT, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_BACKLIGHT, 1);
    spi_bus_config_t bus = {.sclk_io_num = PIN_SCLK, .mosi_io_num = PIN_MOSI, .miso_io_num = PIN_MISO,
                            .quadwp_io_num = -1, .quadhd_io_num = -1, .max_transfer_sz = CYD_COLUMNS * 2 * 2};
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO));
    flushed = xSemaphoreCreateBinary();
    esp_lcd_panel_io_spi_config_t config = {.cs_gpio_num = PIN_CS, .dc_gpio_num = PIN_DC, .spi_mode = 0,
        .pclk_hz = 40 * 1000 * 1000, .trans_queue_depth = 4, .on_color_trans_done = on_flushed,
        .lcd_cmd_bits = 8, .lcd_param_bits = 8};
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &config, &io));
    command(0x01, NULL, 0);
    vTaskDelay(pdMS_TO_TICKS(150));
    uint8_t id[4] = {0};
    esp_lcd_panel_io_rx_param(io, 0x04, id, 4);
    /* ST7789 answers 85 85 52 (CYD2USB); ILI9341 does not. */
    st7789 = (id[1] == 0x85 && id[3] == 0x52) || (id[0] == 0x85 && id[2] == 0x52);
    command(0x11, NULL, 0);
    vTaskDelay(pdMS_TO_TICKS(120));
    uint8_t colmod = 0x55, madctl = st7789 ? 0x00 : 0x08;
    command(0x3a, &colmod, 1);
    command(0x36, &madctl, 1);
    inverted = st7789;
    command(inverted ? 0x21 : 0x20, NULL, 0);
    /* Fixed top (status, scale, spectrum), scrolling waterfall, fixed controls. */
    uint8_t scroll_area[6] = {0, CYD_WATERFALL_Y, 0, CYD_WATERFALL_H, 0, CYD_CONTROLS_H};
    command(0x33, scroll_area, 6);
    scroll_identity();
    command(0x29, NULL, 0);
    printf("#CYD panel %s id %02x %02x %02x %02x\n", st7789 ? "ST7789" : "ILI9341", id[0], id[1], id[2], id[3]);
}

static int touch_transfer(uint8_t cmd) {
    int value = 0;
    for (int bit = 7; bit >= 0; bit--) {
        gpio_set_level(PIN_T_MOSI, cmd >> bit & 1);
        esp_rom_delay_us(2);
        gpio_set_level(PIN_T_CLK, 1);
        esp_rom_delay_us(2);
        gpio_set_level(PIN_T_CLK, 0);
    }
    for (int bit = 0; bit < 16; bit++) {
        gpio_set_level(PIN_T_CLK, 1);
        esp_rom_delay_us(2);
        value = value << 1 | gpio_get_level(PIN_T_MISO);
        gpio_set_level(PIN_T_CLK, 0);
        esp_rom_delay_us(2);
    }
    /* One busy clock, 12 data bits MSB first, then three zeros. */
    return value >> 3 & 0xfff;
}

static bool touch_read(int *raw_x, int *raw_y) {
    if (gpio_get_level(PIN_T_IRQ)) return false;
    gpio_set_level(PIN_T_CS, 0);
    int x = 0, y = 0;
    for (int j = 0; j < 4; j++) {
        x += touch_transfer(0xd0);
        y += touch_transfer(0x90);
    }
    touch_transfer(0x80);
    gpio_set_level(PIN_T_CS, 1);
    *raw_x = x / 4;
    *raw_y = y / 4;
    return true;
}

static void touch_init(void) {
    gpio_config_t out = {.pin_bit_mask = BIT64(PIN_T_CLK) | BIT64(PIN_T_MOSI) | BIT64(PIN_T_CS),
                         .mode = GPIO_MODE_OUTPUT};
    gpio_config(&out);
    gpio_config_t in = {.pin_bit_mask = BIT64(PIN_T_MISO) | BIT64(PIN_T_IRQ), .mode = GPIO_MODE_INPUT};
    gpio_config(&in);
    gpio_set_level(PIN_T_CS, 1);
    gpio_set_level(PIN_T_CLK, 0);
}


static void scroll_identity(void) {
    uint8_t start[2] = {0, CYD_WATERFALL_Y};
    command(0x37, start, 2);
    scroll = 0;
}

static uint16_t swap16(uint16_t v) {
    return v >> 8 | v << 8;
}

static void text_centered(int cx, int y, const char *s, int size, uint16_t fg, uint16_t bg) {
    text(cx - (int)strlen(s) * 3 * size, y, s, size, fg, bg);
}

static int span(void) {
    return cyd_span_mhz[span_index];
}

static int marker_column(void) {
    if (preset < 0 || cyd_presets[preset].marker_khz == CYD_MARKER_NONE) return -1;
    if ((int)radio->frequency() != cyd_presets[preset].lo_mhz) return -1;
    return cyd_offset_column(cyd_presets[preset].marker_khz, span());
}

static bool extended(void) {
    unsigned f = radio->frequency();
    return f < 2400 || f > 2500;
}

/* --- Regions ------------------------------------------------------------ */

static void draw_status(void) {
    char s[32];
    fill(0, CYD_STATUS_Y, CYD_COLUMNS, CYD_STATUS_H, 0x0000);
    snprintf(s, sizeof(s), "%u", radio->frequency());
    text(4, 2, s, 2, 0xffff, 0x0000);
    text(4 + 12 * (int)strlen(s) + 4, 9, "MHZ", 1, 0x8410, 0x0000);
    const char *badge = NULL;
    uint16_t colour = 0x07e0;
    if (host_shown) { badge = "HOST"; colour = 0xfd20; }
    else if (frozen) { badge = "FROZEN"; colour = 0x07ff; }
    else if (preset >= 0 && (int)radio->frequency() == cyd_presets[preset].lo_mhz) badge = cyd_presets[preset].label;
    if (badge) text(150, 2, badge, 1, colour, 0x0000);
    if (extended()) text(210, 2, "EXT", 1, 0xf800, 0x0000);
    if (radio->hardware_agc()) snprintf(s, sizeof(s), "AGC %dM", span());
    else snprintf(s, sizeof(s), "G%u %dM", radio->gain_code(), span());
    text(150, 12, s, 1, 0xbdf7, 0x0000);
}

static void draw_stats(void) {
    char s[40];
    int c = cyd_peak_column(db);
    long khz = (long)(c * 2 + 1) * span() * 1000 / (2 * CYD_COLUMNS) - (long)span() * 500;
    long f10 = (long)radio->frequency() * 10 + khz / 100;
    int level = (int)(db[c] - floor_db);
    int n = snprintf(s, sizeof(s), "PK %ld.%ld +%dDB", f10 / 10, f10 % 10, level < 0 ? 0 : level);
    if (marker_column() >= 0) snprintf(s + n, sizeof(s) - n, "  BURSTS %u", bursts.count);
    fill(0, 22, CYD_COLUMNS, 9, 0x0000);
    text(4, 23, s, 1, 0xffe0, 0x0000);
}

static void draw_scale(void) {
    char s[8];
    fill(0, CYD_SCALE_Y, CYD_COLUMNS, CYD_SCALE_H, 0x0000);
    static const int ticks[5] = {30, 75, 120, 165, 210};
    for (int k = 0; k < 5; k++) {
        int c = ticks[k];
        fill(c, CYD_SCALE_Y, 1, k == 2 ? 4 : 2, 0xffff);
        snprintf(s, sizeof(s), "%d", cyd_column_mhz((int)radio->frequency(), c, span()));
        text_centered(c, CYD_SCALE_Y + 4, s, 1, k == 2 ? 0xffff : 0x8410, 0x0000);
    }
    int m = marker_column();
    if (m >= 0) {
        uint16_t colour = cyd_presets[preset].measured ? 0xf81f : 0x8010;
        fill(m > 1 ? m - 1 : 0, CYD_SCALE_Y, 3, 3, colour);
        if (!cyd_presets[preset].measured) text(m + 3 < 232 ? m + 3 : 226, CYD_SCALE_Y, "?", 1, colour, 0x0000);
    }
}

static void draw_spectrum(void) {
    uint16_t out[CYD_COLUMNS];
    int m = marker_column();
    float range = (float)cyd_range_db[range_index];
    window(0, CYD_SPECTRUM_Y, CYD_COLUMNS - 1, CYD_SPECTRUM_Y + CYD_SPECTRUM_H - 1);
    for (int r = 0; r < CYD_SPECTRUM_H; r++) {
        cyd_spectrum_line(db, peak, floor_db, range, r, m, out);
        for (int c = 0; c < CYD_COLUMNS; c++) line[c] = swap16(out[c]);
        push(line, CYD_COLUMNS, r == 0);
    }
}

static void button(int x, int y, int w, int h, const char *top, const char *big, uint16_t bg) {
    fill(x + 1, y + 1, w - 2, h - 2, bg);
    if (top && big) {
        text_centered(x + w / 2, y + h / 2 - 12, top, 1, 0xbdf7, bg);
        text_centered(x + w / 2, y + h / 2, big, 2, 0xffff, bg);
    } else if (big) {
        text_centered(x + w / 2, y + h / 2 - 8, big, 2, 0xffff, bg);
    } else if (top) {
        text_centered(x + w / 2, y + h / 2 - 4, top, 1, 0xffff, bg);
    }
}

static void draw_controls(int pressed) {
    char step[8];
    snprintf(step, sizeof(step), "%d", cyd_steps_mhz[step_index]);
    const int w = CYD_COLUMNS / 4, y = CYD_CONTROLS_Y, h = CYD_CONTROLS_H;
    fill(0, y, CYD_COLUMNS, 1, 0x4208);
    uint16_t base = 0x2124, hot = 0x7bef;
    button(0, y, w, h, "MHZ", "-", pressed == 0 ? hot : base);
    button(w, y, w, h, "STEP", step, pressed == 1 ? hot : base);
    button(2 * w, y, w, h, "MHZ", "+", pressed == 2 ? hot : base);
    button(3 * w, y, w, h, NULL, "MENU", pressed == 3 ? hot : menu_open ? 0x0320 : base);
}

static const char *menu_label(int item, char *buf, size_t size) {
    switch (item) {
    case 0: case 1: case 2: case 3: case 4: case 5: case 6: return cyd_presets[item].label;
    case 7: snprintf(buf, size, "SPAN %d", cyd_span_mhz[span_index]); return buf;
    case 8:
        if (cyd_filter_mhz[filter_index]) snprintf(buf, size, "FILT %d", cyd_filter_mhz[filter_index]);
        else snprintf(buf, size, "FILT AUTO");
        return buf;
    case 9: return radio->hardware_agc() ? "GAIN AGC" : "GAIN MAN";
    case 10: return "GAIN -";
    case 11: return "GAIN +";
    case 12: snprintf(buf, size, "RANGE %d", cyd_range_db[range_index]); return buf;
    case 13: return frozen ? "RESUME" : "FREEZE";
    default: return "CLOSE";
    }
}

static void draw_menu(int pressed) {
    char buf[16];
    const int w = CYD_COLUMNS / CYD_MENU_COLS;
    fill(0, CYD_WATERFALL_Y, CYD_COLUMNS, CYD_WATERFALL_H, 0x0000);
    for (int i = 0; i < CYD_MENU_ROWS * CYD_MENU_COLS; i++) {
        int r = i / CYD_MENU_COLS, c = i % CYD_MENU_COLS;
        int y0 = CYD_WATERFALL_Y + r * CYD_WATERFALL_H / CYD_MENU_ROWS;
        int y1 = CYD_WATERFALL_Y + (r + 1) * CYD_WATERFALL_H / CYD_MENU_ROWS;
        uint16_t bg = i == pressed ? 0x7bef : i < CYD_PRESETS && i == preset ? 0x0320 : i < CYD_PRESETS ? 0x10a6 : 0x2124;
        button(c * w, y0, w, y1 - y0, menu_label(i, buf, sizeof(buf)), NULL, bg);
    }
}

static void reset_view(void) {
    first_row = true;
    bursts.count = 0;
    bursts.high = false;
}

static void retune(int mhz) {
    if (mhz <= 0 || !radio->tune((unsigned)mhz)) return;
    if (preset >= 0 && (int)radio->frequency() != cyd_presets[preset].lo_mhz) preset = -1;
    reset_view();
    draw_status();
    draw_scale();
    printf("#CYD freq %u span %d\n", radio->frequency(), span());
}

static void open_menu(bool open) {
    menu_open = open;
    scroll_identity();
    if (open) draw_menu(-1);
    else fill(0, CYD_WATERFALL_Y, CYD_COLUMNS, CYD_WATERFALL_H, 0x0000);
    draw_controls(-1);
}

static void menu_action(int item) {
    if (item < 0) return;
    draw_menu(item);
    vTaskDelay(pdMS_TO_TICKS(60));
    if (item < CYD_PRESETS) {
        preset = item;
        /* Measured BLE markers come from 16 MS/s sessions; Wi-Fi fits 40 MHz;
         * the whole 2.4 GHz band needs the 80 MHz span. */
        span_index = item < 3 ? 0 : item < 6 ? 1 : 2;
        retune(cyd_presets[item].lo_mhz);
        open_menu(false);
        return;
    }
    switch (item) {
    case 7: span_index = (span_index + 1) % CYD_SPANS; reset_view(); break;
    case 8:
        filter_index = (filter_index + 1) % CYD_FILTERS;
        radio->set_filter((unsigned)cyd_filter_mhz[filter_index]);
        reset_view();
        break;
    case 9: radio->set_gain(!radio->hardware_agc(), radio->gain_code()); reset_view(); break;
    case 10: case 11: {
        int g = (int)radio->gain_code() + (item == 10 ? -4 : 4);
        if (g < 0) g = 0;
        if (g > (int)radio->gain_max()) g = (int)radio->gain_max();
        radio->set_gain(false, (unsigned)g);
        reset_view();
        break;
    }
    case 12: range_index = (range_index + 1) % CYD_RANGES; break;
    case 13: frozen = !frozen; break;
    default: open_menu(false); draw_status(); return;
    }
    draw_menu(-1);
    draw_status();
    draw_scale();
}

static void main_action(cyd_hit_t hit, int x) {
    int lo = (int)radio->frequency(), step = cyd_steps_mhz[step_index];
    if (hit == CYD_HIT_TUNE) { retune(cyd_column_mhz(lo, x, span())); return; }
    if (hit == CYD_HIT_NONE) return;
    int index = hit == CYD_HIT_DOWN ? 0 : hit == CYD_HIT_STEP ? 1 : hit == CYD_HIT_UP ? 2 : 3;
    draw_controls(index);
    vTaskDelay(pdMS_TO_TICKS(60));
    if (hit == CYD_HIT_DOWN) retune(lo - step);
    else if (hit == CYD_HIT_UP) retune(lo + step);
    else if (hit == CYD_HIT_STEP) step_index = (step_index + 1) % 3;
    else if (hit == CYD_HIT_MENU) { open_menu(!menu_open); return; }
    draw_controls(-1);
}

/* One action per press; only the +/- buttons repeat while held. */
static void handle_touch(void) {
    int raw_x, raw_y, x, y;
    int64_t now = esp_timer_get_time();
    if (!touch_read(&raw_x, &raw_y)) { touch_down = false; return; }
    cyd_touch_map(calibration, raw_x, raw_y, &x, &y);
    if (menu_open && y >= CYD_WATERFALL_Y && y < CYD_CONTROLS_Y) {
        if (!touch_down) menu_action(cyd_hit_menu(x, y));
        touch_down = true;
        return;
    }
    cyd_hit_t hit = cyd_hit_main(x, y);
    if (menu_open && hit == CYD_HIT_TUNE) hit = CYD_HIT_NONE;
    bool repeat = hit == CYD_HIT_DOWN || hit == CYD_HIT_UP;
    if (touch_down && !(repeat && now - touch_at >= TOUCH_REPEAT_US)) return;
    touch_down = true;
    touch_at = now;
    main_action(hit, x);
}

static void draw_row(void) {
    const uint32_t *words;
    if (!radio->acquire(CAPTURE_SAMPLES, span_index, &words)) return;
    cyd_row_db(words, CAPTURE_SAMPLES, db);
    floor_db = cyd_floor_update(floor_db, db, first_row);
    cyd_peak_update(peak, db, PEAK_DECAY_DB, first_row);
    first_row = false;
    int m = marker_column();
    cyd_burst_update(&bursts, db, m, floor_db, BURST_THRESHOLD_DB);
    draw_spectrum();
    if (menu_open) return;
    float range = (float)cyd_range_db[range_index];
    for (int c = 0; c < CYD_COLUMNS; c++) {
        uint16_t v = cyd_palette(cyd_level(db[c], floor_db, range));
        if (c == m && v == 0x0000) v = 0x3007;
        line[c] = swap16(v);
    }
    /* Newest row on top: move the scroll start up one line, then draw it. */
    scroll = (scroll + CYD_WATERFALL_H - 1) % CYD_WATERFALL_H;
    int y = CYD_WATERFALL_Y + (int)scroll;
    window(0, y, CYD_COLUMNS - 1, y);
    push(line, CYD_COLUMNS, true);
    uint8_t start[2] = {y >> 8, y & 255};
    command(0x37, start, 2);
}

static void finish_screen(void) {
    scroll_identity();
    fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, 0x0000);
    draw_status();
    draw_scale();
    draw_controls(-1);
    reset_view();
}

/* Calibration runs from the idle hook as a small state machine, so host
 * commands keep working while it waits for taps. -1 means not calibrating. */
static int cal_step = -1;
static int cal_raw[3][2];
static const int cal_points[3][2] = {{CYD_CAL_MARGIN, CYD_CAL_MARGIN},
    {CYD_COLUMNS - CYD_CAL_MARGIN, CYD_CAL_MARGIN}, {CYD_CAL_MARGIN, CYD_SCREEN_HEIGHT - CYD_CAL_MARGIN}};

/* One press: average the readings taken while it is held. */
static bool sample_press(int *raw_x, int *raw_y) {
    if (gpio_get_level(PIN_T_IRQ)) return false;
    vTaskDelay(pdMS_TO_TICKS(30));
    int sx = 0, sy = 0, n = 0, x, y;
    for (int k = 0; k < 10 && touch_read(&x, &y); k++, n++) {
        sx += x; sy += y;
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    int64_t release = esp_timer_get_time() + 3000000;
    while (!gpio_get_level(PIN_T_IRQ) && esp_timer_get_time() < release) vTaskDelay(pdMS_TO_TICKS(10));
    if (n < 2) return false;
    *raw_x = sx / n;
    *raw_y = sy / n;
    return true;
}

static void cross(int x, int y, uint16_t colour) {
    int x0 = x > 15 ? x - 15 : 0, y0 = y > 15 ? y - 15 : 0;
    fill(x0, y - 1, 31, 3, colour);
    fill(x - 1, y0, 3, 31, colour);
}

static void cal_prompt(const char *headline) {
    char s[24];
    fill(0, 120, CYD_COLUMNS, 60, 0x0000);
    text(30, 124, headline, 1, 0xf800, 0x0000);
    text(30, 140, "PRESS AND HOLD", 2, 0xffff, 0x0000);
    snprintf(s, sizeof(s), "CROSS %d OF 3", cal_step + 1);
    text(30, 160, s, 2, 0xffe0, 0x0000);
    cross(cal_points[cal_step][0], cal_points[cal_step][1], 0xffff);
}

static void start_calibration(const char *headline) {
    fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, 0x0000);
    cal_step = 0;
    cal_prompt(headline);
    printf("#CYD calibration started\n");
}

static void calibration_tick(void) {
    int x, y;
    if (!sample_press(&x, &y)) return;
    cal_raw[cal_step][0] = x;
    cal_raw[cal_step][1] = y;
    printf("#CYD cal point %d raw %d %d\n", cal_step, x, y);
    cross(cal_points[cal_step][0], cal_points[cal_step][1], 0x0000);
    if (++cal_step < 3) { cal_prompt(""); return; }
    cyd_cal_t c;
    if (!cyd_touch_calibrate(cal_raw, &c)) {
        printf("#CYD calibration rejected\n");
        start_calibration("TRY AGAIN");
        return;
    }
    cal = c;
    calibration = &cal;
    nvs_handle_t h;
    if (nvs_open("cyd", NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_blob(h, "touch", &cal, sizeof(cal));
        nvs_commit(h);
        nvs_close(h);
    }
    printf("#CYD cal swap %d u %d %d v %d %d\n", cal.swap, cal.u0, cal.u1, cal.v0, cal.v2);
    cal_step = -1;
    finish_screen();
}

static void load_calibration(void) {
    nvs_handle_t h;
    size_t length = sizeof(cal);
    if (nvs_open("cyd", NVS_READONLY, &h) != ESP_OK) return;
    if (nvs_get_blob(h, "touch", &cal, &length) == ESP_OK && length == sizeof(cal)) calibration = &cal;
    nvs_close(h);
}

void cyd_display_init(const cyd_radio_t *ops) {
    radio = ops;
    line = heap_caps_malloc(CYD_COLUMNS * 2, MALLOC_CAP_DMA);
    if (!line) return;
    panel_init();
    touch_init();
    load_calibration();
    active = true;
    host_at = esp_timer_get_time() - HOST_IDLE_US;
    /* The firmware carries this board's calibration; hold a finger on the
     * screen at power-up to redo it. */
    if (!gpio_get_level(PIN_T_IRQ)) {
        int64_t release = esp_timer_get_time() + 3000000;
        while (!gpio_get_level(PIN_T_IRQ) && esp_timer_get_time() < release) vTaskDelay(pdMS_TO_TICKS(10));
        start_calibration("TOUCH CALIBRATION");
    } else {
        finish_screen();
    }
}

void cyd_display_host_activity(void) {
    host_at = esp_timer_get_time();
}

void cyd_display_idle(void) {
    int64_t now = esp_timer_get_time();
    if (!active) return;
    if (cal_step >= 0) { calibration_tick(); return; }
    if (now - host_at < HOST_IDLE_US) {
        /* The host owns the radio; say so once instead of freezing silently. */
        if (!host_shown) { host_shown = true; draw_status(); }
        return;
    }
    if (host_shown) {
        host_shown = false;
        /* The host may have retuned or changed gain and filter. */
        if (preset >= 0 && (int)radio->frequency() != cyd_presets[preset].lo_mhz) preset = -1;
        reset_view();
        draw_status();
        draw_scale();
    }
    handle_touch();
    if (now - stats_at >= STATS_PERIOD_US && !first_row) {
        stats_at = now;
        draw_stats();
    }
    if (frozen || now - row_at < ROW_PERIOD_US) return;
    row_at = now;
    draw_row();
}

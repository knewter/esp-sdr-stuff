/* CYD display driver for the ESP-SDR ESP32 receiver (GPLv3, as the ESP-SDR
 * project it extends): ILI9341/ST7789 panel (240x320 portrait, HSPI) and
 * bit-banged XPT2046 touch, touch calibration, the CYD* host commands and the
 * idle dispatch into the screens in cyd_ui.c. Everything runs inside the
 * receiver loop between host commands; the radio is never used concurrently.
 */
#include "cyd_display.h"
#include "cyd_gfx.h"
#include "cyd_ui.h"
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
#include "esp_rom_crc.h"
#include "burst_serial.h"

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

uint16_t *gfx_line;
static esp_lcd_panel_io_handle_t io, io_read;
static SemaphoreHandle_t flushed;
static bool active, inverted, st7789, host_shown, press_active;
static int64_t host_at;
static cyd_cal_t cal;
static const cyd_cal_t *calibration = &cyd_cal_default;
/* Virtual touch from CYDTAP, in screen coordinates. */
static int vt_x, vt_y;
static int64_t vt_until;

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
    {0x20,0x10,0x08,0x04,0x02}, {0x00,0x50,0x30,0x00,0x00}, {0x00,0x1c,0x22,0x41,0x00},
    {0x00,0x41,0x22,0x1c,0x00}, {0x00,0x41,0x22,0x14,0x08}, {0x23,0x13,0x08,0x64,0x62},
    {0x00,0x00,0x5f,0x00,0x00}, {0x14,0x14,0x14,0x14,0x14},
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
    if (c == ',') return font[43];
    if (c == '(') return font[44];
    if (c == ')') return font[45];
    if (c == '>') return font[46];
    if (c == '%') return font[47];
    if (c == '!') return font[48];
    if (c == '=') return font[49];
    return font[0];
}

static bool IRAM_ATTR on_flushed(esp_lcd_panel_io_handle_t panel, esp_lcd_panel_io_event_data_t *data, void *ctx) {
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(flushed, &woken);
    return woken == pdTRUE;
}

/* Reads start a new serial transaction on a chip-select falling edge; writes
 * are synchronous, so nothing is in flight when the pin is pulsed. */
static void read_param(int cmd, uint8_t *data, size_t length) {
    gpio_set_level(PIN_CS, 1);
    esp_rom_delay_us(1);
    gpio_set_level(PIN_CS, 0);
    esp_lcd_panel_io_rx_param(io_read, cmd, data, length);
    gpio_set_level(PIN_CS, 1);
    esp_rom_delay_us(1);
    gpio_set_level(PIN_CS, 0);
}

void gfx_command(uint8_t cmd, const uint8_t *data, size_t length) {
    esp_lcd_panel_io_tx_param(io, cmd, data, length);
}
#define command gfx_command

void gfx_window(int x0, int y0, int x1, int y1) {
    uint8_t col[4] = {x0 >> 8, x0, x1 >> 8, x1}, row[4] = {y0 >> 8, y0, y1 >> 8, y1};
    gfx_command(0x2a, col, 4);
    gfx_command(0x2b, row, 4);
}

void gfx_push(const uint16_t *pixels, size_t count, bool first) {
    esp_lcd_panel_io_tx_color(io, first ? 0x2c : 0x3c, pixels, count * 2);
    xSemaphoreTake(flushed, portMAX_DELAY);
}

void gfx_fill(int x, int y, int w, int h, uint16_t colour) {
    if (w <= 0 || h <= 0) return;
    int rows = CYD_LINE_ROWS * CYD_COLUMNS / w;
    if (rows > h) rows = h;
    for (int j = 0; j < w * rows; j++) gfx_line[j] = gfx_swap(colour);
    gfx_window(x, y, x + w - 1, y + h - 1);
    for (int r = 0; r < h; r += rows) gfx_push(gfx_line, (size_t)w * (h - r < rows ? h - r : rows), r == 0);
}

/* One glyph per window: the whole character in a single transfer. */
void gfx_text(int x, int y, const char *s, int size, uint16_t fg, uint16_t bg) {
    int w = 6 * size, h = 8 * size;
    for (; *s; s++, x += w) {
        const uint8_t *g = glyph(*s);
        for (int r = 0; r < h; r++)
            for (int c = 0; c < w; c++) {
                int gc = c / size, gr = r / size;
                bool on = gc < 5 && gr < 7 && (g[gc] >> gr & 1);
                gfx_line[r * w + c] = gfx_swap(on ? fg : bg);
            }
        gfx_window(x, y, x + w - 1, y + h - 1);
        gfx_push(gfx_line, (size_t)w * h, true);
    }
}

void gfx_text_centered(int cx, int y, const char *s, int size, uint16_t fg, uint16_t bg) {
    gfx_text(cx - (int)strlen(s) * 3 * size, y, s, size, fg, bg);
}

void gfx_scroll_start(int line) {
    uint8_t start[2] = {line >> 8, line & 255};
    gfx_command(0x37, start, 2);
}

static void panel_init(void) {
    gpio_set_direction(PIN_BACKLIGHT, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_BACKLIGHT, 1);
    spi_bus_config_t bus = {.sclk_io_num = PIN_SCLK, .mosi_io_num = PIN_MOSI, .miso_io_num = PIN_MISO,
                            .quadwp_io_num = -1, .quadhd_io_num = -1, .max_transfer_sz = CYD_COLUMNS * 2 * CYD_LINE_ROWS};
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO));
    flushed = xSemaphoreCreateBinary();
    /* The panel is the only device on this bus, so chip select is held low
     * and neither SPI handle owns it: two handles sharing one CS pin would
     * leave the pin routed to whichever was created last. */
    gpio_set_direction(PIN_CS, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_CS, 0);
    esp_lcd_panel_io_spi_config_t config = {.cs_gpio_num = -1, .dc_gpio_num = PIN_DC, .spi_mode = 0,
        .pclk_hz = 40 * 1000 * 1000, .trans_queue_depth = 4, .on_color_trans_done = on_flushed,
        .lcd_cmd_bits = 8, .lcd_param_bits = 8};
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &config, &io));
    /* Panel reads are slow (ILI9341 read cycle >= 150 ns): a second handle on
     * the same pins at 5 MHz, used only for the ID and screenshots. */
    esp_lcd_panel_io_spi_config_t slow = config;
    slow.pclk_hz = 5 * 1000 * 1000;
    slow.on_color_trans_done = NULL;
    slow.trans_queue_depth = 1;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &slow, &io_read));
    gfx_command(0x01, NULL, 0);
    vTaskDelay(pdMS_TO_TICKS(150));
    uint8_t id[4] = {0};
    read_param(0x04, id, 4);
    /* ST7789 answers 85 85 52 (CYD2USB); ILI9341 does not. */
    st7789 = (id[1] == 0x85 && id[3] == 0x52) || (id[0] == 0x85 && id[2] == 0x52);
    gfx_command(0x11, NULL, 0);
    vTaskDelay(pdMS_TO_TICKS(120));
    uint8_t colmod = 0x55, madctl = st7789 ? 0x00 : 0x08;
    gfx_command(0x3a, &colmod, 1);
    gfx_command(0x36, &madctl, 1);
    inverted = st7789;
    gfx_command(inverted ? 0x21 : 0x20, NULL, 0);
    /* Fixed top (status, scale, spectrum), scrolling waterfall, fixed controls. */
    uint8_t scroll_area[6] = {0, CYD_WATERFALL_Y, 0, CYD_WATERFALL_H, 0, CYD_CONTROLS_H};
    gfx_command(0x33, scroll_area, 6);
    gfx_scroll_start(CYD_WATERFALL_Y);
    gfx_command(0x29, NULL, 0);
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
    gfx_fill(x0, y - 1, 31, 3, colour);
    gfx_fill(x - 1, y0, 3, 31, colour);
}

static void cal_prompt(const char *headline) {
    char s[24];
    gfx_fill(0, 120, CYD_COLUMNS, 60, 0x0000);
    gfx_text(30, 124, headline, 1, 0xf800, 0x0000);
    gfx_text(30, 140, "PRESS AND HOLD", 2, 0xffff, 0x0000);
    snprintf(s, sizeof(s), "CROSS %d OF 3", cal_step + 1);
    gfx_text(30, 160, s, 2, 0xffe0, 0x0000);
    cross(cal_points[cal_step][0], cal_points[cal_step][1], 0xffff);
}

static void start_calibration(const char *headline) {
    gfx_scroll_start(CYD_WATERFALL_Y);
    gfx_fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, 0x0000);
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
    cyd_ui_redraw();
}

static void load_calibration(void) {
    nvs_handle_t h;
    size_t length = sizeof(cal);
    if (nvs_open("cyd", NVS_READONLY, &h) != ESP_OK) return;
    if (nvs_get_blob(h, "touch", &cal, &length) == ESP_OK && length == sizeof(cal)) calibration = &cal;
    nvs_close(h);
}

void cyd_display_calibrate(void) {
    start_calibration("TOUCH SETUP");
}

/* --- Host commands ------------------------------------------------------------- */

/* Screen row y shows GRAM row: fixed top, scrolled waterfall, fixed bottom. */
static int gram_row(int y) {
    if (y < CYD_WATERFALL_Y || y >= CYD_WATERFALL_Y + CYD_WATERFALL_H) return y;
    return CYD_WATERFALL_Y + (y - CYD_WATERFALL_Y + cyd_ui_scroll()) % CYD_WATERFALL_H;
}

static void reply(const char *text) {
    burst_serial_send(text, strlen(text));
}

/* Rows in display order, read back from the panel's own memory: 1 dummy byte
 * then 3 bytes per pixel (RGB666 as the panel reports it). */
static void screenshot(void) {
    enum { ROW = 1 + CYD_COLUMNS * 3 };
    uint8_t *buf = heap_caps_malloc(ROW + 3, MALLOC_CAP_DMA);
    if (!buf) { reply("CYD ERR memory\n"); return; }
    char head[64];
    snprintf(head, sizeof(head), "CYD SHOT %d %d %d\n", CYD_COLUMNS, CYD_SCREEN_HEIGHT, ROW);
    reply(head);
    uint32_t crc = 0;
    for (int y = 0; y < CYD_SCREEN_HEIGHT; y++) {
        int g = gram_row(y);
        gfx_window(0, g, CYD_COLUMNS - 1, g);
        read_param(0x2e, buf, ROW);
        crc = esp_rom_crc32_le(crc, buf, ROW);
        burst_serial_send(buf, ROW);
    }
    free(buf);
    snprintf(head, sizeof(head), "CYD SHOT END %08lx\n", (unsigned long)crc);
    reply(head);
}

bool cyd_display_host_line(const char *line) {
    int x, y, ms;
    char extra, report[512];
    if (!active || strncmp(line, "CYD", 3)) return false;
    if (!strcmp(line, "CYDSHOT")) screenshot();
    else if (!strcmp(line, "CYDSTAT")) {
        cyd_ui_report(report, sizeof(report));
        reply("CYD STAT ");
        reply(report);
        reply("\n");
    } else if (!strcmp(line, "CYDSTATRESET")) { cyd_ui_reset_stats(); reply("CYD OK\n"); }
    else if (sscanf(line, "CYDTAP %d %d %d %c", &x, &y, &ms, &extra) == 3 && ms > 0 && ms <= 5000) {
        vt_x = x; vt_y = y;
        vt_until = esp_timer_get_time() + (int64_t)ms * 1000;
        reply("CYD OK\n");
    } else reply("CYD ERR command\n");
    return true;
}

/* --- Entry points --------------------------------------------------------------- */

void cyd_display_init(const cyd_radio_t *ops) {
    gfx_line = heap_caps_malloc(CYD_COLUMNS * CYD_LINE_ROWS * 2, MALLOC_CAP_DMA);
    if (!gfx_line) return;
    panel_init();
    touch_init();
    load_calibration();
    active = true;
    host_at = esp_timer_get_time() - HOST_IDLE_US;
    cyd_ui_init(ops);
    /* The firmware carries this board's calibration; hold a finger on the
     * screen at power-up to redo it. */
    if (!gpio_get_level(PIN_T_IRQ)) {
        int64_t release = esp_timer_get_time() + 3000000;
        while (!gpio_get_level(PIN_T_IRQ) && esp_timer_get_time() < release) vTaskDelay(pdMS_TO_TICKS(10));
        start_calibration("TOUCH CALIBRATION");
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
        if (!host_shown) { host_shown = true; cyd_ui_host(true); }
        return;
    }
    if (host_shown) { host_shown = false; cyd_ui_host(false); }
    int raw_x, raw_y, x, y;
    bool pressed = true;
    if (now < vt_until) { x = vt_x; y = vt_y; }
    else if (touch_read(&raw_x, &raw_y)) cyd_touch_map(calibration, raw_x, raw_y, &x, &y);
    else pressed = false;
    if (pressed) { cyd_ui_press(x, y, !press_active, now); press_active = true; }
    else if (press_active) { press_active = false; cyd_ui_release(); }
    cyd_ui_tick(now);
}

/* CYD on-screen waterfall for the ESP-SDR ESP32 receiver (GPLv3, as the
 * ESP-SDR project it extends).
 *
 * Panel: ILI9341 or ST7789 (CYD2USB), 240x320 portrait, HSPI. Rows scroll
 * with the panel's own vertical-scroll registers, so no framebuffer is kept.
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
#define SCROLL_LINES (CYD_SCREEN_HEIGHT - CYD_STATUS_HEIGHT)

static const cyd_radio_t *radio;
static esp_lcd_panel_io_handle_t io;
static SemaphoreHandle_t flushed;
static uint16_t *line;
static int64_t host_at, row_at, touch_at;
static bool active, inverted, st7789, first_row = true;
static unsigned step_index, scroll;
static float floor_db;
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
    {0x07,0x08,0x70,0x08,0x07}, {0x61,0x51,0x49,0x45,0x43},
};

static const uint8_t *glyph(char c) {
    if (c >= 'a' && c <= 'z') c -= 32;
    if (c == '+') return font[1];
    if (c == '-') return font[2];
    if (c == '.') return font[3];
    if (c >= '0' && c <= '9') return font[4 + c - '0'];
    if (c == ':') return font[14];
    if (c >= 'A' && c <= 'Z') return font[15 + c - 'A'];
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

static void status_bar(void) {
    char s[32];
    fill(0, 0, CYD_COLUMNS, CYD_STATUS_HEIGHT, 0x0000);
    snprintf(s, sizeof(s), "%u MHZ", radio->frequency());
    text(4, 2, s, 2, 0xffff, 0x0000);
    text(126, 6, radio->hardware_agc() ? "AGC" : "MAN", 1, 0x07e0, 0x0000);
    fill(0, 21, 78, 37, 0x18e3);
    fill(81, 21, 78, 37, 0x18e3);
    fill(162, 21, 78, 37, 0x18e3);
    text(33, 32, "-", 2, 0xffff, 0x18e3);
    snprintf(s, sizeof(s), "STEP %d", cyd_steps_mhz[step_index]);
    text(90, 32, s, 1, 0xffe0, 0x18e3);
    text(195, 32, "+", 2, 0xffff, 0x18e3);
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
    uint8_t scroll_area[6] = {0, CYD_STATUS_HEIGHT, SCROLL_LINES >> 8, SCROLL_LINES & 255, 0, 0};
    command(0x33, scroll_area, 6);
    /* Identity mapping until the first row: scroll start = top of the area. */
    uint8_t start[2] = {0, CYD_STATUS_HEIGHT};
    command(0x37, start, 2);
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

static void retune(int mhz) {
    if (mhz > 0 && radio->tune((unsigned)mhz)) first_row = true;
    status_bar();
}

static void handle_touch(void) {
    int raw_x, raw_y, x, y;
    int64_t now = esp_timer_get_time();
    if (now - touch_at < TOUCH_REPEAT_US || !touch_read(&raw_x, &raw_y)) return;
    touch_at = now;
    cyd_touch_map(calibration, raw_x, raw_y, &x, &y);
    cyd_touch_t target = cyd_touch_target(x, y);
    int lo = (int)radio->frequency(), step = cyd_steps_mhz[step_index];
    printf("#CYD touch raw %d %d screen %d %d target %d\n", raw_x, raw_y, x, y, (int)target);
    /* Calibration aid: raw readings on screen and a dot where the tap mapped. */
    char raw[24];
    snprintf(raw, sizeof(raw), "%4d %4d", raw_x, raw_y);
    text(156, 6, raw, 1, 0xffff, 0x0000);
    fill(x > 2 ? x - 2 : 0, y > 2 ? y - 2 : 0, 5, 5, 0xffff);
    if (target == CYD_TOUCH_DOWN) retune(lo - step);
    else if (target == CYD_TOUCH_UP) retune(lo + step);
    else if (target == CYD_TOUCH_STEP) { step_index = (step_index + 1) % 3; status_bar(); }
    else if (target == CYD_TOUCH_LABEL) { inverted = !inverted; command(inverted ? 0x21 : 0x20, NULL, 0); }
    else if (target == CYD_TOUCH_WATERFALL) retune(cyd_column_mhz(lo, x));
    if (target != CYD_TOUCH_NONE) printf("#CYD freq %u step %d\n", radio->frequency(), cyd_steps_mhz[step_index]);
}

static void draw_row(void) {
    const uint32_t *words;
    if (!radio->acquire(CAPTURE_SAMPLES, &words)) return;
    float db[CYD_COLUMNS];
    cyd_row_db(words, CAPTURE_SAMPLES, db);
    floor_db = cyd_floor_update(floor_db, db, first_row);
    first_row = false;
    for (int c = 0; c < CYD_COLUMNS; c++) {
        uint16_t v = cyd_palette(cyd_level(db[c], floor_db));
        line[c] = v >> 8 | v << 8;
    }
    /* Newest row on top: move the scroll start up one line, then draw it. */
    scroll = (scroll + SCROLL_LINES - 1) % SCROLL_LINES;
    int y = CYD_STATUS_HEIGHT + (int)scroll;
    window(0, y, CYD_COLUMNS - 1, y);
    push(line, CYD_COLUMNS, true);
    uint8_t start[2] = {y >> 8, y & 255};
    command(0x37, start, 2);
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

static void finish_screen(void) {
    fill(0, 0, CYD_COLUMNS, CYD_SCREEN_HEIGHT, 0x0000);
    status_bar();
    first_row = true;
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
    /* First boot, or a finger held on the screen at power-up: calibrate. */
    if (calibration == &cyd_cal_default || !gpio_get_level(PIN_T_IRQ)) {
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
    if (now - host_at < HOST_IDLE_US) return;
    handle_touch();
    if (now - row_at < ROW_PERIOD_US) return;
    row_at = now;
    draw_row();
}

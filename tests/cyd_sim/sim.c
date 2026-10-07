/* Host simulator for the CYD waterfall display (not hardware evidence).
 *
 * Compiles the real firmware/cyd-waterfall sources against emulated parts:
 * - an ILI9341 panel interpreting CASET/RASET/RAMWR/RAMWRC, MADCTL mirroring,
 *   inversion and the vertical-scroll registers (VSCRDEF/VSCRSADD);
 * - an XPT2046 touch controller answering the firmware's bit-banged reads;
 * - a radio whose IQ holds noise, a CW spur, Wi-Fi-like bursts on channel 1
 *   and BLE bursts placed where this board receives them (sessions 004/005);
 * - simulated time, NVS and the FreeRTOS calls the display uses.
 */
#include "sim_idf.h"
#include "cyd_display.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define W 240
#define H 320

/* --- Time ------------------------------------------------------------- */
static int64_t now_us;
int64_t esp_timer_get_time(void) { return now_us; }
void esp_rom_delay_us(uint32_t us) { now_us += us; }
void vTaskDelay(TickType_t ticks) { now_us += (int64_t)ticks * 1000; }

struct sim_semaphore { int count; };
static struct sim_semaphore semaphore;
SemaphoreHandle_t xSemaphoreCreateBinary(void) { semaphore.count = 0; return &semaphore; }
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t wait) { if (s->count) s->count--; return pdTRUE; }
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t s, BaseType_t *woken) { s->count = 1; return pdTRUE; }
void *heap_caps_malloc(size_t size, uint32_t caps) { return malloc(size); }
size_t heap_caps_get_free_size(uint32_t caps) { return 100000; }

uint32_t esp_rom_crc32_le(uint32_t crc, const uint8_t *buf, uint32_t len) {
    crc = ~crc;
    while (len--) {
        crc ^= *buf++;
        for (int k = 0; k < 8; k++) crc = crc & 1 ? (crc >> 1) ^ 0xedb88320u : crc >> 1;
    }
    return ~crc;
}

/* Host serial output, collected for tests and tools. */
static uint8_t serial_out[1 << 20];
static size_t serial_length;
bool burst_serial_send(const void *data, size_t size) {
    if (serial_length + size > sizeof(serial_out)) return false;
    memcpy(serial_out + serial_length, data, size);
    serial_length += size;
    return true;
}

/* --- Panel (ILI9341 command subset) ----------------------------------- */
struct sim_panel_io { esp_lcd_panel_io_color_trans_done_cb_t done; void *ctx; };
static struct sim_panel_io panel_io;
static uint16_t gram[H][W];
static int col0, col1, row0, row1, cur_x, cur_y, madctl, inverted;
static int tfa, vsa = H, bfa, ssa;
static unsigned pixels_written;

esp_err_t spi_bus_initialize(spi_host_device_t host, const spi_bus_config_t *config, int dma) { return ESP_OK; }
esp_err_t esp_lcd_new_panel_io_spi(esp_lcd_spi_bus_handle_t bus, const esp_lcd_panel_io_spi_config_t *config,
                                   esp_lcd_panel_io_handle_t *io) {
    panel_io.done = config->on_color_trans_done;
    panel_io.ctx = config->user_ctx;
    *io = &panel_io;
    return ESP_OK;
}

esp_err_t esp_lcd_panel_io_tx_param(esp_lcd_panel_io_handle_t io, int cmd, const void *param, size_t size) {
    const uint8_t *p = param;
    switch (cmd) {
    case 0x2a: col0 = p[0] << 8 | p[1]; col1 = p[2] << 8 | p[3]; break;
    case 0x2b: row0 = p[0] << 8 | p[1]; row1 = p[2] << 8 | p[3]; break;
    case 0x36: madctl = p[0]; break;
    case 0x20: inverted = 0; break;
    case 0x21: inverted = 1; break;
    case 0x33: tfa = p[0] << 8 | p[1]; vsa = p[2] << 8 | p[3]; bfa = p[4] << 8 | p[5]; break;
    case 0x37: ssa = p[0] << 8 | p[1]; break;
    default: break;
    }
    return ESP_OK;
}

esp_err_t esp_lcd_panel_io_tx_color(esp_lcd_panel_io_handle_t io, int cmd, const void *color, size_t size) {
    const uint8_t *b = color;
    if (cmd == 0x2c) { cur_x = col0; cur_y = row0; }
    for (size_t k = 0; k + 1 < size; k += 2) {
        if (cur_y >= 0 && cur_y < H && cur_x >= 0 && cur_x < W) {
            int x = madctl & 0x40 ? W - 1 - cur_x : cur_x;
            gram[cur_y][x] = (uint16_t)(b[k] << 8 | b[k + 1]);
        }
        pixels_written++;
        if (++cur_x > col1) { cur_x = col0; if (++cur_y > row1) cur_y = row0; }
    }
    if (panel_io.done) panel_io.done(io, NULL, panel_io.ctx);
    return ESP_OK;
}

/* RAMRD (0x2e): a dummy byte, then RGB666 bytes (6 bits in 7..2) from the
 * window start, as the ILI9341 reports them. */
esp_err_t esp_lcd_panel_io_rx_param(esp_lcd_panel_io_handle_t io, int cmd, void *param, size_t size) {
    uint8_t *out = param;
    memset(param, 0, size);
    if (cmd != 0x2e) return ESP_OK;
    int x = col0, y = row0;
    for (size_t k = 1; k + 2 < size + 1 && k + 2 <= size; k += 3) {
        int px = madctl & 0x40 ? W - 1 - x : x;
        uint16_t v = y < H && x < W ? gram[y][px] : 0;
        out[k] = (uint8_t)((v >> 11 & 31) << 3);
        out[k + 1] = (uint8_t)((v >> 5 & 63) << 2);
        out[k + 2] = (uint8_t)((v & 31) << 3);
        if (++x > col1) { x = col0; y++; }
    }
    return ESP_OK;
}

/* Screen row y shows GRAM row: fixed top, scrolled middle, fixed bottom. */
static int gram_row(int y) {
    if (y < tfa || y >= tfa + vsa) return y;
    return tfa + ((y - tfa) + (ssa - tfa) % vsa + vsa) % vsa;
}

/* --- Touch (XPT2046 over bit-banged GPIO) ------------------------------ */
#define PIN_T_CLK 25
#define PIN_T_MOSI 32
#define PIN_T_MISO 39
#define PIN_T_CS 33
#define PIN_T_IRQ 36
static int touching, raw_x, raw_y;
static int t_cs = 1, t_clk, t_mosi, t_miso, t_bits, t_cmd;
static uint32_t t_resp;

esp_err_t gpio_config(const gpio_config_t *config) { return ESP_OK; }
esp_err_t gpio_set_direction(int pin, gpio_mode_t mode) { return ESP_OK; }

esp_err_t gpio_set_level(int pin, uint32_t level) {
    if (pin == PIN_T_CS) { t_cs = level; if (level) t_bits = 0; }
    else if (pin == PIN_T_MOSI) t_mosi = level;
    else if (pin == PIN_T_CLK) {
        bool rising = level && !t_clk;
        t_clk = level;
        if (rising && !t_cs) {
            if (t_bits < 8) {
                t_cmd = (t_cmd << 1 | t_mosi) & 0xff;
                if (++t_bits == 8) {
                    int value = t_cmd == 0xd0 ? raw_x : t_cmd == 0x90 ? raw_y : 0;
                    t_resp = (uint32_t)(value & 0xfff) << 3; /* busy bit 15 = 0 */
                }
            } else {
                t_miso = t_resp >> 15 & 1;
                t_resp = t_resp << 1 & 0xffff;
                if (++t_bits == 24) t_bits = 0;
            }
        }
    }
    return ESP_OK;
}

int gpio_get_level(int pin) {
    if (pin == PIN_T_IRQ) return touching ? 0 : 1;
    if (pin == PIN_T_MISO) return t_miso;
    return 0;
}

/* --- NVS --------------------------------------------------------------- */
static uint8_t nvs_blob[64];
static size_t nvs_length;
esp_err_t nvs_open(const char *name, nvs_open_mode_t mode, nvs_handle_t *h) { *h = 1; return ESP_OK; }
esp_err_t nvs_get_blob(nvs_handle_t h, const char *key, void *out, size_t *length) {
    if (!nvs_length || *length < nvs_length) return -1;
    memcpy(out, nvs_blob, nvs_length);
    *length = nvs_length;
    return ESP_OK;
}
esp_err_t nvs_set_blob(nvs_handle_t h, const char *key, const void *value, size_t length) {
    if (length > sizeof(nvs_blob)) return -1;
    memcpy(nvs_blob, value, length);
    nvs_length = length;
    return ESP_OK;
}
esp_err_t nvs_commit(nvs_handle_t h) { return ESP_OK; }
void nvs_close(nvs_handle_t h) {}

/* --- Radio -------------------------------------------------------------- */
static unsigned lo_mhz = 2412, gain = 40, filter_mhz;
static bool agc = true, ble_source = true;
static uint32_t words[16384];
static uint64_t rng = 0x9e3779b97f4a7c15ull;
static unsigned acquisitions;

static double noise(void) {
    rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
    return ((double)(rng & 0xffff) / 65535.0 - 0.5) * 2.0;
}

static uint32_t pack(double i, double q) {
    int a = (int)lround(i), b = (int)lround(q);
    a = a < -512 ? -512 : a > 511 ? 511 : a;
    b = b < -512 ? -512 : b > 511 ? 511 : b;
    return (uint32_t)(a & 0x3ff) | (uint32_t)(b & 0x3ff) << 10;
}

/* Apparent carriers on this board (MHz): BLE ch37 2404.3, ch38 2419.1 (from
 * sessions 004/005); a Wi-Fi AP on channel 1; a CW spur at 2440. */
static void synthesize(unsigned n, double rate_hz) {
    double t0 = (double)now_us * 1e-6;
    double scale = agc ? 1.0 : gain / 40.0;
    for (unsigned k = 0; k < n; k++) {
        double t = t0 + k / rate_hz, i = 6 * noise(), q = 6 * noise();
        struct { double mhz, amp, period, length; bool on; } carriers[] = {
            {2404.3, 120, 0.0247, 184e-6, ble_source},
            {2419.1, 90, 0.0313, 184e-6, true},
            {2440.0, 25, 1, 1, true},
        };
        for (unsigned c = 0; c < sizeof(carriers) / sizeof(carriers[0]); c++) {
            if (!carriers[c].on || fmod(t, carriers[c].period) > carriers[c].length) continue;
            double off = (carriers[c].mhz - lo_mhz) * 1e6;
            if (fabs(off) >= rate_hz / 2) continue;
            double ph = 2 * M_PI * off * t;
            i += carriers[c].amp * cos(ph);
            q += carriers[c].amp * sin(ph);
        }
        /* Wi-Fi channel 1: ~18 MHz of tones, 2 ms bursts every 20 ms. */
        if (fmod(t, 0.02) < 0.002) {
            for (int s = -8; s <= 8; s++) {
                double off = (2412.0 + s - lo_mhz) * 1e6;
                if (fabs(off) >= rate_hz / 2) continue;
                double ph = 2 * M_PI * off * t + s * 1.7;
                i += 14 * cos(ph);
                q += 14 * sin(ph);
            }
        }
        words[k] = pack(i * scale, q * scale);
    }
}

static bool acquire(unsigned n, unsigned span, const uint32_t **out) {
    static const double rates[3] = {16e6, 40e6, 80e6};
    if (span > 2 || n > 16380) return false;
    synthesize(n, rates[span]);
    now_us += (int64_t)(n / rates[span] * 1e6) + 200;
    acquisitions++;
    *out = words;
    return true;
}
static bool tune(unsigned mhz) { if (mhz < 100 || mhz > 6000) return false; lo_mhz = mhz; return true; }
static unsigned frequency(void) { return lo_mhz; }
static void set_gain(bool hardware, unsigned code) { agc = hardware; if (code <= 72) gain = code; }
static bool hardware_agc(void) { return agc; }
static unsigned gain_code(void) { return gain; }
static unsigned gain_max(void) { return 72; }
static bool set_filter(unsigned mhz) { filter_mhz = mhz; return true; }
static const cyd_radio_t radio = {acquire, tune, frequency, set_gain, hardware_agc, gain_code, gain_max, set_filter};

/* --- API for tools/cyd_sim.py ------------------------------------------ */
void sim_boot(void) { cyd_display_init(&radio); }
void sim_run_ms(int ms) {
    int64_t end = now_us + (int64_t)ms * 1000;
    while (now_us < end) { cyd_display_idle(); vTaskDelay(1); }
}
/* Press at a screen point (inverse of the firmware's baked calibration). */
void sim_touch(int x, int y, int hold_ms) {
    raw_x = 3491 + (x - 20) * (537 - 3491) / 200;
    raw_y = 470 + (y - 20) * (3636 - 470) / 280;
    touching = 1;
    sim_run_ms(hold_ms);
    touching = 0;
    sim_run_ms(150);
}
void sim_hold_touch_at_boot(int on) { touching = on; raw_x = 2000; raw_y = 2000; }
void sim_host_line(void) { cyd_display_host_activity(); }
void sim_set_ble_source(int on) { ble_source = on; }
unsigned sim_frequency(void) { return lo_mhz; }
unsigned sim_acquisitions(void) { return acquisitions; }
unsigned sim_pixels_written(void) { return pixels_written; }
int sim_agc(void) { return agc; }
unsigned sim_gain(void) { return gain; }
unsigned sim_filter(void) { return filter_mhz; }
/* Composited screen as RGB565, row-major 240x320. */
void sim_screen(uint16_t *out) {
    for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++) {
            uint16_t v = gram[gram_row(y)][x];
            out[y * W + x] = inverted ? (uint16_t)~v : v;
        }
}
/* Test hook: change the radio as a host FREQ would, without the display. */
void sim_tune_for_test(unsigned mhz) { lo_mhz = mhz; }
/* Host command as the receiver loop would deliver it; returns true when the
 * display consumed it. Output accumulates for sim_serial_take. */
int sim_host_command(const char *line) {
    if (cyd_display_host_line(line)) return 1;
    cyd_display_host_activity();
    return 0;
}
size_t sim_serial_take(uint8_t *out, size_t capacity) {
    size_t n = serial_length < capacity ? serial_length : capacity;
    memcpy(out, serial_out, n);
    memmove(serial_out, serial_out + n, serial_length - n);
    serial_length -= n;
    return n;
}

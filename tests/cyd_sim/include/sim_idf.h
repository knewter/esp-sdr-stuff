/* Minimal ESP-IDF surface used by cyd_display.c, implemented by sim.c on the
 * host. Only what the display code calls; behaviour is emulated, not linked. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

#define IRAM_ATTR
#define BIT64(n) (1ULL << (n))
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERROR_CHECK(x) ((void)(x))

/* FreeRTOS */
typedef int BaseType_t;
typedef uint32_t TickType_t;
#define pdFALSE 0
#define pdTRUE 1
#define portMAX_DELAY 0xffffffffu
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
typedef struct sim_semaphore *SemaphoreHandle_t;
SemaphoreHandle_t xSemaphoreCreateBinary(void);
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t wait);
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t s, BaseType_t *woken);
void vTaskDelay(TickType_t ticks);

/* Timer and ROM */
int64_t esp_timer_get_time(void);
void esp_rom_delay_us(uint32_t us);

/* Heap */
#define MALLOC_CAP_DMA 0
void *heap_caps_malloc(size_t size, uint32_t caps);
size_t heap_caps_get_free_size(uint32_t caps);

/* ROM CRC (zlib-compatible) and the ESP-SDR serial transport. */
uint32_t esp_rom_crc32_le(uint32_t crc, const uint8_t *buf, uint32_t len);
bool burst_serial_send(const void *data, size_t size);

/* GPIO */
typedef enum { GPIO_MODE_INPUT = 1, GPIO_MODE_OUTPUT = 2 } gpio_mode_t;
typedef struct { uint64_t pin_bit_mask; gpio_mode_t mode; } gpio_config_t;
esp_err_t gpio_config(const gpio_config_t *config);
esp_err_t gpio_set_direction(int pin, gpio_mode_t mode);
esp_err_t gpio_set_level(int pin, uint32_t level);
int gpio_get_level(int pin);

/* SPI bus */
typedef enum { SPI2_HOST = 1 } spi_host_device_t;
#define SPI_DMA_CH_AUTO 3
typedef struct {
    int sclk_io_num, mosi_io_num, miso_io_num, quadwp_io_num, quadhd_io_num, max_transfer_sz;
} spi_bus_config_t;
esp_err_t spi_bus_initialize(spi_host_device_t host, const spi_bus_config_t *config, int dma);

/* esp_lcd panel IO */
typedef struct sim_panel_io *esp_lcd_panel_io_handle_t;
typedef void *esp_lcd_spi_bus_handle_t;
typedef struct { int unused; } esp_lcd_panel_io_event_data_t;
typedef bool (*esp_lcd_panel_io_color_trans_done_cb_t)(esp_lcd_panel_io_handle_t, esp_lcd_panel_io_event_data_t *, void *);
typedef struct {
    int cs_gpio_num, dc_gpio_num, spi_mode;
    unsigned pclk_hz;
    size_t trans_queue_depth;
    esp_lcd_panel_io_color_trans_done_cb_t on_color_trans_done;
    void *user_ctx;
    int lcd_cmd_bits, lcd_param_bits;
} esp_lcd_panel_io_spi_config_t;
esp_err_t esp_lcd_new_panel_io_spi(esp_lcd_spi_bus_handle_t bus, const esp_lcd_panel_io_spi_config_t *config,
                                   esp_lcd_panel_io_handle_t *io);
esp_err_t esp_lcd_panel_io_tx_param(esp_lcd_panel_io_handle_t io, int cmd, const void *param, size_t size);
esp_err_t esp_lcd_panel_io_tx_color(esp_lcd_panel_io_handle_t io, int cmd, const void *color, size_t size);
esp_err_t esp_lcd_panel_io_rx_param(esp_lcd_panel_io_handle_t io, int cmd, void *param, size_t size);

/* NVS */
typedef uint32_t nvs_handle_t;
typedef enum { NVS_READONLY, NVS_READWRITE } nvs_open_mode_t;
esp_err_t nvs_open(const char *name, nvs_open_mode_t mode, nvs_handle_t *handle);
esp_err_t nvs_get_blob(nvs_handle_t handle, const char *key, void *out, size_t *length);
esp_err_t nvs_set_blob(nvs_handle_t handle, const char *key, const void *value, size_t length);
esp_err_t nvs_commit(nvs_handle_t handle);
void nvs_close(nvs_handle_t handle);

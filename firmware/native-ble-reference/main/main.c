/* Passive owned-marker source reference. No SDR or transmitted-event claims. */
#include <inttypes.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "nvs_flash.h"

int native_privacy_crypto_selftest(void);

#define VERSION "native-ble-ref-v2"
#define SCAN_MS 90000
static const uint8_t owned_ad[] = {0x0f,0xff,0xff,0xff,0x45,0x53,0x50,0x2d,
                                 0x53,0x44,0x52,0x2d,0x45,0x56,0x41,0x4c};
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static volatile bool synced, failed, finalized, unexpected_complete;
static int complete_reason, stop_status;
static bool stopped_active = true;
static int64_t started_us, finished_us, interval_start_us;
static uint32_t total, bucket, rssi_known;
static int64_t rssi_sum;
static int rssi_min = 127, rssi_max = -128;
static uint32_t sequence;
static char nonce[17];

static void error(const char *stage, int code) {
    failed = true;
    printf("{\"schema\":1,\"kind\":\"ERROR\",\"version\":\"" VERSION "\","
           "\"stage\":\"%s\",\"code\":%d}\n", stage, code);
    fflush(stdout);
}

static bool exact_owned(const uint8_t *data, unsigned length) {
    for (unsigned offset = 0; offset < length;) {
        unsigned size = data[offset];
        if (!size || offset + size + 1 > length) return false;
        if (size + 1 == sizeof owned_ad && !memcmp(data + offset, owned_ad, sizeof owned_ad)) return true;
        offset += size + 1;
    }
    return false;
}

static int gap_event(struct ble_gap_event *event, void *unused) {
    (void) unused;
    if (event->type == BLE_GAP_EVENT_DISC) {
        /* Foreign AD and all addresses are discarded before any output. */
        if (!exact_owned(event->disc.data, event->disc.length_data)) return 0;
        portENTER_CRITICAL(&mux);
        if (finalized) { portEXIT_CRITICAL(&mux); return 0; }
        if (total == UINT32_MAX || bucket == UINT32_MAX) failed = true;
        else { total++; bucket++; }
        int rssi = event->disc.rssi;
        if (rssi >= -127 && rssi <= 20) {
            rssi_known++; rssi_sum += rssi;
            if (rssi < rssi_min) rssi_min = rssi;
            if (rssi > rssi_max) rssi_max = rssi;
        }
        portEXIT_CRITICAL(&mux);
    } else if (event->type == BLE_GAP_EVENT_DISC_COMPLETE) {
        portENTER_CRITICAL(&mux);
        /* cancel() does not synthesize DISC_COMPLETE. Any such event is an
         * unexpected end, never the acknowledged application-stop receipt. */
        complete_reason = event->disc_complete.reason; unexpected_complete = true;
        portEXIT_CRITICAL(&mux);
    }
    return 0;
}

static void on_sync(void) { synced = true; }
static void on_reset(int code) { error("CONTROLLER_RESET", code); }
static void host_task(void *unused) {
    (void) unused;
    nimble_port_run();
    nimble_port_freertos_deinit();
}

static void config(void) {
    printf("{\"schema\":1,\"kind\":\"CONFIG\",\"version\":\"" VERSION "\","
           "\"completion_mode\":\"application_cancel\",\"scan_ms\":90000,\"passive\":true,\"filter_duplicates\":false,"
           "\"interval_units\":160,\"window_units\":160,\"uart_baud\":115200,"
           "\"owned_ad_hex\":\"0fffffff4553502d5344522d4556414c\"}\n");
    fflush(stdout);
}

static bool wait_start(void) {
    char command[24]; unsigned used = 0;
    int64_t deadline = esp_timer_get_time() + 30000000;
    int64_t next_config = 0;
    while (!failed && esp_timer_get_time() < deadline) {
        if (synced && esp_timer_get_time() >= next_config) {
            config(); next_config = esp_timer_get_time() + 1000000;
        }
        uint8_t value;
        int read = uart_read_bytes(UART_NUM_0, &value, 1, pdMS_TO_TICKS(50));
        if (read < 0) { error("UART", read); return false; }
        if (!read) continue;
        if (value == '\n') {
            command[used] = 0;
            if (!synced || used != 22 || memcmp(command,"START ",6)) {
                error("COMMAND", -1); return false;
            }
            for (unsigned n = 6; n < 22; n++) {
                if (!((command[n] >= '0' && command[n] <= '9') ||
                      (command[n] >= 'a' && command[n] <= 'f'))) {
                    error("COMMAND", -2); return false;
                }
            }
            memcpy(nonce,command+6,16); nonce[16] = 0; return true;
        }
        if (value < 32 || value > 126 || used >= 22) {
            error("COMMAND", -3); return false;
        }
        command[used++] = value;
    }
    if (!failed) error("START_TIMEOUT", -1);
    return false;
}

static void emit_bucket(bool terminal) {
    uint32_t count, cumulative, known; int64_t sum, end;
    int minimum, maximum;
    portENTER_CRITICAL(&mux);
    if (!terminal && finalized) { portEXIT_CRITICAL(&mux); return; }
    end = terminal ? finished_us : esp_timer_get_time();
    count = bucket; cumulative = total; known = rssi_known;
    sum = rssi_sum; minimum = rssi_min; maximum = rssi_max;
    bucket = rssi_known = 0; rssi_sum = 0; rssi_min = 127; rssi_max = -128;
    portEXIT_CRITICAL(&mux);
    printf("{\"schema\":1,\"kind\":\"%s\",\"version\":\"" VERSION "\","
           "\"nonce\":\"%s\",\"sequence\":%" PRIu32 ","
           "\"interval_start_us\":%" PRId64 ",\"interval_end_us\":%" PRId64 ","
           "\"owned_interval\":%" PRIu32 ",\"owned_total\":%" PRIu32 ","
           "\"rssi_known\":%" PRIu32 ",\"rssi_sum\":%" PRId64 ",",
           terminal ? "END" : "AGG",nonce,++sequence,interval_start_us,end,
           count,cumulative,known,sum);
    if (known) printf("\"rssi_min\":%d,\"rssi_max\":%d",minimum,maximum);
    else printf("\"rssi_min\":null,\"rssi_max\":null");
    if (terminal) printf(",\"completion_mode\":\"application_cancel\",\"cancel_status\":%d,"
                         "\"scan_active_after_stop\":%s,\"elapsed_us\":%" PRId64 ",\"scan_ms\":%d",
                         stop_status,stopped_active ? "true" : "false",end-started_us,SCAN_MS);
    puts("}"); fflush(stdout); interval_start_us = end;
}

void app_main(void) {
    esp_log_level_set("*",ESP_LOG_NONE);
    uart_config_t uart = {.baud_rate=115200,.data_bits=UART_DATA_8_BITS,
        .parity=UART_PARITY_DISABLE,.stop_bits=UART_STOP_BITS_1,
        .flow_ctrl=UART_HW_FLOWCTRL_DISABLE,.source_clk=UART_SCLK_DEFAULT};
    esp_err_t result = uart_param_config(UART_NUM_0,&uart);
    if (result == ESP_OK) result = uart_set_pin(UART_NUM_0,1,3,UART_PIN_NO_CHANGE,UART_PIN_NO_CHANGE);
    if (result == ESP_OK) result = uart_driver_install(UART_NUM_0,256,0,0,NULL,0);
    if (result != ESP_OK) { error("UART",result); return; }
    int crypto = native_privacy_crypto_selftest();
    if (crypto) { error("CRYPTO_SELFTEST",crypto); return; }
    /* No erase/retry: initialization failure is inert and retained. */
    result = nvs_flash_init();
    if (result != ESP_OK) { error("NVS",result); return; }
    result = nimble_port_init();
    if (result != ESP_OK) { error("NIMBLE",result); return; }
    ble_hs_cfg.sync_cb = on_sync; ble_hs_cfg.reset_cb = on_reset;
    nimble_port_freertos_init(host_task);
    if (!wait_start()) return;
    struct ble_gap_disc_params params = {0};
    params.passive = 1; params.filter_duplicates = 0;
    params.itvl = 160; params.window = 160;
    started_us = interval_start_us = esp_timer_get_time();
    int rc = ble_gap_disc(BLE_OWN_ADDR_PUBLIC,SCAN_MS,&params,gap_event,NULL);
    if (rc) { error("SCAN",rc); return; }
    printf("{\"schema\":1,\"kind\":\"READY\",\"version\":\"" VERSION "\","
           "\"nonce\":\"%s\",\"scan_start_us\":%" PRId64 ",\"scan_status\":0}\n",
           nonce,started_us); fflush(stdout);
    /* The pinned observer-only SDK compiles out ble_gap_timer dispatch under
     * NIMBLE_BLE_CONNECT. Do not enable connection roles or patch the SDK:
     * cancel the unchanged passive scan explicitly after 90s on the ESP clock. */
    int64_t next_bucket = started_us + 1000000;
    for (;;) {
        if (failed) {
            if (ble_gap_disc_active()) ble_gap_disc_cancel();
            error("COUNTER_OR_RESET",-1); return;
        }
        if (unexpected_complete) { error("UNEXPECTED_COMPLETE",complete_reason); return; }
        if (!ble_gap_disc_active()) { error("SCAN_INACTIVE",-1); return; }
        int64_t now = esp_timer_get_time();
        if (now-started_us >= 90000000) break;
        if (now >= next_bucket) {
            emit_bucket(false); next_bucket = now + 1000000;
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    int cancel_status = ble_gap_disc_cancel();
    int active_after_stop = ble_gap_disc_active();
    int64_t stopped_us = esp_timer_get_time();
    if (cancel_status) { error("SCAN_CANCEL",cancel_status); return; }
    if (active_after_stop) { error("SCAN_STILL_ACTIVE",active_after_stop); return; }
    if (stopped_us-started_us < 90000000 || stopped_us-started_us > 92000000) {
        error("SCAN_TIME_OVERRUN",-1); return;
    }
    portENTER_CRITICAL(&mux);
    /* All later queued advertising reports are discarded, so END freezes the
     * same cumulative count/RSSI state protected by the callback critical section. */
    finalized = true; finished_us = esp_timer_get_time();
    stop_status = cancel_status; stopped_active = active_after_stop != 0;
    bool invalid = failed || unexpected_complete;
    bool late = finished_us-started_us > 92000000;
    portEXIT_CRITICAL(&mux);
    if (invalid) { error("COUNTER_OR_RESET",-1); return; }
    if (late) { error("SCAN_TIME_OVERRUN",-1); return; }
    emit_bucket(true);
    nimble_port_stop(); nimble_port_deinit();
}

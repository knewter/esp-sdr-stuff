/* SPDX-License-Identifier: GPL-3.0-only
 * Bounded read-only observation; included inside the original ESP32 backend.
 * RX_GAIN is intentionally interpreted only as the field apply_gain writes.
 */
#pragma once
#include <stddef.h>

#define REGOBS_LIMIT 81u
#define REGOBS_CAPTURES 20u
#define REGOBS_LINE_LIMIT 2048u
#define REGOBS_VERSION "regobs-v1"
#define REGOBS_PROFILE "esp32-register-observation-v1"
typedef enum { REGOBS_NEW, REGOBS_ARMED, REGOBS_FAILED, REGOBS_DONE } regobs_state_t;
typedef enum { REGOBS_POST_SETTINGS, REGOBS_BEFORE_ACQUIRE, REGOBS_ARMED_BEFORE_TRIGGER,
    REGOBS_DUMP_COMPLETE, REGOBS_RESTORED_AFTER_DUMP } regobs_stage_t;
typedef struct {
    int64_t read_begin_us, read_end_us;
    uint16_t sequence;
    int8_t capture_ordinal;
    uint8_t stage, selector, bit23;
    uint32_t hook_cycles;
} regobs_record_t;
_Static_assert(sizeof(regobs_record_t) == 32, "Observation record differs from declared 32-byte ABI");

/* External symbols are deliberate: ELF/map validation checks entire buffers. */
regobs_record_t regobs_records[REGOBS_LIMIT];
char regobs_json[REGOBS_LINE_LIMIT];
char regobs_wire[REGOBS_LINE_LIMIT];
static regobs_state_t regobs_state;
static unsigned regobs_used, regobs_captures;
static bool regobs_in_capture, regobs_transfer_started, regobs_wire_broken;
static const char *regobs_error;
static char regobs_nonce[33];
static int64_t regobs_start_us, regobs_deadline_us;
static int regobs_completion = -1, regobs_count = -1, regobs_elapsed = -1;
static uint32_t regobs_payload_crc;

/* Separate non-inlined body makes its entry/return observable inside the
 * wrapper's cycle bracket; the compiled target must be reviewed as well. */
static __attribute__((noinline)) regobs_record_t *regobs_observe_body(regobs_stage_t stage) {
    if (!regobs_in_capture && stage != REGOBS_POST_SETTINGS) return NULL;
    if (regobs_used >= REGOBS_LIMIT) { regobs_error = "record_capacity"; return NULL; }
    regobs_record_t *record = &regobs_records[regobs_used];
    record->read_begin_us = esp_timer_get_time();
    uint32_t word = REG_READ(RX_GAIN);
    record->read_end_us = esp_timer_get_time();
    record->sequence = regobs_used++;
    record->capture_ordinal = stage == REGOBS_POST_SETTINGS ? -1 : (int8_t)regobs_captures;
    record->stage = stage;
    record->selector = (word >> 24) & 127;
    record->bit23 = (word >> 23) & 1;
    return record;
}

static void regobs_observe(regobs_stage_t stage) {
    /* Full body call: prechecks, pointer lookup, both timers, MMIO, original
     * field stores and body entry/return. Counter/delta publication and the
     * wrapper/callsite overhead are residual, not zero-cost instrumentation. */
    __asm__ __volatile__("" ::: "memory");
    uint32_t cycles_begin = esp_cpu_get_cycle_count();
    __asm__ __volatile__("" ::: "memory");
    regobs_record_t *record = regobs_observe_body(stage);
    __asm__ __volatile__("" ::: "memory");
    uint32_t cycles_end = esp_cpu_get_cycle_count();
    __asm__ __volatile__("" ::: "memory");
    if (record) record->hook_cycles = cycles_end-cycles_begin;
}

static bool regobs_append(size_t *used, const char *format, ...) {
    if (*used >= sizeof(regobs_json)) return false;
    va_list args; va_start(args, format);
    int n = vsnprintf(regobs_json+*used, sizeof(regobs_json)-*used, format, args);
    va_end(args);
    if (n < 0 || (size_t)n >= sizeof(regobs_json)-*used) return false;
    *used += n; return true;
}

static bool regobs_common(size_t *used, const char *kind) {
    *used = 0;
    return regobs_append(used, "{\"schema\":1,\"kind\":\"%s\",\"nonce\":\"%s\",\"revision\":\"" REGOBS_VERSION "\"", kind, regobs_nonce);
}

static bool regobs_write_records(size_t *used, unsigned first) {
    static const char *const names[] = {"post_settings", "before_acquire", "armed_before_trigger", "dump_complete", "restored_after_dump"};
    if (first > regobs_used || regobs_used > REGOBS_LIMIT || !regobs_append(used, ",\"records\":[")) return false;
    for (unsigned i = first; i < regobs_used; i++) {
        const regobs_record_t *r = &regobs_records[i];
        if (r->stage > REGOBS_RESTORED_AFTER_DUMP) return false;
        if (!regobs_append(used, "%s{\"sequence\":%u,\"capture_ordinal\":", i == first ? "" : ",", r->sequence)) return false;
        if (r->capture_ordinal < 0) { if (!regobs_append(used, "null")) return false; }
        else if (!regobs_append(used, "%d", r->capture_ordinal)) return false;
        if (!regobs_append(used, ",\"stage\":\"%s\",\"read_begin_us\":%"PRId64",\"read_end_us\":%"PRId64",\"selector\":%u,\"bit23\":%u,\"hook_cycles\":%"PRIu32"}",
            names[r->stage], r->read_begin_us, r->read_end_us, r->selector, r->bit23, r->hook_cycles)) return false;
    }
    return regobs_append(used, "]}");
}

static bool regobs_send_json(size_t used) {
    uint32_t crc = esp_rom_crc32_le(0, (const uint8_t *)regobs_json, used);
    int length = snprintf(regobs_wire, sizeof(regobs_wire), "REGOBS1 %08"PRIx32" %s\n", crc, regobs_json);
    if (length < 0 || (size_t)length >= sizeof(regobs_wire)) return false;
    return burst_serial_send(regobs_wire, length);
}

static bool regobs_capture_receipt(unsigned first) {
    size_t n;
    return regobs_common(&n, "capture") &&
        regobs_append(&n, ",\"capture_ordinal\":%u,\"completion\":true,\"returned_samples\":%d,\"payload_bytes\":40950,\"payload_crc32\":\"%08"PRIx32"\",\"capture_elapsed_us\":%d",
            regobs_captures, regobs_count, regobs_payload_crc, regobs_elapsed) &&
        regobs_write_records(&n, first) && regobs_send_json(n);
}

/* Only called where binary transmission has not begun, or completed fully. */
static void regobs_failed(const char *kind, unsigned first) {
    regobs_state = REGOBS_FAILED;
    if (!regobs_in_capture) regobs_completion = regobs_count = regobs_elapsed = -1;
    reply("ERR REGOBS1 %s\n", kind);
    size_t n;
    if (!regobs_common(&n, "failed") || !regobs_append(&n, ",\"failure_kind\":\"%s\",\"capture_ordinal\":", kind)) return;
    if (!regobs_in_capture) {
        if (!regobs_append(&n, "null")) return;
    } else if (!regobs_append(&n, "%u", regobs_captures)) return;
    if (!regobs_append(&n, ",\"completion\":%s,\"returned_samples\":", regobs_completion < 0 ? "null" : regobs_completion ? "true" : "false")) return;
    if (regobs_count < 0) { if (!regobs_append(&n, "null")) return; }
    else if (!regobs_append(&n, "%d", regobs_count)) return;
    if (!regobs_append(&n, ",\"capture_elapsed_us\":")) return;
    if (regobs_elapsed < 0) { if (!regobs_append(&n, "null")) return; }
    else if (!regobs_append(&n, "%d", regobs_elapsed)) return;
    if (!regobs_write_records(&n, first) || !regobs_send_json(n)) regobs_wire_broken = true;
}

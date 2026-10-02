/* SPDX-License-Identifier: GPL-3.0-only */
#pragma once

static bool regobs_valid_nonce(const char *nonce) {
    if (strlen(nonce) != 32) return false;
    for (unsigned i = 0; i < 32; i++) if (!((nonce[i] >= '0' && nonce[i] <= '9') || (nonce[i] >= 'a' && nonce[i] <= 'f'))) return false;
    return true;
}

/* The common parser consumes BAUD commands before receiver.command(). This
 * hook is linked only into the diagnostic copy and runs before that consumer. */
bool regobs_transport_guard(const char *line) {
    if (regobs_wire_broken) return true;
    if (regobs_state == REGOBS_NEW || strncmp(line, "BAUD", 4)) return false;
    if (regobs_state == REGOBS_ARMED) regobs_failed("session_state", regobs_used);
    else reply("ERR REGOBS1 session_state\n");
    return true;
}

static bool regobs_command(const char *line) {
    if (regobs_wire_broken) return true;
    const char *begin = "REGOBS1 BEGIN ", *end = "REGOBS1 END ";
    if (!strncmp(line, begin, strlen(begin))) {
        const char *nonce = line+strlen(begin);
        if (regobs_state != REGOBS_NEW || !regobs_valid_nonce(nonce) || frequency_mhz != 2401 || rx_filter != 64 || hardware_agc || gain_code != 48 || burst_serial_baud() != 921600) {
            if (regobs_state == REGOBS_ARMED) regobs_failed("session_state", regobs_used);
            else {
                if (regobs_state == REGOBS_NEW && regobs_valid_nonce(nonce)) memcpy(regobs_nonce, nonce, 33);
                regobs_failed("session_state", regobs_used);
            }
            return true;
        }
        memcpy(regobs_nonce, nonce, 33);
        regobs_start_us = esp_timer_get_time(); regobs_deadline_us = regobs_start_us+30000000;
        regobs_state = REGOBS_ARMED;
        regobs_observe(REGOBS_POST_SETTINGS);
        size_t n;
        if (!(regobs_common(&n, "config") && regobs_append(&n,
            ",\"profile\":\"" REGOBS_PROFILE "\",\"settings\":{\"frequency_mhz\":2401,\"bandwidth_mhz\":20,\"filter_code\":64,\"gain_mode\":\"MANUAL\",\"gain_selector\":48},\"rate_hz\":16000000,\"bits\":10,\"samples\":16380,\"captures\":20,\"record_limit\":81,\"start_us\":%"PRId64, regobs_start_us) &&
            regobs_write_records(&n, 0) && regobs_send_json(n))) { regobs_state = REGOBS_FAILED; regobs_wire_broken = true; }
        return true;
    }
    if (regobs_state == REGOBS_ARMED) {
        if (esp_timer_get_time() >= regobs_deadline_us) { regobs_failed("session_deadline", regobs_used); return true; }
        if (!strcmp(line, "CAP20 16380 6")) {
            if (regobs_captures >= REGOBS_CAPTURES) { regobs_failed("session_state", regobs_used); return true; }
            if (regobs_used > REGOBS_LIMIT-4) { regobs_failed("record_capacity", regobs_used); return true; }
            unsigned first = regobs_used;
            regobs_in_capture = true; regobs_transfer_started = false; regobs_error = NULL;
            regobs_completion = regobs_count = regobs_elapsed = -1;
            bool ok = capture_rate(16380, 6, 10);
            if (!ok) {
                if (!regobs_transfer_started) regobs_failed(regobs_error ? regobs_error : "session_state", first);
                else { regobs_state = REGOBS_FAILED; regobs_wire_broken = true; } /* Never append text to partial DATA. */
            } else if (regobs_error || esp_timer_get_time() >= regobs_deadline_us) {
                regobs_failed(regobs_error ? regobs_error : "session_deadline", first);
            } else if (regobs_used != first+4 || !regobs_capture_receipt(first)) { regobs_state = REGOBS_FAILED; regobs_wire_broken = true; }
            else regobs_captures++;
            regobs_in_capture = false;
            return true;
        }
        if (!strncmp(line, end, strlen(end)) && !strcmp(line+strlen(end), regobs_nonce) && regobs_captures == REGOBS_CAPTURES && regobs_used == REGOBS_LIMIT) {
            size_t n; int64_t end_us = esp_timer_get_time();
            bool sent = regobs_common(&n, "end") && regobs_append(&n,
                ",\"status\":\"completed\",\"captures\":20,\"pairs\":327600,\"payload_bytes\":819000,\"record_count\":81,\"start_us\":%"PRId64",\"end_us\":%"PRId64"}", regobs_start_us, end_us) && regobs_send_json(n);
            regobs_state = sent ? REGOBS_DONE : REGOBS_FAILED;
            if (!sent) regobs_wire_broken = true;
            return true;
        }
        regobs_failed("session_state", regobs_used); return true;
    }
    if (regobs_state != REGOBS_NEW && strcmp(line, "INFO") && strcmp(line, "RELEASE")) {
        reply("ERR REGOBS1 session_state\n"); return true;
    }
    if (!strncmp(line, "REGOBS1", 7)) { regobs_state = REGOBS_FAILED; reply("ERR REGOBS1 session_state\n"); return true; }
    return false;
}

# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic, hash-guarded overlay of the pinned original ESP32 backend."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Pinned receiver patch anchor mismatch')
    return text.replace(old, new)


def receiver_text(base=None):
    original = (HERE/'base/receiver.c').read_bytes()
    if base is not None and base != original:
        raise ValueError('Receiver is not the exact pinned original ESP32 backend')
    text = original.decode()
    text = once(text, '#include <stdio.h>', '#ifdef REGOBS_HOST_TEST\n#include "harness_shim.h"\n#else\n#include <stdio.h>')
    text = once(text, '#include "heap_memory_layout.h"', '#include "heap_memory_layout.h"\n#endif')
    text = once(text, 'static uint32_t *const samples = (void *)0x3ffe8000;',
                '#ifdef REGOBS_HOST_TEST\nstatic uint32_t *const samples = test_samples;\n#else\nstatic uint32_t *const samples = (void *)0x3ffe8000;\n#endif')
    text = once(text, '/* Clock selectors:', '#include "register_observation.h"\n\n/* Clock selectors:')
    text = once(text, '    REG_WRITE(DUMP_CTRL, 0);\n    for',
                '    regobs_observe(REGOBS_BEFORE_ACQUIRE);\n    REG_WRITE(DUMP_CTRL, 0);\n    for')
    text = once(text, '    int64_t start = esp_timer_get_time();',
                '    regobs_observe(REGOBS_ARMED_BEFORE_TRIGGER);\n    int64_t start = esp_timer_get_time();')
    text = once(text, '    unsigned elapsed = esp_timer_get_time()-start;',
                '    unsigned elapsed = esp_timer_get_time()-start;\n'
                '    if (regobs_in_capture) { regobs_completion = !!(result & BIT(18)); regobs_count = status & 0x7fff; regobs_elapsed = elapsed; }\n'
                '    regobs_observe(REGOBS_DUMP_COMPLETE);')
    text = once(text, '    filter_restore();\n    if',
                '    filter_restore();\n    regobs_observe(REGOBS_RESTORED_AFTER_DUMP);\n    if')
    text = once(text, '        reply("ERR capture_timeout\\n");',
                '        if (regobs_in_capture) regobs_error = !(result & BIT(18)) ? "capture_timeout" : "capture_count";\n'
                '        else reply("ERR capture_timeout\\n");')
    text = once(text, '            reply("ERR capture_memory %u\\n", j);',
                '            if (regobs_in_capture) regobs_error = "capture_memory";\n'
                '            else reply("ERR capture_memory %u\\n", j);')
    text = once(text, '    return burst_serial_send(header, length) && burst_serial_send(samples, bytes);',
                '    if (regobs_in_capture) { regobs_payload_crc = crc; regobs_transfer_started = true; }\n'
                '    return burst_serial_send(header, length) && burst_serial_send(samples, bytes);')
    text = once(text, 'static void command(const char *line) {',
                '#include "register_commands.h"\n\nstatic void command(const char *line) {\n'
                '    if (regobs_command(line)) return;')
    text = once(text, 'reply("ESP32SDR 6 burst 16380\\n")', 'reply("ESP32REGOBS1 regobs-v1 burst 16380\\n")')
    text = once(text, 'void app_main(void) {', '#ifndef REGOBS_HOST_TEST\nvoid app_main(void) {')
    return text+'\n#endif\n'


def receiver_sha256():
    return hashlib.sha256(receiver_text().encode()).hexdigest()


def transport_text(base=None):
    original=(HERE/'base/burst_serial.c').read_bytes()
    if base is not None and base!=original:
        raise ValueError('Transport is not the exact pinned burst_serial backend')
    text=original.decode()
    text=once(text,'#include "burst_serial.h"',
              '#ifdef REGOBS_HOST_TEST\n#include "transport_shim.h"\n#else\n#include "burst_serial.h"')
    text=once(text,'#ifndef CONFIG_ESP_SDR_UART_BAUD',
              '#endif\nextern bool regobs_transport_guard(const char *line);\n\n#ifndef CONFIG_ESP_SDR_UART_BAUD')
    return once(text,'            if (baud_command(line)) return 0;',
                '            if (regobs_transport_guard(line)) return 0;\n            if (baud_command(line)) return 0;')

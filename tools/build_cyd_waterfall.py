#!/usr/bin/env python3
"""Build the CYD on-screen waterfall variant of ESP-SDR 550fade (no hardware).

Copies a clean, pinned ESP-SDR checkout into a fresh scratch work directory,
adds firmware/cyd-waterfall/src, inserts three exact-match hooks into the
ESP32 receiver, and builds with the 921600-baud UART configuration. The input
checkout and SDK are never modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

SOURCE_COMMIT = '550fadea4d00a9e26ce921c5832167becb3dc20c'
DSP_COMMIT = 'a53a0756833c045311ea1d79a2badf495cdfde4c'
ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT/'firmware'/'cyd-waterfall'
VERSION = '550fade-cyd-waterfall'

RECEIVER_HOOKS = [
    ('#include "spectrum.h"\n', '#include "spectrum.h"\n#include "cyd_display.h"\n'),
    ('void app_main(void) {\n',
     '/* CYD display hooks: the same radio routines the host commands use. */\n'
     'static bool cyd_acquire(unsigned n, unsigned span, const uint32_t **words) {\n'
     '    static const unsigned clocks[3] = {0, 2, 1}; /* 16, 40, 80 MS/s */\n'
     '    unsigned elapsed;\n'
     '    bool ok = span < 3 && acquire_iq(n, 0, clocks[span], &elapsed);\n'
     '    *words = samples;\n'
     '    return ok;\n'
     '}\n'
     'static bool cyd_tune(unsigned mhz) {\n'
     '    if (!rx_frequency_valid(mhz)) return false;\n'
     '    frequency_mhz = mhz; tune_rx(mhz);\n'
     '    prepare_rx(); apply_gain();\n'
     '    return true;\n'
     '}\n'
     'static unsigned cyd_frequency(void) { return frequency_mhz; }\n'
     'static void cyd_set_gain(bool agc, unsigned code) {\n'
     '    hardware_agc = agc;\n'
     '    if (code <= gain_max) gain_code = code;\n'
     '    apply_gain();\n'
     '}\n'
     'static bool cyd_agc(void) { return hardware_agc; }\n'
     'static unsigned cyd_gain(void) { return gain_code; }\n'
     'static unsigned cyd_gain_max(void) { return gain_max; }\n'
     'static bool cyd_filter(unsigned mhz) {\n'
     '    if (!mhz) { rx_filter = -1; return true; }\n'
     '    if (mhz < RX_BANDWIDTH_MIN || mhz > RX_BANDWIDTH_MAX) return false;\n'
     '    rx_filter = rx_bandwidth_dcap(mhz);\n'
     '    return true;\n'
     '}\n'
     'static const cyd_radio_t cyd_radio = {cyd_acquire, cyd_tune, cyd_frequency, cyd_set_gain,\n'
     '                                      cyd_agc, cyd_gain, cyd_gain_max, cyd_filter};\n\n'
     'void app_main(void) {\n'),
    ('    burst_serial_init();\n', '    burst_serial_init();\n    cyd_display_init(&cyd_radio);\n'),
    ('        if (!status) { vTaskDelay(1); continue; }\n',
     '        if (!status) { cyd_display_idle(); vTaskDelay(1); continue; }\n'
     '        if (status > 0 && cyd_display_host_line(line)) continue;\n'
     '        cyd_display_host_activity();\n'),
]
CMAKE_HOOKS = [
    ('set(dependencies esp_phy esp_wifi nvs_flash esp_timer esp_driver_uart esp-dsp)\n',
     'set(dependencies esp_phy esp_wifi nvs_flash esp_timer esp_driver_uart esp-dsp)\n'
     'if(IDF_TARGET STREQUAL "esp32")\n'
     '    list(APPEND sources "targets/esp32/cyd_display.c" "targets/esp32/cyd_ui.c" "targets/esp32/cyd_waterfall_logic.c")\n'
     '    list(APPEND dependencies esp_lcd esp_driver_spi esp_driver_gpio)\n'
     'endif()\n'),
]
DEFAULTS = 'CONFIG_ESP_SDR_UART_BAUD=921600\nCONFIG_APP_PROJECT_VER_FROM_CONFIG=y\nCONFIG_APP_PROJECT_VER="%s"\n' % VERSION


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


def apply(path, hooks):
    text = path.read_text()
    for old, new in hooks:
        if text.count(old) != 1:
            raise SystemExit(f'{path.name}: hook anchor not found exactly once: {old.strip()!r}')
        text = text.replace(old, new)
    path.write_text(text)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source', type=Path, required=True, help='clean ESP-SDR checkout at 550fade')
    cli.add_argument('--work', type=Path, required=True, help='fresh directory under .scratch/')
    a = cli.parse_args()
    work = a.work.resolve()
    if '.scratch' not in work.parts or work.exists():
        cli.error('--work must be a fresh path under .scratch/')
    if not os.environ.get('ESP_SDR_IDF_PROVENANCE'):
        cli.error('run inside nix develop .#firmware')
    if git(a.source, 'rev-parse', 'HEAD') != SOURCE_COMMIT or git(a.source, 'status', '--porcelain'):
        cli.error(f'source must be a clean checkout of {SOURCE_COMMIT}')
    if DSP_COMMIT not in git(a.source, 'submodule', 'status'):
        cli.error('esp-dsp submodule must be at the pinned commit')
    project = work/'project'
    shutil.copytree(a.source, project, ignore=shutil.ignore_patterns('.git', 'build*', 'sdkconfig'))
    target = project/'main'/'targets'/'esp32'
    for f in sorted((OVERLAY/'src').iterdir()):
        shutil.copy2(f, target/f.name)
    apply(target/'receiver.c', RECEIVER_HOOKS)
    apply(project/'main'/'CMakeLists.txt', CMAKE_HOOKS)
    (project/'cyd.defaults').write_text(DEFAULTS)
    build = work/'build'
    log = work/'build.log'
    with log.open('w') as stream:
        subprocess.run(['idf.py', '-C', str(project), '-B', str(build), '-DIDF_TARGET=esp32',
                        f'-DSDKCONFIG={work/"sdkconfig"}',
                        '-DSDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.defaults.esp32;cyd.defaults', 'build'],
                       check=True, stdout=stream, stderr=subprocess.STDOUT)
    parts = {'bootloader.bin@0x1000': build/'bootloader'/'bootloader.bin',
             'partition-table.bin@0x8000': build/'partition_table'/'partition-table.bin',
             'esp_sdr.bin@0x10000': build/'esp_sdr.bin'}
    info = {'version': VERSION, 'source_commit': SOURCE_COMMIT, 'esp_dsp_commit': DSP_COMMIT,
            'idf_provenance': os.environ['ESP_SDR_IDF_PROVENANCE'],
            'overlay_sha256': {f.name: sha256(f) for f in sorted((OVERLAY/'src').iterdir())},
            'builder_sha256': sha256(Path(__file__)),
            'defaults': DEFAULTS.splitlines(),
            'images_sha256': {k: sha256(v) for k, v in parts.items()},
            'flash': {'mode': 'dio', 'size': '2MB', 'freq': '40m'}}
    (work/'build-info.json').write_text(json.dumps(info, indent=2)+'\n')
    print(json.dumps(info, indent=1))


if __name__ == '__main__':
    main()

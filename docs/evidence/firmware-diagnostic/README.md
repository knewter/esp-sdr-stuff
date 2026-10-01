# UART and startup diagnostic firmware

Build verification, 2026-10-01. This diagnostic is intended to locate a runtime
initialization stall or eliminate ambiguity about the bridge's physical baud.
Its build record does not establish an observed stall or RF failure.

The source base remains ESPARGOS
`550fadea4d00a9e26ce921c5832167becb3dc20c`, SDK remains
`25fe69f946311abdaf9ad56591f25fedbc20ac98`, and the target is original ESP32.
The diagnostic configuration defaults to **115200 baud**, which also matches
the ROM/bootloader console. Application version is `550fade-diag115k`.

[diagnostic.patch](diagnostic.patch) inserts ROM UART markers around:

1. Entry to `app_main` and NVS initialization/result.
2. Event-loop setup and each Wi-Fi initialization/configuration call.
3. Each original radio `prepare_rx` subcall and gain-register access.
4. UART parameter configuration, driver installation and input flush.
5. Completion of transport initialization and command-loop readiness.

Each operation has enter/done markers. If physical output stops between them,
the last marker narrows the unresolved step. Absence of a marker is not itself
proof that reception is unsupported. Commands must be sent only after the
`DIAG transport-init-done command-loop-ready` marker. Runtime remains RX-only.

The markers also appear on later calls to `prepare_rx`, such as `FREQ`, so this
image is **not suitable as a clean protocol or RF baseline**. Restore a clean
configuration variant once the transport/init issue is resolved. No hardware
acceptance task is checked by this diagnostic build.

Reproduction: check out the pinned source separately, initialize its ESP-DSP
submodule, apply the retained patch, and generate defaults from
`sdkconfig.defaults.esp32` with `CONFIG_ESP_SDR_UART_BAUD=115200`. Activate the
same pinned SDK, then use a fresh build directory:

```sh
python .scratch/esp-idf/tools/idf.py \
  -C .scratch/esp-sdr-diag -B .scratch/build-esp32-diag \
  -DIDF_TARGET=esp32 \
  -DSDKCONFIG=.scratch/build-esp32-diag/sdkconfig \
  -DSDKCONFIG_DEFAULTS=.scratch/diag-defaults.esp32 \
  -DPROJECT_VER=550fade-diag115k build
```

Use absolute paths for build/config/defaults when invoking from another working
directory. Export uses the pinned upstream `export_web_firmware.export` tool.
[Build info](build-info.json), [manifest](manifest.json) and
[image parser output](image-info.log) retain the patch hash, revisions, part
hashes and valid ESP32 image identity. Every part size/SHA256 was independently
verified against the exported manifest. Flash offsets/settings remain standard.

No binary or full build log is published. The source patch follows the upstream
[GPL-3.0 license](LICENSE); original project source remains linked by revision.

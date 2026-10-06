# FPGA route decision: the Forgix stays off the ESP sample path

Decided 2026-10-06 from physical measurements on the user's Forgix. **There is
no useful FPGA route for the original ESP32's radio samples with the current
equipment.** The Forgix works as a small, self-contained FPGA. It is good for
counters, timing, triggers and kilobyte-per-second results, not for carrying
ESP IQ. Better ESP reception should come from improving the original chip's
own capture and transfer path. If continuous wideband capture becomes the
goal, use a separate S3 + FPGA front end (the eSpDR architecture).

## Inventory (task 1.1)

| Item | Finding | Basis |
| --- | --- | --- |
| Board | Adiuvo Forgix ("RP2354 + T8" silkscreen) | user photos; USB identity |
| MCU | RP2354 (package `RP2354A0A4`); ROM reports RP2350 A4, 2 MiB flash detected | photo marking; [preservation](../forgix-preservation/README.md) |
| FPGA | Efinix Trion T8F49, **speed grade 2** (Efinix sells T8F49 only as C2/I2); 7,384 LEs, 15 KiB block RAM, 33 GPIO | [Efinix selector guide v3.5](https://www.efinixinc.com/docs/trion-selector-guide-v3.5.pdf); [datasheet](../fpga-inventory/README.md) |
| FPGA clock | **32 MHz oscillator, measured**: 31.92–32.13 MHz (clock observer) and 31.99982 MHz (register counter); both use the nominal RP clock as reference | [clock](../forgix-clock-episode-001/README.md), [register](../forgix-register-episode-001/README.md) |
| Host link | USB **full speed (12 Mb/s)** through the RP; enumerates at 12 Mb/s | sysfs `speed=12` |
| Memory | PSRAM wired to the **RP's QSPI**, not to the FPGA; 2 MiB RP flash | [schematic review](../fpga-inventory/README.md) |
| RP↔FPGA wiring | Passive-SPI configuration plus 3-wire SPIBone on G3/F3/F2. **Functionally verified**: configured, 13-command register session, synthetic stream | [register](../forgix-register-episode-001/README.md), [synthetic](../forgix-synthetic-episode-001/README.md) |
| I/O voltage | 3.3 V LVCMOS banks (FPGA project constraints and the official specification); not measured with a meter | build constraints; [forgix.tech](https://forgix.tech/) |
| PCIe candidate | `dabc:1017`, unbound; no bring-up attempted; separate from the Forgix | [host survey](../fpga-inventory/README.md) |

## Measured transport (tasks 2.1, 3.3, 3.4)

The full route was FPGA generator/FIFO → guarded SPIBone at about 0.97 MHz
SCK → RP SRAM queue → USB CDC → PC:

| Offered rate | Result |
| --- | --- |
| 256 B/s | Lossless (960/960) |
| 1,024 B/s | Lossless (3,840/3,840) |
| 2,048 B/s | 153/7,680 records dropped at the FPGA FIFO, during PC-side USB stalls on a heavily loaded host; zero RP-to-PC loss |

Wire time alone would allow about 3.3 KB/s on this guarded SPI route. Even
the theoretical ceiling of USB full speed is about 1.2 MB/s.

## RF integration (task 2.2): failing limit recorded

The conditional RF step was not attempted, for two reasons:

1. **No connection exists.** The ESP32 and the Forgix share no wiring, and this
   evaluation assumes no inter-board wiring is available.
2. **The capacity does not fit.** Even with wiring, the measured route carries
   kilobytes per second. The original ESP32's snapshot stream at its smallest
   setting (16 MS/s × 2 × 8 bit) is **32 MB/s** during a capture window, and
   the decision gate's 80 MS/s × 20 bit case is **200 MB/s**. Decimating 200 MB/s
   by 256 still leaves 0.78 MB/s, about 400× more than this route has carried.
   Raising the SPI clock or framing efficiency would not close a gap of three to
   five orders of magnitude while the PC link is USB full speed.

The original ESP32 also cannot stream radio samples to pins: its radio dump
engine fills an internal 64 KiB aperture. Getting samples out to an FPGA would
need new firmware that copies completed snapshots out over SPI or I2S, which
inherits the same gaps.

## Decision (task 2.3)

| Option | Verdict |
| --- | --- |
| **Original-chip improvement** | **Selected next.** The [hit-rate measurements](../ble-receiver-hitrate-002/README.md) show reception is limited by acquisition. Each 1 ms snapshot is followed by about 400 ms of UART transfer, so only about 0.3% of events overlap a window. A faster host link, on-device processing (the on-chip FFT already streams about 70 spectra/s), or trigger-driven captures attack that limit directly. |
| Separate S3 front end (eSpDR-style) | Viable later for continuous wideband: the S3's dedicated GPIO, SIMD and a high-speed FPGA/USB 3 path are the demonstrated route. It needs different hardware. |
| Forgix on the sample path | **Not useful.** It is limited by USB full speed and has no ESP connection. Keep it for standalone counting, timing or trigger experiments with KB/s outputs. |
| PCIe FPGA | Unverified and unbound; it would also need an ESP-to-FPGA connection. Out of scope until hardware wiring is available. |

## Limits

- Capacity above about 2 KB/s on the guarded route is unmeasured.
- Voltages come from documents, not meter readings.
- The PCIe card was not brought up.
- The 32 MHz figures rest on the RP's uncalibrated crystal.
- The factory loader sometimes stops answering USB some time after a session;
  a replug clears it.

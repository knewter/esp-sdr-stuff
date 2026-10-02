# A native passive BLE source reference

Status: implementation and build-only evaluation. **No native reference firmware
has been installed or measured.** This proposed diagnostic does not change the
SDR acceptance rules. The fresh [8-bit](../evidence/ble-bluez-control-001/README.md)
and [10-bit](../evidence/ble-bluez-control-002/README.md) SDR controls remain null;
the five older complete packet proofs remain valid.

The native Bluetooth controller on this same ESP32 can test whether its supported
BLE stack receives the exact owned manufacturer AD at the current placement and
time. Its scan spans advertising channels; GAP reports do not provide a fixed RF
channel, every emission, raw protected PDU/CRC bytes or a synchronized RF timestamp.
A native positive would not prove SDR demodulation, an independent hardware
reference or the historical source configuration. A null would remain inconclusive.
Reported totals are **controller-delivered matching receptions**, never transmitted
event counts or a detection rate.

## Separate firmware and artifact boundary

The app is in `firmware/native-ble-reference/`. It uses the already pinned Nix
ESP-IDF revision `25fe69f946311abdaf9ad56591f25fedbc20ac98`, original ESP32 target,
BLE-only NimBLE and observer role. Central, peripheral, broadcaster, persistent
bonds, the security manager and generic SDK/NimBLE logging are disabled and checked in the **generated**
SDKconfig. Boot security/flash encryption/signing are disabled as well; preserved
board security must already be verified disabled. No code erases NVS, advertises,
connects, pairs or sends active scan requests. NVS/PHY calibration initialization
may write reversible state; the final full-image restoration remains necessary.

The first build-only attempt compiled the application but failed to link. In this
pinned SDK, the original ESP32 unconditionally compiles host privacy code even
when the privacy Kconfig options are disabled. Its AES helper is otherwise omitted
when both connection roles are disabled. The application therefore supplies only
the required real `ble_sm_alg_encrypt` primitive: reverse the key/plaintext bytes,
AES-128 ECB without padding through SDK PSA, then reverse the ciphertext bytes.
It does not add a connection role or modify the SDK. Requested privacy options
remain disabled; **actual SDK host privacy is forced on for this target**.

The exact tracked `main/privacy_crypto.c` uses bounded stack buffers, resets key
attributes, attempts imported-key destruction on every cipher path, clears local
key/input/output buffers and emits no key or payload logs. API/length/destruction
errors leave the caller output untouched and return failure. Before NimBLE
initialization or CONFIG, a published NIST AES known-answer and an in-place variant
must pass with the target SDK PSA implementation; failure emits only the typed
`CRYPTO_SELFTEST` error and never reaches scanning. Host tests separately exercise
the exact C primitive against pinned Nix mbedTLS PSA and mock API failures; mock
contracts do not prove AES. These are software/build checks, not reception evidence.

Generated-config validation rejects duplicate or contradictory assignments for
every guarded key. Hidden NVS-persistence/privacy children may be absent when
their explicit parents are disabled; any enabled or duplicate child assignment
is rejected. The actual generated configuration remains part of artifact hashing.

Firmware waits at most 30 seconds for `START <nonce>` after stack initialization.
A typed CONFIG heartbeat identifies the profile. The host requires that exact
configuration before sending a fresh 16-character lowercase hexadecimal nonce.
Malformed commands fail inertly. One 90,000-ms `ble_gap_disc` call then uses passive
scanning, duplicate filtering off, and interval/window 160 units each (100 ms).
READY is emitted **only after that API returns success**. No automatic restart or
fallback occurs. The watchdog fails if normal completion is missing; it does not
turn a timed-out session into successful reception evidence.

AD structures are length checked before comparing the whole owned 16-byte field
`0fffffff4553502d5344522d4556414c`. Foreign payloads and every address are discarded
before the callback updates counters or writes output. Matching data itself is
not dumped. Every one-second aggregate contains a consecutive sequence, firmware
interval start/end, interval/cumulative owned-report counts and an uncalibrated
RSSI count/sum/min/max. The terminal aggregate includes discovery status, requested
duration and actual firmware elapsed time. Counter overflow and reset/init errors
fail explicitly. Generic example logging/connection behavior is deliberately absent.

The builder emits the **separate** `native-ble-source-reference-v1` manifest,
generated SDKconfig and build provenance: committed source files/tree hashes,
SDK fixed-output source hash, compiler version and exact three-part hashes/layout.
The native guard rehashes source files via the recorded Git commit, checks actual
observer-only generated config, private artifact permissions, partition-table MD5,
binary target/header, application descriptor and image checksum/SHA digest.
The existing SDR artifact allowlist remains unchanged. Native binaries, build logs
and all captured UART/readback bytes stay in ignored private directories.

## Host lifecycle and source schedule

`tools/native_ble_reference.py run` shares the stable CP2102 identity check, two
preserved original-image checks, board lock, full current-image baseline read,
signal-safe process ownership and restoration helpers with the proven ESP demo.
It installs only a separately guarded native artifact. A child exclusively owns
UART, retains boot/raw bytes privately, and publishes only exact typed schema
records. Readiness and terminal nonce must match; unexpected fields, configuration
changes, sequence gaps, inconsistent totals/RSSI and unsuccessful/short completion
fail. Each firmware bucket and READY record retains the **whole host line receipt
bracket**. These clocks are nominal and UART/controller latency is uncalibrated;
they are not exact RF packet times. Terminal firmware elapsed must be 89–92 seconds
and host observation at least 88 seconds, tolerating API/timer scheduling rather
than implying calibrated duration. These bounds are not the strict SDR demo gate.

After any installation attempt, failure/cancellation also closes the complete
owned UART process group and restores the original. If closure is unconfirmed,
restoration is blocked and recovery stays explicitly unverified. Recovery verifies
all 4,194,304 bytes against the preserved baseline and expected reset boot. A
standalone `restore` action does not require the current image to equal baseline,
so it can recover a failed native session. It proves reset recovery, not electrical
power removal. Signals during restoration are deferred through completion.

The runner never controls the host Bluetooth source. The sole operator starts
the separate source/monitor after JSON `NATIVE_REFERENCE_READY`, waits **at least
10 seconds OFF**, then runs **three 10-second ON episodes with 5-second OFF gaps**.
Keep the same BlueZ marker/properties `0x0013`/map `0x07`/20-ms requested interval.
After source unregister, bus disconnect and process-group closure, retain **more
than 10 seconds OFF** before native completion. This planned 40-second source
schedule fits the 90-second scan with initial/final guards. If readiness, monitor,
source cleanup or native reception fails, retain failure and close each owned
process; do not resume or silently change configuration. Root owns the separate
source/monitor supervision. Conservative phase joins exclude buckets crossing
source transitions or uncertain latency brackets. Overall delivered-report totals
remain independent of phase classification; no emitted-event denominator exists.

## Offline build and prospective commands

All dependencies come from the locked flake. Root adds Task bindings for these
scripts; the intended contract is:

```sh
nix develop .#firmware --command task native:ble:build -- --build .scratch/native-reference-build-next --output .scratch/native-reference-artifact-next --jobs 2
nix develop --command task native:ble:run -- --artifact .scratch/native-reference-artifact-next --manifest .scratch/native-reference-artifact-next/manifest.json --private .scratch/native-reference-session-next --output docs/evidence/native-reference-session-next
nix develop --command task native:ble:restore -- --private .scratch/native-reference-recovery-next --output docs/evidence/native-reference-recovery-next
```

The source must be committed before a fresh build. Help and build commands access
no hardware. Run/restore are physical operations for the exclusive operator only;
all named directories must be fresh. Before an installation, reviewer approval
of the actual artifact/provenance and complete host lifecycle is still required.
No physical criterion is checked by source tests or a successful build.

Primary sources: [pinned Espressif passive-scan example](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/examples/bluetooth/nimble/blecent/main/main.c#L396),
[pinned NimBLE role/logging configuration](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/bt/host/nimble/Kconfig.in),
[pinned BLE-only example defaults](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/examples/bluetooth/nimble/blecent/sdkconfig.defaults),
and [Espressif discovery guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/ble/get-started/ble-device-discovery.html).
The SDK example also prints foreign fields, initiates connections and can erase
NVS; this observer-only app uses its API pattern with those behaviors removed.

Crypto provenance: [pinned NimBLE little-endian AES helper](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/bt/host/nimble/nimble/nimble/host/src/ble_sm_alg.c#L118),
[pinned original ESP32 forced privacy configuration](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/bt/host/nimble/port/include/esp_nimble_cfg.h#L964),
and [NIST FIPS 197 (2001), Appendix C.1 AES-128 vector](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197.pdf).
The independent vector uses key `000102030405060708090a0b0c0d0e0f`, plaintext
`00112233445566778899aabbccddeeff`, ciphertext
`69c4e0d86a7b0430d8cdb78070b4c55a`; API arguments/results reverse those bytes.

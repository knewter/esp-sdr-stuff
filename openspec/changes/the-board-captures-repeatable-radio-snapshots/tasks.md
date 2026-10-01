## 1. Build the pinned baseline

- [x] 1.1 Record ESP-SDR/SDK revisions and the original ESP32 target configuration; verify the build identifies esp32 rather than esp32s3.
- [x] 1.2 Check the preservation prerequisite before installing; record flash verification and the first SDR boot.

Proof: [pinned build](docs/evidence/firmware-uart1m/README.md),
[preservation](docs/evidence/firmware-preservation/README.md), and
[actual installation and first SDR boot](docs/evidence/sdr-installation/README.md).
The first two transport rates failed protocol synchronization;
[115200 diagnostic replies](docs/evidence/sdr-diagnostic-trial/README.md)
prove initialization, not capture integrity.

## 2. Measure capture integrity

- [x] 2.1 Query INFO, CAPS, LIMITS?, RANGE? and TRANSPORT?; retain replies with firmware revision. Proof: [clean 921600 physical replies](docs/evidence/sdr-installation-uart921600/README.md).
- [x] 2.2 Collect at least 100 snapshots at each advertised rate; verify CRC, sample counts and wall-clock gaps in a CSV. Proof: [600 physical snapshots](docs/evidence/snapshot-baseline/README.md).
- [ ] 2.3 Capture a 60-second browser spectrum session and save a still plus the acquisition settings; describe missed-event limits.

## Proof procedure

Build uses the SDK revision from the pinned firmware-targets.json, then `idf.py -B build-esp32 -DIDF_TARGET=esp32 -DSDKCONFIG=sdkconfig.esp32 -DSDKCONFIG_DEFAULTS=sdkconfig.defaults.esp32 build`. Protocol replies and a future CRC-checking host harness prove the physical capture tasks.

Required outcome: At least 100 CRC-checked snapshots per advertised rate with failures and timestamps counted; 60 seconds of browser display with gaps documented.

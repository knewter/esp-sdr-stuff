# Full-flash preservation

Evidence class: **Physical flash read**, October 1, 2026.

[Manifest](manifest.json) records two independent complete 4,194,304-byte reads with identical SHA-256 `6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`. The images remain private under ignored backups. [First read](read-1.log) and [second read](read-2.log) record successful ROM/stub transfers and elapsed times; the RAM stub does not write application flash.

[Selected security fields](security.log) show secure boot V1/V2 disabled and flash-encryption count zero. No eFuse was changed. [Fresh application baseline](../preservation-baseline/README.md) precedes the backup.

The standard partition table at 0x8000 has a matching MD5 trailer, independently checked against the saved image. Its NVS, PHY and factory application ranges are nonoverlapping and within physical 4 MiB; the manifest records exact offsets and sizes. The current boot header declares 2 MiB, which is preserved as part of the original bytes.

## Recovery procedure

1. Stop all serial clients and confirm the stable CP2102 identity; one operator owns the port.
2. Check the private original image is exactly 4,194,304 bytes and its SHA-256 equals the manifest. Never overwrite it with an experimental image.
3. Restore the entire original address range with `esptool --chip esp32 --port SELECTED_PORT --baud 460800 write-flash --no-progress 0 backups/original.bin`. Keep default header settings; do not use force, encryption, flash-size override or an eFuse command.
4. Verify the restored bytes with `esptool --chip esp32 --port SELECTED_PORT --baud 460800 verify-flash 0 backups/original.bin`. Independently reread the full image and compare its SHA-256 with the baseline if the restoration record requires complete byte proof.
5. Record a fresh application boot, then remove/reapply board power and record another boot. Check application identity, CPU speed and repeated pin toggles against the baseline. A successful checksum alone does not complete recovery acceptance.

Preservation is verified. [The first post-trial restoration](../first-restoration/README.md)
also has a full matching readback and reset boot. Recovery acceptance still
requires the physical power-cycle boot.

Primary procedure references: [Espressif esptool commands](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html) and [ESP-IDF partition format](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/partition-tables.html).

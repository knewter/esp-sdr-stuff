# Original firmware restored after zero-counter RF diagnostics

Physical write/readback/reset-boot proof, 2026-10-02 UTC. Both receiver
segments and all source/monitor processes closed before restoration.
[The preserved full image write](write.log) succeeded at offset zero, without
force, header overrides or eFuse operations.

[An independent readback](readback.log) is 4,194,304 bytes, SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`,
matching both original preservation reads. The full private image remains
outside Git/site, under ignored `backups/zero-counter-restored-readback.bin`,
mode 0600. The [manifest](manifest.json) records matching bytes and successful
esptool verification.

[Fresh reset boot](boot-inspection/boot.log) identifies ESP-IDF v5.4-dirty
hello_world GPIO at 160 MHz. [Identity](boot-inspection/chip-and-flash.log)
again verifies ESP32-D0WD-V3 revision 3.1, 40 MHz crystal and 4 MiB flash.
Every serial handle is closed. The ESP is currently running the original
application. The earlier [restoration checkpoint](../final-restoration/README.md)
remains historical evidence.

**Electrical power-cycle recovery remains open.** RTS reset and a successful
boot/readback do not prove removal of the ESP supply. No USB power-switch
command was issued; user-confirmed power removal/reapplication and a subsequent
original application boot are still required.

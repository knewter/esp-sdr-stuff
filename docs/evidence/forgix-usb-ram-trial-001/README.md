# First Forgix RAM USB episode: stopped before loading

October 2, 2026: **failed pre-load episode**. The factory serial worker hit
its 15-second deadline while opening the exact identity-selected CDC tty.
The retained traceback reports a USB DTR-control timeout, then interruption
while closing the descriptor. The parent confirmed termination of the owned
process group. No factory HELLO frame, ROM transition, RAM load, throughput
capture, flash write or FPGA programming operation was reached.

[Sanitized receipt](receipt.json). The exact historical build and runtime
preflight passed, including original private backup hashes, source/artifact
identity, loaded Nix image ID, verified runtime closure and corrected actual
picotool version. The [historical lifecycle review](../forgix-usb-ram-lifecycle-review/README.md)
and [version-check supplement](../forgix-usb-ram-version-review/README.md)
remain separate offline proof. Neither establishes physical recovery.

The [independent saved-file audit](../forgix-usb-ram-trial-001-review/README.md)
passes and retains this as a failed episode. Process closure is the parent's
recorded attestation; the independent reviewer did not check live PID absence.

The [prospective protocol](../../research/forgix-usb-ram-trial-protocol.md)
requested one 64 KiB/s, 60-second condition with a 100 ms host pause. None
of that payload condition ran. Do not report zero loss or any throughput.
The factory VID/PID remained present, but enumeration does not prove a
responsive application or unchanged device flash. Original backup files
still match; fresh device verification remains outstanding.

The operator requested a physical USB replug before explicit guarded
recovery. All raw identities, worker logs and complete session provenance
remain private. No automatic trial retry or new rate condition was launched.
FPGA and RF acceptance tasks remain unchanged.

# Independent Forgix MCU preservation review

**Pass for preservation of the detected 2 MiB MCU flash range and return to
the observed original loader.** This is not an FPGA configuration backup,
firmware rewrite/restoration trial or transport benchmark. The review opened
no device and performed no hardware operation.

Reviewed public checkpoints are
`0c231437ec324e2163ef391f757e9071b7202d3c` and receipt clarification
`2107e2f1ac0dd05f59ad0b17a47b2509528d8745`.
[Operator evidence](../forgix-preservation/README.md) identifies the user's
new Forgix connection, records targeted software ROM entry, two separate
full-range save processes, separate verification and application return.

## Independently verified files and responses

Both existing private backups are exactly **2,097,152 bytes**, byte-identical,
SHA-256 `72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4`.
Each has mode 0600 in a mode-0700 directory, and Git ignores both. No firmware
bytes are included in this review or the site.

The reviewer independently parsed all four private FLDR response frames:
initial and returned HELLO/STATUS. All have the correct magic, version 1,
reserved flags 0, ACK type 128, sequences 1/2, exact payload length and valid
payload CRC32. All return success, loader state idle and zero bytes written.
HELLO reports `forge-loader rp2350 ready`; STATUS reports `status`. The
[published initial](../forgix-preservation/initial-application.json) and
[returned observations](../forgix-preservation/returned-application.json)
agree with these actual frames and the private operator records.

All six successful picotool command receipts match their private arguments,
timestamps, exit codes and captured-stdout hashes. Both `save -a -v` runs
and the separate `verify` reach 100% and terminal `OK` in private output.
Targeted ROM-entry and application-return commands exit 0. Earlier direct
access/normal-application information failures remain private historical
attempts; they are not counted as successful device operations.

## Source semantics and capacity limit

The actual picotool binary SHA-256 is
`cdaca603f918dff63967292466a610aad18ba9df752b524b7318d8eddd42fd64`.
Its clean source is version 2.3.1, commit
`2041936441b48a3cc53ae3da9e805229fe8f4e18`; the clean Pico SDK checkout is
2.2.0, commit `a1438dff1d38bd9c65dbd693f0e5db4b9ae91779`.

The pinned [save implementation](https://github.com/raspberrypi/picotool/blob/2041936441b48a3cc53ae3da9e805229fe8f4e18/main.cpp#L4940)
sets `save -a` to flash start plus the detected extent, covering
`0x10000000` to `0x10200000` exclusive here. It is not the default
program-only save ending near `0x10006084`. BIN output preserves all bytes
in this range. Save verification clears the read cache and compares the
saved file against the device; the separate verify command compares the
file's complete mapped range at the default flash start.

Both information and full save use the same
[page-wrap capacity heuristic](https://github.com/raspberrypi/picotool/blob/2041936441b48a3cc53ae3da9e805229fe8f4e18/main.cpp#L3176).
Thus the 2048K report and 2 MiB saves agree but are not independent capacity
measurements. This review accepts preservation of that detected range and
does not claim JEDEC/BOM capacity verification, OTP preservation or coverage
of independently stored FPGA configuration.

## Privacy and remaining gates

[Public ROM information](../forgix-preservation/rom-info.txt) matches the
private information after the documented unique-identity redaction. Chip
identity and boot-random values do not appear in the five public evidence
files. The [receipt](../forgix-preservation/receipt.json) explicitly documents
text-mode newline normalization, identity redaction and omitted transient
percentage progress; terminal results and original captured-stdout hashes
are retained. [Numerical checks](numerical-checks.json) record reviewed
public-file hashes, backup checks and independently decoded response metadata.

RP2350/A4/QFN60 and `pico2` are reported MCU/build metadata. They do not
identify physical FPGA grade, PCB revision, oscillator or header wiring.
Matching loader metadata/protocol does not authenticate installed source
equivalence. Idle STATUS describes loader context, not an FPGA configuration
or DONE-pin measurement.

No replacement firmware was loaded, so software ROM entry and application
return do not prove recovery after rewriting flash or a physical BOOTSEL
bypass. The operator's command/script records report no flash write, OTP
operation or FPGA START/DATA/END/ABORT request. No FPGA inventory, sequence,
CRC, sustained-throughput, clock, voltage or RF-integration gate is closed.
The original FPGA proposal remains unfinished under its original criteria.

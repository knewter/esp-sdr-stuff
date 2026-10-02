# Independent review: BLE counter unavailable

Reviewed 2026-10-02 UTC, without opening a hardware device. The physical
source-only receipts establish accepted configuration and successful cleanup;
they **do not establish transmitted-event counts or complete the burst trial**.

## Reviewed revisions and receipts

- Physical evidence: `1ce0af67dbcf53cae3a816a81190ade9ef3b4424`,
  [source-only receipts](../ble-counted-source-smoke/README.md).
- Source helper: revision `9bf820588355e30d09f9ba11bc549a9b12feb1b8`, SHA256
  `50bdcec8491626ad0ba2628cf776ad49c8f0b2188f6431fab454b4f3cc69723f`.
- Separate dumpcap monitor: SHA256
  `362d841571340d3b8fa8b00a92297281a9eaf797027882e6b2543048fbfc0dd2`.
- Reporter fix: author `8ba4c71751e77c6934089b674b528ead0d231f1f`,
  integrated `218cd47dd6da057c963bd3b66122ad4821a73b59`; reporter SHA256
  `37e3d0cc828b2c0fd2fe914a2c8052dc921de9fccd4e517261c5e08c867cc92a`.

All 18 public receipt-file SHA256 values match the
[provenance manifest](../ble-counted-source-smoke/provenance.json). Actual source
and monitor scripts match their recorded hashes. The three traces contain the
five ordered commands and status-zero acknowledgements, no observed
termination, then acknowledged handle-specific disable/removal and socket
closure. Each monitor completed with 18 packets and 10 retained control records;
its five HCI event packets were command acknowledgements, not a termination.
BlueZ preflight/postflight retain powered=true and ActiveInstances=0.

| Requested limit / interval | Expected wait | Actual enable-to-cleanup wait | Observed completed count |
| --- | --- | --- | --- |
| 255 / 20 ms | 12.650 s | 12.650730 s | Unknown |
| 10 / 20 ms | 5.300 s | 5.300989 s | Unknown |
| 10 / 100 ms | 6.100 s | 6.101080 s | Unknown |

The helper's timeout is `count × (interval + 10 ms) + 5 s`; all three waited
that full period. The smaller limits and longer interval exclude a 255-counter
edge or the first trial's timeout as sufficient explanations. They do not
identify the cause. Reviewed public JSON/log fields contain sanitized control
metadata, no Bluetooth address patterns, raw HCI/pcap or foreign payloads.
Monitor loss remains unmeasured.

## Counter semantics and unresolved event delivery

[Core 5.2](https://faculty-web.msoe.edu/johnsontimoj/EE4980/files4980/Core_v5.2.pdf),
Vol 4 Part E §§7.8.56 and 7.7.65.18 (printed pp. 2595–2598 and 2415–2416),
permits a finite event limit through the Extended Advertising API without a
legacy-PDU exclusion. When that limit terminates advertising, status `0x43`
and the completed-event field report the controller's actual completed events.
Host disable does not generate that termination. Requested limits and accepted
commands cannot substitute for the event. The independently read original PDF
has SHA256 `b3824746f3b5a2000e59609bc0d5f8a475d350b5bc411a5a05ce87fbd65bfadd`.

In [Linux v7.1.9 initialization](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_sync.c#L4532),
extended-advertising capability enables LE event-mask bit 17. The
[capability check](https://github.com/gregkh/linux/blob/v7.1.9/include/net/bluetooth/hci_core.h#L2026)
uses LE feature byte 1 bit `0x10`; cached byte `0x59` includes it. This supports
the expected initialization policy, **not current mask readback**. Inspected
`hci_core.h`, `hci_debugfs.c` and `hci_sysfs.c` have no current mask cache/readback.
The [debugfs features file](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_debugfs.c#L91)
exposes cached capabilities only. Suppression or controller behavior remains a
hypothesis. A guessed global-mask write/reset cannot preserve an unknown mask;
this review recommends an observable counted source before receiver trials.

## Reporter acceptance and remaining gates

Independently reran **11 reporter tests and 12 source-helper tests**, all passing.
The fix rejects two distinct exact-owned AA clusters in one approximately
1.024 ms snapshot: a source with minimum 20 ms interval cannot justify counting
them as two source events. It also rejects undeclared refinement bounds,
missing refined symbol periods and nonfinite/out-of-range periods. Alternate
slicings of one packet remain one observation; complete plus clipped clusters
cannot silently inflate the count.

An actually observed, matching single-channel legacy nonconnectable termination
counter can establish the original proposal's recorded source denominator,
with explicit controller-versus-radiation uncertainty. It would not establish
an independently measured RF emission count. Three predeclared receiver trials,
saved waveforms, verified complete owned packets and observed/missed-event
analysis remain physical work. `N − H` means **not verified complete**; it does
not distinguish unsampled, truncated, decoder-failed or source-path events.
The reporter's descriptive fractions/bounds do not supply that missing
classification or an IID confidence interval. No gate is accepted from these
source-only failures.

## Related USB recovery review

Reparsed both [hub descriptor receipts](../usb-power-control/descriptor-followup.json):
`092904a900006400ff` gives characteristics `0x00a9`; `0c2a040900000202c8000000`
gives `0x0009`. Both advertise individual switching, four ports and zero stated
power-on delay. The recorded reader SHA256
`bab3b62de1c6c8ed2571d0610d25d5c57b80881cdeb4c23352cbe78db39ded29`
matches. Its 64-bit control ABI is 24 bytes with offsets 0/1/2/4/6/8/16 and
ioctl `0xc0185500`; only the two IN/class/device GET_DESCRIPTOR requests are
present. No port-state write or electrical measurement occurred. Actual ESP32
power removal, sibling isolation and cold recovery remain unverified.

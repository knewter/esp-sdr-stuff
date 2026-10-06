# C3 burst sessions 001–002: no ch37 detection

Recorded 2026-10-06 under pre-declared protocols
([001](../../research/c3-burst-001-protocol.md),
[002](../../research/c3-burst-002-protocol.md)). The receiver is the
[ESP32-C3](../esp32c3-receiver/README.md) running ESP-SDR at 80 MS/s (204.75 µs
windows), tuned to LO 2396 MHz with BW 40, listening for the counted ch37
extended-advertising source.

**Session 001 has no result.** Pair 1 aborted on a UART short read (32748 of
32760 bytes) after about 100 windows, before the source started. The host's
load average was about 96 from unrelated work. As declared, the remaining pairs
were skipped and nothing was retried.

**Session 002 completed every pair, but nothing was detected: not
confirmed.** The capture tool's new opt-in `--recover-faults` lost one window
in pair 1 and one in pair 3 to UART faults and resynchronized; pair 2 had none.
The source ran 45 counted cycles (11,475 controller-counted events).

| Windows | Count | Detected |
| --- | ---: | ---: |
| Source ON | 1096 | 0 |
| Source OFF | 697 | 0 |
| Guard/boundary | 5 | — |

About 14–17 ON windows should have overlapped part of a packet. The fixed
detector found no narrowband burst above 10 dB with 6 dB of contrast in
2399–2409 MHz, in either state.

## Exploration after the result (not part of the protocol)

- **The strongest ON events are not packets.** The top in-band excesses (20.0,
  18.6 and 14.6 dB) are broadband level steps across the whole 2380–2412 MHz
  passband at the start or end of a window. They look like hardware AGC
  settling, and none passed the contrast test.
- **The AGC reference band had a flaw.** A narrowband interferer at
  2382–2385 MHz appears in both ON and OFF windows, inside the declared
  2380–2392 MHz scaling band.
- **The C3 does tune and receive 2.4 GHz.** In 150 windows each at LO 2412 and
  2437 MHz, 25 and 4 windows showed ≥10 dB wideband, Wi-Fi-like rises. The
  BW 40 passband spans roughly LO −20 to LO +18 MHz.

So the miss looks like signal level at this placement (or AGC behaviour), not
a tuning failure. The original ESP32 decoded the same source with a 1 ms window.
Next candidates: place the C3 next to the source, try manual gain, and move
the AGC reference band clear of 2382–2385 MHz. Each needs a new pre-declared
session. Summary: [results.json](results.json).

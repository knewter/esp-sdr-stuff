# Controlled spectrum session 002: pre-declared protocol

Declared 2026-10-06, before any session 002 data exists. It follows
[session 001](../evidence/spectrum-controlled-001/README.md), where burst-gated
spectra could not isolate the sparse owned source and the ESP's tuning offset
varied between retunes. The common setup (preservation, receiver image, capture
settings, source, restoration) is unchanged from the
[session 001 protocol](spectrum-controlled-001-protocol.md).

## Order

1. **C — extended tuning (task 2.2)**, unchanged from the amended session 001
   protocol. The RTL-SDR reference is recorded first. ESP captures at LO 100,
   102 and 106 MHz with hardware gain, and LO 100 MHz with gain 48; 60 windows
   each. The confirmation rule is the same: the 101.1 MHz peak must sit at
   about +1.1 MHz at LO 100 and about −0.9 MHz at LO 102.
2. **B — gain 72 (task 2.1):** the condition missing from session 001. The ch37
   source stays on, BW 20, 100 windows.
3. **A — channel location by decoded packets (task 1.2).** For each of channels
   37, 38 and 39, one continuous capture: three pairs of 30 s OFF then one
   source container of 18 counted cycles ON (about 115 s), then a 30 s OFF tail.
   LO is the channel centre minus 1 MHz, BW 12, hardware gain.

## A analysis: decoded-packet location

Decode every window with the extended-primary decoder for that channel, using
`--accept-chsel`. Run it at each translation in a fixed grid: −0.6, −1.0, −1.4,
−1.8, −2.2, −2.6 and −3.0 MHz. Count a packet once: the same window and
access-address position within 4 µs is one packet across grid points.

Each decoded owned packet gives an absolute carrier frequency:

> LO − translation + the decoder's residual carrier estimate.

For each pair, report:

- owned packets in ON and in OFF windows;
- the median absolute carrier;
- that carrier's offset from the nominal channel centre.

**Confirmed (per channel):** in at least 3 pairs, at least one owned packet
decodes in ON windows, and none decode in OFF windows across the channel. The
channel's median carrier offset is reported with its spread, for every channel.
**Not confirmed:** otherwise, reported as is.

## Stop conditions

Same as session 001: stop on any capture fault, then restore and verify the
original image. No retry.

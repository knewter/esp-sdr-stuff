# Controlled spectrum session 003: pre-declared protocol (task 1.2)

Declared 2026-10-06, before any session 003 data exists. Common setup
(preservation, receiver image, capture settings, source, restoration) is
unchanged from the [session 001 protocol](spectrum-controlled-001-protocol.md).
It applies the [session 002](../evidence/spectrum-controlled-002/README.md)
lessons: decode owned packets across a shift grid, and keep every capture under
400 windows.

## Captures

For each channel and each of 3 pairs, run one separate capture:

| Channel | Centre | LO |
| --- | --- | --- |
| 37 | 2402 MHz | 2401 MHz |
| 38 | 2426 MHz | 2425 MHz |
| 39 | 2480 MHz | 2479 MHz |

Each capture uses BW 12, hardware gain and 390 windows. The source starts 25 s
after the capture: one container of 20 counted cycles (about 128 s). The rest
of the capture is OFF.

## Analysis

Analysis matches the session 002 decoded-packet location:

- the same translation grid, −0.6 to −3.0 MHz in 0.4 MHz steps;
- `--accept-chsel`;
- a packet is counted once per window and access position within 4 µs;
- 100 ms guards around the counted source spans;
- each packet's absolute carrier is LO − translation + the decoder's residual.

**Confirmed (per channel):** all 3 pairs decode at least one owned packet in
ON windows, and none decode in OFF windows. Report the median carrier offset
from the channel centre and its spread per channel. **Not confirmed:**
otherwise, reported as is.

## Stop conditions

On a capture fault, keep the completed captures, skip the remaining ones,
restore the original image and verify it by readback. No retry.

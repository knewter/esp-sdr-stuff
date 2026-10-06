## Why

The receiver can only be seen through a host computer today. The Cheap Yellow
Display ([CYD](../../../docs/evidence/cyd-receiver/README.md)) has a 320×240
touchscreen on the same ESP32 that runs ESP-SDR. The user wants a live
waterfall on that screen, tunable by touch, so the board can be explored
without a host.

## What Changes

- A CYD build of ESP-SDR `550fade` with an on-screen waterfall drawn from the
  receiver's own 16 MS/s snapshots.
- Touch controls set the centre frequency and step size.
- The display runs only while no host session is active. Host commands keep
  their existing protocol, and a host session pauses the display.

## Capabilities

### New Capabilities

- `board/cyd-local-waterfall`: a stand-alone, touch-tuned waterfall on the
  CYD's own screen.

### Modified Capabilities

None. The host protocol and capture behaviour stay unchanged.

## Impact

Hardware: the CYD (ESP32-D0WD-V3 rev v3.1, CH340, ILI9341 panel with an
XPT2046 touch controller). Firmware: a deterministic overlay on pinned ESP-SDR
`550fade` under `firmware/cyd-waterfall/`, built in the locked
`.#firmware` shell. The CYD's original image is preserved in ignored
`backups/cyd/`.

Dependencies:
- [CYD receiver install](../../../docs/evidence/cyd-receiver/README.md);
- [spectrum session 004](../../../docs/evidence/spectrum-controlled-004/README.md),
  for this board's tuning offsets.

## Non-goals

No calibrated power scale, no on-screen packet decoding, no continuous
streaming, and no change to the host capture protocol or its results. The
waterfall is a qualitative view, with snapshot gaps between rows.

## Decision gate

- **Screen:** a photo or video shows the waterfall updating, with the tuned
  frequency displayed.
- **Touch:** a touch retune moves the displayed frequency.
- **Known signal:** with the counted source on ch37, bursts appear near the
  board's measured ch37 carrier and vanish when the source stops.
- **Host session:** the session 004 protocol queries (`INFO`, `LIMITS?`) and
  a short capture still work over the CH340.

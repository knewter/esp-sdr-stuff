# Forgix synthetic stream: lossless FPGA-to-PC transport at 256 and 1,024 B/s

Recorded 2026-10-06. **The Forgix FPGA generated a counted, patterned record
stream. The RP read it over the guarded on-board SPI bus and sent it to the
PC over USB. The PC received every record at 256 and 1,024 B/s.** At 2,048 B/s
the FPGA dropped 153 of 7,680 records when its FIFO overflowed during host-side
stalls. Every record the RP took reached the PC.

| Episode | Offered | Generated | FPGA drops | Received | Delivered | END | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 001 | 256 B/s | — | — | 727 | — | none | failed: host throttled itself (see below) |
| 002 | 256 B/s | 960 | 0 | 960 | 253 B/s | status 0 | **lossless** |
| 003 | 1,024 B/s | 3,840 | 0 | 3,840 | 1,021 B/s | status 0 | **lossless** |
| 004 | 2,048 B/s | 7,680 | 153 | 7,527 | 2,006 B/s | status 8 (loss) | FPGA FIFO drops in 2 bursts (68 + 85) |

Every episode ran preserve, ROM entry, RAM load, stream, factory return and a
post-run full-flash check. The original 2 MiB flash matched the baseline
afterwards, and no flash write occurred. Frame CRCs, sequence numbers, CONFIG,
START and END controls, the record pattern and nonce, and the END counters all
replay offline. Reconciliation shows zero records lost between the RP and the PC.

## Admission

Registry entries for the three rates use the synthetic RAM image ARM002 and
FPGA candidate-004. ARM002's only change is a USB drain fix (`675080b`). The
qualification rests on four points:

- Efinix's selector guide lists T8F49 only in speed grade 2.
- The FPGA clock was measured in [clock episode 005](../forgix-clock-episode-001/README.md).
- An independent SPI handoff review found no window where both sides drive the
  shared data pin. It also found adequate SCK and turnaround margins at the
  measured clock.
- The existing artifact, startup and lifecycle reviews.

Residual risks are recorded in each private qualification: external pad
timing, and the factory firmware's reset ordering after an unplanned RP reset.

## Episode 001: the host was the bottleneck

The first run streamed real records, but the PC spent about 500 ms between
512-byte reads. Each read call took a median of 32 ms. The collector re-ran its
full admission check up to three times per frame, re-hashing every frozen
input. That throttled the PC to about 2 frames/s, which caused this chain:

1. The RP's USB queue filled.
2. The FPGA FIFO overflowed, losing 97 records in 7 gaps.
3. The RP hit its deadline without sending END.

Commit `a1c3c05` limits full admission to every command, the end, and once a
second while streaming. Identity, lock and deadline checks still run on every
read. An independent review accepted the change, and its regression test fails
on the old collector (1,459 admissions for 483 frames). The registry was then
rebound (`e2a3d1e`).

## Independent review

An independent offline replay of episodes 002–004 **accepts** FPGA task 2.1.
It attributes the 2,048 B/s loss to host-side USB stalls, the longest 2.79 s.
These filled the RP's 16-frame queue and stopped it reading from the FPGA until
the 64-entry FIFO overflowed. It is not an SPI limit: wire time alone allows
about 210 records/s against the 128/s offered.

## Limits

- Capacity above about 2 KB/s is not measured; the losses coincide with host
  stalls while the PC was heavily loaded.
- Delivered rates are host-timed over about 60 s, and the RP clock is nominal.
- This proves the synthetic FPGA → SPI → RP → USB route only. It does not
  connect ESP radio samples or measure RF.
- After some idle time following a session, the Forgix factory loader stops
  answering USB control requests; a power cycle clears it (cause unknown).

Summary: [results.json](results.json). Receipts, raw streams and flash images
stay under ignored `backups/`.

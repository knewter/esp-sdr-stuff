# Synthetic source and USB batch codec v1

UNVERIFIED transport preparation for FPGA task2.1. These are pure codecs, with
no RP engine, serial CLI, load command, physical trial or admission. The source
contract is the separately authored finite generator README/source. Its four
nonce words are immutable after START. The XOR pattern is a deterministic fault
fixture, not a collision-resistant signature or ownership proof. A future caller
must bind the exact source/image, full nonce, coherent START tick and profile.

## Canonical source record

Exactly16 bytes, four little-endian uint32 words: generated sequence, low32 of
absolute FPGA tick, pattern and CRC32/IEEE over bytes0..11. The pattern is
`seq ^ rol32(seq,7) ^ nonce0 ^ nonce1 ^ nonce2 ^ nonce3 ^ 0x46534731`;
nonce words are the four little-endian words of the16-byte run nonce. CRC uses
reflected polynomial0xedb88320 with initial/final XOR0xffffffff.
Independent vector: ASCII `123456789` -> `0xcbf43926`.

Sequence0 is offered first, at `START_tick64 + period_cycles`. Every offer,
including a full-FIFO discard, advances source sequence. Canonical bytes are
little-endian even though SPIBone transaction words are big-endian. The pure
record decoder verifies length, CRC and pattern. Encoding an existing record
verifies its original CRC; it never repairs a damaged source CRC. A separate
constructor makes synthetic fixtures with a computed pattern/CRC.

## Exactly512-byte USB DATA frame

All multibyte fields are little-endian. There is one DATA frame type and no
implicit START, END, resynchronization, control packet or empty heartbeat.

| Offset | Bytes | Field |
| --- | ---: | --- |
| 0 | 4 | ASCII `FSB1` |
| 4 | 1 | version1 |
| 5 | 1 | type1 DATA |
| 6 | 2 | header length64 |
| 8 | 4 | frame sequence, starting0 |
| 12 | 2 | frame length512 |
| 14 | 2 | source record count1..26 |
| 16 | 2 | source record bytes, exactly16*count |
| 18 | 2 | reserved zero |
| 20 | 8 | RP batch timestamp in microseconds |
| 28 | 16 | complete nonzero128-bit run nonce |
| 44 | 4 | first source sequence, equal to first included record |
| 48 | 4 | nominal FPGA period in cycles |
| 52 | 4 | finite requested source target |
| 56 | 8 | reserved zero |
| 64 | 16*count | unchanged canonical source records |
| 64+16*count | 444-16*count | all-zero padding through byte507 |
| 508 | 4 | independent frame CRC32/IEEE over bytes0..507 |

The maximum frame carries416 source-record bytes,104 pattern bytes and96
framing/padding/CRC bytes. A one-record frame carries16 record bytes,4 pattern
bytes and496 other bytes. Report whole16-byte source records (including source
CRC), the four-byte known pattern and all512 USB frame bytes separately.
These counts do not become rates without independently retained elapsed time.
The frame timestamp is a software sample after collecting the batch and before
queueing it. It is not the FPGA tick, calibrated RF time or host receipt time.

Only period/target pairs `(2000000,960)`, `(500000,3840)` and `(250000,7680)`
are accepted. These describe nominal256/1024/2048 record B/s at nominal32MHz,
not delivered capacity or measured clocks. A future bridge flushes partial
batches on its separately bounded timer; the codecs have no timer or deadline.

## Strict one-run state contract

Initialize a fresh stream with an independently selected nonce, exact profile
and coherent64-bit START tick. A frame must bind that nonce/profile, have the
next frame sequence, and carry the next consecutive source records. Device
batch timestamps may stay equal but must not decrease. No source sequence or
frame sequence wrap is permitted: finite source targets are at most7680.
Wrong nonce/profile, CRC, nonzero reserved/padding, duplicate, reorder, gap,
excess records or a wrong expected tick fail permanently for this stream.
A full-FIFO gap therefore produces a failed strict delivery qualification; a
separate forensic/counter reconciliation may account for that loss but cannot
silently turn this stream into zero-loss success.

For record sequence n, verify low32 of
`START_tick64 + (n+1)*period`. Reject an anchor whose full finite range would
overflow uint64. This handles tick32 wrapping without guessing elapsed time.
The reconstructed64-bit tick and wrap count are expectations from the supplied
anchor/profile and validated words, not independent measurements. RP timestamp
wrap is rejected as a decrease; a run must stay within the uint64 domain.

Frame acceptance is atomic: a bad record later in a batch does not advance
accepted counts for earlier records in that same frame. The first failure is
latched; further frames cannot retry or resynchronize it. `finish()` succeeds
only once, after exactly the target records and an empty fragment buffer. This
is strict codec completeness, not a valid device END, final counters, closure,
restoration or physical trial success. Final counters and all failure prefixes
remain future lifecycle/collector obligations.

Python's finite fragment adapter buffers at most511 bytes between calls and
accepts chunks of at most512 bytes. It retains the failing frame/prefix and the
unconsumed suffix in the failure, with no silent discard. EOF with a partial
frame fails even after a complete target. C accepts caller-owned exact records
and frames; every partial length is refused. The caller owns and must persist
raw input/prefixes before calling C. The C codec allocates no heap. Neither codec opens a device or retries transport.

## Offline verification

Commit this contract before building. Use the locked Nix shell and an owned
private Taskfile to run `tests/test_forgix_synthetic_codec.py`. Compile the actual
C implementation with strict warnings, exercise it through ctypes and compare
canonical bytes against independent Python/zlib, literal fixtures and the
published CRC check vector. Mutations include every reserved/padding byte,
structural fields, record/frame CRC, wrong nonce/pattern and stream chronology,
plus all partial lengths and representative fragmented inputs. Keep failures.
No model or codec result closes FPGA/RF hardware tasks or admits a load.

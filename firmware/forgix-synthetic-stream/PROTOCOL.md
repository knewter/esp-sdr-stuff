# Finite synthetic stream profile v1

UNVERIFIED implementation contract for the existing FPGA evaluation task 2.1.
This is a distinct RAM-only RP application, not an extension of the old register
bridge's whitelist or qualification tuple. No load is admitted. Physical FPGA
identity, clock/pad timing, recoverable volatile image, actual linked resources,
whole-path review, preservation and recovery remain prerequisites. The source
and DATA codecs are the separately reviewed finite implementations.

## Ownership and bounds

One core, one TinyUSB owner, no heap, flash/OTP writer, PSRAM or DMA. Watchdog is
enabled for two seconds before checked ROM UID initialization, USB or application
GPIO. Invalid UID/USB initialization stops feeding and returns through watchdog;
no fake identity is emitted. Pre-main startup remains outside this watchdog.
The product/profile is distinct; the checked 16-hex USB serial remains unchanged.

Exactly one configuration attempt and one START attempt, both before RP boot
+30 seconds. Configuration has its own 20-second cap clipped to that deadline.
The immutable FPGA source independently requires START before reset+30 nominal
seconds and generates for 60 nominal seconds. The RP allows acquisition/drain
only until START+65 seconds, allowing at most five seconds after the nominal
60-second episode; it never extends this ceiling because packets arrive. Source
completion is observed, not manufactured by the RP clock. Terminal transmission
has at most two seconds after finalization. All activity ends before boot+120
seconds. A source still running at START+65 is failed and receives one bounded
STOP intent if the transport is still trustworthy. Never retry ambiguous writes.

Reuse the reviewed exact-image configuration body and PIO request/response
timing. Transactions are individually capped at 20 ms and clipped to the active
deadline. Interleave USB and watchdog service between every transaction; these
polling bounds do not guarantee service during a stalled CPU. Raw CS high,
DATA input and SCK low settle before any new transaction. No faster PIO preset
or changed four-pin gateware mapping is proposed.

## Host commands: exactly 128 bytes

Little-endian fields; CRC32/IEEE uses the unchanged source codec polynomial and
initial/final XOR. No line protocol, resynchronization, retry or automatic START.

| Offset | Bytes | Field |
| --- | ---: | --- |
| 0 | 4 | ASCII `FSQ1` |
| 4 | 1 | version 1 |
| 5 | 1 | operation: 1 CONFIG, 2 START |
| 6 | 2 | length 128 |
| 8 | 16 | full nonzero run nonce |
| 24 | 4 | period cycles |
| 28 | 4 | target records |
| 32 | 32 | exact RP build-input SHA256, binary |
| 64 | 32 | exact embedded decoded FPGA image SHA256 |
| 96 | 28 | zero reserved bytes |
| 124 | 4 | CRC over bytes 0..123 |

Only the reviewed period/target pairs (2000000,960), (500000,3840),
(250000,7680) are permitted. CONFIG consumes the attempt before calling the
configuration writer, binds all fields immutably and returns CONFIG. A failing
configuration never prepares SPI or starts the source. START must exactly match
the successful CONFIG binding and consumes its attempt before any source write.
Malformed/late/duplicate commands fail inertly before CONFIG, or terminate an
existing session; they cannot create another configuration/START attempt.
A partial command expires at the same absolute deadline; its prefix belongs in
the private host log. No ordinary register or arbitrary address command exists.

START reads exact source ABI 46534731, nominal Hz 32000000 and caps 00074010;
requires idle/empty source; writes period, target and four nonce words once and
reads each back. It sends control 1 once, then checks attempted/START-accepted and
captures coherent START tick64 and state through one SNAPSHOT. Failed or partial
acknowledgements do not qualify START or permit fallback/reapplication. The
coherent snapshot is also the independent tick anchor supplied to the host codec.

## Frames and controls

Every output frame is exactly 512 bytes. DATA type 1 is byte-identical to the
reviewed `FSB1` codec: 64-byte header, 1..26 unchanged 16-byte records, zero
padding, CRC at 508. Its frame sequence starts at zero and advances per DATA
frame, independently of control ordinals. CONFIG/START/END use types 2/3/4.
They reuse the common header with count/record-bytes/first-source-sequence zero,
header length 64, full nonce/profile, and control ordinal 0/1/2 at offset 8.
No empty DATA, heartbeat or untyped text is emitted. Controls use the following
fixed body; fields not yet applicable are zero, not inferred observations.

| Offset | Type | Meaning |
| --- | --- | --- |
| 64 / 96 | bytes32 / bytes32 | RP build-input / decoded image SHA256 |
| 128 / 132 | u32 / u32 | status / validity flags |
| 136 / 144 / 152 | u64 each | boot age / START RP time / finalized RP time us |
| 160 / 168 / 176 | u64 each | FPGA START / snapshot / STOP tick |
| 184 / 188 | u32 each | source state / snapshot ID |
| 192 / 196 / 200 / 204 | u32 each | generated / enqueued / full drops / popped |
| 208 / 212 / 216 / 220 | u32 each | remaining / source high-water / refused POP / refused command |
| 224 / 228 | u32 each | readback-confirmed RP records / records staged into DATA |
| 232 / 236 | u32 each | DATA frames encoded / fully accepted by CDC write API |
| 240 | u64 | bytes accepted by CDC API before this control is encoded |
| 248 / 252 / 256 | u32 / u32 / u64 | partial writes / stall intervals / longest stall us |
| 264 / 268 | u32 each | RP frame queue high-water / uncertain POP sequence |
| 272 | bytes16 | uncertain canonical record, otherwise zero |
| 288 / 292 | u32 each | pending POP flags / queued complete DATA frames |
| 296 / 300 | u32 each | partial batch record count / STOP verification state |
| 304 / 312 | u64 each | actual optional RP pause start/end us |
| 320..507 | bytes188 | zero reserved padding |
| 508 | u32 | CRC32 over bytes 0..507 |

Flags: bit0 configuration verified, bit1 START verified, bit2 coherent snapshot
valid, bit3 uncertain POP intent, all other bits zero. Pending POP flags: bit0
intent attempted, bit1 response returned, bit2 effect readback confirmed; no
other bits. STOP state: 0 not attempted, 1 intent attempted, 2 effect verified.
Status: 0 completed, 1 malformed command, 2 deadline, 3 configuration failure,
4 SPI transport/response failure, 5 source state/readback failure, 6 record
integrity failure, 7 ambiguous consumption, 8 accounted source loss, 9 USB
backlog/noncompletion. Status is latched: later cleanup cannot erase failure.
CONFIG/START status zero means their particular operation verified, not stream
completion. END status zero additionally requires complete target, empty source,
all confirmed records staged and all DATA bytes accepted, zero source drops and
refusals, exact counts and no unresolved intent. Host delivery/closure/recovery
are separate requirements. If final state cannot be read, snapshot-valid is
false and counters remain the last verified snapshot, with its time/ID retained.

## POP and queue contract

Reserve capacity for one record before reading HEAD. Read four stable HEAD words
and verify original CRC, full nonce-derived pattern and tick against the START
anchor. A source sequence gap is retained as a failed zero-loss outcome, not
repaired; forensic delivery can continue only while source/readback integrity
remains established. Read live popped count, persist pending intent/record in
SRAM, issue exactly one matching POP, then read live popped count again. Only an
increment of one proves RP ownership. No response, late response or inconsistent
effect terminates with uncertain record and no second POP, resync or reapply.
Unexpected source refusal/invalid head never becomes a successful record.

Sixteen immutable 512-byte queue slots cost 8192 bytes; a separate partial batch,
pending record, control frame and transmitted-byte offset are explicitly mapped.
Never overwrite a queued/partially accepted frame. Reserve before POP; a full RP
queue stops POP while FPGA offers continue and overflow is recorded. DATA flush
is fixed at 26 records or 100 ms after its first confirmed record, whichever is
earlier, and at finite finalization. No estimator or timer tuning per rate.
CDC write acceptance is not USB completion or host receipt. Track exact partial
write offsets and stalls. Do not use an earlier completion callback as proof of
END delivery. A partially emitted frame must finish before another frame; if
this cannot happen within the deadline, reboot with a retained host prefix and
no fabricated END. Never block forever waiting for terminal bytes.

Final source snapshot must satisfy generated=enqueued+full-drops and
enqueued=popped+remaining. Distinguish confirmed RP records, partial batch,
queued/partially written DATA, API-accepted bytes and independently received
host records. Preserve null/failed outcomes and unresolved counts. The pure
strict DATA validator still permanently rejects a gap; separate forensic loss
accounting cannot relabel it lossless. Tick32 is checked against coherent tick64;
no guessing around wrap. The optional RP 100 ms drain pause at START+30 seconds
is declared in the fixed build/profile, not inferred from a host pause or source
control8. The latter two are separately declared controls, not added here.

## Implementation and review gates

Actual C engine tests inject clock, SPI and USB API outcomes: all three complete
rates; wrong/late headers; CRC/tick/pattern corruption before POP; wrong/stale
readback; ambiguous response; queue full; concurrent source offers; partial/no
USB progress; source drops; snapshot/refusal/null outcomes; clock wrap; START,
drain, terminal and lifetime deadlines; disconnect/cancel; nonrepeated writes.
Cross-check actual source records against the independent Python codec.
Controls require independent parser/mutation tests, prefix retention and final
reconciliation; codecs alone do not implement the stream.

Keep engine/platform adapter separate for actual-C fault injection, but test the
real adapter and linked startup too. Dedicated build policy binds committed
engine, control codec, platform adapter, old reviewed UID/config/PIO inputs,
FPGA sources/generated map/image, SDK/TinyUSB/compiler and post-build hashes.
Audit complete embedded image and 8 KiB queue plus USB/state/stack allocation
under a distinct 256 KiB ordinary-SRAM cap; old caps/whitelists remain unchanged.
Actual ELF marker/load segments/vector/reset, one USB owner, no flash/OTP writer,
heap/core1 and all GPIO/PIO paths require independent disassembly review.

A separate collector must own the existing inherited operator lock and complete
private raw prefixes, validate every control/frame/record and report actual host
pause, per-second throughput, backlog, counters and deadlines. The lifecycle
still requires exact-image/backend qualification, fresh original preservation,
whole-group closure, factory return and fresh full post-trial flash comparison.
This protocol/implementation checkpoint does not complete a hardware task.

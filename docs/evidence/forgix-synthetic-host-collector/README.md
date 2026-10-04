# Offline finite synthetic host collector

October 4, 2026. Preparation only: no USB device was opened, FPGA programmed,
vendor software run, transport measured or hardware task accepted. Internal
32 MHz setup still fails in compiler003. Physical qualification, the linked RP
artifact, whole lifecycle/worker admission, preservation and recovery remain
separate prerequisites.

The [prospective plan](../../research/forgix-synthetic-host-collector.md) was
committed before implementation. The new parser binds CONFIG/START/END to the
full nonce, exact RP build/image hashes and finite period/target. DATA uses the
reviewed source/frame codec and coherent START tick64. Strict completeness
fails permanently on a gap; forensic forward-gap accounting can continue
without becoming lossless. Invalid final snapshot fields stay historical and
cannot be reported as actual final source counters. Build-declared RP pause and
the measured host-reader100ms pause are distinct.

The caller-owned collector persists one-shot CONFIG/START intent and command
bytes, every returned raw chunk before parsing, transfer brackets, failures and
the terminal result privately. Partial or ambiguous operations never trigger
retry or resynchronization. Cancellation and disk/read/clock failures still
reach serial close. Failed persistence or closure cannot report success. A
private read-only replay verifies the saved hash/count and command binding;
it does not infer physical admission, recovery or whole-worker closure.

The original `3c574d5` parser freeze is retained. A narrow follow-up latches any
protocol rejection permanently, including invalid controls rejected before the
DATA codec; catching an error and submitting replacement bytes cannot regain
lossless status. Invalid-frame and complete real-C replay regressions cover this
correction without changing the wire contract or collector hardware boundary.

Thirty-two focused test groups pass under locked Nix/Task: nineteen control/wire
groups and thirteen host fault groups. Actual native C output at the corrected
engine revision `c4cae186` verifies all three complete rates, tick32 wrap, RP
pause, source loss, ambiguous POP and invalid final snapshot. Independent
literal controls and recomputed-CRC mutations test structure, bounds, ownership
and counters. Host fixtures use a real inherited flock and cover17-byte reads,
partial/empty/late replies, attached read prefix, cancellation, disk failure,
late/failed closure, identity/lock refusal, command ambiguity, retained CRC
failure and offline receipt tampering. These are host simulations, not measured
FPGA/RP/USB timing. The initial failing author checks are retained privately.

A retained independent-clock fixture also demonstrates natural completion at
59.99 RP seconds with exact FPGA target, record ticks and STOP. The original
parser rejected it using an unsupported60-RP-second lower bound. Completion is
now determined by exact source counters/ticks; the65-second upper, source
tick/STOP exactness, terminal deadline and failure latch remain intact. Clock
frequencies are not assumed equal or inferred calibrated from this simulation.

The `4d2a785` freeze is also retained. A second narrow correction permanently
latches START-intent ordering errors and rejects fresh final source snapshots
that rewind known tick or cumulative source counters. Done snapshots require a
STOP within their start/tick bounds; previously verified completion cannot lose
its done state or change STOP. Recomputed-CRC failed-END fixtures cover these
checks, including zero STOP when the actual source starts at tick zero.

Runtime project-module closure consists of
`tools/forgix_synthetic_collect.py`, `tools/forgix_synthetic_stream.py`,
`tools/forgix_synthetic_codec.py` and `tools/forgix_usb_ram_capture.py`.
Any future hardware coordinator must freeze those exact files and its complete
qualification/identity/worker/transport/Nix inputs; this list is not permission
to omit the caller's dependency closure. The collector has no device CLI. Its
API requires caller-supplied synthetic lifecycle qualification, matching build/
image/pause policy, original identity and inherited operator lock before open.
Every action rechecks these inputs. The caller owns containment of potentially
blocked transport calls and independently verified whole-group closure.

For this isolated author freeze, a private Taskfile runs both focused files:

```text
nix develop .#ci --command task --taskfile .scratch/collector-tests/task.yml test
```

The C fixture is an exact private export of the reviewed engine/headers/protocol/
test harness/fixture at `c4cae186`, plus the reviewed source codec. The tests
verify all seven input hashes before compilation. `FORGIX_ENGINE_FIXTURE_ROOT`
selects that export; after those reviewed engine files are integrated, the
default fixture root is the repository. No absent fixture is silently skipped.

The report separates16-byte source records,4-byte patterns and512-byte frames.
Host per-second arrivals include empty bins, scheduling/buffering and actual
reader pause; CDC API acceptance is not host delivery. The API stops at END and
closes the transport; it does not probe for subsequent device bytes. Sustained
physical throughput, signal timing and complete factory/flash recovery still
require the named real experiment. The OpenSpec hardware tasks remain unchecked.

## Independent replacement review

The final replacement passes 32 author groups and three independent retained
fault probes. [Checks](checks.json) bind the corrected source and failed prior
review. Protocol/START-order rejection is permanent; fresh final snapshot ticks
and counters cannot rewind. An actual-C independent-clock fixture verifies
natural FPGA completion slightly before 60 RP seconds without inventing a
cross-clock lower bound. Exact FPGA STOP/target, 65-second successful upper
bound and all lifetime/terminal limits remain required.

Repeat: `nix develop .#ci --command task forgix:synthetic:stream:collector:test`.
This caller-owned collector has no hardware CLI. Complete identity-selected
worker/lifecycle integration and physical qualification remain outstanding;
private fixture success provides no loading or measured-throughput admission.

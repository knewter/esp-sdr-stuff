# Duration termination arrived, but the controller reported zero completed events

Three source-only diagnostics observed one matching Advertising Set Terminated
event with status `0x3C` and completed-event count **zero**. The native source
socket and independent dumpcap monitor agreed in every trial. All five commands
received status zero, own-set disable/removal succeeded, and the source socket
closed. These trials still fail the recorded source-denominator gate.

Root exclusively operated the controller. The publishing agent read and checked
the sanitized records offline. No ESP capture, reference RF measurement, decoded
air packet or independently observed radiation count was obtained in these
trials. A zero controller report does not establish that no signal was radiated.

## Requests and observed outcomes

Every request used legacy LE1M, nonconnectable/nonscannable properties `0x0010`,
single primary channel map `0x01` (channel 37), 20 ms interval bounds, the owned
16-byte manufacturer marker and nonzero maximum-event limit **255**. Each trial
enabled one selected set once, with no restart or fallback.

| Native trial record | Handle | Requested duration | Host enable-result → termination | Observed status / completed count |
| --- | --- | --- | --- | --- |
| [EF, 1 second](ef-1000ms/source-control.jsonl) | `0xEF` | 1000 ms | 0.985075025 s | `0x3C` / **0** |
| [Handle 1, 1 second](handle1-1000ms/source-control.jsonl) | `0x01` | 1000 ms | 0.977966489 s | `0x3C` / **0** |
| [Handle 1, 5 seconds](handle1-5000ms/source-control.jsonl) | `0x01` | 5000 ms | 5.047873652 s | `0x3C` / **0** |

Those measured intervals subtract the source JSONL `command_result` for enable
from its `termination_observed`, using host monotonic timestamps. They are
neither RF start timestamps nor measurements of advertising-event spacing.
The requested duration remains a separate configuration field.

The first trial pins helper SHA-256
`82c7158a369add7ad66ebdd3ee79520d513dc2b3b887eae2d69e1150a8c838f1`.
Both handle-1 trials pin
`5628261cff21b3220d66842d347d88c5a6800c7770b99f596ef54a2f759625cc`.
The latter helper makes the selected handle explicit. Both preserve strict
requested-limit success: status `0x43`, actual count equal to the requested
limit, a valid event sequence and successful cleanup. Here each summary instead
records `trial_failed`, `termination_status_or_count_mismatch`, and
`controller_completed_count_verified=false`.

Both handles produced the same zero-count result in their one-second trials;
the five-second handle-1 trial also reported zero. This comparison supplies no
causal explanation about handle selection, firmware, scheduling or masks. It
establishes that matching termination events reached both readers under these
configurations. No global event mask, adapter reset or firmware change was made
within these trials.

## Physical control records and limitations

The native JSONL, independent monitor and external pre/post checks are preserved
byte-for-byte from root's already sanitized outputs:

- EF / 1000 ms: [monitor](ef-1000ms/hci-control.json),
  [preflight](ef-1000ms/preflight.json), [postflight](ef-1000ms/postflight.json).
- Handle 1 / 1000 ms: [monitor](handle1-1000ms/hci-control.json),
  [preflight](handle1-1000ms/preflight.json), [postflight](handle1-1000ms/postflight.json).
- Handle 1 / 5000 ms: [monitor](handle1-5000ms/hci-control.json),
  [preflight](handle1-5000ms/preflight.json), [postflight](handle1-5000ms/postflight.json).

All pre/post receipts show `powered=true` and `active_instances=0`. These narrow
checks do not enumerate dormant advertising sets or prove handle availability;
reservation and exclusive source ownership were operator preconditions. Monitor
records show only the selected set was disabled and removed. Each monitor
finished normally, retained five commands, five successful command completions
and one matching termination event, and discarded raw HCI/address traffic before
storage. Bluetooth monitor loss remains unknown; completion is not loss-free
capture proof.

[receipt.json](receipt.json) records per-file SHA-256 and byte counts, the
per-trial helper pin, checked configuration, native/monitor agreement, cleanup,
external state checks and measured host interval. Publication checks parsed all
12 native files, checked their fields and ordering, and screened for address-like
strings/private identifier fields. Operation logs and raw traffic were omitted.

The earlier [count-only smoke failures](../ble-counted-source-smoke/README.md) remain a
distinct evidence set: duration zero and no observed termination event. These
new duration results neither rewrite those receipts nor convert requested event
limits into successful counts. The original burst evaluation remains open until
a verified, nonzero source denominator and separate ESP reception evidence exist.

## Primary specification basis

The mirrored original [Bluetooth Core v5.2 PDF](https://faculty-web.msoe.edu/johnsontimoj/EE4980/files4980/Core_v5.2.pdf)
has SHA-256
`b3824746f3b5a2000e59609bc0d5f8a475d350b5bc411a5a05ce87fbd65bfadd`.
Vol 4 Part E supplies the relevant semantics:

- §7.7.65.18, pages 2415–2416: when MaxEvents was nonzero, the completed count
  represents events transmitted before either duration expiry or limit
  termination. Duration expiry uses `0x3C`; limit reached uses `0x43`.
- §7.8.56, pages 2595–2598: Duration is a 16-bit field in 10 ms units and starts
  at the first advertising event. Re-enabling an active set resets its timer and
  counter. The rule supplies no legacy-PDU exception.
- §7.8.58, page 2600: supported advertising sets measures simultaneous capacity,
  rather than the greatest usable handle. A capacity value does not make legal
  handle `0xEF` invalid.

The official [HCI Test Suite p37](https://files.bluetooth.com/wp-content/uploads/dlm_uploads/2025/05/HCI.TS_.p37.pdf),
page 125, test HCI/HFC/BV-19-C, explicitly uses legacy properties `0x0010`,
MaxEvents 8 and duration zero. It expects eight ADV_NONCONN_IND PDUs and,
when enabled in the mask, a termination event reporting eight completed events.
This supports applying event-count semantics to legacy advertising. These local
diagnostics did not perform that conformance test or its mask mutations and
independent RF observations. Specification expectations do not turn their zero
reports into a measured count or identify a firmware defect.

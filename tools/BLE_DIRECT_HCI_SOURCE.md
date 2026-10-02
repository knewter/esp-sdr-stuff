# Bounded owned source with an observed controller event count

`ble_direct_hci_source.py` is an **operator-run experimental source**, tested
here with synthetic socket fixtures. It has not been run on hardware by the
firmware-tools agent. Root owns all physical controller/source operations.

Before running, the operator must establish exclusive HCI0 source ownership,
check BlueZ `ActiveInstances=0`, reserve advertising handle `0xEF`, and ensure
no concurrent same-opcode advertising commands. A high handle avoids the
observed BlueZ-managed handles; these preconditions require an external check.
The helper does not query or change BlueZ state.

```sh
python3 tools/ble_direct_hci_source.py --interval-ms 20 --events 100 \
  --start-delay 10 > docs/evidence/YOUR-TRIAL/source-control.jsonl
```

For root's isolated container, mount this file read-only and give the existing
Python container host networking with only `NET_ADMIN` and `NET_RAW` added
after dropping other capabilities. This recipe does not create that container
or alter host executable capabilities. The helper uses standard-library Python
and numeric Linux AF/protocol constants, allowing builds without Python's
Bluetooth named constants.

## Fixed source and allowed operations

One trial defines one advertising set on handle `0xEF`, using legacy LE1M,
nonconnectable/nonscannable undirected properties `0x0010`, channel map `0x01`
(channel 37 / 2402 MHz), public own-address type, and a complete 16-byte owned
manufacturer AD containing `ESP-SDR-EVAL`. Both interval bounds are exactly
20 ms by default, or explicitly 100 ms. Controller advertising delay still
affects actual event spacing. Tx power is the controller's choice.

The only allowed outgoing command opcodes are `2036` (parameters), `2037`
(data), `2039` (enable/disable), and `203c` (remove this set). Both enabling
and disabling specify one set, handle `0xEF`; disabling with zero sets is
never generated. There is no reset, address-setting command, event-mask
mutation, pairing, scanning, controller power change or global fallback.

The explicit native `sockaddr_hci` binds AF31 / device0 / RAW channel0. The
socket receive filter selects HCI events, Command Complete/Status and LE Meta.
Only selected command status metadata and this handle's termination event are
emitted. Addresses, connection handles and raw packet/AD bytes are discarded.

## Audit sequence and failures

Each flushed JSONL record includes host `monotonic_ns` and UTC. The initial
`configuration_requested` pins the executed file's SHA-256 and requested
settings; its owned-marker boolean describes the generator's data policy.
Actual controller acceptance requires the corresponding successful
`command_complete` and matched `command_result` records for parameters/data.
`source_ready` follows those acknowledgements and precedes the start delay.
`source_enabled` follows successful enable acknowledgement. Commands have a
two-second acknowledgement bound. No retransmission or automatic restart is
performed.

The helper waits for its matching `termination_observed`, with requested count
1–255, status `0x43`, and the same actual completed count. Wrong status/count,
missing acknowledgement/event, a pre-enable termination or duplicate matching
termination cannot yield a verified count. Every trial attempts this handle's
disable and removal in `finally`, records their actual results, and closes the
socket. Failed cleanup prevents an overall successful result. `source_closed`
contains the summary and `source_socket_closed` records handle closure; audit
the full sequence rather than trusting a summary flag alone.

The termination wait permits requested count × (interval + 10 ms) + 5 seconds;
the start delay is bounded to 0–60 seconds. CLI success requires the verified
controller count and successful disable/removal; all other outcomes exit 2.
Parameter rejection is recorded without silently changing interval or PHY.

## Optional duration diagnostic

After the count-only source timed out on the actual host controller, an operator
can explicitly compare the own-set duration timer without changing global
event masks, resetting the adapter, or changing any other advertising set:

```sh
python3 tools/ble_direct_hci_source.py --interval-ms 20 --events 255 \
  --duration-ms 1000 --start-delay 1 > YOUR-DIAGNOSTIC/source-control.jsonl
```

`--duration-ms` defaults to zero, preserving the original count-only protocol.
An explicit nonzero diagnostic must be 100–5000 ms in exact multiples of 10 ms;
values are rejected before socket creation. The enable packet encodes the
duration as a little-endian 16-bit count of 10 ms units. Configuration,
enable acknowledgement and summary records expose those units. The requested
event limit remains 1–255 and nonzero. Disable cleanup always sends duration
zero and event limit zero for only handle `0xEF`, followed by own-set removal.

The diagnostic waits duration + 5 seconds after enable acknowledgement, at most
10 seconds, before cleanup. The controller's duration starts with its first
advertising event; host acknowledgement and JSONL timestamps do not measure that
RF start time. No automatic fallback or re-enable occurs.

A matching `0x3C` duration-termination event and its actual completed count are
retained in `termination_observed` and the summary's `termination` field, but
the trial still fails the unchanged strict requested-limit gate and exits 2.
Even a duration result with 100 or more completed events receives no automatic
receiver/source acceptance. A count-limit `0x43` event can win the timer race
and succeeds only with the exact requested count, valid sequence and successful
cleanup. A small requested limit also does not satisfy a separate evaluation
requirement for at least 100 recorded source events.

Core v5.2 Vol 4 Part E §7.7.65.18, page 2415, explicitly makes the completed
count meaningful when a nonzero MaxEvents was used and either duration or
event limit ends advertising. Status `0x3C` means duration elapsed, while `0x43`
means limit reached. §7.8.56, pages 2595–2598, specifies duration units and
has no legacy-PDU exception. The special duration bound of 1.28 seconds applies
to high-duty connectable directed advertising; the fixed properties `0x0010`
here are nonconnectable undirected advertising. The helper does not claim that
the present controller fulfills these semantics until an actual event is seen.

`controller_reported_completed_extended_advertising_events` is a controller
report of completed transmitted events. It can provide a recorded source
denominator independently of the ESP decoder, under the stated policy and
audit checks. `independently_observed_air_emission_count` remains null: this
does not measure independently radiated RF, received signal level or actual
ESP reception. The separate ESP captures and decoder evidence must establish
those outcomes.

## Primary semantics and software validation

The original [Bluetooth Core v5.2 specification PDF](https://faculty-web.msoe.edu/johnsontimoj/EE4980/files4980/Core_v5.2.pdf)
is a mirror of the SIG document, SHA-256
`b3824746f3b5a2000e59609bc0d5f8a475d350b5bc411a5a05ce87fbd65bfadd`.
Its Vol4 PartE §7.8.56, pages2595–2598, describes a nonzero event limit and
termination for sets enabled through the Extended Advertising API. It gives
no legacy-PDU exception; the explicit ignored condition is enable=0.
§7.7.65.18, pages2415–2416, defines the actual completed-event count when a
nonzero limit was used and status `0x43` when that limit ends advertising.
§7.8.53 defines legacy properties and parameter fields. These semantics support
the method; actual controller acceptance and termination remain trial gates.
The official [HCI specification chapter](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html)
provides the corresponding command/event reference.

Linux socket/filter definitions were checked against the installed BlueZ HCI
header and the [Linux HCI socket ABI](https://github.com/torvalds/linux/blob/master/include/net/bluetooth/hci_sock.h).
Only the per-socket receive filter is set; the controller event mask is unchanged.

```sh
python3 -m unittest discover -s tests -p test_ble_direct_hci_source.py -v
```

Seventeen hardware-free tests check exact wire encoding, 100/255 limits, fixture
events, status/counter/handle errors, duplicate and early termination, missing
acknowledgement/event, cleanup failures and own-handle rollback. Synthetic
counts and fixtures are software checks, and establish no hardware acceptance.
Duration tests additionally check exact field boundaries, validation before
opening a socket, timer versus count-limit outcomes, bounded host timeout,
retention of actual diagnostic counts without acceptance, and zeroed cleanup.

# Controller-counted owned BLE trials

This is an offline reporting protocol and readiness checkpoint. It contains no
new physical reception result. The earlier four-plus-one verified packets used
an uncounted BlueZ source and do not establish an emitted-event denominator.

## Predeclared repetitions

Retain three independent trials, in order: `counted-01`, `counted-02`,
`counted-03`. Each requests **255 events**, for 765 events across the complete
experiment. Retain zero-hit trials. Do not substitute a source-only smoke check
for a receiver trial, or omit an unsuccessful trial from an apparently complete
aggregate. Failure of any source/count/coverage gate leaves that aggregate
unverified.

The source uses the reserved handle `0xEF`, 20 ms advertising interval,
legacy nonconnectable properties `0x10`, LE1M, and only primary channel 37
(2402 MHz). It configures the exact 16-byte manufacturer AD structure
`0fffffff4553502d5344522d4556414c`. Configure the receiver at LO 2401 MHz,
20 MHz filter, manual gain 48, nominal 16 MS/s, 8 bits per component, and
16,380 complex samples. Receiver runs approximately 35 seconds per trial;
each must include at least five seconds before enable and ten seconds after
source cleanup/closure. The receiver decodes **every** recorded snapshot with
the existing blind bounded AA-trained refinement, channel 37, and digital
translation −1 MHz. No known-marker bit repairs are allowed.

## What establishes the denominator

The [Bluetooth SIG HCI test suite, Figure 4.61](https://files.bluetooth.com/wp-content/uploads/dlm_uploads/2025/05/HCI.TS_.p37.pdf)
independently describes a count-limited, legacy nonconnectable advertisement
sequence through the extended advertising interface, including the completed
advertising-event count at termination. [Core error code 0x43](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/architecture%2C-change-history%2C-and-conventions/controller-error-codes.html)
is Limit Reached. The [Linux HCI event definition](https://github.com/torvalds/linux/blob/master/include/net/bluetooth/hci.h)
defines the termination event's status, advertising handle and completed-event
count separately from the enable command's requested maximum.

`tools/ble_counted_report.py` requires the direct source's full sanitized JSONL
sequence: accepted parameters, exact data, one enable, an actual matching
termination event with status `0x43` and completed count 255, successful
handle-specific disable/remove, and socket closure. It rejects commanded-count
only, missing termination, handle mismatch, duplicate termination, restarts,
fallbacks and failed cleanup. The source script's executed SHA-256 is recorded.
A separate completed dumpcap monitor must agree on the parameters, marker,
enable/count, termination and cleanup, with successful command completions.
Monitor traffic is sanitized before storage; no raw capture is retained.
Monitor completeness checks do **not** prove loss-free monitoring.

The denominator is **controller-reported completed advertising events** under
this verified single-channel, single-PDU configuration. There is no independent
RF emission counter; the report leaves that field null. Do not relabel this as
an independent RF measurement.

## Numerator and unresolved outcomes

The report checks every private waveform's length, SHA-256 and transport CRC
against its capture row and decoder input. It requires complete contiguous
capture/decoder index coverage and nonoverlapping host acquisition brackets.
Repeated waveform identity across captures is rejected as unresolved stale-data
or duplicate provenance, rather than silently counted twice.

A hit requires a complete CRC-valid exact owned AD packet, type 2
(ADV_NONCONN_IND), length 22, and its full nominal preamble-through-CRC sample
window inside the snapshot. Only snapshots whose entire host acquisition
bracket lies between enable-command send and termination observation enter the
numerator. Edge captures and a CRC-valid owned packet of another PDU type are
reported separately. Preamble/AA errors are retained openly; the preamble is
not CRC protected. Nominal sample-window bounds are not a calibrated sample
clock or hardware RF timestamp.

Within each snapshot, access-start positions within four microseconds form one
packet cluster; successful slicing/timing hypotheses count once. Distinct
nonoverlapping captures of the same fixed payload remain distinct packets.

For each trial and the full aggregate, report `H / N`, where H is full verified
hits and N is actual controller-completed events. `N − H` means **not verified
complete**, with unresolved contributions from unsampled events, truncated
windows, receiver/decoder failures and source-path uncertainty. It is never a
count of confirmed RF misses. An arbitrary failed/truncated AA candidate does
not establish an owned incomplete packet. A CRC-valid exact marker whose
nominal full-packet window is clipped can support a specifically labelled
owned incomplete candidate; retain these separately as I. Current failed or
truncated AA-only outputs establish no incomplete-marker matches. Conservative
bounds for incomplete observations among the remaining events are
`[I, N − H]`; the possible fraction of events with any owned observation is
bounded by `[(H + I) / N, 1]`. These are deterministic unresolved bounds, not confidence
intervals. No IID binomial interval is claimed for the correlated snapshot
schedule.

## Replay input

Create a local JSON input listing `expected_ids`, `expected_count: 255`, and
three `trials` entries. Each entry contains `trial_id` plus paths `source`
(sanitized JSONL), `monitor` (sanitized dumpcap JSON), `captures` (CSV),
`receiver` (physical manifest), `decoder` (full blind replay manifest), and
`private` (ignored raw-IQ directory). Paths resolve from that JSON's directory.
Private paths are not copied into the public output.

Run `python3 tools/ble_counted_report.py --plan PATH --output FRESH-PATH`.
The output includes per-trial and aggregate results, packet-proof hashes,
input-manifest hashes and reporter/decoder script hashes. It excludes raw
waveforms, addresses and foreign payloads. Publish physical results only after
independent replay and committed evidence; the synthetic regression tests prove
the accounting checks, not reception.

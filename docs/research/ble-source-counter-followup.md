# Advertising counter follow-up

Offline research, 2026-10-02, against published checkpoint `566fb8b`.
The comparison below is **prospective and unverified**. No hardware, controller
settings, source helpers or acceptance gates changed during this investigation.

A subsequent [single actual mode pair](../evidence/ble-mode-counter-001/README.md)
completed with both modes reporting `0x3c/count0`. The prospective comparison
below records its rationale; that result did not establish a mode-associated
reporting difference, RF emissions or a usable denominator.

## Legacy PDUs do not exempt the counter

Core 6.2 HCI §7.7.65.18 applies Advertising Set Terminated to both legacy and
extended advertising enabled through the extended command. With nonzero
Max_Extended_Advertising_Events, its count reports completed events when duration
expires or the limit is reached; with MaxEvents zero, the count must be zero.
Duration expiry uses status `0x3c`; reaching the limit uses `0x43`.
[Official event definition](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-b7eedd85-4369-f88f-7872-7278f7778cd2).

In §7.8.56, Duration starts at the first event, not the ACK. Duration/MaxEvents
are ignored on disable and reset on reenable. The high-duty directed restriction
does not exempt our legacy `0x0010`.
[Official enable command](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-d05d4cfe-f0b5-b0e2-1a63-672c960dc088).

The SIG qualification test independently makes the legacy expectation explicit:
HCI/HFC/BV-19-C configures legacy ADV_NONCONN_IND, enables MaxEvents eight and
expects eight transmissions and a terminal count of eight when reporting is
enabled. This is a specification example, not a measurement here; its global
event-mask steps are not proposed for this host.
[Official HCI test suite p37, p125](https://files.bluetooth.com/wp-content/uploads/dlm_uploads/2025/05/HCI.TS_.p37.pdf#page=125).

The [completed native comparison](../evidence/native-direct-reference-002/README.md)
observed six `0x3c/count0` terminations, alternating MaxEvents 255 and zero,
with matching independent HCI receipts and positive exact-owned native reception.
Zero is prescribed for the zero-Max episodes. For nonzero-Max episodes, zero
cannot safely be treated as proof of no transmission. These receipts establish
an unresolved discrepancy, not a controller-firmware cause or compliance verdict.

## What Linux adds

Linux v7.1.9's ordinary extended-advertising enable path zero-initializes the
per-set structure and only fills its handle and optional duration; it leaves
MaxEvents zero. Its termination handler uses status/handle for lifecycle cleanup
and does not synthesize a transmitted-event count or rewrite zero based on legacy
properties. Upstream therefore supplies no alternative count interpretation for
our direct-HCI receipts. [Enable path, lines 1619–1662](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_sync.c#L1619),
[termination handler, lines 5926–5994](https://github.com/gregkh/linux/blob/v7.1.9/net/bluetooth/hci_event.c#L5926).
The raw source socket and monitor agreement still observe the controller's
reporting, rather than two independent RF counters. The delivered duration events
give no reason to revisit global mask/reset experiments.

## One bounded mode comparison

After a separate protocol and implementation review, one source-only pair could
compare `0x0010` with `0x0000`, clearing only the legacy-PDU property bit. Keep
handle 1, primary map 1, requested 20 ms interval, primary/secondary LE1M,
secondary skip zero, the same owned AD, Duration 500 (five seconds), and MaxEvents
255. Secondary settings become operative in extended mode; this compares entire
advertising modes, not an isolated internal firmware mechanism. The parameter
command permits this combination and 20 ms minimum.
[Core 6.2 §7.8.53](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-2d5f3e1f-6666-baa9-dcc2-5d8af3709dac).

Use one enable per condition, a finite duration-plus-margin host deadline, exact
typed command/ACK/termination agreement between source and monitor, and verified
disable/remove/socket/container/group closure before proceeding. Externally
reserve the owned handle; powered/ActiveInstances checks alone do not enumerate
dormant sets. Preserve rejection, timeout, zero and positive counts. Stop on
unknown cleanup; no retry, reset, power, address or mask changes. No ESP flashing
or hidden SDR acquisition is necessary for this source-only comparison. The
existing fixed-property helper cannot execute this proposal unchanged.

A nonzero extended count with another zero legacy count would support a
mode-associated reporting difference. Two zeros would remain inconclusive.
Five seconds at the requested interval does not guarantee reaching 255; retain
actual duration/limit status and count separately. Neither outcome qualifies the
legacy source, proves radiated counts, supplies an SDR detection rate, or releases
the withheld Trial B.

Extended advertising carries this AD in an auxiliary PDU, not the channel-37
legacy packet. An extended event can include multiple PDUs, so its event count
is not a count of channel-37 marker packets. [Core 6.2 Link Layer
§§4.4.2.2.2 and 4.4.2.6](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html).
The current original-ESP32 observer cannot provide that extended-marker reference:
[Espressif documents its lack of advertising-extension support](https://www.espressif.com/en/node/4252).
Any RF claim needs a separate extended-capable receiver that follows
the auxiliary pointer and validates the whole owned AD. Such equipment is not
established by the attached RTL-SDR or FPGA ownership.

The full official HCI chapter exceeded the browser tool's size limit; the relevant
sections were checked in the existing official-page cache (SHA-256
`94da1492e4c1be5e08ad27fb45e02b0aed9ba65dd0658d61257941bf8266d35f`).
The cache and source downloads remain private; only this compact note is added.

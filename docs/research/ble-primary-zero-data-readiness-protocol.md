# Prospective zero-data extended-primary count100 readiness

Declared October 4, 2026, before implementation or source actions. This separate
source-only condition qualifies `extended-primary-zero-data-v1` requested HCI
profile and controller-completed-event limiter. Earlier marker-data readiness,
failed diagnostics and all original RF/legacy TrialB gates remain unchanged.
No controller event count is an independently counted radiated primary PDU.

The sole root operator retains an inherited exclusive mode0600 global
`.scratch/esp-demo.lock` descriptor, exact private controller USB/topology/BlueZ
binding and externally reserved free handle1. Require powered=true and
ActiveInstances0 before launch and unchanged after closure. No discovery,
pairing, power/reset, event-mask changes, fallback or retry. Root performs any
physical source trial only after independent offline preflight of frozen files.

Exactly one episode: handle1; properties0; primary-map1; primary/secondary PHY1;
interval bounds32×625us=20ms; Own_Address_Type0; unused Peer_Address_Type0 and
zero Peer_Address; filter-policy0; requested power127/no preference; secondary
skip0; SID0; scan-notify0. Host data is empty: complete operation3, fragmentation
preference1, length0. Start delay0; Duration500×10ms; MaxEvents100. Explicit
extended-mode and primary-zero-data flags are required; no legacy marker data.

Both native source and independently sanitized monitor must retain exactly five
ordered command/complete pairs (parameters,data,enable,scoped disable,remove),
all status0, selected-power byte for parameters (agreeing between readers), and
exactly one matching handle1 termination0x43/count100 after accepted enable and
before cleanup. The independent monitor validates every supported v1 wire field,
including unused/redacted peer-zero boolean, SID, skip/filter/scan and data
fragment preference; native configuration is intent, not independent wire proof.
Missing/malformed/duplicate/wrong/timer0x3c records remain failed attempts. Native
socket/container closure, normal monitor completion and whole process-group
closure are required. Preserve every log and receipt durably in fresh0700/0600
ignored storage. No raw addresses, foreign payload or private binding is public.

Freeze caller/Task/tests/protocol, full imported committed-helper closure,
Taskfile/flake lock, private controller binding, exact image archives/config IDs
and Nix executable/closure manifests before actions. Read-only image inspection
is permitted; the prepared runner launches neither source nor monitor during
freeze or tests. Exact source image reuse is required. A mutable tag, substituted
archive/executable, missing closure proof, changed helper or inherited lock
failure prevents launch. Record preflight and unchanged postflight.

Preloaded monitor producer startup/header readiness15s is separate from bounded
outer Task/container startup75s. Normal monitor capture30s with grace5s, active
producer bound50s. Overall source-only supervisor120s includes monitor launch,
validated readiness, one source (40s parent cap) and normal monitor completion;
check clocks before/after spawn, marker scans, waits and group closure. No source
launches before validated MONITOR_READY or after its bound. Final cleanup uses
separate finite waits; interrupted/forced/unknown cleanup cannot qualify success.
Immediately before source spawn, after durable source-intent persistence and
inherited-lock validation, require the monitor still alive and the current clock
strictly below all outer-readiness, source-parent and supervisor deadlines.
Until that final check passes, source-attempted remains false.
Normal completion must observe the whole owned process group naturally absent
within the remaining deadline. Leader exit alone is insufficient. Required
signal cleanup is retained explicitly and fails qualification even if subsequent
bounded cleanup verifies closure; shared cleanup helpers are unchanged.

After profile readiness passes, a separately frozen future receiver protocol
may request three repetitions at fixed ten-bit/16MS/s/16380 pairs,LO2401MHz,
BW20/manual48, with complete preservation/restoration, monitor ready first,
>=5s OFF baseline, >=1s OFF gaps and >10s continuous final OFF tail. Actual
primary layout, optional AUX/AdvA and known private address/header ownership
must be observed, not assumed. Missing AdvA, ADI-only or AUX AD cannot establish
primary ownership. No receiver is implemented or admitted by this condition.
Controller-event normalized metrics need explicit units and omission uncertainty;
count100 does not close original >=100 deliberately emitted-event criteria.

Grounding: [existing primary-profile protocol](ble-extended-primary-zero-data-protocol.md),
[fuller v1 HCI preparation](../evidence/ble-hci-metadata-preparation/README.md),
[HCI Core6.2 Vol4E7.8.53–56 and7.7.65.18](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html),
and [LL Core6.2 Vol6B4.4.2.1/2 omission rules](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html).
This is prospective control-profile proof, not RF reception or air-count proof.

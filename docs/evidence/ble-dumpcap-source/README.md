# Actual advertising settings via the capture-capable monitor

The host's existing `dumpcap` has capture capabilities. The
[streaming wrapper](../../../tools/ble_dumpcap_monitor.py) opens only
`bluetooth-monitor`, consumes classic pcap in an anonymous pipe, and writes
selected sanitized HCI0 control metadata. No raw pcap/HCI/address or foreign
payload was saved; no capabilities or controller power/pairings were changed.

[The physical record](hci-control.json) completes 15.212 seconds, sees 22 pcap
records and retains eight control records. All four retained commanded operations have
status-zero Command Complete responses; the producer exits zero and is reaped.
A validated stream header established readiness before the owned source began.
The 22 monitor-kind totals reconcile with the record, but monitor drop counts
are not a measured loss guarantee.

## Observed configuration

- Set Extended Advertising Parameters: **20 ms minimum and maximum**,
  primary channel map **7** (37/38/39), primary/secondary PHY **1**.
- Event properties **0x0013**: legacy, connectable and scannable advertising.
- Set Extended Advertising Data: 16 bytes, complete fragment operation,
  **exact owned manufacturer AD matched**, then raw data discarded.
- Enable accepts one handle with duration zero and MaxEvents **zero**;
  later explicit disable accepts. Zero means no event-count limit.

The [source log](source-results.json) shows one five-second registration and
successful removal, with ActiveInstances zero before and after. This proves
actual accepted HCI settings for this new trial. It does not retrospectively
establish all settings of earlier trials.

The API requested Type `broadcast`, yet the observed HCI properties are
connectable/scannable legacy. That configuration is consistent with the actual
ADV_IND type0 packets decoded earlier; no cause for the API/controller
mismatch is asserted. The packet type was correctly preserved in those reports.

## Scope and remaining denominator

This resolves the earlier native MONITOR EPERM problem **for this existing
capture-capable executable**. The native Python socket bind remains denied.
No controller Advertising Set Terminated count was observed: the source was
unlimited and stopped explicitly. Exact RF emissions and the source event
denominator remain unknown; five seconds divided by 20 ms is not a count.

The [finite source diagnostics](../ble-counted-source-smoke/README.md) then used
one primary channel, nonconnectable and nonscannable legacy LE1M, with a finite
MaxEvents. The controller accepted all commands but supplied no observed
termination count in three tests. An **actually observed** matching-handle
controller source counter could provide
an independent-from-ESP denominator under the original proposal. It must stay
labeled controller-reported transmitted events rather than independently
measured radiated RF packets. Capture accounting and uncertainty remain separate.

[Provenance](provenance.json), [monitor operation](monitor-operation.log),
[source operation](source-operation.log), and the
[tool format/bounds references](../../../tools/BLE_DUMPCAP_MONITOR.md) retain the
procedure. No ESP port was opened; original firmware remains restored.

# Streaming dumpcap Bluetooth Monitor fallback

`ble_dumpcap_monitor.py` uses the host's existing `/usr/bin/dumpcap` executable
to receive Bluetooth Monitor data through an anonymous stdout pipe. It passes
converted frames to the existing `ble_hci_monitor.sanitized_packet` function,
storing only its selected HCI0 advertising-control metadata and timestamps.
Addresses, names, advertising bytes, foreign payloads and dumpcap stderr are
discarded. No raw pcap, HCI or temporary capture file is requested.

The tool is implemented and tested with synthetic data. **Physical operation
and capture permissions must be verified by the designated device operator.**
It does not configure, power, pair, scan or advertise with the controller.

From the integrated repository, using a fresh result path:

```sh
python3 tools/ble_dumpcap_monitor.py --seconds 30 \
  --output docs/evidence/YOUR-TRIAL/hci-control.json
```

The producer command is fixed to one interface and stdout:

```sh
/usr/bin/dumpcap -i bluetooth-monitor -P -Q -s 65539 \
  -a duration:30 -w -
```

Use the Python wrapper for real trials so the raw stream is consumed in memory;
running the producer directly would send raw packets to the terminal. The
[dumpcap manual](https://www.wireshark.org/docs/man-pages/dumpcap.html)
documents `-w -` as stdout, `-P` as classic pcap, and duration-based autostop.
Installed read-only help identifies dumpcap 4.7.2; package metadata identifies
libpcap 1.10.6 on this host. The wrapper does not request elevated privileges
or change executable capabilities.

`MONITOR_STARTING` means the process was created. `MONITOR_READY` means the
pipe supplied a validated DLT254 classic-pcap header, allowing the operator
to coordinate a separate owned source trial. No advertising command is sent
by this tool. The controller's own `Command Complete` events and marker-match
booleans are the subsequent evidence; header readiness alone verifies no RF.
`MONITOR_CLOSED` reports the sanitized record count and completion status.

## Format and bounds

The primary [DLT254 specification](https://www.tcpdump.org/linktypes/LINKTYPE_BLUETOOTH_LINUX_MONITOR.html)
defines a four-byte, big-endian adapter ID / opcode pseudoheader. The
[installed-version libpcap source](https://github.com/the-tcpdump-group/libpcap/blob/libpcap-1.10.6/pcap-bt-monitor-linux.c#L142)
shows the conversion from Linux's opcode/index/length monitor header. The
wrapper reconstructs `<HHH` opcode, index and payload length in memory before
calling the existing sanitizer; HCI payload byte order is preserved.

The [classic-pcap format](https://github.com/the-tcpdump-group/libpcap/blob/libpcap-1.10.6/pcap-savefile.manfile.in)
has a 24-byte file header and 16-byte per-packet headers. The parser supports
both byte orders and microsecond/nanosecond magic variants. It rejects pcapng,
unsupported versions/link types, invalid timestamps and excessive lengths.
Snaplen-truncated packets are counted and discarded before sanitization.

The CLI accepts 0.1–3,600 seconds. The producer has a duration stop; the parent
adds a five-second grace deadline, terminates/reaps a producer that exceeds it,
and caps stored control records at 10,000. Pipe reads and parser buffering are
bounded. A malformed stream or failed producer is recorded with fixed error
codes and exits 2; successful producer/stream closure exits 0. A completed
empty capture establishes no successful source trial.

Stored capture timestamps come from pcap; `monotonic_ns` records host parsing
time. Those clocks do not synchronize ESP sample start or RF emission time.
`independently_observed_air_emission_count` remains null. Controller-reported
completed extended-advertising events remain labeled controller reports.
The [libpcap monitor statistics implementation](https://github.com/the-tcpdump-group/libpcap/blob/libpcap-1.10.6/pcap-bt-monitor-linux.c#L159)
returns zero counters without independently measuring drops, so an empty loss
count cannot establish loss-free monitoring or an exact air-packet count.

## Synthetic validation

```sh
python3 -m unittest discover -s tests -p test_ble_dumpcap_monitor.py -v
```

Ten tests cover byte order, timestamps, single-byte fragmented input, privacy
redaction, marker match without byte publication, truncation, malformed formats,
buffer limits, process errors, deadlines, record bounds and child reaping.
Synthetic producer processes emit only synthetic stdout data and never open a
Bluetooth or network interface. The firmware-tools worktree imports the
already-integrated sanitizer through the main repository's tools directory
on `PYTHONPATH`; integrated tests need no additional path setup.

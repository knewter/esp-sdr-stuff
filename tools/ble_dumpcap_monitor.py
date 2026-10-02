#!/usr/bin/env python3
"""Bounded dumpcap-to-pipe Bluetooth Monitor fallback; store sanitized metadata only."""
import argparse
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import struct
import subprocess
import time

from ble_hci_monitor import sanitized_packet

MAX_PACKET = 65539  # Four-byte DLT254 header plus uint16-sized HCI payload.
MAX_RECORDS = 10000
MAGICS = {b'\xd4\xc3\xb2\xa1': ('<', 1000000), b'\xa1\xb2\xc3\xd4': ('>', 1000000),
          b'\x4d\x3c\xb2\xa1': ('<', 1000000000), b'\xa1\xb2\x3c\x4d': ('>', 1000000000)}


class PcapError(ValueError):
    """Messages are fixed codes, never packet contents or raw diagnostics."""


class MonitorPcap:
    def __init__(self):
        self.buffer = bytearray()
        self.order = None
        self.time_units = None
        self.snaplen = None
        self.total_packets = 0
        self.truncated_packets = 0
        self.kind_counts = {}

    def feed(self, chunk):
        # Caller reads at most64KiB; a partial packet can span two reads.
        if len(chunk) > 65536 or len(self.buffer) + len(chunk) > MAX_PACKET + 16 + 65536:
            raise PcapError('buffer_bound')
        self.buffer.extend(chunk)
        if self.order is None:
            if len(self.buffer) < 24:
                return []
            mode = MAGICS.get(bytes(self.buffer[:4]))
            if mode is None:
                raise PcapError('unsupported_pcap_magic')
            order, units = mode
            major, minor, _, _, snaplen, linktype = struct.unpack_from(order+'HHIIII', self.buffer, 4)
            if (major, minor) != (2, 4) or linktype != 254:
                raise PcapError('unsupported_version_or_linktype')
            if not 4 <= snaplen <= MAX_PACKET:
                raise PcapError('invalid_snaplen')
            self.order, self.time_units, self.snaplen = order, units, snaplen
            del self.buffer[:24]
        records = []
        while len(self.buffer) >= 16:
            seconds, fraction, captured, original = struct.unpack_from(self.order+'IIII', self.buffer)
            if fraction >= self.time_units or captured > self.snaplen or captured > original or original > MAX_PACKET:
                raise PcapError('invalid_packet_length_or_timestamp')
            if len(self.buffer) < 16+captured:
                break
            packet = bytes(self.buffer[16:16+captured])
            del self.buffer[:16+captured]
            self.total_packets += 1
            if captured != original:
                self.truncated_packets += 1
                continue
            if len(packet) < 4:
                raise PcapError('short_monitor_header')
            # libpcap strips kernel <opcode,index,len>, replacing it with
            # network-order adapter_id,opcode. HCI payload remains unchanged.
            adapter, opcode = struct.unpack_from('>HH', packet)
            key = str(opcode)
            self.kind_counts[key] = self.kind_counts.get(key, 0)+1
            kernel_frame = struct.pack('<HHH', opcode, adapter, len(packet)-4)+packet[4:]
            result = sanitized_packet(kernel_frame)
            if result is not None:
                result['capture_timestamp_ns'] = seconds*1000000000+fraction*(1000000000//self.time_units)
                result['monotonic_ns'] = time.monotonic_ns()
                records.append(result)
        return records

    def finish(self):
        if self.order is None or self.buffer:
            raise PcapError('incomplete_pcap_stream')


def dumpcap_command(seconds):
    executable = os.environ.get('DUMPCAP') or shutil.which('dumpcap')
    if not executable:
        raise FileNotFoundError('dumpcap is missing; enter the Nix development shell')
    return [executable, '-i', 'bluetooth-monitor', '-P', '-Q',
            '-s', str(MAX_PACKET), '-a', f'duration:{seconds:g}', '-w', '-']


def capture_command(command, seconds, grace=5, record_limit=MAX_RECORDS, producer_cleanup=None):
    """Run a bounded producer. Tests substitute a synthetic stdout-only process."""
    parser = MonitorPcap()
    record = {'schema': 1, 'kind': 'read-only sanitized HCI0 advertising control',
              'transport': 'dumpcap classic-pcap stdout pipe', 'hci_channel': 2,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'independently_observed_air_emission_count': None, 'records': [],
              'raw_capture_written_to_disk': False, 'dumpcap_stderr_retained': False,
              'limitations': 'HCI control-plane evidence only. Unknown monitor/socket loss. Unrelated traffic and addresses discarded before storage; libpcap Bluetooth monitor statistics cannot prove loss-free capture.'}
    proc = None
    started = time.monotonic()
    status = 'starting'
    interrupted = False
    def request_stop(signum, _):
        nonlocal interrupted
        interrupted = True
    previous_handlers = {sig: signal.signal(sig, request_stop)
                         for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, bufsize=0)
        print('MONITOR_STARTING dumpcap stdout pipe; capture readiness pending', flush=True)
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            until = started+seconds+grace
            ready_announced = False
            while True:
                if interrupted:
                    status = 'interrupted'
                    break
                if time.monotonic() >= until:
                    status = 'host_deadline'
                    break
                events = selector.select(min(.2, max(0, until-time.monotonic())))
                if not events:
                    continue
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    parser.finish()
                    status = 'completed'
                    break
                incoming = parser.feed(chunk)
                if parser.order is not None and not ready_announced:
                    record['validated_header_ready_monotonic_ns'] = time.monotonic_ns()
                    print('MONITOR_READY validated DLT254 pcap header; sanitized metadata only', flush=True)
                    ready_announced = True
                remaining = record_limit-len(record['records'])
                record['records'].extend(incoming[:remaining])
                if len(record['records']) >= record_limit:
                    status = 'record_bound'
                    break
    except PcapError as error:
        status = 'invalid_pcap'
        record['parser_error_code'] = str(error)
    except OSError as error:
        status = 'producer_or_pipe_error'
        record['error_errno'] = error.errno
    finally:
        # Managed signals only request stop, including repeated cancellation
        # during exact-name container removal and producer reaping.
        try:
            if producer_cleanup is not None:
                try:
                    record['owned_container_removed'] = bool(producer_cleanup())
                except Exception:
                    record['owned_container_removed'] = False
                if not record['owned_container_removed']:
                    status = 'container_cleanup_failed'
        finally:
            try:
                if proc is not None:
                    if proc.poll() is None:
                        if status == 'completed':
                            try:
                                proc.wait(timeout=1)
                            except subprocess.TimeoutExpired:
                                status = 'producer_not_closed'
                        if proc.poll() is None:
                            proc.terminate()
                            try:
                                proc.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                                proc.wait(timeout=2)
                    record['producer_returncode'] = proc.returncode
                    proc.stdout.close()
            finally:
                parser.buffer.clear()
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)
    if interrupted and status == 'completed':
        status = 'interrupted'
    record['interrupted'] = interrupted
    if status == 'completed' and record.get('producer_returncode') != 0:
        status = 'producer_failed'
    record.update(status=status, elapsed_s=time.monotonic()-started,
                  packet_counts_by_monitor_kind=parser.kind_counts,
                  pcap_packets_seen=parser.total_packets,
                  snaplen_truncated_packets_discarded=parser.truncated_packets,
                  pcap_byte_order=parser.order, pcap_timestamp_units_per_second=parser.time_units,
                  producer_reaped=proc is not None and proc.poll() is not None)
    return record


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--seconds', type=float, default=60)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    if not .1 <= args.seconds <= 3600 or args.output.exists():
        cli.error('Use bounded seconds and a fresh output path')
    record = capture_command(dumpcap_command(args.seconds), args.seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as sink:
        json.dump(record, sink, indent=2)
        sink.write('\n')
    print(f'MONITOR_CLOSED status={record["status"]} sanitized_records={len(record["records"])}', flush=True)
    raise SystemExit(0 if record['status'] == 'completed' else 2)


if __name__ == '__main__':
    main()

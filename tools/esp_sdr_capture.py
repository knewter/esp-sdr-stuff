#!/usr/bin/env python3
"""CRC-checked ESPARGOS protocol-6 snapshots. Operates only the confirmed CP2102.

No flash writes. Raw RF payloads are kept in ignored .scratch/ by default.
Public output consists of settings, CRCs, timing and anonymous numerical statistics.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import zlib

SOURCE_REVISION = '550fadea4d00a9e26ce921c5832167becb3dc20c'
STABLE_PORT = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
RATE_CODES = {80000000: 0, 40000000: 1, 16000000: 6}


class ProtocolError(RuntimeError):
    pass


class ReadPrefix:
    """An exact read failed; caller-observed bytes remain available privately.

    The underlying read may itself have consumed bytes before raising. Those
    unreturned bytes cannot be reconstructed and are explicitly unknown.
    """
    def __init__(self, partial, expected_bytes, reason, cause=None):
        self.partial = bytes(partial)
        self.expected_bytes = expected_bytes
        self.reason = reason
        self.read_error_kind = type(cause).__name__ if cause is not None else None
        self.failure_ns = time.monotonic_ns()
        self.unreturned_read_bytes_unknown = cause is not None
        message = (f'short payload: {len(self.partial)}/{expected_bytes}'
                   if reason == 'empty_read' else f'exact read failed: {reason}')
        super().__init__(message)


class PartialReadError(ReadPrefix, TimeoutError):
    """Empty/unterminated read, compatible with existing TimeoutError callers."""


class PartialReadException(ReadPrefix, OSError):
    """Transport/read exception, with its original cause and observed prefix."""


def exact(port, size):
    if not isinstance(size, int) or size < 0:
        raise ValueError('exact read size must be a nonnegative integer')
    data = bytearray()
    while len(data) < size:
        try:
            chunk = port.read(size - len(data))
        except BaseException as error:
            if isinstance(error, Exception):
                raise PartialReadException(data, size, 'read_exception', error) from error
            # Keep cancellation semantics while making delivered bytes
            # available to finally-based private retention/closure.
            error.partial = bytes(data)
            error.expected_bytes = size
            error.reason = 'read_interrupted'
            error.read_error_kind = type(error).__name__
            error.failure_ns = time.monotonic_ns()
            error.unreturned_read_bytes_unknown = True
            raise
        if not chunk:
            raise PartialReadError(data, size, 'empty_read')
        data.extend(chunk)
        if len(data) > size:
            raise PartialReadError(data, size, 'overlong_read')
    return bytes(data)


def raw_line(port):
    try:
        raw = port.read_until(b'\n', 8192)
    except BaseException as error:
        error.unreturned_read_bytes_unknown = True
        error.read_error_kind = type(error).__name__
        error.failure_ns = time.monotonic_ns()
        error.reason = 'reply_read_exception'
        raise
    if not raw.endswith(b'\n'):
        raise PartialReadError(raw, None, 'unterminated_reply')
    return raw


def line(port):
    return raw_line(port).decode('ascii', errors='strict').strip()


def write_private(path, data):
    """Keep a fresh private file; retain any disk-error prefix, never overwrite."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        if stream.write(data) != len(data):
            raise OSError('private write was incomplete')
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data:
        raise OSError('private saved bytes differ from consumed bytes')


def attach_capture_failure(error, context, payload=b'', raw_header=b''):
    """Exception bytes are private; the attached receipt contains safe scalars."""
    info = dict(context)
    failure_ns = error.failure_ns if hasattr(error, 'failure_ns') else time.monotonic_ns()
    info.update(failure_kind=type(error).__name__, failure_ns=failure_ns,
                received_payload_bytes=len(payload), private_payload_prefix_sha256=hashlib.sha256(payload).hexdigest(),
                prefix_crc32=f'{zlib.crc32(payload):08x}', private_header_bytes=len(raw_header),
                private_header_sha256=hashlib.sha256(raw_header).hexdigest(),
                read_failure_reason=getattr(error, 'reason', None),
                underlying_read_error_kind=getattr(error, 'read_error_kind', None),
                unreturned_read_bytes_unknown=getattr(error, 'unreturned_read_bytes_unknown', False))
    # Neither an incomplete-prefix CRC nor a complete-but-unsaved read enters
    # the successful receiver CSV. Full validity, if known, is separately named.
    error.capture_failure = info
    error.private_payload_prefix = bytes(payload)
    error.private_header = bytes(raw_header)
    return info


def retain_capture_failure(private, stem, error):
    """Persist consumed bytes and a receipt; a failure here stays explicit."""
    info = dict(error.capture_failure)
    info['retention_status'] = 'attempted'
    paths = {'payload_prefix': stem + '.payload-prefix.bin', 'header': stem + '.header.bin',
             'metadata': stem + '.json'}
    try:
        write_private(private / paths['payload_prefix'], error.private_payload_prefix)
        write_private(private / paths['header'], error.private_header)
        info.update(retention_status='verified_saved', private_files=paths)
        write_private(private / paths['metadata'], (json.dumps(info, indent=2) + '\n').encode())
    except Exception as failure:
        info.update(retention_status='failed', retention_error_kind=type(failure).__name__)
        # A disk failure cannot be repaired by issuing another capture. Keep
        # any created prefix files and the original exception's bytes in memory.
    return info


def command(port, request):
    raw = b''
    try:
        port.write((request + '\n').encode('ascii'))
        port.flush()
        raw = raw_line(port)
        reply = raw.decode('ascii', errors='strict').strip()
        if reply.startswith('ERR '):
            raise ProtocolError(reply)
        return reply
    except BaseException as error:
        # Preserve default exception semantics; consuming callers may retain
        # this attribute privately without reproducing raw text publicly.
        error.private_reply = getattr(error, 'partial', raw)
        raise


def synchronize(port, seconds=5):
    """Recover from UART-open reset without leaving queued SYNC replies.

    Some CP2102 open sequences reset the MCU despite inactive modem lines.
    Requests sent during boot can be lost. Retry unique nonces, then fence all
    outstanding requests with one final ordered nonce before returning.
    """
    if seconds <= 0:
        raise ValueError('Synchronization deadline must be positive')
    original_timeout = port.timeout
    deadline = time.monotonic() + seconds
    retry_at = time.monotonic()
    counter = time.monotonic_ns() & ((1 << 63) - 1)
    pending = set()
    fence = None
    buffered = bytearray()

    def request():
        nonlocal counter
        counter = (counter + 1) & ((1 << 63) - 1)
        response = f'SYNC {counter}'.encode('ascii')
        port.write(b'\n' + response + b'\n')
        port.flush()
        return response

    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if fence is None and now >= retry_at:
                pending.add(request())
                retry_at = now + .25
            port.timeout = min(.05, max(0, deadline - time.monotonic()))
            buffered.extend(port.read(4096))
            while b'\n' in buffered:
                end = buffered.index(b'\n')
                response = bytes(buffered[:end]).strip()
                del buffered[:end + 1]
                if fence is not None and response == fence:
                    # No requests are sent after the fence. UART command order
                    # means every earlier retry/reply has now been consumed.
                    return
                if fence is None and response in pending:
                    fence = request()
            # During recovery, incomplete binary payloads or startup noise may
            # not contain newline. Bound memory without clearing live UART RX.
            if len(buffered) > 65536:
                del buffered[:-8192]
        raise TimeoutError('SYNC acknowledgement missing before startup deadline')
    finally:
        port.timeout = original_timeout


def open_board(path, baud=2000000, timeout=3):
    import serial
    from serial.tools import list_ports
    stable = Path(path)
    if not str(stable).startswith('/dev/serial/by-id/') or not stable.is_symlink():
        raise RuntimeError('Use the confirmed stable /dev/serial/by-id CP2102 path')
    actual = stable.resolve()
    matches = [p for p in list_ports.comports() if Path(p.device).resolve() == actual]
    if len(matches) != 1 or (matches[0].vid, matches[0].pid) != (0x10c4, 0xea60):
        raise RuntimeError('Stable path does not resolve to the expected Silicon Labs CP2102')
    port = serial.Serial(port=None, baudrate=baud, timeout=timeout, exclusive=True)
    # Setting lines before opening prevents intentionally pulsing EN/BOOT.
    port.dtr = port.rts = False
    port.port = str(stable)
    port.open()
    # Classic CP2102 silently clamps requests above1M in Linux. Check the
    # accepted termios speed, not pyserial's cached requested baud value.
    try:
        import termios
        expected = getattr(termios, f'B{baud}', None)
        speeds = termios.tcgetattr(port.fileno())[4:6]
        if expected is not None and speeds != [expected, expected]:
            raise RuntimeError('Kernel accepted a different UART baud rate; use a compatible firmware default and matching host baud')
    except Exception:
        port.close()
        raise
    return port


def queries(port):
    result = {q: command(port, q) for q in ['INFO', 'CAPS', 'LIMITS?', 'RANGE?', 'TRANSPORT?', 'SPECINFO?', 'GAIN?', 'BAUD?']}
    if result['INFO'] != 'ESP32SDR 6 burst 16380':
        raise RuntimeError('Unexpected firmware identity; original ESP32 protocol 6 required')
    if not result['LIMITS?'].startswith('LIMITS '):
        raise ProtocolError('Malformed LIMITS')
    result['parsed_limits'] = json.loads(result['LIMITS?'][7:])
    return result


def settings(port, frequency=2412, bandwidth=20, gain='hardware'):
    requests = [f'FREQ {frequency}', f'BANDWIDTH {bandwidth}', 'GAIN HARDWARE' if gain == 'hardware' else f'GAIN MANUAL {int(gain)}']
    replies = {}
    for request in requests:
        reply = command(port, request)
        if reply != 'OK':
            raise ProtocolError(f'unexpected setting response: {reply}')
        replies[request] = reply
    return replies


def capture(port, samples, rate, bits):
    code = RATE_CODES[rate]
    t0 = time.monotonic_ns()
    request = f'CAP{bits * 2} {samples} {code}'
    context = {'stage': 'command', 'capture_command': request, 'command_start_ns': t0,
               'requested_samples': samples, 'rate_hz': rate, 'bits_per_component': bits,
               'header_received_ns': None, 'expected_payload_bytes': None,
               'payload_complete': False, 'framing_uncertain': True}
    raw_header = b''
    try:
        context['command_write_bytes_returned'] = port.write((request + '\n').encode('ascii'))
        port.flush()
        context['command_flush_returned'] = True
        context['stage'] = 'header'
        raw_header = raw_line(port)
        t1 = time.monotonic_ns()
        context['header_received_ns'] = t1
        header = raw_header.decode('ascii', errors='strict').strip()
        if header.startswith('ERR '):
            raise ProtocolError('firmware rejected capture command')
        match = re.fullmatch(r'DATA (\d+) ([0-9a-fA-F]{8}) (\d+)', header)
        if not match:
            raise ProtocolError('bad DATA header')
        n, expected, hardware_us = int(match[1]), int(match[2], 16), int(match[3])
        context.update(returned_samples=n, expected_crc32=f'{expected:08x}', firmware_capture_us=hardware_us)
        if not 256 <= n <= 16380:
            raise ProtocolError('unsafe returned sample count')
        context.update(stage='payload', expected_payload_bytes=(n * bits * 2 + 7) // 8)
        payload = exact(port, context['expected_payload_bytes'])
    except BaseException as error:
        partial = getattr(error, 'partial', b'')
        attach_capture_failure(error, context,
                               partial if context['stage'] == 'payload' else b'',
                               partial if context['stage'] == 'header' and partial else raw_header)
        raise
    t2 = time.monotonic_ns()
    actual = zlib.crc32(payload)
    return payload, {'returned_samples': n, 'expected_crc32': f'{expected:08x}',
                     'actual_crc32': f'{actual:08x}', 'crc_ok': expected == actual,
                     'sample_count_ok': n == samples, 'firmware_capture_us': hardware_us,
                     'command_start_ns': t0, 'header_received_ns': t1, 'payload_received_ns': t2,
                     'round_trip_ms': (t2 - t0) / 1e6, 'payload_transfer_ms': (t2 - t1) / 1e6,
                     'nominal_rf_window_us': n / rate * 1e6}


def unpack(payload, samples, bits):
    import numpy as np
    if len(payload) != math.ceil(samples * 2 * bits / 8):
        raise ValueError('payload size mismatch')
    if bits == 8:
        components = np.frombuffer(payload, dtype=np.int8).astype(np.float64)
    elif bits == 10:
        # Firmware packs each 20-bit I/Q word least significant bit first.
        words = np.unpackbits(np.frombuffer(payload, dtype=np.uint8), bitorder='little')[:samples * 20]
        values = words.reshape(samples * 2, 10).dot(1 << np.arange(10))
        components = np.where(values >= 512, values - 1024, values).astype(np.float64)
    else:
        raise ValueError('bits must be 8 or 10')
    return components[::2] + 1j * components[1::2]


def numerical_stats(payload, samples, bits):
    import numpy as np
    iq = unpack(payload, samples, bits)
    full = 2 ** (bits - 1)
    power = float(np.mean(np.abs(iq) ** 2))
    centered = iq - np.mean(iq)
    return {'mean_i': float(iq.real.mean()), 'mean_q': float(iq.imag.mean()),
            'mean_power_codes_squared': power,
            'ac_power_codes_squared': float(np.mean(np.abs(centered) ** 2)),
            'component_endpoint_fraction': float(np.mean((np.column_stack([iq.real, iq.imag]) == -full) | (np.column_stack([iq.real, iq.imag]) == full - 1))),
            'unique_i_codes': int(len(np.unique(iq.real))), 'unique_q_codes': int(len(np.unique(iq.imag)))}


def run_snapshots(port, output, private, count, samples, bits_list, rates, config, artifact_revision):
    output.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False, mode=0o700)
    provenance = {'schema': 1, 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'firmware_source_revision_asserted_from_install_record': artifact_revision,
                  'firmware_source_base_revision': SOURCE_REVISION,
                  'firmware_revision_is_not_returned_by_INFO': True,
                  'settings': config, 'protocol_queries': queries(port), 'runs': [], 'completed': False,
                  'timing_note': 'Host monotonic command and receive timestamps; no synchronized hardware capture-start timestamp. Nominal RF windows use advertised sample rates, not calibrated clocks.'}
    advertised = provenance['protocol_queries']['parsed_limits']['rates']
    if any(rate not in advertised for rate in rates):
        raise RuntimeError('Requested rate not advertised by connected board')
    settings(port, **config)
    previous = None
    series_start = time.monotonic_ns()
    rows = []
    terminal_failure = None
    try:
        for bits in bits_list:
            for rate in rates:
                for attempt in range(count):
                    row = {'bits_per_component': bits, 'rate_hz': rate, 'attempt': attempt,
                           'requested_samples': samples, 'status': 'error'}
                    t0 = time.monotonic_ns()
                    payload = measured = None
                    try:
                        payload, measured = capture(port, samples, rate, bits)
                        row.update(measured)
                        row['status'] = 'ok' if measured['crc_ok'] and measured['sample_count_ok'] else 'integrity_failure'
                        row['private_payload_sha256'] = hashlib.sha256(payload).hexdigest()
                        write_private(private / f'iq-{rate}-{bits}-{attempt:04d}.bin', payload)
                        if row['status'] == 'ok':
                            row.update(numerical_stats(payload, row['returned_samples'], bits))
                        if previous is not None:
                            row['host_command_interval_ms'] = (row['command_start_ns'] - previous) / 1e6
                        previous = row['command_start_ns']
                    except BaseException as error:
                        terminal_failure = error
                        if not hasattr(error, 'capture_failure'):
                            context = {'stage': 'private_payload_or_processing', 'payload_complete': payload is not None,
                                       'framing_uncertain': payload is None, 'command_start_ns': t0}
                            if measured is not None:
                                context.update(measured)
                                context['full_read_crc_and_count_valid'] = bool(measured['crc_ok'] and measured['sample_count_ok'])
                                context['expected_payload_bytes'] = len(payload)
                            attach_capture_failure(error, context, payload or b'')
                        row['status'] = 'error'
                        row['error_kind'] = type(error).__name__
                        # Never turn a failed fragment into a CRC/count row or
                        # discard its tail by resynchronizing and retrying.
                        row['command_start_ns'] = error.capture_failure.get('command_start_ns', t0)
                        row['failure_ns'] = error.capture_failure['failure_ns']
                        try:
                            port.close()
                            error.serial_close_returned = True
                            error.capture_failure['port_close'] = 'returned'
                        except Exception as cleanup:
                            error.capture_failure['port_close_error_kind'] = type(cleanup).__name__
                        provenance['terminal_failure'] = retain_capture_failure(
                            private, f'failed-{rate}-{bits}-{attempt:04d}', error)
                        raise
                    finally:
                        for key in ['command_start_ns', 'header_received_ns', 'payload_received_ns', 'failure_ns']:
                            if key in row:
                                row[key.replace('_ns', '_relative_ms')] = (row.pop(key) - series_start) / 1e6
                        rows.append(row)
                        if attempt % 10 == 0:
                            print(f'rate={rate} bits={bits} attempt={attempt + 1}/{count} status={row["status"]}', flush=True)
        provenance['completed'] = True
    finally:
        try:
            publish_snapshots(output, provenance, rows, bits_list, rates, count)
        except Exception as publication:
            if terminal_failure is None:
                raise
            terminal_failure.publication_error_kind = type(publication).__name__
            terminal_failure.add_note("Terminal receipt publication failed: " + type(publication).__name__)
    return all(run['success'] == count for run in provenance['runs'])


def publish_snapshots(output, provenance, rows, bits_list, rates, count):
    columns = sorted({key for row in rows for key in row})
    with (output / 'snapshots.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)
    provenance['ended_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    for bits in bits_list:
        for rate in rates:
            group = [r for r in rows if r['bits_per_component'] == bits and r['rate_hz'] == rate]
            good = [r for r in group if r['status'] == 'ok']
            wall_ms = max((r.get('payload_received_relative_ms', r.get('command_start_relative_ms', 0)) for r in group), default=0) - min((r.get('command_start_relative_ms', 0) for r in group), default=0)
            provenance['runs'].append({'bits': bits, 'rate_hz': rate, 'attempts': len(group), 'success': len(good),
                                       'failures': len(group) - len(good), 'requested_attempts': count,
                                       'wall_ms': wall_ms, 'nominal_sampled_ms': sum(r['nominal_rf_window_us'] / 1000 for r in good),
                                       'nominal_coverage_fraction': sum(r['nominal_rf_window_us'] / 1000 for r in good) / wall_ms if wall_ms else 0})
    (output / 'results.json').write_text(json.dumps(provenance, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default=STABLE_PORT)
    parser.add_argument('--baud', type=int, default=2000000, choices=[115200, 460800, 921600, 1000000, 2000000])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--samples', type=int, default=16380)
    parser.add_argument('--bits', type=int, nargs='+', default=[8, 10], choices=[8, 10])
    parser.add_argument('--rates', type=int, nargs='+', default=[16000000, 40000000, 80000000], choices=RATE_CODES)
    parser.add_argument('--frequency', type=int, default=2412)
    parser.add_argument('--bandwidth', type=int, default=20)
    parser.add_argument('--gain', default='hardware')
    parser.add_argument('--firmware-revision', default=SOURCE_REVISION)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000 or not 256 <= args.samples <= 16380:
        parser.error('count 1..10000 and samples 256..16380 required')
    private = args.private.resolve()
    root = Path(__file__).resolve().parents[1]
    if not any(part in {'.scratch', 'backups'} for part in private.parts):
        parser.error('Raw payload directory must be under ignored .scratch/ or backups/')
    if private.is_relative_to(root / 'site') or private.is_relative_to(root / 'docs'):
        parser.error('Private payloads cannot be stored under published roots')
    port = open_board(args.port, args.baud)
    failure = None
    try:
        synchronize(port)
        ok = run_snapshots(port, args.output, private, args.count, args.samples, args.bits, args.rates,
                           {'frequency': args.frequency, 'bandwidth': args.bandwidth, 'gain': args.gain}, args.firmware_revision)
    except BaseException as error:
        failure = error
        raise
    finally:
        try:
            if not getattr(failure, 'serial_close_returned', False) and (failure is None or not getattr(failure, 'capture_failure', {}).get('framing_uncertain', False)):
                command(port, 'RELEASE')
        except Exception:
            pass
        if not getattr(failure, 'serial_close_returned', False):
            try:
                port.close()
            except Exception as cleanup:
                if failure is None:
                    raise
                failure.serial_close_error_kind = type(cleanup).__name__
                failure.add_note('Serial closure failed: ' + type(cleanup).__name__)
    raise SystemExit(0 if ok else 2)


if __name__ == '__main__':
    main()

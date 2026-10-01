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
from pathlib import Path
import re
import time
import zlib

SOURCE_REVISION = '550fadea4d00a9e26ce921c5832167becb3dc20c'
STABLE_PORT = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
RATE_CODES = {80000000: 0, 40000000: 1, 16000000: 6}


class ProtocolError(RuntimeError):
    pass


def exact(port, size):
    data = bytearray()
    while len(data) < size:
        chunk = port.read(size - len(data))
        if not chunk:
            raise TimeoutError(f'short payload: {len(data)}/{size}')
        data.extend(chunk)
    return bytes(data)


def line(port):
    raw = port.read_until(b'\n', 8192)
    if not raw.endswith(b'\n'):
        raise TimeoutError('unterminated protocol reply')
    return raw.decode('ascii', errors='strict').strip()


def command(port, request):
    port.write((request + '\n').encode('ascii'))
    port.flush()
    reply = line(port)
    if reply.startswith('ERR '):
        raise ProtocolError(reply)
    return reply


def synchronize(port, seconds=5):
    # No reset_input_buffer while a reply may still be arriving: find a unique
    # acknowledgement after all outstanding bytes, then clear only known text.
    nonce = time.monotonic_ns() & ((1 << 63) - 1)
    port.write(f'\nSYNC {nonce}\n'.encode('ascii'))
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        raw = port.read_until(b'\n', 65536)
        if raw.strip() == f'SYNC {nonce}'.encode():
            return
    raise TimeoutError('SYNC acknowledgement missing')


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
    header = command(port, f'CAP{bits * 2} {samples} {code}')
    t1 = time.monotonic_ns()
    match = re.fullmatch(r'DATA (\d+) ([0-9a-fA-F]{8}) (\d+)', header)
    if not match:
        raise ProtocolError(f'bad DATA header: {header}')
    n, expected, hardware_us = int(match[1]), int(match[2], 16), int(match[3])
    if not 256 <= n <= 16380:
        raise ProtocolError('unsafe returned sample count')
    payload = exact(port, (n * bits * 2 + 7) // 8)
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
    private.mkdir(parents=True, exist_ok=False)
    provenance = {'schema': 1, 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'firmware_source_revision_asserted_from_install_record': artifact_revision,
                  'firmware_revision_is_not_returned_by_INFO': True,
                  'settings': config, 'protocol_queries': queries(port), 'runs': [],
                  'timing_note': 'Host monotonic command and receive timestamps; no synchronized hardware capture-start timestamp. Nominal RF windows use advertised sample rates, not calibrated clocks.'}
    advertised = provenance['protocol_queries']['parsed_limits']['rates']
    if any(rate not in advertised for rate in rates):
        raise RuntimeError('Requested rate not advertised by connected board')
    settings(port, **config)
    previous = None
    series_start = time.monotonic_ns()
    rows = []
    try:
        for bits in bits_list:
            for rate in rates:
                for attempt in range(count):
                    row = {'bits_per_component': bits, 'rate_hz': rate, 'attempt': attempt,
                           'requested_samples': samples, 'status': 'error'}
                    t0 = time.monotonic_ns()
                    try:
                        payload, measured = capture(port, samples, rate, bits)
                        row.update(measured)
                        row['status'] = 'ok' if measured['crc_ok'] and measured['sample_count_ok'] else 'integrity_failure'
                        row['private_payload_sha256'] = hashlib.sha256(payload).hexdigest()
                        (private / f'iq-{rate}-{bits}-{attempt:04d}.bin').write_bytes(payload)
                        if row['status'] == 'ok':
                            row.update(numerical_stats(payload, row['returned_samples'], bits))
                        if previous is not None:
                            row['host_command_interval_ms'] = (row['command_start_ns'] - previous) / 1e6
                        previous = row['command_start_ns']
                    except (ProtocolError, TimeoutError, UnicodeError) as error:
                        row['error_kind'] = type(error).__name__
                        row['error'] = str(error)[:240]
                        row['command_start_ns'] = t0
                        try:
                            synchronize(port)
                        except Exception as recovery:
                            row['recovery_failed'] = type(recovery).__name__
                            raise
                    finally:
                        for key in ['command_start_ns', 'header_received_ns', 'payload_received_ns']:
                            if key in row:
                                row[key.replace('_ns', '_relative_ms')] = (row.pop(key) - series_start) / 1e6
                        rows.append(row)
                        if attempt % 10 == 0:
                            print(f'rate={rate} bits={bits} attempt={attempt + 1}/{count} status={row["status"]}', flush=True)
    finally:
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
    return all(run['success'] == count for run in provenance['runs'])


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
    try:
        synchronize(port)
        ok = run_snapshots(port, args.output, private, args.count, args.samples, args.bits, args.rates,
                           {'frequency': args.frequency, 'bandwidth': args.bandwidth, 'gain': args.gain}, args.firmware_revision)
    finally:
        try:
            command(port, 'RELEASE')
        except Exception:
            pass
        port.close()
    raise SystemExit(0 if ok else 2)


if __name__ == '__main__':
    main()

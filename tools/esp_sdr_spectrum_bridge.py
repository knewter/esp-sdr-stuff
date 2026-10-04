#!/usr/bin/env python3
"""Live browser spectrum via one host-owned UART, with CRC evidence.

Browser uses localhost HTTP; this is explicitly a UART bridge, not Web Serial.
Device access begins only when the local viewer starts the bounded trial.
"""
import argparse
import csv
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import struct
import threading
import time
import zlib
from esp_sdr_capture import STABLE_PORT, RATE_CODES, SOURCE_REVISION, command, exact, line, raw_line, open_board, queries, settings, synchronize, ProtocolError, ReadPrefix


MAX_RETAINED_STREAM_BYTES = 64 * 1024 * 1024  # Accepted bytes; reject/retain the consumed overflow packet.


class RejectedFrame(ProtocolError):
    """Retain consumed bytes privately without accepting a malformed frame."""
    def __init__(self, message, raw, kind, crc_ok=None, expected_crc=None, actual_crc=None):
        super().__init__(message)
        self.raw = raw
        self.metadata = {'kind': kind, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                         'crc_ok': crc_ok, 'expected_crc32': expected_crc, 'actual_crc32': actual_crc}


def spectrum_frame(port, bins):
    received = bytearray()
    started = time.monotonic_ns()
    magic_received = None
    kind = 'unknown'

    def remember(error, size):
        prefix = bytes(received) + getattr(error, 'partial', b'')
        error.rejected_raw = prefix
        error.rejected_metadata = {
            'kind': kind, 'complete_frame': False, 'bytes': len(prefix),
            'sha256': hashlib.sha256(prefix).hexdigest(), 'crc_ok': None,
            'expected_crc32': None, 'actual_crc32': None,
            'expected_frame_bytes': len(received) + size if size is not None else None,
            'frame_read_start_ns': started, 'magic_received_ns': magic_received,
            'failure_ns': getattr(error, 'failure_ns', None),
            'failure_kind': type(error).__name__,
            'read_failure_reason': getattr(error, 'reason', None),
            'underlying_read_error_kind': getattr(error, 'read_error_kind', None),
            'unreturned_read_bytes_unknown': getattr(error, 'unreturned_read_bytes_unknown', False)}

    def piece(size):
        try:
            chunk = exact(port, size)
        except BaseException as error:
            remember(error, size)
            raise
        received.extend(chunk)
        return chunk

    magic = piece(4)
    magic_received = time.monotonic_ns()
    if magic == b'SPEC':
        kind = 'end'
        try:
            tail = raw_line(port)
        except BaseException as error:
            remember(error, None)
            raise
        raw = magic + tail
        try:
            report = raw.decode('ascii', errors='strict').split()
        except UnicodeError as error:
            raise RejectedFrame('invalid SPECEND encoding', raw, 'end') from error
        if len(report) != 13 or report[0] != 'SPECEND':
            raise RejectedFrame('invalid SPECEND report', raw, 'end')
        try:
            values = [int(v) for v in report[1:]]
        except ValueError as error:
            raise RejectedFrame('invalid SPECEND values', raw, 'end') from error
        return {'kind': 'end', 'report': values}, None
    if magic == b'SPS1':
        kind = 'statistics'
        raw = magic + piece(36)
        actual, expected = zlib.crc32(raw[:-4]), int.from_bytes(raw[-4:], 'little')
        if actual != expected:
            raise RejectedFrame('statistics CRC mismatch', raw, 'statistics', False, f'{expected:08x}', f'{actual:08x}')
        return {'kind': 'statistics'}, raw
    if magic != b'SPC1':
        raise RejectedFrame('spectrum framing lost', magic, 'unknown')
    kind = 'spectrum'
    raw = magic + piece(bins + 28)
    expected = int.from_bytes(raw[-4:], 'little')
    actual = zlib.crc32(raw[:-4])
    if actual != expected:
        raise RejectedFrame('spectrum CRC mismatch', raw, 'spectrum', False, f'{expected:08x}', f'{actual:08x}')
    if 1 << raw[26] != bins or raw[27] != 2:
        raise RejectedFrame('unexpected spectrum encoding', raw, 'spectrum', True)
    return {'kind': 'spectrum', 'sequence': int.from_bytes(raw[4:8], 'little'),
            'sample_index': int.from_bytes(raw[8:16], 'little'),
            'samples_processed': int.from_bytes(raw[16:20], 'little'),
            'ffts': int.from_bytes(raw[20:22], 'little'), 'flags': raw[22], 'gain_code': raw[23],
            'crc32': f'{expected:08x}', 'power_codes': list(raw[28:-4])}, raw


def persist_verified(path, data):
    """Persist only after UART closure; verify saved bytes with a bounded read."""
    expected = hashlib.sha256(data).hexdigest()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    if path.write_bytes(data) != len(data):
        raise OSError('private raw write was incomplete')
    actual = hashlib.sha256()
    saved_bytes = 0
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            actual.update(chunk)
            saved_bytes += len(chunk)
    if saved_bytes != len(data) or actual.hexdigest() != expected:
        raise OSError('private raw write verification failed')
    return {'bytes': saved_bytes, 'sha256': expected}


HTML = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Measured ESP32 spectrum</title><style>
body{background:#09151c;color:#dce7ed;font:17px system-ui;margin:32px auto;max-width:1120px;padding:0 20px}h1{font-size:42px}p{line-height:1.5}small{color:#a3bac5}button{background:#83e1bd;padding:14px 24px;border:0;border-radius:8px;font-weight:bold}canvas{width:100%;height:360px;background:#0c202a;border:1px solid #446170}pre{white-space:pre-wrap;padding:16px;background:#0c202a}strong{color:#83e1bd}</style>
<h1>ESP32: a measured spectrum</h1><p><strong>Live hardware trial · host UART bridge</strong><br>This viewer receives CRC-checked on-device FFT frames from the confirmed original ESP32. The browser communicates with localhost HTTP; the host owns the CP2102 UART. Each update averages separately acquired FFT snapshots, with reception gaps between windows and updates.</p>
<p id="settings"></p><button id="start">Start bounded trial</button><p id="status">Ready. No device handle is open.</p><canvas width="1080" height="360" id="spectrum"></canvas><small>X: frequency in MHz. Y: firmware power code 0–255 (uncalibrated, not dBm). No signal identification is inferred.</small><pre id="stats"></pre><script>
const c=document.querySelector('canvas'),x=c.getContext('2d');let active=false;
function draw(s){x.clearRect(0,0,c.width,c.height);x.font='15px monospace';x.fillStyle='#a3bac5';for(let j=0;j<5;j++){let xx=55+j*(c.width-85)/4;x.fillText((s.frequency_mhz+(j/4-.5)*s.rate_hz/1e6).toFixed(1),xx-20,c.height-12);x.strokeStyle='#28424f';x.beginPath();x.moveTo(xx,20);x.lineTo(xx,c.height-36);x.stroke()}for(let j=0;j<5;j++){let yy=20+j*(c.height-56)/4;x.fillText(String(Math.round(255*(1-j/4))),10,yy+5)}if(!s.power_codes)return;x.strokeStyle='#83e1bd';x.lineWidth=2;x.beginPath();let n=s.power_codes.length;for(let j=0;j<n;j++){let yy=20+(255-s.power_codes[(j+n/2)%n])*(c.height-56)/255,xx=55+j*(c.width-85)/(n-1);j?x.lineTo(xx,yy):x.moveTo(xx,yy)}x.stroke()}
async function poll(){let s=await(await fetch('/state')).json();document.querySelector('#settings').textContent=`${s.frequency_mhz}MHz · ${s.rate_hz/1e6}MS/s nominal · ${s.bins} FFT bins · ${s.ffts_per_frame} FFT windows averaged per update · hardware AGC · ${s.duration_seconds}s requested`;
document.querySelector('#status').textContent=s.status;document.querySelector('#stats').textContent=JSON.stringify({frames:s.frames,crc_failures:s.crc_failures,elapsed_seconds:s.elapsed_seconds,snapshot_gap_flag:s.snapshot_gap_flag,nominal_coverage_fraction:s.nominal_coverage_fraction,error:s.error},null,2);draw(s);setTimeout(poll,200)}
document.querySelector('#start').onclick=async()=>{document.querySelector('#start').disabled=true;await fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})};poll();
</script></html>'''


class Trial:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.state = {'status': 'Ready', 'frames': 0, 'crc_failures': 0, 'elapsed_seconds': 0,
                      'frequency_mhz': args.frequency, 'rate_hz': args.rate, 'bins': args.bins,
                      'ffts_per_frame': getattr(args, 'ffts_per_frame', 1),
                      'duration_seconds': args.seconds, 'transport': 'host UART bridge, localhost HTTP browser'}
        self.started = False

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def start(self):
        with self.lock:
            if self.started:
                return False
            self.started = True
        threading.Thread(target=self.run, daemon=True).start()
        return True

    def run(self):
        a = self.args
        port = None
        output_created = False
        private_created = False
        rows = []
        sampled = ffts = 0
        retained = bytearray()
        rejected = None
        interrupted = None
        acquisition_started = False
        t0 = None
        expected_ffts = getattr(a, 'ffts_per_frame', 1)
        record = {'schema': 1, 'firmware_revision_asserted_from_install_record': getattr(a, 'firmware_revision', SOURCE_REVISION),
                  'firmware_source_base_revision': SOURCE_REVISION,
                  'browser_transport': 'localhost HTTP polling a host UART reader; not native Web Serial',
                  'settings': {'frequency_mhz': a.frequency, 'rate_hz': a.rate, 'bins': a.bins, 'gain': a.gain,
                               'ffts_per_frame': expected_ffts, 'detector': 'mean power over separately acquired FFT snapshots',
                               'bandwidth_mhz': a.bandwidth, 'seconds_requested': a.seconds},
                  'private_stream_retention': 'bounded RAM; persisted only after UART closure',
                  'private_stream_memory_cap_bytes': MAX_RETAINED_STREAM_BYTES,
                  'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'limitations': 'Snapshot FFTs contain gaps. Codes are uncalibrated. Hardware nominal clock and synthesized sample index do not independently prove actual sample rate.'}
        try:
            a.output.mkdir(parents=True, exist_ok=False)
            output_created = True
            a.private.mkdir(parents=True, exist_ok=False, mode=0o700)
            private_created = True
            port = open_board(a.port, a.baud)
            synchronize(port)
            record['queries'] = queries(port)
            record['setting_replies'] = settings(port, a.frequency, a.bandwidth, a.gain)
            if not 1 <= expected_ffts <= 8:
                raise ValueError('FFT windows per frame must be 1..8')
            record['start_command_ns'] = time.monotonic_ns()
            profile = command(port, f'SPEC {a.seconds * 1000} 1 {expected_ffts} 0 {RATE_CODES[a.rate]} {a.bins} 1').split()
            record['start_reply_received_ns'] = time.monotonic_ns()
            if len(profile) != 5 or profile[0] != 'SPEC' or [int(v) for v in profile[1:]] != [a.bins, a.rate, a.bins, a.frequency]:
                raise ProtocolError('spectrum start does not match requested settings')
            t0 = time.monotonic()
            previous = -1
            sampled = 0
            ffts = 0
            acquisition_started = True
            self.update(status='Acquiring real hardware spectra')
            while True:
                frame, raw = spectrum_frame(port, a.bins)
                elapsed = time.monotonic() - t0
                if frame['kind'] == 'end':
                    record['end_report'] = frame['report']
                    report = frame['report']
                    if report[0] != 0:
                        raise ProtocolError('firmware reported failed spectrum session')
                    if report[1] != 0 or report[2] != ffts or report[3] != sampled or report[7] != len(rows) or report[10] != ffts or report[11] != 0:
                        raise ProtocolError('spectrum end totals or stop state do not match received frames')
                    if report[4] < a.seconds * 1000000 * .95:
                        raise ProtocolError('firmware duration shorter than requested session')
                    break
                if frame['kind'] == 'statistics':
                    if len(retained) + len(raw) > MAX_RETAINED_STREAM_BYTES:
                        raise RejectedFrame('private stream memory cap exceeded', raw, 'statistics', True)
                    retained.extend(raw)
                    continue
                if frame['sample_index'] <= previous or not frame['ffts']:
                    raise RejectedFrame('non-monotonic or empty FFT frame', raw, 'spectrum', True)
                if frame['sequence'] != len(rows):
                    raise RejectedFrame('lost, duplicate or out-of-order spectrum sequence', raw, 'spectrum', True)
                if frame['ffts'] != expected_ffts:
                    raise RejectedFrame('returned FFT windows per frame do not match requested grouping', raw, 'spectrum', True)
                if frame['flags'] & 1:
                    raise RejectedFrame('returned peak detector does not match requested mean power', raw, 'spectrum', True)
                if frame['samples_processed'] != frame['ffts'] * a.bins or not frame['flags'] & 8:
                    raise RejectedFrame('invalid snapshot sample total or missing gap flag', raw, 'spectrum', True)
                if len(retained) + len(raw) > MAX_RETAINED_STREAM_BYTES:
                    raise RejectedFrame('private stream memory cap exceeded', raw, 'spectrum', True)
                retained.extend(raw)
                previous = frame['sample_index']
                sampled += frame['samples_processed']
                ffts += frame['ffts']
                power = frame.pop('power_codes')
                row = {**frame, 'received_relative_seconds': elapsed,
                       'minimum_power_code': min(power), 'maximum_power_code': max(power),
                       'mean_power_code': sum(power) / len(power)}
                rows.append(row)
                self.update(frames=len(rows), elapsed_seconds=elapsed, power_codes=power,
                            snapshot_gap_flag=bool(frame['flags'] & 8),
                            nominal_coverage_fraction=sampled / a.rate / elapsed if elapsed else 0)
            record['frames'] = len(rows)
            record['elapsed_seconds'] = time.monotonic() - t0
            record['nominal_sampled_seconds'] = sampled / a.rate
            record['nominal_coverage_fraction'] = sampled / a.rate / record['elapsed_seconds']
            record['status'] = 'completed'
            if not rows or record['elapsed_seconds'] < a.seconds * .95:
                raise ProtocolError('bounded duration not established')
        except BaseException as error:
            if not isinstance(error, Exception):
                interrupted = error
            record['status'] = 'failed'
            record['error_kind'] = type(error).__name__
            record['error'] = str(error)[:240] if isinstance(error, (ProtocolError, ReadPrefix)) else 'Spectrum acquisition failed'
            if isinstance(error, RejectedFrame) and private_created:
                rejected = error.raw
                record['rejected_frame'] = error.metadata
            if hasattr(error, 'rejected_raw') and private_created:
                rejected = error.rejected_raw
                record['rejected_frame'] = error.rejected_metadata
                record['framing_uncertain'] = True
            elif ('start_command_ns' in record and 'start_reply_received_ns' not in record
                  and (isinstance(error, ReadPrefix) or getattr(error, 'reason', None) == 'reply_read_exception')):
                # SPEC may already be streaming after a partial START reply.
                # Retain the observed reply and close; RELEASE cannot be safely
                # interpreted against that remaining response/stream tail.
                rejected = getattr(error, 'partial', b'')
                record['rejected_frame'] = {
                    'kind': 'start_reply', 'complete_frame': False, 'bytes': len(rejected),
                    'sha256': hashlib.sha256(rejected).hexdigest(), 'crc_ok': None,
                    'expected_crc32': None, 'actual_crc32': None,
                    'expected_frame_bytes': None, 'reply_limit_bytes': 8192,
                    'command_start_ns': record['start_command_ns'],
                    'failure_ns': getattr(error, 'failure_ns', None),
                    'failure_kind': type(error).__name__,
                    'read_failure_reason': getattr(error, 'reason', None),
                    'underlying_read_error_kind': getattr(error, 'read_error_kind', None),
                    'unreturned_read_bytes_unknown': getattr(error, 'unreturned_read_bytes_unknown', False)}
                record['framing_uncertain'] = True
            self.update(status='Failed', error=record['error'], crc_failures=int('CRC' in record['error']))
        finally:
            acquisition_finished = time.monotonic() if t0 is not None else None
            if port is not None:
                try:
                    if not record.get('framing_uncertain'):
                        command(port, 'RELEASE')
                    else:
                        record['release_command'] = 'skipped_uncertain_framing'
                except Exception:
                    pass
                try:
                    port.close()
                    record['port_close'] = 'returned'
                except Exception as cleanup:
                    record['port_close'] = {'error_kind': type(cleanup).__name__}
                    record['status'] = 'failed'
                    record.setdefault('error_kind', type(cleanup).__name__)
                    record.setdefault('error', 'UART closure failed')
            record['ended_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            record['frames'] = len(rows)
            record['accepted_ffts'] = ffts
            record['accepted_sample_pairs'] = sampled
            if t0 is not None:
                record['elapsed_seconds'] = acquisition_finished - t0
                record['nominal_sampled_seconds'] = sampled / a.rate
                record['nominal_coverage_fraction'] = sampled / a.rate / record['elapsed_seconds'] if record['elapsed_seconds'] else 0
                # Terminal timing includes the end report, not only the last
                # spectrum frame. Keep its arrival time separately for inspection.
                self.update(elapsed_seconds=record['elapsed_seconds'],
                            nominal_coverage_fraction=record['nominal_coverage_fraction'],
                            last_frame_received_seconds=rows[-1]['received_relative_seconds'] if rows else None)
            # Continuous UART output must not wait for filesystem writes. The
            # accepted stream and a consumed rejection are bounded in RAM until
            # RELEASE/close, preserving the same byte order and prefix semantics.
            record['raw_persistence'] = {'accepted_stream': 'not_started', 'rejected_packet': 'not_applicable'}
            for kind, name, data in [('accepted_stream', 'spectrum-frames.bin', retained),
                                     ('rejected_packet', 'rejected-frame.bin', rejected)]:
                if not private_created or (kind == 'accepted_stream' and not acquisition_started) or data is None:
                    continue
                record['raw_persistence'][kind + '_expected_bytes'] = len(data)
                try:
                    saved = persist_verified(a.private / name, data)
                    record['raw_persistence'][kind] = 'verified'
                    if kind == 'accepted_stream':
                        record['private_frames_sha256'] = saved['sha256']
                        record['private_frames_bytes'] = saved['bytes']
                except Exception as error:
                    # Partial files remain private for inspection. Never label
                    # their expected buffer hash as a verified saved-file hash.
                    record['raw_persistence'][kind] = 'unverified'
                    record['raw_persistence'][kind + '_error_kind'] = type(error).__name__
                    record['status'] = 'failed'
                    record.setdefault('error_kind', 'RawPersistenceError')
                    record.setdefault('error', 'Private raw persistence failed after UART closure')
                    self.update(status='Failed', error='Private raw persistence failed after UART closure')
            record['prefix_integrity_note'] = 'Retained stream contains accepted spectrum frames and CRC-valid statistics; rejected consumed bytes are saved separately. Prefix success does not establish complete session integrity.'
            if output_created:
                if rows:
                    with (a.output / 'spectra.csv').open('w', newline='') as stream:
                        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
                # This atomic publication is the completion fence: UART closed,
                # CSV closed and JSON complete before a viewer can observe it.
                temporary = a.output / 'results.json.tmp'
                temporary.write_text(json.dumps(record, indent=2) + '\n')
                temporary.replace(a.output / 'results.json')
                if record['status'] == 'completed':
                    self.update(status='Completed real hardware trial; UART released')
            print(json.dumps({k:v for k,v in record.items() if k in {'status','frames','elapsed_seconds','error'} }), flush=True)
        if interrupted is not None:
            raise interrupted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default=STABLE_PORT)
    parser.add_argument('--baud', type=int, default=2000000)
    parser.add_argument('--firmware-revision', default=SOURCE_REVISION)
    parser.add_argument('--http-port', type=int, default=4340)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--rate', type=int, default=80000000, choices=RATE_CODES)
    parser.add_argument('--bins', type=int, default=1024, choices=[256,512,1024,2048])
    parser.add_argument('--ffts-per-frame', type=int, default=1, choices=range(1,9))
    parser.add_argument('--frequency', type=int, default=2412)
    parser.add_argument('--bandwidth', type=int, default=20)
    parser.add_argument('--gain', default='hardware')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('seconds must be 1..3600')
    private = args.private.resolve()
    if not any(p in {'.scratch','backups'} for p in private.parts) or any(p in {'site','docs'} for p in private.parts):
        parser.error('private payload directory must be under ignored .scratch/ or backups/, outside site/docs')
    trial = Trial(args)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                body = HTML.encode(); content_type = 'text/html'
            elif self.path == '/state':
                with trial.lock:
                    body = json.dumps(trial.state).encode()
                content_type = 'application/json'
            else:
                self.send_error(404); return
            self.send_response(200); self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
        def do_POST(self):
            origin = self.headers.get('Origin')
            if self.path != '/start' or (origin and origin not in {f'http://127.0.0.1:{args.http_port}', f'http://localhost:{args.http_port}'}):
                self.send_error(403); return
            self.rfile.read(int(self.headers.get('Content-Length','0')))
            self.send_response(202 if trial.start() else 409); self.end_headers()
        def log_message(self, *_):
            pass
    print(f'UART bridge viewer: http://127.0.0.1:{args.http_port}; device opens only after Start', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.http_port), Handler).serve_forever()


if __name__ == '__main__':
    main()

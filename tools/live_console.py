#!/usr/bin/env python3
"""Live localhost radio console: ESP32 2.4 GHz waterfall/BLE decode + RTL-SDR FM/RDS.

Operator tool for the exclusive hardware owner. The ESP must already run the
reviewed ESPARGOS protocol-6 receiver image (install with flash_trial.py and
restore afterwards). Nothing is saved: frames go to the browser over SSE only.
BLE addresses are reduced to short salted hashes before leaving this process.

    nix develop --command python3 tools/live_console.py
    # then open http://127.0.0.1:4350
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
from collections import deque
import secrets
import subprocess
import sys
import threading
import time

import numpy as np
from scipy import signal as sps

import ble_decode_iq as legacy
import ble_extended_primary as primary
from esp_sdr_capture import (RATE_CODES, STABLE_PORT, capture, command, open_board, queries,
                             settings, synchronize, unpack)
from esp_sdr_spectrum_bridge import spectrum_frame

TOOLS = Path(__file__).resolve().parent
HTML = (TOOLS/'live_console.html').read_bytes()
SALT = secrets.token_bytes(16)  # per-run: hashes cannot be joined across runs

# BLE advertising channel -> centre MHz; LO sits 1 MHz below to dodge the DC spur.
ADV_CHANNELS = {37: 2402, 38: 2426, 39: 2480}


class Hub:
    """Fan-out of JSON events to every connected SSE client."""

    def __init__(self):
        self.clients = set()
        self.lock = threading.Lock()
        self.latest = {}
        self.history = deque(maxlen=60)  # replayed packet-log events

    def subscribe(self):
        q = queue.Queue(maxsize=400)
        with self.lock:
            self.clients.add(q)
            for event in self.latest.values():
                q.put_nowait(event)
            for event in self.history:
                q.put_nowait(event)
        return q

    def unsubscribe(self, q):
        with self.lock:
            self.clients.discard(q)

    def publish(self, kind, sticky=False, history=False, **data):
        event = json.dumps({'kind': kind, 't': time.time(), **data}, separators=(',', ':'))
        with self.lock:
            if sticky:
                self.latest[kind] = event
            if history:
                self.history.append(event)
            for q in list(self.clients):
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass  # slow tab: drop rather than stall the radios


def short_hash(data):
    return hashlib.sha256(SALT+bytes(data)).hexdigest()[:8]


# ---------------------------------------------------------------- ESP32 worker

class EspWorker(threading.Thread):
    def __init__(self, hub, port_path, baud, reference, translation_hz=-1_800_000):
        super().__init__(daemon=True)
        # Measured: this board's carrier lands ~+0.8 MHz above nominal, so the
        # channel sits ~1.8 MHz above the LO (live AA carrier estimate + trial 001).
        self.translation_hz = translation_hz
        self.hub, self.port_path, self.baud, self.reference = hub, port_path, baud, reference
        self.want = {'mode': 'spectrum', 'center_mhz': 2442, 'channel': 37, 'gain': 'hardware'}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.stats = {'snapshots': 0, 'aa_candidates': 0, 'crc_valid': 0, 'owned': 0}

    def configure(self, **changes):
        with self.lock:
            self.want.update({k: v for k, v in changes.items() if v is not None})
            self.hub.publish('esp_config', sticky=True, **self.want)

    def current(self):
        with self.lock:
            return dict(self.want)

    def status(self, text, **extra):
        self.hub.publish('esp_status', sticky=True, text=text, **extra)

    def run(self):
        port = None
        try:
            self.status('Opening ESP32 UART…')
            port = open_board(self.port_path, self.baud)
            synchronize(port)
            info = queries(port)
            self.status('ESP32 receiver ready', firmware=info['INFO'])
            self.hub.publish('esp_config', sticky=True, **self.current())
            while not self.stop.is_set():
                want = self.current()
                if want['mode'] == 'spectrum':
                    self.spectrum_session(port, want)
                else:
                    self.decode_burst(port, want)
        except Exception as error:  # surface, never hide, hardware failures
            self.status(f'ESP32 stopped: {type(error).__name__}: {error}', error=True)
        finally:
            if port is not None:
                try:
                    command(port, 'RELEASE')
                except Exception:
                    pass
                port.close()

    def spectrum_session(self, port, want, seconds=6, bins=512, rate=80000000, ffts=4):
        settings(port, want['center_mhz'], 20, want['gain'])
        self._tuned = None
        reply = command(port, f'SPEC {seconds*1000} 1 {ffts} 0 {RATE_CODES[rate]} {bins} 1').split()
        if len(reply) != 5 or reply[0] != 'SPEC':
            raise RuntimeError(f'unexpected SPEC reply {reply}')
        self.status(f'Wideband FFT · {rate/1e6:.0f} MHz span @ {want["center_mhz"]} MHz')
        while True:
            frame, _ = spectrum_frame(port, bins)
            if frame['kind'] == 'end':
                return
            if frame['kind'] != 'spectrum':
                continue
            codes = np.asarray(frame['power_codes'], dtype=np.uint8)
            row = np.roll(codes, bins//2)  # natural FFT order -> low..high frequency
            self.hub.publish('esp_row', center_mhz=want['center_mhz'], span_mhz=rate/1e6,
                             scale='code', row=base64.b64encode(row.tobytes()).decode())

    def decode_burst(self, port, want, rate=16000000, samples=16380):
        channel = want['channel']
        lo = ADV_CHANNELS[channel]-1
        if getattr(self, '_tuned', None) != (lo, want['gain']):
            settings(port, lo, 12, want['gain'])
            self._tuned = (lo, want['gain'])
            self.status(f'Snapshot IQ + BLE decode · ch{channel} ({lo+1} MHz) · 16 MS/s · 1.02 ms windows')
        payload, meta = capture(port, samples, rate, 8)
        if not (meta['crc_ok'] and meta['sample_count_ok']):
            self.status('Snapshot failed CRC/count; dropped', error=True)
            return
        iq = unpack(payload, samples, 8)
        self.stats['snapshots'] += 1
        # Short-time spectrogram of this 1 ms window: 63 x 256 bins.
        n = 256
        frames = (iq[:len(iq)//n*n]-iq.mean()).reshape(-1, n)*np.hanning(n)
        power = 10*np.log10(np.abs(np.fft.fftshift(np.fft.fft(frames, axis=1), axes=1))**2+1e-3)
        lo_db, hi_db = 0.0, 60.0
        spec = np.clip((power-lo_db)/(hi_db-lo_db)*255, 0, 255).astype(np.uint8)
        envelope = np.abs(iq-iq.mean())
        env = envelope[:len(envelope)//64*64].reshape(-1, 64).mean(axis=1)
        burst_ratio = float(np.percentile(env, 99)/max(np.median(env), 1e-9))
        packets = self.decode(iq, rate, channel)
        self.hub.publish('esp_snapshot', channel=channel, center_mhz=lo, span_mhz=rate/1e6,
                         spectrogram=base64.b64encode(spec.tobytes()).decode(), rows=spec.shape[0], bins=n,
                         envelope=[round(float(v), 2) for v in env], burst_ratio=round(burst_ratio, 2),
                         window_us=samples/rate*1e6, transfer_ms=round(meta['payload_transfer_ms'], 1),
                         stats=self.stats)
        if packets:
            self.hub.publish('esp_packets', history=True, channel=channel, packets=packets)
        # Stack this window's 63 time slices (0.016 ms each) plus a gap marker.
        self.hub.publish('esp_rows', center_mhz=lo, span_mhz=rate/1e6, bins=n,
                         rows=base64.b64encode(spec[::-1].tobytes()).decode())

    def decode(self, iq, rate, channel):
        found = []
        try:
            frames = legacy.decode_iq(iq, rate, channel, legacy.MARKER_AD, self.translation_hz, True)
        except Exception:
            frames = []
        if channel == 37 and self.reference is not None:
            try:
                frames += primary.decode_primary_iq(iq, self.reference, rate, self.translation_hz, accept_chsel=True)
            except Exception:
                pass
        for f in frames:
            status = f.get('status', '')
            self.stats['aa_candidates'] += 1
            entry = {'status': status, 'pdu_type': f.get('pdu_type'), 'length': f.get('pdu_length'),
                     'owned': status.startswith('valid_owned'),
                     'crc_ok': status.startswith('valid'),
                     'offset_us': round(f.get('access_address_sample_offset', 0)/rate*1e6, 1),
                     'carrier_khz': round(f['estimated_carrier_offset_hz']/1e3, 1) if 'estimated_carrier_offset_hz' in f else None,
                     'aa_errors': f.get('access_address_hamming_errors'),
                     'correlation': round(f['access_correlation'], 3) if 'access_correlation' in f else None,
                     'kind': 'extended' if f.get('pdu_type') == 7 else 'legacy'}
            if entry['crc_ok']:
                self.stats['crc_valid'] += 1
                self.stats['owned'] += entry['owned']
                # Only a per-run salted hash of the PDU leaves the decoder.
                entry['pdu_hash'] = short_hash(json.dumps(f, sort_keys=True, default=str).encode())
            found.append(entry)
        return found


# ---------------------------------------------------------------- RTL worker

class RtlWorker(threading.Thread):
    RATE = 1_200_000
    OFFSET = 300_000  # tune off-station so the RTL DC spike is not on the carrier
    CHUNK = 1 << 17

    def __init__(self, hub, station_hz):
        super().__init__(daemon=True)
        self.hub = hub
        self.station_hz = station_hz
        self.retune = threading.Event()
        self.stop = threading.Event()
        self.audio_enabled = False

    def tune(self, station_hz):
        self.station_hz = station_hz
        self.retune.set()

    def run(self):
        while not self.stop.is_set():
            self.retune.clear()
            try:
                self.session()
            except Exception as error:
                self.hub.publish('rtl_status', sticky=True, text=f'RTL stopped: {type(error).__name__}: {error}', error=True)
                time.sleep(2)

    def session(self):
        station = self.station_hz
        center = station+self.OFFSET
        rtl = subprocess.Popen(['rtl_sdr', '-d', '0', '-f', str(center), '-s', str(self.RATE), '-g', '0', '-'],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        redsea = subprocess.Popen(['redsea', '-r', '240000', '-E'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        threading.Thread(target=self.rds_reader, args=(redsea, station), daemon=True).start()
        self.hub.publish('rtl_status', sticky=True, text=f'FM {station/1e6:.1f} MHz · RTL-SDR {self.RATE/1e6:.1f} MS/s',
                         station_mhz=station/1e6, span_mhz=self.RATE/1e6, center_mhz=center/1e6)
        self.hub.publish('rds', sticky=True, reset=True, station_mhz=station/1e6)
        # Stateful filters so chunk edges stay continuous.
        chan_taps = sps.firwin(101, 110_000, fs=self.RATE)
        chan_zi = np.zeros(len(chan_taps)-1, complex)
        audio_taps = sps.firwin(101, 15_000, fs=240_000)
        audio_zi = np.zeros(len(audio_taps)-1)
        tau = 75e-6  # North American de-emphasis
        alpha = 1-np.exp(-1/(48_000*tau))
        de_zi = np.zeros(1)
        index = 0
        last = 1+0j
        window = np.hanning(2048)
        try:
            while not self.stop.is_set() and not self.retune.is_set():
                raw = self.read_exact(rtl.stdout, self.CHUNK*2)
                if raw is None:
                    raise RuntimeError('rtl_sdr ended')
                u = np.frombuffer(raw, np.uint8).astype(np.float32)-127.5
                iq = (u[0::2]+1j*u[1::2])/127.5
                # Waterfall: four rows per chunk (~37 rows/s), 1024 bins over 1.2 MHz.
                for block in np.array_split(iq, 4):
                    seg = block[:len(block)//2048*2048].reshape(-1, 2048)*window
                    p = np.mean(np.abs(np.fft.fftshift(np.fft.fft(seg, axis=1), axes=1))**2, axis=0)
                    p = p.reshape(1024, 2).mean(axis=1)
                    db = 10*np.log10(p+1e-12)
                    row = np.clip((db+20)/50*255, 0, 255).astype(np.uint8)
                    self.hub.publish('rtl_row', row=base64.b64encode(row.tobytes()).decode())
                # Shift station to 0 Hz, channel filter, decimate to 240 kHz.
                n = np.arange(index, index+len(iq))
                index += len(iq)
                base = iq*np.exp(2j*np.pi*self.OFFSET*n/self.RATE)
                filtered, chan_zi = sps.lfilter(chan_taps, 1, base, zi=chan_zi)
                narrow = filtered[::5]
                prev = np.concatenate(([last], narrow[:-1]))
                last = narrow[-1]
                mpx = np.angle(narrow*np.conj(prev))
                redsea.stdin.write(np.clip(mpx*12000, -32767, 32767).astype('<i2').tobytes())
                if self.audio_enabled:
                    mono, audio_zi = sps.lfilter(audio_taps, 1, mpx, zi=audio_zi)
                    mono = mono[::5]
                    mono, de_zi = sps.lfilter([alpha], [1, alpha-1], mono, zi=de_zi)
                    pcm = np.clip(mono*20000, -32767, 32767).astype('<i2')
                    self.hub.publish('audio', rate=48000, pcm=base64.b64encode(pcm.tobytes()).decode())
        finally:
            rtl.terminate()
            try:
                redsea.stdin.close()
            except OSError:
                pass
            redsea.terminate()
            for proc in (rtl, redsea):
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

    @staticmethod
    def read_exact(stream, size):
        buf = bytearray()
        while len(buf) < size:
            chunk = stream.read(size-len(buf))
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def rds_reader(self, proc, station):
        groups = 0
        for line in proc.stdout:
            try:
                group = json.loads(line)
            except ValueError:
                continue
            groups += 1
            keep = {k: group[k] for k in ('pi', 'ps', 'radiotext', 'prog_type', 'callsign', 'group',
                                          'bler', 'clock_time', 'partial_ps', 'partial_radiotext',
                                          'tp', 'ta', 'is_music') if k in group}
            self.hub.publish('rds', station_mhz=station/1e6, groups=groups, **keep)


# ---------------------------------------------------------------- owned source

class SourceRunner:
    def __init__(self, hub):
        self.hub = hub
        self.proc = None

    def start(self, cycles):
        if self.proc is not None and self.proc.poll() is None:
            return False
        self.proc = subprocess.Popen([sys.executable, str(TOOLS/'ble_repeat_source_container.py'),
                                      '--cycles', str(cycles)], stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True)
        threading.Thread(target=self.relay, args=(self.proc, cycles), daemon=True).start()
        return True

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(2)

    def relay(self, proc, cycles):
        counted = 0
        self.hub.publish('source', sticky=True, state='starting', cycles=cycles, counted=0)
        for line in proc.stdout:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get('kind') == 'cycle_verified':
                counted += record['controller_reported_completed_extended_advertising_events']
                self.hub.publish('source', sticky=True, state='advertising', cycles=cycles,
                                 cycle=record['cycle']+1, counted=counted)
            elif record.get('kind') == 'source_ready':
                self.hub.publish('source', sticky=True, state='advertising', cycles=cycles, cycle=0, counted=0)
        proc.wait()
        self.hub.publish('source', sticky=True, state='idle', cycles=cycles, counted=counted,
                         exit_code=proc.returncode)


# ---------------------------------------------------------------- HTTP

def make_handler(hub, esp, rtl, source):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body, kind='application/json'):
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/':
                return self.reply(200, HTML, 'text/html; charset=utf-8')
            if self.path != '/events':
                return self.reply(404, b'{}')
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            q = hub.subscribe()
            try:
                while True:
                    try:
                        event = q.get(timeout=10)
                        self.wfile.write(b'data: '+event.encode()+b'\n\n')
                    except queue.Empty:
                        self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                hub.unsubscribe(q)

        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            try:
                body = json.loads(self.rfile.read(length) or b'{}')
            except ValueError:
                return self.reply(400, b'{"error":"json"}')
            if self.path == '/esp' and esp is not None:
                mode = body.get('mode')
                center = body.get('center_mhz')
                channel = body.get('channel')
                gain = body.get('gain')
                if (mode not in (None, 'spectrum', 'decode') or
                        (center is not None and not (2412 <= int(center) <= 2472)) or
                        (channel is not None and int(channel) not in ADV_CHANNELS) or
                        (gain is not None and gain != 'hardware' and not 0 <= int(gain) <= 64)):
                    return self.reply(400, b'{"error":"range"}')
                esp.configure(mode=mode, center_mhz=None if center is None else int(center),
                              channel=None if channel is None else int(channel), gain=gain)
                return self.reply(200, b'{}')
            if self.path == '/rtl' and rtl is not None:
                if 'station_mhz' in body:
                    mhz = float(body['station_mhz'])
                    if not 87.5 <= mhz <= 108.0:
                        return self.reply(400, b'{"error":"range"}')
                    rtl.tune(int(round(mhz*10))*100_000)
                if 'audio' in body:
                    rtl.audio_enabled = bool(body['audio'])
                return self.reply(200, b'{}')
            if self.path == '/source':
                if body.get('action') == 'stop':
                    source.stop()
                    return self.reply(200, b'{}')
                cycles = int(body.get('cycles', 10))
                if not 1 <= cycles <= 60:
                    return self.reply(400, b'{"error":"cycles"}')
                return self.reply(200 if source.start(cycles) else 409, b'{}')
            return self.reply(404, b'{}')
    return Handler


def main():
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument('--port', type=int, default=4350)
    cli.add_argument('--esp-port', default=STABLE_PORT)
    cli.add_argument('--baud', type=int, default=921600)
    cli.add_argument('--fm-mhz', type=float, default=101.1)
    cli.add_argument('--owned-reference', type=Path,
                     help='Private 0600 AdvA reference to flag our own extended-primary packets')
    cli.add_argument('--translation-hz', type=float, default=-1_800_000,
                     help='Digital shift applied before BLE decoding (LO is 1 MHz below the channel, plus measured board offset)')
    cli.add_argument('--no-esp', action='store_true')
    cli.add_argument('--no-rtl', action='store_true')
    args = cli.parse_args()
    hub = Hub()
    reference = primary.load_reference(args.owned_reference) if args.owned_reference else None
    esp = None if args.no_esp else EspWorker(hub, args.esp_port, args.baud, reference, args.translation_hz)
    rtl = None if args.no_rtl else RtlWorker(hub, int(round(args.fm_mhz*10))*100_000)
    source = SourceRunner(hub)
    hub.publish('features', sticky=True, esp=esp is not None, rtl=rtl is not None,
                owned_reference=reference is not None,
                source=bool(os.environ.get('BLE_SOURCE_IMAGE')))
    for worker in (esp, rtl):
        if worker is not None:
            worker.start()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(hub, esp, rtl, source))
    server.daemon_threads = True
    print(f'Live console on http://127.0.0.1:{args.port}  (Ctrl-C releases the radios)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        source.stop()
        for worker in (esp, rtl):
            if worker is not None:
                worker.stop.set()
        server.server_close()
        for worker in (esp, rtl):
            if worker is not None:
                worker.join(timeout=10)


if __name__ == '__main__':
    main()

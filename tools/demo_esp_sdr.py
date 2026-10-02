#!/usr/bin/env python3
"""Install a verified receiver, show a bounded live spectrum, and restore it.

Help is hardware free. Run and restore are physical operations for the exclusive
operator. Raw frames, subprocess logs, and full-flash readback stay private.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import flash_trial
from esp_sdr_capture import STABLE_PORT, SOURCE_REVISION, RATE_CODES, open_board
from esp_sdr_spectrum_bridge import HTML, Trial

ROOT = Path(__file__).resolve().parents[1]
SIZE = 0x400000


class Cancelled(RuntimeError):
    pass


class OwnedHardwareClosureError(RuntimeError):
    """Restoration is unsafe until the owned UART worker is confirmed closed."""
    pass


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def identity_check(port):
    """Inspect stable topology only; does not open/reset the serial device."""
    from serial.tools import list_ports
    path = Path(port)
    if str(path) != STABLE_PORT or not path.is_symlink():
        raise RuntimeError('Confirmed stable CP2102 link is required')
    found = [p for p in list_ports.comports() if Path(p.device).resolve() == path.resolve()]
    if len(found) != 1 or (found[0].vid, found[0].pid) != (0x10c4, 0xea60):
        raise RuntimeError('Stable USB target is absent or ambiguous')


def baseline_check():
    manifest = json.loads((ROOT / 'docs/evidence/firmware-preservation/manifest.json').read_text())
    image = ROOT / 'backups/original.bin'
    second = ROOT / 'backups/readback.bin'
    if (manifest.get('bytes') != SIZE or manifest.get('read_hashes_equal') is not True
            or manifest.get('independent_reads', 0) < 2
            or image.stat().st_size != SIZE or flash_trial.sha(image) != manifest['sha256']):
        raise RuntimeError('Private baseline does not match verified preservation')
    if second.stat().st_size != SIZE or flash_trial.sha(second) != manifest['sha256']:
        raise RuntimeError('Second preserved independent read does not match baseline')
    return manifest


def receiver_profile(artifact, manifest, baud):
    """Reject unreviewed profiles before a write; flash_trial repeats its guards."""
    data = json.loads(manifest.read_text())
    build = json.loads(manifest.with_name('build-info.json').read_text())
    profile = data['variants']['esp32']
    if not (build.get('source_commit') == SOURCE_REVISION
            and build.get('idf_commit') == flash_trial.SDK_REVISION
            and build.get('target') == profile.get('target') == 'esp32'
            and build.get('app_version') == data['version'] == profile.get('version')
            and build.get('source_code_patch', 'missing') is None
            and build.get('configuration_difference_from_upstream_defaults') == {'CONFIG_ESP_SDR_UART_BAUD': baud}
            and baud in (115200, 460800, 921600, 1000000)):
        raise RuntimeError('Receiver must be the pinned UART-only ESP32 variant matching host baud')
    expected = [('0-bootloader.bin', 0x1000, 0x8000),
                ('1-partition-table.bin', 0x8000, 0x9000),
                ('2-esp_sdr.bin', 0x10000, 0x110000)]
    if len(profile['parts']) != len(expected):
        raise RuntimeError('Unexpected receiver part count')
    for part, (name, offset, end) in zip(profile['parts'], expected):
        if part['name'] != name or part['offset'] != offset or not 0 < part['size'] <= end - offset:
            raise RuntimeError('Receiver part layout is not verified')
        path = artifact / 'esp32' / name
        if path.stat().st_size != part['size'] or flash_trial.sha(path) != part['sha256']:
            raise RuntimeError('Receiver part hash or size mismatch')
    return data['version']


def validate_paths(output, private):
    output, private = output.resolve(), private.resolve()
    if not output.is_relative_to(ROOT / 'docs/evidence') or output == ROOT / 'docs/evidence':
        raise RuntimeError('Public output must be a fresh directory within docs/evidence')
    if not any(private.is_relative_to(ROOT / name) and private != ROOT / name for name in ('.scratch', 'backups')):
        raise RuntimeError('Private directory must be within repository .scratch or backups')
    if output.exists() or private.exists():
        raise RuntimeError('Output and private directories must both be fresh')
    check = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '--quiet', str(private)], capture_output=True)
    if check.returncode != 0:
        raise RuntimeError('Private directory must be ignored by Git')
    return output, private


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_group_gone(pid, seconds):
    deadline = time.monotonic() + seconds
    while group_exists(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(.05)
    return True


def stop_process(proc, grace_seconds=8):
    """Wait for all owned UART/browser subprocesses to end before restoration."""
    if proc is None:
        return
    handlers = {s: signal.signal(s, lambda *_: None) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        # flash_trial's esptool child shares this group. Leader exit alone
        # cannot establish closure of the actual UART-owning descendant.
        if group_exists(proc.pid):
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            pass
        if not wait_group_gone(proc.pid, grace_seconds):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=grace_seconds)
            if not wait_group_gone(proc.pid, grace_seconds):
                raise OwnedHardwareClosureError('Owned process group remains present after bounded cleanup')
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


@contextmanager
def defer_spawn_cancellation():
    """Deliver cancellation after Popen and ownership assignment complete.

    Callable Python handlers become defaults after exec, so child SIGTERM is
    not blocked. pthread_sigmask across Popen would inherit a blocked mask.
    The caller establishes its finally BEFORE entering this context.
    """
    pending = []
    handlers = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            handlers[signum] = signal.signal(signum, lambda number, _: pending.append(number))
        yield
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    for signum in pending:
        handler = handlers[signum]
        if callable(handler):
            # During restoration the lifecycle's handler prints and returns.
            # Preserve that policy instead of inventing a new cancellation.
            handler(signum, None)
        elif handler != signal.SIG_IGN:
            raise Cancelled('Operator cancelled during owned process startup')


def execute(command, private_log, timeout=600):
    with private_log.open('wb') as log:
        proc = None
        try:
            with defer_spawn_cancellation():
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            code = proc.wait(timeout=timeout)
            if code:
                raise RuntimeError('Owned subprocess failed; inspect private log')
        finally:
            try:
                stop_process(proc)
            except Exception as error:
                raise OwnedHardwareClosureError('Owned hardware subprocess exit could not be confirmed') from error


def flash(action, a):
    identity_check(a.port)
    command = [sys.executable, str(ROOT / 'tools/flash_trial.py'), action,
               '--port', a.port, '--evidence', str(a.private / action)]
    if action == 'install':
        command += ['--artifact', str(a.artifact), '--manifest', str(a.manifest)]
    execute(command, a.private / f'{action}.log')


def read_full_flash(a, name):
    identity_check(a.port)
    if subprocess.run(['fuser', a.port], capture_output=True).returncode == 0:
        raise RuntimeError('Serial target is already open; refusing read/reset')
    image = a.private / f'{name}.bin'
    execute(['esptool', '--chip', 'esp32', '--port', a.port, '--baud', '460800',
             'read-flash', '--no-progress', '0', hex(SIZE), str(image)], a.private / f'{name}.log')
    return {'bytes': image.stat().st_size, 'sha256': flash_trial.sha(image)}


def current_baseline_check(a, baseline):
    read = read_full_flash(a, 'before-install-flash')
    read['matches_preserved_baseline'] = read['bytes'] == SIZE and read['sha256'] == baseline['sha256']
    write_json(a.output / 'before-install.json', read)
    if not read['matches_preserved_baseline']:
        raise RuntimeError('Current firmware differs from baseline; retained private read, refusing installation')


def observe_baseline_boot(port, destination):
    # read-flash's hard reset plus open may reset the MCU. This is a reset boot
    # observation, never an independently verified electrical power cycle.
    identity_check(port)
    connection = open_board(port, 115200, timeout=.1)
    data = bytearray()
    try:
        until = time.monotonic() + 8
        while time.monotonic() < until:
            data.extend(connection.read(8192))
    finally:
        connection.close()
    destination.write_bytes(data)
    text = data.decode(errors='replace')
    return {'application_identity_observed': 'hello_world' in text and '8b73cb1-dirty' in text,
            'sdk_observed': 'v5.4-dirty' in text,
            'gpio_high_observed': 'all pins -> 1' in text,
            'gpio_low_observed': 'all pins -> 0' in text,
            'boot_bytes_private': len(data), 'reset_boot_only': True, 'power_cycle_proven': False}


def restore_verified(a, baseline):
    flash('restore', a)
    read = read_full_flash(a, 'restored-flash')
    record = {'full_readback_bytes': read['bytes'], 'full_readback_sha256': read['sha256'],
              'baseline_sha256': baseline['sha256'], 'flash_write_verified': True}
    record['full_readback_matches_baseline'] = record['full_readback_bytes'] == SIZE and record['full_readback_sha256'] == baseline['sha256']
    write_json(a.output / 'restoration.json', record)
    if not record['full_readback_matches_baseline']:
        raise RuntimeError('Restored full-flash readback differs from baseline')
    record['boot'] = observe_baseline_boot(a.port, a.private / 'restored-boot.bin')
    record['verified'] = all(record['boot'][key] for key in ('application_identity_observed', 'sdk_observed', 'gpio_high_observed', 'gpio_low_observed'))
    write_json(a.output / 'restoration.json', record)
    if not record['verified']:
        raise RuntimeError('Full flash restored but expected baseline reset boot not observed')
    return record


def viewer_handler(trial, token):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                html = HTML.replace("fetch('/start'", f"fetch('/start/{token}'")
                html = html.replace('<p id="settings">', '<p>After this bounded session, the demo closes its UART and restores the preserved original firmware. Keep the terminal open through full-flash and boot verification.</p><p id="settings">')
                body = html.encode()
                content_type = 'text/html'
            elif self.path == '/state':
                with trial.lock:
                    state = dict(trial.state)
                # Arbitrary UART errors/paths never appear on the public canvas.
                state.pop('error', None)
                body = json.dumps(state).encode(); content_type = 'application/json'
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'")
            self.end_headers(); self.wfile.write(body)

        def do_POST(self):
            origin = self.headers.get('Origin')
            port = self.server.server_address[1]
            if self.path != f'/start/{token}' or origin not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
                self.send_error(403); return
            self.send_response(202 if trial.start() else 409); self.end_headers()

        def log_message(self, *_):
            pass
    return Handler


def viewer_child(a):
    # Socket was already bound by the parent, before firmware installation.
    trial_args = SimpleNamespace(**vars(a))
    trial_args.output = a.private / 'capture-metadata'
    trial_args.private = a.private / 'frames'
    trial = Trial(trial_args)
    server = ThreadingHTTPServer(('127.0.0.1', 0), viewer_handler(trial, a.token), bind_and_activate=False)
    server.socket.close()
    server.socket = socket.socket(fileno=a.listen_fd)
    server.server_address = server.socket.getsockname()
    try:
        server.serve_forever(poll_interval=.1)
    finally:
        server.server_close()


def publish_capture(a):
    source = a.private / 'capture-metadata/results.json'
    if not source.exists():
        raise RuntimeError('No terminal capture record was produced')
    record = json.loads(source.read_text())
    record.pop('error', None)
    # Replies cannot carry personal strings into the publication. Numerical
    # spectrum/timing evidence and source provenance are retained separately.
    record.pop('queries', None)
    record.pop('setting_replies', None)
    write_json(a.output / 'spectrum.json', record)
    csv = source.with_name('spectra.csv')
    if csv.exists():
        (a.output / 'spectra.csv').write_bytes(csv.read_bytes())
    return record


def installed_provenance(a):
    install = json.loads((a.private / 'install/manifest.json').read_text())
    if install['exit_code'] != 0 or install['firmware_variant'] != a.firmware_revision:
        raise RuntimeError('Installation receipt does not match verified receiver')
    return {'firmware_revision': install['firmware_variant'], 'source_commit': SOURCE_REVISION,
            'sdk_commit': flash_trial.SDK_REVISION, 'parts': install['parts'],
            'receiver_manifest_sha256': flash_trial.sha(a.manifest),
            'build_info_sha256': flash_trial.sha(a.manifest.with_name('build-info.json'))}


def live_view(a, listener):
    from playwright.sync_api import sync_playwright, expect
    executable = os.environ.get('CHROMIUM_EXECUTABLE')
    if not executable or not Path(executable).is_file():
        raise RuntimeError('Use the Nix shell providing CHROMIUM_EXECUTABLE')
    token = secrets.token_hex(24)
    command = [sys.executable, str(Path(__file__).resolve()), 'run', '--viewer-child',
               '--listen-fd', str(listener.fileno()), '--token', token,
               '--output', str(a.output), '--private', str(a.private), '--port', a.port,
               '--baud', str(a.baud), '--firmware-revision', a.firmware_revision,
               '--seconds', str(a.seconds), '--frequency', str(a.frequency), '--rate', str(a.rate),
               '--bins', str(a.bins), '--bandwidth', str(a.bandwidth)]
    command += ['--ffts-per-frame', str(a.ffts_per_frame)]
    url = f'http://127.0.0.1:{listener.getsockname()[1]}'
    proc = browser_proc = None
    try:
        with (a.private / 'viewer.log').open('wb') as log:
            with defer_spawn_cancellation():
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                        pass_fds=(listener.fileno(),), start_new_session=True)
                a.owned_worker_closed = False
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=executable, headless=True)
                try:
                    page = browser.new_page(viewport={'width': 1200, 'height': 1000})
                    page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    expect(page.locator('#settings')).to_contain_text('MHz')
                    print(f'Live viewer: {url} — press Start for the bounded session.', flush=True)
                    if a.headless:
                        page.locator('#start').click()
                    else:
                        with defer_spawn_cancellation():
                            browser_proc = subprocess.Popen([executable, '--new-window',
                                '--user-data-dir=' + str(a.private / 'browser-profile'), url],
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    deadline = time.monotonic() + a.start_timeout + a.seconds + 30
                    screenshot = False
                    while time.monotonic() < deadline:
                        if proc.poll() is not None:
                            raise RuntimeError('Owned viewer exited before terminal capture')
                        if browser_proc is not None and browser_proc.poll() is not None:
                            raise RuntimeError('Interactive browser exited; use --headless on a display-free host')
                        state = page.request.get(url + '/state').json()
                        if not screenshot and state['frames'] > 0 and state['elapsed_seconds'] >= min(5, a.seconds / 2):
                            page.screenshot(path=str(a.output / 'live-spectrum.png'), full_page=True)
                            screenshot = True
                        if (a.private / 'capture-metadata/results.json').exists():
                            expect(page.locator('#status')).to_have_text(re.compile(r'Completed.*|Failed'))
                            page.screenshot(path=str(a.output / 'completed-spectrum.png'), full_page=True)
                            return publish_capture(a)
                        if not state['frames'] and state['status'] == 'Ready' and deadline - time.monotonic() < a.seconds + 30:
                            raise TimeoutError('Viewer Start deadline expired')
                        page.wait_for_timeout(200)
                    raise TimeoutError('Terminal spectrum record deadline expired')
                finally:
                    browser.close()
    finally:
        try:
            try:
                try:
                    stop_process(browser_proc)
                except Exception as error:
                    # A browser group does not own UART. Still record its
                    # cleanup failure, while attempting hardware-safe recovery
                    # after the capture group's independent closure succeeds.
                    raise RuntimeError('Owned browser group cleanup failed') from error
            finally:
                try:
                    stop_process(proc)
                    a.owned_worker_closed = True
                except Exception as error:
                    a.owned_worker_closed = False
                    raise OwnedHardwareClosureError('Owned UART worker exit could not be confirmed') from error
        finally:
            listener.close()


def lifecycle(a):
    """Always restore after an installation attempt, even if its write failed."""
    a.output, a.private = validate_paths(a.output, a.private)
    baseline = baseline_check()
    if a.action == 'run':
        a.firmware_revision = receiver_profile(a.artifact, a.manifest, a.baud)
        if not os.environ.get('CHROMIUM_EXECUTABLE'):
            raise RuntimeError('Enter the locked Nix development shell')
    identity_check(a.port)
    # Private parents are ignored. umask protects logs/frames/readbacks/profiles.
    previous_umask = os.umask(0o077)
    a.private.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(a.private, 0o700)
    a.output.mkdir(parents=True, exist_ok=False)
    record = {'schema': 1, 'started_utc': utc(), 'action': a.action,
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'restore_policy': 'always after installation attempt, including failure/cancel',
              'stable_usb_identity_verified': True, 'usb_vid_pid': '10c4:ea60',
              'source_revision': SOURCE_REVISION, 'baseline_sha256': baseline['sha256'],
              'status': 'failed', 'capture_status': 'not_started', 'restoration_status': 'not_attempted',
              'screenshot_scope': 'Live viewer evidence only; RF integrity is established by CRC frames and terminal totals',
              'limitations': 'Snapshot gaps; uncalibrated power codes; no signal identification or continuous reception claim'}
    attempted = a.action == 'restore'
    a.owned_worker_closed = True
    listener = None
    signals = {}
    cleaning = False

    def cancel(signum, _):
        if not cleaning:
            raise Cancelled('Operator cancelled bounded demo')
        print('Restoration is in progress; waiting for verified completion.', flush=True)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            signals[signum] = signal.signal(signum, cancel)
        if a.action == 'run':
            listener = socket.socket()
            listener.bind(('127.0.0.1', a.http_port))
            listener.listen(16)
            current_baseline_check(a, baseline)
            attempted = True
            flash('install', a)
            record['receiver'] = installed_provenance(a)
            capture = live_view(a, listener)
            listener = None
            capture['bridge_status'] = capture['status']
            if capture['status'] == 'completed':
                capture['demo_duration_check'] = {'seconds_requested': a.seconds,
                    'host_elapsed_seconds': capture['elapsed_seconds'],
                    'firmware_elapsed_us': capture['end_report'][4],
                    'host_reached_requested_duration': capture['elapsed_seconds'] >= a.seconds,
                    'firmware_reached_requested_duration': capture['end_report'][4] >= a.seconds * 1000000}
                capture['demo_duration_gate_passed'] = all(capture['demo_duration_check'][key] for key in
                    ('host_reached_requested_duration', 'firmware_reached_requested_duration'))
                if not capture['demo_duration_gate_passed']:
                    capture['status'] = 'failed'
                    capture['error_kind'] = 'DemoDurationError'
            write_json(a.output / 'spectrum.json', capture)
            record['capture_status'] = capture['status']
            if capture['status'] != 'completed':
                raise RuntimeError('Spectrum session did not complete successfully')
    except (Exception, KeyboardInterrupt) as error:
        if isinstance(error, OwnedHardwareClosureError):
            a.owned_worker_closed = False
        record['error_kind'] = type(error).__name__
        # Error content is retained privately only; no path/device/foreign data.
        write_json(a.private / 'failure.json', {'error_kind': type(error).__name__, 'error': str(error)})
        try:
            if a.action == 'run' and not (a.output / 'spectrum.json').exists():
                record['capture_status'] = publish_capture(a)['status']
        except Exception:
            pass
    finally:
        cleaning = True
        if listener:
            listener.close()
        record['owned_uart_worker_exit_confirmed'] = a.owned_worker_closed
        if attempted and not a.owned_worker_closed:
            record['restoration_status'] = 'blocked_owned_worker_not_closed'
        elif attempted:
            try:
                restore_verified(a, baseline)
                record['restoration_status'] = 'verified'
            except Exception as error:
                record['restoration_status'] = 'failed'
                record['restore_error_kind'] = type(error).__name__
                if isinstance(error, OwnedHardwareClosureError):
                    record['owned_uart_worker_exit_confirmed'] = False
                write_json(a.private / 'restore-failure.json', {'error_kind': type(error).__name__, 'error': str(error)})
        if record['restoration_status'] == 'verified' and (a.action == 'restore' or record['capture_status'] == 'completed') and 'error_kind' not in record:
            record['status'] = 'completed'
        record['ended_utc'] = utc()
        write_json(a.output / 'demo.json', record)
        for signum, handler in signals.items():
            signal.signal(signum, handler)
        os.umask(previous_umask)
    print(f"Demo {record['status']}; capture {record['capture_status']}; restoration {record['restoration_status']}.")
    print(f'Results: {a.output / "demo.json"}')
    if record['restoration_status'] != 'verified' and attempted:
        print('Recovery is unverified. Resolve owned device access, then run task demo:esp:restore with fresh paths.')
    return 0 if record['status'] == 'completed' else 2


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['run', 'restore'], nargs='?', default='run')
    p.add_argument('--artifact', type=Path, help='Private pinned UART-only build directory containing esp32/')
    p.add_argument('--manifest', type=Path, help='Verified receiver manifest with adjacent build-info.json')
    p.add_argument('--port', default=STABLE_PORT, choices=[STABLE_PORT], help='Confirmed stable CP2102 only')
    p.add_argument('--output', type=Path, required=True, help='Fresh sanitized docs/evidence directory')
    p.add_argument('--private', type=Path, required=True, help='Fresh ignored .scratch/ or backups/ directory')
    p.add_argument('--headless', action='store_true', help='Auto-start in owned Nix Chromium and record a live screenshot')
    p.add_argument('--seconds', type=int, default=60, help='Bounded duration 1..3600; milestone requires 60')
    p.add_argument('--baud', type=int, default=921600, choices=[115200, 460800, 921600, 1000000])
    p.add_argument('--http-port', type=int, default=0, help='Owned localhost port; 0 selects a free port')
    p.add_argument('--start-timeout', type=int, default=120, help='Bounded wait for interactive Start, 1..600s')
    p.add_argument('--frequency', type=int, default=2412)
    p.add_argument('--rate', type=int, default=80000000, choices=RATE_CODES)
    p.add_argument('--bins', type=int, default=512, choices=[256, 512, 1024, 2048])
    p.add_argument('--ffts-per-frame', type=int, default=8, choices=range(1,9), help='Average 1..8 separately acquired FFT windows per update; default8 reduces per-FFT emission overhead')
    p.add_argument('--bandwidth', type=int, default=20)
    p.add_argument('--gain', default='hardware', choices=['hardware'])
    p.add_argument('--viewer-child', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--listen-fd', type=int, help=argparse.SUPPRESS)
    p.add_argument('--token', help=argparse.SUPPRESS)
    p.add_argument('--firmware-revision', help=argparse.SUPPRESS)
    return p


def main():
    p = parser(); a = p.parse_args()
    if a.viewer_child:
        viewer_child(a); return 0
    if a.action == 'run' and (a.artifact is None or a.manifest is None):
        p.error('run requires --artifact and --manifest')
    if not 1 <= a.seconds <= 3600 or not 1 <= a.start_timeout <= 600 or not 0 <= a.http_port <= 65535:
        p.error('duration, Start timeout, or localhost port out of bounds')
    # This lock coordinates demos/recovery; all other hardware tools still need
    # the exclusive human operator and their existing fuser/exclusive guards.
    (ROOT / '.scratch').mkdir(exist_ok=True)
    with (ROOT / '.scratch/esp-demo.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            p.error('Another demo/recovery owns this board')
        return lifecycle(a)


if __name__ == '__main__':
    raise SystemExit(main())

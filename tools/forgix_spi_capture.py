#!/usr/bin/env python3
"""Private finite register collector; no discovery, load or recovery entry point.

The lifecycle caller supplies its lock/identity checks and transport factory.
Factories must close failed opens; a bounded owning worker must contain OS/USB
calls. Injected tests do not qualify physical USB/FPGA timing or factory return.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from forgix_spi_bridge import RegisterRun
from forgix_usb_ram_capture import PrivateCapture, inherited_operator_lock


def select_bridge(topology, port, sys_root=Path('/sys'), require_character=True):
    """Bind explicit tty/USB enumeration, not FPGA image or MCU unique identity.

    The RAM firmware has no serial string. The caller's factory/ROM continuity
    and exact-image receipt must independently bind the same physical socket.
    """
    if not re.fullmatch(r'[0-9]+-[0-9]+(?:\.[0-9]+)*', topology):
        raise ValueError('explicit physical USB topology required')
    usb = (sys_root/'bus/usb/devices'/topology).resolve(strict=True)
    read = lambda name: (usb/name).read_text().strip()
    product = 'Forgix SPI RAM bridge v1'
    if (read('idVendor').lower(), read('idProduct').lower(), read('product')) != ('cafe','4012',product):
        raise ValueError('selected USB node is not the distinct register bridge')
    port = Path(port).resolve(strict=True)
    if not re.fullmatch(r'ttyACM[0-9]+', port.name):
        raise ValueError('explicit bridge CDC ACM tty required')
    if require_character and not stat.S_ISCHR(port.stat().st_mode):
        raise ValueError('bridge tty must be a character device')
    tty = (sys_root/'class/tty'/port.name/'device').resolve(strict=True)
    nodes = [p for p in (tty,*tty.parents) if (p/'idVendor').exists()]
    if not nodes or nodes[0] != usb:
        raise ValueError('selected tty does not belong exactly to bridge USB node')
    return {'port':str(port), 'usb_node':str(usb), 'topology':topology,
            'bus':read('busnum'), 'enumeration':read('devnum'),
            'vid':'cafe', 'pid':'4012', 'product':product}


def durable(stream, data):
    if stream.write(data) != len(data):
        raise OSError('short private capture write')
    stream.flush()
    os.fsync(stream.fileno())


def sync_directory(path):
    fd = os.open(path, os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(store, name, record):
    with store.open(name) as stream:
        durable(stream, (json.dumps(record, sort_keys=True, indent=2)+'\n').encode())
    sync_directory(store.path)


class RecordedTransport:
    """Journal intent before I/O and preserve received bytes before validation.

    A write intent does not prove device consumption. An exception/failed
    journal commit after I/O is ambiguous, never an invitation to retry.
    """
    def __init__(self, raw, journal, clock):
        self.raw, self.journal, self.clock = raw, journal, clock
        self.transport = None
        self.received = bytearray()
        self.events = []
        self.pending = None

    def record(self, event):
        durable(self.journal, (json.dumps(event, sort_keys=True)+'\n').encode())
        self.events.append(event)

    def transfer(self, kind, value, deadline):
        event = {'kind': kind+'_intent', 'deadline': deadline, 'host_s': self.clock()}
        event.update({'data_hex': value.hex()} if kind == 'write' else {'size': value})
        self.record(event)
        if self.clock() >= deadline:
            raise TimeoutError('deadline expired while persisting transfer intent')
        self.pending = kind
        try:
            result = getattr(self.transport, kind)(value, deadline)
        except BaseException as exc:
            self.record({'kind': kind+'_exception', 'error_kind': type(exc).__name__,
                         'host_s': self.clock()})
            self.pending = None
            raise
        event = {'kind': kind+'_return', 'host_s': self.clock()}
        if kind == 'read' and isinstance(result, bytes):
            offset = len(self.received)
            self.received.extend(result)
            durable(self.raw, result)
            event.update({'offset': offset, 'length': len(result),
                          'sha256': hashlib.sha256(result).hexdigest()})
        elif kind == 'write' and type(result) is int:
            event['count'] = result
        else:
            event['invalid_return_type'] = type(result).__name__
        self.record(event)
        self.pending = None
        return result

    def read(self, size, deadline):
        return self.transfer('read', size, deadline)

    def write(self, data, deadline):
        return self.transfer('write', data, deadline)


class SerialDeadlineTransport:
    """Adapt an already-owned serial handle to absolute register deadlines.

    Timeouts are capped on every call. This is cooperative bounded I/O, not a
    kernel-call kill bound; the future lifecycle owns its containing worker.
    """
    def __init__(self, serial, clock=time.monotonic):
        self.serial, self.clock = serial, clock

    def allowance(self, deadline, cap):
        left = deadline-self.clock()
        if left <= 0:
            raise TimeoutError('serial deadline expired')
        return min(left, cap)

    def read(self, size, deadline):
        while True:
            self.serial.timeout = self.allowance(deadline, .05)
            data = self.serial.read(size)
            if data:
                return data  # Collector retains even bytes arriving too late.

    def write(self, data, deadline):
        self.serial.write_timeout = self.allowance(deadline, 1.)
        return self.serial.write(data)

    def close(self):
        self.serial.close()
        if self.serial.is_open:
            raise OSError('serial handle remains open after close')


def collect(store, source_hash, nonce, transport_factory, identity_check,
            lock_check, clock=time.monotonic):
    """One private register run; no load/reboot/recovery and no lock mutation.

    Callbacks bind the selected enumeration before/after open and before each
    command's I/O. The caller must independently bind the exact FPGA image,
    verified RAM artifact and lifecycle; CDONE/product names do not do that.
    """
    began = clock()
    serial = None
    engine = RegisterRun(None, source_hash, nonce, clock)
    recorder = None
    error = None
    manifest = {'kind': 'private finite FPGA register capture', 'status': 'incomplete',
                'build_source_sha256': source_hash, 'host_deadline_s': 30,
                'factory_return_verified': False, 'lifecycle_complete': False,
                'physical_qualification_proved': False,
                'scope': 'Register collector only; caller owns load, FPGA identity, timing and full flash/factory recovery.'}
    # Source/nonce validation above precedes raw files or any transport open.
    deadline = began+30
    sync_directory(store.path.parent)
    save(store, 'started.json', manifest)
    try:
        with store.open('raw.bin') as raw, store.open('journal.jsonl') as journal:
            durable(raw, b'')
            durable(journal, b'')
            sync_directory(store.path)
            recorder = RecordedTransport(raw, journal, clock)
            engine.transport = recorder
            engine.deadline = deadline
            def check(until=deadline):
                lock = lock_check()
                identity = identity_check()
                if lock != manifest['operator_lock'] or identity != manifest['identity_private']:
                    raise ValueError('selected identity or lifecycle lock changed')
                if clock() >= until:
                    raise TimeoutError('collector preflight/identity deadline expired')
            manifest['operator_lock'] = lock_check()
            manifest['identity_private'] = identity_check()
            check()
            serial = transport_factory(manifest['identity_private']['port'], deadline)
            check()
            class SelectedTransport:
                def read(self, size, until):
                    check(until)
                    return serial.read(size, until)
                def write(self, data, until):
                    check(until)
                    return serial.write(data, until)
            recorder.transport = SelectedTransport()
            manifest['register_run'] = engine.run()
            manifest['status'] = 'registers_verified' if engine.summary['result']=='passed' else 'failed'
    except BaseException as exc:
        error = exc
        manifest['status'] = 'cancelled' if not isinstance(exc, Exception) else 'failed'
        manifest['error_kind'] = type(exc).__name__
    finally:
        if serial is not None:
            try:
                serial.close()
                manifest['transport_closed'] = True
            except BaseException as exc:
                error = error or exc
                manifest['status'] = 'failed'
                manifest['close_error_kind'] = type(exc).__name__
                manifest['transport_closed'] = False
        else:
            manifest['transport_closed'] = None
        if engine is not None:
            manifest['register_run'] = getattr(engine, 'summary', {'result':'failed'})
            transcript = [{'request_hex': t['request'].hex(), 'sent': t['sent'],
                           'response_hex': bytes(t['response']).hex(), 'validated': t['validated']}
                          for t in engine.transcript]
            try:
                save(store, 'transcript.json', transcript)
            except BaseException as exc:
                error = error or exc
                manifest['status'] = 'failed'
                manifest['transcript_error_kind'] = type(exc).__name__
        try:
            raw_bytes = (store.path/'raw.bin').read_bytes()
            journal_bytes = (store.path/'journal.jsonl').read_bytes()
            records = [json.loads(line) for line in journal_bytes.splitlines()]
            # Compare closed files independently to all returns seen in memory.
            verified = (recorder is not None and raw_bytes==bytes(recorder.received)
                        and records==recorder.events and recorder.pending is None)
            manifest.update({'raw_bytes': len(raw_bytes), 'raw_sha256': hashlib.sha256(raw_bytes).hexdigest(),
                             'journal_sha256': hashlib.sha256(journal_bytes).hexdigest(),
                             'persistence_verified': verified,
                             'transfer_return_uncommitted': recorder is not None and recorder.pending is not None})
            if not verified:
                raise OSError('raw/journal persistence not fully verified')
        except BaseException as exc:
            error = error or exc
            manifest['status'] = 'failed'
            manifest['persistence_error_kind'] = type(exc).__name__
            manifest['persistence_verified'] = False
        if clock() >= deadline:
            manifest['status'] = 'failed'
            manifest['host_deadline_exceeded'] = True
        manifest['host_elapsed_s'] = clock()-began
        save(store, 'manifest.json', manifest)
        if clock() >= deadline and not manifest.get('host_deadline_exceeded'):
            # Final receipt persistence is part of the cooperative bound too.
            manifest.update(status='failed', host_deadline_exceeded=True,
                            host_elapsed_s=clock()-began)
            save(store, 'late-manifest.json', manifest)
            os.replace(store.path/'late-manifest.json', store.path/'manifest.json')
            sync_directory(store.path)
    if error is not None and not isinstance(error, Exception):
        raise error
    return manifest

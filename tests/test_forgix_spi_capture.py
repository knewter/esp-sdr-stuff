"""Real C replies and local PTYs exercise collector faults, never physical USB."""
import json
import os
from pathlib import Path
import pty
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import forgix_spi_capture as capture
import test_forgix_spi_bridge as native
import test_forgix_spi_bridge_host as host_tests


class Device(host_tests.Device):
    def __init__(self, codec, **kwargs):
        super().__init__(codec, **kwargs)
        self.closed = False
        self.close_calls = 0
        self.on_close = None

    def close(self):
        self.close_calls += 1
        self.closed = True
        if self.on_close:
            self.on_close()


class Collector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.NativeProtocol.setUpClass()

    @classmethod
    def tearDownClass(cls):
        native.NativeProtocol.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = capture.PrivateCapture(root/'run', root)
        self.device = Device(native.NativeProtocol.lib)
        self.opens = []
        self.identity = lambda: {'port': 'synthetic-only', 'enumeration': 'fixture'}
        self.lock = lambda: {'ownership': 'injected fixture, no hardware'}

    def tearDown(self):
        self.temp.cleanup()

    def run_capture(self):
        def opened(port, deadline):
            self.opens.append((port, deadline))
            return self.device
        return capture.collect(self.store, 'a'*64, b'x'*16, opened,
                               self.identity, self.lock, lambda: self.device.now)

    def saved(self):
        return json.loads((self.store.path/'manifest.json').read_text())

    def test_fragmented_c_replies_persist_before_validation_and_close(self):
        write = self.device.write
        def check_intent(data, deadline):
            events = [json.loads(x) for x in (self.store.path/'journal.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['kind'], 'write_intent')
            self.assertEqual(events[-1]['data_hex'], data.hex())
            return write(data, deadline)
        self.device.write = check_intent
        result = self.run_capture()
        self.assertEqual(result['status'], 'registers_verified')
        self.assertTrue(result['persistence_verified'] and result['transport_closed'])
        self.assertEqual(self.device.close_calls, 1)
        self.assertEqual(self.device.scratch, 0xdeadbeef)
        self.assertFalse(result['factory_return_verified'] or result['lifecycle_complete'])
        transcript = json.loads((self.store.path/'transcript.json').read_text())
        self.assertEqual(len(transcript), 13)
        self.assertEqual(result['raw_bytes'], 13*128)
        self.assertEqual((self.store.path/'raw.bin').read_bytes(),
                         b''.join(bytes.fromhex(t['response_hex']) for t in transcript))
        for path in self.store.path.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.saved(), result)

    def test_pattern_failure_still_records_restoration_and_finish(self):
        self.device.fault = 'pattern'
        result = self.run_capture()
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['register_run']['scratch_restore_verified'])
        self.assertTrue(result['register_run']['finish_reply_verified'])
        self.assertTrue(result['persistence_verified'] and self.device.closed)

    def test_bad_crc_or_late_prefix_retained_without_more_commands(self):
        for fault, count, raw_bytes in [('crc', 5, 640), ('late-ready', 1, 9)]:
            with self.subTest(fault=fault):
                self.store = capture.PrivateCapture(Path(self.temp.name)/fault, Path(self.temp.name))
                self.device = Device(native.NativeProtocol.lib, fault=fault)
                result = self.run_capture()
                self.assertEqual(result['status'], 'failed')
                self.assertTrue(result['register_run']['session_ambiguous'])
                self.assertTrue(result['persistence_verified'] and self.device.closed)
                self.assertEqual(len(self.device.commands), count)
                self.assertEqual(result['raw_bytes'], raw_bytes)

    def test_cancelled_partial_read_saved_and_handle_closed(self):
        read = self.device.read
        calls = [0]
        def cancelled(size, until):
            calls[0] += 1
            if calls[0] == 3:
                raise KeyboardInterrupt()
            return read(size, until)
        self.device.read = cancelled
        with self.assertRaises(KeyboardInterrupt):
            self.run_capture()
        result = self.saved()
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['raw_bytes'], 18)
        self.assertTrue(result['persistence_verified'] and self.device.closed)
        self.assertEqual(len(self.device.commands), 1)
        self.assertEqual(result['register_run']['requests_attempted'], 1)

    def test_unheld_lock_and_changed_enumeration_refuse_command_io(self):
        cases = ['missing-lock', 'before-open', 'after-open', 'during-command']
        for case in cases:
            with self.subTest(case=case):
                self.store = capture.PrivateCapture(Path(self.temp.name)/case, Path(self.temp.name))
                self.device = Device(native.NativeProtocol.lib)
                self.opens = []
                self.lock = lambda: {'ownership': 'injected fixture, no hardware'}
                calls = [0]
                def identity():
                    calls[0] += 1
                    at = {'before-open': 2, 'after-open': 3, 'during-command': 4}.get(case, 999)
                    return {'port': 'synthetic-only', 'enumeration': 'fixture' if calls[0]<at else 'changed'}
                self.identity = identity
                if case == 'missing-lock':
                    def denied():
                        raise ValueError('not held')
                    self.lock = denied
                result = self.run_capture()
                self.assertEqual(result['status'], 'failed')
                self.assertFalse(self.device.commands)
                self.assertEqual(len(self.opens), 0 if case in ('missing-lock','before-open') else 1)
                if self.opens:
                    self.assertTrue(self.device.closed)

    def test_return_journal_failure_stops_and_retains_raw_prefix(self):
        durable = capture.durable
        # os.fdopen streams expose integer fd names; resolve through /proc.
        def injected(stream, data):
            target = Path(os.readlink('/proc/self/fd/'+str(stream.fileno())))
            if target.name == 'journal.jsonl' and b'"kind": "read_return"' in data:
                raise OSError('injected journal failure after raw save')
            return durable(stream, data)
        with patch.object(capture, 'durable', injected):
            result = self.run_capture()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['persistence_verified'])
        self.assertTrue(result['transfer_return_uncommitted'] and self.device.closed)
        self.assertEqual(result['raw_bytes'], 9)
        self.assertEqual(len(self.device.commands), 1)
        self.assertTrue(result['register_run']['session_ambiguous'])

    def test_partial_raw_write_failure_is_retained_and_failed(self):
        durable = capture.durable
        def injected(stream, data):
            target = Path(os.readlink('/proc/self/fd/'+str(stream.fileno())))
            if target.name == 'raw.bin' and data:
                durable(stream, data[:3])
                raise OSError('injected raw partial write')
            return durable(stream, data)
        with patch.object(capture, 'durable', injected):
            result = self.run_capture()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['persistence_verified'])
        self.assertEqual(result['raw_bytes'], 3)
        self.assertTrue(self.device.closed)
        self.assertEqual(len(self.device.commands), 1)

    def test_intent_persistence_crossing_deadline_refuses_io(self):
        durable = capture.durable
        def delayed(stream, data):
            durable(stream, data)
            if b'"kind": "write_intent"' in data:
                self.device.now = json.loads(data)['deadline']
        with patch.object(capture, 'durable', delayed):
            result = self.run_capture()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(self.device.commands)
        self.assertTrue(self.device.closed and result['persistence_verified'])

    def test_closed_file_reread_detects_truncated_raw(self):
        def truncate():
            path = self.store.path/'raw.bin'
            path.write_bytes(path.read_bytes()[:-1])
        self.device.on_close = truncate
        result = self.run_capture()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['persistence_verified'])
        self.assertEqual(result['raw_bytes'], 1663)
        self.assertTrue(result['transport_closed'])

    def test_close_failure_or_cleanup_deadline_cannot_pass(self):
        for fault in ('close-error', 'late-close'):
            with self.subTest(fault=fault):
                self.store = capture.PrivateCapture(Path(self.temp.name)/fault, Path(self.temp.name))
                self.device = Device(native.NativeProtocol.lib)
                def fail():
                    if fault=='close-error':
                        raise OSError('private exception text omitted')
                    self.device.now = 30
                self.device.on_close = fail
                result = self.run_capture()
                self.assertEqual(result['status'], 'failed')
                if fault=='close-error':
                    self.assertFalse(result['transport_closed'])
                    self.assertEqual(result['close_error_kind'], 'OSError')
                else:
                    self.assertTrue(result['host_deadline_exceeded'])
                self.assertNotIn('private exception text', json.dumps(result))

    def test_malformed_source_or_nonce_opens_nothing(self):
        for source, nonce in [('A'*64, b'x'*16), ('a'*64, bytes(16))]:
            with self.assertRaises(ValueError):
                capture.collect(self.store, source, nonce, lambda *a:self.opens.append(a),
                                self.identity, self.lock)
        self.assertFalse(self.opens)
        self.assertFalse(list(self.store.path.iterdir()))


class SerialAdapter(unittest.TestCase):
    def test_real_pty_read_write_deadline_and_descriptor_close(self):
        import serial
        master, slave = pty.openpty()
        port = serial.Serial(os.ttyname(slave), timeout=.05, write_timeout=1, exclusive=True)
        adapter = capture.SerialDeadlineTransport(port)
        fd = port.fileno()
        try:
            os.write(master, b'prefix')
            self.assertEqual(adapter.read(6, time.monotonic()+1), b'prefix')
            self.assertEqual(adapter.write(b'command', time.monotonic()+1), 7)
            self.assertEqual(os.read(master, 7), b'command')
            with self.assertRaises(TimeoutError):
                adapter.read(1, time.monotonic()+.02)
            with self.assertRaises(TimeoutError):
                adapter.write(b'x', time.monotonic())
        finally:
            adapter.close()
            os.close(master)
            os.close(slave)
        self.assertFalse(port.is_open)
        with self.assertRaises(OSError):
            os.fstat(fd)

    def test_late_nonempty_read_is_returned_for_prefix_retention(self):
        class Serial:
            now = 0
            def read(self, n):
                self.now = 2
                return b'late'
        serial = Serial()
        adapter = capture.SerialDeadlineTransport(serial, lambda:serial.now)
        self.assertEqual(adapter.read(4, 1), b'late')
        self.assertEqual(serial.timeout, .05)


class BridgeIdentity(unittest.TestCase):
    def test_distinct_product_topology_and_tty_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            usb = root/'bus/usb/devices/3-3'
            usb.mkdir(parents=True)
            for name,value in {'idVendor':'cafe','idProduct':'4012',
                               'product':'Forgix SPI RAM bridge v1',
                               'busnum':'3','devnum':'9'}.items():
                (usb/name).write_text(value)
            interface = usb/'3-3:1.0'
            interface.mkdir()
            tty = root/'class/tty/ttyACM9'
            tty.mkdir(parents=True)
            (tty/'device').symlink_to(interface)
            port = root/'ttyACM9'
            port.touch()
            self.assertEqual(capture.select_bridge('3-3',port,root,False)['pid'], '4012')
            with self.assertRaises(ValueError):
                capture.select_bridge('3-3:1.0',port,root,False)
            (usb/'idProduct').write_text('4011')
            with self.assertRaises(ValueError):
                capture.select_bridge('3-3',port,root,False)
            (usb/'idProduct').write_text('4012')
            (usb/'product').write_text('unrelated project')
            with self.assertRaises(ValueError):
                capture.select_bridge('3-3',port,root,False)
            (usb/'product').write_text('Forgix SPI RAM bridge v1')
            foreign = root/'foreign'
            foreign.mkdir()
            (foreign/'idVendor').write_text('cafe')
            (tty/'device').unlink()
            (tty/'device').symlink_to(foreign)
            with self.assertRaises(ValueError):
                capture.select_bridge('3-3',port,root,False)


if __name__ == '__main__':
    unittest.main()

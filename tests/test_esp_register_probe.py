"""Bounded worker tests using real C-generated synthetic IQ and receipts."""
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import esp_register_probe as worker
import esp_register_receipts as protocol
import test_esp_register_observation_firmware as fixture
from test_esp_register_receipts import NONCE, frame, transcript


class Wire:
    def __init__(self, rows, bad_crc=None, partial=None, missing_stage=None, old_info=False):
        self.rows = rows
        self.bad_crc = bad_crc
        self.partial = partial
        self.missing_stage = missing_stage
        self.old_info = old_info
        self.buffer = bytearray()
        self.requests = []
        self.captures = 0
        self.timeout = .25
        self.write_timeout = None
        self.is_open = True
        self.read_delay = 0
        self.close_failure = False
    def write(self, raw):
        for command in raw.decode('ascii').splitlines():
            if not command:
                continue
            self.requests.append(command)
            if command.startswith('SYNC '):
                self.buffer.extend((command+'\n').encode())
            elif command == 'INFO':
                self.buffer.extend(('ESP32SDR 6 burst 16380\n' if self.old_info else protocol.INFO+'\n').encode())
            elif command == 'LIMITS?':
                self.buffer.extend(b'LIMITS {"gain":[0,72,1],"bandwidth":[2,30,1,0],"rates":[80000000,40000000,16000000],"bits":[8,10]}\n')
            elif command == 'BAUD?':
                self.buffer.extend(b'BAUD 921600\n')
            elif command in ('FREQ 2401','BANDWIDTH 20','GAIN MANUAL 48'):
                self.buffer.extend(b'OK\n')
            elif command == 'REGOBS1 BEGIN '+NONCE:
                self.buffer.extend(self.rows[0][0])
            elif command == 'CAP20 16380 6':
                index = self.captures
                self.captures += 1
                line, data = self.rows[index+1]
                count, crc, elapsed, payload = data
                if self.bad_crc == index:
                    crc = f'{int(crc,16)^1:08x}'
                self.buffer.extend(f'DATA {count} {crc} {elapsed}\n'.encode())
                if self.partial == index:
                    self.buffer.extend(payload[:17])
                else:
                    self.buffer.extend(payload)
                    if self.missing_stage == index:
                        obj = protocol.parse_line(line)
                        obj['records'].pop()
                        line = frame(obj)
                    self.buffer.extend(line)
            elif command == 'REGOBS1 END '+NONCE:
                self.buffer.extend(self.rows[-1][0])
            else:
                raise AssertionError('Unexpected worker command')
        return len(raw)
    def flush(self):
        pass
    def read(self, n):
        if self.read_delay:
            time.sleep(self.read_delay)
        chunk = bytes(self.buffer[:n])
        del self.buffer[:n]
        return chunk
    def close(self):
        if self.close_failure:
            raise OSError('synthetic close failure')
        self.is_open = False


class WorkerActualC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        fixture.ActualReceiverC.setUpClass()
        output = subprocess.run([str(fixture.ActualReceiverC.path/'check'),'0'],
                                check=True,capture_output=True,timeout=5)
        cls.rows = transcript(output.stdout)
    @classmethod
    def tearDownClass(cls):
        fixture.ActualReceiverC.tearDownClass()

    def trial(self, wire=None, seconds=30, persist=None, opener=None):
        wire = wire or Wire(self.rows)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        private = root/'.scratch/trial'
        with patch.object(worker,'ROOT',root), \
             patch.object(worker.subprocess,'run',return_value=type('Result',(),{'returncode':0})()), \
             patch.object(worker,'open_board',side_effect=opener or (lambda *a,**k:wire)), \
             patch.object(worker.secrets,'token_hex',return_value=NONCE), \
             patch.object(worker,'SECONDS',seconds):
            old = os.umask(0o077)
            try:
                if persist:
                    with patch.object(worker,'persist',side_effect=persist):
                        result = worker.run(private)
                else:
                    result = worker.run(private)
            finally:
                os.umask(old)
        return result, wire, private

    def test_actual_twenty_frames_all_stages_single_settings_and_real_sync(self):
        result, wire, private = self.trial()
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['verified_capture_count'],20)
        self.assertEqual(len(result['records']),81)
        self.assertEqual(len(result['receipts']),22)
        self.assertEqual(wire.captures,20)
        self.assertFalse(wire.is_open)
        start = result['acquisition_start_ns']
        for reply in result['queries'].values():
            self.assertLessEqual(start, reply['bracket']['command_start_ns'])
        settings = ['FREQ 2401','BANDWIDTH 20','GAIN MANUAL 48']
        for setting in settings:
            self.assertEqual(wire.requests.count(setting),1)
        begin = wire.requests.index('REGOBS1 BEGIN '+NONCE)
        self.assertEqual(wire.requests[begin+1:], ['CAP20 16380 6']*20+['REGOBS1 END '+NONCE])
        self.assertEqual(len(list(private.glob('iq-*.bin'))),20)
        self.assertEqual(result['wire_persistence']['saved_sha256'],
                         hashlib.sha256((private/'wire.bin').read_bytes()).hexdigest())
        self.assertEqual(result,json.loads((private/'capture.json').read_text()))
        self.assertEqual(private.stat().st_mode&0o777,0o700)
        for file in private.iterdir():
            self.assertEqual(file.stat().st_mode&0o777,0o600)

    def test_crc_or_stage_failure_stops_without_retry_end_or_reapply(self):
        for wire in (Wire(self.rows,bad_crc=3),Wire(self.rows,missing_stage=3)):
            result, wire, private = self.trial(wire)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(wire.captures,4)
            self.assertEqual(result['verified_capture_count'],3)
            self.assertNotIn('REGOBS1 END '+NONCE,wire.requests)
            self.assertEqual(wire.requests.count('GAIN MANUAL 48'),1)
            self.assertEqual(len((private/'iq-03.bin').read_bytes()),40950)

    def test_deadline_retains_consumed_partial_binary_then_closes(self):
        result, wire, private = self.trial(Wire(self.rows,partial=0),seconds=.08)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error_kind'],'AcquisitionDeadline')
        self.assertLess(result['acquisition_elapsed_seconds'],.3)
        self.assertEqual(len((private/'iq-00.bin').read_bytes()),17)
        self.assertFalse(wire.is_open)
        self.assertEqual(wire.captures,1)
        self.assertTrue(result['wire_persistence']['verified'])

    def test_slow_sync_is_part_of_absolute_acquisition_deadline(self):
        wire = Wire(self.rows)
        wire.read_delay = .5
        before = time.monotonic()
        result, wire, _ = self.trial(wire,seconds=.04)
        self.assertLess(time.monotonic()-before,.3)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error_kind'],'AcquisitionDeadline')
        self.assertEqual(wire.captures,0)

    def test_storage_failure_is_after_uart_closure_and_has_no_saved_hash(self):
        wire = Wire(self.rows)
        def fail(path,data):
            self.assertFalse(wire.is_open)
            with path.open('xb') as stream:
                stream.write(data[:7])
            raise OSError('synthetic disk failure')
        result, wire, private = self.trial(wire,persist=fail)
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['wire_persistence']['verified'])
        self.assertNotIn('saved_sha256',result['wire_persistence'])
        self.assertEqual(len((private/'wire.bin').read_bytes()),7)
        self.assertTrue(all(not r['payload_persistence']['verified'] for r in result['captures']))

    def test_old_receiver_is_refused_before_settings_or_capture(self):
        result, wire, _ = self.trial(Wire(self.rows,old_info=True))
        self.assertEqual(result['status'],'failed')
        self.assertNotIn('FREQ 2401',wire.requests)
        self.assertEqual(wire.captures,0)

    def test_cancel_during_open_assignment_closes_before_retention(self):
        wire = Wire(self.rows)
        def opener(*a,**k):
            os.kill(os.getpid(),signal.SIGTERM)
            return wire
        result, wire, private = self.trial(wire,opener=opener)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['cancelled'])
        self.assertFalse(wire.is_open)
        self.assertEqual(wire.requests,[])
        self.assertEqual((private/'wire.bin').read_bytes(),b'')

    def test_unconfirmed_uart_close_cannot_persist_buffers(self):
        wire = Wire(self.rows)
        wire.close_failure = True
        result, wire, private = self.trial(wire)
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['uart_closed'])
        self.assertFalse(result['wire_persistence']['verified'])
        self.assertFalse(result['capture_receipt_persisted'])
        self.assertEqual(list(private.iterdir()),[])

    def test_each_write_caps_and_restores_its_own_timeout(self):
        wire = Wire(self.rows)
        budget = worker.BudgetPort(wire,time.monotonic()+.1)
        observed = []
        original_write = wire.write
        def write(raw):
            observed.append(wire.write_timeout)
            return original_write(raw)
        with patch.object(wire,'write',side_effect=write):
            budget.write(b'SYNC 1\n')
        self.assertIsNone(wire.write_timeout)
        self.assertGreater(observed[0],0)
        self.assertLessEqual(observed[0],.1)
        wire.write_timeout = .01
        with patch.object(wire,'write',side_effect=OSError('synthetic write failure')):
            with self.assertRaises(OSError):
                budget.write(b'SYNC 2\n')
        self.assertEqual(wire.write_timeout,.01)

    def test_cancel_during_storage_is_failed_after_uart_is_closed(self):
        wire = Wire(self.rows)
        original = worker.persist
        cancelled = False
        def store(path,data):
            nonlocal cancelled
            self.assertFalse(wire.is_open)
            if not cancelled:
                cancelled = True
                os.kill(os.getpid(),signal.SIGTERM)
            return original(path,data)
        result, _, _ = self.trial(wire,persist=store)
        self.assertTrue(result['cancelled'])
        self.assertEqual(result['status'],'failed')

    def test_error_prefix_cannot_turn_capture_or_end_into_verified_receipt(self):
        session = protocol.Session(NONCE,100000)
        config, _ = self.rows[0]
        bracket = dict(host_start_ns=1,host_end_ns=2,host_start_utc='synthetic',host_end_utc='synthetic')
        worker.receipt(session,config,bracket)
        line,data = self.rows[1]
        fake = Wire(self.rows)
        fake.buffer.extend(line)
        # Patch the independent receive brackets into the synthetic deadline.
        with patch.object(worker,'read_line',return_value=(line,dict(bracket,host_start_ns=11,host_end_ns=12))):
            with self.assertRaises(protocol.ProtocolError):
                worker.response(session,fake,b'ERR REGOBS1 session_state\n',bracket,data)
        self.assertEqual(len(session.captures),0)


if __name__ == '__main__':
    unittest.main()

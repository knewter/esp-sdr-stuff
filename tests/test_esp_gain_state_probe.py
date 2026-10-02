"""Synthetic bounded probe transport/cleanup; no serial device is opened."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import esp_gain_state_probe as probe


class Wire:
    def __init__(self, bad_crc=None, wrong_count=None, bit_change=None, partial=None, malformed_gain=False):
        self.timeout=.25;self.is_open=True;self.buffer=bytearray();self.requests=[]
        self.bad_crc=bad_crc;self.wrong_count=wrong_count;self.bit_change=bit_change
        self.partial=partial;self.malformed_gain=malformed_gain;self.captures=0
        self.payload=b'\x00'*40950;self.read_delay=0;self.foreign_limits=False
    def write(self,data):
        command=data.decode().strip();self.requests.append(command)
        if command=='GAIN?':
            bit=0 if self.bit_change is not None and self.captures>=self.bit_change else 1
            reply=f'GAIN MANUAL 48 0 87 {bit}\n' if not self.malformed_gain else 'foreign private identifier\n'
            self.buffer.extend(reply.encode())
        elif command.startswith('CAP20'):
            index=self.captures;self.captures+=1
            samples=16378 if self.wrong_count==index else 16380
            payload=self.payload[:(samples*20+7)//8];crc=zlib.crc32(payload)^(self.bad_crc==index)
            self.buffer.extend(f'DATA {samples} {crc:08x} 1030\n'.encode())
            self.buffer.extend(payload[:10] if self.partial==index else payload)
        elif command=='INFO':self.buffer.extend(b'ESP32SDR 6 burst 16380\n')
        elif command=='BAUD?':self.buffer.extend(b'BAUD 921600\n')
        elif command=='LIMITS?':
            limits={'gain':[0,87,1],'bandwidth':[2,30,1,0],'rates':[80000000,40000000,16000000],'bits':[8,10]}
            if self.foreign_limits:limits['foreign_address']='secret'
            self.buffer.extend(('LIMITS '+json.dumps(limits)+'\n').encode())
        else:self.buffer.extend(b'OK\n')
        return len(data)
    def flush(self):pass
    def read(self,n):
        if self.read_delay:time.sleep(self.read_delay)
        result=bytes(self.buffer[:n]);del self.buffer[:n];return result
    def close(self):self.is_open=False


class GainProbeTests(unittest.TestCase):
    def trial(self,wire=None,seconds=None,persist=None,opener=None):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);wire=wire or Wire()
        private=root/'.scratch/trial';output=root/'docs/evidence/trial'
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(probe,'ROOT',root))
            stack.enter_context(patch.object(probe.subprocess,'run',return_value=type('Result',(),{'returncode':0})()))
            stack.enter_context(patch.object(probe,'open_board',side_effect=opener or (lambda *a,**k:wire)))
            stack.enter_context(patch.object(probe,'synchronize'))
            if seconds is not None:stack.enter_context(patch.object(probe,'SECONDS',seconds))
            if persist is not None:stack.enter_context(patch.object(probe,'persist',side_effect=persist))
            with contextlib.redirect_stdout(io.StringIO()):code=probe.main(['--private',str(private),'--output',str(output)])
        result=json.loads((output/'results.json').read_text())
        self.assertEqual(result,json.loads((private/'results.json').read_text()))
        self.assertFalse(wire.is_open)
        return code,result,wire,private

    def test_twenty_exact_captures_single_settings_and_all_gain_brackets(self):
        code,r,wire,private=self.trial()
        self.assertEqual(code,0);self.assertEqual(r['integrity_valid_count'],20)
        self.assertEqual(len(r['gain_observations']),41)
        settings=['FREQ 2401','BANDWIDTH 20','GAIN MANUAL 48']
        for setting in settings:self.assertEqual(wire.requests.count(setting),1)
        loop=wire.requests[wire.requests.index('GAIN MANUAL 48')+1:]
        self.assertEqual(loop,['GAIN?']+['GAIN?','CAP20 16380 6','GAIN?']*20)
        for query in r['gain_observations']:
            self.assertLessEqual(query['command_start_ns'],query['host_line_start_ns'])
            self.assertLessEqual(query['host_line_start_ns'],query['host_line_end_ns'])
        self.assertTrue(r['uart_closed']);self.assertTrue(r['private_wire_persistence']['verified'])
        self.assertEqual(r['private_wire_persistence']['saved_sha256'],hashlib.sha256((private/'wire.bin').read_bytes()).hexdigest())
        self.assertEqual(len(list(private.glob('iq-*.bin'))),20)
        for file in private.iterdir():self.assertEqual(file.stat().st_mode&0o777,0o600)
        self.assertEqual(private.stat().st_mode&0o777,0o700)

    def test_crc_and_count_failures_retained_without_retry_or_reapply(self):
        for wire in (Wire(bad_crc=3),Wire(wrong_count=3)):
            code,r,wire,private=self.trial(wire)
            self.assertEqual(code,2);self.assertEqual(r['capture_count'],20)
            self.assertEqual(r['integrity_valid_count'],19)
            self.assertEqual(wire.requests.count('CAP20 16380 6'),20)
            self.assertEqual(wire.requests.count('GAIN MANUAL 48'),1)
            self.assertEqual(len((private/'iq-03.bin').read_bytes()),40945 if wire.wrong_count==3 else 40950)
            self.assertTrue(r['captures'][3]['private_payload_persistence']['verified'])

    def test_changed_observed_bit_is_reported_without_changing_software_index(self):
        code,r,wire,private=self.trial(Wire(bit_change=5))
        self.assertEqual(code,2);self.assertTrue(r['expected_software_state_all_observed'])
        self.assertFalse(r['manual_enable_bit_all_observed_set'])
        self.assertEqual(r['gain_observations'][10]['observed_register_bit23'],0)
        self.assertEqual(wire.requests.count('GAIN MANUAL 48'),1)
        self.assertEqual(r['capture_count'],20)

    def test_absolute_deadline_partial_prefix_is_saved_after_uart_close(self):
        wire=Wire(partial=0)
        code,r,wire,private=self.trial(wire,seconds=.08)
        self.assertEqual(code,2);self.assertEqual(r['error_kind'],'AcquisitionDeadline')
        self.assertLess(r['acquisition_elapsed_seconds'],.25)
        self.assertEqual(len((private/'iq-00.bin').read_bytes()),10)
        self.assertEqual(r['captures'][0]['retained_payload_bytes'],10)
        self.assertTrue((private/'wire.bin').read_bytes().endswith(b'\x00'*10))
        self.assertEqual(wire.requests.count('CAP20 16380 6'),1)

    def test_alarm_interrupts_slow_read_without_waiting_for_serial_timeout(self):
        wire=Wire();wire.read_delay=.5
        before=time.monotonic();code,r,_,_=self.trial(wire,seconds=.04)
        self.assertLess(time.monotonic()-before,.3)
        self.assertEqual(code,2);self.assertEqual(r['error_kind'],'AcquisitionDeadline')
        self.assertTrue(r['uart_closed'])

    def test_private_persistence_failure_does_not_leave_uart_open_or_claim_saved_hash(self):
        wire=Wire()
        def fail(path,data):
            self.assertFalse(wire.is_open)
            raise OSError('synthetic disk failure')
        code,r,_,_=self.trial(wire,persist=fail)
        self.assertEqual(code,2);self.assertFalse(r['private_wire_persistence']['verified'])
        self.assertNotIn('saved_sha256',r['private_wire_persistence'])
        self.assertTrue(all(not row['private_payload_persistence']['verified'] for row in r['captures']))

    def test_untyped_gain_and_extra_limits_never_leak_raw_reply_to_public(self):
        for wire in (Wire(malformed_gain=True),Wire()):
            if not wire.malformed_gain:wire.foreign_limits=True
            code,r,_,private=self.trial(wire)
            self.assertEqual(code,2)
            self.assertNotIn('foreign',json.dumps(r));self.assertNotIn('secret',json.dumps(r))
            self.assertIn(b'foreign',(private/'wire.bin').read_bytes())
            self.assertEqual(wire.captures,0)

    def test_cancel_during_open_assignment_closes_owned_port(self):
        wire=Wire()
        def opener(*a,**k):os.kill(os.getpid(),signal.SIGTERM);return wire
        code,r,_,_=self.trial(wire,opener=opener)
        self.assertEqual(code,2);self.assertTrue(r['cancelled']);self.assertTrue(r['uart_closed'])
        self.assertEqual(wire.requests,[])

    def test_invalid_private_path_cannot_open_serial(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(probe,'ROOT',Path(temporary)),patch.object(probe,'open_board') as opening:
            with self.assertRaises(probe.ProbeError):probe.run(Path(temporary)/'docs/evidence/raw',Path(temporary)/'docs/evidence/result')
            opening.assert_not_called()


if __name__=='__main__':unittest.main()

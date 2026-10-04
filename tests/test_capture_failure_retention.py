"""Consumed-prefix, stop/close and private persistence tests; no hardware."""
import contextlib
import csv
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import esp_sdr_capture as capture
import measure_owned_ble as receiver
import esp_sdr_spectrum_bridge as spectrum


class Wire:
    def __init__(self, events, samples=16380, header=None):
        self.events = list(events)
        self.samples = samples
        self.header = header or f'DATA {samples} 1234abcd 1030\n'.encode()
        self.requests = []
        self.closed = False
        self.reads = 0
    def read(self, size):
        self.reads += 1
        if not self.events:
            return b''
        item = self.events.pop(0)
        if isinstance(item, BaseException):
            raise item
        if len(item) > size:
            self.events.insert(0, item[size:])
        return item[:size]
    def read_until(self, *_):
        return self.header
    def write(self, data):
        self.requests.append(data)
        return len(data)
    def flush(self):pass
    def close(self):self.closed = True


class ExactRead(unittest.TestCase):
    def test_timeout_keeps_binary_prefix_and_does_not_read_late_tail(self):
        wire = Wire([b'\x00\xff\n', b'', b'late'])
        with self.assertRaises(TimeoutError) as caught:
            capture.exact(wire, 8)
        error = caught.exception
        self.assertEqual(error.partial, b'\x00\xff\n')
        self.assertEqual(error.expected_bytes, 8)
        self.assertEqual(error.reason, 'empty_read')
        self.assertEqual(wire.events, [b'late'])
        self.assertEqual(wire.reads, 2)
        self.assertFalse(error.unreturned_read_bytes_unknown)

    def test_transport_failure_is_not_relabelled_timeout_and_keeps_cause(self):
        cause = OSError('private transport detail')
        with self.assertRaises(capture.PartialReadException) as caught:
            capture.exact(Wire([b'abc', cause]), 10)
        error = caught.exception
        self.assertNotIsInstance(error, TimeoutError)
        self.assertIs(error.__cause__, cause)
        self.assertEqual(error.partial, b'abc')
        self.assertEqual(error.read_error_kind, 'OSError')
        self.assertTrue(error.unreturned_read_bytes_unknown)
        self.assertNotIn('private transport detail', str(error))

    def test_empty_prefix_and_complete_fragmented_read_are_distinct(self):
        with self.assertRaises(capture.PartialReadError) as caught:
            capture.exact(Wire([b'']), 4)
        self.assertEqual(caught.exception.partial, b'')
        self.assertEqual(capture.exact(Wire([b'a', b'bc', b'd']), 4), b'abcd')
        self.assertEqual(capture.exact(Wire([]), 0), b'')

    def test_nonconforming_overlong_read_keeps_every_delivered_byte_and_fails(self):
        wire=Wire([])
        with patch.object(wire,'read',return_value=b'12345'), self.assertRaises(capture.PartialReadError) as caught:
            capture.exact(wire,4)
        self.assertEqual(caught.exception.partial,b'12345')
        self.assertEqual(caught.exception.reason,'overlong_read')

    def test_interruption_preserves_prefix_and_keyboard_interrupt_semantics(self):
        with self.assertRaises(KeyboardInterrupt) as caught:
            capture.exact(Wire([b'prefix', KeyboardInterrupt()]), 20)
        self.assertEqual(caught.exception.partial, b'prefix')
        self.assertEqual(caught.exception.reason, 'read_interrupted')

    def test_capture_retains_parsed_header_and_monotonic_failure_bracket(self):
        wire = Wire([b'abc', b''], samples=256)
        ticks = iter([10, 20, 30])
        with patch.object(capture.time, 'monotonic_ns', side_effect=lambda: next(ticks)):
            with self.assertRaises(capture.PartialReadError) as caught:
                capture.capture(wire, 256, 16000000, 8)
        error = caught.exception; info = error.capture_failure
        self.assertEqual(error.private_header, b'DATA 256 1234abcd 1030\n')
        self.assertEqual(info['expected_payload_bytes'], 512)
        self.assertEqual(info['expected_crc32'], '1234abcd')
        self.assertEqual(info['returned_samples'], 256)
        self.assertEqual(info['firmware_capture_us'], 1030)
        self.assertEqual([info[k] for k in ['command_start_ns', 'header_received_ns', 'failure_ns']], [10,20,30])
        self.assertFalse(info['payload_complete'])
        self.assertNotIn('crc_ok', info)
        self.assertEqual(info['prefix_crc32'], f'{zlib.crc32(b"abc"):08x}')

    def test_bad_or_short_header_remains_private_and_no_payload_is_read(self):
        for header in [b'DATA 256 1234', b'PRIVATE-ADDRESS\n', b'\xffbad\n']:
            with self.subTest(header=header):
                wire = Wire([b'late'], samples=256, header=header)
                with self.assertRaises((capture.PartialReadError, capture.ProtocolError, UnicodeError)) as caught:
                    capture.capture(wire, 256, 16000000, 8)
                self.assertEqual(caught.exception.private_header, header)
                self.assertEqual(caught.exception.private_payload_prefix, b'')
                self.assertEqual(wire.reads, 0)
                self.assertNotIn('PRIVATE-ADDRESS', json.dumps(caught.exception.capture_failure))


class ReceiverRetention(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.args = ['--output', str(self.root/'public'), '--private', str(self.root/'.scratch/iq'), '--seconds', '1']
    def run_receiver(self, wire):
        with patch.object(receiver, 'open_board', return_value=wire), \
             patch.object(receiver, 'synchronize') as sync, \
             patch.object(receiver, 'queries', return_value={'synthetic':True}), \
             patch.object(receiver, 'settings', return_value={'synthetic':'OK'}), \
             contextlib.redirect_stdout(io.StringIO()):
            receiver.main(self.args)
        return sync
    def receipt(self):return json.loads((self.root/'public/manifest.json').read_text())

    def test_real_short_size_is_saved_privately_after_close_without_retry(self):
        prefix = b'PRIVATE-FOREIGN-AIR' + b'\x9f' * (31995-19)
        self.assertEqual(len(prefix), 31995)
        wire = Wire([prefix, b'', b'late tail'])
        original = capture.write_private
        def checked(path, data):
            self.assertTrue(wire.closed)
            return original(path, data)
        with patch.object(capture, 'write_private', checked), self.assertRaises(capture.PartialReadError):
            self.run_receiver(wire)
        info = self.receipt()
        self.assertFalse(info['completed'])
        self.assertEqual(info['captures'], 0)
        self.assertEqual(info['integrity_failures'], 0)
        self.assertEqual(info['terminal_capture_failures'], 1)
        self.assertEqual(info['failed_capture']['expected_payload_bytes'], 32760)
        self.assertEqual(info['failed_capture']['received_payload_bytes'], 31995)
        self.assertEqual(info['failed_capture']['retention_status'], 'verified_saved')
        self.assertNotIn('PRIVATE-FOREIGN-AIR', json.dumps(info))
        private = self.root/'.scratch/iq'
        self.assertEqual((private/'failed-0000.payload-prefix.bin').read_bytes(), prefix)
        self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o700)
        for file in private.iterdir():self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
        self.assertEqual(wire.requests, [b'CAP16 16380 6\n'])
        self.assertEqual(wire.events, [b'late tail'])
        with (self.root/'public/captures.csv').open() as file:
            self.assertEqual(list(csv.DictReader(file)), [])

    def test_empty_or_transport_failed_prefix_is_saved_with_precise_failure(self):
        for index,events in enumerate([[b''], [b'ab', OSError('PRIVATE-PORT')]]):
            with self.subTest(events=events):
                self.args[1] = str(self.root/f'public-{index}')
                self.args[3] = str(self.root/f'.scratch/iq-{index}')
                wire=Wire(events)
                with self.assertRaises((capture.PartialReadError,capture.PartialReadException)) as caught:
                    self.run_receiver(wire)
                info=json.loads(Path(self.args[1]).joinpath('manifest.json').read_text())
                self.assertEqual(info['terminal_failure']['failure_kind'], type(caught.exception).__name__)
                self.assertNotIn('PRIVATE-PORT', json.dumps(info))
                self.assertEqual(Path(self.args[3]).joinpath('failed-0000.payload-prefix.bin').read_bytes(), b'' if index==0 else b'ab')
                self.assertTrue(wire.closed)

    def test_raw_disk_failure_keeps_full_consumed_bytes_and_never_creates_success_row(self):
        payload=b'\x7f\x80'*16380
        wire=Wire([payload],header=f'DATA 16380 {zlib.crc32(payload):08x} 1030\n'.encode())
        with patch.object(receiver,'write_private',side_effect=OSError('disk unavailable')), self.assertRaises(OSError):
            self.run_receiver(wire)
        info=self.receipt()
        self.assertTrue(wire.closed)
        self.assertEqual(info['captures'],0)
        self.assertTrue(info['failed_capture']['payload_complete'])
        self.assertTrue(info['failed_capture']['full_read_crc_and_count_valid'])
        self.assertEqual((self.root/'.scratch/iq/failed-0000.payload-prefix.bin').read_bytes(),payload)

    def test_complete_prior_capture_remains_only_success_and_failure_gets_next_index(self):
        payload=b'\x7f\x80'*16380
        wire=Wire([payload,b'partial',b''],header=f'DATA 16380 {zlib.crc32(payload):08x} 1030\n'.encode())
        with self.assertRaises(capture.PartialReadError):self.run_receiver(wire)
        info=self.receipt()
        self.assertEqual(info['captures'],1)
        self.assertEqual(info['terminal_capture_failures'],1)
        with (self.root/'public/captures.csv').open() as file:rows=list(csv.DictReader(file))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['crc_and_count_valid'],'True')
        self.assertEqual((self.root/'.scratch/iq/iq-0000.bin').read_bytes(),payload)
        self.assertEqual((self.root/'.scratch/iq/failed-0001.payload-prefix.bin').read_bytes(),b'partial')
        self.assertEqual(wire.requests,[b'CAP16 16380 6\n']*2)

    def test_retention_and_publication_disk_failure_do_not_mask_original_read(self):
        wire=Wire([b'prefix',b''])
        original=Path.write_text
        def fail_public(path,*args,**kwargs):
            if path.name=='manifest.json':
                self.assertTrue(wire.closed)
                raise OSError('public disk full')
            return original(path,*args,**kwargs)
        with patch.object(capture,'write_private',side_effect=OSError('private disk full')), \
             patch.object(Path,'write_text',fail_public), self.assertRaises(capture.PartialReadError) as caught:
            self.run_receiver(wire)
        self.assertTrue(wire.closed)
        self.assertEqual(caught.exception.private_payload_prefix,b'prefix')
        self.assertEqual(caught.exception.publication_error_kind,'OSError')

    def test_close_failure_preserves_prefix_and_original_failure(self):
        wire=Wire([b'prefix',b''])
        with patch.object(wire,'close',side_effect=OSError('close failed')), self.assertRaises(capture.PartialReadError):
            self.run_receiver(wire)
        info=self.receipt()
        self.assertEqual(info['port_close']['error_kind'],'OSError')
        self.assertEqual(info['terminal_failure']['failure_kind'],'PartialReadError')
        self.assertEqual(info['failed_capture']['retention_status'],'verified_saved')

    def test_snapshot_loop_stops_and_closes_before_persistence_without_sync(self):
        wire=Wire([b'prefix',b'',b'late'],samples=256)
        original=capture.write_private
        def checked(path,data):
            self.assertTrue(wire.closed)
            return original(path,data)
        with patch.object(capture,'queries',return_value={'parsed_limits':{'rates':[16000000]}}), \
             patch.object(capture,'settings'),patch.object(capture,'synchronize') as sync, \
             patch.object(capture,'write_private',checked),contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaises(capture.PartialReadError):
            capture.run_snapshots(wire,self.root/'public',self.root/'.scratch/iq',3,256,[8],[16000000],{},'synthetic')
        sync.assert_not_called()
        self.assertEqual(wire.requests,[b'CAP16 256 6\n'])
        result=json.loads((self.root/'public/results.json').read_text())
        self.assertFalse(result['completed'])
        self.assertEqual(result['runs'][0]['success'],0)
        self.assertEqual(result['runs'][0]['attempts'],1)
        self.assertEqual(result['runs'][0]['requested_attempts'],3)
        with (self.root/'public/snapshots.csv').open() as file:row=list(csv.DictReader(file))[0]
        self.assertEqual(row['status'],'error')
        self.assertNotIn('crc_ok',row)

    def test_snapshot_main_close_failure_cannot_mask_original_read_or_send_release(self):
        wire=Wire([b'prefix',b''],samples=256)
        argv=['capture','--output',str(self.root/'public'),'--private',str(self.root/'.scratch/iq'),
              '--samples','256','--count','3','--bits','8','--rates','16000000']
        with patch.object(sys,'argv',argv),patch.object(capture,'open_board',return_value=wire), \
             patch.object(capture,'queries',return_value={'parsed_limits':{'rates':[16000000]}}), \
             patch.object(capture,'settings'),patch.object(capture,'synchronize') as sync, \
             patch.object(wire,'close',side_effect=OSError('close failed')), \
             contextlib.redirect_stdout(io.StringIO()),self.assertRaises(capture.PartialReadError) as caught:
            capture.main()
        self.assertEqual(sync.call_count,1)
        self.assertEqual(wire.requests,[b'CAP16 256 6\n'])
        self.assertEqual(caught.exception.serial_close_error_kind,'OSError')
        self.assertEqual((self.root/'.scratch/iq/failed-16000000-8-0000.payload-prefix.bin').read_bytes(),b'prefix')


class SpectrumRetention(unittest.TestCase):
    def test_actual_command_partial_start_reply_closes_without_release_and_saves_header(self):
        header=b'SPEC 256 16000000 PRIVATE-ADDRESS'
        wire=Wire([],header=header)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            args=SimpleNamespace(output=root/'public',private=root/'.scratch/raw',port='MOCK',baud=921600,
                frequency=2401,bandwidth=12,gain='hardware',seconds=60,rate=16000000,bins=256)
            with patch.object(spectrum,'open_board',return_value=wire),patch.object(spectrum,'synchronize'), \
                 patch.object(spectrum,'queries',return_value={}),patch.object(spectrum,'settings',return_value={}), \
                 contextlib.redirect_stdout(io.StringIO()):
                trial=spectrum.Trial(args);trial.run()
            result=json.loads((args.output/'results.json').read_text())
            self.assertTrue(wire.closed)
            self.assertEqual(wire.requests,[b'SPEC 60000 1 1 0 6 256 1\n'])
            self.assertEqual(result['rejected_frame']['kind'],'start_reply')
            self.assertTrue(result['framing_uncertain'])
            self.assertEqual(result['raw_persistence']['rejected_packet'],'verified')
            self.assertEqual((args.private/'rejected-frame.bin').read_bytes(),header)
            self.assertNotIn('PRIVATE-ADDRESS',json.dumps(result))
            self.assertNotIn('PRIVATE-ADDRESS',json.dumps(trial.state))

    def test_every_short_frame_stage_keeps_all_consumed_bytes(self):
        for prefix,expected in [(b'SP',4),(b'SPC1'+bytes(15),288),(b'SPS1abc',40)]:
            wire=Wire([prefix,b'',b'late'])
            with self.subTest(prefix=prefix), self.assertRaises(capture.PartialReadError) as caught:
                spectrum.spectrum_frame(wire,256)
            error=caught.exception
            self.assertEqual(error.rejected_raw,prefix)
            self.assertEqual(error.rejected_metadata['expected_frame_bytes'],expected)
            self.assertFalse(error.rejected_metadata['complete_frame'])
            self.assertIsNone(error.rejected_metadata['crc_ok'])
            self.assertEqual(wire.events,[b'late'])

    def test_partial_end_reply_and_read_exception_keep_prefix_and_original_cause(self):
        wire=Wire([b'SPEC'],header=b'END 0 0')
        with self.assertRaises(capture.PartialReadError) as caught:spectrum.spectrum_frame(wire,256)
        self.assertEqual(caught.exception.rejected_raw,b'SPECEND 0 0')
        cause=OSError('PRIVATE-TRANSPORT')
        with self.assertRaises(capture.PartialReadException) as caught:
            spectrum.spectrum_frame(Wire([b'SPC1',b'abc',cause]),256)
        self.assertIs(caught.exception.__cause__,cause)
        self.assertEqual(caught.exception.rejected_raw,b'SPC1abc')

    def test_trial_saves_short_frame_after_close_and_never_retries_or_exposes_bytes(self):
        wire=Wire([b'SPC1PRIVATE-ADDRESS',b'',b'late'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            args=SimpleNamespace(output=root/'public',private=root/'.scratch/raw',port='MOCK',baud=921600,
                frequency=2401,bandwidth=12,gain='hardware',seconds=60,rate=16000000,bins=256)
            original=spectrum.persist_verified
            def checked(path,data):
                self.assertTrue(wire.closed)
                return original(path,data)
            with patch.object(spectrum,'open_board',return_value=wire),patch.object(spectrum,'synchronize') as sync, \
                 patch.object(spectrum,'queries',return_value={}),patch.object(spectrum,'settings',return_value={}), \
                 patch.object(spectrum,'command',return_value='SPEC 256 16000000 256 2401') as command, \
                 patch.object(spectrum,'persist_verified',checked),contextlib.redirect_stdout(io.StringIO()):
                trial=spectrum.Trial(args);trial.run()
            self.assertTrue(wire.closed)
            self.assertEqual(sync.call_count,1)
            self.assertEqual(command.call_count,1)
            result=json.loads((args.output/'results.json').read_text())
            self.assertEqual(result['frames'],0)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['raw_persistence']['rejected_packet'],'verified')
            self.assertEqual((args.private/'rejected-frame.bin').read_bytes(),b'SPC1PRIVATE-ADDRESS')
            self.assertNotIn('PRIVATE-ADDRESS',json.dumps(result))
            self.assertNotIn('PRIVATE-ADDRESS',json.dumps(trial.state))
            self.assertFalse((args.output/'spectra.csv').exists())
            self.assertEqual(stat.S_IMODE(args.private.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE((args.private/'rejected-frame.bin').stat().st_mode),0o600)


if __name__=='__main__':unittest.main()

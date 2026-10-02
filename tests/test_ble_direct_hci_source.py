"""Direct source wire encoding/event/rollback tests, using no hardware."""
from collections import deque
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_direct_hci_source import Source, parameters, advertising_data, enable, command_frame, parse_event, raw_sockaddr, event_filter, duration_units, main


def complete(opcode, status=0):
    body = bytes([1])+struct.pack('<H', opcode)+bytes([status])
    if opcode == 0x2036:
        body += bytes([4])
    return bytes([4, 0x0e, len(body)])+body


TERMINATED_100 = bytes.fromhex('043e061243efffff64')


class FakeSocket:
    def __init__(self, failed=None, termination=TERMINATED_100, inject_early=False, duplicate=False, missing_ack=None):
        self.sent = []
        self.pending = deque()
        self.failed = failed or {}
        self.termination = termination
        self.inject_early = inject_early
        self.duplicate = duplicate
        self.missing_ack = missing_ack

    def settimeout(self, value):
        self.timeout = value

    def send(self, frame):
        self.sent.append(frame)
        opcode = struct.unpack_from('<H', frame, 1)[0]
        occurrence = sum(struct.unpack_from('<H', f, 1)[0] == opcode for f in self.sent)
        if self.inject_early and opcode == 0x2036:
            self.pending.append(TERMINATED_100)
        if self.missing_ack != (opcode, occurrence):
            self.pending.append(complete(opcode, self.failed.get((opcode, occurrence), 0)))
        if opcode == 0x2039 and frame[4] == 1 and self.failed.get((opcode, occurrence), 0) == 0:
            if self.termination is not None:
                self.pending.append(self.termination)
            if self.duplicate:
                self.pending.append(self.termination)
        return len(frame)

    def recv(self, size):
        if self.pending:
            return self.pending.popleft()
        raise TimeoutError()

    def close(self):
        self.closed = True


class DirectSourceTests(unittest.TestCase):
    def test_native_sockaddr_and_receive_filter_without_bluetooth_constants(self):
        self.assertEqual(raw_sockaddr(), struct.pack('=HHH', 31, 0, 0))
        self.assertEqual(len(event_filter()), 16)
        self.assertEqual(struct.unpack_from('=IIIH', event_filter()), (16, 49152, 1 << 30, 0))

    def test_fixed_legacy_single_channel_parameter_wire_layout(self):
        self.assertEqual(parameters(20).hex(), 'ef1000200000200000010000000000000000007f0100010000')
        self.assertEqual(len(parameters(20)), 25)
        self.assertEqual(parameters(100)[3:9], bytes.fromhex('a00000a00000'))
        self.assertEqual(parameters(20)[9], 1)
        self.assertEqual(parameters(20)[20], 1)
        with self.assertRaises(ValueError):
            parameters(30)

    def test_data_is_complete_sixteen_byte_owned_ad(self):
        data = advertising_data()
        self.assertEqual(data.hex(), 'ef0301100fffffff4553502d5344522d4556414c')
        self.assertEqual(command_frame(0x2037, data)[:4].hex(), '01372014')

    def test_enable_limit_and_disable_are_scoped_to_one_handle(self):
        self.assertEqual(enable(True, 100).hex(), '0101ef000064')
        self.assertEqual(enable(False).hex(), '0001ef000000')
        for count in (0, 256):
            with self.assertRaises(ValueError):
                enable(True, count)
        with self.assertRaises(ValueError):
            command_frame(0x0c03, b'')  # Reset must never be allowed.

    def test_handle_one_changes_only_scoped_handle_fields(self):
        self.assertEqual(parameters(20, 1), b'\x01'+parameters(20)[1:])
        self.assertEqual(advertising_data(1), b'\x01'+advertising_data()[1:])
        self.assertEqual(enable(True, 255, 1000, 1).hex(), '0101016400ff')
        self.assertEqual(enable(False, 255, 1000, 1).hex(), '000101000000')
        own = bytes.fromhex('043e06124301ffff64')
        self.assertEqual(parse_event(own, 1)['advertising_handle'], 1)
        self.assertIsNone(parse_event(TERMINATED_100, 1))
        self.assertIsNone(parse_event(own))
        for handle in (0, 2, 238, 240, True, '1'):
            sock = FakeSocket()
            with self.subTest(handle=handle), self.assertRaises(ValueError):
                Source(sock, lambda record: None).run(handle=handle)
            self.assertEqual(sock.sent, [])

    def test_handle_one_own_count_and_cleanup_exclude_foreign_ef(self):
        class ForeignBeforeOwn(FakeSocket):
            def send(self, frame):
                result = super().send(frame)
                if frame[1:3] == bytes.fromhex('3920') and frame[4] == 1:
                    self.pending.appendleft(TERMINATED_100)  # Foreign EF event.
                return result
        sock = ForeignBeforeOwn(termination=bytes.fromhex('043e06124301ffff64'))
        records = []
        result = Source(sock, records.append).run(20, 100, 0, handle=1)
        self.assertEqual(result['status'], 'controller_count_verified')
        self.assertTrue(result['handle_diagnostic_requested'])
        self.assertEqual(result['termination_events_observed'], 1)
        self.assertTrue(result['cleanup_success'])
        self.assertEqual(sock.sent[0][4], 1)
        self.assertEqual(sock.sent[1][4], 1)
        self.assertEqual(sock.sent[2][4:].hex(), '010101000064')
        self.assertEqual(sock.sent[-2][4:].hex(), '000101000000')
        self.assertEqual(sock.sent[-1][4:], b'\x01')
        self.assertTrue(all(r['advertising_handle'] == 1 for r in records if 'advertising_handle' in r))

    def test_handle_one_foreign_only_event_cannot_verify_count(self):
        clock = [0.]
        class AdvanceOnEmpty(FakeSocket):
            def recv(self, size):
                if not self.pending:
                    clock[0] += 30
                return super().recv(size)
        sock = AdvanceOnEmpty(termination=TERMINATED_100)
        with patch('ble_direct_hci_source.time.monotonic', lambda: clock[0]):
            result = Source(sock, lambda record: None).run(20, 100, 0, handle=1)
        self.assertEqual(result['error_code'], 'event_timeout')
        self.assertEqual(result['termination_events_observed'], 0)
        self.assertFalse(result['controller_completed_count_verified'])
        self.assertTrue(result['cleanup_success'])
        self.assertEqual(sock.sent[-2][4:].hex(), '000101000000')
        self.assertEqual(sock.sent[-1][4:], b'\x01')

    def test_handle_one_parameter_rejection_cleans_only_selected_handle(self):
        sock = FakeSocket(failed={(0x2036, 1): 0x12})
        result = Source(sock, lambda record: None).run(handle=1)
        self.assertFalse(result['controller_completed_count_verified'])
        self.assertTrue(result['cleanup_success'])
        self.assertEqual([struct.unpack_from('<H', f, 1)[0] for f in sock.sent], [0x2036, 0x2039, 0x203c])
        self.assertEqual(sock.sent[-2][4:].hex(), '000101000000')
        self.assertEqual(sock.sent[-1][4:], b'\x01')

    def test_handle_one_cli_records_diagnostic_and_closes_selected_socket(self):
        sock = FakeSocket(termination=bytes.fromhex('043e06123c01ffff00'))
        records = []
        with patch('sys.argv', ['source', '--handle', '1', '--events', '255',
                                 '--duration-ms', '1000', '--start-delay', '0']), \
                patch('ble_direct_hci_source.socket.socket', return_value=sock), \
                patch('ble_direct_hci_source.bind_raw'), \
                patch('ble_direct_hci_source.emit_stdout', records.append):
            self.assertEqual(main(), 2)
        config = records[0]
        self.assertEqual(config['advertising_handle'], 1)
        self.assertTrue(config['handle_diagnostic_requested'])
        self.assertEqual(config['duration_10ms_units'], 100)
        summary = [r for r in records if r['kind'] == 'source_closed'][0]
        self.assertEqual(summary['termination']['status'], 0x3c)
        self.assertEqual(summary['termination']['controller_reported_completed_extended_advertising_events'], 0)
        self.assertFalse(summary['controller_completed_count_verified'])
        self.assertTrue(summary['cleanup_success'])
        self.assertTrue(sock.closed)
        self.assertEqual(records[-1]['kind'], 'source_socket_closed')

    def test_published_shape_event_fixture_redacts_connection_handle(self):
        result = parse_event(TERMINATED_100)
        self.assertEqual(result, {'kind': 'termination_observed', 'status': 67,
                                 'advertising_handle': 239,
                                 'controller_reported_completed_extended_advertising_events': 100})
        self.assertNotIn('ffff', json.dumps(result))
        self.assertIsNone(parse_event(bytes.fromhex('043e06124301ffff64')))
        self.assertIsNone(parse_event(TERMINATED_100[:-1]))
        self.assertIsNone(parse_event(b'PRIVATE ADDRESS'))
        self.assertEqual(parse_event(complete(0x2036))['controller_selected_tx_power_dbm'], 4)
        self.assertEqual(parse_event(complete(0x2036, 0x12))['status'], 0x12)

    def run_fake(self, sock):
        records = []
        result = Source(sock, records.append, command_timeout=.005).run(20, 100, 0)
        return records, result

    def test_success_requires_observed_limit_termination_and_cleanup(self):
        sock = FakeSocket()
        records, result = self.run_fake(sock)
        self.assertEqual(result['status'], 'controller_count_verified')
        self.assertTrue(result['controller_completed_count_verified'])
        self.assertTrue(result['cleanup_success'])
        self.assertIsNone(result['independently_observed_air_emission_count'])
        self.assertEqual(result['termination_events_observed'], 1)
        self.assertEqual(len([r for r in records if r['kind'] == 'source_enabled']), 1)
        self.assertEqual([struct.unpack_from('<H', f, 1)[0] for f in sock.sent], [0x2036, 0x2037, 0x2039, 0x2039, 0x203c])
        self.assertEqual(sock.sent[-2][4:], enable(False))
        self.assertEqual(sock.sent[-1][4:], b'\xef')

    def test_maximum_255_event_limit_and_observed_counter(self):
        sock = FakeSocket(termination=bytes.fromhex('043e061243efffffff'))
        result = Source(sock, lambda record: None, command_timeout=.005).run(20, 255, 0)
        self.assertEqual(result['status'], 'controller_count_verified')
        self.assertEqual(result['termination']['controller_reported_completed_extended_advertising_events'], 255)
        self.assertEqual(sock.sent[2][4:].hex(), '0101ef0000ff')

    def test_duration_diagnostic_wire_bounds_and_cleanup_zeros(self):
        self.assertEqual(enable(True, 255, 100).hex(), '0101ef0a00ff')
        self.assertEqual(enable(True, 255, 1000).hex(), '0101ef6400ff')
        self.assertEqual(enable(True, 255, 5000).hex(), '0101eff401ff')
        self.assertEqual(enable(False, 255, 5000).hex(), '0001ef000000')
        self.assertEqual(duration_units(0), 0)
        for invalid in (-10, 10, 99, 101, 5001, 5010, 100.0):
            sock = FakeSocket()
            with self.subTest(duration=invalid), self.assertRaises(ValueError):
                Source(sock, lambda record: None).run(duration_ms=invalid)
            self.assertEqual(sock.sent, [])

    def test_duration_expiry_retains_actual_count_but_cannot_pass_limit_gate(self):
        for duration, observed_count in ((0, 255), (1000, 0), (1000, 9), (5000, 99),
                                          (5000, 100), (5000, 255)):
            packet = bytes.fromhex('043e06123cefffff')+bytes([observed_count])
            sock = FakeSocket(termination=packet)
            records = []
            result = Source(sock, records.append).run(100, 255, 0, duration)
            with self.subTest(duration=duration, observed_count=observed_count):
                self.assertEqual(result['status'], 'trial_failed')
                self.assertEqual(result['error_code'], 'termination_status_or_count_mismatch')
                self.assertFalse(result['controller_completed_count_verified'])
                self.assertEqual(result['termination']['status'], 0x3c)
                self.assertEqual(result['termination']['controller_reported_completed_extended_advertising_events'], observed_count)
                self.assertTrue(result['cleanup_success'])
                self.assertEqual(sock.sent[-2][4:], enable(False, 255))
                self.assertEqual(len([r for r in records if r['kind'] == 'termination_observed']), 1)
                self.assertEqual(result['duration_diagnostic_requested'], duration != 0)

    def test_limit_can_win_duration_race_without_relaxing_count_or_sequence(self):
        good = bytes.fromhex('043e061243efffffff')
        for sock, accepted in ((FakeSocket(termination=good), True),
                               (FakeSocket(termination=good, duplicate=True), False),
                               (FakeSocket(termination=good, inject_early=True), False),
                               (FakeSocket(termination=TERMINATED_100), False),
                               (FakeSocket(termination=good, failed={(0x2039, 2): 0x0c}), False)):
            result = Source(sock, lambda record: None).run(20, 255, 0, 5000)
            self.assertEqual(result['status'] == 'controller_count_verified', accepted)
            self.assertEqual(sock.sent[-2][4:], enable(False, 255))

    def test_duration_timeout_is_bounded_and_does_not_invent_emissions(self):
        clock = [0.]
        class AdvanceOnEmpty(FakeSocket):
            def recv(self, size):
                if not self.pending:
                    clock[0] += .25
                return super().recv(size)
        sock = AdvanceOnEmpty(termination=None)
        with patch('ble_direct_hci_source.time.monotonic', lambda: clock[0]):
            result = Source(sock, lambda record: None).run(100, 255, 0, 1000)
        self.assertEqual(clock[0], 6.)
        self.assertEqual(result['error_code'], 'event_timeout')
        self.assertNotIn('termination', result)
        self.assertFalse(result['controller_completed_count_verified'])
        self.assertIsNone(result['independently_observed_air_emission_count'])
        self.assertTrue(result['cleanup_success'])

    def test_invalid_cli_duration_never_opens_controller_socket(self):
        with patch('sys.argv', ['source', '--duration-ms', '101']), \
                patch('ble_direct_hci_source.socket.socket') as socket_factory, \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        socket_factory.assert_not_called()

    def test_parameter_rejection_never_enables_or_falls_back(self):
        sock = FakeSocket(failed={(0x2036, 1): 0x12})
        records, result = self.run_fake(sock)
        self.assertEqual(result['status'], 'trial_failed')
        self.assertEqual([struct.unpack_from('<H', f, 1)[0] for f in sock.sent], [0x2036, 0x2039, 0x203c])
        self.assertEqual(sock.sent[1][4], 0)
        self.assertFalse(result['controller_completed_count_verified'])
        self.assertEqual(result['automatic_fallbacks'], 0)
        self.assertTrue(result['cleanup_success'])

    def test_data_failure_and_missing_enable_ack_both_cleanup(self):
        for sock in (FakeSocket(failed={(0x2037, 1): 0x0c}), FakeSocket(missing_ack=(0x2039, 1))):
            with self.subTest(sock=sock):
                _, result = self.run_fake(sock)
                self.assertEqual(result['status'], 'trial_failed')
                self.assertTrue(result['cleanup_success'])

    def test_mismatched_count_status_and_pre_enable_termination_rejected(self):
        for sock in (FakeSocket(termination=bytes.fromhex('043e061243efffff63')),
                     FakeSocket(termination=bytes.fromhex('043e061200efffff64')),
                     FakeSocket(inject_early=True)):
            with self.subTest(sock=sock):
                _, result = self.run_fake(sock)
                self.assertEqual(result['status'], 'trial_failed')
                self.assertFalse(result['controller_completed_count_verified'])
                self.assertTrue(result['cleanup_success'])

    def test_duplicate_termination_and_failed_cleanup_cannot_pass(self):
        _, duplicate = self.run_fake(FakeSocket(duplicate=True))
        self.assertEqual(duplicate['status'], 'trial_failed')
        self.assertFalse(duplicate['controller_completed_count_verified'])
        _, cleanup = self.run_fake(FakeSocket(failed={(0x2039, 2): 0x0c}))
        self.assertEqual(cleanup['status'], 'cleanup_failed')
        self.assertEqual(cleanup['cleanup']['cleanup_disable']['status'], 0x0c)
        self.assertEqual(cleanup['cleanup']['cleanup_remove']['status'], 0)

    def test_missing_or_foreign_handle_termination_times_out_and_cleans_up(self):
        for foreign in (None, bytes.fromhex('043e06124301ffff64')):
            clock = [0.]
            class AdvanceOnEmpty(FakeSocket):
                def recv(self, size):
                    if not self.pending:
                        clock[0] += 30
                    return super().recv(size)
            sock = AdvanceOnEmpty(termination=foreign)
            with patch('ble_direct_hci_source.time.monotonic', lambda: clock[0]):
                _, result = self.run_fake(sock)
            self.assertEqual(result['status'], 'trial_failed')
            self.assertEqual(result['termination_events_observed'], 0)
            self.assertFalse(result['controller_completed_count_verified'])
            self.assertTrue(result['cleanup_success'])


if __name__ == '__main__':
    unittest.main()

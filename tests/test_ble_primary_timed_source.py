"""Host-only timer/wire/order/clock/cleanup fixtures; never a real socket."""
from collections import deque
import contextlib
import io
from pathlib import Path
import signal
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ble_primary_timed_source as timed
import ble_direct_hci_source as v1


class Clock:
    def __init__(self): self.now = 100.0
    def monotonic(self): return self.now
    def ns(self): return round(self.now * 1e9)


def ack(opcode, status=0, power=7):
    body = bytes([1]) + struct.pack('<H', opcode) + bytes([status])
    if opcode == 0x2036 and power is not None: body += bytes([power & 255])
    return bytes([4, 14, len(body)]) + body


def termination(status=0x3c, count=0, handle=1):
    return bytes([4, 0x3e, 6, 0x12, status, handle, 255, 255, count])


class Socket:
    def __init__(self, clock, elapsed=25, status=0x3c, count=0, before=None,
                 duplicate=False, fail=None, power=7, missing=None, term_handle=1):
        self.clock = clock; self.elapsed = elapsed; self.status = status; self.count = count
        self.before = before; self.duplicate = duplicate; self.fail = fail or {}
        self.power = power; self.missing = missing; self.term_handle = term_handle
        self.pending = deque(); self.sent = []; self.closed = False
    def settimeout(self, timeout): self.timeout = timeout
    def send(self, frame):
        self.sent.append(frame); opcode = struct.unpack_from('<H', frame, 1)[0]
        number = sum(struct.unpack_from('<H', f, 1)[0] == opcode for f in self.sent)
        key = (opcode, number)
        if opcode == 0x2039 and frame[4] == 0:
            # Scoped disable cancels a timer packet scheduled for the future;
            # already queued/duplicate immediate events remain visible.
            self.pending = deque((delay,packet)for delay,packet in self.pending if delay <= 0)
        if self.before == key: self.pending.append((0, termination()))
        if self.missing != key: self.pending.append((0, ack(opcode, self.fail.get(key, 0), self.power)))
        if opcode == 0x2039 and frame[4] == 1:
            self.pending.append((self.elapsed, termination(self.status, self.count, self.term_handle)))
            if self.duplicate: self.pending.append((0, termination(self.status, self.count)))
        return len(frame)
    def recv(self, _):
        if not self.pending:
            self.clock.now += 3
            raise TimeoutError()
        delay, packet = self.pending.popleft(); self.clock.now += delay; return packet
    def close(self): self.closed = True


class TimedSourceTests(unittest.TestCase):
    def test_parent_clock_and_enable_margin_include_commands_and_emission(self):
        for deadline_ns, delay, success in ((132000000000, 0, True),
                                           (131999999999, 0, False),
                                           (145000000000, 14, False)):
            clock=Clock();sock=Socket(clock);records=[]
            def emit(row):
                records.append(row)
                if row['kind']=='command_sent' and row.get('step')=='enable':clock.now+=delay
            with patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns):
                source=timed.TimedSource(sock,emit,deadline_ns=deadline_ns)
                result=source.run_timed()
            self.assertEqual(result['controller_timed_profile_verified'],success)
            self.assertEqual(result['episode_deadline_monotonic_ns'],deadline_ns)
            enables=[f for f in sock.sent if f[1:3]==b'\x39\x20' and f[4]==1]
            self.assertEqual(len(enables),int(success));self.assertTrue(result['cleanup_success'])

    def test_late_final_cleanup_and_terminal_return_never_qualify(self):
        for phase in ('cleanup_remove','source_closed'):
            def sink(clock,row):
                if (row['kind']=='command_result' and row.get('step')==phase)or row['kind']==phase:
                    clock.now=145
            result,_,_,_=self.run_fixture(sink=sink)
            self.assertFalse(result['controller_timed_profile_verified'])

    def test_parent_deadline_validation_and_expired_cli_before_socket(self):
        for value in (True,0,-1,2**63,'100'):
            with self.assertRaises(ValueError):timed.parent_deadline(value)
        with patch.object(timed.socket,'socket')as sock,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(timed.main(['--profile',timed.PROFILE,'--parent-deadline-monotonic-ns','1']),2)
        sock.assert_not_called()

    def test_slow_frame_construction_and_short_send_refuse_with_cleanup(self):
        clock=Clock();sock=Socket(clock);frames=v1.command_frame
        def frame(opcode,payload):
            if opcode==0x2039 and payload[0]==1:clock.now+=14
            return frames(opcode,payload)
        with patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns),\
             patch.object(v1,'command_frame',side_effect=frame):
            result=timed.TimedSource(sock,lambda row:None).run_timed()
        self.assertFalse(result['controller_timed_profile_verified']);self.assertTrue(result['cleanup_success'])
        self.assertFalse(any(f[1:3]==b'\x39\x20' and f[4]==1 for f in sock.sent))
        class Short(Socket):
            def send(self,frame):
                value=super().send(frame)
                return value-1 if frame[1:3]==b'\x36\x20' else value
        result,_,_,_=self.run_fixture(socket=Short)
        self.assertFalse(result['controller_timed_profile_verified']);self.assertEqual(result['error_code'],'short_command_send')

    def run_fixture(self, socket=None, sink=None, **options):
        clock = Clock(); sock = socket(clock) if socket else Socket(clock, **options); records = []
        def emit(record):
            records.append(record)
            if sink: sink(clock, record)
        with patch.object(timed.time, 'monotonic', clock.monotonic), patch.object(timed.time, 'monotonic_ns', clock.ns):
            source = timed.TimedSource(sock, emit); result = source.run_timed()
        return result, records, sock, source

    def test_exact_independent_wire_and_new_success_status(self):
        result, records, sock, _ = self.run_fixture()
        self.assertEqual([f.hex() for f in sock.sent], [
            '01362019010000200000200000010000000000000000007f0100010000',
            '0137200401030100', '01392006010101c40900', '01392006000101000000', '013c200101'])
        self.assertEqual(result['status'], 'controller_timed_profile_verified')
        self.assertTrue(result['controller_timed_profile_verified']); self.assertFalse(result['controller_completed_count_verified'])
        self.assertFalse(result['termination_count_field_meaningful']); self.assertIsNone(result['independently_observed_air_emission_count'])
        self.assertEqual(result['observed_enabled_seconds'], 25); self.assertTrue(result['cleanup_success'])
        self.assertEqual(result['accepted_steps'], sorted(timed.STEPS))
        self.assertEqual(len(records), 19)

    def test_all_uint8_counts_retained_as_unqualified_metadata(self):
        for count in (0, 1, 100, 160, 255):
            with self.subTest(count=count):
                result, _, _, _ = self.run_fixture(count=count)
                self.assertTrue(result['controller_timed_profile_verified'])
                self.assertEqual(result['termination']['controller_reported_completed_extended_advertising_events'], count)
                self.assertEqual(result['completed_count_metadata_anomaly'], count != 0)
                self.assertFalse(result['controller_completed_count_verified'])

    def test_exact_lower_boundary_and_strict_upper_boundary(self):
        for elapsed, passes in ((23.999, False), (24, True), (29.999, True), (30, False), (31, False)):
            with self.subTest(elapsed=elapsed):
                result, _, sock, _ = self.run_fixture(elapsed=elapsed)
                self.assertEqual(result['controller_timed_profile_verified'], passes)
                self.assertTrue(result['cleanup_success']); self.assertEqual(sock.sent[-1][4:], b'\x01')

    def test_limit_success_cannot_replace_timer_profile(self):
        for status in (0, 0x43, 0x42):
            result, _, _, _ = self.run_fixture(status=status, count=100)
            self.assertFalse(result['controller_timed_profile_verified']); self.assertTrue(result['cleanup_success'])

    def test_profile_mutation_and_bool_alias_refused_without_commands(self):
        for key, values in {'profile':['extended-primary-zero-data-v1', True], 'handle':[239, True],
                            'interval_ms':[100, 20.0], 'events':[100, False],
                            'duration_ms':[5000, 25000.0], 'start_delay':[1, True, float('nan')]}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    timed.validate_profile(**{key:value})
        with self.assertRaises(ValueError): timed.enable_frame(1)

    def test_invalid_cli_never_creates_socket(self):
        for argv in ([], ['--profile', timed.PROFILE, '--events', '100'],
                     ['--profile', timed.PROFILE, '--duration-ms', '5000'],
                     ['--profile', timed.PROFILE, '--unlimited-events']):
            with patch.object(timed.socket, 'socket') as factory, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                timed.main(argv)
            factory.assert_not_called()

    def test_v1_rejects_new_profile_and_keeps_counted_gate(self):
        with self.assertRaises(ValueError): v1.duration_units(25000)
        with self.assertRaises(ValueError): v1.validate_primary_zero_data(20,0,25000,1,True,True,True)
        from test_ble_direct_hci_source import FakeSocket
        sock = FakeSocket(termination=termination(0x3c,0))
        result = v1.Source(sock, lambda _:None).run(20,100,0,5000,1,False,True,True)
        self.assertEqual(result['status'], 'trial_failed'); self.assertFalse(result['controller_completed_count_verified'])

    def test_before_ack_or_before_enable_termination_refuses(self):
        for key in ((0x2036,1), (0x2037,1), (0x2039,1)):
            result, _, sock, _ = self.run_fixture(before=key)
            self.assertFalse(result['controller_timed_profile_verified'])
            self.assertEqual(result['error_code'], 'termination_before_enable_ack')
            self.assertEqual(sock.sent[-1][4:], b'\x01')

    def test_duplicate_during_cleanup_never_qualifies(self):
        result, records, _, _ = self.run_fixture(duplicate=True)
        self.assertFalse(result['controller_timed_profile_verified']); self.assertEqual(result['termination_events_observed'],2)
        self.assertTrue(any(r.get('kind')=='termination_observed' for r in records))

    def test_foreign_handle_cannot_qualify(self):
        result, _, _, _ = self.run_fixture(term_handle=239)
        self.assertFalse(result['controller_timed_profile_verified']); self.assertEqual(result['termination_events_observed'],0)

    def test_unsolicited_or_duplicate_ack_refuses(self):
        class ExtraAck(Socket):
            def send(self, frame):
                out = super().send(frame)
                if frame[1:3] == bytes.fromhex('3620'): self.pending.append((0, ack(0x2036)))
                return out
        result, _, sock, _ = self.run_fixture(socket=ExtraAck)
        self.assertFalse(result['controller_timed_profile_verified']); self.assertEqual(result['error_code'],'unexpected_or_duplicate_ack')
        self.assertFalse(any(f[1:3]==bytes.fromhex('3920') and f[4]==1 for f in sock.sent))

    def test_selected_power_full_signed_range_and_invalid_power(self):
        for power in (-127, 0, 7, 20, -128, 21, 127, None):
            with self.subTest(power=power):
                result, _, _, _ = self.run_fixture(power=power)
                self.assertEqual(result['controller_timed_profile_verified'], power is not None and -127<=power<=20)

    def test_failed2036_discards_undefined_power_and_retains_failure(self):
        for power in (None, -128, 7):
            result, records, _, _ = self.run_fixture(fail={(0x2036,1):0x12}, power=power)
            self.assertFalse(result['controller_timed_profile_verified'])
            failed = [r for r in records if r.get('hci_opcode_hex')=='2036' and r.get('status')==0x12]
            self.assertTrue(failed); self.assertTrue(all('controller_selected_tx_power_dbm'not in r for r in failed))

    def test_each_rejected_or_missing_ack_still_attempts_both_cleanup_commands(self):
        for key in ((0x2036,1),(0x2037,1),(0x2039,1),(0x2039,2),(0x203c,1)):
            for mode in ('fail','missing'):
                opts={'fail':{key:0x12}} if mode=='fail' else {'missing':key}
                with self.subTest(key=key,mode=mode):
                    result, _, sock, _ = self.run_fixture(**opts)
                    self.assertFalse(result['controller_timed_profile_verified'])
                    self.assertEqual(sock.sent[-2][4:], timed.enable_frame(False)); self.assertEqual(sock.sent[-1][4:],b'\x01')

    def test_late_send_receive_and_emit_cannot_pass(self):
        class SlowSend(Socket):
            def send(self, frame):
                out=super().send(frame)
                if len(self.sent)==1:self.clock.now+=2
                return out
        class SlowRecv(Socket):
            def recv(self,size):
                out=super().recv(size)
                if len(self.sent)==1:self.clock.now+=2
                return out
        def slow_emit(clock,record):
            if record['kind']=='command_result' and record['step']=='set_parameters':clock.now+=2
        for socket, sink in ((SlowSend,None),(SlowRecv,None),(None,slow_emit)):
            result, _, _, _ = self.run_fixture(socket=socket,sink=sink)
            self.assertFalse(result['controller_timed_profile_verified']); self.assertEqual(result['error_code'],'timed_operation_deadline')

    def test_cleanup_ack_late_return_prevents_success(self):
        def slow(clock,record):
            if record['kind']=='command_result' and record['step']=='cleanup_remove':clock.now+=2
        result, _, _, _ = self.run_fixture(sink=slow)
        self.assertFalse(result['controller_timed_profile_verified']); self.assertFalse(result['cleanup_success'])

    def test_cancel_defers_repeated_requests_through_cleanup(self):
        clock=Clock(); sock=Socket(clock); records=[]; source=None
        def emit(row):
            records.append(row)
            if row.get('kind')=='source_enabled' or row.get('step')=='cleanup_disable':source.cancel()
        with patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns):
            source=timed.TimedSource(sock,emit);result=source.run_timed()
        self.assertEqual(result['status'],'interrupted');self.assertTrue(result['cleanup_success'])
        self.assertFalse(result['controller_timed_profile_verified']);self.assertEqual(sock.sent[-1][4:],b'\x01')

    def test_no_second_run_or_fallback(self):
        _, _, sock, source = self.run_fixture();before=len(sock.sent)
        with self.assertRaises(ValueError):source.run_timed()
        self.assertEqual(len(sock.sent),before)

    def test_cancel_while_no_packet_arrives_returns_to_bounded_cleanup(self):
        clock=Clock();source=None
        class IdleThenCancel(Socket):
            def send(self,frame):
                out=super().send(frame)
                if frame[1:3]==bytes.fromhex('3920')and frame[4]==1:
                    self.pending=deque((d,p)for d,p in self.pending if d==0)
                return out
            def recv(self,size):
                if not self.pending:
                    source.cancel();clock.now+=.2;raise TimeoutError()
                return super().recv(size)
        sock=IdleThenCancel(clock)
        with patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns):
            source=timed.TimedSource(sock,lambda _:None);result=source.run_timed()
        self.assertEqual(result['status'],'interrupted');self.assertTrue(result['cleanup_success']);self.assertLess(clock.now,101)

    def test_main_cancellation_during_socket_close_refuses_success(self):
        clock=Clock()
        class CancelOnClose(Socket):
            def close(self):
                super().close();signal.getsignal(signal.SIGTERM)(signal.SIGTERM,None)
        sock=CancelOnClose(clock);output=io.StringIO()
        with patch.object(timed.socket,'socket',return_value=sock),patch.object(v1,'bind_raw'),\
             patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns),\
             contextlib.redirect_stdout(output):self.assertEqual(timed.main(['--profile',timed.PROFILE]),2)
        rows=[__import__('json').loads(v)for v in output.getvalue().splitlines()]
        self.assertFalse([v for v in rows if v['kind']=='source_closed'][-1]['controller_timed_profile_verified'])

    def test_post_summary_cancel_and_late_socket_close_correct_saved_terminal(self):
        clock=Clock();sock=Socket(clock);records=[];source=None
        def emit(row):
            records.append(dict(row))
            if row['kind']=='source_closed':source.cancel()
        with patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns):
            source=timed.TimedSource(sock,emit);result=source.run_timed()
        self.assertFalse(result['controller_timed_profile_verified']);self.assertFalse(records[-1]['controller_timed_profile_verified'])
        class LateClose(Socket):
            def close(self):super().close();clock.now+=25
        clock=Clock();sock=LateClose(clock);output=io.StringIO()
        with patch.object(timed.socket,'socket',return_value=sock),patch.object(v1,'bind_raw'),\
             patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns),\
             contextlib.redirect_stdout(output):self.assertEqual(timed.main(['--profile',timed.PROFILE]),2)
        rows=[__import__('json').loads(v)for v in output.getvalue().splitlines()]
        self.assertTrue(sock.closed);self.assertFalse([v for v in rows if v['kind']=='source_closed'][-1]['controller_timed_profile_verified'])

    def test_output_or_close_error_still_restores_signal_handlers(self):
        clock=Clock();sock=Socket(clock);prior={s:signal.getsignal(s)for s in (signal.SIGINT,signal.SIGTERM)}
        rows=[]
        def emit(record):
            rows.append(dict(record))
            if record['kind']=='source_socket_closed':raise OSError('fixture output failed')
        with patch.object(timed.socket,'socket',return_value=sock),patch.object(v1,'bind_raw'),\
             patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns),\
             patch.object(timed,'emit_stdout',side_effect=emit):self.assertEqual(timed.main(['--profile',timed.PROFILE]),2)
        self.assertTrue(sock.closed);self.assertEqual({s:signal.getsignal(s)for s in prior},prior)
        self.assertFalse([v for v in rows if v['kind']=='source_closed'][-1]['controller_timed_profile_verified'])

    def test_main_closes_socket_and_restores_handlers_on_normal_and_cancel(self):
        clock=Clock();sock=Socket(clock);prior={s:signal.getsignal(s)for s in (signal.SIGINT,signal.SIGTERM)}
        with patch.object(timed.socket,'socket',return_value=sock),patch.object(v1,'bind_raw'),\
             patch.object(timed.time,'monotonic',clock.monotonic),patch.object(timed.time,'monotonic_ns',clock.ns),\
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(timed.main(['--profile',timed.PROFILE]),0)
        self.assertTrue(sock.closed);self.assertEqual({s:signal.getsignal(s)for s in prior},prior)


if __name__ == '__main__': unittest.main()

"""Scoped container policy and lifecycle checks; no Docker or devices opened."""
import contextlib
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ble_dumpcap_container_monitor import container_command, remove_owned_container
from ble_dumpcap_monitor import capture_command

NAME = 'esp-sdr-ble-monitor-'+'a'*32
IMAGE = 'sha256:'+'b'*64
EXECUTABLE = '/nix/store/test-wireshark/bin/dumpcap'


class ContainerMonitorTests(unittest.TestCase):
    def test_real_sigterm_during_capture_runs_cleanup_and_reaps_producer(self):
        from test_ble_dumpcap_monitor import global_header
        previous = signal.getsignal(signal.SIGTERM)
        code = ('import os,signal,sys,time;'
                'sys.stdout.buffer.write('+repr(global_header())+');sys.stdout.flush();'
                'time.sleep(.1);os.kill(os.getppid(),signal.SIGTERM);time.sleep(30)')
        calls = []
        with contextlib.redirect_stdout(io.StringIO()):
            result = capture_command([sys.executable, '-c', code], 3,
                                     producer_cleanup=lambda: calls.append('removed') or True)
        self.assertEqual(result['status'], 'interrupted')
        self.assertTrue(result['interrupted'])
        self.assertEqual(calls, ['removed'])
        self.assertTrue(result['owned_container_removed'])
        self.assertTrue(result['producer_reaped'])
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)

    def test_repeated_signals_during_cleanup_do_not_skip_reaping(self):
        from test_ble_dumpcap_monitor import global_header
        def cleanup():
            os.kill(os.getpid(), signal.SIGTERM)
            os.kill(os.getpid(), signal.SIGINT)
            return True
        command = [sys.executable, '-c', 'import sys;sys.stdout.buffer.write('+repr(global_header())+')']
        with contextlib.redirect_stdout(io.StringIO()):
            result = capture_command(command, 1, producer_cleanup=cleanup)
        self.assertEqual(result['status'], 'interrupted')
        self.assertTrue(result['owned_container_removed'])
        self.assertTrue(result['producer_reaped'])

    def test_cleanup_exception_still_reaps_producer(self):
        from test_ble_dumpcap_monitor import global_header
        def cleanup():
            raise RuntimeError('private diagnostic')
        command = [sys.executable, '-c', 'import sys;sys.stdout.buffer.write('+repr(global_header())+')']
        with contextlib.redirect_stdout(io.StringIO()):
            result = capture_command(command, 1, producer_cleanup=cleanup)
        self.assertEqual(result['status'], 'container_cleanup_failed')
        self.assertTrue(result['producer_reaped'])
        self.assertNotIn('private diagnostic', str(result))

    def test_only_fixed_nix_monitor_can_run_without_host_mounts(self):
        command = container_command(NAME, IMAGE, EXECUTABLE, 5)
        self.assertEqual(command[command.index('--network')+1], 'host')
        self.assertEqual(command[command.index('--cap-drop')+1], 'ALL')
        self.assertEqual(command[command.index('--cap-add')+1], 'NET_RAW')
        self.assertEqual(command[command.index('--pull')+1], 'never')
        self.assertEqual(command[command.index('--entrypoint')+1], EXECUTABLE)
        self.assertEqual(command[command.index('-i')+1], 'bluetooth-monitor')
        self.assertEqual(command[command.index('-w')+1], '-')
        self.assertIn('no-new-privileges', command)
        self.assertIn('--read-only', command)
        for forbidden in ('--privileged', '--volume', '-v', '--mount', '--device', 'NET_ADMIN'):
            self.assertNotIn(forbidden, command)

    def test_mutable_image_unknown_name_executable_or_unbounded_time_rejected(self):
        for name, image, executable, seconds in (
                ('someone-elses-container', IMAGE, EXECUTABLE, 5),
                (NAME, 'latest', EXECUTABLE, 5), (NAME, IMAGE, '/usr/bin/dumpcap', 5),
                (NAME, IMAGE, '/nix/store/x/../../../tmp/bin/dumpcap', 5),
                (NAME, IMAGE, EXECUTABLE, 0), (NAME, IMAGE, EXECUTABLE, 3601)):
            with self.assertRaises(ValueError):
                container_command(name, image, executable, seconds)

    def test_cleanup_targets_only_owned_name(self):
        with patch('ble_dumpcap_container_monitor.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertTrue(remove_owned_container(NAME))
        self.assertEqual(run.call_args.args[0], ['docker', 'rm', '--force', NAME])
        with patch('ble_dumpcap_container_monitor.subprocess.run') as run, self.assertRaises(ValueError):
            remove_owned_container('someone-elses-container')
        run.assert_not_called()

    def test_missing_container_requires_successful_absence_check(self):
        for list_status, stdout, accepted in ((0, b'', True), (0, b'still-running', False), (1, b'', False)):
            results = [subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], list_status, stdout=stdout)]
            with patch('ble_dumpcap_container_monitor.subprocess.run', side_effect=results) as run:
                self.assertEqual(remove_owned_container(NAME), accepted)
            self.assertEqual(run.call_args.args[0][3:5], ['--filter', f'name=^{NAME}$'])

    def test_parser_failure_still_runs_owned_cleanup_and_reaps_producer(self):
        with contextlib.redirect_stdout(io.StringIO()), patch('builtins.print'):
            calls = []
            result = capture_command([sys.executable, '-c', 'import sys;sys.stdout.buffer.write(bytes(24))'],
                                     1, producer_cleanup=lambda: calls.append('removed') or True)
        self.assertEqual(calls, ['removed'])
        self.assertEqual(result['status'], 'invalid_pcap')
        self.assertTrue(result['owned_container_removed'])
        self.assertTrue(result['producer_reaped'])

    def test_cleanup_failure_cannot_be_completed(self):
        from test_ble_dumpcap_monitor import global_header
        command = [sys.executable, '-c', 'import sys;sys.stdout.buffer.write('+repr(global_header())+')']
        with contextlib.redirect_stdout(io.StringIO()):
            result = capture_command(command, 1, producer_cleanup=lambda: False)
        self.assertEqual(result['status'], 'container_cleanup_failed')
        self.assertFalse(result['owned_container_removed'])
        self.assertTrue(result['producer_reaped'])


if __name__ == '__main__':
    unittest.main()

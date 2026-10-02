"""Source container scoping/interrupt policy without Docker or HCI access."""
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
import ble_source_container as wrapper
from ble_direct_hci_source import interrupt_source

NAME = 'esp-sdr-ble-source-'+'c'*32
IMAGE = 'sha256:'+'d'*64
PYTHON = '/nix/store/test-python/bin/python3'
OPTIONS = ['--handle', '1', '--events', '0', '--unlimited-events', '--duration-ms', '5000']


class SourceContainerTests(unittest.TestCase):
    def test_fixed_source_mount_and_capabilities_without_host_writes(self):
        command = wrapper.source_command(NAME, IMAGE, PYTHON, OPTIONS)
        self.assertEqual(command[command.index('--pull')+1], 'never')
        self.assertEqual(command[command.index('--cap-drop')+1], 'ALL')
        self.assertEqual(command.count('--cap-add'), 2)
        self.assertIn('NET_RAW', command); self.assertIn('NET_ADMIN', command)
        self.assertEqual(command[command.index('--network')+1], 'host')
        self.assertEqual(command.count('--mount'), 1)
        self.assertEqual(command[command.index('--mount')+1], f'type=bind,src={wrapper.SOURCE},dst=/source.py,readonly')
        self.assertIn('--read-only', command); self.assertIn('no-new-privileges', command)
        self.assertEqual(command[-len(OPTIONS)-1:], ['/source.py', *OPTIONS])
        self.assertNotIn('--privileged', command); self.assertNotIn('--device', command)

    def test_mutable_image_non_nix_python_or_other_owned_name_rejected(self):
        for name, image, executable in (('other-container', IMAGE, PYTHON),
                                       (NAME, 'latest', PYTHON), (NAME, IMAGE, '/usr/bin/python3')):
            with self.assertRaises(ValueError):
                wrapper.source_command(name, image, executable, OPTIONS)

    def test_graceful_cleanup_precedes_any_force_removal(self):
        with patch.object(wrapper, 'container_absent', return_value=True), \
                patch.object(wrapper.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            receipt = wrapper.stop_owned_source(NAME)
        self.assertTrue(receipt['owned_container_removed'])
        self.assertFalse(receipt['force_removal_required'])
        self.assertEqual(run.call_args.args[0], ['docker', 'stop', '--signal', 'SIGINT', '--timeout', '8', NAME])

    def test_force_removal_is_explicit_and_no_other_container_is_touched(self):
        with patch.object(wrapper, 'container_absent', side_effect=[False, True]), \
                patch.object(wrapper.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)) as run:
            receipt = wrapper.stop_owned_source(NAME)
        self.assertTrue(receipt['force_removal_required'])
        self.assertTrue(receipt['owned_container_removed'])
        self.assertEqual(run.call_args_list[0].args[0][-1], NAME)
        self.assertEqual(run.call_args_list[1].args[0], ['docker', 'rm', '--force', NAME])
        with patch.object(wrapper.subprocess, 'run') as run, self.assertRaises(ValueError):
            wrapper.stop_owned_source('other-container')
        run.assert_not_called()

    def test_invalid_unbounded_request_never_calls_docker(self):
        with patch.object(sys, 'argv', ['wrapper', '--events', '0', '--unlimited-events']), \
                patch.object(wrapper.subprocess, 'run') as run, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            wrapper.main()
        run.assert_not_called()

    def test_term_interrupt_runs_owned_cleanup_and_restores_host_handlers(self):
        class FakeProducer:
            returncode = None
            def poll(self): return self.returncode
        proc = FakeProducer()
        previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
        def graceful_stop(name):
            proc.returncode = 2
            return {'owned_container_removed': True, 'force_removal_required': False}
        def interrupt(_seconds):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        env = {'BLE_SOURCE_IMAGE': '/nix/store/test-source.tar.gz',
               'BLE_SOURCE_IMAGE_TAG': 'esp-source:test', 'BLE_SOURCE_PYTHON': PYTHON}
        output = io.StringIO()
        with patch.object(sys, 'argv', ['wrapper', *OPTIONS]), patch.dict(os.environ, env), \
                patch.object(Path, 'is_file', return_value=True), \
                patch.object(wrapper.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                patch.object(wrapper.subprocess, 'check_output', return_value=('[{"Id":"'+IMAGE+'"}]').encode()), \
                patch.object(wrapper.subprocess, 'Popen', return_value=proc), \
                patch.object(wrapper, 'container_absent', return_value=False), \
                patch.object(wrapper, 'stop_owned_source', side_effect=graceful_stop) as stop, \
                patch.object(wrapper.time, 'sleep', side_effect=interrupt), contextlib.redirect_stdout(output):
            self.assertEqual(wrapper.main(), 2)
        stop.assert_called_once()
        self.assertIn('"interrupted": true', output.getvalue())
        self.assertIn('"source_controller_cleanup_verified_by_wrapper": false', output.getvalue())
        self.assertEqual({sig: signal.getsignal(sig) for sig in previous}, previous)

    def test_source_sigterm_uses_existing_keyboard_interrupt_cleanup_path(self):
        with self.assertRaises(KeyboardInterrupt):
            interrupt_source(signal.SIGTERM, None)


if __name__ == '__main__':
    unittest.main()

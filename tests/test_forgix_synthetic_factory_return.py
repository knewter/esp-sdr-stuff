"""Exercise actual factory query admission with the synthetic caller's label."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import forgix_synthetic_backend as backend
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve


class FactoryReturn(unittest.TestCase):
    def run_query(self, folder, label):
        target = preserve.USBTarget('3-3', 1, 2, preserve.FACTORY_PID, '/fixture/usb', 'a' * 64)
        request = folder / 'query.json'
        request.write_text(json.dumps({'label': label, 'lockfd': 17, 'topology': '3-3',
                                       'port': '/fixture/tty', 'target': target.__dict__}))
        def save(store, name, value):
            (store.path / name).write_text(json.dumps(value))
        # Admission/parsing are actual code. Device/lock/signal/storage boundaries
        # use harmless fixtures; no USB, serial or container is opened.
        with patch.object(trial.sys, 'argv', ['trial', '_query', '--request', str(request)]), \
                patch.object(trial, 'private_file', return_value=request), \
                patch('forgix_usb_ram_capture.inherited_operator_lock') as lock, \
                patch.object(trial.signal, 'signal'), \
                patch.object(preserve, 'query_factory', return_value={'fixture': 'factory'}) as query, \
                patch.object(preserve.PrivateStore, 'json', save):
            code = trial.query_worker()
            self.assertEqual(code, 0)
            lock.assert_called_once_with(17, trial.ROOT / '.scratch/esp-demo.lock')
            self.assertEqual(query.call_args.args[3], label)
        self.assertEqual(json.loads((folder / (label + '-query-result.json')).read_text()),
                         {'fixture': 'factory'})
        return target

    def test_actual_synthetic_return_reaches_query_worker_for_both_loader_paths(self):
        for existing in (False, True):
            with self.subTest(existing_loader=existing), tempfile.TemporaryDirectory() as name:
                folder = Path(name)
                store = SimpleNamespace(path=folder)
                loader = SimpleNamespace(store=store, deadline=0)
                b = object.__new__(backend.Backend)
                b.loader = loader if existing else None
                b.environment = {'picotool_executable': 'fixture', 'image_id': 'fixture'}
                b.inspector = SimpleNamespace(deadline=0)
                b.private = folder
                b.profile = {}; b.frozen = {}; b.bus = 1; b.lockfd = 17
                b.owner = SimpleNamespace(runners=[])
                factory = preserve.USBTarget('3-3', 1, 2, preserve.FACTORY_PID, '/fixture/usb', 'a' * 64)
                def bounded(inspector, target, actual_store, label, lockfd, until, runner):
                    self.assertIs(inspector, b.inspector); self.assertEqual(target, factory)
                    self.assertIs(actual_store, store); self.assertEqual(lockfd, 17)
                    self.assertEqual(until, 123); self.assertIs(runner, loader)
                    self.run_query(folder, label)
                with patch.object(b, 'hardware_gate') as gate, \
                        patch.object(backend, 'preserve', SimpleNamespace(PrivateStore=lambda *args: store)), \
                        patch.object(backend, 'SyntheticPicotool', return_value=loader), \
                        patch.object(trial, 'watched_factory', return_value=factory) as watched, \
                        patch.object(backend.runtime, 'check') as dispatch, \
                        patch.object(trial, 'bounded_query', side_effect=bounded) as query:
                    self.assertEqual(b.return_factory(123), {'factory_application_verified': True})
                    gate.assert_called_once_with(123); dispatch.assert_called_once_with(b.environment)
                    watched.assert_called_once_with(b.inspector, 1, 123, loader)
                    self.assertEqual(query.call_args.args[3], 'returned-after-ram')
                self.assertEqual(b.owner.runners, [] if existing else [loader])
                self.assertEqual(loader.deadline, 123)

    def test_old_stream_label_is_rejected_by_actual_worker(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaisesRegex(preserve.PreservationError, 'Internal query label invalid'):
                self.run_query(Path(name), 'returned-after-stream')


if __name__ == '__main__':
    unittest.main()

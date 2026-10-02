"""Controlled episodes must unregister even if BlueZ releases the prior object."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ble_owned_source


class FakeManager:
    def __init__(self, bus):
        self.bus = bus
        self.active = False
        self.registrations = self.removals = 0
    async def call_register_advertisement(self, path, options):
        if self.active:
            raise RuntimeError('prior owned advertisement leaked')
        self.active = True
        self.registrations += 1
    async def call_unregister_advertisement(self, path):
        self.active = False
        self.removals += 1
        self.bus.advertisement.Release()


class FakeProperties:
    def __init__(self, manager):
        self.manager = manager
    async def call_get(self, interface, name):
        values = {'Powered': True, 'ActiveInstances': int(self.manager.active), 'SupportedInstances': 12}
        return argparse.Namespace(value=values[name])


class FakeBus:
    def __init__(self):
        self.manager = FakeManager(self)
        self.properties = FakeProperties(self.manager)
        self.disconnected = False
    async def connect(self):
        return self
    async def introspect(self, *args):
        return None
    def get_proxy_object(self, *args):
        return self
    def get_interface(self, name):
        return self.properties if name == 'org.freedesktop.DBus.Properties' else self.manager
    def export(self, path, advertisement):
        self.advertisement = advertisement
    def disconnect(self):
        self.disconnected = True


class OwnedSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_each_episode_removes_its_own_registration(self):
        bus = FakeBus()
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output=Path(directory) / 'trial', episodes=3, seconds=.001, off_seconds=0, interval_ms=20)
            with patch.object(ble_owned_source, 'MessageBus', return_value=bus):
                status = await ble_owned_source.run(args)
            result = json.loads((args.output / 'results.json').read_text())
        self.assertEqual(status, 0)
        self.assertEqual(bus.manager.registrations, 3)
        self.assertEqual(bus.manager.removals, 3)
        self.assertFalse(bus.manager.active)
        self.assertTrue(bus.disconnected)
        self.assertEqual(result['exact_over_air_emission_count'], None)
        self.assertEqual([entry['active_instances_after'] for entry in result['episodes']], [0, 0, 0])
        self.assertEqual(result['source_script_sha256'], hashlib.sha256(Path(ble_owned_source.__file__).read_bytes()).hexdigest())
        self.assertEqual(result['requested_episodes'], 3)
        self.assertTrue(result['source_bus_disconnected'])

    async def test_early_release_cannot_be_reported_as_a_completed_series(self):
        bus = FakeBus()
        async def release_on_registration(path, options):
            bus.manager.registrations += 1
            bus.advertisement.Release()
        bus.manager.call_register_advertisement = release_on_registration
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output=Path(directory) / 'trial', episodes=3, seconds=.001, off_seconds=0, interval_ms=20)
            with patch.object(ble_owned_source, 'MessageBus', return_value=bus):
                status = await ble_owned_source.run(args)
            result = json.loads((args.output / 'results.json').read_text())
        self.assertEqual(status, 2)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'source_released_before_scheduled_removal')
        self.assertEqual(len(result['episodes']), 1)
        self.assertTrue(result['episodes'][0]['release_observed_before_unregister'])
        self.assertIsNotNone(result['episodes'][0]['release_monotonic_ns'])
        self.assertEqual(bus.manager.removals, 0)
        self.assertTrue(bus.disconnected)
        self.assertIsNone(result['exact_over_air_emission_count'])

    async def test_failed_connect_retains_receipt_without_private_error_text(self):
        class UnavailableBus(FakeBus):
            async def connect(self):
                raise RuntimeError('private-controller-00:11:22:33:44:55')
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output=Path(directory) / 'trial', episodes=1, seconds=.001, off_seconds=0, interval_ms=20)
            with patch.object(ble_owned_source, 'MessageBus', return_value=UnavailableBus()):
                status = await ble_owned_source.run(args)
            text = (args.output / 'results.json').read_text()
            result = json.loads(text)
        self.assertEqual(status, 2)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_kind'], 'RuntimeError')
        self.assertEqual(result['episodes'], [])
        self.assertNotIn('private-controller', text)
        self.assertNotIn('00:11:22:33:44:55', text)


if __name__ == '__main__':
    unittest.main()

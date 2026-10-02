"""Build provenance gates only; no SDK build or device access."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_esp_sdr_uart import SDK, SDK_NIX_SOURCE_HASH, nix_sdk_provenance


class NixSdkProvenance(unittest.TestCase):
    def record(self, **updates):
        return dict(revision=SDK, idf_path='/nix/store/pinned-sdk',
                    source_path='/nix/store/pinned-source',
                    source_hash=SDK_NIX_SOURCE_HASH, **updates)

    def check(self, record, sdk='/nix/store/pinned-sdk', env_updates=None):
        env = {'ESP_SDR_IDF_PROVENANCE': '/nix/store/provenance.json',
               'ESP_SDR_IDF_REVISION': SDK}
        env.update(env_updates or {})
        with patch.dict(os.environ, env, clear=True), patch.object(Path, 'read_text', return_value=json.dumps(record)):
            return nix_sdk_provenance(Path(sdk))

    def test_exact_pin_accepts_immutable_sdk(self):
        record = self.record()
        self.assertEqual(self.check(record), record)

    def test_missing_nix_metadata_retains_git_checkout_route(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(nix_sdk_provenance(Path('/some/git/sdk')))

    def test_wrong_revision_hash_or_sdk_path_refuses_build(self):
        for key, value in [('revision', 'another-sdk'), ('source_hash', 'wrong-hash'),
                           ('idf_path', '/nix/store/another-sdk')]:
            record = self.record()
            record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(record)

    def test_mutable_or_escaping_source_path_refuses_build(self):
        for source in ['/tmp/source', '/nix/store/../../tmp/source']:
            record = self.record()
            record['source_path'] = source
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.check(record)
        with self.assertRaises(ValueError):
            self.check(self.record(), sdk='/tmp/sdk')

    def test_mutable_provenance_or_wrong_shell_refuses_build(self):
        for env in [{'ESP_SDR_IDF_PROVENANCE': '/tmp/provenance.json'},
                    {'ESP_SDR_IDF_REVISION': 'another-sdk'}]:
            with self.subTest(env=env), self.assertRaises(ValueError):
                self.check(self.record(), env_updates=env)


if __name__ == '__main__':
    unittest.main()

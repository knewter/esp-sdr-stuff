"""DC-order regression with the independent published SIG packet modulator."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'tools'),
                str(Path(__file__).resolve().parent)]
from ble_dc_first_replay import decode_dc_first
from ble_decode_iq import decode_iq
from test_ble_decode_iq import independent_vector_iq


class DCFirstTests(unittest.TestCase):
    def test_independent_sig_packet_with_large_raw_offset_and_translation(self):
        iq = independent_vector_iq(cfo=1000000, noise=.03) + 32 - 16j
        saved = iq.copy()
        original = decode_iq(iq, 16000000, 38, frequency_translation_hz=-1000000,
                             refine=True)
        corrected = decode_dc_first(iq, 16000000, 38,
                                    frequency_translation_hz=-1000000, refine=True)
        self.assertFalse(any(f['status'].startswith('valid') for f in original))
        valid = [f for f in corrected if f['status'].startswith('valid')]
        self.assertTrue(valid)
        self.assertTrue(all(f['status'] == 'valid_other_redacted' and f['crc24_ok']
                            and f['pdu_sha256'] is None for f in valid))
        np.testing.assert_array_equal(iq, saved)

    def test_no_translation_preserves_independent_vector(self):
        iq = independent_vector_iq(noise=.03) + 16 + 7j
        frames = decode_dc_first(iq, 16000000, 38, refine=True)
        self.assertTrue(any(f['status'] == 'valid_other_redacted' for f in frames))

    def test_offset_only_is_not_a_packet(self):
        frames = decode_dc_first(np.full(16380, 32-16j), 16000000, 38,
                                 frequency_translation_hz=-1000000, refine=True)
        self.assertFalse(any(f['status'].startswith('valid') for f in frames))

    def test_truncated_independent_packet_stays_unverified(self):
        iq = independent_vector_iq(cfo=1000000, noise=.03)[:2000] + 32-16j
        frames = decode_dc_first(iq, 16000000, 38,
                                 frequency_translation_hz=-1000000, refine=True)
        self.assertFalse(any(f['status'].startswith('valid') for f in frames))

    def test_invalid_input_refused(self):
        for iq in (np.array([]), np.zeros((2, 2)), np.array([complex('nan')])):
            with self.assertRaises(ValueError):
                decode_dc_first(iq, 16000000, 38)


if __name__ == '__main__':
    unittest.main()

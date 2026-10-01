"""Independent Bluetooth SIG vector and bounded IQ decoder checks.

Vector: Core 6.3, Vol 6 Part C section 4.2.1 ADV_NONCONN_IND.
Bit strings are chronological, not conventional big-endian hex notation.
"""
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ble_decode_iq import bits_of, bytes_of, crc_bits, whiten, decode_packet, decode_iq

PDU = '01000010 10010000 01100101 10100101 00100101 11000101 01000101 10000011 10000000 01000000 11000000'
CRC = '10110101 00101101 11010111'
WHITENED = '00101001 00110011 01000111 10100001 10111111 10111110 11000010 01110010 01011000 11100101 00110101 11110111 11110011 10100101'
PREAMBLE_ACCESS = '01010101 01101011 01111101 10010001 01110001'


def bitstring(value):
    return np.array([int(bit) for bit in value.replace(' ', '')], dtype=np.uint8)


def independent_vector_iq(rate=16000000, cfo=0, conjugate=False, noise=0):
    # This test modulator uses the published complete packet, not decoder CRC
    # or whitening routines. It is synthetic proof, never RF evidence.
    samples = rate // 1000000
    bits = bitstring(PREAMBLE_ACCESS + ' ' + WHITENED)
    nrz = np.repeat(bits.astype(float) * 2 - 1, samples)
    shaped = gaussian_filter1d(nrz, np.sqrt(np.log(2)) / (2 * np.pi * .5) * samples)
    phase = 2 * np.pi * np.cumsum(shaped * 250000 + cfo) / rate
    packet = np.exp(1j * phase)
    iq = np.zeros(16380, dtype=complex)
    offset = 64 * samples + 3
    iq[offset:offset + len(packet)] = packet
    if conjugate:
        iq = iq.conj()
    random = np.random.default_rng(71)
    return iq + noise * (random.normal(size=iq.size) + 1j * random.normal(size=iq.size))


class BLEDecoderTests(unittest.TestCase):
    def test_sig_crc_vector(self):
        np.testing.assert_array_equal(crc_bits(bitstring(PDU)), bitstring(CRC))

    def test_sig_whitening_vector(self):
        np.testing.assert_array_equal(whiten(bitstring(PDU + ' ' + CRC), 38), bitstring(WHITENED))
        np.testing.assert_array_equal(whiten(bitstring(WHITENED), 38), bitstring(PDU + ' ' + CRC))

    def test_sig_packet_redacts_other_payload(self):
        result = decode_packet(bitstring(WHITENED), 38)
        self.assertEqual(result['status'], 'valid_other_redacted')
        self.assertTrue(result['crc24_ok'])
        self.assertIsNone(result['pdu_sha256'])
        self.assertNotIn('payload', result)
        self.assertEqual(result['packet_duration_us'], 152)

    def test_corrupt_and_truncated_packets(self):
        bits = bitstring(WHITENED)
        corrupt = bits.copy(); corrupt[40] ^= 1
        self.assertEqual(decode_packet(corrupt, 38)['status'], 'crc_failed')
        self.assertEqual(decode_packet(bits[:-1], 38)['status'], 'truncated_packet')
        self.assertEqual(decode_packet(bits[:8], 38)['status'], 'truncated_header')
        self.assertFalse(decode_packet(bits, 37)['status'].startswith('valid'))

    def test_exact_ad_structure_matching(self):
        # Additional generated owned packet tests check policy, not independent
        # protocol conformance (the independent vector above supplies that).
        marker = bytes.fromhex('0fffffff4553502d5344522d4556414c')
        body = bytes(6) + marker
        pdu = bits_of(bytes([2, len(body)]) + body)
        result = decode_packet(whiten(np.r_[pdu, crc_bits(pdu)], 37), 37)
        self.assertEqual(result['status'], 'valid_owned')
        result = decode_packet(whiten(np.r_[pdu, crc_bits(pdu)], 37), 37, marker[1:])
        self.assertEqual(result['status'], 'valid_other_redacted')

    def test_sig_vector_modulated_iq_offsets_polarity_and_noise(self):
        for cfo, conjugate, noise in [(0, False, 0), (120000, False, .02), (-100000, True, .02)]:
            with self.subTest(cfo=cfo, conjugate=conjugate):
                result = decode_iq(independent_vector_iq(cfo=cfo, conjugate=conjugate, noise=noise), 16000000, 38)
                valid = [frame for frame in result if frame['status'] == 'valid_other_redacted']
                self.assertEqual(len(valid), 1)
                self.assertEqual(valid[0]['pdu_length'], 9)

    def test_noise_yields_no_valid_payload(self):
        rng = np.random.default_rng(17)
        iq = rng.normal(size=16380) + 1j * rng.normal(size=16380)
        self.assertFalse(any(frame['status'].startswith('valid') for frame in decode_iq(iq, 16000000, 37)))


if __name__ == '__main__':
    unittest.main()

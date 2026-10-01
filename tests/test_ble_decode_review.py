"""Independent wire-vector, marker-policy and duplicate-slicing checks.

The register representation and fixtures do not use decoder CRC/whitening.
These synthetic checks are separate from private physical-IQ review.
"""
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ble_decode_iq as decoder

MARKER = bytes.fromhex("0fffffff4553502d5344522d4556414c")
SIG_PDU = "01000010 10010000 01100101 10100101 00100101 11000101 01000101 10000011 10000000 01000000 11000000"
SIG_CRC = "10110101 00101101 11010111"
SIG_WHITENED = "00101001 00110011 01000111 10100001 10111111 10111110 11000010 01110010 01011000 11100101 00110101 11110111 11110011 10100101"


def wire_bits(data):
    return [(byte >> bit) & 1 for byte in data for bit in range(8)]


def reflected_crc(bits):
    # Reflected register: initial bit-reversal of0x555555; right shifts.
    state = 0xAAAAAA
    for bit in bits:
        feedback = (state & 1) ^ bit
        state >>= 1
        if feedback:
            state ^= 0xDA6000
    return [(state >> bit) & 1 for bit in range(24)]


def register_whitening(bits, channel):
    state = channel | 0x40
    result = []
    for bit in bits:
        whitening_bit = state & 1
        result.append(bit ^ whitening_bit)
        if whitening_bit:
            state ^= 0x88
        state >>= 1
    return result


def owned_wire(advertising=MARKER, channel=37):
    body = bytes(6) + advertising  # Synthetic address only.
    pdu = wire_bits(bytes([2, len(body)]) + body)
    return register_whitening(pdu + reflected_crc(pdu), channel)


def modulate_packets(offsets_us, advertising=MARKER):
    rate = 16_000_000
    samples_per_bit = 16
    bits = wire_bits(bytes.fromhex("aad6be898e")) + owned_wire(advertising)
    symbols = np.repeat(np.asarray(bits) * 2.0 - 1.0, samples_per_bit)
    symbols = gaussian_filter1d(symbols, np.sqrt(np.log(2)) / np.pi * samples_per_bit)
    phase = 2 * np.pi * np.cumsum(symbols * 250_000 + 1_000_000) / rate
    packet = np.exp(1j * phase)
    iq = np.zeros(16380, dtype=complex)
    for offset_us in offsets_us:
        start = int(offset_us * samples_per_bit) + 3
        iq[start:start + len(packet)] += packet
    return iq


class IndependentBLEReview(unittest.TestCase):
    def test_reflected_crc_and_whitening_match_independent_sig_vector(self):
        pdu = [int(bit) for bit in SIG_PDU.replace(" ", "")]
        crc = reflected_crc(pdu)
        self.assertEqual("".join(map(str, crc)), SIG_CRC.replace(" ", ""))
        self.assertEqual("".join(map(str, register_whitening(pdu + crc, 38))), SIG_WHITENED.replace(" ", ""))

    def test_independently_generated_owned_wire_decodes(self):
        result = decoder.decode_packet(owned_wire(), 37, MARKER)
        self.assertEqual(result["status"], "valid_owned")
        self.assertEqual(result["packet_duration_us"], 256)

    def test_known_marker_never_repairs_different_valid_payload(self):
        other = bytearray(MARKER)
        other[-1] ^= 1
        result = decoder.decode_packet(owned_wire(bytes(other)), 37, MARKER)
        self.assertEqual(result["status"], "valid_other_redacted")
        self.assertFalse(result["owned_manufacturer_ad_exact_match"])
        self.assertIsNone(result["pdu_sha256"])

    def test_exact_marker_inside_another_ad_item_does_not_match(self):
        other_ad = bytes([len(MARKER) + 1, 9]) + MARKER
        result = decoder.decode_packet(owned_wire(other_ad), 37, MARKER)
        self.assertEqual(result["status"], "valid_other_redacted")

    def test_corruption_is_rejected_despite_correct_known_marker(self):
        bits = owned_wire()
        bits[32] ^= 1
        self.assertEqual(decoder.decode_packet(bits, 37, MARKER)["status"], "crc_failed")

    def test_many_slicer_timings_do_not_duplicate_one_packet(self):
        frames = decoder.decode_iq(modulate_packets([200]), 16_000_000, 37, MARKER)
        owned = [frame for frame in frames if frame["status"] == "valid_owned"]
        self.assertEqual(len(owned), 1)

    def test_repeated_payload_at_two_distinct_positions_counts_two_packets(self):
        frames = decoder.decode_iq(modulate_packets([150, 600]), 16_000_000, 37, MARKER)
        owned = [frame for frame in frames if frame["status"] == "valid_owned"]
        self.assertEqual(len(owned), 2)
        self.assertEqual(owned[0]["pdu_sha256"], owned[1]["pdu_sha256"])


if __name__ == "__main__":
    unittest.main()

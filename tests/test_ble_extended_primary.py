"""Spec-field fixtures and independent reflected-CRC/register-whitening wires.

Synthetic AdvA from an explicit fixture, never a connected device address.
Crypto construction is independent of production left-shift CRC/whitening.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import ble_decode_iq as legacy
import ble_extended_primary as primary
from test_ble_decode_review import reflected_crc, register_whitening, wire_bits, SIG_PDU, SIG_CRC, SIG_WHITENED

ADDRESS = bytes.fromhex('a6a5a4a3a2a1')
REFERENCE = {'schema': 1, 'address_type': 0, 'advertising_sid': 0,
             'adva_lsb_first_hex': ADDRESS.hex()}
# Core5.4 Table2.4 no-AUX: ExtHeaderLength7, flagsAdvA1, six-byte AdvA.
NO_AUX = bytes.fromhex('07080701')+ADDRESS
# Core5.4 Table2.4 with-AUX: AdvA+ADI+AuxPtr, SID0/DID0x123;
# channel5,30usunits,offset20 (600us), auxiliaryLE1M encoding0.
WITH_AUX = bytes.fromhex('070d0c19')+ADDRESS+bytes.fromhex('2301051400')


def wire(pdu):
    bits = wire_bits(pdu)
    return register_whitening(bits+reflected_crc(bits), 37)


def modulate(pdu, positions=(200,), rate=16000000):
    samples_per_symbol = rate//1000000
    bits = wire_bits(bytes.fromhex('aad6be898e'))+wire(pdu)
    symbols = np.repeat(np.array(bits)*2.0-1, samples_per_symbol)
    symbols = gaussian_filter1d(symbols, np.sqrt(np.log(2))/np.pi*samples_per_symbol)
    packet = np.exp(2j*np.pi*np.cumsum(symbols*250000+1000000)/rate)
    iq = np.zeros(16380, dtype=complex)
    for microseconds in positions:
        offset = int(microseconds*samples_per_symbol)+3
        count = min(len(packet), len(iq)-offset)
        if count > 0:
            iq[offset:offset+count] += packet[:count]
    return iq


class ExtendedPrimaryTests(unittest.TestCase):
    def decode(self, pdu):
        return primary.decode_primary(wire(pdu), 37, REFERENCE)

    def test_independent_wire_generator_matches_published_sig_crypto_vector(self):
        bits = [int(bit) for bit in SIG_PDU.replace(' ', '')]
        crc = reflected_crc(bits)
        self.assertEqual(''.join(map(str, crc)), SIG_CRC.replace(' ', ''))
        self.assertEqual(''.join(map(str, register_whitening(bits+crc, 38))), SIG_WHITENED.replace(' ', ''))

    def test_no_aux_144us_full_owned_primary(self):
        frame = self.decode(NO_AUX)
        self.assertEqual(frame['status'], 'valid_owned_primary')
        self.assertEqual(frame['packet_duration_us'], 144)
        self.assertEqual(frame['pdu_length'], 8)
        self.assertTrue(frame['owned_public_adva_exact_match'])
        self.assertFalse(frame['aux_pointer_present'])
        self.assertNotIn('owned_manufacturer_ad_exact_match', frame)
        self.assertNotIn(ADDRESS.hex(), json.dumps(frame))

    def test_with_aux_184us_still_requires_exact_owned_primary_address(self):
        frame = self.decode(WITH_AUX)
        self.assertEqual(frame['status'], 'valid_owned_primary')
        self.assertEqual(frame['packet_duration_us'], 184)
        self.assertTrue(frame['aux_pointer_present'])
        self.assertTrue(frame['adi_present'])
        self.assertNotIn('2301', json.dumps(frame))

    def test_controller_optional_txpower_in_both_formats(self):
        for pdu in [bytes.fromhex('07090841')+ADDRESS+b'\xf8',
                    bytes.fromhex('070e0d59')+ADDRESS+bytes.fromhex('2301051400f8')]:
            result = self.decode(pdu)
            self.assertEqual(result['status'], 'valid_owned_primary')
            self.assertTrue(result['tx_power_present'])

    def test_absent_address_and_adi_only_never_establish_ownership(self):
        # Legal with-AUX header without AdvA: flagsADI+AuxPtr only.
        pdu = bytes.fromhex('070706182301051400')
        result = self.decode(pdu)
        self.assertEqual(result['status'], 'valid_other_primary_redacted')
        self.assertFalse(result['adva_present'])
        self.assertIsNone(result['pdu_sha256'])
        # TxAdd is RFU when no AdvA is present.
        self.assertFalse(self.decode(bytes([0x47])+pdu[1:])['status'].startswith('valid'))
        # ADI without AuxPtr is excluded by Table2.4.
        self.assertFalse(self.decode(bytes.fromhex('070403082301'))['status'].startswith('valid'))

    def test_different_valid_address_not_repaired_or_disclosed(self):
        pdu = bytearray(NO_AUX);pdu[-1] ^= 1
        result = self.decode(bytes(pdu))
        self.assertEqual(result['status'], 'valid_other_primary_redacted')
        self.assertIsNone(result['pdu_sha256'])
        self.assertNotIn(bytes(pdu[4:]).hex(), json.dumps(result))

    def test_random_address_type_and_wrong_sid_not_owned(self):
        pdu = bytearray(NO_AUX);pdu[0] |= 0x40
        self.assertEqual(self.decode(bytes(pdu))['status'], 'valid_other_primary_redacted')
        pdu = bytearray(WITH_AUX);pdu[11] |= 0x10
        self.assertEqual(self.decode(bytes(pdu))['status'], 'valid_other_primary_redacted')

    def test_crc_corruption_and_packet_truncation_never_pass(self):
        bits = wire(NO_AUX);bits[32] ^= 1
        self.assertEqual(primary.decode_primary(bits, 37, REFERENCE)['status'], 'crc_failed')
        for size in [0, 15, len(bits)-1]:
            self.assertFalse(primary.decode_primary(wire(NO_AUX)[:size], 37, REFERENCE)['status'].startswith('valid'))

    def test_reserved_flags_fields_modes_and_header_bits_rejected(self):
        for index, bit in [(0, 0x10), (0, 0x20), (0, 0x80), (2, 0x40), (2, 0x80),
                           (2, 0xc0), (3, 0x02), (3, 0x04), (3, 0x20), (3, 0x80)]:
            pdu = bytearray(NO_AUX);pdu[index] |= bit
            with self.subTest(index=index, bit=bit):
                self.assertFalse(self.decode(bytes(pdu))['status'].startswith('valid'))

    def test_all_length_and_field_bounds_are_strict(self):
        for payload in [b'\x00', bytes.fromhex('0601')+ADDRESS,
                        bytes.fromhex('0801')+ADDRESS+b'\x00',
                        bytes.fromhex('0701')+ADDRESS+b'\x00',
                        bytes.fromhex('0801')+ADDRESS+b'\x01']:
            self.assertFalse(self.decode(bytes([7,len(payload)])+payload)['status'].startswith('valid'))
        # Full8-bit PDU length must not be masked to6 bits.
        pdu = bytes([7,72])+NO_AUX[2:]+bytes(64)
        self.assertFalse(self.decode(pdu)['status'].startswith('valid'))

    def test_aux_data_marker_and_acad_cannot_substitute_ownership(self):
        marker = legacy.MARKER_AD
        for extra in [marker, b'\x00'+marker]:
            pdu = NO_AUX+extra
            pdu = bytes([7,len(pdu)-2])+pdu[2:]
            self.assertFalse(self.decode(pdu)['status'].startswith('valid'))

    def test_aux_channel_and_phy_bounds_and_field_pairing(self):
        for channel in [37,38,39,63]:
            pdu=bytearray(WITH_AUX);pdu[12]=channel
            self.assertFalse(self.decode(bytes(pdu))['status'].startswith('valid'))
        for phy in range(1,8):
            pdu=bytearray(WITH_AUX);pdu[14]=phy<<5
            self.assertFalse(self.decode(bytes(pdu))['status'].startswith('valid'))
        # A zero-offset AuxPtr is permitted (§2.3.4.5); not proof AUX airs.
        pdu=bytearray(WITH_AUX);pdu[13]=0
        self.assertEqual(self.decode(bytes(pdu))['status'], 'valid_owned_primary')
        for flag in [0x09,0x11]:
            pdu=bytearray(WITH_AUX);pdu[3]=flag
            self.assertFalse(self.decode(bytes(pdu))['status'].startswith('valid'))

    def test_crc_valid_aux_offset_timing_and_units_boundaries(self):
        # Independent CRC/whitening is regenerated after every mutation:
        # malformed timing is rejected semantically, not by CRC failure.
        # LE1M packet184us+T_MAFS300us needs at least484us.
        for units, offset, valid in [(30,1,False),(30,16,False),(30,17,True),
                                     (300,20,False),(300,818,False),
                                     (300,819,True),(30,8191,True),
                                     (30,0,True),(300,0,False)]:
            pdu=bytearray(WITH_AUX)
            pdu[12]=5 | (0x80 if units==300 else 0)
            pdu[13]=offset & 255;pdu[14]=offset >> 8
            with self.subTest(units=units,offset=offset):
                result=self.decode(bytes(pdu))
                self.assertTrue(result['crc24_ok'])
                self.assertEqual(result['status'], 'valid_owned_primary' if valid
                                 else 'invalid_aux_pointer_timing')
        # Duration is derived from this complete PDU, not a fixed184us:
        # omit AdvA ->136us, so450us is permitted while420us is too short.
        for offset, valid in [(14,False),(15,True)]:
            pdu=bytes.fromhex('07070618230105')+bytes([offset,0])
            result=self.decode(pdu)
            self.assertEqual(result['status'], 'valid_other_primary_redacted' if valid
                             else 'invalid_aux_pointer_timing')

    def test_private_reference_validation_mode_and_channel(self):
        for bad in [dict(REFERENCE,address_type=1),dict(REFERENCE,advertising_sid=1),
                    dict(REFERENCE,schema=True),dict(REFERENCE,adva_lsb_first_hex='00'*6),
                    dict(REFERENCE,adva_lsb_first_hex='ff'*6),dict(REFERENCE,adva_lsb_first_hex='bad')]:
            with self.assertRaises(ValueError):primary.validate_reference(bad)
        with self.assertRaises(ValueError):primary.decode_primary(wire(NO_AUX),38,REFERENCE)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'reference.json';path.write_text(json.dumps(REFERENCE));path.chmod(0o644)
            with self.assertRaises(ValueError):primary.load_reference(path)
            path.chmod(0o600)
            self.assertEqual(primary.load_reference(path), REFERENCE)

    def test_owned_primary_blind_iq_fit_and_no_legacy_global_mutation(self):
        old_parser=legacy.decode_packet
        for rate in [16000000,40000000,80000000]:
            positions=(200,) if rate==16000000 else (20,)
            result=primary.decode_primary_iq(modulate(NO_AUX,positions,rate),REFERENCE,rate)
            owned=[f for f in result if f['status']=='valid_owned_primary']
            self.assertEqual(len(owned),1)
            self.assertTrue(owned[0]['complete_preamble_and_pdu_crc_within_capture_nominal'])
            self.assertEqual(owned[0]['samples_per_symbol_at_4msps'],4.0)
        self.assertIs(legacy.decode_packet,old_parser)
        self.assertEqual(legacy.decode_packet(wire(NO_AUX),37)['status'],'unsupported_or_invalid_header')

    def test_duplicate_timings_and_distinct_packets_are_diagnostics_not_events(self):
        for positions, count in [((200,),1),((150,600),2)]:
            frames=primary.decode_primary_iq(modulate(NO_AUX,positions),REFERENCE)
            owned=[f for f in frames if f['status']=='valid_owned_primary']
            self.assertEqual(len(owned),count)
            self.assertTrue(all(f['complete_preamble_and_pdu_crc_within_capture_nominal'] for f in owned))
        # Two clusters in a1.024ms window are possible synthetically, but the
        #20ms source profile cannot attribute them as two source events.

    def test_refined_receiver_is_blind_bounded_and_keeps_full_window(self):
        iq=modulate(NO_AUX)
        iq*=np.exp(-2j*np.pi*1000000*np.arange(len(iq))/16000000)
        base=resample_poly(iq-iq.mean(),1,4)
        phase=np.angle(base[1:]*np.conj(base[:-1]))
        receiver=primary.make_receiver(REFERENCE)
        refine=receiver.__globals__['refine_packet']
        frame=refine(phase,(200*16+3+128)/4,4,37,b'')
        self.assertEqual(frame['status'],'valid_owned_primary')
        self.assertTrue(frame['complete_preamble_and_pdu_crc_within_capture_nominal'])
        self.assertLessEqual(frame['receiver_hypotheses_checked'],13*17*37)
        self.assertTrue(3.97<=frame['samples_per_symbol_at_4msps']<=4.03)
        wrong=dict(REFERENCE,adva_lsb_first_hex='a6a5a4a3a2a0')
        other_refine=primary.make_receiver(wrong).__globals__['refine_packet']
        other=other_refine(phase,(200*16+3+128)/4,4,37,b'')
        self.assertEqual(other['status'],'valid_other_primary_redacted')
        # Private ownership cannot change the AA-trained hypothesis selection.
        for key in ['samples_per_symbol_at_4msps','threshold_bias_deviation_fraction',
                    'access_address_sample_offset','access_correlation']:
            self.assertEqual(frame[key],other[key])

    def test_nonfinite_translation_and_cli_redaction_fresh_output(self):
        for frequency in [float('nan'),float('inf'),float('-inf'),8000000]:
            with self.assertRaises(ValueError):
                primary.decode_primary_iq(modulate(NO_AUX),REFERENCE,frequency_translation_hz=frequency)
        from contextlib import redirect_stdout,redirect_stderr
        import io
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);reference=directory/'reference.json'
            reference.write_text(json.dumps(REFERENCE));reference.chmod(0o600)
            iq=directory/'iq-000000.bin';iq.write_bytes(bytes(32760))
            output=directory/'decode.json'
            args=['--input',str(iq),'--output',str(output),'--owned-reference',str(reference)]
            with redirect_stdout(io.StringIO()):primary.main(args)
            result=json.loads(output.read_text())
            self.assertEqual(result['captures_analyzed'],1)
            self.assertEqual(result['crc_valid_owned_primary_candidates'],0)
            self.assertFalse(result['captures'][0]['source_event_attribution_ambiguous'])
            self.assertEqual(result['receiver_source_sha256'],primary.LEGACY_SHA256)
            self.assertNotIn(ADDRESS.hex(),output.read_text())
            self.assertNotIn(str(reference),output.read_text())
            with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):primary.main(args)

    def test_edge_packet_not_claimed_complete(self):
        frames=primary.decode_primary_iq(modulate(NO_AUX,(950,)),REFERENCE)
        self.assertFalse(any(f['status']=='valid_owned_primary' and
            f['complete_preamble_and_pdu_crc_within_capture_nominal'] for f in frames))


if __name__=='__main__':unittest.main()

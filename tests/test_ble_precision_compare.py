"""Digital-only diagnostic: exhaustive upper bits and independent wire fixtures."""
import json
import hashlib
from pathlib import Path
import sys
import unittest
import zlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ble_precision_compare import upper8,independent_components,independent_packet,classify,verify_row,SAMPLES
from ble_decode_iq import decode_iq
from test_ble_decode_iq import independent_vector_iq

def pack(values):
    # Literal bit-stream encoder does not call either production packing path.
    bits=[(int(value)&1023)>>k&1 for value in values for k in range(10)]
    assert len(bits)%8==0
    return bytes(sum(bit<<k for k,bit in enumerate(bits[i:i+8])) for i in range(0,len(bits),8))

class Precision(unittest.TestCase):
    def test_exhaustive_signed_1024_values_and_unsigned_firmware_bits(self):
        values=np.arange(-512,512,dtype=np.int16);raw=pack(values)
        result=upper8(raw,512)
        self.assertEqual(result,bytes(((int(v)&1023)>>2) for v in values))
        np.testing.assert_array_equal(np.frombuffer(result,dtype=np.int8),values>>2)
        np.testing.assert_array_equal(independent_components(raw),values)

    def test_asymmetric_LE40_literal_and_independent_random_groups(self):
        raw=pack([-512,511,-1,1]);self.assertEqual(raw.hex(),'00fef77f00')
        self.assertEqual(upper8(raw,2),bytes.fromhex('807fff00'))
        rng=np.random.default_rng(47);values=rng.integers(-512,512,4000,dtype=np.int16)
        self.assertEqual(upper8(pack(values),2000),bytes((int(v)>>2)&255 for v in values))

    def test_no_mean_removal_rounding_or_saturation_before_conversion(self):
        values=[-5,-4,-3,-1,0,1,3,4,5,7,8,511]
        self.assertEqual(upper8(pack(values),6),bytes.fromhex('feffffff000000010101027f'))

    def test_invalid_length_sample_or_groups_rejected(self):
        for raw,n in [(b'',2),(bytes(4),2),(bytes(5),1),(bytes(5),True),(bytes(5),0)]:
            with self.subTest(n=n),self.assertRaises(ValueError):upper8(raw,n)
        with self.assertRaises(ValueError):independent_components(bytes(4))

    def test_independent_SIG_waveform_CRC_and_whitening_both_precisions(self):
        iq=independent_vector_iq(cfo=120000,noise=.02)*180
        values=np.column_stack((np.rint(iq.real),np.rint(iq.imag))).reshape(-1).astype(int)
        raw=pack(values)
        for bits,payload,scale in [(10,raw,1),(8,upper8(raw,SAMPLES),4)]:
            components=independent_components(payload) if bits==10 else np.frombuffer(payload,dtype=np.int8)
            measured=components[::2]+1j*components[1::2]
            frames=decode_iq(measured,16000000,38,refine=True)
            frame=next(f for f in frames if f['status']=='valid_other_redacted')
            proof=independent_packet(payload,bits,0,frame,channel=38)
            self.assertTrue(proof['crc24_ok']);self.assertTrue(proof['complete_preamble_and_pdu_crc_within_capture_nominal'])
            self.assertFalse(proof['owned_manufacturer_ad_exact_match']);self.assertIsNone(proof['pdu_sha256'])
            self.assertEqual((proof['pdu_type'],proof['pdu_length']),(2,9))

    def test_complete_windows_cluster_dedup_and_conflicts(self):
        p={'status':'valid_owned','crc24_ok':True,'owned_manufacturer_ad_exact_match':True,
           'pdu_sha256':'a'*64,'packet_duration_us':256,'access_address_sample_offset':1000,
           'access_correlation':.9}
        self.assertEqual(len(classify([p,{**p,'access_address_sample_offset':1020}])['full_owned_packets']),1)
        self.assertTrue(classify([p,{**p,'access_address_sample_offset':3000}])['owned_cluster_conflict'])
        self.assertTrue(classify([p,{**p,'pdu_sha256':'b'*64}])['owned_cluster_conflict'])
        self.assertEqual(classify([{**p,'access_address_sample_offset':100}])['full_owned_packets'],[])
        self.assertEqual(classify([{**p,'access_address_sample_offset':16000}])['full_owned_packets'],[])
        with self.assertRaises(ValueError):classify([{**p,'crc24_ok':False}])
        with self.assertRaises(ValueError):classify([{**p,'refined':True,'samples_per_symbol_at_4msps':float('nan')}])

    def test_transport_binding_hash_failures_and_invalid_row_retained(self):
        raw=bytes(SAMPLES*5//2);digest=hashlib.sha256(raw).hexdigest();crc=f'{zlib.crc32(raw):08x}'
        entry={'bytes':len(raw),'sha256':digest}
        row={'private_payload_sha256':digest,'returned_samples':str(SAMPLES),
             'crc_ok':'True','sample_count_ok':'True','actual_crc32':crc,'expected_crc32':crc}
        self.assertEqual(verify_row(raw,row,entry),(True,crc))
        self.assertFalse(verify_row(raw,{**row,'expected_crc32':'00000000'},entry)[0])
        with self.assertRaises(ValueError):verify_row(raw+b'X',row,entry)
        with self.assertRaises(ValueError):verify_row(raw,{**row,'private_payload_sha256':'0'*64},entry)

if __name__=='__main__':unittest.main()

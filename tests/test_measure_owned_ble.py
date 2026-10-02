"""Synthetic complete wire responses verify receiver formats; no device access."""
import contextlib
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import measure_owned_ble as receiver


class SyntheticWire:
    def __init__(self,bits,samples=16380,corrupt_crc=False):
        if bits==8:
            self.payload=b'\x7f\x80'*samples
        else:
            word=511|(512<<10)
            self.payload=(word|(word<<20)).to_bytes(5,'little')*(samples//2)
            if samples%2:self.payload+=word.to_bytes(3,'little')
        self.buffer=bytearray(self.payload)
        self.samples=samples
        self.crc=zlib.crc32(self.payload)^(1 if corrupt_crc else 0)
        self.requests=[];self.closed=False
    def write(self,request):self.requests.append(request.decode().strip())
    def flush(self):pass
    def read_until(self,*args):
        return (f'DATA {self.samples} {self.crc:08x} 1030\n' if self.requests[-1].startswith('CAP') else 'OK\n').encode()
    def read(self,count):
        chunk=bytes(self.buffer[:count]);del self.buffer[:count];return chunk
    def close(self):self.closed=True


class ReceiverFormats(unittest.TestCase):
    def trial(self,bits=8,explicit_bits=False,samples=16380,corrupt_crc=False):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);wire=SyntheticWire(bits,samples,corrupt_crc)
        args=['--output',str(root/'metadata'),'--private',str(root/'.scratch/iq'),'--seconds','1',
              '--frequency','2401','--bandwidth','20' if bits==10 else '12','--gain','48' if bits==10 else 'hardware']
        if explicit_bits:args+=['--bits',str(bits)]
        clock=iter([0,0,10,20,30,2_000_000_000])
        with patch.object(receiver,'open_board',return_value=wire),patch.object(receiver,'synchronize'), \
             patch.object(receiver,'queries',return_value={'INFO':'synthetic'}), \
             patch.object(receiver,'settings',return_value={'synthetic':'OK'}) as configure, \
             patch.object(receiver.time,'monotonic_ns',side_effect=lambda:next(clock)), \
             contextlib.redirect_stdout(io.StringIO()):
            receiver.main(args)
        self.assertTrue(wire.closed)
        self.assertEqual(wire.requests[-1],'RELEASE')
        record=json.loads((root/'metadata/manifest.json').read_text())
        with (root/'metadata/captures.csv').open(newline='') as stream:row=list(csv.DictReader(stream))[0]
        payload=(root/'.scratch/iq/iq-0000.bin').read_bytes()
        return wire,record,row,payload,configure

    def test_default_eight_bit_path_keeps_wire_format_and_statistics(self):
        wire,record,row,payload,configure=self.trial()
        self.assertEqual(wire.requests[0],'CAP16 16380 6')
        self.assertEqual(record['bits_per_component'],8)
        self.assertEqual(record['integrity_failures'],0)
        self.assertEqual(len(payload),32760)
        self.assertEqual((float(row['mean_i']),float(row['mean_q'])),(127,-128))
        configure.assert_called_once_with(wire,2401,12,'hardware')

    def test_ten_bit_path_uses_packed_wire_size_and_ten_bit_statistics(self):
        wire,record,row,payload,configure=self.trial(bits=10,explicit_bits=True)
        self.assertEqual(wire.requests[0],'CAP20 16380 6')
        self.assertEqual(record['bits_per_component'],10)
        self.assertEqual(record['integrity_failures'],0)
        self.assertEqual(len(payload),40950)
        self.assertEqual((float(row['mean_i']),float(row['mean_q'])),(511,-512))
        self.assertEqual(float(row['component_endpoint_fraction']),1)
        self.assertEqual(row['actual_crc32'],row['expected_crc32'])
        configure.assert_called_once_with(wire,2401,20,'48')

    def test_ten_bit_bad_crc_is_retained_as_integrity_failure(self):
        _,record,row,payload,_=self.trial(bits=10,explicit_bits=True,corrupt_crc=True)
        self.assertEqual(record['integrity_failures'],1)
        self.assertEqual(row['crc_and_count_valid'],'False')
        self.assertNotIn('mean_i',row)
        self.assertEqual(len(payload),40950)

    def test_ten_bit_wrong_sample_count_is_retained_and_rejected(self):
        _,record,row,payload,_=self.trial(bits=10,explicit_bits=True,samples=16378)
        self.assertEqual(record['integrity_failures'],1)
        self.assertEqual(row['crc_ok'],'True')
        self.assertEqual(row['sample_count_ok'],'False')
        self.assertEqual(len(payload),40945)


if __name__=='__main__':unittest.main()

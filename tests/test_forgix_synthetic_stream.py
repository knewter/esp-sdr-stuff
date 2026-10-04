"""Host/control checks against literal packets and frozen real C engine output."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from forgix_synthetic_stream import Binding, Control, Validator, StreamError, CONTRACT_SHA256
from forgix_synthetic_codec import Batch, SourceRecord, CodecError

B=Binding(bytes(range(1,17)),2_000_000,960,bytes([3])*32,bytes([4])*32)

def literal(kind, binding=B, **changes):
    raw=bytearray(512)
    # Independent, explicit wire offsets; no production control encoder exists.
    raw[:4]=b'FSB1';raw[4]=1;raw[5]=kind
    struct.pack_into('<H',raw,6,64);struct.pack_into('<I',raw,8,kind-2)
    struct.pack_into('<H',raw,12,512);struct.pack_into('<Q',raw,20,1000)
    raw[28:44]=binding.nonce
    struct.pack_into('<II',raw,48,binding.period,binding.target)
    raw[64:96]=binding.build;raw[96:128]=binding.image
    for offset,value in changes.items():
        offset=int(offset)
        width='Q' if offset in (20,136,144,152,160,168,176,240,256,304,312) else 'I'
        struct.pack_into('<'+width,raw,offset,value)
    struct.pack_into('<I',raw,508,zlib.crc32(raw[:508]))
    return bytes(raw)

def mutate(raw,offset,value,fmt='I'):
    raw=bytearray(raw);struct.pack_into('<'+fmt,raw,offset,value)
    struct.pack_into('<I',raw,508,zlib.crc32(raw[:508]))
    return bytes(raw)

def started():
    v=Validator(B)
    v.accept(literal(2,**{'132':1}),0);v.mark_start()
    v.accept(literal(3,**{'132':7,'144':1000,'160':32000,'168':32000,'184':67,'188':1,'240':512}),1)
    return v

class HostWire(unittest.TestCase):
    def test_command_literal_crc_reserved_binding_and_profile(self):
        p=B.command(1)
        self.assertEqual(p[:8],bytes.fromhex('4653513101018000'))
        self.assertEqual(p[8:24],B.nonce);self.assertEqual(p[32:64],B.build)
        self.assertEqual(p[96:124],bytes(28));self.assertEqual(zlib.crc32(p[:124]),int.from_bytes(p[124:],'little'))
        self.assertEqual(int.from_bytes(p[24:28],'little'),2_000_000)
        for bad in [0,3,True]:
            with self.assertRaises(StreamError):B.command(bad)
        with self.assertRaises(StreamError):Binding(B.nonce,250_000,960,B.build,B.image)

    def test_all_control_byte_corruptions_fail_crc_or_binding(self):
        p=literal(2,**{'132':1})
        self.assertEqual(Control.decode(p,B).kind,2)
        for i in range(512):
            q=bytearray(p);q[i]^=1
            with self.subTest(i=i),self.assertRaises((StreamError,CodecError)):Control.decode(bytes(q),B)

    def test_recomputed_crc_mutations_reject_structure_and_limits(self):
        p=literal(2,**{'132':1})
        for offset,value,fmt in [(8,1,'I'),(14,1,'H'),(16,16,'H'),(18,1,'H'),(44,1,'I'),(56,1,'Q'),
                                 (128,10,'I'),(132,16,'I'),(184,128,'I'),(208,65,'I'),(212,65,'I'),
                                 (264,17,'I'),(292,17,'I'),(296,27,'I'),(300,3,'I'),(320,1,'I')]:
            with self.subTest(offset=offset),self.assertRaises((StreamError,CodecError)):Control.decode(mutate(p,offset,value,fmt),B)
        for off in (28,48,52,64,96):
            with self.subTest(off=off),self.assertRaises(StreamError):Control.decode(mutate(p,off,123),B)

    def test_atomic_invalid_record_and_duplicate_rejection(self):
        v=started();r=SourceRecord.create(0,2_032_000,B.nonce)
        p=Batch(0,2000,B.nonce,B.period,B.target,(r,)).encode()
        damaged=bytearray(p);damaged[80]=1
        with self.assertRaises(CodecError):v.accept(bytes(damaged),2)
        self.assertEqual((v.frames,v.records,v.next_record),(0,0,0))
        v.accept(p,2)
        with self.assertRaises(StreamError):v.accept(p,3)
        self.assertEqual(v.records,1)

    def test_forward_gap_forensics_never_reset_strict_failure(self):
        v=started()
        for frame,seq in [(0,1),(2,2)]:
            p=Batch(frame,2000+frame,B.nonce,B.period,B.target,(SourceRecord.create(seq,32000+(seq+1)*B.period,B.nonce),)).encode()
            v.accept(p,frame+2)
        self.assertEqual(v.records,2);self.assertEqual(v.strict_failure,'GAP')
        self.assertEqual(v.gaps[0],{'first':0,'last':0,'count':1})
        self.assertFalse(v.summary()['lossless'])

    def test_timing_ownership_ordering_and_snapshot_conservation(self):
        for q in [literal(3,**{'132':7}),literal(4,**{'152':999})]:
            with self.assertRaises(StreamError):Validator(B).accept(q,0)
        p=literal(3,**{'132':7,'144':1000,'160':32000,'168':32000,'184':67,'188':1,'240':512})
        for off,value in [(192,1),(196,1),(208,1),(184,71),(188,0),(240,0)]:
            v=Validator(B);v.accept(literal(2,**{'132':1}),0);v.mark_start()
            with self.subTest(off=off),self.assertRaises(StreamError):v.accept(mutate(p,off,value),1)
        v=started()
        with self.assertRaises(StreamError):v.accept(literal(2,**{'132':1}),2)


class ActualC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frozen=Path(os.environ.get('FORGIX_ENGINE_FIXTURE_ROOT',Path(__file__).resolve().parents[1]))
        subject=frozen/'tests/test_forgix_stream_engine.py'
        expected='eecc1bbe6424a6344222bf6559fcb7769296464c5dff3d02ef55c14038764347'
        assert hashlib.sha256(subject.read_bytes()).hexdigest()==expected
        assert hashlib.sha256((frozen/'firmware/forgix-synthetic-stream/PROTOCOL.md').read_bytes()).hexdigest()==CONTRACT_SHA256
        assert hashlib.sha256((frozen/'firmware/forgix-synthetic-stream/engine.c').read_bytes()).hexdigest()=='6dc304f164cdecfd19b977be9dccfc0ca5b62fbe7e90e01ad4f2de0530f573b5'
        for name,digest in {
            'firmware/forgix-synthetic-stream/engine.h':'488be071b9ffc1cdd1ede05e0a013804578faf61ee36689d2a7784942fdfac04',
            'tests/fixtures/forgix_stream_engine.c':'d841fcf75e10e229b99992499d815de74bbf6f8a74ea7cc1d2cadd12b4388732',
            'firmware/forgix-synthetic-source/codec.c':'e875416516bfe05187b56065140c7af60d73e310af4bd4930d05632fdb8e6011',
            'firmware/forgix-synthetic-source/codec.h':'17de584ec8b71160a36a2d755644a105c875f36853e5b08547053b52b23aa154',
        }.items():assert hashlib.sha256((frozen/name).read_bytes()).hexdigest()==digest
        spec=importlib.util.spec_from_file_location('frozen_actual_engine',subject)
        cls.engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.engine)
        cls.engine.ActualEngine.setUpClass();cls.lib=cls.engine.ActualEngine.lib

    @classmethod
    def tearDownClass(cls):cls.engine.ActualEngine.tearDownClass()

    @classmethod
    def complete(cls,pair=(2_000_000,960),boot=1000):
        r=cls.engine.Rig(cls.lib,pair,boot=boot);r.ready()
        for _ in range(60001):r.time+=1000;r.step()
        r.finish();return r

    def replay(self,r):
        binding=Binding(r.nonce,*r.pair,r.build,r.image,r.field(21)>0);v=Validator(binding)
        for ix,p in enumerate(r.frames()):
            if p[5]==3:v.mark_start()
            v.accept(p,ix*1_000_000)
        return v

    def test_all_three_actual_C_complete_wire_sequences(self):
        for pair in ((2_000_000,960),(500_000,3840),(250_000,7680)):
            with self.subTest(pair=pair):
                r=self.complete(pair);v=self.replay(r)
                self.assertTrue(v.summary()['lossless']);self.assertEqual(v.records,pair[1])
                self.assertEqual(v.end.values['accepted_bytes'],512*(v.frames+2))

    def test_actual_C_tick32_wrap(self):
        r=self.complete(boot=(1<<32)//32-2000);v=self.replay(r)
        self.assertTrue(v.summary()['lossless']);self.assertGreater(v.strict.tick32_wraps,0)

    def test_actual_C_RP_pause_is_bound_separately_from_host_pause(self):
        r=self.engine.Rig(self.lib,pause=True);r.ready()
        for _ in range(60001):r.time+=1000;r.step()
        r.finish();v=self.replay(r);self.assertTrue(v.summary()['lossless'])
        self.assertEqual(v.end.values['pause_end_us']-v.end.values['pause_start_us'],100000)
        wrong=Validator(B)
        for p in r.frames()[:-1]:
            if p[5]==3:wrong.mark_start()
            wrong.accept(p,1)
        with self.assertRaises(StreamError):wrong.accept(r.frames()[-1],1)

    def test_actual_C_source_loss_forensic_and_bad_final_snapshot(self):
        r=self.engine.Rig(self.lib,(250000,7680));r.ready();r.usb_limit=0
        for _ in range(11000):r.time+=1000;r.step()
        r.usb_limit=512
        for _ in range(55000):r.time+=1000;r.step()
        r.finish();v=self.replay(r)
        self.assertFalse(v.summary()['lossless']);self.assertEqual(v.end.values['status'],8)
        self.assertGreater(sum(g['count'] for g in v.gaps),0)
        r=self.engine.Rig(self.lib);r.ready();r.fail=(False,0x50);r.time+=65_000_000;r.step();r.finish()
        v=self.replay(r);self.assertFalse(v.end.values['flags']&4)
        self.assertFalse(v.summary()['lossless'])

    def test_actual_C_ambiguous_pop_retains_canonical_record(self):
        r=self.engine.Rig(self.lib);r.pop_refuse=True;r.ready();r.time+=70000;r.step();r.finish()
        v=self.replay(r);self.assertEqual(v.end.values['status'],7)
        self.assertEqual(v.end.values['pending_flags'],3)
        self.assertEqual(len(v.end.uncertain_record),16);self.assertFalse(v.summary()['lossless'])

    def test_actual_C_complete_end_mutations_and_failed_latch(self):
        r=self.complete();frames=r.frames()
        for off,value,fmt in [(132,3,'I'),(176,1,'Q'),(192,959,'I'),(224,959,'I'),(240,0,'Q'),(184,67,'I'),(300,1,'I')]:
            with self.subTest(off=off):
                v=Validator(B)
                for p in frames[:-1]:
                    if p[5]==3:v.mark_start()
                    v.accept(p,1)
                with self.assertRaises(StreamError):v.accept(mutate(frames[-1],off,value,fmt),1)

if __name__=='__main__':unittest.main()

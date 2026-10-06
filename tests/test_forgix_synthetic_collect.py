"""Owned host fixtures: no device, real C wire output and real inherited flock."""
import fcntl
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from forgix_synthetic_collect import collect, PrivateRun, replay
from forgix_synthetic_stream import Binding, StreamError, CONTRACT_SHA256
import test_forgix_synthetic_stream as wire

class Clock:
    def __init__(self):self.value=1_000_000_000
    def now(self):return self.value
    def pause(self,seconds):self.value+=round(seconds*1e9)

class Transport:
    def __init__(self,frames,clock,binding):
        self.frames=frames;self.clock=clock;self.binding=binding;self.index=0;self.offset=0
        self.writes=[];self.closed=False;self.chunk=512;self.short_write=None
        self.error=None;self.late=False;self.close_error=False;self.close_late=False
        self.eof=None
    def write(self,data,until):
        self.writes.append(bytes(data));self.clock.value+=1000
        return len(data) if self.short_write is None else self.short_write
    def read(self,n,until):
        if self.error is not None:raise self.error
        if self.late:self.clock.value=round(until*1e9)
        if self.eof is not None and self.index==self.eof:return b''
        p=self.frames[self.index]
        # A fixture replays complete real-C packets with their RP time, retaining
        # host scheduler/pause delays separately. The firmware is not re-run here.
        device=struct.unpack_from('<Q',p,20)[0]
        self.clock.value=max(self.clock.value,1_000_000_000+(device-1000)*1000)
        size=min(n,self.chunk,len(p)-self.offset)
        data=p[self.offset:self.offset+size];self.offset+=size
        if self.offset==512:self.index+=1;self.offset=0
        return data
    def close(self):
        self.closed=True
        if self.close_late:self.clock.value=122_000_000_000
        if self.close_error:raise OSError('private close failure')

class Collection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wire.ActualC.setUpClass();r=wire.ActualC.complete()
        cls.frames=r.frames();cls.binding=Binding(r.nonce,*r.pair,r.build,r.image)
    @classmethod
    def tearDownClass(cls):wire.ActualC.tearDownClass()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.lockpath=self.root/'operator.lock';self.fd=os.open(self.lockpath,os.O_RDWR|os.O_CREAT,0o600)
        fcntl.flock(self.fd,fcntl.LOCK_EX)
        self.clock=Clock();self.tx=Transport(self.frames,self.clock,self.binding)
        self.identity={'selected':'fixture-original'};self.opens=0
    def tearDown(self):os.close(self.fd);self.temp.cleanup()
    def admission(self):
        return {'synthetic_stream_qualified':True,'lifecycle_admitted':True,'contract_sha256':CONTRACT_SHA256,
                'build_sha256':self.binding.build.hex(),'image_sha256':self.binding.image.hex(),'rp_drain_pause_enabled':False}
    def open(self,identity,until):self.opens+=1;return self.tx
    def run_trial(self,**kw):
        values=dict(path=self.root/'run',binding=self.binding,open_transport=self.open,
                    verify_admission=self.admission,select_identity=lambda:self.identity.copy(),lockfd=self.fd,
                    lockpath=self.lockpath,boot_host_ns=1_000_000_000,clock_ns=self.clock.now,pause=self.clock.pause)
        values.update(kw);return collect(**values)
    def failed(self,kind=Exception,**kw):
        with self.assertRaises(kind) as ctx:self.run_trial(**kw)
        return ctx.exception.collection_result

    def test_partial_read_complete_success_pause_permissions_and_lock_retained(self):
        self.tx.chunk=17;r=self.run_trial()
        self.assertEqual(r['status'],'lossless');self.assertEqual(r['validation']['received_records'],960)
        self.assertEqual(r['host_pause']['duration_ns'],100_000_000)
        self.assertTrue(r['transport_closed'] and r['persistence_verified'])
        self.assertEqual(self.tx.writes,[self.binding.command(1),self.binding.command(2)])
        self.assertEqual((self.root/'run/raw.bin').read_bytes(),b''.join(self.frames))
        self.assertEqual((self.root/'run').stat().st_mode&0o777,0o700)
        for p in (self.root/'run').iterdir():self.assertEqual(p.stat().st_mode&0o777,0o600)
        self.assertTrue(os.fstat(self.fd)) # collector never closes inherited lock
        offline=replay(self.root/'run',self.binding)
        self.assertTrue(offline['lossless']);self.assertEqual(offline['received_records'],960)
        self.assertEqual(sum(b['record_bytes'] for b in offline['per_second_host_arrivals'].values()),960*16)

    def test_short_command_write_no_retry_and_closed(self):
        self.tx.short_write=127;r=self.failed(StreamError)
        self.assertEqual(len(self.tx.writes),1);self.assertTrue(self.tx.closed)
        self.assertEqual(r['raw_bytes'],0);self.assertTrue(r['persistence_verified'])
        self.assertEqual((self.root/'run/config-command.bin').read_bytes(),self.binding.command(1))

    def test_partial_reply_eof_deadline_retains_exact_prefix(self):
        self.tx.frames=[self.frames[0][:113]+bytes(399)]
        self.tx.chunk=113
        original=self.tx.read
        def partial(n,deadline):
            if self.tx.offset>=113:return b''
            return original(n,deadline)
        self.tx.read=partial;r=self.failed(StreamError)
        self.assertEqual((self.root/'run/raw.bin').read_bytes(),self.frames[0][:113])
        self.assertEqual(r['raw_bytes'],113);self.assertTrue(self.tx.closed)

    def test_empty_reply_and_late_fragment_never_accepted(self):
        self.tx.eof=0;r=self.failed(StreamError)
        self.assertEqual(r['raw_bytes'],0);self.assertTrue(self.tx.closed)
        self.root.joinpath('run').rename(self.root/'empty-attempt')
        self.clock=Clock();self.tx=Transport(self.frames,self.clock,self.binding);self.tx.late=True
        r=self.failed(StreamError)
        self.assertEqual(r['raw_bytes'],512);self.assertEqual(r['validation']['received_records'],0)

    def test_read_exception_attached_prefix_and_cancel_preserve_cause(self):
        error=OSError('private foreign bytes excluded');error.consumed_prefix=self.frames[0][:53]
        self.tx.error=error;r=self.failed(OSError)
        self.assertEqual(r['failure']['kind'],'OSError');self.assertEqual(r['raw_bytes'],53)
        self.assertEqual((self.root/'run/raw.bin').read_bytes(),self.frames[0][:53])
        self.root.joinpath('run').rename(self.root/'read-exception')
        self.clock=Clock();self.tx=Transport(self.frames,self.clock,self.binding)
        self.tx.error=KeyboardInterrupt();r=self.failed(KeyboardInterrupt)
        self.assertTrue(self.tx.closed);self.assertEqual(len(self.tx.writes),1)

    def test_disk_failure_still_closes_no_received_integrity_claim(self):
        class Broken(PrivateRun):
            def append(self,data):raise OSError('disk full')
        r=self.failed(OSError,store_factory=Broken)
        self.assertTrue(self.tx.closed);self.assertEqual(r['status'],'failed')
        self.assertEqual(r['raw_bytes'],0);self.assertEqual(r['validation']['received_records'],0)
        self.assertEqual(r['observed_unpersisted_bytes'],512);self.assertFalse(r['persistence_verified'])

    def test_result_disk_failure_and_close_failure_are_not_success(self):
        class BrokenResult(PrivateRun):
            def result(self,value):raise OSError('disk full')
        r=self.failed(OSError,store_factory=BrokenResult)
        self.assertFalse(r['persistence_verified']);self.assertTrue(r['transport_closed'])
        self.root.joinpath('run').rename(self.root/'result-write-failed')
        self.clock=Clock();self.tx=Transport(self.frames,self.clock,self.binding);self.tx.close_error=True
        r=self.failed(OSError);self.assertFalse(r['transport_closed']);self.assertEqual(r['status'],'failed')

    def test_late_closure_and_reversed_clock_refuse_success(self):
        self.tx.close_late=True;r=self.failed(StreamError)
        self.assertTrue(r['transport_closed']);self.assertEqual(r['status'],'failed')
        self.root.joinpath('run').rename(self.root/'late-close')
        self.clock=Clock();self.tx=Transport(self.frames,self.clock,self.binding)
        original=self.tx.read
        def reversed_clock(n,deadline):
            data=original(n,deadline);self.clock.value=0;return data
        self.tx.read=reversed_clock;r=self.failed(StreamError);self.assertTrue(self.tx.closed)
        self.assertEqual(r['raw_bytes'],512)

    def test_write_exception_and_cancel_never_reapply_command(self):
        def failed_write(data,deadline):
            self.tx.writes.append(data)
            raise OSError('may have reached source')
        self.tx.write=failed_write;r=self.failed(OSError)
        self.assertEqual(len(self.tx.writes),1);self.assertTrue(self.tx.closed)
        self.assertEqual(r['failure']['operation'],'config-write')
        self.assertEqual((self.root/'run/config-command.bin').read_bytes(),self.binding.command(1))

    def test_frame_CRC_error_retained_without_start_or_resync(self):
        p=bytearray(self.frames[0]);p[128]^=1;self.tx.frames=[bytes(p),*self.frames[1:]]
        r=self.failed(StreamError)
        self.assertEqual((self.root/'run/raw.bin').read_bytes(),bytes(p))
        self.assertEqual(len(self.tx.writes),1);self.assertTrue(self.tx.closed)

    def test_replay_refuses_tampered_hash_and_missing_START_intent(self):
        self.run_trial()
        raw=self.root/'run/raw.bin';original=raw.read_bytes();raw.write_bytes(original[:-1])
        with self.assertRaises(StreamError):replay(self.root/'run',self.binding)
        raw.write_bytes(original)
        journal=self.root/'run/journal.jsonl'
        events=[json.loads(line) for line in journal.read_bytes().splitlines()]
        journal.write_text(''.join(json.dumps(e)+'\n' for e in events if not (e.get('operation')=='start' and e.get('phase')=='intent')))
        with self.assertRaises(StreamError):replay(self.root/'run',self.binding)

    def test_unqualified_or_missing_flock_refuses_before_open(self):
        r=self.failed(StreamError,verify_admission=lambda:{})
        self.assertEqual(self.opens,0);self.assertFalse((self.root/'run').exists())
        fcntl.flock(self.fd,fcntl.LOCK_UN)
        self.failed(Exception);self.assertEqual(self.opens,0)

    def test_identity_change_and_short_pause_abort_and_close(self):
        original=self.tx.read
        def changed(n,deadline):
            data=original(n,deadline);self.identity={'selected':'different'};return data
        self.tx.read=changed;r=self.failed(StreamError)
        self.assertEqual(r['raw_bytes'],512);self.assertTrue(self.tx.closed)
        self.root.joinpath('run').rename(self.root/'changed-identity')
        self.clock=Clock();self.tx=Transport(self.frames,self.clock,self.binding)
        r=self.failed(StreamError,pause=lambda seconds:None)
        self.assertEqual(r['host_pause']['duration_ns'],0);self.assertTrue(self.tx.closed)

    def test_full_admission_rate_limited_but_identity_checked_every_frame(self):
        """Episode 001 regression: per-frame full admission throttled the host."""
        calls=[];selects=[]
        def admission():calls.append(self.clock.value);return self.admission()
        def select():selects.append(self.clock.value);return self.identity.copy()
        r=self.run_trial(verify_admission=admission,select_identity=select)
        self.assertEqual(r['status'],'lossless')
        frames=len(self.frames)
        # Identity is still re-read on every check (several per frame).
        self.assertGreaterEqual(len(selects),2*frames)
        # Full admission: commands + end + at most about one per streamed second.
        span=(calls[-1]-calls[0])/1e9
        self.assertLess(len(calls),frames)
        self.assertLessEqual(len(calls),span+12)
        gaps=[(b-a)/1e9 for a,b in zip(calls,calls[1:])]
        self.assertLessEqual(max(gaps),2.5)  # never more than ~1s plus one frame wait

    def test_admission_failure_mid_stream_still_stops(self):
        state={'n':0}
        def admission():
            state['n']+=1
            return self.admission() if state['n']<8 else {}
        r=self.failed(StreamError,verify_admission=admission)
        self.assertNotEqual(r['status'],'lossless');self.assertTrue(self.tx.closed)
        self.assertLess(r['raw_bytes'],len(self.frames)*512)

if __name__=='__main__':unittest.main()

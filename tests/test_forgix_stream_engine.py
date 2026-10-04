"""Actual C engine with explicit source/USB fault injection; no hardware model claim."""
import ctypes as C
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
NOW=C.CFUNCTYPE(C.c_uint64,C.c_void_p)
SERVICE=C.CFUNCTYPE(None,C.c_void_p)
BOUND=C.CFUNCTYPE(C.c_bool,C.c_void_p,C.c_uint64)
XFER=C.CFUNCTYPE(C.c_bool,C.c_void_p,C.c_bool,C.c_uint32,C.POINTER(C.c_uint32),C.c_uint64)
USB=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.POINTER(C.c_uint8),C.c_size_t)
class IO(C.Structure):
    _fields_=[('ctx',C.c_void_p),('now',NOW),('service',SERVICE),('configure',BOUND),('prepare',BOUND),('xfer',XFER),('usb',USB),('safe',SERVICE)]

class Rig:
    def __init__(self,lib,pair=(2000000,960),pause=False,boot=1000):
        self.lib=lib;self.time=boot;self.cfg=0;self.prepared=0;self.safe=0;self.service=0
        self.pair=pair;self.nonce=bytes(range(1,17));self.build=bytes([3])*32;self.image=bytes([4])*32
        self.settings={};self.start=None;self.stop=None;self.generated=0;self.enqueued=0;self.popped=0;self.drops=0;self.fifo=[]
        self.highwater=0;self.refused_pop=0;self.snap={};self.snapid=0;self.calls=[];self.output=bytearray();self.usb_limit=512;self.usb_delay=0
        self.fail=None;self.corrupt=None;self.pop_refuse=False;self.config_ok=True;self.config_delay=0;self.final_forge=None
        self.callback_errors=[]
        self._callbacks=[NOW(lambda _:self.time),SERVICE(self._service),BOUND(self._config),BOUND(self._prepare),XFER(self._guard_xfer),USB(self._usb),SERVICE(self._safe)]
        self.io=IO(None,*self._callbacks);self.engine=C.create_string_buffer(lib.engine_size())
        assert lib.fs_init(self.engine,self.io,self.build,self.image,pause)
    def _service(self,_):self.service+=1
    def _safe(self,_):self.safe+=1
    def _config(self,_,until):self.cfg+=1;self.time+=self.config_delay;return self.config_ok
    def _prepare(self,_,until):self.prepared+=1;return True
    def tick(self):return self.time*32
    def offers(self):
        if self.start is None:return
        due=min(self.pair[1],(self.tick()-self.start)//self.pair[0])
        if self.stop is not None:due=min(due,self.generated)
        while self.generated<due:
            seq=self.generated;tick=(self.start+(seq+1)*self.pair[0])&0xffffffff
            fold=0
            for x in struct.unpack('<4I',self.nonce):fold^=x
            pattern=seq^(((seq<<7)|(seq>>25))&0xffffffff)^fold^0x46534731
            body=struct.pack('<3I',seq,tick,pattern);record=body+struct.pack('<I',zlib.crc32(body))
            if len(self.fifo)<64:self.fifo.append(record);self.enqueued+=1;self.highwater=max(self.highwater,len(self.fifo))
            else:self.drops+=1
            self.generated+=1
        if self.generated==self.pair[1] and self.stop is None:self.stop=self.start+self.pair[0]*self.pair[1]
    def state(self):
        if self.start is None:return 0
        return 65|(2 if self.stop is None else 4)|(8 if self.fifo else 0)
    def _guard_xfer(self,*args):
        try:return self._xfer(*args)
        except Exception as exc:self.callback_errors.append(repr(exc));return False
    def _xfer(self,_,write,address,value,until):
        off=address-0x10000;self.offers();self.calls.append((write,off,value[0] if write else None,until))
        if self.fail==(write,off):return False
        if write:
            v=value[0]
            if off in (0x10,0x14,0x18,0x1c,0x20,0x24):self.settings[off]=v
            elif off==0xc and v==1:self.start=self.tick()
            elif off==0xc and v==2:self.stop=self.tick()
            elif off==0xc and v==4:
                self.snapid+=1
                self.snap={0x4c:self.snapid,0x50:self.tick()&0xffffffff,0x54:self.tick()>>32,0x58:self.state(),0x5c:self.generated,0x60:self.enqueued,
                    0x64:self.drops,0x68:self.popped,0x6c:self.refused_pop,0x70:0,0x74:len(self.fifo),0x78:self.highwater,
                    0x7c:(self.start or 0)&0xffffffff,0x80:(self.start or 0)>>32,0x84:(self.stop or 0)&0xffffffff,0x88:(self.stop or 0)>>32}
                if self.snapid>1 and self.final_forge:
                    key,value=self.final_forge;self.snap[key]=value
            elif off==0x40 and self.fifo and not self.pop_refuse:
                assert v==struct.unpack_from('<I',self.fifo[0])[0]
                self.fifo.pop(0);self.popped+=1
            elif off==0x40:self.refused_pop+=1 # SPIBone ACK is indistinguishable from ERR.
            else:raise AssertionError(('unexpected write',off,v))
        else:
            if off in self.settings:v=self.settings[off]
            elif off in (0,4,8):v={0:0x46534731,4:32000000,8:0x74010}[off]
            elif off==0x28:v=self.state()
            elif off==0x2c:v=len(self.fifo)
            elif off==0x48:v=self.popped
            elif off in (0x34,0x38,0x3c,0x44):
                ix={0x34:0,0x38:4,0x3c:8,0x44:12}[off];v=struct.unpack_from('<I',self.fifo[0],ix)[0]
            elif off in self.snap:v=self.snap[off]
            else:raise AssertionError(('unexpected read',off))
            value[0]=v^(1 if self.corrupt==off else 0)
        return True
    def _usb(self,_,data,size):
        self.time+=self.usb_delay;n=min(size,self.usb_limit)
        self.output.extend(C.string_at(data,n));return n
    def command(self,op=1,**changes):
        p=bytearray(128);struct.pack_into('<4sBBH16sII32s32s',p,0,b'FSQ1',1,op,128,self.nonce,*self.pair,self.build,self.image)
        for offset,value in changes.items():p[int(offset)]=value
        struct.pack_into('<I',p,124,zlib.crc32(p[:124]));self.lib.fs_command(self.engine,bytes(p),128)
    def field(self,n):return self.lib.engine_field(self.engine,n)
    def step(self):self.lib.fs_step(self.engine)
    def ready(self):self.command();self.step();self.command(2);self.step()
    def finish(self):
        for _ in range(200):
            self.step();self.time+=10000
            if self.field(0)==5:return
        raise AssertionError('not finite')
    def frames(self):
        self.assert_frame_bound()
        return [bytes(self.output[i:i+512]) for i in range(0,len(self.output),512)]
    def assert_frame_bound(self):
        assert not self.callback_errors,self.callback_errors
        assert len(self.output)%512==0

class ActualEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();out=Path(cls.temp.name)/'engine.so'
        include=ROOT/'firmware/forgix-synthetic-stream';codec=ROOT/'firmware/forgix-synthetic-source'
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-Wall','-Wextra','-Werror','-fPIC','-shared','-O2',
            '-I'+str(include),'-I'+str(codec),str(include/'engine.c'),str(codec/'codec.c'),str(ROOT/'tests/fixtures/forgix_stream_engine.c'),'-o',str(out)],check=True)
        cls.lib=C.CDLL(str(out));cls.lib.engine_size.restype=C.c_size_t
        cls.lib.fs_init.argtypes=[C.c_void_p,IO,C.c_char_p,C.c_char_p,C.c_bool];cls.lib.fs_init.restype=C.c_bool
        cls.lib.fs_command.argtypes=[C.c_void_p,C.c_char_p,C.c_size_t];cls.lib.fs_step.argtypes=[C.c_void_p]
        cls.lib.engine_field.argtypes=[C.c_void_p,C.c_uint];cls.lib.engine_field.restype=C.c_uint64
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def check_frames(self,r):
        f=r.frames()
        for p in f:self.assertEqual(zlib.crc32(p[:508]),struct.unpack_from('<I',p,508)[0]);self.assertEqual(p[:5],b'FSB1\1')
        return f
    def test_all_finite_rates_actual_record_and_control_bytes(self):
        for pair in ((2000000,960),(500000,3840),(250000,7680)):
            with self.subTest(pair=pair):
                r=Rig(self.lib,pair);r.ready()
                for _ in range(60001):r.time+=1000;r.step()
                r.finish();self.assertEqual((r.field(0),r.field(1),r.field(3)),(5,0,pair[1]))
                f=self.check_frames(r);self.assertEqual([p[5] for p in f if p[5]!=1],[2,3,4])
                records=[]
                for p in f:
                    if p[5]!=1:continue
                    count=struct.unpack_from('<H',p,14)[0]
                    for i in range(count):
                        q=p[64+i*16:80+i*16];self.assertEqual(zlib.crc32(q[:12]),struct.unpack_from('<I',q,12)[0]);records.append(q)
                self.assertEqual(len(records),pair[1]);self.assertEqual([struct.unpack_from('<I',q)[0] for q in records],list(range(pair[1])))
                self.assertFalse(any(w and off==0xc and v==2 for w,off,v,_ in r.calls))
                self.assertEqual(struct.unpack_from('<I',f[-1],204)[0],pair[1])
                self.assertEqual([struct.unpack_from('<I',p,8)[0] for p in f if p[5]!=1],[0,1,2])
                self.assertEqual(struct.unpack_from('<I',f[0],132)[0],1)
                self.assertEqual(struct.unpack_from('<I',f[1],132)[0],7)
                for p in (f[0],f[1],f[-1]):self.assertEqual(p[320:508],bytes(188))
    def test_corrupt_crc_prevents_pop(self):
        r=Rig(self.lib);r.ready();r.time+=70000;r.corrupt=0x44;r.step();r.finish()
        self.assertEqual(r.field(1),6);self.assertFalse(any(w and o==0x40 for w,o,_,_ in r.calls))
    def test_consumed_pop_missing_reply_is_retained_and_never_retried(self):
        r=Rig(self.lib);r.fail=(False,0x48)
        # Fail only the readback AFTER POP, not the prior live count.
        def x(_,w,a,v,u):
            if r.popped and not w and a==0x10048:return False
            fail=r.fail;r.fail=None
            try:return r._xfer(_,w,a,v,u)
            finally:r.fail=fail
        callback=XFER(x);r.io.xfer=callback
        # IO was copied by C; reinitialize a fresh rig with this callback.
        r.lib.fs_init(r.engine,r.io,r.build,r.image,False);r.ready();r.time+=70000;r.step();r.finish()
        self.assertEqual(r.field(1),7);self.assertEqual(r.popped,1);self.assertEqual(r.field(9),3)
        self.assertEqual(sum(w and o==0x40 for w,o,_,_ in r.calls),1)
        self.assertEqual(struct.unpack_from('<I',r.frames()[-1],268)[0],0)
    def test_full_usb_queue_does_not_consume_then_accounts_source_loss(self):
        r=Rig(self.lib,(250000,7680));r.ready();r.usb_limit=0
        for _ in range(10000):r.time+=1000;r.step()
        self.assertEqual(r.field(7),16);before=r.popped
        for _ in range(1000):r.time+=1000;r.step()
        self.assertEqual(r.popped,before);r.offers();self.assertGreater(r.drops,0)
        r.usb_limit=512
        for _ in range(55000):r.time+=1000;r.step()
        r.finish();self.assertEqual(r.field(1),8);self.assertGreater(r.field(17),0)
        self.assertEqual(r.field(15),r.field(16)+r.field(17));self.assertEqual(r.field(16),r.field(18)+r.field(19))
    def test_partial_usb_writes_preserve_exact_frames(self):
        r=Rig(self.lib);r.usb_limit=7;r.ready();r.time+=70000
        for _ in range(400):r.step();r.time+=1000
        r.time+=65000000;r.finish();self.check_frames(r);self.assertGreater(r.field(12),0)
    def test_invalid_identity_duplicate_and_late_config_no_gpio_retries(self):
        for kind in ('identity','late','duplicate'):
            r=Rig(self.lib)
            if kind=='identity':r.command(**{'32':9});self.assertEqual(r.cfg,0)
            elif kind=='late':r.time+=30000000;r.command();self.assertEqual(r.cfg,0)
            else:r.command();r.command();self.assertEqual(r.cfg,1)
            self.assertNotEqual(r.field(1),0);self.assertFalse(r.calls)
    def test_config_timeout_and_start_readback_refusal_are_failed(self):
        r=Rig(self.lib);r.config_delay=20000000;r.command();self.assertEqual(r.field(1),3)
        r=Rig(self.lib);r.command();r.corrupt=0x10;r.command(2);self.assertEqual(r.field(1),5)
        self.assertFalse(any(w and o==0xc and v==1 for w,o,v,_ in r.calls))
    def test_no_progress_terminal_is_bounded_without_fabricated_end(self):
        r=Rig(self.lib);r.ready();r.usb_limit=0;r.time+=65000000;r.step();r.time+=2000000;r.step()
        self.assertEqual(r.field(0),5);self.assertNotEqual(r.field(1),0);self.assertEqual([p[5] for p in r.frames()],[2,3]);self.assertGreater(r.safe,0)
    def test_late_usb_return_and_clock_reversal_cannot_complete(self):
        r=Rig(self.lib);r.command();r.usb_delay=120000000;r.step();self.assertEqual(r.field(0),5);self.assertNotEqual(r.field(1),0)
        r=Rig(self.lib);r.command();r.time=0;r.step();self.assertEqual(r.field(0),5);self.assertNotEqual(r.field(1),0)
    def test_exact_rp_pause_is_separate_from_host_stall(self):
        r=Rig(self.lib,pause=True);r.ready();r.time+=30000000;r.step();begin=r.field(21);before=r.popped
        r.time+=99999;r.step();self.assertEqual(r.popped,before)
        r.time+=1;r.step();self.assertEqual(r.field(22)-begin,100000);self.assertEqual(r.popped,before+1)
    def test_tick32_wrap_uses_coherent_full_start_tick(self):
        r=Rig(self.lib,boot=134210000);r.ready()
        for _ in range(60001):r.time+=1000;r.step()
        r.finish();self.assertEqual(r.field(1),0)
        data=[p for p in r.frames() if p[5]==1]
        record=data[0][64:80];self.assertEqual(struct.unpack_from('<I',record,4)[0],(r.start+2000000)&0xffffffff)
        self.assertGreater(r.start+2000000,0xffffffff)
    def test_refused_pop_effect_is_not_accepted_or_retried(self):
        r=Rig(self.lib);r.ready();r.pop_refuse=True;r.time+=70000;r.step();r.finish()
        self.assertEqual(r.field(1),7);self.assertEqual(r.field(3),0)
        self.assertEqual(sum(w and o==0x40 for w,o,_,_ in r.calls),1)
        self.assertEqual(r.field(9),3)
    def test_duplicate_start_does_not_restart_or_rewrite_nonce(self):
        r=Rig(self.lib);r.ready();r.command(2);r.finish()
        self.assertEqual(r.field(1),1)
        self.assertEqual(sum(w and o==0xc and v==1 for w,o,v,_ in r.calls),1)
        for off in (0x10,0x14,0x18,0x1c,0x20,0x24):self.assertEqual(sum(w and o==off for w,o,_,_ in r.calls),1)
    def test_old_snapshot_not_claimed_valid_after_failed_head_transfer(self):
        r=Rig(self.lib);r.ready();r.fail=(False,0x34);r.time+=70000;r.step();r.finish()
        end=r.frames()[-1];self.assertEqual(end[5],4)
        self.assertEqual(struct.unpack_from('<I',end,132)[0]&4,0)
        self.assertEqual(struct.unpack_from('<I',end,188)[0],1)
        self.assertEqual(r.field(1),4)
    def test_final_snapshot_semantics_cannot_forge_zero_loss_success(self):
        for mutation in ('state','start','tick','stop','head','highwater'):
            with self.subTest(mutation=mutation):
                r=Rig(self.lib);r.ready()
                r.final_forge={'state':(0x58,0),'start':(0x7c,(r.start+1)&0xffffffff),'tick':(0x50,0),'stop':(0x84,0),
                    'head':(0x58,77),'highwater':(0x78,0)}[mutation]
                for _ in range(60001):r.time+=1000;r.step()
                r.finish();self.assertNotEqual(r.field(1),0)
                self.assertNotEqual(struct.unpack_from('<I',r.frames()[-1],128)[0],0)
    def test_contradictory_live_state_is_rejected_before_head_or_pop(self):
        for state in (72,74,79):
            with self.subTest(state=state):
                r=Rig(self.lib);r.ready();r.state=lambda:state
                r.time+=70000;r.step();r.finish()
                self.assertEqual(r.field(1),5);self.assertEqual(r.popped,0)
                self.assertFalse(any(o in (0x34,0x38,0x3c,0x44,0x40) for _,o,_,_ in r.calls))
    def test_fresh_configuration_cap_clock_cannot_launch_late_side_effect(self):
        r=Rig(self.lib);calls=0
        def sampled(_):
            nonlocal calls
            calls+=1
            if calls>=3:r.time=30001000
            return r.time
        clock=NOW(sampled);r.io.now=clock
        self.lib.fs_init(r.engine,r.io,r.build,r.image,False)
        r.command();self.assertEqual(r.cfg,0);self.assertEqual(r.field(1),2)
    def test_malformed_unbound_command_cannot_emit_fake_nonce_control(self):
        r=Rig(self.lib);r.command(**{'32':9});r.step()
        self.assertEqual(r.field(0),5);self.assertEqual(r.cfg,0);self.assertEqual(r.output,b'')

if __name__=='__main__':unittest.main()

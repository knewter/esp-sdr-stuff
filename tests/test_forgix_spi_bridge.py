"""Real C codec and assembled PIO driving real guarded SPIBone; no hardware.

The small PIO interpreter covers only the assembled programs' instruction
subset. It does not model MMIO, pad delay, metastability, SDK startup or a
physical RP clock. Compiled firmware review and physical timing remain gates.
"""
import ctypes as C
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_spi_bridge as host
from forgix_usb_ram_artifact import inspect_elf,PROFILE,BRIDGE_PROFILE
from test_forgix_usb_ram import fixture

U8=C.c_uint8
class Request(C.Structure):
    _fields_=[('op',U8),('nonce',U8*16),('sequence',C.c_uint32),('address',C.c_uint32),('value',C.c_uint32)]
class Session(C.Structure):
    _fields_=[('attempted',C.c_bool),('nonce',U8*16),('next',C.c_uint32)]

class NativeProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('cc')
        if not compiler or not str(Path(compiler).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Use the locked Nix shell: native C compiler required')
        cls.temp=tempfile.TemporaryDirectory(prefix='forgix-bridge-c-')
        lib=Path(cls.temp.name)/'protocol.so'
        subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',
            str(ROOT/'firmware/forgix-spi-bridge/protocol.c'),'-o',str(lib)],check=True,timeout=30,capture_output=True)
        cls.lib=C.CDLL(str(lib))
        cls.lib.bridge_parse.argtypes=[C.POINTER(U8),C.POINTER(Request)];cls.lib.bridge_parse.restype=C.c_bool
        cls.lib.bridge_allowed.argtypes=[C.POINTER(Request)];cls.lib.bridge_allowed.restype=C.c_bool
        cls.lib.bridge_admit.argtypes=[C.POINTER(Session),C.POINTER(Request),C.c_uint64];cls.lib.bridge_admit.restype=C.c_uint
        cls.lib.bridge_wire_request.argtypes=[C.POINTER(Request),C.POINTER(U8)];cls.lib.bridge_wire_request.restype=C.c_uint
        cls.lib.bridge_wire_response.argtypes=[C.c_bool,C.POINTER(U8),C.POINTER(C.c_uint32)];cls.lib.bridge_wire_response.restype=C.c_uint
        cls.lib.bridge_response.argtypes=[C.POINTER(U8),C.POINTER(Request),C.c_uint,C.c_uint32,C.c_uint64,C.c_char_p]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def parse(self,data):
        r=Request();valid=self.lib.bridge_parse((U8*48).from_buffer_copy(data),C.byref(r));return valid,r
    def test_python_plan_matches_real_c_and_exact_big_endian_wire(self):
        nonce=bytes(range(16));commands=host.plan(nonce)+host.restore_and_finish(nonce,0xdeadbeef,11)
        session=Session()
        for i,data in enumerate(commands):
            valid,r=self.parse(data);self.assertTrue(valid);self.assertTrue(self.lib.bridge_allowed(C.byref(r)))
            self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(r),1000),1 if i==0 else 2)
            wire=(U8*9)();n=self.lib.bridge_wire_request(C.byref(r),wire)
            if r.op in (host.READ,host.WRITE):
                expected=bytes([0 if r.op==host.WRITE else 1])+r.address.to_bytes(4,'big')
                if r.op==host.WRITE:expected+=r.value.to_bytes(4,'big')
                self.assertEqual(bytes(wire[:n]),expected)
            else:self.assertEqual(n,0)
    def test_each_corrupted_byte_is_inert_and_reserved_fields_cannot_be_smuggled(self):
        original=host.request(host.ARM,1,bytes(range(16)))
        for i in range(48):
            p=bytearray(original);p[i]^=1;self.assertFalse(self.parse(p)[0],i)
        for i in (4,6,7,*range(36,44)):
            p=bytearray(original);p[i]^=1;struct.pack_into('<I',p,44,zlib.crc32(p[:44]));self.assertFalse(self.parse(p)[0],i)
    def test_nonce_replay_order_start_window_and_finite_count(self):
        nonce=bytes(range(16));session=Session();_,arm=self.parse(host.request(host.ARM,1,nonce))
        self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(arm),30000000),0)
        self.assertFalse(session.attempted)
        self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(arm),29999999),1)
        self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(arm),1),0)
        _,wrong=self.parse(host.request(host.READ,2,b'x'*16,host.COUNTER))
        self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(wrong),1),0);self.assertEqual(session.next,2)
        for i in range(2,25):
            _,r=self.parse(host.request(host.READ,i,nonce,host.COUNTER))
            self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(r),1),2)
        r.sequence=25;self.assertEqual(self.lib.bridge_admit(C.byref(session),C.byref(r),1),0)
    def test_reset_and_arbitrary_addresses_never_encode_spi(self):
        _,r=self.parse(host.request(host.WRITE,2,b'x'*16,host.SCRATCH,0x1357ace0))
        for address in (0,4,8,0x1000,0x1005,0x800,0xffffffff):
            r.address=address;self.assertFalse(self.lib.bridge_allowed(C.byref(r)))
            self.assertEqual(self.lib.bridge_wire_request(C.byref(r),(U8*9)()),0)
        r.address=host.SCRATCH;r.nonce[:]=bytes(16);self.assertFalse(self.lib.bridge_allowed(C.byref(r)))
    def test_response_pending_ack_wrong_header_and_truncation(self):
        for write in (False,True):
            for prefix in (0,1,17,59):
                p=bytearray(b'\xff'*64);p[prefix]=0 if write else 1
                if not write:p[prefix+1:prefix+5]=bytes.fromhex('a55a1122')
                value=C.c_uint32();self.assertEqual(self.lib.bridge_wire_response(write,(U8*64).from_buffer_copy(p),C.byref(value)),0)
                if not write:self.assertEqual(value.value,0xa55a1122)
        value=C.c_uint32()
        self.assertEqual(self.lib.bridge_wire_response(False,(U8*64)(*([255]*64)),C.byref(value)),2)
        for prefix,header in ((3,0),(60,1),(63,1),(0,0x80)):
            p=bytearray(b'\xff'*64);p[prefix]=header
            self.assertEqual(self.lib.bridge_wire_response(False,(U8*64).from_buffer_copy(p),C.byref(value)),3)
    def test_real_c_reply_roundtrips_and_host_rejects_wrong_identity_and_crc(self):
        expected=host.request(host.READ,2,b'x'*16,host.SCRATCH);_,r=self.parse(expected)
        output=(U8*128)();digest='a'*64
        self.lib.bridge_response(output,C.byref(r),0,0x1357ace0,12345,digest.encode())
        data=bytes(output)
        self.assertEqual(host.response(data,expected=expected,source_hash=digest),{'value':0x1357ace0,'device_us':12345})
        for i in (6,12,31,44,108,120,124):
            p=bytearray(data);p[i]^=1
            if i!=124:struct.pack_into('<I',p,124,zlib.crc32(p[:124]))
            with self.assertRaises(ValueError):host.response(p,expected=expected,source_hash=digest)
    def test_bridge_layout_policy_does_not_weaken_default_usb_guard(self):
        d=fixture();d[0x1300:0x1300+len(PROFILE)]=bytes(len(PROFILE))
        d[0x1300:0x1300+len(BRIDGE_PROFILE)]=BRIDGE_PROFILE
        with self.assertRaisesRegex(ValueError,'distinct application profile'):inspect_elf(d)
        with self.assertRaisesRegex(ValueError,'bridge implementation symbols'):inspect_elf(d,application='spi-bridge')
        with self.assertRaisesRegex(ValueError,'unknown application'):inspect_elf(fixture(),application='anything')

def assemble(directory):
    pioasm=shutil.which('pioasm')
    if not pioasm or not str(Path(pioasm).resolve()).startswith('/nix/store/'):
        raise RuntimeError('Pinned Nix pioasm required')
    output=Path(directory)/'wire.pio.h'
    subprocess.run([pioasm,'-o','c-sdk','-v','1',str(ROOT/'firmware/forgix-spi-bridge/wire.pio'),str(output)],check=True,capture_output=True,timeout=30)
    text=output.read_text();result={}
    for name in ('request','response'):
        body=re.search(r'forgix_'+name+r'_program_instructions\[\] = \{(.*?)\};',text,re.S).group(1)
        result[name]=[int(x,16) for x in re.findall(r'0x([0-9a-f]{4})',body)]
    return result

class Pio:
    """Only the actual assembled instruction subset, fail on unsupported code."""
    def __init__(self,code,fifo=(),transmit=True):
        self.code=code;self.fifo=list(fifo);self.tx=transmit;self.pc=0;self.x=0;self.y=0
        self.osr=0;self.out_count=32;self.isr=0;self.in_count=0;self.data=0;self.oe=int(transmit)
        self.clk=0;self.delay=0;self.done=False;self.words=[];self.stalled=False
    def step(self,input_bit=1):
        if self.delay:self.delay-=1;return
        if self.done:return
        word=self.code[self.pc];self.clk=(word>>12)&1;self.delay=(word>>8)&15
        op=word>>13;dest=(word>>5)&7;arg=word&31;following=self.pc+1
        if op==4:
            if word&0xff!=0xa0:raise AssertionError('unsupported pull')
            if not self.fifo:self.stalled=True;return
            self.osr=self.fifo.pop(0);self.out_count=0
        elif op==3:
            bits=arg or 32
            if self.out_count>=32 and self.tx:
                if not self.fifo:self.stalled=True;return
                self.osr=self.fifo.pop(0);self.out_count=0
            value=self.osr>>(32-bits);self.osr=(self.osr<<bits)&0xffffffff;self.out_count+=bits
            if dest==1:self.x=value
            elif dest==0 and bits==1:self.data=value
            else:raise AssertionError('unsupported OUT')
        elif op==2:
            if dest!=0 or arg!=1:raise AssertionError('unsupported IN')
            self.isr=((self.isr<<1)|input_bit)&0xffffffff;self.in_count+=1
            if self.in_count==32:self.words.append(self.isr);self.in_count=0;self.isr=0
        elif op==0:
            if dest==2:
                take=self.x!=0;self.x=(self.x-1)&0xffffffff
            elif dest==4:
                take=self.y!=0;self.y=(self.y-1)&0xffffffff
            else:raise AssertionError('unsupported JMP')
            if take:following=arg
        elif op==7:
            if dest==1:self.x=arg
            elif dest==2:self.y=arg
            elif dest==4:self.oe=arg
            else:raise AssertionError('unsupported SET')
        elif op==6:
            if word&0xff not in (0x20,0x21):raise AssertionError('unsupported IRQ')
            self.done=True
        elif op==5:
            if word&0xff!=0x42:raise AssertionError('unsupported MOV')
        else:raise AssertionError('unsupported instruction')
        self.pc=following

class AssembledPio(unittest.TestCase):
    def test_assembled_final_zero_release_and_guard_envelope(self):
        with tempfile.TemporaryDirectory() as temp:code=assemble(temp)
        for wire in (b'\x01\x00\x00\x10\x00',b'\x00\x00\x00\x10\x04\x13\x57\xac\xe0'):
            fifo=[len(wire)*8-1]+[int.from_bytes(wire[i:i+4].ljust(4,b'\0'),'big') for i in range(0,len(wire),4)]
            vm=Pio(code['request'],fifo);rises=[];release=None;bits=[]
            for cycle in range(4000):
                old=vm.clk;oe=vm.oe;vm.step()
                if vm.clk and not old:rises.append(cycle);bits.append(vm.data)
                if oe and not vm.oe:release=cycle
                if vm.done:break
            self.assertTrue(vm.done);self.assertFalse(vm.stalled);self.assertFalse(vm.oe);self.assertEqual(vm.clk,1)
            self.assertEqual(bits,[(b>>n)&1 for b in wire for n in range(7,-1,-1)])
            self.assertEqual(release-rises[-1],17);self.assertGreaterEqual(cycle-rises[-1],72)
            self.assertTrue(all(b-a>=32 for a,b in zip(rises,rises[1:])))

try:
    from migen import Module,Signal,Mux
    from migen.sim import run_simulation,passive
    from forgix_spi_guard import GuardedSPIBone
except ImportError:GuardedSPIBone=None

@unittest.skipUnless(GuardedSPIBone,'Use .#forgix-spi-bridge for actual Migen guard integration')
class PioGuardIntegration(unittest.TestCase):
    def test_actual_pio_read_write_scratch_counter_and_cpu_stall_across_phases(self):
        with tempfile.TemporaryDirectory() as temp:program=assemble(temp)
        for phase in (0,1,4,7):
            from types import SimpleNamespace
            dut=Module();pads=SimpleNamespace(clk=Signal(),cs_n=Signal(reset=1),mosi=Signal())
            rp_oe=Signal();rp_data=Signal();dut.submodules.guard=guard=GuardedSPIBone(pads,with_tristate=False)
            dut.comb+=pads.mosi.eq(Mux(rp_oe,rp_data,Mux(guard.io.oe,guard.io.o,1)))
            state={'done':False,'scratch':0xa55a1122,'counter':0,'requests':[],'pending':False,'delay':0}
            @passive
            def backend():
                while True:
                    state['counter']+=1
                    self.assertFalse((yield rp_oe) and (yield guard.io.oe),'modeled electrical contention')
                    if (yield guard.bus.cyc) and (yield guard.bus.stb):
                        if not state['pending']:
                            state['pending']=True;state['delay']=0
                            state['requests'].append(((yield guard.bus.adr),(yield guard.bus.we),(yield guard.bus.dat_w)))
                        if state['delay']==13 and (yield guard.bus.we):state['scratch']=(yield guard.bus.dat_w)
                        yield guard.bus.ack.eq(state['delay']>=13);state['delay']+=1
                    else:state['pending']=False;yield guard.bus.ack.eq(0)
                    yield guard.bus.dat_r.eq(state['counter'] if (yield guard.bus.adr)==0x400 else state['scratch'])
                    yield
            def driver():
                observed=[]
                for command,address,value in ((0,0x1004,0x1357ace0),(1,0x1004,0),(1,0x1000,0),(1,0x1000,0)):
                    before=len(state['requests'])
                    yield pads.cs_n.eq(1);yield pads.clk.eq(0);yield rp_oe.eq(0)
                    for _ in range(160):yield
                    self.assertTrue((yield guard.qualified))
                    wire=bytes([command])+address.to_bytes(4,'big')+(value.to_bytes(4,'big') if command==0 else b'')
                    fifo=[len(wire)*8-1]+[int.from_bytes(wire[i:i+4].ljust(4,b'\0'),'big') for i in range(0,len(wire),4)]
                    vm=Pio(program['request'],fifo);yield rp_oe.eq(1);yield pads.cs_n.eq(0)
                    for _ in range(32):yield
                    for _ in range(4000):
                        vm.step();yield rp_data.eq(vm.data);yield rp_oe.eq(vm.oe);yield pads.clk.eq(vm.clk);yield
                        if vm.done:break
                    self.assertTrue(vm.done);self.assertFalse((yield guard.io.oe))
                    # Simulate an arbitrarily slow CPU while PIO holds SCK high and DATA input.
                    for _ in range(phase*32):yield
                    self.assertEqual(len(state['requests']),before,'no bus request before the falling handoff')
                    rx=Pio(program['response'],transmit=False)
                    for _ in range(20000):
                        rx.step((yield pads.mosi));yield pads.clk.eq(rx.clk);yield
                        if rx.done:break
                    self.assertTrue(rx.done);self.assertEqual(len(rx.words),16)
                    data=b''.join(w.to_bytes(4,'big') for w in rx.words)
                    prefix=next((i for i,b in enumerate(data) if b!=255),64)
                    self.assertLess(prefix,60);self.assertEqual(data[prefix],command)
                    if command:observed.append(int.from_bytes(data[prefix+1:prefix+5],'big'))
                    yield pads.cs_n.eq(1);yield pads.clk.eq(0);yield
                    self.assertFalse((yield guard.io.oe))
                self.assertEqual(observed[0],0x1357ace0);self.assertGreater(observed[2],observed[1])
                self.assertEqual(len(state['requests']),4);state['done']=True
            run_simulation(dut,{'sys':backend(),'pio':driver()},clocks={'sys':10,'pio':(10,phase)})
            self.assertTrue(state['done'])

if __name__=='__main__':unittest.main()

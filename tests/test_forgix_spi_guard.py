"""Real asynchronous Migen simulation under the prospective RP release contract.

Digital CDC simulation does not establish metastability, pin direction latency,
clock frequency, physical setup/hold, or actual electrical contention safety.
"""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
try:
    from migen import Module, Signal, Mux
    from migen.sim import run_simulation, passive
    from forgix_spi_guard import GuardedSPIBone
except ImportError:GuardedSPIBone = None

if GuardedSPIBone:
    from types import SimpleNamespace
    class Bench(Module):
        def __init__(self):
            self.pads=SimpleNamespace(clk=Signal(),cs_n=Signal(),mosi=Signal())
            self.rp_oe=Signal(reset=1);self.rp_out=Signal()
            self.submodules.guard=GuardedSPIBone(self.pads,with_tristate=False)
            self.comb += self.pads.mosi.eq(Mux(self.rp_oe,self.rp_out,Mux(self.guard.io.oe,self.guard.io.o,1)))

@unittest.skipUnless(GuardedSPIBone,'Use locked Forgix shell for Migen simulation')
class Guard(unittest.TestCase):
    def simulate(self,host,phase=3,delay=0,error=False,idle_ack=False):
        dut=Bench();requests=[];state={'done':False};scratch=0xA55A1122;counter=0
        @passive
        def monitor():
            nonlocal scratch,counter
            pending=False;wait=0;committed=False
            while True:
                counter+=1
                self.assertFalse((yield dut.rp_oe) and (yield dut.guard.io.oe),'synthetic RP/FPGA contention')
                if (yield dut.guard.bus.cyc) and (yield dut.guard.bus.stb):
                    self.assertTrue((yield dut.guard.response_enabled))
                    if not pending:
                        requests.append(((yield dut.guard.bus.adr),(yield dut.guard.bus.we),(yield dut.guard.bus.dat_w)))
                        pending=True;wait=0;committed=False
                    if wait>=delay:
                        if not committed and not error and (yield dut.guard.bus.we):scratch=(yield dut.guard.bus.dat_w)
                        committed=True
                        yield dut.guard.bus.ack.eq(not error);yield dut.guard.bus.err.eq(error)
                    else:wait+=1
                else:
                    pending=False;yield dut.guard.bus.ack.eq(idle_ack);yield dut.guard.bus.err.eq(0)
                yield dut.guard.bus.dat_r.eq(counter if (yield dut.guard.bus.adr)==0x400 else scratch)
                yield
        def process():
            yield from host(dut,requests)
            state['done']=True
        run_simulation(dut,{'sys':monitor(),'host':process()},clocks={'sys':10,'host':(106,phase)})
        self.assertTrue(state['done']);return requests
    def idle(self,dut,cycles=5):
        yield dut.pads.cs_n.eq(1);yield dut.pads.clk.eq(0)
        for _ in range(cycles):yield
    def begin(self,dut):
        yield from self.idle(dut)
        self.assertTrue((yield dut.guard.qualified))
        yield dut.rp_oe.eq(1);yield dut.pads.cs_n.eq(0);yield
    def request(self,dut,command=1,address=0x1000,data=0):
        values=bytes([command])+address.to_bytes(4,'big')+(data.to_bytes(4,'big') if command==0 else b'')
        bits=[(x>>n)&1 for x in values for n in range(7,-1,-1)]
        for i,bit in enumerate(bits):
            yield dut.rp_out.eq(bit);yield
            yield dut.pads.clk.eq(1);yield
            if i!=len(bits)-1:yield dut.pads.clk.eq(0);yield
    def handoff(self,dut,release=1):
        for _ in range(release):yield
        yield dut.rp_oe.eq(0)
        for _ in range(8-release):yield
        self.assertTrue((yield dut.guard.request_complete));self.assertFalse((yield dut.guard.io.oe))
        yield dut.pads.clk.eq(0);yield
        self.assertTrue((yield dut.guard.response_enabled))
    def receive(self,dut,n):
        data=[]
        for _ in range(n):
            value=0
            for _ in range(8):
                yield dut.pads.clk.eq(1);yield
                value=(value<<1)|(yield dut.guard.io.o)
                yield dut.pads.clk.eq(0);yield
            data.append(value)
        return data
    def test_read_and_write_alignment_backpressure_across_async_phases(self):
        for phase in (0,1,4,7):
            for command in (0,1):
                def host(dut,requests):
                    yield from self.begin(dut)
                    yield from self.request(dut,command,0x1004,0x12345678)
                    self.assertEqual(requests,[])
                    yield from self.handoff(dut,release=phase%3)
                    data=yield from self.receive(dut,8)
                    self.assertIn(command,data)
                    index=data.index(command)
                    if command==1:self.assertEqual(data[index+1:index+5],[0xA5,0x5A,0x11,0x22])
                    self.assertEqual(len(requests),1)
                    self.assertEqual(requests[0][:2],(0x401,command==0))
                    if command==0:self.assertEqual(requests[0][2],0x12345678)
                    yield from self.idle(dut)
                    self.assertFalse((yield dut.guard.io.oe))
                with self.subTest(phase=phase,command=command):self.simulate(host,phase,delay=23)
    def test_configuration_tail_glitch_and_clock_high_never_arm(self):
        def host(dut,requests):
            # Simulated configuration bits and 32 zero trailing bytes, CS low.
            for i in range(300):
                yield dut.rp_out.eq(i<44);yield dut.pads.clk.eq(1);yield
                yield dut.pads.clk.eq(0);yield
                self.assertFalse((yield dut.guard.io.oe))
            yield dut.pads.cs_n.eq(1);yield
            yield dut.pads.cs_n.eq(0);yield
            yield from self.request(dut)
            self.assertEqual(requests,[]);self.assertFalse((yield dut.guard.active))
            yield dut.pads.cs_n.eq(1);yield dut.pads.clk.eq(1)
            for _ in range(8):yield
            self.assertFalse((yield dut.guard.qualified))
        self.simulate(host)
    def test_early_clock_and_invalid_command_refuse_without_bus(self):
        for command in (1,0xFF,0x02):
            def host(dut,requests):
                yield from self.begin(dut);yield from self.request(dut,command)
                yield dut.pads.clk.eq(0);yield
                for _ in range(8):yield
                self.assertTrue((yield dut.guard.bad))
                self.assertFalse((yield dut.guard.io.oe));self.assertEqual(requests,[])
                yield from self.idle(dut)
                yield from self.begin(dut);yield from self.request(dut)
                yield from self.handoff(dut)
                data=yield from self.receive(dut,8);self.assertIn(1,data)
            with self.subTest(command=command):self.simulate(host)
    def test_unknown_release_stopped_clock_has_no_output_or_side_effect(self):
        def host(dut,requests):
            yield from self.begin(dut);yield from self.request(dut,0,0x1004,0x55)
            for _ in range(20):yield
            self.assertFalse((yield dut.guard.io.oe));self.assertEqual(requests,[])
            yield from self.idle(dut)
        self.simulate(host)
    def test_raw_cs_abort_and_idle_ack_do_not_advance_guarded_core(self):
        def host(dut,requests):
            yield from self.begin(dut)
            # Idle external ACK must not reach core while bus gate is closed.
            yield from self.request(dut,0,0x1004,0x55)
            for _ in range(4):yield
            self.assertEqual(requests,[]);self.assertFalse((yield dut.guard.io.oe))
            yield from self.handoff(dut)
            self.assertTrue((yield dut.guard.io.oe))
            yield dut.pads.cs_n.eq(1)
            # Combinational OE drop is checked before the next sys sync edge.
            yield dut.pads.clk.eq(0);yield
            self.assertFalse((yield dut.guard.io.oe));self.assertFalse((yield dut.guard.bus.cyc))
            yield from self.idle(dut)
        self.simulate(host,delay=1000,idle_ack=True)
    def test_repeated_scratch_write_read_and_counter_reads(self):
        def host(dut,requests):
            observed=[]
            for cmd,address,value in ((0,0x1004,0x1357ACE0),(1,0x1004,0),(1,0x1000,0),(1,0x1000,0)):
                yield from self.begin(dut);yield from self.request(dut,cmd,address,value)
                yield from self.handoff(dut)
                data=yield from self.receive(dut,8)
                index=data.index(cmd)
                self.assertTrue(all(x==0xFF for x in data[:index]))
                if cmd:observed.append(int.from_bytes(bytes(data[index+1:index+5]),'big'))
                yield from self.idle(dut)
            self.assertEqual(observed[0],0x1357ACE0)
            self.assertGreater(observed[2],observed[1]);self.assertEqual(len(requests),4)
        self.simulate(host,phase=6,delay=19)
    def test_abort_partial_request_and_completed_write_has_no_rollback(self):
        def host(dut,requests):
            yield from self.begin(dut)
            for _ in range(12):
                yield dut.pads.clk.eq(1);yield
                yield dut.pads.clk.eq(0);yield
            yield from self.idle(dut);self.assertEqual(requests,[])
            yield from self.begin(dut);yield from self.request(dut,0,0x1004,0x55667788)
            yield from self.handoff(dut)
            for _ in range(5):yield
            self.assertEqual(len(requests),1)
            yield from self.idle(dut)
            yield from self.begin(dut);yield from self.request(dut,1,0x1004)
            yield from self.handoff(dut)
            data=yield from self.receive(dut,8);index=data.index(1)
            self.assertEqual(data[index+1:index+5],[0x55,0x66,0x77,0x88])
            yield from self.idle(dut)
        self.simulate(host,delay=7)
    def test_error_response_is_not_distinguished_from_ack(self):
        def host(dut,requests):
            yield from self.begin(dut);yield from self.request(dut)
            yield from self.handoff(dut)
            data=yield from self.receive(dut,8);self.assertIn(1,data)
            self.assertEqual(len(requests),1)
            yield from self.idle(dut)
        self.simulate(host,error=True)

if __name__=='__main__':unittest.main()

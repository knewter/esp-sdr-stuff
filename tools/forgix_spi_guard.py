"""Prospective SPIBone three-pin guard; simulation is not electrical admission.

Uses unmodified LiteX 8c01073 SPIBone(wires=4, with_tristate=False):
https://github.com/enjoy-digital/litex/blob/8c01073afb71aa0a0709f02f8e24247589e8f5e4/litex/soc/cores/spi/spi_bone.py#L121

RP contract in *system cycles*: CS high/SCK low >=40 to qualify (32 stable
synchronized samples); CS-low setup >=8; SCK half-period >=8. Last request
rising edge is followed by SCK held high, final data held through capture,
RP MOSI held >=8 cycles after the final physical rising edge and released
within32 cycles of capture; the falling handoff edge occurs >=72 cycles after
that rising edge. FPGA enforces64 cycles after its request capture and
refuses an earlier falling edge. RP stays input through all responses and
CS-high >=40 before reacquiring MOSI. Unknown release => hold SCK, no handoff.
These are prospective constraints, not measured RP latency/clock bounds.
Neither the FPGA nor this simulation can sense an external pin's high-Z.
CS abort immediately gates outputs/requests but cannot undo an issued write.
"""
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace
from migen import Signal, If, Cat
from migen.fhdl.specials import TSTriple
from migen.genlib.cdc import MultiReg
from litex.gen import LiteXModule
from litex.soc.cores.spi.spi_bone import SPIBone
from litex.soc.interconnect import wishbone

ARM_CYCLES = 32
TURN_CYCLES = 64
SPIBONE_SHA256 = '0bbefa902db7ae943dc6121c9508672ccbabfee44befe501ac903f196bc4c5d5'


class GuardedSPIBone(LiteXModule):
    def __init__(self, pads, wires=3, with_tristate=True):
        if wires != 3:raise ValueError('Guard is fixed to three physical SPI wires')
        if hashlib.sha256(Path(inspect.getfile(SPIBone)).read_bytes()).hexdigest() != SPIBONE_SHA256:
            raise ValueError('Unreviewed upstream SPIBone bytes')
        self.io = io = TSTriple()
        if with_tristate:self.specials += io.get_tristate(pads.mosi)
        else:self.comb += io.i.eq(pads.mosi) # simulation observes identical logic without resolving a pad
        clk = Signal(); cs = Signal(); mosi = Signal(); previous = Signal()
        self.specials += [MultiReg(pads.clk, clk), MultiReg(pads.cs_n, cs), MultiReg(io.i, mosi)]
        self.sync += previous.eq(clk)
        rise = Signal(); fall = Signal()
        self.comb += [rise.eq(clk & ~previous), fall.eq(~clk & previous)]
        self.qualified = qualified = Signal()
        self.active = active = Signal()
        self.bad = bad = Signal()
        self.request_complete = done = Signal()
        self.response_enabled = enabled = Signal()
        idle = Signal(max=ARM_CYCLES)
        guard = Signal(max=TURN_CYCLES + 1)
        count = Signal(max=73)
        command = Signal(8); write = Signal()
        self.sync += [
            If(pads.cs_n,
                active.eq(0), bad.eq(0), done.eq(0), enabled.eq(0),
                guard.eq(0), count.eq(0), command.eq(0), write.eq(0)
            ).Elif(~active,
                If(qualified & ~cs, active.eq(1), qualified.eq(0))
            ).Elif(~bad & ~done & rise,
                count.eq(count + 1),
                If(count < 8, command.eq(Cat(mosi, command[:7]))),
                If(count == 7,
                    If((Cat(mosi, command[:7]) != 0) & (Cat(mosi, command[:7]) != 1), bad.eq(1)),
                    write.eq(Cat(mosi, command[:7]) == 0)
                ),
                If(((count == 39) & ~write) | ((count == 71) & write), done.eq(1), guard.eq(0))
            ).Elif(done & ~bad & ~enabled,
                If(fall,
                    If(guard == TURN_CYCLES, enabled.eq(1)).Else(bad.eq(1))
                ).Elif(guard < TURN_CYCLES, guard.eq(guard + 1))
            ),
            If(pads.cs_n & cs & ~pads.clk & ~clk,
                If(idle == ARM_CYCLES - 1, qualified.eq(1)).Else(idle.eq(idle + 1))
            ).Elif(pads.cs_n, idle.eq(0), qualified.eq(0)).Else(idle.eq(0))
        ]
        proxy = SimpleNamespace(clk=Signal(), cs_n=Signal(reset=1), mosi=Signal(), miso=Signal())
        self.core = core = SPIBone(proxy, wires=4, with_tristate=False)
        self.comb += [proxy.cs_n.eq(pads.cs_n | ~active | bad),
                      proxy.clk.eq(pads.clk & active & ~bad), proxy.mosi.eq(io.i)]
        permitted = Signal()
        self.comb += [permitted.eq(enabled & active & ~bad & ~pads.cs_n),
                      io.oe.eq(permitted), io.o.eq(proxy.miso)]
        self.bus = bus = wishbone.Interface(address_width=32, data_width=32, addressing='word')
        self.comb += [bus.adr.eq(core.bus.adr), bus.dat_w.eq(core.bus.dat_w), bus.sel.eq(core.bus.sel),
                      bus.we.eq(core.bus.we), bus.cti.eq(core.bus.cti), bus.bte.eq(core.bus.bte),
                      bus.cyc.eq(core.bus.cyc & permitted), bus.stb.eq(core.bus.stb & permitted),
                      core.bus.ack.eq(bus.ack & permitted), core.bus.err.eq(bus.err & permitted),
                      core.bus.dat_r.eq(bus.dat_r)]

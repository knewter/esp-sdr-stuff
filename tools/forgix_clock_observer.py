"""Unregistered one-way observer and digital clock-ratio interval.

No compiler, device or load entrypoint. See the prospective observer protocol.
"""
from fractions import Fraction
from migen import Module, Signal, If
from migen.fhdl.specials import TSTriple
from migen.genlib.cdc import MultiReg

DIVISOR = 1024
BURST_PERIODS = 1024
ARM_CYCLES = 32
SAMPLES = 16
PIO_UNCERTAINTY = 16  # Digital instruction/sampling envelope, not pad timing.


class ClockObserver(Module):
    def __init__(self, pads, *, with_tristate=True, divisor=DIVISOR,
                 periods=BURST_PERIODS, arm_cycles=ARM_CYCLES):
        for value in (divisor, periods, arm_cycles):
            if type(value) is not int or value < 2:
                raise ValueError('Positive integer observer geometry required')
        if divisor < 4 or divisor & (divisor-1):
            raise ValueError('Observer divisor must be a power of two >=4')
        if divisor*periods > 1 << 24 or arm_cycles > 1024:
            raise ValueError('Observer geometry exceeds finite counter bounds')
        self.io = io = TSTriple()
        if with_tristate:
            self.specials += io.get_tristate(pads.mosi)
        else:
            self.comb += io.i.eq(pads.mosi)
        cs = Signal(); sck = Signal()
        self.specials += [MultiReg(pads.cs_n, cs), MultiReg(pads.clk, sck)]
        self.cold = cold = Signal(reset=1)
        self.qualified = qualified = Signal()
        self.active = active = Signal()
        self.spent = spent = Signal()
        self.complete = complete = Signal()
        self.aborted = aborted = Signal()
        idle = Signal(max=arm_cycles)
        total = divisor*periods
        tail = divisor//2
        self.cycles = cycles = Signal(max=total+tail)
        self.comb += [
            io.oe.eq(active & ~pads.cs_n & ~pads.clk & ~cold),
            io.o.eq((cycles < total) & cycles[divisor.bit_length()-2])]
        self.sync += [
            cold.eq(0),
            If(cold,
                idle.eq(0), qualified.eq(0), active.eq(0), spent.eq(0),
                complete.eq(0), aborted.eq(0), cycles.eq(0)
            ).Elif(active,
                If(pads.cs_n | pads.clk,
                    active.eq(0), aborted.eq(1)
                ).Elif(cycles == total+tail-1,
                    active.eq(0), complete.eq(1)
                ).Else(cycles.eq(cycles+1))
            ).Elif(~spent,
                If(pads.cs_n & cs & ~pads.clk & ~sck,
                    If(idle == arm_cycles-1, qualified.eq(1))
                    .Else(idle.eq(idle+1))
                ).Elif(~pads.cs_n & qualified & ~pads.clk,
                    idle.eq(0),
                    If(~cs & ~sck,
                        qualified.eq(0), spent.eq(1), active.eq(1), cycles.eq(0))
                ).Else(idle.eq(0), qualified.eq(0))
            )]


def ratio_interval(decrements):
    """Exact digital FPGA/PIO interval; no absolute-frequency conversion.

Samples may be nonconsecutive. A propagated constant edge delay cancels between
like edges; unverified variable pad/synchronizer delays are outside this bound.
"""
    if type(decrements) not in (tuple, list) or len(decrements) != SAMPLES:
        raise ValueError('Exactly 16 complete period samples required')
    bounds = []
    for n in decrements:
        if type(n) is not int or not 8 < n < 0x7fffffff:
            raise ValueError('Zero, impossible or overflowed period count')
        low, high = 2*n-PIO_UNCERTAINTY, 2*n+PIO_UNCERTAINTY
        bounds.append((Fraction(DIVISOR, high), Fraction(DIVISOR, low)))
    lower = max(a for a, _ in bounds)
    upper = min(z for _, z in bounds)
    if lower > upper:
        raise ValueError('Inconsistent clock period intervals')
    return {'kind': 'digital FPGA/PIO frequency ratio',
            'lower': [lower.numerator, lower.denominator],
            'upper': [upper.numerator, upper.denominator],
            'samples': SAMPLES, 'divisor': DIVISOR,
            'pio_instruction_uncertainty': PIO_UNCERTAINTY,
            'calibrated_absolute_frequency': False,
            'physical_timing_qualified': False}

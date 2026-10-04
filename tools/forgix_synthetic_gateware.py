#!/usr/bin/env python3
"""Generate private source+guarded SoC RTL only; no vendor, load or hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CORE = 'firmware/forgix-synthetic-source/source.v'
BASE = 0x10000
SYSTEM_HZ = 32000000
INPUTS = (CORE, 'tools/forgix_synthetic_gateware.py', 'tools/forgix_fpga_candidate.py',
          'tools/forgix_spi_guard.py', 'flake.nix', 'flake.lock', 'nix/forgix-toolchain.nix')
REGISTERS = {
    'abi': 0x00, 'system_hz_requested': 0x04, 'capacities': 0x08, 'control': 0x0c,
    'period_config': 0x10, 'target_config': 0x14,
    'nonce0': 0x18, 'nonce1': 0x1c, 'nonce2': 0x20, 'nonce3': 0x24,
    'state': 0x28, 'level': 0x2c, 'high_water': 0x30,
    'head_sequence': 0x34, 'head_tick': 0x38, 'head_pattern': 0x3c,
    'pop_expected_sequence': 0x40, 'head_crc': 0x44, 'popped_live': 0x48,
    'snapshot_id': 0x4c, 'snapshot_tick_lo': 0x50, 'snapshot_tick_hi': 0x54,
    'snapshot_state': 0x58, 'generated': 0x5c, 'enqueued': 0x60,
    'full_dropped': 0x64, 'popped': 0x68, 'refused_pop': 0x6c,
    'refused_command': 0x70, 'remaining': 0x74, 'snapshot_high_water': 0x78,
    'start_lo': 0x7c, 'start_hi': 0x80, 'stop_lo': 0x84, 'stop_hi': 0x88,
    'pause_begin_lo': 0x8c, 'pause_begin_hi': 0x90,
    'pause_end_lo': 0x94, 'pause_end_hi': 0x98,
}


def committed_inputs():
    hashes = {}
    for name in INPUTS:
        recorded = subprocess.check_output(['git', 'show', 'HEAD:'+name], cwd=ROOT, timeout=10)
        actual = (ROOT/name).read_bytes()
        if actual != recorded:
            raise ValueError('Commit synthetic RTL and generator sources before generation')
        hashes[name] = hashlib.sha256(actual).hexdigest()
    return hashes


def make_soc(platform_class):
    from migen import ClockSignal, ResetSignal, Signal, Instance, Cat, Constant
    from litex.gen import LiteXModule
    from litex.soc.interconnect import wishbone
    from litex.soc.integration.soc import SoCRegion
    import forgix_fpga_candidate as existing

    class Source(LiteXModule):
        def __init__(self):
            self.bus = bus = wishbone.Interface(address_width=32, data_width=32, addressing='word')
            # The old SoC reset defaults low. Reset-only raw Verilog registers
            # must see a deterministic initial clock edge instead of relying
            # on device-specific, unstated configuration initialization.
            initial_reset = Signal(reset=1)
            self.sync += initial_reset.eq(0)
            self.specials += Instance('forgix_synthetic_source', p_SYSTEM_HZ=SYSTEM_HZ,
                i_clk=ClockSignal(), i_reset=ResetSignal() | initial_reset,
                i_wb_cyc=bus.cyc, i_wb_stb=bus.stb, i_wb_we=bus.we,
                i_wb_addr=Cat(Constant(0, 2), bus.adr[:10]),
                i_wb_data_in=bus.dat_w, i_wb_sel=bus.sel,
                o_wb_ack=bus.ack, o_wb_err=bus.err, o_wb_data_out=bus.dat_r)

    # Original generator/CSR bank and GuardedSPIBone are reused unchanged.
    soc = existing.make_soc(platform_class)
    soc.synthetic_source = Source()
    soc.bus.add_slave('synthetic_source', soc.synthetic_source.bus,
                      SoCRegion(origin=BASE, size=0x1000, cached=False))
    soc.platform.add_source(str(ROOT/CORE))
    return soc


def generate(output):
    from litex.build.generic_platform import GenericPlatform
    from litex_boards.platforms import adiuvo_forgix as board
    import forgix_fpga_candidate as existing
    hashes = committed_inputs()
    output = Path(output)
    if not output.is_absolute():
        output = ROOT/output
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('Fresh nonsymlink output required')
    output = output.resolve()
    if not output.is_relative_to(ROOT/'.scratch'):
        raise ValueError('Private ignored .scratch output required')

    class Platform(GenericPlatform):
        default_clk_freq = SYSTEM_HZ
        def __init__(self):
            super().__init__('T8F49I2', board._io, board._connectors)
        def do_finalize(self, fragment):
            pass

    soc = make_soc(Platform)
    soc.finalize()
    conversion = soc.platform.get_verilog(soc.get_fragment(), name='forgix_synthetic_top')
    pins = {name: pins for name, pins, others, res in soc.platform.resolve_signals(conversion.ns)[0]}
    if pins != existing.PINS:
        raise ValueError('Synthetic image changed the guarded four-pin boundary')
    if soc.csr_regions['registers'].origin != 0x1000:
        raise ValueError('Original register CSR map changed')
    output.mkdir(mode=0o700)
    previous = Path.cwd()
    try:
        os.chdir(output)
        conversion.write('forgix_synthetic_top.v')
        (output/'source.v').write_bytes((ROOT/CORE).read_bytes())
    finally:
        os.chdir(previous)
    artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    receipt = {
        'schema': 1, 'kind': 'RTL-only finite synthetic FPGA source preparation',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'inputs_sha256': hashes, 'artifacts_sha256': artifacts,
        'requested_system_hz': SYSTEM_HZ, 'registers': {k: BASE+v for k, v in REGISTERS.items()},
        'original_counter_address': 0x1000, 'original_scratch_address': 0x1004,
        'pins': pins, 'fifo_records': 64, 'record_bytes': 16,
        'offered_record_bytes_s': [256, 1024, 2048],
        'guard_half_period_min_system_cycles': 8,
        'vendor_executed': False, 'hardware_opened': False, 'loading_admitted': False,
        'limits': 'Generated RTL only. No timing closure, resource fit, grade/clock/pad qualification, RP stream image, host collector, sustained payload or recovery proof.'}
    (output/'manifest.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output', required=True, type=Path)
    args = cli.parse_args()
    os.umask(0o077)
    generate(args.output)
    print('Private synthetic RTL generated; no vendor compiler or hardware invoked.')


if __name__ == '__main__':
    main()

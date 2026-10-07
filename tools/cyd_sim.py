#!/usr/bin/env python3
"""Render the CYD waterfall UI in a host simulator (simulation, not hardware).

Compiles firmware/cyd-waterfall/src with tests/cyd_sim/sim.c (emulated
ILI9341 panel, XPT2046 touch, synthetic radio, simulated time) and writes PNG
screenshots of scripted scenarios, plus a side-by-side contact sheet.
Requires a host C compiler (cc) and zlib only.
"""
import argparse
import ctypes
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT/'firmware'/'cyd-waterfall'/'src'
SIM = ROOT/'tests'/'cyd_sim'
W, H = 240, 320


def build(out_dir):
    lib = Path(out_dir)/'cyd_sim.so'
    subprocess.run(['cc', '-O2', '-shared', '-fPIC', '-std=gnu11', '-D_DEFAULT_SOURCE', '-Wall', '-Werror',
                    '-Wno-unused-function', '-I', str(SIM/'include'), '-I', str(SRC), '-o', str(lib),
                    str(SIM/'sim.c'), str(SRC/'cyd_display.c'), str(SRC/'cyd_waterfall_logic.c'), '-lm'],
                   check=True)
    return Simulator(ctypes.CDLL(str(lib)))


class Simulator:
    def __init__(self, c):
        self.c = c
        for name in ('sim_frequency', 'sim_acquisitions', 'sim_pixels_written', 'sim_gain', 'sim_filter'):
            getattr(c, name).restype = ctypes.c_uint

    def boot(self, hold=False):
        self.c.sim_hold_touch_at_boot(int(hold))
        self.c.sim_boot()
        self.c.sim_hold_touch_at_boot(0)

    def run(self, ms):
        self.c.sim_run_ms(int(ms))

    def tap(self, x, y, hold_ms=120):
        self.c.sim_touch(int(x), int(y), int(hold_ms))

    def host(self):
        self.c.sim_host_line()

    def source(self, on):
        self.c.sim_set_ble_source(int(on))

    @property
    def frequency(self):
        return self.c.sim_frequency()

    def screen(self):
        buf = (ctypes.c_uint16*(W*H))()
        self.c.sim_screen(buf)
        return list(buf)


def rgb(v):
    return ((v >> 11 & 31)*255//31, (v >> 5 & 63)*255//63, (v & 31)*255//31)


def png(path, pixels, width, height, scale=2):
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row += bytes(rgb(pixels[y*width+x]))*scale
        rows.append(bytes(row)*scale)
    raw = b''.join(rows)
    chunk = lambda kind, data: struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', width*scale, height*scale, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 9))+chunk(b'IEND', b''))


def sheet(path, screens, gap=8):
    width = len(screens)*W+(len(screens)-1)*gap
    pixels = [0x2104]*(width*H)
    for k, s in enumerate(screens):
        x0 = k*(W+gap)
        for y in range(H):
            pixels[y*width+x0:y*width+x0+W] = s[y*W:(y+1)*W]
    png(path, pixels, width, H, scale=2)


# Menu cell centres (5x3 grid over the waterfall, y 92..263).
def menu_cell(i):
    r, c = divmod(i, 3)
    return 40+c*80, 92+r*172//5+17


SCENARIOS = [
    ('01-boot', lambda s: s.run(3000)),
    ('02-menu', lambda s: s.tap(210, 290)),
    ('03-ble37', lambda s: (s.tap(*menu_cell(0)), s.run(6000))),
    ('04-cursor', lambda s: (s.tap(169, 180), s.run(1500))),
    ('05-band', lambda s: (s.tap(210, 290), s.tap(*menu_cell(6)), s.run(4000))),
    ('06-flat', lambda s: (s.tap(210, 290), s.tap(*menu_cell(14)), s.tap(210, 290), s.run(4000))),
    ('07-host', lambda s: (s.host(), s.run(50))),
]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output', type=Path, required=True)
    a = cli.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        sim = build(tmp)
        sim.boot()
        screens = []
        for name, step in SCENARIOS:
            step(sim)
            screen = sim.screen()
            screens.append(screen)
            png(a.output/f'{name}.png', screen, W, H)
            print(f'{name}: LO {sim.frequency} MHz')
        sheet(a.output/'sheet.png', screens)


if __name__ == '__main__':
    main()

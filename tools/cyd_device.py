#!/usr/bin/env python3
"""Screenshots, measurements and virtual taps from the CYD waterfall build.

Talks to the display's own commands (CYDSHOT, CYDSTAT, CYDSTATRESET, CYDTAP),
which do not pause the display. Opening the CH340 port resets the board, so
the tool waits for the boot line and a settle period first. One operator owns
the port; it is closed when the tool exits.

  cyd_device.py tour --output DIR     screens of each main view plus stats
  cyd_device.py shot --output FILE    one screenshot
  cyd_device.py stat                  one measurement line
"""
import argparse
import json
import re
from pathlib import Path
import sys
import time
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cyd_sim import png, menu_cell, W, H, HOME_TILES, HOME_BUTTON, LIVE  # noqa: E402

PORT = '/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0'


def parse_shot(data):
    """Bytes after the CYD SHOT header line -> (RGB565 pixels, crc_ok, rest)."""
    head_end = data.index(b'\n')
    head = data[:head_end].decode().split()
    width, height, row = int(head[2]), int(head[3]), int(head[4])
    body = data[head_end+1:head_end+1+height*row]
    tail = data[head_end+1+height*row:]
    end = tail[:tail.index(b'\n')].decode().split()
    crc_ok = end[:3] == ['CYD', 'SHOT', 'END'] and int(end[3], 16) == zlib.crc32(body)
    pixels = []
    for y in range(height):
        r = body[y*row+1:(y+1)*row]                       # skip the dummy byte
        for x in range(width):
            red, green, blue = r[3*x], r[3*x+1], r[3*x+2]
            pixels.append((red >> 3) << 11 | (green >> 2) << 5 | blue >> 3)
    return pixels, crc_ok, tail[tail.index(b'\n')+1:]


class Device:
    def __init__(self, port=PORT, settle_s=5.0):
        import serial
        self.port = serial.Serial(port=None, baudrate=921600, timeout=0.2, exclusive=True)
        self.port.dtr = self.port.rts = False
        self.port.port = port
        self.port.open()
        self.buffer = b''
        deadline = time.monotonic()+10
        while b'#CYD panel' not in self.buffer and time.monotonic() < deadline:
            self.buffer += self.port.read(4096)
        found = re.search(rb'#CYD panel[^\r\n]*', self.buffer)
        self.boot_line = found.group(0).decode(errors='replace') if found else ''
        time.sleep(settle_s)
        self.port.reset_input_buffer()
        self.buffer = b''

    def close(self):
        self.port.close()

    def _until(self, marker, timeout=10):
        deadline = time.monotonic()+timeout
        while marker not in self.buffer and time.monotonic() < deadline:
            self.buffer += self.port.read(65536)
        if marker not in self.buffer:
            raise TimeoutError(marker)

    def command(self, line, timeout=5):
        self.buffer = b''
        self.port.write(line.encode()+b'\n')
        self._until(b'CYD ', timeout)
        self._until(b'\n', timeout)
        start = self.buffer.index(b'CYD ')
        reply = self.buffer[start:self.buffer.index(b'\n', start)].decode()
        if reply.startswith('CYD ERR'):
            raise RuntimeError(reply)
        return reply

    def stat(self):
        return json.loads(self.command('CYDSTAT')[len('CYD STAT '):])

    def tap(self, x, y, ms=150):
        self.command(f'CYDTAP {x} {y} {ms}')
        time.sleep(ms/1000+0.3)

    def shot(self, attempts=3):
        # The CH340 link can drop bytes under host load; a bad frame fails its
        # CRC or loses its header, so retry a few times.
        for attempt in range(attempts):
            self.buffer = b''
            self.port.write(b'CYDSHOT\n')
            try:
                self._until(b'CYD SHOT END', timeout=30)
                self._until(b'\n', timeout=5)
                start = self.buffer.index(b'CYD SHOT ')
                pixels, ok, _ = parse_shot(self.buffer[start:])
                if ok:
                    return pixels
            except (ValueError, IndexError, TimeoutError):
                pass
            time.sleep(0.5)
            self.port.reset_input_buffer()
        raise RuntimeError(f'screenshot failed after {attempts} attempts')


TOUR = [
    ('01-home', [], 1.0),
    ('02-live', [HOME_TILES['live']], 6.0),
    ('03-more', [LIVE['more']], 1.0),
    ('04-band', [menu_cell(6)], 6.0),
    ('05-ble37', [LIVE['more'], menu_cell(0)], 6.0),
    ('06-wifi', [LIVE['home'], HOME_TILES['wifi']], 25.0),
    ('07-bluetooth', [HOME_BUTTON, HOME_TILES['bluetooth']], 25.0),
    ('08-settings', [HOME_BUTTON, HOME_TILES['settings']], 1.0),
    ('09-help', [HOME_BUTTON, HOME_TILES['help']], 1.0),
]


def main():
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument('action', choices=['tour', 'shot', 'stat'])
    cli.add_argument('--output', type=Path)
    cli.add_argument('--port', default=PORT)
    a = cli.parse_args()
    device = Device(a.port)
    try:
        print(device.boot_line)
        if a.action == 'stat':
            print(json.dumps(device.stat()))
        elif a.action == 'shot':
            png(a.output, device.shot(), W, H)
        else:
            a.output.mkdir(parents=True, exist_ok=True)
            report = {'boot': device.boot_line, 'views': []}
            for name, taps, dwell in TOUR:
                for x, y in taps:
                    device.tap(x, y)
                device.command('CYDSTATRESET')
                time.sleep(dwell)
                stat = device.stat()
                t0 = time.monotonic()
                png(a.output/f'{name}.png', device.shot(), W, H)
                stat['screenshot_s'] = round(time.monotonic()-t0, 2)
                report['views'].append({'view': name, **stat})
                print(name, json.dumps(stat))
            (a.output/'measurements.json').write_text(json.dumps(report, indent=2)+'\n')
    finally:
        device.close()


if __name__ == '__main__':
    main()

"""Host tests for the CYD waterfall's hardware-free logic (compiled C via ctypes)."""
import ctypes
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'firmware'/'cyd-waterfall'/'src'/'cyd_waterfall_logic.c'
COLUMNS, RATE = 240, 16_000_000
TARGETS = ['NONE', 'DOWN', 'STEP', 'UP', 'LABEL', 'WATERFALL']


def word(i, q):
    return (int(i) & 0x3ff) | ((int(q) & 0x3ff) << 10)


@unittest.skipUnless(shutil.which('cc'), 'needs a C compiler')
class Logic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib = Path(cls.tmp.name)/'logic.so'
        subprocess.run(['cc', '-O2', '-shared', '-fPIC', '-std=c11', '-D_DEFAULT_SOURCE', '-Wall', '-Werror',
                        '-o', str(lib), str(SOURCE), '-lm'], check=True)
        cls.c = ctypes.CDLL(str(lib))
        cls.c.cyd_row_db.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint, ctypes.POINTER(ctypes.c_float)]
        cls.c.cyd_floor_update.restype = ctypes.c_float
        cls.c.cyd_floor_update.argtypes = [ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_bool]
        cls.c.cyd_level.restype = ctypes.c_uint8
        cls.c.cyd_level.argtypes = [ctypes.c_float, ctypes.c_float]
        cls.c.cyd_palette.restype = ctypes.c_uint16
        cls.c.cyd_unpack.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def row(self, words):
        data = (ctypes.c_uint32*len(words))(*words)
        out = (ctypes.c_float*COLUMNS)()
        blocks = self.c.cyd_row_db(data, len(words), out)
        return blocks, list(out)

    def tone(self, offset_hz, n=4096, amplitude=200, burst=None):
        words = []
        for k in range(n):
            on = burst is None or burst[0] <= k < burst[1]
            a = 2*math.pi*offset_hz*k/RATE
            words.append(word(amplitude*math.cos(a)*on, amplitude*math.sin(a)*on))
        return words

    def test_unpack_is_signed_ten_bit(self):
        i, q = ctypes.c_float(), ctypes.c_float()
        self.c.cyd_unpack(word(-512, 511), ctypes.byref(i), ctypes.byref(q))
        self.assertEqual((i.value, q.value), (-512, 511))
        self.c.cyd_unpack(word(-1, 3) | 0xfff00000, ctypes.byref(i), ctypes.byref(q))
        self.assertEqual((i.value, q.value), (-1, 3))

    def test_tone_lands_in_its_column(self):
        for offset in (-6e6, -2e6, 0.5e6, 4e6):
            blocks, db = self.row(self.tone(offset))
            self.assertEqual(blocks, 8)
            expected = int((offset+8e6)/16e6*COLUMNS)
            self.assertLessEqual(abs(db.index(max(db))-expected), 1, offset)

    def test_short_burst_survives_max_hold(self):
        _, db = self.row(self.tone(3e6, burst=(1024, 1536)))
        peak = db.index(max(db))
        self.assertLessEqual(abs(peak-int((3e6+8e6)/16e6*COLUMNS)), 1)
        self.assertGreater(max(db)-sorted(db)[COLUMNS//4], 20)

    def test_dc_offset_is_removed(self):
        words = [word(100, -60)]*4096
        _, db = self.row(words)
        self.assertLess(max(db)-min(db), 1.0)

    def test_floor_tracks_slowly(self):
        row = (ctypes.c_float*COLUMNS)(*([10.0]*COLUMNS))
        first = self.c.cyd_floor_update(0.0, row, True)
        self.assertAlmostEqual(first, 10.0)
        row2 = (ctypes.c_float*COLUMNS)(*([30.0]*COLUMNS))
        self.assertAlmostEqual(self.c.cyd_floor_update(first, row2, False), 11.0, places=4)

    def test_level_and_palette_ends(self):
        self.assertEqual(self.c.cyd_level(5.0, 10.0), 0)
        self.assertEqual(self.c.cyd_level(40.0, 10.0), 255)
        self.assertEqual(self.c.cyd_level(25.0, 10.0), 127)
        self.assertEqual(self.c.cyd_palette(0), 0x0000)
        self.assertEqual(self.c.cyd_palette(255), 0xffff)

    def test_column_to_frequency(self):
        self.assertEqual(self.c.cyd_column_mhz(2425, 0), 2417)
        self.assertEqual(self.c.cyd_column_mhz(2425, 120), 2425)
        self.assertEqual(self.c.cyd_column_mhz(2425, 239), 2433)

    def test_touch_targets(self):
        target = lambda x, y: TARGETS[self.c.cyd_touch_target(x, y)]
        self.assertEqual(target(100, 5), 'LABEL')
        self.assertEqual(target(200, 5), 'NONE')
        self.assertEqual(target(10, 50), 'DOWN')
        self.assertEqual(target(120, 25), 'STEP')
        self.assertEqual(target(230, 59), 'UP')
        self.assertEqual(target(120, 60), 'WATERFALL')
        self.assertEqual(target(120, 200), 'WATERFALL')
        self.assertEqual(target(-1, 200), 'NONE')

    def test_touch_map_clamps(self):
        x, y = ctypes.c_int(), ctypes.c_int()
        self.c.cyd_touch_map(0, 5000, ctypes.byref(x), ctypes.byref(y))
        self.assertEqual((x.value, y.value), (0, 319))
        self.c.cyd_touch_map(1950, 2020, ctypes.byref(x), ctypes.byref(y))
        self.assertEqual((x.value, y.value), (120, 160))


if __name__ == '__main__':
    unittest.main()

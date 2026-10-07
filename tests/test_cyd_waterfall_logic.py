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

    class Cal(ctypes.Structure):
        _fields_ = [(n, ctypes.c_int) for n in ('swap', 'u0', 'u1', 'v0', 'v2')]

    def calibrate(self, raw):
        cal = self.Cal()
        arr = ((ctypes.c_int*2)*3)(*[(ctypes.c_int*2)(*r) for r in raw])
        self.c.cyd_touch_calibrate.restype = ctypes.c_bool
        ok = self.c.cyd_touch_calibrate(arr, ctypes.byref(cal))
        return ok, cal

    def mapped(self, cal, rx, ry):
        x, y = ctypes.c_int(), ctypes.c_int()
        self.c.cyd_touch_map(ctypes.byref(cal), rx, ry, ctypes.byref(x), ctypes.byref(y))
        return x.value, y.value

    def test_calibration_recovers_swapped_flipped_axes(self):
        # Raw X channel runs down the screen (inverted), raw Y runs across.
        raw = lambda sx, sy: (3800-sy*10, 300+sx*12)
        ok, cal = self.calibrate([raw(20, 20), raw(220, 20), raw(20, 300)])
        self.assertTrue(ok)
        self.assertEqual(cal.swap, 1)
        for sx, sy in ((20, 20), (120, 160), (220, 300), (60, 250)):
            x, y = self.mapped(cal, *raw(sx, sy))
            self.assertLessEqual(abs(x-sx), 1)
            self.assertLessEqual(abs(y-sy), 1)

    def test_calibration_plain_axes_and_clamp(self):
        raw = lambda sx, sy: (200+sx*14, 240+sy*11)
        ok, cal = self.calibrate([raw(20, 20), raw(220, 20), raw(20, 300)])
        self.assertTrue(ok)
        self.assertEqual(cal.swap, 0)
        self.assertEqual(self.mapped(cal, *raw(120, 160)), (120, 160))
        self.assertEqual(self.mapped(cal, 0, 0), (0, 0))
        self.assertEqual(self.mapped(cal, 4095, 4095), (239, 319))

    def test_baked_default_matches_measured_board(self):
        cal = self.Cal.in_dll(self.c, 'cyd_cal_default')
        self.assertEqual((cal.swap, cal.u0, cal.u1, cal.v0, cal.v2), (0, 3491, 537, 470, 3636))
        # The calibration taps themselves land on the crosses.
        self.assertEqual(self.mapped(cal, 3491, 470), (20, 20))
        self.assertEqual(self.mapped(cal, 537, 470), (220, 20))
        self.assertEqual(self.mapped(cal, 3491, 3636), (20, 300))

    def test_degenerate_calibration_rejected(self):
        ok, _ = self.calibrate([(1000, 1000), (1010, 1005), (1003, 1100)])
        self.assertFalse(ok)

if __name__ == '__main__':
    unittest.main()

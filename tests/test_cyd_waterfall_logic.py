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
HITS = ['NONE', 'DOWN', 'STEP', 'UP', 'MENU', 'TUNE']


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
        cls.c.cyd_level.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]
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
        self.assertEqual(self.c.cyd_level(5.0, 10.0, 30.0), 0)
        self.assertEqual(self.c.cyd_level(40.0, 10.0, 30.0), 255)
        self.assertEqual(self.c.cyd_level(25.0, 10.0, 30.0), 127)
        self.assertEqual(self.c.cyd_level(20.0, 10.0, 20.0), 127)
        self.assertEqual(self.c.cyd_palette(0), 0x0000)
        self.assertEqual(self.c.cyd_palette(255), 0xffff)

    def test_column_to_frequency_per_span(self):
        self.assertEqual(self.c.cyd_column_mhz(2425, 0, 16), 2417)
        self.assertEqual(self.c.cyd_column_mhz(2425, 120, 16), 2425)
        self.assertEqual(self.c.cyd_column_mhz(2425, 239, 16), 2433)
        self.assertEqual(self.c.cyd_column_mhz(2442, 0, 80), 2402)
        self.assertEqual(self.c.cyd_column_mhz(2442, 239, 80), 2482)

    def test_offset_column_and_board_markers(self):
        self.assertEqual(self.c.cyd_offset_column(0, 16), 120)
        self.assertEqual(self.c.cyd_offset_column(3300, 16), 169)   # ch37 at LO 2401
        self.assertEqual(self.c.cyd_offset_column(-5900, 16), 31)   # ch38 at LO 2425
        self.assertEqual(self.c.cyd_offset_column(9000, 16), -1)
        self.assertEqual(self.c.cyd_offset_column(30000, 80), 210)

    def test_presets_match_measured_sessions(self):
        class Preset(ctypes.Structure):
            _fields_ = [('label', ctypes.c_char_p), ('lo_mhz', ctypes.c_int), ('marker_khz', ctypes.c_int),
                        ('measured', ctypes.c_bool)]
        presets = (Preset*7).in_dll(self.c, 'cyd_presets')
        table = {p.label.decode(): (p.lo_mhz, p.marker_khz, p.measured) for p in presets}
        self.assertEqual(table['BLE 37'], (2401, 3300, True))
        self.assertEqual(table['BLE 38'], (2425, -5900, True))
        self.assertFalse(table['BLE 39'][2])
        self.assertEqual(table['2.4 BAND'][0], 2442)

    def test_hit_main(self):
        hit = lambda x, y: HITS[self.c.cyd_hit_main(x, y)]
        self.assertEqual(hit(100, 10), 'NONE')
        self.assertEqual(hit(100, 40), 'NONE')
        self.assertEqual(hit(100, 50), 'TUNE')
        self.assertEqual(hit(100, 200), 'TUNE')
        self.assertEqual([hit(x, 300) for x in (5, 70, 130, 235)], ['DOWN', 'STEP', 'UP', 'MENU'])
        self.assertEqual(hit(-1, 300), 'NONE')

    def test_hit_menu_grid(self):
        self.assertEqual(self.c.cyd_hit_menu(5, 95), 0)
        self.assertEqual(self.c.cyd_hit_menu(235, 95), 2)
        self.assertEqual(self.c.cyd_hit_menu(120, 160), 4)
        self.assertEqual(self.c.cyd_hit_menu(235, 262), 14)
        self.assertEqual(self.c.cyd_hit_menu(120, 80), -1)
        self.assertEqual(self.c.cyd_hit_menu(120, 270), -1)

    def test_peak_hold_decays(self):
        peak = (ctypes.c_float*COLUMNS)(*([0.0]*COLUMNS))
        row = (ctypes.c_float*COLUMNS)(*([10.0]*COLUMNS))
        self.c.cyd_peak_update.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.c_bool]
        self.c.cyd_peak_update(peak, row, 1.0, True)
        low = (ctypes.c_float*COLUMNS)(*([0.0]*COLUMNS))
        self.c.cyd_peak_update(peak, low, 1.0, False)
        self.assertAlmostEqual(peak[0], 9.0)
        high = (ctypes.c_float*COLUMNS)(*([20.0]*COLUMNS))
        self.c.cyd_peak_update(peak, high, 1.0, False)
        self.assertAlmostEqual(peak[0], 20.0)

    def test_spectrum_line_draws_trace_peak_marker_and_cursor(self):
        db = [0.0]*COLUMNS
        db[100] = 30.0
        peak = list(db)
        peak[50] = 15.0
        peak[60] = 5.0                                   # below CYD_PEAK_MIN_DB: hidden
        f = ctypes.c_float*COLUMNS
        out = (ctypes.c_uint16*COLUMNS)()
        self.c.cyd_spectrum_line.argtypes = [f, f, f, ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                             ctypes.POINTER(ctypes.c_uint16)]
        rows = []
        for r in range(48):
            self.c.cyd_spectrum_line(f(*db), f(*peak), f(*([0.0]*COLUMNS)), 30.0, r, 200, 20, out)
            rows.append(list(out))
        self.assertEqual(rows[0][100], 0xffff)          # full-scale trace edge at the top
        self.assertNotEqual(rows[47][100], 0x0000)      # filled to the bottom
        floor_edge = [r for r in range(48) if rows[r][10] == 0xffff]
        self.assertEqual(floor_edge, [47-int(0.15*255)*47//255])  # noise floor sits on the baseline
        self.assertEqual(len([r for r in range(48) if rows[r][50] == 0xffe0]), 1)
        self.assertEqual([r for r in range(48) if rows[r][60] == 0xffe0], [])
        self.assertEqual(rows[0][200], 0xf81f)          # marker column, dashed
        self.assertEqual(rows[2][200], 0x0000)
        self.assertEqual(rows[0][20], 0x07ff)           # cursor column, dotted
        self.assertNotEqual(rows[1][20], 0x07ff)

    def test_flat_floor_and_dc_mask(self):
        f = ctypes.c_float*COLUMNS
        floor = f(*([0.0]*COLUMNS))
        self.c.cyd_colfloor_update.argtypes = [f, f, ctypes.c_bool]
        self.c.cyd_colfloor_update(floor, f(*([10.0]*COLUMNS)), True)
        self.c.cyd_colfloor_update(floor, f(*([0.0]*COLUMNS)), False)
        self.assertAlmostEqual(floor[0], 8.0, places=4)    # falls fast
        self.c.cyd_colfloor_update(floor, f(*([108.0]*COLUMNS)), False)
        self.assertAlmostEqual(floor[0], 9.0, places=4)    # rises slowly
        row = f(*[50.0 if 118 < c < 122 else 0.0 for c in range(COLUMNS)])
        self.c.cyd_mask_dc(row)
        self.assertEqual(max(row[118:123]), 0.0)

    def test_burst_counter_counts_rising_edges(self):
        class Burst(ctypes.Structure):
            _fields_ = [('high', ctypes.c_bool), ('count', ctypes.c_uint)]
        b = Burst()
        quiet = (ctypes.c_float*COLUMNS)(*([0.0]*COLUMNS))
        loud = list(quiet)
        loud[121] = 20.0
        loud = (ctypes.c_float*COLUMNS)(*loud)
        for row in (quiet, loud, loud, quiet, loud, quiet):
            self.c.cyd_burst_update(ctypes.byref(b), row, 120, ctypes.c_float(0.0), ctypes.c_float(12.0))
        self.assertEqual(b.count, 2)
        self.c.cyd_burst_update(ctypes.byref(b), loud, -1, ctypes.c_float(0.0), ctypes.c_float(12.0))
        self.assertEqual(b.count, 2)

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

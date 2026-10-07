"""UI behaviour tests for the CYD waterfall, run in the host simulator.

The real firmware/cyd-waterfall sources drive an emulated panel and touch
controller (tools/cyd_sim.py). These are simulation tests, not hardware proof.
"""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import cyd_sim  # noqa: E402

W = cyd_sim.W
MENU = (210, 290)
GREEN_BUTTON = 0x0320


@unittest.skipUnless(shutil.which('cc'), 'needs a C compiler')
class DisplaySim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sim = cyd_sim.build(self.tmp.name)
        self.sim.boot()
        self.sim.run(1500)

    def tearDown(self):
        self.tmp.cleanup()

    def pixel(self, x, y):
        return self.sim.screen()[y*W+x]

    def test_boot_draws_every_region(self):
        screen = self.sim.screen()
        lit = lambda y0, y1: sum(1 for y in range(y0, y1) for x in range(W) if screen[y*W+x])
        self.assertGreater(lit(0, 22), 200)       # frequency text
        self.assertGreater(lit(32, 44), 50)       # scale ticks and labels
        self.assertGreater(lit(44, 92), 500)      # spectrum trace
        self.assertGreater(lit(92, 140), 2000)    # waterfall rows
        self.assertGreater(lit(264, 320), 5000)   # control buttons

    def test_menu_opens_and_back_closes(self):
        self.sim.tap(*MENU)
        self.assertEqual(self.pixel(185, 270), GREEN_BUTTON)
        self.sim.tap(*MENU)
        self.assertNotEqual(self.pixel(185, 270), GREEN_BUTTON)

    def test_preset_retunes_without_leaving_a_cursor(self):
        self.sim.tap(*MENU)
        self.sim.tap(*cyd_sim.menu_cell(0))   # BLE 37
        self.assertEqual(self.sim.frequency, 2401)
        self.sim.run(1000)
        # No cyan cursor column anywhere in the spectrum strip.
        screen = self.sim.screen()
        self.assertFalse(any(screen[y*W+x] == 0x07ff for y in range(44, 92) for x in range(W)))

    def test_tap_inspects_and_hold_tunes(self):
        self.sim.tap(60, 200, hold_ms=120)
        self.assertEqual(self.sim.frequency, 2412)            # a tap only inspects
        self.sim.tap(60, 200, hold_ms=900)
        self.assertEqual(self.sim.frequency, 2412-4)          # column 60 at 16 MHz span

    def test_buttons_step_and_repeat(self):
        self.sim.tap(150, 290)                                 # +
        self.assertEqual(self.sim.frequency, 2413)
        self.sim.tap(90, 290)                                  # STEP -> 5
        self.sim.tap(150, 290)
        self.assertEqual(self.sim.frequency, 2418)
        self.sim.tap(30, 290, hold_ms=1300)                    # - held: repeats
        self.assertLessEqual(self.sim.frequency, 2418-15)

    def test_settings_survive_reboot(self):
        self.sim.tap(*MENU)
        self.sim.tap(*cyd_sim.menu_cell(6))                    # 2.4 BAND
        self.sim.run(3500)                                     # past the 3 s save delay
        self.sim.c.sim_tune_for_test(2412)
        self.sim.boot()
        self.assertEqual(self.sim.frequency, 2442)

    def test_host_activity_pauses_capture(self):
        before = self.sim.c.sim_acquisitions()
        self.sim.host()
        self.sim.run(1000)
        self.assertEqual(self.sim.c.sim_acquisitions(), before)
        self.sim.run(5000)
        self.assertGreater(self.sim.c.sim_acquisitions(), before)


if __name__ == '__main__':
    unittest.main()

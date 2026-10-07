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
TILES, LIVE, HOME_BUTTON = cyd_sim.HOME_TILES, cyd_sim.LIVE, cyd_sim.HOME_BUTTON
GREEN_BUTTON = 0x0320


@unittest.skipUnless(shutil.which('cc'), 'needs a C compiler')
class DisplaySim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sim = cyd_sim.build(self.tmp.name)
        self.sim.boot()
        self.sim.run(500)

    def tearDown(self):
        self.tmp.cleanup()

    def pixel(self, x, y):
        return self.sim.screen()[y*W+x]

    def live(self):
        self.sim.tap(*TILES['live'])
        self.sim.run(1500)

    def test_boot_lands_on_home_with_four_tiles(self):
        tile_colours = {self.pixel(10, 60), self.pixel(130, 60), self.pixel(10, 160), self.pixel(130, 160)}
        self.assertEqual(len(tile_colours), 4)
        self.assertEqual(self.sim.c.sim_acquisitions(), 0)    # HOME leaves the radio idle

    def test_live_draws_every_region(self):
        self.live()
        screen = self.sim.screen()
        lit = lambda y0, y1: sum(1 for y in range(y0, y1) for x in range(W) if screen[y*W+x])
        self.assertGreater(lit(0, 22), 200)
        self.assertGreater(lit(32, 44), 50)
        self.assertGreater(lit(44, 92), 500)
        self.assertGreater(lit(92, 140), 2000)
        self.assertGreater(lit(264, 320), 5000)

    def test_more_opens_and_done_closes(self):
        self.live()
        self.sim.tap(*LIVE['more'])
        self.assertEqual(self.pixel(185, 270), GREEN_BUTTON)
        self.sim.tap(*LIVE['more'])
        self.assertNotEqual(self.pixel(185, 270), GREEN_BUTTON)

    def test_preset_retunes_without_leaving_a_cursor(self):
        self.live()
        self.sim.tap(*LIVE['more'])
        self.sim.tap(*cyd_sim.menu_cell(0))   # BLE 37
        self.assertEqual(self.sim.frequency, 2401)
        self.sim.run(1000)
        screen = self.sim.screen()
        self.assertFalse(any(screen[y*W+x] == 0x07ff for y in range(44, 92) for x in range(W)))

    def test_tap_inspects_and_hold_tunes(self):
        self.live()
        self.sim.tap(60, 200, hold_ms=120)
        self.assertEqual(self.sim.frequency, 2412)
        self.sim.tap(60, 200, hold_ms=900)
        self.assertEqual(self.sim.frequency, 2412-4)

    def test_buttons_step_repeat_and_go_home(self):
        self.live()
        self.sim.tap(*LIVE['up'])
        self.assertEqual(self.sim.frequency, 2413)
        self.sim.tap(*LIVE['more'])
        self.sim.tap(*cyd_sim.menu_cell(8))   # STEP -> 5
        self.sim.tap(*LIVE['more'])
        self.sim.tap(*LIVE['up'])
        self.assertEqual(self.sim.frequency, 2418)
        self.sim.tap(*LIVE['down'], hold_ms=1300)
        self.assertLessEqual(self.sim.frequency, 2418-15)
        self.sim.tap(*LIVE['home'])
        before = self.sim.c.sim_acquisitions()
        self.sim.run(500)
        self.assertEqual(self.sim.c.sim_acquisitions(), before)

    def test_live_settings_survive_reboot(self):
        self.live()
        self.sim.tap(*LIVE['more'])
        self.sim.tap(*cyd_sim.menu_cell(6))   # 2.4 BAND
        self.sim.run(3500)
        self.sim.c.sim_tune_for_test(2412)
        self.sim.boot()
        self.live()
        self.assertEqual(self.sim.frequency, 2442)

    def test_wifi_names_a_quiet_main_channel(self):
        import json
        self.sim.tap(*TILES['wifi'])
        self.sim.run(20000)
        self.assertEqual(self.sim.frequency, 2442)
        stat = self.stat()
        self.assertIn(stat['wifi_best'], (6, 11))   # the simulated AP sits on channel 1
        self.sim.tap(*HOME_BUTTON)
        self.assertEqual(len({self.pixel(10, 60), self.pixel(130, 60)}), 2)

    def test_bluetooth_cycles_all_three_channels(self):
        self.sim.tap(*TILES['bluetooth'])
        self.sim.run(9000)
        stat = self.stat()
        self.assertTrue(all(s > 0 for s in stat['ble_s']))

    def test_settings_reset_needs_two_taps(self):
        self.sim.tap(*TILES['settings'])
        self.sim.tap(180, 67)                  # COLOUR 30 -> 40
        self.sim.tap(60, 266)                  # RESET ALL: arms
        self.assertEqual(self.pixel(10, 252), 0xf800)
        self.sim.tap(60, 266)                  # confirms
        self.assertNotEqual(self.pixel(10, 252), 0xf800)

    def test_help_pages_and_done(self):
        self.sim.tap(*TILES['help'])
        for _ in range(3):
            self.sim.tap(180, 265)             # NEXT
        self.sim.tap(180, 265)                 # DONE -> HOME
        self.assertEqual(len({self.pixel(10, 60), self.pixel(130, 60), self.pixel(10, 160)}), 3)

    def test_host_activity_pauses_capture(self):
        self.live()
        before = self.sim.c.sim_acquisitions()
        self.sim.host()
        self.sim.run(1000)
        self.assertEqual(self.sim.c.sim_acquisitions(), before)
        self.sim.run(5000)
        self.assertGreater(self.sim.c.sim_acquisitions(), before)

    def stat(self):
        import ctypes
        import json
        self.sim.c.sim_host_command.argtypes = [ctypes.c_char_p]
        self.sim.c.sim_serial_take.restype = ctypes.c_size_t
        self.sim.c.sim_host_command(b'CYDSTAT')
        buf = (ctypes.c_uint8*65536)()
        n = self.sim.c.sim_serial_take(buf, len(buf))
        return json.loads(bytes(buf[:n]).decode().split('CYD STAT ', 1)[1])


@unittest.skipUnless(shutil.which('cc'), 'needs a C compiler')
class DeviceCommandsSim(unittest.TestCase):
    def setUp(self):
        import ctypes
        self.ctypes = ctypes
        self.tmp = tempfile.TemporaryDirectory()
        self.sim = cyd_sim.build(self.tmp.name)
        self.sim.c.sim_host_command.argtypes = [ctypes.c_char_p]
        self.sim.c.sim_serial_take.restype = ctypes.c_size_t
        self.sim.boot()
        self.sim.run(1500)

    def tearDown(self):
        self.tmp.cleanup()

    def output(self):
        buf = (self.ctypes.c_uint8*(1 << 20))()
        n = self.sim.c.sim_serial_take(buf, len(buf))
        return bytes(buf[:n])

    def test_screenshot_matches_the_emulated_screen(self):
        from cyd_device import parse_shot
        self.assertEqual(self.sim.c.sim_host_command(b'CYDSHOT'), 1)
        pixels, crc_ok, _ = parse_shot(self.output())
        self.assertTrue(crc_ok)
        # RGB666 readback drops the low red/blue bit only.
        expected = [v & 0xffff for v in self.sim.screen()]
        self.assertEqual(pixels, expected)

    def test_stat_and_tap_do_not_pause_the_display(self):
        import json
        before = self.sim.c.sim_acquisitions()
        self.sim.c.sim_host_command(b'CYDTAP 61 96 150')       # HOME -> LIVE
        self.sim.run(1500)
        before = self.sim.c.sim_acquisitions()
        self.sim.c.sim_host_command(b'CYDSTAT')
        stat = json.loads(self.output().decode().split('CYD STAT ', 1)[1])
        self.assertEqual((stat['screen'], stat['freq']), ('live', 2412))
        self.assertGreater(stat['rows'], 0)
        self.sim.c.sim_host_command(b'CYDTAP 150 292 150')
        self.sim.run(400)
        self.assertEqual(self.sim.frequency, 2413)
        self.assertGreater(self.sim.c.sim_acquisitions(), before)

    def test_unknown_cyd_command_is_rejected_and_others_pass_through(self):
        self.assertEqual(self.sim.c.sim_host_command(b'CYDNOPE'), 1)
        self.assertIn(b'CYD ERR', self.output())
        self.assertEqual(self.sim.c.sim_host_command(b'INFO'), 0)


if __name__ == '__main__':
    unittest.main()

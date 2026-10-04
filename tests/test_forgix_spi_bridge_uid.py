"""Actual UID C against ROM/clock faults; no hardware or private device IDs."""
import ctypes as C
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'firmware/forgix-spi-bridge'

class UID(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=shutil.which('cc')
        if not cc or not str(Path(cc).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Use locked Nix compiler')
        cls.tmp=tempfile.TemporaryDirectory();d=Path(cls.tmp.name);(d/'pico').mkdir()
        (d/'pico/stdlib.h').write_text('#include <stdint.h>\nuint64_t time_us_64(void);\n')
        (d/'pico/bootrom.h').write_text('''#include <stdint.h>
#define ROM_FUNC_GET_SYS_INFO 0x5349
#define SYS_INFO_CHIP_INFO 1
typedef int (*rom_get_sys_info_fn)(uint32_t*,uint32_t,uint32_t);
void *rom_func_lookup(unsigned);
''')
        (d/'rom.c').write_text('''#include "pico/bootrom.h"
#include <stddef.h>
static unsigned mode,ticks,lookups,reads;static uint64_t clock;
void fixture(unsigned m){mode=m;ticks=lookups=reads=0;clock=m==8?500000:0;}
unsigned count(unsigned which){return which?reads:lookups;}
uint64_t time_us_64(void){ticks++;if((mode==9&&ticks==4)||(mode==10&&ticks==5))clock=500000;return clock;}
static int info(uint32_t *p,uint32_t n,uint32_t flags){
 reads++;if(n!=9||flags!=1)return -99;
 p[0]=mode==11?0:mode==12?3:1;p[1]=0x12345678;
 p[2]=mode==4?0:mode==5?0xffffffff:0x76543210;
 p[3]=mode==4?0:mode==5?0xffffffff:0xfedcba98;
 if(mode==7)clock=500000;
 return mode==2?3:mode==3?-4:4;
}
void *rom_func_lookup(unsigned code){
 lookups++;if(mode==6)clock=500000;
 return code==ROM_FUNC_GET_SYS_INFO&&mode!=1?(void*)info:NULL;
}
''')
        subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC',
                        '-I'+str(d),str(PROJECT/'uid.c'),str(d/'rom.c'),'-o',str(d/'uid.so')],
                       check=True,capture_output=True,timeout=30)
        cls.lib=C.CDLL(str(d/'uid.so'));cls.lib.bridge_uid_init.argtypes=[C.c_uint64]
        cls.lib.bridge_uid_init.restype=C.c_bool
        cls.lib.pico_get_unique_board_id_string.argtypes=[C.c_void_p,C.c_uint]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def get(self,size=17):
        value=C.create_string_buffer(size)
        self.lib.pico_get_unique_board_id_string(value,size)
        return value.value
    def test_actual_rom_uid_matches_sdk_byte_order_and_bounded_getter(self):
        self.lib.fixture(0);self.assertTrue(self.lib.bridge_uid_init(500000))
        self.assertEqual(self.get(),b'FEDCBA9876543210')
        self.assertEqual(self.get(5),b'FEDC');self.assertEqual(self.get(1),b'')
        self.lib.pico_get_unique_board_id_string(None,0)
        self.assertEqual(self.lib.count(0),1);self.assertEqual(self.lib.count(1),1)
    def test_lookup_return_flags_and_invalid_uid_never_publish_cached_or_fake_id(self):
        for mode in (1,2,3,4,5,11,12):
            with self.subTest(mode=mode):
                self.lib.fixture(0);self.assertTrue(self.lib.bridge_uid_init(500000))
                self.lib.fixture(mode);self.assertFalse(self.lib.bridge_uid_init(500000))
                self.assertEqual(self.get(),b'')
                self.assertEqual(self.lib.count(1),0 if mode==1 else 1)
    def test_deadline_before_lookup_after_lookup_rom_format_and_publication(self):
        for mode in (6,7,8,9,10):
            with self.subTest(mode=mode):
                self.lib.fixture(mode);self.assertFalse(self.lib.bridge_uid_init(500000))
                self.assertEqual(self.get(),b'')
                self.assertEqual(self.lib.count(0),0 if mode==8 else 1)
                self.assertEqual(self.lib.count(1),0 if mode in (6,8) else 1)
    def test_watchdog_precedes_checked_uid_and_usb_before_application_gpio(self):
        main=(PROJECT/'main.c').read_text().split('int main(void) {',1)[1]
        self.assertLess(main.index('watchdog_enable(2000,false)'),main.index('bridge_uid_init('))
        self.assertLess(main.index('bridge_uid_init('),main.index('tud_init(0)'))
        self.assertLess(main.index('tud_init(0)'),main.index('wire_prepare('))
        self.assertIn('bridge_uid_init(boot+UINT64_C(500000))',main)
        self.assertIn('watchdog_reboot(0,0,1);while(true)tight_loop_contents();',main)
        cmake=(PROJECT/'CMakeLists.txt').read_text()
        self.assertNotIn('pico_unique_id',cmake);self.assertIn('uid.c',cmake)
        source=(PROJECT/'uid.c').read_text()
        self.assertNotIn('__attribute__',source)
        self.assertNotIn('watchdog_update(',source)
        self.assertNotIn('pico/unique_id.h',(PROJECT/'usb_descriptors.c').read_text())

if __name__=='__main__':unittest.main()

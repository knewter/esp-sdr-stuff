"""Actual bridge C control flow against a fake SDK clock/ready adapter.

These tests prove acceptance and operation-order checks, not MMIO, electrical
pin release, fractional-divider timing, FIFO-full behavior or metastability.
The harness extracts named functions unchanged; it never opens a device.
"""
import ctypes as C
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ.get('FORGIX_SPI_BRIDGE_TEST_ROOT', Path(__file__).resolve().parents[1]))
FUNCTIONS = ('expired', 'wire_end', 'wire_config', 'bridge_spi_transaction')


def extract_function(source, name):
    import re
    match = re.search(r'^(?:static\s+)?[^\n;{}]+\b' + re.escape(name) + r'\([^;{}]*\)\s*\{', source, re.M)
    if not match:
        raise AssertionError('Actual firmware function missing: ' + name)
    opening = source.index('{', match.start())
    depth = 1
    cursor = opening + 1
    while depth:
        if source[cursor] == '{':
            depth += 1
        elif source[cursor] == '}':
            depth -= 1
        cursor += 1
    return source[match.start():cursor]


SDK = r'''
#include <stdbool.h>
#include <stdint.h>
#include "protocol.h"
#define CS 1u
#define SCK 2u
#define DATA 3u
#define TRANSACTION_US UINT64_C(20000)
#define MAX_LIFETIME_US UINT64_C(120000000)
typedef void *PIO;
typedef struct { unsigned unused; } pio_sm_config;
static PIO const wire_pio=(void*)1;
static unsigned sm=0,tx_offset=1,rx_offset=2;
static bool pins_ready=true;
static uint64_t lifetime_until=MAX_LIFETIME_US;
static uint64_t clock_us;
static unsigned scenario,puts,gets,ends,rx_inits,current_offset,tx_starts,rx_starts;
static int64_t cs_low_at,rx_init_at;
uint64_t time_us_64(void){return clock_us;}
void gpio_put(unsigned pin,unsigned value){if(pin==CS&&!value)cs_low_at=(int64_t)clock_us;}
void pio_sm_set_enabled(PIO p,unsigned s,bool e){(void)p;(void)s;if(e){if(current_offset==rx_offset)rx_starts++;else tx_starts++;}}
void pio_sm_set_consecutive_pindirs(PIO p,unsigned s,unsigned pin,unsigned n,bool out){(void)p;(void)s;(void)pin;(void)n;(void)out;}
void pio_sm_set_pins_with_mask(PIO p,unsigned s,uint32_t v,uint32_t mask){(void)p;(void)s;(void)v;(void)mask;}
void busy_wait_us_32(uint32_t delay){
 clock_us+=delay;
 if(delay==100){ends++;if((scenario==1&&ends==1)||(scenario==7&&ends==2))clock_us=21000;}
}
pio_sm_config forgix_request_program_get_default_config(unsigned o){(void)o;return (pio_sm_config){0};}
pio_sm_config forgix_response_program_get_default_config(unsigned o){(void)o;return (pio_sm_config){0};}
#define sm_config_set_sideset_pins(c,p) ((void)(c),(void)(p))
#define sm_config_set_set_pins(c,p,n) ((void)(c),(void)(p),(void)(n))
#define sm_config_set_out_pins(c,p,n) ((void)(c),(void)(p),(void)(n))
#define sm_config_set_in_pins(c,p) ((void)(c),(void)(p))
#define sm_config_set_out_shift(c,a,b,n) ((void)(c),(void)(a),(void)(b),(void)(n))
#define sm_config_set_in_shift(c,a,b,n) ((void)(c),(void)(a),(void)(b),(void)(n))
#define sm_config_set_clkdiv_int_frac(c,a,b) ((void)(c),(void)(a),(void)(b))
#define sm_config_set_fifo_join(c,a) ((void)(c),(void)(a))
#define PIO_FIFO_JOIN_TX 1
#define PICO_OK 0
int pio_sm_init(PIO p,unsigned s,unsigned offset,pio_sm_config const *c){
 (void)p;(void)s;(void)c;current_offset=offset;
 if(offset==rx_offset){rx_inits++;rx_init_at=(int64_t)clock_us;}
 return ((scenario==9&&offset==tx_offset)||(scenario==10&&offset==rx_offset))?-1:PICO_OK;
}
void pio_interrupt_clear(PIO p,unsigned irq){(void)p;(void)irq;}
void pio_sm_put(PIO p,unsigned s,uint32_t word){
 (void)p;(void)s;(void)word;puts++;if(scenario==2&&puts==4)clock_us=21000;
}
bool pio_interrupt_get(PIO p,unsigned irq){
 (void)p;if((scenario==3&&irq==0)||(scenario==5&&irq==1))clock_us=21000;
 if(scenario==8&&irq==0)clock_us=120000001;
 return true;
}
bool pio_sm_is_rx_fifo_empty(PIO p,unsigned s){
 (void)p;(void)s;if(scenario==4)clock_us=21000;return false;
}
uint32_t pio_sm_get(PIO p,unsigned s){(void)p;(void)s;gets++;return 0;}
unsigned __real_bridge_wire_response(bool write,const uint8_t data[64],uint32_t *value);
unsigned __wrap_bridge_wire_response(bool write,const uint8_t data[64],uint32_t *value){
 unsigned result=__real_bridge_wire_response(write,data,value);
 if(scenario==6)clock_us=21000;return result;
}
'''
ENTRY = r'''
unsigned adapter_run(unsigned mode){
 scenario=mode;clock_us=mode==8?119990000:0;puts=gets=ends=rx_inits=tx_starts=rx_starts=current_offset=0;cs_low_at=rx_init_at=-1;
 lifetime_until=MAX_LIFETIME_US;pins_ready=true;
 bridge_request request={.op=BRIDGE_WRITE,.nonce={1},.sequence=2,.address=BRIDGE_SCRATCH_ADDR,.value=0x1357ace0};
 uint32_t value=0;return bridge_spi_transaction(&request,&value);
}
uint64_t adapter_clock(void){return clock_us;}
int64_t adapter_cs_low(void){return cs_low_at;}
int64_t adapter_rx_init(void){return rx_init_at;}
unsigned adapter_gets(void){return gets;}
unsigned adapter_tx_starts(void){return tx_starts;}
unsigned adapter_rx_starts(void){return rx_starts;}
'''


class NativeDeadline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        directory = Path(cls.temp.name)
        project = ROOT / 'firmware/forgix-spi-bridge'
        cls.source_bytes = (project/'main.c').read_bytes()
        cls.source_sha256 = hashlib.sha256(cls.source_bytes).hexdigest()
        functions = '\n'.join(extract_function(cls.source_bytes.decode(), name) for name in FUNCTIONS)
        (directory/'adapter.c').write_text(SDK + '\n' + functions + '\n' + ENTRY)
        compiler = shutil.which(os.environ.get('CC', 'cc'))
        if not compiler or not str(Path(compiler).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Use the locked Nix shell native compiler')
        result = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Wno-unused-variable',
                                 '-shared', '-fPIC', '-I'+str(project), str(directory/'adapter.c'),
                                 str(project/'protocol.c'), '-Wl,--wrap=bridge_wire_response',
                                 '-o', str(directory/'adapter.so')], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError('Actual-function harness compile failed: '+result.stderr)
        cls.lib = C.CDLL(str(directory/'adapter.so'))
        cls.lib.adapter_run.argtypes = [C.c_uint]
        cls.lib.adapter_run.restype = C.c_uint
        for name in ('adapter_cs_low','adapter_rx_init'):
            getattr(cls.lib,name).restype = C.c_int64
        cls.lib.adapter_clock.restype = C.c_uint64
        for name in ('adapter_gets','adapter_tx_starts','adapter_rx_starts'):
            getattr(cls.lib,name).restype = C.c_uint

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_timely_ready_write_remains_accepted(self):
        self.assertEqual(self.lib.adapter_run(0), 0)
        self.assertGreaterEqual(self.lib.adapter_cs_low(), 0)
        self.assertGreaterEqual(self.lib.adapter_rx_init(), 0)
        self.assertEqual(self.lib.adapter_gets(),16)
        self.assertLess(self.lib.adapter_clock(),20000)

    def assert_timeout(self, mode):
        self.assertEqual(self.lib.adapter_run(mode),2,'Late ready path accepted by actual firmware')

    def test_initial_idle_wait_expiry_refuses_cs_assertion(self):
        self.assert_timeout(1)
        self.assertEqual(self.lib.adapter_cs_low(),-1)

    def test_preloaded_request_expiry_refuses_cs_assertion(self):
        self.assert_timeout(2)
        self.assertEqual(self.lib.adapter_cs_low(),-1)

    def test_late_ready_tx_irq_refuses_rx_handoff(self):
        self.assert_timeout(3)
        self.assertEqual(self.lib.adapter_rx_init(),-1)

    def test_late_ready_fifo_refuses_consumption(self):
        self.assert_timeout(4)
        self.assertEqual(self.lib.adapter_gets(),0)

    def test_late_ready_final_irq_refuses_success(self):
        self.assert_timeout(5)

    def test_response_decode_finishing_late_refuses_success(self):
        self.assert_timeout(6)

    def test_cleanup_finishing_late_refuses_success(self):
        self.assert_timeout(7)

    def test_tx_init_error_refuses_cs_and_activation(self):
        self.assertNotEqual(self.lib.adapter_run(9),0)
        self.assertEqual(self.lib.adapter_cs_low(),-1)
        self.assertEqual(self.lib.adapter_tx_starts(),0)

    def test_rx_init_error_refuses_response_activation(self):
        self.assertNotEqual(self.lib.adapter_run(10),0)
        self.assertEqual(self.lib.adapter_rx_starts(),0)

    def test_transaction_deadline_is_capped_by_lifetime(self):
        self.assert_timeout(8)
        self.assertEqual(self.lib.adapter_rx_init(),-1)


if __name__ == '__main__':
    unittest.main()

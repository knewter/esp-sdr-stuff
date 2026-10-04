"""Actual HDL, actual C and committed PIO instruction tests; no device/build."""
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from migen import Signal
from migen.fhdl import verilog
from migen.sim import run_simulation

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from forgix_clock_observer import ClockObserver,ratio_interval,DIVISOR,SAMPLES
FIRMWARE=ROOT/'firmware/forgix-clock-observer'


class HDL(unittest.TestCase):
    def test_actual_async_configuration_qualification_abort_and_no_rearm(self):
        for phase in (0,1,3,7):
            pads=SimpleNamespace(cs_n=Signal(),clk=Signal(),mosi=Signal())
            dut=ClockObserver(pads,with_tristate=False,divisor=16,periods=8,arm_cycles=8)
            def host():
                # Long actual CS-low configuration and256 trailing clocks.
                for n in range(320):
                    yield pads.clk.eq(n%2);yield
                    self.assertFalse((yield dut.io.oe));self.assertFalse((yield dut.spent))
                yield pads.clk.eq(0);yield pads.cs_n.eq(1);yield
                yield pads.cs_n.eq(0)
                for _ in range(20):yield
                self.assertFalse((yield dut.io.oe));self.assertFalse((yield dut.spent))
                yield pads.cs_n.eq(1);yield pads.clk.eq(1)
                for _ in range(20):yield
                self.assertFalse((yield dut.qualified))
                yield pads.clk.eq(0)
                for _ in range(20):yield
                self.assertTrue((yield dut.qualified))
                yield pads.cs_n.eq(0)
                for _ in range(8):yield
                self.assertTrue((yield dut.io.oe));self.assertTrue((yield dut.spent))
                yield pads.cs_n.eq(1);yield
                self.assertFalse((yield dut.io.oe))
                for _ in range(20):yield
                self.assertTrue((yield dut.aborted));self.assertFalse((yield dut.qualified))
                yield pads.cs_n.eq(0)
                for _ in range(200):yield
                self.assertFalse((yield dut.io.oe));self.assertFalse((yield dut.complete))
            with self.subTest(phase=phase):
                run_simulation(dut,{'host':host()},clocks={'sys':10,'host':(13,phase)})

    def generated(self,script):
        pads=SimpleNamespace(cs_n=Signal(name='cs'),clk=Signal(name='sck'),mosi=Signal())
        dut=ClockObserver(pads,with_tristate=False)
        dut.io.o.name_override='wave';dut.io.oe.name_override='oe'
        dut.complete.name_override='complete';dut.spent.name_override='spent'
        rtl=str(verilog.convert(dut,ios={pads.cs_n,pads.clk,dut.io.o,dut.io.oe,dut.complete,dut.spent},name='observer'))
        tb='''module tb;
reg sys_clk=0,sys_rst=0,cs=0,sck=0;wire wave,oe,complete,spent;
observer dut(.sys_clk(sys_clk),.sys_rst(sys_rst),.cs(cs),.sck(sck),
 .wave(wave),.oe(oe),.complete(complete),.spent(spent));
reg running=1;always #5 if(running)sys_clk=~sys_clk;
integer rises=0,cycles=0;reg previous=0;
initial begin
repeat(100)begin @(negedge sys_clk);sck=~sck;@(posedge sys_clk);#1;if(oe)$fatal(1,"configuration OE");end
@(negedge sys_clk);cs=1;sck=0;repeat(40)@(negedge sys_clk);
cs=0;
while(!complete && cycles<1100000)begin
 @(posedge sys_clk);#1;
 if(oe && wave && !previous)rises=rises+1;
 previous=wave;cycles=cycles+1;
end
if(!complete||oe||!spent||rises!=1024)$fatal(1,"production burst %d",rises);
cs=1;repeat(100)@(negedge sys_clk);cs=0;repeat(100)@(negedge sys_clk);
if(oe)$fatal(1,"rearm");SCRIPT
$display("PASS %0d",rises);$finish;end
endmodule'''.replace('SCRIPT',script)
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);(folder/'rtl.v').write_text(rtl);(folder/'tb.v').write_text(tb)
            iv,vvp=shutil.which('iverilog'),shutil.which('vvp')
            self.assertTrue(iv and str(Path(iv).resolve()).startswith('/nix/store/'))
            subprocess.run([iv,'-g2012','-s','tb','-o',str(folder/'sim'),str(folder/'rtl.v'),str(folder/'tb.v')],check=True,capture_output=True,timeout=30)
            result=subprocess.run([vvp,str(folder/'sim')],check=True,capture_output=True,text=True,timeout=30)
            self.assertIn('PASS 1024',result.stdout)

    def test_generated_production_hdl_exact_1024_periods_and_finite_low_tail(self):
        self.generated('')

    def test_actual_hdl_reset_unarmed_and_raw_inhibit_with_stopped_clock(self):
        self.generated('''
sys_rst=1;repeat(2)@(negedge sys_clk);sys_rst=0;
repeat(100)@(negedge sys_clk);if(oe||spent)$fatal(1,"reset CS-low armed");
cs=1;repeat(40)@(negedge sys_clk);cs=0;
repeat(20)@(negedge sys_clk);if(!oe)$fatal(1,"not active");
running=0;#10;cs=1;#1;if(oe)$fatal(1,"raw inhibit waits for stopped clock");
''')

    def test_geometry_refuses_unbounded_and_inexact_types(self):
        pads=SimpleNamespace(cs_n=Signal(),clk=Signal(),mosi=Signal())
        for kw in ({'divisor':3},{'divisor':True},{'periods':1<<25},{'arm_cycles':2048}):
            with self.assertRaises(ValueError):ClockObserver(pads,with_tristate=False,**kw)


class PIO(unittest.TestCase):
    def test_actual_locked_pio_assembler_accepts_input_only_program(self):
        assembler=shutil.which('pioasm')
        self.assertTrue(assembler and str(Path(assembler).resolve()).startswith('/nix/store/'))
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'period.h'
            subprocess.run([assembler,'-o','c-sdk',str(FIRMWARE/'period.pio'),str(output)],check=True,capture_output=True,timeout=10)
            header=output.read_text()
            self.assertIn('.length = 10',header)
            self.assertIn('forgix_clock_period_program_get_default_config',header)

    def run_program(self,period,phase=0,push_delay=0):
        instructions=[];labels={}
        for line in (FIRMWARE/'period.pio').read_text().splitlines():
            line=line.split(';')[0].strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):labels[line[:-1]]=len(instructions)
            else:instructions.append(line.replace(',','').split())
        self.assertFalse(any(x[0] in ('out','set','side') for x in instructions))
        pc=0;x=0;isr=0;cycle=0;result=[]
        while len(result)<SAMPLES and cycle<1000000:
            # Two sampled-system-cycle synchronizer delay; ideal digital edges.
            pin=((Fraction(cycle-2)-phase)%period)<period/2
            ins=instructions[pc];advance=True;next_pc=(pc+1)%len(instructions)
            if ins[0]=='wait':advance=(pin==bool(int(ins[1])))
            elif ins[0]=='mov':
                if ins[1]=='x':x=0xffffffff
                else:isr=x
            elif ins[0]=='jmp':
                if len(ins)==2:next_pc=labels[ins[1]]
                elif ins[1]=='pin':
                    if pin:next_pc=labels[ins[2]]
                elif ins[1]=='x--':
                    old=x;x=(x-1)&0xffffffff
                    if old:next_pc=labels[ins[2]]
                else:self.fail('unreviewed PIO instruction')
            elif ins[0]=='push':
                result.append(0xffffffff-isr);cycle+=push_delay
            else:self.fail('unreviewed PIO instruction')
            if advance:pc=next_pc
            cycle+=1
        self.assertEqual(len(result),SAMPLES)
        return result

    def test_literal_instruction_period_envelope_across_true_async_phases(self):
        for period in (Fraction(48),Fraction(101,2),Fraction(4800),Fraction(96001,20)):
            for phase in (Fraction(0),Fraction(1,3),Fraction(7,5)):
                values=self.run_program(period,phase)
                bounds=ratio_interval(values)
                low=Fraction(*bounds['lower']);high=Fraction(*bounds['upper'])
                self.assertLessEqual(low,DIVISOR/period);self.assertGreaterEqual(high,DIVISOR/period)

    def test_fifo_backpressure_skips_whole_periods_without_stretching_sample(self):
        bounds=ratio_interval(self.run_program(Fraction(4800),Fraction(1,3),push_delay=20000))
        self.assertLessEqual(Fraction(*bounds['lower']),Fraction(1024,4800))
        self.assertGreaterEqual(Fraction(*bounds['upper']),Fraction(1024,4800))

    def test_reducer_strict_zero_overflow_count_and_disagreement_refusal(self):
        for values in ([2400]*15,[True]*16,[8]*16,[0xffffffff]*16,[2400]*15+[200]):
            with self.assertRaises(ValueError):ratio_interval(values)
        result=ratio_interval([2400]*16)
        self.assertFalse(result['physical_timing_qualified']);self.assertFalse(result['calibrated_absolute_frequency'])


HARNESS=r'''
#include <stdio.h>
#include <stdlib.h>
#include "observer.h"
static int fault,prepares,starts,stops,services,takes;
static uint64_t tick;
static uint64_t now(void*c){(void)c;return tick;}
static bool cancel(void*c){(void)c;return fault==6&&takes==3;}
static bool prepare(void*c,uint64_t u){(void)c;(void)u;prepares++;if(fault==2)tick=10000;return fault!=1;}
static bool start(void*c,uint64_t u){(void)c;(void)u;starts++;if(fault==3)tick=10000;return true;}
static bool ready(void*c){(void)c;return fault!=4;}
static uint32_t take(void*c){(void)c;takes++;if(fault==5&&takes==5)tick=10000;
return fault==9?UINT32_MAX-1:fault==10?0:UINT32_MAX-2400;}
static void service(void*c){(void)c;services++;tick++;}
static bool stop(void*c){(void)c;stops++;if(fault==8)tick=10000;return fault!=7;}
int main(int argc,char**argv){fault=argc>1?atoi(argv[1]):0;bool attempted=false;observer_result out;
observer_io io={0,now,cancel,prepare,start,ready,take,service,stop};
unsigned status=observer_capture(&io,&attempted,fault==11?0:10000,&out);
unsigned count=out.count;unsigned cleanup=out.cleanup_verified;uint32_t last=count?out.decrements[count-1]:0;
observer_result second;unsigned again=observer_capture(&io,&attempted,10000,&second);
printf("{\"status\":%u,\"count\":%u,\"cleanup\":%u,\"prepare\":%d,\"start\":%d,\"stop\":%d,\"again\":%u,\"last\":%u}\n",status,count,cleanup,prepares,starts,stops,again,last);
return 0;}
'''

class ActualC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory();cls.folder=Path(cls.directory.name)
        (cls.folder/'harness.c').write_text(HARNESS);cls.binary=cls.folder/'harness'
        cc=shutil.which(os.environ.get('CC','cc'))
        if not cc or not str(Path(cc).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Use locked Nix CI compiler for actual C tests')
        subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(FIRMWARE),str(FIRMWARE/'observer.c'),str(cls.folder/'harness.c'),'-o',str(cls.binary)],check=True,capture_output=True,timeout=30)

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def probe(self,fault):
        return json.loads(subprocess.check_output([str(self.binary),str(fault)],text=True,timeout=10))

    def test_complete_native_capture_one_attempt_and_inert_refusal(self):
        r=self.probe(0);self.assertEqual((r['status'],r['count'],r['cleanup'],r['start'],r['stop'],r['again']),(0,16,1,1,1,1))
        r=self.probe(11);self.assertEqual((r['status'],r['prepare'],r['start'],r['stop']),(1,0,0,0))

    def test_late_prepare_start_and_stopped_source_never_qualify(self):
        for fault in (2,3,4):
            r=self.probe(fault);self.assertEqual(r['status'],2);self.assertEqual(r['count'],0);self.assertEqual(r['stop'],1)
        self.assertEqual(self.probe(2)['start'],0)

    def test_completed_late_sample_cancel_and_bad_period_remain_saved(self):
        for fault,status,count in ((5,2,5),(6,4,3),(9,5,1),(10,5,1)):
            r=self.probe(fault);self.assertEqual((r['status'],r['count'],r['stop']),(status,count,1))
        self.assertEqual(self.probe(5)['last'],2400)
        self.assertEqual(self.probe(10)['last'],0xffffffff)

    def test_prepare_and_cleanup_failures_or_late_cleanup_are_not_success(self):
        for fault,status in ((1,3),(7,3),(8,2)):
            r=self.probe(fault);self.assertEqual(r['status'],status);self.assertEqual(r['stop'],1)
        self.assertEqual(self.probe(7)['cleanup'],0)


SDK_HEADER=r'''
#ifndef SDK_FIXTURE_H
#define SDK_FIXTURE_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
enum { GPIO_IN,GPIO_OUT,GPIO_FUNC_SIO=5,GPIO_FUNC_PIO0=6,
       clk_sys=0,PICO_OK=0,PIO_FIFO_JOIN_RX=2 };
typedef struct { uint32_t dbg_padoe; } pio_hw_t;
typedef pio_hw_t *PIO;
extern pio_hw_t fixture_pio;
#define pio0 (&fixture_pio)
typedef struct { unsigned in,jmp,div_i,div_f,fifo; } pio_sm_config;
struct pio_program { unsigned unused; };
uint64_t time_us_64(void);
unsigned clock_get_hz(unsigned);
unsigned gpio_get_function(unsigned);
bool gpio_get_dir(unsigned);
bool gpio_get(unsigned);
void gpio_put(unsigned,bool);
void gpio_set_dir(unsigned,bool);
void gpio_set_function(unsigned,unsigned);
void gpio_disable_pulls(unsigned);
void busy_wait_us_32(unsigned);
bool pio_can_add_program(PIO,const struct pio_program*);
int pio_claim_unused_sm(PIO,bool);
unsigned pio_add_program(PIO,const struct pio_program*);
void pio_remove_program(PIO,const struct pio_program*,unsigned);
void pio_sm_unclaim(PIO,unsigned);
void sm_config_set_in_pins(pio_sm_config*,unsigned);
void sm_config_set_jmp_pin(pio_sm_config*,unsigned);
void sm_config_set_clkdiv_int_frac(pio_sm_config*,unsigned,unsigned);
void sm_config_set_fifo_join(pio_sm_config*,unsigned);
int pio_sm_init(PIO,unsigned,unsigned,const pio_sm_config*);
void pio_sm_set_consecutive_pindirs(PIO,unsigned,unsigned,unsigned,bool);
void pio_gpio_init(PIO,unsigned);
void pio_sm_set_enabled(PIO,unsigned,bool);
bool pio_sm_is_rx_fifo_empty(PIO,unsigned);
uint32_t pio_sm_get(PIO,unsigned);
void pio_sm_clear_fifos(PIO,unsigned);
void watchdog_update(void);
#endif
'''
SDK_HARNESS=r'''
#include "sdk.h"
#include "rp_input.h"
#include <stdio.h>
#include <stdlib.h>
pio_hw_t fixture_pio;
static int fault,writes_data,starts,claims,takes,waits;
static uint64_t tick;
static unsigned funcs[4]={5,5,5,5};
static bool dirs[4]={0,1,1,0},values[4]={0,1,1,0};
uint64_t time_us_64(void){return tick;}
unsigned clock_get_hz(unsigned c){(void)c;return fault==1?120000000:150000000;}
unsigned gpio_get_function(unsigned n){return funcs[n];}
bool gpio_get_dir(unsigned n){return dirs[n];}
bool gpio_get(unsigned n){return values[n];}
void gpio_put(unsigned n,bool v){if(n==3)writes_data++;
 if(n==1&&!v){if(dirs[3]||fixture_pio.dbg_padoe)abort();if(fault==7)tick=10000;}values[n]=v;}
void gpio_set_dir(unsigned n,bool v){if(n==3&&v)abort();dirs[n]=v;}
void gpio_set_function(unsigned n,unsigned f){funcs[n]=f;}
void gpio_disable_pulls(unsigned n){if(n!=3)abort();}
void busy_wait_us_32(unsigned n){tick+=n;waits++;if((fault==6&&waits==1)||(fault==9&&waits==2))tick=10000;}
bool pio_can_add_program(PIO p,const struct pio_program*q){(void)p;(void)q;return true;}
int pio_claim_unused_sm(PIO p,bool required){(void)p;if(required)abort();if(fault==4)return -1;claims++;return 0;}
unsigned pio_add_program(PIO p,const struct pio_program*q){(void)p;(void)q;return 0;}
void pio_remove_program(PIO p,const struct pio_program*q,unsigned o){(void)p;(void)q;(void)o;}
void pio_sm_unclaim(PIO p,unsigned s){(void)p;(void)s;claims--;}
void sm_config_set_in_pins(pio_sm_config*c,unsigned n){c->in=n;}
void sm_config_set_jmp_pin(pio_sm_config*c,unsigned n){c->jmp=n;}
void sm_config_set_clkdiv_int_frac(pio_sm_config*c,unsigned i,unsigned f){c->div_i=i;c->div_f=f;}
void sm_config_set_fifo_join(pio_sm_config*c,unsigned n){c->fifo=n;}
int pio_sm_init(PIO p,unsigned s,unsigned o,const pio_sm_config*c){(void)p;(void)s;(void)o;
 if(c->in!=3||c->jmp!=3||c->div_i!=1||c->div_f||c->fifo!=2)abort();return fault==5?-1:0;}
void pio_sm_set_consecutive_pindirs(PIO p,unsigned s,unsigned pin,unsigned count,bool out){(void)s;
 if(pin!=3||count!=1||out)abort();p->dbg_padoe=0;}
void pio_gpio_init(PIO p,unsigned n){funcs[n]=6;if(fault==3)p->dbg_padoe=1u<<3;}
void pio_sm_set_enabled(PIO p,unsigned s,bool enabled){(void)p;(void)s;if(enabled)starts++;}
bool pio_sm_is_rx_fifo_empty(PIO p,unsigned s){(void)p;(void)s;return fault==11;}
uint32_t pio_sm_get(PIO p,unsigned s){(void)p;(void)s;takes++;if(fault==8&&takes==5)tick=10000;return UINT32_MAX-2400;}
void pio_sm_clear_fifos(PIO p,unsigned s){(void)p;(void)s;}
void watchdog_update(void){tick++;}
static bool cancel(void*c){(void)c;return false;}
int main(int argc,char**argv){fault=argc>1?atoi(argv[1]):0;if(fault==2)dirs[3]=true;
 observer_io io;observer_rp_io(&io,cancel,NULL);bool attempted=false;observer_result r;
 unsigned status=observer_capture(&io,&attempted,10000,&r);
 printf("{\"status\":%u,\"count\":%u,\"cleanup\":%u,\"data_writes\":%d,\"starts\":%d,\"claims\":%d,\"CS\":%u}\n",status,r.count,r.cleanup_verified,writes_data,starts,claims,values[1]);
 return 0;}
'''

class ActualSDKBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory();folder=Path(cls.directory.name)
        (folder/'sdk.h').write_text(SDK_HEADER)
        for name in ('pico/stdlib.h','hardware/clocks.h','hardware/pio.h','hardware/watchdog.h'):
            path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('#include "sdk.h"\n')
        (folder/'period.pio.h').write_text('''#include "sdk.h"
static const struct pio_program forgix_clock_period_program={0};
static inline pio_sm_config forgix_clock_period_program_get_default_config(unsigned o){(void)o;pio_sm_config c={0};return c;}
''')
        (folder/'harness.c').write_text(SDK_HARNESS);cls.binary=folder/'harness'
        cc=shutil.which(os.environ.get('CC','cc'))
        if not cc or not str(Path(cc).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Locked native Nix compiler required')
        subprocess.run([cc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(folder),'-I',str(FIRMWARE),str(FIRMWARE/'observer.c'),str(FIRMWARE/'rp_input.c'),str(folder/'harness.c'),'-o',str(cls.binary)],check=True,capture_output=True,timeout=30)

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def probe(self,fault):
        return json.loads(subprocess.check_output([str(self.binary),str(fault)],text=True,timeout=10))

    def test_actual_sdk_body_never_drives_data_and_releases_owned_PIO(self):
        r=self.probe(0)
        self.assertEqual((r['status'],r['count'],r['cleanup'],r['data_writes'],r['starts'],r['claims'],r['CS']),(0,16,1,0,1,0,1))

    def test_actual_sdk_wrong_clock_or_existing_output_is_inert(self):
        for fault in (1,2):
            r=self.probe(fault);self.assertEqual((r['status'],r['starts'],r['data_writes'],r['claims']),(3,0,0,0))

    def test_actual_sdk_OE_claim_init_and_late_paths_preserve_input_cleanup(self):
        for fault in (3,4,5,6,7,8,9,11):
            r=self.probe(fault);self.assertIn(r['status'],(2,3));self.assertEqual((r['data_writes'],r['claims'],r['CS']),(0,0,1))
        self.assertEqual(self.probe(8)['count'],5)

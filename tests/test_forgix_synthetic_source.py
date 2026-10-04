"""Actual HDL source/control/FIFO simulations; no vendor compiler or device.

Icarus executes the committed Verilog. Python checks literal bus fixtures and
zlib's independent CRC implementation, not a second copy of the HDL generator.
Scaled SYSTEM_HZ shortens simulation; production wrapper pins32MHz.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import forgix_synthetic_gateware as generator

COMMON = r'''
module tb;
  reg clk=0, reset=1, cyc=0, stb=0, we=0;
  reg [11:0] addr=0; reg [31:0] data=0; reg [3:0] sel=15;
  wire ack,err; wire [31:0] q;
  localparam HZ=12800;
  forgix_synthetic_source #(.SYSTEM_HZ(HZ)) dut(clk,reset,cyc,stb,we,addr,data,sel,ack,err,q);
  always #5 clk=~clk;
  task wr(input [11:0] a,input [31:0] v,input expected_error);
    begin
      @(negedge clk); addr=a;data=v;we=1;cyc=1;stb=1;
      @(posedge clk);#1;if(!ack || err!==expected_error)$fatal(1,"write %h ack/err %b/%b",a,ack,err);
      @(negedge clk);cyc=0;stb=0;we=0;
      @(posedge clk);#1;
    end
  endtask
  task rd(input [11:0] a,output [31:0] v);
    begin
      @(negedge clk);addr=a;we=0;cyc=1;stb=1;
      @(posedge clk);#1;if(!ack || err)$fatal(1,"read %h failed",a);v=q;
      @(negedge clk);cyc=0;stb=0;
      @(posedge clk);#1;
    end
  endtask
  task setup(input [31:0] period,input [31:0] count);
    begin
      wr('h010,period,0);wr('h014,count,0);
      wr('h018,'h01234567,0);wr('h01c,'h89abcdef,0);
      wr('h020,'h13579bdf,0);wr('h024,'h2468ace0,0);
    end
  endtask
  reg [31:0] st,s,t,p,c,g,e,d,o,l,h,id0,id1;
  task snapshot;
    begin
      wr('h00c,4,0);rd('h05c,g);rd('h060,e);rd('h064,d);rd('h068,o);rd('h074,l);rd('h078,h);
      if(g!==e+d || e!==o+l || h>64 || l>64)$fatal(1,"counter reconciliation");
    end
  endtask
  task take;
    begin
      rd('h034,s);rd('h038,t);rd('h03c,p);rd('h044,c);
      $display("R %08x %08x %08x %08x",s,t,p,c);
      wr('h040,s,0);rd('h048,o);
    end
  endtask
  initial begin
    repeat(5)@(posedge clk);@(negedge clk);reset=0;
    SCRIPT
    $display("PASS");$finish;
  end
  initial begin #20000000;$fatal(1,"simulation deadline");end
endmodule
'''


class ActualHDL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.iverilog, cls.vvp = shutil.which('iverilog'), shutil.which('vvp')
        if not cls.iverilog or not cls.vvp or not str(Path(cls.iverilog).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Use locked nix develop .#forgix for Icarus HDL simulations')

    def run_hdl(self, script):
        with tempfile.TemporaryDirectory(prefix='forgix-source-hdl-') as directory:
            folder=Path(directory);tb=folder/'tb.v';tb.write_text(COMMON.replace('SCRIPT',script))
            subprocess.run([self.iverilog,'-g2012','-s','tb','-o',str(folder/'sim'),str(ROOT/generator.CORE),str(tb)],
                           check=True,capture_output=True,timeout=30)
            result=subprocess.run([self.vvp,str(folder/'sim')],check=True,capture_output=True,text=True,timeout=30)
            self.assertIn('PASS',result.stdout)
            return result.stdout

    def test_all_three_rates_exact_finite_records_crc_ticks_and_pop_readback(self):
        for period,count in [(800,960),(200,3840),(100,7680)]:
            with self.subTest(period=period):
                out=self.run_hdl(f'''
                    setup({period},{count});wr('h00c,1,0);
                    $display("BEGIN %0d",dut.start_tick);
                    begin : drain
                      integer loops;reg[31:0] previous_pop;
                      previous_pop=0;
                      for(loops=0;loops<1000000;loops=loops+1)begin
                        rd('h028,st);
                        if(st[3])begin take;if(o!=previous_pop+1)$fatal(1,"POP readback");previous_pop=o;end
                        if(st[2] && dut.level==0)disable drain;
                      end
                      $fatal(1,"not finite");
                    end
                    snapshot;
                    if(g!={count} || e!={count} || d!=0 || o!={count} || l!=0)$fatal(1,"rate counters");
                    repeat(2000)@(posedge clk);snapshot;
                    if(g!={count})$fatal(1,"generation continued after target");
                    wr('h00c,1,1);wr('h010,{period},1);
                    $display("END %0d %0d %0d %0d %0d",g,e,d,o,l);
                ''')
                start=int(next(line.split()[1] for line in out.splitlines() if line.startswith('BEGIN ')))
                parsed=[tuple(int(v,16) for v in line.split()[1:]) for line in out.splitlines() if line.startswith('R ')]
                self.assertEqual(len(parsed),count)
                nonce_xor=0x01234567^0x89abcdef^0x13579bdf^0x2468ace0
                for expected,(seq,tick,pattern,crc) in enumerate(parsed):
                    self.assertEqual(seq,expected)
                    self.assertEqual(tick,(start+(seq+1)*period)&0xffffffff)
                    rotated=((seq<<7)|(seq>>25))&0xffffffff
                    self.assertEqual(pattern,seq^rotated^nonce_xor^0x46534731)
                    self.assertEqual(crc,zlib.crc32(struct.pack('<III',seq,tick,pattern)))

    def test_backpressure_full_fifo_stable_head_and_exact_accounted_loss(self):
        out=self.run_hdl(r'''
            setup(800,960);wr('h00c,1,0);
            wait(dut.level==64);repeat(10000)@(posedge clk);
            rd('h034,s);rd('h038,t);rd('h03c,p);rd('h044,c);
            if(s!=0)$fatal(1,"head overwritten");
            repeat(10000)@(posedge clk);rd('h034,st);if(st!=s)$fatal(1,"head unstable");
            wait(dut.done);snapshot;
            if(g!=960 || e!=64 || d!=896 || o!=0 || l!=64 || h!=64)$fatal(1,"full counters");
            repeat(64)begin take;end
            snapshot;if(o!=64 || l!=0)$fatal(1,"drain reconciliation");
        ''')
        records=[tuple(int(v,16) for v in line.split()[1:]) for line in out.splitlines() if line.startswith('R ')]
        self.assertEqual([r[0] for r in records],list(range(64)))
        for seq,tick,pattern,crc in records:
            self.assertEqual(crc,zlib.crc32(struct.pack('<III',seq,tick,pattern)))

    def test_wrong_stale_empty_pop_and_head_valid_delay(self):
        self.run_hdl(r'''
            wr('h040,0,1);setup(800,960);wr('h00c,1,0);
            wait(dut.generated_count>=2);repeat(3)@(posedge clk);
            rd('h034,s);if(s!=0)$fatal(1,"first");wr('h040,1,1);
            rd('h034,s);if(s!=0)$fatal(1,"wrong POP moved head");
            take;wr('h040,0,1);rd('h034,s);if(s!=1)$fatal(1,"stale POP moved head");
            snapshot;rd('h06c,p);if(p!=3 || o!=1)$fatal(1,"refusal count");
        ''')

    def test_held_pop_request_is_acknowledged_once_and_reset_clears_state(self):
        self.run_hdl(r'''
            setup(100,7680);wr('h00c,1,0);wait(dut.generated_count>=3);
            repeat(3)@(posedge clk);
            @(negedge clk);addr='h040;data=0;we=1;cyc=1;stb=1;
            @(posedge clk);#1;if(!ack || err)$fatal(1,"first held POP");
            repeat(10)begin @(posedge clk);#1;
              if(ack || dut.popped_count!=1 || dut.refused_pop!=0)$fatal(1,"held request repeated");
            end
            @(negedge clk);cyc=0;stb=0;we=0;reset=1;
            repeat(3)@(posedge clk);@(negedge clk);reset=0;
            rd('h028,st);rd('h034,s);snapshot;
            if(st!=0 || s!=0 || g!=0 || e!=0 || o!=0 || l!=0)$fatal(1,"stale post-reset state");
        ''')

    def test_snapshot_is_coherent_immutable_while_source_runs(self):
        self.run_hdl(r'''
            setup(100,7680);wr('h00c,1,0);wait(dut.generated_count>=7);snapshot;
            rd('h04c,id0);s=g;t=l;repeat(1000)@(posedge clk);
            rd('h05c,p);rd('h074,c);rd('h04c,id1);
            if(p!=s || c!=t || id1!=id0)$fatal(1,"snapshot changed without SNAPSHOT");
            snapshot;rd('h04c,id1);if(id1!=id0+1 || g<=s)$fatal(1,"snapshot not refreshed");
        ''')

    def test_pause_is_one_bounded_pop_block_without_stopping_generator(self):
        self.run_hdl(r'''
            setup(100,7680);wr('h00c,1,0);wait(dut.head_valid);
            wr('h00c,8,0);s=dut.generated_count;
            wr('h040,0,1);wr('h00c,8,1);
            if(!dut.pause_active)$fatal(1,"no pause");
            wait(!dut.pause_active);repeat(3)@(posedge clk);
            if(dut.generated_count<=s || dut.level<12)$fatal(1,"pause hid generation/backlog");
            if(dut.pause_end-dut.pause_begin!=1280)$fatal(1,"pause bound");
            take;wr('h00c,8,1);
        ''')

    def test_start_refusals_window_no_restart_and_no_bad_select_mutation(self):
        self.run_hdl(r'''
            wr('h00c,1,1);wr('h010,800,1);wr('h00c,1,1);
            if(dut.running || dut.accepted || !dut.attempted)$fatal(1,"failed intent started");
        ''')
        self.run_hdl(r'''
            setup(799,960);wr('h00c,1,1);if(dut.running)$fatal(1,"unsupported rate");
        ''')
        self.run_hdl(r'''
            setup(800,961);wr('h00c,1,1);if(dut.running)$fatal(1,"unbounded target");
        ''')
        self.run_hdl(r'''
            setup(800,960);wait(dut.tick>=384000);wr('h00c,1,1);
            if(dut.running)$fatal(1,"late start");
        ''')
        self.run_hdl(r'''
            sel=1;wr('h010,800,1);sel=15;rd('h010,s);if(s!=0)$fatal(1,"partial mutation");
            wr('h011,800,1);wr('h000,0,1);wr('h0fc,0,1);wr('h00c,3,1);
            if(dut.attempted)$fatal(1,"bad control consumed valid intent");
        ''')

    def test_early_stop_freezes_source_and_bounded_drain_expires(self):
        self.run_hdl(r'''
            setup(800,960);wr('h00c,1,0);wait(dut.generated_count>=4);
            wr('h00c,2,0);s=dut.generated_count;repeat(10000)@(posedge clk);
            if(dut.generated_count!=s || !dut.done || dut.running)$fatal(1,"STOP did not freeze");
            wr('h00c,1,1);wait(dut.drain_expired);wr('h040,0,1);
            if(dut.level!=4 || dut.popped_count!=0)$fatal(1,"late drain moved data");
            snapshot;if(g!=4 || e!=4 || d!=0 || o!=0 || l!=4)$fatal(1,"STOP counters");
        ''')

    def test_pop_push_same_full_cycle_does_not_drop_or_overwrite(self):
        self.run_hdl(r'''
            setup(100,7680);wr('h00c,1,0);wait(dut.level==64);
            // Aim the request at the actual source's next due edge, not a
            // second software generator. This exercises concurrent full POP/PUSH.
            @(negedge clk);
            while(dut.tick-dut.start_tick<dut.next_due)@(negedge clk);
            addr='h040;data=0;we=1;cyc=1;stb=1;
            @(posedge clk);#1;if(!ack || err)$fatal(1,"simultaneous POP refused");
            @(negedge clk);cyc=0;stb=0;we=0;
            @(posedge clk);#1;
            if(dut.generated_count!=65 || dut.enqueued_count!=65 || dut.dropped_count!=0 || dut.popped_count!=1 || dut.level!=64)
              $fatal(1,"full concurrent counts %d %d %d",dut.generated_count,dut.enqueued_count,dut.dropped_count);
            wr('h00c,2,0);
            repeat(64)begin take;end
            snapshot;if(l!=0 || o!=65)$fatal(1,"pointer wrap drain");
        ''')

    def compare_original(self, script):
        # Undo only this reviewed optimization, then require every byte to
        # match the immutable original source. Execute both real HDL modules;
        # do not replace source behavior with a software timing model.
        current=(ROOT/generator.CORE).read_text()
        original=current.replace('    reg [63:0] drain_until;\n','').replace(
            'tick >= drain_until','tick >= stop_tick + DRAIN_CYCLES').replace(
            '            drain_until <= 0;\n','').replace(
            '                            2: if (running) begin\n'
            '                                   running <= 0; done <= 1; stop_tick <= tick;\n'
            '                                   drain_until <= tick + DRAIN_CYCLES;\n'
            '                               end\n',
            '                            2: if (running) begin running <= 0; done <= 1; stop_tick <= tick; end\n').replace(
            '                    drain_until <= tick + DRAIN_CYCLES;\n','')
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         'ec067fbbe7ebcab49c4924afda7a8303ef581945924db2658b77ff807bdaf48c')
        reference=original.replace('module forgix_synthetic_source #(',
                                   'module source_reference #(',1)
        fields=('tick,start_tick,stop_tick,seen,attempted,accepted,running,done,'
                'pause_attempted,pause_begin,pause_end,generated_count,enqueued_count,'
                'dropped_count,popped_count,refused_pop,refused_command,level,high_water,'
                'next_due,head_wait,head,snapshot_id,snapshot_tick,snapshot_start,'
                'snapshot_stop,snap_generated,snap_enqueued,snap_dropped,snap_popped,'
                'snap_refused_pop,snap_refused_command,snap_state,snap_level,snap_high_water').split(',')
        monitor='\n'.join(f'if(dut.{n}!==reference.{n})$fatal(1,"original mismatch {n}");' for n in fields)
        extra='''
  wire ref_ack,ref_err;wire[31:0] ref_q;
  source_reference #(.SYSTEM_HZ(HZ)) reference(clk,reset,cyc,stb,we,addr,data,sel,ref_ack,ref_err,ref_q);
  always @(posedge clk)begin #2;
    if({ack,err,q}!=={ref_ack,ref_err,ref_q})$fatal(1,"original bus mismatch");
    if(dut.drain_expired!==reference.drain_expired)$fatal(1,"drain edge mismatch");
    MONITOR
  end
  reg[63:0] deadline,stopped;
'''.replace('MONITOR',monitor)
        tb=COMMON.replace('  reg [31:0] st,s,t,p,c,g,e,d,o,l,h,id0,id1;',extra+'  reg [31:0] st,s,t,p,c,g,e,d,o,l,h,id0,id1;').replace('SCRIPT',script)
        with tempfile.TemporaryDirectory(prefix='forgix-source-equivalence-') as directory:
            folder=Path(directory);(folder/'reference.v').write_text(reference);(folder/'tb.v').write_text(tb)
            subprocess.run([self.iverilog,'-g2012','-s','tb','-o',str(folder/'sim'),str(ROOT/generator.CORE),
                            str(folder/'reference.v'),str(folder/'tb.v')],check=True,capture_output=True,timeout=30)
            result=subprocess.run([self.vvp,str(folder/'sim')],check=True,capture_output=True,text=True,timeout=30)
            self.assertIn('PASS',result.stdout)

    def test_stop_drain_exact_edges_carries_and_wrapping_match_original(self):
        for stop in ('dut.tick', "64'h00000000fffff000", "64'hfffffffffffff000"):
            for offset in (-1,0,1):
                with self.subTest(stop=stop,offset=offset):
                    self.compare_original(f'''
                        setup(800,960);wr('h00c,1,0);wait(dut.generated_count>=3);
                        @(negedge clk);dut.tick={stop};reference.tick=dut.tick;
                        dut.start_tick=dut.tick;reference.start_tick=dut.tick;
                        wr('h00c,2,0);stopped=dut.stop_tick;
                        deadline=stopped+64'd64000;
                        if(dut.drain_until!==deadline)$fatal(1,"STOP deadline");
                        @(negedge clk);dut.tick=deadline{'-' if offset<0 else '+'}64'd{abs(offset)};reference.tick=dut.tick;
                        addr='h040;data=0;we=1;cyc=1;stb=1;
                        @(posedge clk);#1;if(!ack || err!==1'b{int(offset>=0)})$fatal(1,"boundary POP");
                        if(dut.popped_count!={int(offset<0)})$fatal(1,"boundary consumption");
                        @(negedge clk);cyc=0;stb=0;we=0;
                        @(posedge clk);#1;snapshot;
                        if(dut.snapshot_stop!==stopped || dut.snap_generated!=3)$fatal(1,"STOP snapshot");
                        wr('h00c,2,1);wr('h00c,1,1);
                    ''')

    def test_natural_completion_concurrent_pop_or_stop_match_original(self):
        # Deposit an accelerated, reconciled final-record checkpoint into both
        # actual modules. Normal full-target record tests above remain separate.
        for tick in ('dut.tick', "64'h00000000fffff000", "64'hfffffffffffff000"):
            for command in ('none','pop','stop'):
                with self.subTest(tick=tick,command=command):
                    boundary={'none':-1,'pop':0,'stop':1}[command]
                    request={'none':'cyc=0;stb=0;we=0;',
                             'pop':"addr='h040;data=0;we=1;cyc=1;stb=1;",
                             'stop':"addr='h00c;data=2;we=1;cyc=1;stb=1;"}[command]
                    self.compare_original(f'''
                        setup(100,7680);wr('h00c,1,0);wait(dut.generated_count>=3);
                        @(negedge clk);dut.tick={tick};reference.tick=dut.tick;stopped=dut.tick;
                        dut.start_tick=dut.tick-100;reference.start_tick=dut.start_tick;
                        dut.next_due=100;reference.next_due=100;
                        dut.generated_count=7679;reference.generated_count=7679;
                        dut.dropped_count=7679-dut.enqueued_count;reference.dropped_count=dut.dropped_count;
                        {request}
                        @(posedge clk);#1;
                        if(!dut.done || dut.running || dut.generated_count!=7680)$fatal(1,"finite completion");
                        if(dut.stop_tick!==stopped || dut.drain_until!==stopped+64'd64000)$fatal(1,"completion stamp");
                        if(dut.popped_count!={int(command=='pop')})$fatal(1,"completion concurrent POP");
                        @(negedge clk);cyc=0;stb=0;we=0;
                        @(posedge clk);#1;snapshot;
                        if(g!=7680 || e!=o+l)$fatal(1,"completion counters");
                        deadline=stopped+64'd64000;
                        @(negedge clk);dut.tick=deadline{'-' if boundary<0 else '+'}64'd{abs(boundary)};
                        reference.tick=dut.tick;
                        addr='h040;data=dut.head[31:0];we=1;cyc=1;stb=1;
                        @(posedge clk);#1;
                        if(!ack || err!==1'b{int(boundary>=0)})$fatal(1,"completion drain boundary");
                        if(dut.popped_count!={int(command=='pop')+int(boundary<0)})$fatal(1,"completion drain consumption");
                        @(negedge clk);cyc=0;stb=0;we=0;
                        @(posedge clk);#1;snapshot;
                    ''')

    def test_boundary_snapshot_is_pre_edge_and_reset_clears_deadline(self):
        self.compare_original(r'''
            setup(800,960);wr('h00c,1,0);wait(dut.generated_count>=3);wr('h00c,2,0);
            stopped=dut.stop_tick;deadline=stopped+64'd64000;
            @(negedge clk);dut.tick=deadline-1;reference.tick=dut.tick;
            addr='h00c;data=4;we=1;cyc=1;stb=1;
            @(posedge clk);#1;
            if(!ack || err || dut.snap_state[5] || dut.snapshot_tick!==deadline-1 || !dut.drain_expired)
                $fatal(1,"snapshot must retain pre-edge expiration state");
            @(negedge clk);cyc=0;stb=0;we=0;reset=1;
            repeat(3)@(posedge clk);@(negedge clk);reset=0;
            rd('h028,st);snapshot;
            if(st!=0 || dut.drain_until!=0 || dut.stop_tick!=0 || dut.drain_expired)$fatal(1,"reset deadline");
            wr('h00c,2,1);setup(800,960);wr('h00c,1,0);wait(dut.generated_count>=1);
            wr('h00c,2,0);if(dut.drain_expired)$fatal(1,"stale expired latch");
        ''')


class Wrapper(unittest.TestCase):
    def test_production_soc_adds_no_pins_and_preserves_old_register_bank_guard(self):
        from litex.build.generic_platform import GenericPlatform
        from litex_boards.platforms import adiuvo_forgix as board
        import forgix_fpga_candidate as original
        class Platform(GenericPlatform):
            default_clk_freq=32000000
            def __init__(self):super().__init__('T8F49I2',board._io,board._connectors)
            def do_finalize(self,fragment):pass
        soc=generator.make_soc(Platform);soc.finalize()
        conversion=soc.platform.get_verilog(soc.get_fragment(),name='source_fixture')
        pins={name:pins for name,pins,others,res in soc.platform.resolve_signals(conversion.ns)[0]}
        self.assertEqual(pins,original.PINS)
        self.assertEqual(soc.csr_regions['registers'].origin,0x1000)
        self.assertEqual(soc.bus.regions['synthetic_source'].origin,0x10000)
        self.assertEqual(soc.bus.regions['synthetic_source'].size,0x1000)
        literal=re.search(r"\.SYSTEM_HZ\((\d+)'h([0-9a-f]+)\)",str(conversion).replace(' ',''))
        self.assertIsNotNone(literal)
        self.assertEqual(int(literal[2],16),32000000)
        self.assertEqual(soc.registers.counter.size,32);self.assertEqual(soc.registers.scratch.size,32)
        # Compile and execute the complete generated wrapper through its
        # physical SPI pads. This catches reset, map translation, interconnect
        # and module wiring errors that direct local-bus core tests cannot.
        tb=r'''
module tb;
 reg clk=0,sck=0,cs=1,oe=1,out=0;wire io;
 assign io=oe?out:1'bz;
 source_fixture dut(.clk32(clk),.spibone_clk(sck),.spibone_cs_n(cs),.spibone_mosi(io));
 always #5 clk=~clk;
 reg[7:0] rx[0:7];integer i,j,k;reg[71:0] bits;
 task transfer(input[7:0] cmd,input[31:0] address,input[31:0] value,output[31:0] result);
 begin
   cs=1;sck=0;oe=1;#1000;cs=0;#100;
   bits={cmd,address,value};
   for(i=71;i>=(cmd==0?0:32);i=i-1)begin
     out=bits[i];#100;sck=1;#100;if(i!=(cmd==0?0:32))sck=0;
   end
   oe=0;#800;sck=0;#100;
   for(j=0;j<8;j=j+1)begin
     rx[j]=0;
     for(k=7;k>=0;k=k-1)begin
       sck=1;#100;rx[j][k]=io;sck=0;#100;
     end
   end
   result=0;
   begin : find
     for(j=0;j<4;j=j+1)if(rx[j]===cmd)begin
       result={rx[j+1],rx[j+2],rx[j+3],rx[j+4]};disable find;
     end
     $fatal(1,"SPI response absent");
   end
   cs=1;sck=0;#1000;oe=1;
 end
 endtask
 reg[31:0] value,earlier;
 initial begin
   #1000;
   transfer(1,'h10000,0,value);if(value!=='h46534731)$fatal(1,"new ABI/address route");
   transfer(1,'h10028,0,value);if(value!==0)$fatal(1,"source cold-start reset");
   transfer(1,'h1002c,0,value);if(value!==0)$fatal(1,"cold FIFO");
   transfer(0,'h1004,'h1234abcd,value);
   transfer(1,'h1004,0,value);if(value!=='h1234abcd)$fatal(1,"old scratch ABI changed");
   transfer(1,'h1000,0,earlier);transfer(1,'h1000,0,value);
   if(value<=earlier)$fatal(1,"old counter stopped");
   transfer(0,'h10010,2000000,value);
   transfer(1,'h10010,0,value);if(value!==2000000)$fatal(1,"new config address translation");
   $display("PASS");$finish;
 end
 initial begin #1000000;$fatal(1,"integration timeout");end
endmodule
'''
        with tempfile.TemporaryDirectory(prefix='forgix-wrapper-hdl-') as directory:
            folder=Path(directory);previous=Path.cwd()
            try:
                os.chdir(folder);conversion.write('top.v')
            finally:os.chdir(previous)
            (folder/'tb.v').write_text(tb)
            subprocess.run([shutil.which('iverilog'),'-g2012','-s','tb','-o',str(folder/'sim'),
                str(folder/'top.v'),str(ROOT/generator.CORE),str(folder/'tb.v')],
                check=True,capture_output=True,timeout=30)
            result=subprocess.run([shutil.which('vvp'),str(folder/'sim')],cwd=folder,
                check=True,capture_output=True,text=True,timeout=30)
            self.assertIn('PASS',result.stdout)

    def test_generator_requires_committed_fresh_private_inputs(self):
        hashes=generator.committed_inputs()
        self.assertEqual(hashes[generator.CORE],hashlib.sha256((ROOT/generator.CORE).read_bytes()).hexdigest())
        with patch.object(generator.subprocess,'check_output',return_value=b'foreign'):
            with self.assertRaisesRegex(ValueError,'Commit'):generator.committed_inputs()
        with self.assertRaisesRegex(ValueError,'private|Private|Fresh'):
            generator.generate(Path('/tmp/unsupported-forgix-source-output'))
        # Inspect the generator's imports in a fresh interpreter. Combined
        # unittest discovery has unrelated repository helpers in sys.modules;
        # they are not part of this generator's execution input closure.
        script = r'''
import sys
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root/'tools'))
import forgix_synthetic_gateware as generator
try:
    generator.generate(Path('/tmp/unsupported-forgix-source-output'))
except ValueError:
    pass
else:
    raise AssertionError('Unsupported output was not refused')
for module in tuple(sys.modules.values()):
    path = getattr(module, '__file__', None)
    if path and Path(path).resolve().is_relative_to(root/'tools'):
        assert str(Path(path).resolve().relative_to(root)) in generator.INPUTS
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

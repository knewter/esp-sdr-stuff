#!/usr/bin/env python3
"""Narrow offline synthetic-stream reset audit; no hardware or load admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
from build_forgix_usb_ram import ROOT,SDK,TINY,fresh,sha
from build_forgix_synthetic_stream import FILES
from forgix_usb_ram_artifact import inspect_elf

NAR='sha256-X9mPMzmeJzuhHp7VbTc8BLoF1LE41YOLxK0dAwgYEds='
EXPORTS={'build.log','wire.pio.h','disassembly.txt','symbols.txt','forgix_synthetic_stream.map','forgix_synthetic_stream.elf'}
EARLY=bytes.fromhex('0648dff828c0064b064a0749c0f800c01a608b6832ea0303fbd17047')
RUNNER=bytes.fromhex('38b5054c054dac4204d254f8043b9847ac42fad338bd00bf')
SDK_FILES=('src/rp2_common/pico_runtime_init/runtime_init.c',
 'src/rp2350/hardware_regs/include/hardware/regs/resets.h',
 'src/rp2350/hardware_regs/include/hardware/regs/io_bank0.h',
 'src/rp2350/hardware_regs/include/hardware/regs/pads_bank0.h')

def require(ok,message):
 if not ok:raise ValueError(message)

def regular(path,limit):
 path=Path(path)
 require(not any(p.is_symlink() for p in (path,*path.parents)),'symlinked audit input')
 s=path.stat();require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<=limit,'invalid audit input')
 return path

def linked_resets(elf,layout,sdk):
 """Recognize fixed loaded instructions/table only; not a whole CFG audit."""
 def memory(address,size):
  p=next((p for p in layout['load_segments'] if p['vaddr']<=address and address+size<=p['vaddr']+p['filesz']),None)
  require(p is not None and size>0,'startup reference outside loaded bytes')
  off=p['offset']+address-p['vaddr'];return elf[off:off+size]
 def word(address):return struct.unpack('<I',memory(address,4))[0]
 symbols=layout['symbols']
 names=('runtime_init_early_resets','runtime_init_post_clock_resets','runtime_run_initializers')
 require(all(n in symbols for n in names),'missing linked reset function')
 early=symbols[names[0]]&~1;runner=symbols[names[2]]&~1
 require(memory(early,len(EARLY))==EARLY,'unreviewed early-reset instructions')
 set_addr,clear_addr,release,base,asserted=[word(early+x) for x in (28,32,36,40,44)]
 require((set_addr,clear_addr,base)==(0x40022000,0x40023000,0x40020000),'unreviewed reset register mapping')
 require(memory(runner,len(RUNNER))==RUNNER,'unreviewed initializer-loop instructions')
 begin,end=word(runner+24),word(runner+28)
 require(begin<end and (end-begin)%4==0 and end-begin<=1024,'invalid initializer table')
 table=struct.unpack('<'+'I'*((end-begin)//4),memory(begin,end-begin))
 bound=[]
 for name in names[:2]:
  slot=symbols.get('__pre_init_'+name)
  require(type(slot) is int and begin<=slot<end and (slot-begin)%4==0 and word(slot)==symbols[name] and
          table.count(symbols[name])==1,'initializer table does not bind unique reset function')
  bound.append({'function':name,'function_address':symbols[name],'slot_address':slot})
 def macro(text,name):
  matches=re.findall(r'^#define '+re.escape(name)+r'\s+_u\((0x[0-9a-f]+)\)',text,re.M)
  require(len(matches)==1,'missing or duplicate SDK reset macro');return int(matches[0],16)
 headers=[regular(sdk/n,8*1024**2).read_text() for n in SDK_FILES]
 resets,io,pads=headers[1:]
 blocks={n:{'asserted_by_early_reset':bool(asserted&macro(resets,'RESETS_RESET_'+n+'_BITS')),
            'released_by_early_reset':bool(release&macro(resets,'RESETS_RESET_'+n+'_BITS'))}
         for n in ('IO_BANK0','PADS_BANK0','PIO0')}
 require(all(all(v.values()) for v in blocks.values()),'reviewed peripheral reset behavior changed')
 defaults={str(pin):{'function_select':macro(io,f'IO_BANK0_GPIO{pin}_CTRL_FUNCSEL_RESET'),
     'pad_isolated':bool(macro(pads,f'PADS_BANK0_GPIO{pin}_ISO_RESET')),
     'pull_down':bool(macro(pads,f'PADS_BANK0_GPIO{pin}_PDE_RESET')),
     'pull_up':bool(macro(pads,f'PADS_BANK0_GPIO{pin}_PUE_RESET'))} for pin in (1,2,3,4,5,19)}
 return {'initializer_bindings':bound,'initializer_table_begin':begin,'initializer_table_end':end,
     'recognized_early_reset_address':early,'recognized_initializer_runner_address':runner,
     'early_assert_mask':hex(asserted),'early_release_mask':hex(release),'reset_blocks':blocks,
     'documented_gpio_reset_defaults':defaults,'sdk_source_sha256':{n:sha(sdk/n) for n in SDK_FILES}}

def audit(folder):
 folder=Path(folder).absolute()
 require(folder.is_relative_to(ROOT/'.scratch') and folder!=ROOT/'.scratch' and '..' not in folder.parts,'private artifact directory required')
 manifest=regular(folder/'manifest.json',512*1024);m=json.loads(manifest.read_bytes())
 require(m.get('kind')=='forgix-synthetic-stream-offline-build' and m.get('status')=='built_layout_guard_passed' and
         m.get('sdk_revision')==SDK and m.get('tinyusb_revision')==TINY and m.get('sdk_nar_hash')==NAR and
         m.get('linked_embedded_image_verified') is True and m.get('inputs_unchanged_after_build') is True and
         m.get('hardware_opened') is False and m.get('loading_admitted') is False,'successful pinned stream build required')
 exports=m.get('artifact_sha256');sources=m.get('source_sha256');revision=m.get('source_commit')
 require(type(exports) is dict and set(exports)==EXPORTS and type(sources) is dict and set(sources)==set(FILES) and
         type(revision) is str and re.fullmatch('[0-9a-f]{40}',revision),'complete export/source bindings required')
 for n,h in exports.items():
  require(type(h) is str and re.fullmatch('[0-9a-f]{64}',h) and sha(regular(folder/n,16*1024**2))==h,'exported artifact differs')
 for n,h in sources.items():
  require(type(h) is str and re.fullmatch('[0-9a-f]{64}',h),'invalid source hash')
  recorded=subprocess.check_output(['git','show',revision+':'+n],cwd=ROOT,timeout=10)
  require(hashlib.sha256(recorded).hexdigest()==h,'committed source binding differs')
 elf=(folder/'forgix_synthetic_stream.elf').read_bytes();layout=inspect_elf(elf,application='synthetic-stream')
 require(layout==m.get('layout'),'stream ELF layout differs')
 sdk=Path(m['sdk_path'])
 require(sdk.is_absolute() and sdk.is_relative_to('/nix/store') and '..' not in sdk.parts and
         not any(p.is_symlink() for p in (sdk,*sdk.parents)),'immutable SDK directory required')
 require(subprocess.check_output(['nix','hash','path',str(sdk)],text=True,timeout=60).strip()==NAR,'SDK NAR differs')
 reset=linked_resets(elf,layout,sdk)
 return {'kind':'offline-synthetic-linked-startup-audit','result':'recognized_reset_transition_requires_qualification',
     'source_commit':revision,'elf_sha256':sha(folder/'forgix_synthetic_stream.elf'),'manifest_sha256':sha(manifest),
     'sdk_revision':SDK,'tinyusb_revision':TINY,'sdk_nar_hash':NAR,**reset,
     'hardware_opened':False,'loading_admitted':False,'whole_boot_path_qualified':False,
     'conclusion':'Linked GPIO/pad/PIO reset sequence and initializer slots are recognized. Prior FPGA image/pin continuity is not established. Main watchdog does not protect pre-main startup.',
     'limits':'Fixed reset instructions/table plus pinned SDK reset metadata only. Not complete boot-ROM/initializer CFG, application sequencing, external pulls/levels, physical timing, image continuity, delivery or recovery proof.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();os.umask(0o077);result=audit(a.artifact);out=fresh(a.output);receipt=out/'startup-audit.json'
 receipt.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':result['result'],'receipt_sha256':sha(receipt),'hardware_opened':False,'loading_admitted':False}))
if __name__=='__main__':main()

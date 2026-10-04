#!/usr/bin/env python3
"""Offline audit of the pinned bridge startup sequence; never opens hardware.

Recognizes one linked early-reset instruction sequence, not arbitrary ARM code
or electrical behavior. A different compiler/sequence requires new review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from build_forgix_usb_ram import ROOT,SDK,fresh,sha
from forgix_usb_ram_artifact import inspect_elf

def audit(folder):
 folder=Path(folder).resolve(strict=True)
 if not folder.is_relative_to(ROOT/'.scratch'):raise ValueError('private build artifacts required')
 m=json.loads((folder/'manifest.json').read_text());elf=(folder/'forgix_spi_bridge.elf').read_bytes()
 if m['status']!='built_layout_guard_passed' or m['sdk_revision']!=SDK:
  raise ValueError('successful pinned bridge build required')
 for name,digest in m['artifact_sha256'].items():
  if Path(name).name!=name or (folder/name).is_symlink() or sha(folder/name)!=digest:
   raise ValueError('exported artifact differs')
 policy='spi-config-bridge' if m.get('fpga_configuration_writer') is True else 'spi-bridge'
 layout=inspect_elf(elf,application=policy)
 if layout!=m['layout']:raise ValueError('layout differs')
 for name,digest in m['source_sha256'].items():
  recorded=subprocess.check_output(['git','show',m['source_commit']+':'+name],cwd=ROOT)
  if hashlib.sha256(recorded).hexdigest()!=digest:raise ValueError('committed build source differs')
 sdk=Path(m['sdk_path']).resolve(strict=True)
 if not sdk.is_relative_to('/nix/store') or subprocess.check_output(['nix','hash','path',str(sdk)],text=True).strip()!=m['sdk_nar_hash']:
  raise ValueError('immutable SDK differs')
 if m['sdk_nar_hash']!='sha256-X9mPMzmeJzuhHp7VbTc8BLoF1LE41YOLxK0dAwgYEds=':
  raise ValueError('reviewed SDK NAR required')
 def memory(address,size):
  p=next(p for p in layout['load_segments'] if p['vaddr']<=address<address+size<=p['vaddr']+p['filesz'])
  off=p['offset']+address-p['vaddr'];return elf[off:off+size]
 def word(address):return struct.unpack('<I',memory(address,4))[0]
 symbols=layout['symbols'];early=symbols['runtime_init_early_resets']&~1
 # Reviewed Thumb sequence: load five literals, write reset SET/CLR aliases,
 # then poll RESET_DONE. Refuse a changed instruction sequence or literal map.
 expected=bytes.fromhex('0648dff828c0064b064a0749c0f800c01a608b6832ea0303fbd17047')
 if memory(early,len(expected))!=expected:raise ValueError('unreviewed early-reset instruction sequence')
 set_addr,clear_addr,release,base,asserted=[word(early+offset) for offset in (28,32,36,40,44)]
 if (set_addr,clear_addr,base)!=(0x40022000,0x40023000,0x40020000):
  raise ValueError('unreviewed reset register mapping')
 runner=symbols['runtime_run_initializers']&~1
 if memory(runner,24)!=bytes.fromhex('38b5054c054dac4204d254f8043b9847ac42fad338bd00bf'):
  raise ValueError('unreviewed initializer-loop instruction sequence')
 begin,end=word(runner+24),word(runner+28)
 if not begin<end or (end-begin)%4:raise ValueError('invalid linked initializer table')
 bound=[]
 for name in ('runtime_init_early_resets','runtime_init_post_clock_resets'):
  initializer=symbols['__pre_init_'+name]
  if not begin<=initializer<end or (initializer-begin)%4 or word(initializer)!=symbols[name]:
   raise ValueError('initializer table slot does not bind linked reset function')
  bound.append(name)
 text=(sdk/'src/rp2350/hardware_regs/include/hardware/regs/resets.h').read_text()
 blocks={}
 for name in ('IO_BANK0','PADS_BANK0','PIO0'):
  bit=int(re.search(r'#define RESETS_RESET_'+name+r'_BITS\s+_u\((0x[0-9a-f]+)\)',text)[1],16)
  blocks[name]={'asserted_by_early_reset':bool(asserted&bit),'released_by_early_reset':bool(release&bit)}
 if not all(all(v.values()) for v in blocks.values()):raise ValueError('reviewed peripheral reset behavior changed')
 source_files=['src/rp2_common/pico_runtime_init/runtime_init.c',
  'src/rp2350/hardware_regs/include/hardware/regs/resets.h',
  'src/rp2350/hardware_regs/include/hardware/regs/io_bank0.h',
  'src/rp2350/hardware_regs/include/hardware/regs/pads_bank0.h']
 pads=(sdk/source_files[-1]).read_text();io=(sdk/source_files[-2]).read_text()
 def macro(text,name):return int(re.search(r'#define '+name+r'\s+_u\((0x[0-9a-f]+)\)',text)[1],16)
 defaults={}
 for pin in (1,2,3,4,5,19):
  defaults[str(pin)]={'function_select':macro(io,f'IO_BANK0_GPIO{pin}_CTRL_FUNCSEL_RESET'),
   'pad_isolated':bool(macro(pads,f'PADS_BANK0_GPIO{pin}_ISO_RESET')),
   'pull_down':bool(macro(pads,f'PADS_BANK0_GPIO{pin}_PDE_RESET')),
   'pull_up':bool(macro(pads,f'PADS_BANK0_GPIO{pin}_PUE_RESET'))}
 return {'kind':'offline-linked-startup-audit','result':'reviewed_transition_requires_qualification',
  'source_commit':m['source_commit'],'elf_sha256':hashlib.sha256(elf).hexdigest(),
  'manifest_sha256':sha(folder/'manifest.json'),'sdk_revision':SDK,'sdk_nar_hash':m['sdk_nar_hash'],
  'sdk_source_sha256':{name:sha(sdk/name) for name in source_files},
  'initializer_bindings':bound,'early_assert_mask':hex(asserted),'early_release_mask':hex(release),
  'reset_blocks':blocks,'documented_gpio_reset_defaults':defaults,
  'hardware_opened':False,'loading_admitted':False,
  'conclusion':'Linked startup resets ordinary GPIO, pads and PIO before main. Prior FPGA configuration/pin continuity cannot be assumed. Main watchdog does not protect pre-main startup.',
  'limits':'One recognized reset function and initializer bindings plus pinned SDK reset metadata. Not full boot-ROM/startup control-flow, external pull network, physical pin levels, timing, image continuity or recovery proof.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifact',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path);a=p.parse_args();os.umask(0o077)
 out=fresh(a.output);result=audit(a.artifact)
 (out/'startup-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Build only the committed, distinct observer ARM profile; never load."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from build_forgix_usb_ram import ROOT,SDK,TINY,execute,fresh,sha
from forgix_clock_image import candidate
from forgix_clock_artifact import inspect_elf
import forgix_clock_candidate as fpga
OWN='firmware/forgix-clock-observer/'
BRIDGE='firmware/forgix-spi-bridge/'
PROJECT={n:OWN+n for n in ('CMakeLists.txt','main.c','engine.c','engine.h','observer.c','observer.h','rp_input.c','rp_input.h','period.pio')}
PROJECT.update({n:BRIDGE+n for n in ('uid.c','uid.h','config.c','config.h','protocol.c','protocol.h','tusb_config.h')})
FILES=tuple(dict.fromkeys((*PROJECT.values(),BRIDGE+'usb_descriptors.c',OWN+'PROTOCOL.md',
 'tools/build_forgix_clock_observer.py','tools/forgix_clock_image.py','tools/forgix_clock_artifact.py',
 'tools/build_forgix_usb_ram.py','tools/forgix_usb_ram_artifact.py',*fpga.INPUTS)))

def descriptor(data):
 if data.count(b'Forgix SPI RAM bridge v1')!=1 or data.count(b'.idProduct=0x4012')!=1:raise ValueError('Reviewed descriptor changed')
 return data.replace(b'Forgix SPI RAM bridge v1',b'Forgix Clock RAM observer v1').replace(b'.idProduct=0x4012',b'.idProduct=0x4014')

def stage(project):
 project.mkdir(mode=0o700)
 for n,p in PROJECT.items():(project/n).write_bytes((ROOT/p).read_bytes())
 (project/'usb_descriptors.c').write_bytes(descriptor((ROOT/BRIDGE/'usb_descriptors.c').read_bytes()))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();os.umask(0o077)
 if os.environ.get('PICO_SDK_REVISION')!=SDK or os.environ.get('PICO_TINYUSB_REVISION')!=TINY:raise ValueError('Locked ARM shell required')
 sdk=Path(os.environ['PICO_SDK_PATH']).resolve();compiler=Path(shutil.which('arm-none-eabi-gcc')).resolve();pioasm=Path(os.environ['PIOASM_EXECUTABLE']).resolve()
 if not all(v.is_relative_to('/nix/store') for v in (sdk,compiler,pioasm)):raise ValueError('Immutable compiler/SDK/assembler required')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=10).strip();hashes={n:sha(ROOT/n) for n in FILES}
 for n,h in hashes.items():
  if hashlib.sha256(subprocess.check_output(['git','show',revision+':'+n],cwd=ROOT,timeout=10)).hexdigest()!=h:raise ValueError('Commit observer build inputs')
 image,binding=candidate(a.candidate);build=fresh(a.build);out=fresh(a.output);began=time.monotonic()
 m={'kind':'forgix-clock-observer-offline-build','status':'failed','source_commit':revision,'source_sha256':hashes,
  'configuration':binding,'hardware_opened':False,'loading_admitted':False,'physical_timing_verified':False,
  'sdk_revision':SDK,'tinyusb_revision':TINY,'sdk_path':str(sdk),'compiler_executable':str(compiler),
  'compiler_executable_sha256':sha(compiler),'pioasm_executable':str(pioasm),'pioasm_executable_sha256':sha(pioasm)}
 try:
  m['sdk_nar_hash']=subprocess.check_output(['nix','hash','path',str(sdk)],text=True,timeout=60).strip()
  m['compiler_version']=subprocess.check_output([str(compiler),'--version'],text=True,timeout=10).splitlines()[0]
  project=build/'source';stage(project)
  def array(data):return ','.join(str(n) for n in data)
  generated=project/'fpga_image.c';generated.write_text('#include "config.h"\nconst uint8_t bridge_fpga_image[]={'+array(image)+'};\nconst uint8_t bridge_fpga_sha256[32]={'+array(bytes.fromhex(binding['decoded_sha256']))+'};\n'+f'const uint32_t bridge_fpga_image_bytes={len(image)}u,bridge_fpga_crc32={binding["decoded_crc32"]}u;\n')
  identity=hashlib.sha256(json.dumps({'sources':hashes,'configuration':binding},sort_keys=True).encode()).hexdigest()
  header=build/'build_identity.h';header.write_text('static const unsigned char BUILD_SOURCE_BYTES[32]={'+array(bytes.fromhex(identity))+'};\n')
  staged={p.name:sha(p) for p in project.iterdir()};fixed=sha(header)
  m.update(build_source_sha256=identity,staged_source_sha256=staged,build_identity_header_sha256=fixed)
  log=out/'build.log'
  execute(['cmake','-S',str(project),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DFORGIX_CONFIG_IMAGE='+str(generated)],log,ROOT)
  execute(['cmake','--build',str(build),'--parallel','2'],log,ROOT)
  if any(sha(ROOT/n)!=h for n,h in hashes.items()) or staged!={p.name:sha(p) for p in project.iterdir()} or sha(header)!=fixed or candidate(a.candidate)!=(image,binding):raise ValueError('Observer inputs changed during build')
  elf=build/'forgix_clock_observer.elf';data=elf.read_bytes();layout=inspect_elf(data)
  def loaded(address,length):
   r=next(r for r in layout['load_segments'] if r['vaddr']<=address and address+length<=r['vaddr']+r['filesz']);off=r['offset']+address-r['vaddr'];return data[off:off+length]
  if loaded(layout['symbols']['bridge_fpga_image'],len(image))!=image or loaded(layout['symbols']['bridge_fpga_sha256'],32)!=bytes.fromhex(binding['decoded_sha256']):raise ValueError('Linked observer image differs')
  (out/elf.name).write_bytes(data);maps=list(build.glob('*.map'))
  if len(maps)!=1:raise ValueError('Exactly one linked map required')
  (out/'forgix_clock_observer.map').write_bytes(maps[0].read_bytes());(out/'period.pio.h').write_bytes((build/'period.pio.h').read_bytes())
  for name,cmd in [('symbols.txt',['arm-none-eabi-readelf','-W','-l','-S','-s',str(elf)]),('disassembly.txt',['arm-none-eabi-objdump','-d',str(elf)])]:execute(cmd,out/name,ROOT,timeout=30)
  m.update(status='built_layout_guard_passed',layout=layout,linked_embedded_image_verified=True,inputs_unchanged_after_build=True)
 except BaseException as error:m.update(error_kind=type(error).__name__);raise
 finally:
  m['duration_seconds']=time.monotonic()-began;m['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()};(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 print(json.dumps({k:m[k] for k in ('status','source_commit','hardware_opened','loading_admitted')}))
if __name__=='__main__':main()

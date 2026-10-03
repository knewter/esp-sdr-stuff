#!/usr/bin/env python3
"""Compile the finite RP PIO register bridge; no device, load or programming path."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from build_forgix_usb_ram import ROOT, SDK, TINY, execute, fresh, sha
from forgix_usb_ram_artifact import inspect_elf

PROJECT=['CMakeLists.txt','main.c','protocol.h','protocol.c','wire.pio','usb_descriptors.c','tusb_config.h']
FILES=['firmware/forgix-spi-bridge/'+n for n in PROJECT]+[
 'tools/build_forgix_spi_bridge.py','tools/build_forgix_usb_ram.py',
 'tools/forgix_usb_ram_artifact.py','tools/forgix_spi_guard.py','flake.nix','flake.lock','Taskfile.yml']

def main():
 cli=argparse.ArgumentParser(description=__doc__)
 cli.add_argument('--build',required=True);cli.add_argument('--output',required=True)
 a=cli.parse_args();os.umask(0o077)
 if os.environ.get('PICO_SDK_REVISION')!=SDK or os.environ.get('PICO_TINYUSB_REVISION')!=TINY:
  raise ValueError('locked forgix-spi-bridge shell required')
 sdk=Path(os.environ['PICO_SDK_PATH']).resolve();compiler=Path(shutil.which('arm-none-eabi-gcc')).resolve()
 pioasm=Path(os.environ['PIOASM_EXECUTABLE']).resolve()
 if not all(str(p).startswith('/nix/store/') for p in (sdk,compiler,pioasm)) or not (sdk/'lib/tinyusb/src/tusb.c').is_file():
  raise ValueError('complete immutable SDK/TinyUSB and ARM compiler required')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 hashes={n:sha(ROOT/n) for n in FILES}
 for n,h in hashes.items():
  if hashlib.sha256(subprocess.check_output(['git','show',revision+':'+n],cwd=ROOT)).hexdigest()!=h:
   raise ValueError('commit bridge sources before building')
 build=fresh(Path(a.build));out=fresh(Path(a.output));log=out/'build.log';started=time.monotonic()
 result={'kind':'forgix-spi-bridge-offline-build','status':'failed','source_commit':revision,
  'source_sha256':hashes,'hardware_opened':False,'loading_admitted':False,'physical_timing_verified':False,
  'fpga_configuration_writer':False,'flash_writer':False,'sdk_revision':SDK,'tinyusb_revision':TINY,
  'sdk_path':str(sdk),'compiler_executable':str(compiler),'compiler_executable_sha256':sha(compiler)}
 result.update(pioasm_executable=str(pioasm),pioasm_executable_sha256=sha(pioasm))
 try:
  result['sdk_nar_hash']=subprocess.check_output(['nix','hash','path',str(sdk)],text=True).strip()
  result['compiler_version']=subprocess.check_output([str(compiler),'--version'],text=True).splitlines()[0]
  project=build/'source';project.mkdir(mode=0o700)
  for name in PROJECT:(project/name).write_bytes((ROOT/'firmware/forgix-spi-bridge'/name).read_bytes())
  identity=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
  (build/'build_identity.h').write_text('#define BUILD_SOURCE_SHA256 "'+identity+'"\n')
  execute(['cmake','-S',str(project),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release'],log,ROOT)
  execute(['cmake','--build',str(build),'--parallel','2'],log,ROOT)
  elf=build/'forgix_spi_bridge.elf';payload=elf.read_bytes();(out/elf.name).write_bytes(payload)
  maps=list(build.glob('*.map'))
  if len(maps)!=1:raise ValueError('exactly one linked map required')
  (out/'forgix_spi_bridge.map').write_bytes(maps[0].read_bytes())
  (out/'wire.pio.h').write_bytes((build/'wire.pio.h').read_bytes())
  for name,command in [('symbols.txt',['arm-none-eabi-readelf','-W','-l','-S','-s',str(elf)]),
                       ('disassembly.txt',['arm-none-eabi-objdump','-d',str(elf)])]:
   execute(command,out/name,ROOT,timeout=30)
  if any(sha(ROOT/n)!=h for n,h in hashes.items()):raise ValueError('build inputs changed')
  if any(sha(project/n)!=hashes['firmware/forgix-spi-bridge/'+n] for n in PROJECT):raise ValueError('staged source changed')
  result.update(status='built_layout_guard_passed',inputs_unchanged_after_build=True,
                build_source_sha256=identity,layout=inspect_elf(payload,application='spi-bridge'))
 except BaseException as e:
  result.update(error_kind=type(e).__name__,error=str(e));raise
 finally:
  result['duration_seconds']=time.monotonic()-started
  result['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
  (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ('status','source_commit','hardware_opened','loading_admitted','duration_seconds')}))

if __name__=='__main__':main()

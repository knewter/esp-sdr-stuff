#!/usr/bin/env python3
"""Offline finite-stream ARM build. No device, configuration or load command."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from build_forgix_usb_ram import ROOT,SDK,TINY,execute,fresh,sha
from forgix_usb_ram_artifact import inspect_elf
from forgix_synthetic_image import candidate,wire_primitives

OWN='firmware/forgix-synthetic-stream/'
BRIDGE='firmware/forgix-spi-bridge/'
SOURCE='firmware/forgix-synthetic-source/'
PROJECT={n:OWN+n for n in ('CMakeLists.txt','main.c','platform.c','platform.h','wire_packet.c','engine.c','engine.h')}
PROJECT.update({n:BRIDGE+n for n in ('protocol.c','protocol.h','config.c','config.h','uid.c','uid.h','tusb_config.h','wire.pio')})
PROJECT.update({n:SOURCE+n for n in ('codec.c','codec.h')})
FILES=tuple(PROJECT.values())+(BRIDGE+'main.c',BRIDGE+'usb_descriptors.c',OWN+'PROTOCOL.md',
 'tools/build_forgix_synthetic_stream.py','tools/forgix_synthetic_image.py','tools/forgix_usb_ram_artifact.py',
 'tools/build_forgix_usb_ram.py','tools/forgix_synthetic_candidate.py','tools/forgix_synthetic_gateware.py',
 'tools/forgix_spi_guard.py','tools/forgix_fpga_candidate.py','tools/efinity_bootstrap.py',
 'tools/efinity_compile_smoke.py',SOURCE+'source.v','nix/forgix-toolchain.nix','flake.nix','flake.lock','Taskfile.yml')

def descriptor(data):
    old=b'Forgix SPI RAM bridge v1';new=b'Forgix Synthetic RAM stream v1'
    if data.count(old)!=1 or data.count(b'.idProduct=0x4012')!=1:raise ValueError('Reviewed USB descriptor changed')
    return data.replace(old,new).replace(b'.idProduct=0x4012',b'.idProduct=0x4013')

def stage(project):
    project.mkdir(mode=0o700)
    for name,path in PROJECT.items():(project/name).write_bytes((ROOT/path).read_bytes())
    (project/'wire_primitives.inc').write_bytes(wire_primitives((ROOT/BRIDGE/'main.c').read_bytes()))
    (project/'usb_descriptors.c').write_bytes(descriptor((ROOT/BRIDGE/'usb_descriptors.c').read_bytes()))

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--build',type=Path,required=True);cli.add_argument('--output',type=Path,required=True)
    cli.add_argument('--candidate',type=Path,required=True)
    cli.add_argument('--rp-pause',action='store_true',help='Distinct fixed 100ms RP-drain pause at START+30s')
    a=cli.parse_args();os.umask(0o077)
    if os.environ.get('PICO_SDK_REVISION')!=SDK or os.environ.get('PICO_TINYUSB_REVISION')!=TINY:
        raise ValueError('Enter locked forgix-spi-bridge shell')
    sdk=Path(os.environ['PICO_SDK_PATH']).resolve();compiler=Path(shutil.which('arm-none-eabi-gcc')).resolve()
    pioasm=Path(os.environ['PIOASM_EXECUTABLE']).resolve()
    if not all(str(p).startswith('/nix/store/') for p in (sdk,compiler,pioasm)):raise ValueError('Immutable ARM build dependencies required')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=10).strip()
    hashes={p:sha(ROOT/p) for p in FILES}
    for p,digest in hashes.items():
        if hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT,timeout=10)).hexdigest()!=digest:
            raise ValueError('Commit stream inputs before building')
    image,binding=candidate(a.candidate)
    build=fresh(a.build);out=fresh(a.output);started=time.monotonic();log=out/'build.log'
    result={'kind':'forgix-synthetic-stream-offline-build','status':'failed','source_commit':revision,
        'source_sha256':hashes,'configuration':binding,'rp_pause':a.rp_pause,'hardware_opened':False,
        'loading_admitted':False,'physical_timing_verified':False,'flash_writer':False,'fpga_configuration_writer':True,
        'sdk_revision':SDK,'tinyusb_revision':TINY,'sdk_path':str(sdk),
        'compiler_executable':str(compiler),'compiler_executable_sha256':sha(compiler),
        'pioasm_executable':str(pioasm),'pioasm_executable_sha256':sha(pioasm)}
    try:
        result['sdk_nar_hash']=subprocess.check_output(['nix','hash','path',str(sdk)],text=True,timeout=60).strip()
        result['compiler_version']=subprocess.check_output([str(compiler),'--version'],text=True,timeout=10).splitlines()[0]
        project=build/'source';stage(project)
        def array(data):return ','.join(str(v) for v in data)
        generated=project/'fpga_image.c'
        generated.write_text('#include "config.h"\nconst uint8_t bridge_fpga_image[]={' +array(image)+'};\n'
            +'const uint8_t bridge_fpga_sha256[32]={'+array(bytes.fromhex(binding['decoded_sha256']))+'};\n'
            +f'const uint32_t bridge_fpga_image_bytes={len(image)}u,bridge_fpga_crc32={binding["decoded_crc32"]}u;\n')
        identity=hashlib.sha256(json.dumps({'sources':hashes,'configuration':binding,'rp_pause':a.rp_pause},sort_keys=True).encode()).hexdigest()
        (build/'build_identity.h').write_text('static const unsigned char BUILD_SOURCE_BYTES[32]={'+array(bytes.fromhex(identity))+'};\n'
            +f'#define FORGIX_RP_PAUSE {int(a.rp_pause)}\n')
        staged={p.name:sha(p) for p in project.iterdir()};identity_hash=sha(build/'build_identity.h')
        result.update(build_source_sha256=identity,staged_source_sha256=staged,build_identity_header_sha256=identity_hash)
        execute(['cmake','-S',str(project),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release'],log,ROOT)
        execute(['cmake','--build',str(build),'--parallel','2'],log,ROOT)
        if any(sha(ROOT/p)!=h for p,h in hashes.items()) or staged!={p.name:sha(p) for p in project.iterdir()} or sha(build/'build_identity.h')!=identity_hash:
            raise ValueError('Stream sources changed during build')
        if candidate(a.candidate)!=(image,binding):raise ValueError('Synthetic image inputs changed during build')
        elf=build/'forgix_synthetic_stream.elf';payload=elf.read_bytes();layout=inspect_elf(payload,application='synthetic-stream')
        def loaded(address,length):
            r=next(r for r in layout['load_segments'] if r['vaddr']<=address and address+length<=r['vaddr']+r['filesz'])
            offset=r['offset']+address-r['vaddr'];return payload[offset:offset+length]
        if loaded(layout['symbols']['bridge_fpga_image'],len(image))!=image or loaded(layout['symbols']['bridge_fpga_sha256'],32)!=bytes.fromhex(binding['decoded_sha256']):
            raise ValueError('Linked stream image identity differs')
        (out/elf.name).write_bytes(payload)
        maps=list(build.glob('*.map'))
        if len(maps)!=1:raise ValueError('Exactly one linked stream map required')
        (out/'forgix_synthetic_stream.map').write_bytes(maps[0].read_bytes())
        (out/'wire.pio.h').write_bytes((build/'wire.pio.h').read_bytes())
        for name,cmd in [('symbols.txt',['arm-none-eabi-readelf','-W','-l','-S','-s',str(elf)]),('disassembly.txt',['arm-none-eabi-objdump','-d',str(elf)])]:execute(cmd,out/name,ROOT,timeout=30)
        result.update(status='built_layout_guard_passed',layout=layout,linked_embedded_image_verified=True,inputs_unchanged_after_build=True)
    except BaseException as error:result.update(error_kind=type(error).__name__,error=str(error));raise
    finally:
        result['duration_seconds']=time.monotonic()-started
        result['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
        (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','source_commit','hardware_opened','loading_admitted','duration_seconds')}))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Build/export the isolated original-ESP32 register diagnostic; no hardware."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from build_esp_sdr_uart import SOURCE as BASE, SDK, nix_sdk_provenance

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT/'firmware/register-observation'
KIND = 'esp32-register-observation-v1'
VERSION = 'regobs-v1'
FILES = ('README.md','profile.json','overlay.py','register_observation.h','register_commands.h',
         'base/receiver.c','base/rx_bandwidth.h','base/rx_tuning.h','base/burst_serial.c','base/burst_serial.h','base/COPYING')
REQUIRED = ('CONFIG_IDF_TARGET="esp32"','CONFIG_ESP_SDR_UART_ENABLED=y',
    'CONFIG_ESP_SDR_UART_BAUD=921600','CONFIG_ESP_SDR_UART_TX_PIN=1','CONFIG_ESP_SDR_UART_RX_PIN=3',
    'CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240=y','CONFIG_FREERTOS_UNICORE=y',
    'CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ=240',
    'CONFIG_ESPTOOLPY_FLASHMODE_DIO=y','CONFIG_ESPTOOLPY_FLASHFREQ_40M=y','CONFIG_ESPTOOLPY_FLASHSIZE_2MB=y',
    'CONFIG_ESPTOOLPY_FLASHMODE="dio"','CONFIG_ESPTOOLPY_FLASHFREQ="40m"','CONFIG_ESPTOOLPY_FLASHSIZE="2MB"',
    'CONFIG_PARTITION_TABLE_SINGLE_APP=y','CONFIG_PARTITION_TABLE_FILENAME="partitions_singleapp.csv"','CONFIG_PARTITION_TABLE_MD5=y',
    'CONFIG_PARTITION_TABLE_OFFSET=0x8000','# CONFIG_SECURE_BOOT is not set',
    '# CONFIG_SECURE_FLASH_ENC_ENABLED is not set','# CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT is not set')
DISABLED_HIDDEN = ('CONFIG_BT_ENABLED','CONFIG_SECURE_BOOT_V1_ENABLED','CONFIG_SECURE_BOOT_V2_ENABLED',
    'CONFIG_FLASH_ENCRYPTION_ENABLED','CONFIG_PARTITION_TABLE_CUSTOM','CONFIG_PARTITION_TABLE_TWO_OTA',
    'CONFIG_ESPTOOLPY_FLASHMODE_QIO','CONFIG_ESPTOOLPY_FLASHMODE_QOUT','CONFIG_ESPTOOLPY_FLASHMODE_DOUT',
    'CONFIG_ESPTOOLPY_FLASHFREQ_80M','CONFIG_ESPTOOLPY_FLASHSIZE_4MB')
PARTS = (('bootloader.bin',0x1000,0x8000),('partition-table.bin',0x8000,0x9000),
         ('esp_sdr.bin',0x10000,0x110000))
BUFFER_SYMBOLS = {'regobs_records':(1,81*32), 'regobs_json':(2048,2048),'regobs_wire':(2048,2048)}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def load_overlay():
    spec=importlib.util.spec_from_file_location('register_observation_overlay',FIRMWARE/'overlay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def source_files():
    actual={p.relative_to(FIRMWARE).as_posix() for p in FIRMWARE.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}
    if actual != set(FILES): raise ValueError('Unexpected diagnostic firmware source files')
    files={name:sha(FIRMWARE/name) for name in FILES}
    profile=json.loads((FIRMWARE/'profile.json').read_text())
    for name,value in profile['base_files'].items():
        if files['base/'+name] != value: raise ValueError('Pinned base source hash mismatch')
    if profile['source_base'] != BASE or profile['sdk_revision'] != SDK or profile['kind'] != KIND:
        raise ValueError('Diagnostic profile pins mismatch')
    return files,profile


def tree_hash(files):
    return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_config(text):
    guarded={re.search(r'CONFIG_[A-Z0-9_]+',line).group():line for line in REQUIRED}
    seen={key:[] for key in (*guarded,*DISABLED_HIDDEN)}
    for line in text.splitlines():
        match=re.fullmatch(r'(CONFIG_[A-Z0-9_]+)=.*|# (CONFIG_[A-Z0-9_]+) is not set',line)
        if match:
            key=match.group(1) or match.group(2)
            if key in seen:seen[key].append(line)
    if (any(seen[key] != [line] for key,line in guarded.items()) or
            any(seen[key] not in ([],[f'# {key} is not set']) for key in DISABLED_HIDDEN)):
        raise ValueError('Generated configuration differs from isolated diagnostic profile')


def validate_symbols(nm_text):
    found={}
    for line in nm_text.splitlines():
        fields=line.split()
        if len(fields)==4 and fields[3] in BUFFER_SYMBOLS:
            if fields[3] in found:raise ValueError('Duplicate diagnostic buffer symbol')
            address,size=int(fields[0],16),int(fields[1],16)
            lower,upper=BUFFER_SYMBOLS[fields[3]]
            if fields[2] not in ('b','B','d','D') or not lower<=size<=upper:
                raise ValueError('Diagnostic buffer size/type mismatch')
            if fields[3]=='regobs_records' and (size % 81 or not 24<=size//81<=32):
                raise ValueError('Linked record array does not contain 81 declared-size records')
            if not 0x3ffb0000<=address<address+size<=0x3ffe8000:
                raise ValueError('Diagnostic buffer is outside reviewed DRAM or overlaps sample slab')
            found[fields[3]]=dict(address=address,size=size,end=address+size)
    if set(found)!=set(BUFFER_SYMBOLS):raise ValueError('Missing linked diagnostic buffers')
    ranges=sorted(found.values(),key=lambda x:x['address'])
    if any(a['end']>b['address'] for a,b in zip(ranges,ranges[1:])):
        raise ValueError('Linked diagnostic buffers overlap')
    return found


def prepare_project(source,project):
    actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if actual!=BASE:raise ValueError('Receiver source revision mismatch')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True):
        raise ValueError('Receiver tracked files must be clean')
    status=subprocess.check_output(['git','-C',str(source),'submodule','status','--recursive'],text=True)
    if any(line.startswith(('-', '+', 'U')) for line in status.splitlines()):
        raise ValueError('Receiver submodules must be initialized at pinned revisions')
    overlay=load_overlay()
    generated=overlay.receiver_text((source/'main/targets/esp32/receiver.c').read_bytes())
    generated_transport=overlay.transport_text((source/'main/common/burst_serial.c').read_bytes())
    for name in ('rx_bandwidth.h','rx_tuning.h','burst_serial.h'):
        if (source/'main/common'/name).read_bytes()!=(FIRMWARE/'base'/name).read_bytes():
            raise ValueError('Pinned common header mismatch')
    # Copy only Git-pinned files (including initialized submodules). Untracked
    # local CMake/components/build output must never affect the artifact.
    tracked=subprocess.check_output(['git','-C',str(source),'ls-files','--recurse-submodules','-z']).decode().split('\0')
    project.mkdir(mode=0o700)
    for name in filter(None,tracked):
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe pinned source path')
        src=source/relative;target=project/relative
        if src.is_symlink() or not src.is_file():raise ValueError('Pinned source must consist of regular files')
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(src,target)
    backend=project/'main/targets/esp32'
    (backend/'receiver.c').write_text(generated)
    (project/'main/common/burst_serial.c').write_text(generated_transport)
    for name in ('register_observation.h','register_commands.h'):shutil.copyfile(FIRMWARE/name,backend/name)
    defaults=project/'sdkconfig.defaults.esp32'
    value=defaults.read_text()
    if value.count('CONFIG_ESP_SDR_UART_BAUD=2000000')!=1:raise ValueError('UART defaults anchor mismatch')
    value=value.replace('CONFIG_ESP_SDR_UART_BAUD=2000000','CONFIG_ESP_SDR_UART_BAUD=921600')
    value+='\n# CONFIG_SECURE_BOOT is not set\n# CONFIG_SECURE_FLASH_ENC_ENABLED is not set\n# CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT is not set\n'
    defaults.write_text(value)
    return dict(receiver_sha256=sha(backend/'receiver.c'),transport_sha256=sha(project/'main/common/burst_serial.c'),defaults_sha256=sha(defaults),
                receiver_submodules=status.strip().splitlines())


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=2)
    a=p.parse_args(argv)
    sdk=Path(os.environ.get('IDF_PATH','')).resolve()
    provenance=nix_sdk_provenance(sdk)
    if not provenance:p.error('Use the pinned Nix firmware shell')
    if not 1<=a.jobs<=4:p.error('jobs must be in 1..4')
    build,output=a.build.resolve(),a.output.resolve()
    if build==output or build.is_relative_to(output) or output.is_relative_to(build):p.error('Build/output paths must be disjoint')
    for path in (build,output):
        if path.exists() or path==ROOT/'.scratch' or not path.is_relative_to(ROOT/'.scratch'):
            p.error('Build/output paths must be fresh private .scratch directories')
        subprocess.run(['git','-C',str(ROOT),'check-ignore','--quiet',str(path)],check=True)
    files,profile=source_files()
    revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    for name,hash_value in files.items():
        tracked=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':firmware/register-observation/'+name])
        if hashlib.sha256(tracked).hexdigest()!=hash_value:raise ValueError('Firmware bytes differ from recorded commit')
    builder_bytes=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':tools/build_esp_register_observation.py'])
    if hashlib.sha256(builder_bytes).hexdigest()!=sha(Path(__file__)):raise ValueError('Builder must be committed before build')
    old_umask=os.umask(0o077)
    try:
        build.mkdir(parents=True,mode=0o700);output.mkdir(parents=True,mode=0o700)
        project=build/'source';prepared=prepare_project(a.source.resolve(),project)
        binary_build=build/'idf';config_path=binary_build/'sdkconfig'
        command=[str(sdk/'bin/idf.py'),'-C',str(project),'-B',str(binary_build),'-DIDF_TARGET=esp32',
                 '-DSDKCONFIG='+str(config_path),'-DPROJECT_VER='+VERSION,
                 '-DRING_PROBE=OFF','-DSAMPLE_RATE_PROBE=OFF','-DFILTER_REGISTER_PROBE=OFF',
                 '-DS3_RF_PROBE=OFF','-DC5_TUNE_PROBE=OFF','-DS2_RF_PROBE=OFF','reconfigure']
        env=dict(os.environ,IDF_COMPONENT_MANAGER='0')
        with (output/'build.log').open('wb') as log:
            subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            validate_config(config_path.read_text())
            subprocess.run(['cmake','--build',str(binary_build),'--parallel',str(a.jobs)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        validate_config(config_path.read_text())
        shutil.copyfile(config_path,output/'sdkconfig')
        elf=binary_build/'esp_sdr.elf';map_path=binary_build/'esp_sdr.map'
        symbols=subprocess.check_output(['xtensa-esp-elf-nm','-S',str(elf)],text=True)
        buffers=validate_symbols(symbols)
        shutil.copyfile(elf,output/'esp_sdr.elf')
        shutil.copyfile(map_path,output/'linker.map')
        shutil.copyfile(binary_build/'flasher_args.json',output/'flasher_args.json')
        (output/'symbols.txt').write_text(symbols)
        (output/'buffer-symbols.txt').write_text('\n'.join(line for line in symbols.splitlines() if line.split() and line.split()[-1] in BUFFER_SYMBOLS)+'\n')
        folder=output/'esp32';folder.mkdir(mode=0o700)
        locations=(binary_build/'bootloader/bootloader.bin',binary_build/'partition_table/partition-table.bin',binary_build/'esp_sdr.bin')
        parts=[]
        for src,(name,offset,end) in zip(locations,PARTS):
            target=folder/name;shutil.copyfile(src,target)
            if not 0<target.stat().st_size<=end-offset:raise ValueError('Diagnostic image exceeds reviewed partition')
            parts.append(dict(name=name,offset=offset,size=target.stat().st_size,sha256=sha(target)))
        info=dict(kind=KIND,target='esp32',version=VERSION,info=profile['info'],source_commit=revision,
                  source_base_revision=BASE,source_files=files,source_tree_sha256=tree_hash(files),
                  builder_sha256=sha(Path(__file__)),idf_commit=SDK,nix_sdk_provenance=provenance,
                  sdkconfig_sha256=sha(output/'sdkconfig'),required_sdkconfig_lines=list(REQUIRED),
                  disabled_hidden_sdkconfig_keys=list(DISABLED_HIDDEN),
                  profile=profile,prepared_source=prepared,linked_buffers=buffers,
                  linker_map_sha256=sha(output/'linker.map'),elf_sha256=sha(elf),
                  symbols_sha256=sha(output/'symbols.txt'),flasher_args_sha256=sha(output/'flasher_args.json'),
                  compiler_version=subprocess.check_output(['xtensa-esp-elf-gcc','--version'],text=True).splitlines()[0])
        (output/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
        manifest=dict(schema=1,kind=KIND,target='esp32',version=VERSION,info=profile['info'],parts=parts,
                      flash_settings=dict(flash_mode='dio',flash_freq='40m',flash_size='2MB'),
                      source_tree_sha256=info['source_tree_sha256'],build_info_sha256=sha(output/'build-info.json'))
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        for name in ('bootloader.bin','esp_sdr.bin'):
            image=subprocess.check_output(['esptool','--chip','esp32','image-info',str(folder/name)],text=True)
            (output/(name+'.image-info.log')).write_text(image)
        print('Isolated register observation artifact exported; no hardware accessed.')
    finally:os.umask(old_umask)


if __name__=='__main__':main()

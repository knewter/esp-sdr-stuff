#!/usr/bin/env python3
"""Build a separate pinned passive BLE reference artifact; never touches hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from build_esp_sdr_uart import SDK, SDK_NIX_SOURCE_HASH, nix_sdk_provenance

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'firmware/native-ble-reference'
KIND = 'native-ble-source-reference-v1'
VERSION = 'native-ble-ref-v1'
FILES = ('CMakeLists.txt','main/CMakeLists.txt','main/main.c','partitions.csv','sdkconfig.defaults')
REQUIRED = ('CONFIG_IDF_TARGET="esp32"','CONFIG_BT_ENABLED=y','CONFIG_BTDM_CTRL_MODE_BLE_ONLY=y',
    'CONFIG_BT_NIMBLE_ENABLED=y','CONFIG_BT_NIMBLE_ROLE_OBSERVER=y',
    '# CONFIG_BT_NIMBLE_ROLE_CENTRAL is not set','# CONFIG_BT_NIMBLE_ROLE_PERIPHERAL is not set',
    '# CONFIG_BT_NIMBLE_ROLE_BROADCASTER is not set','# CONFIG_BT_NIMBLE_NVS_PERSIST is not set',
    'CONFIG_BT_NIMBLE_LOG_LEVEL_NONE=y','CONFIG_LOG_DEFAULT_LEVEL_NONE=y',
    'CONFIG_BOOTLOADER_LOG_LEVEL_NONE=y','CONFIG_ESP_CONSOLE_UART_BAUDRATE=115200',
    'CONFIG_ESPTOOLPY_FLASHMODE_DIO=y','CONFIG_ESPTOOLPY_FLASHFREQ_40M=y','CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y',
    'CONFIG_PARTITION_TABLE_CUSTOM=y','CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"',
    'CONFIG_PARTITION_TABLE_OFFSET=0x8000','# CONFIG_SECURE_BOOT is not set',
    '# CONFIG_SECURE_FLASH_ENC_ENABLED is not set','# CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT is not set')
PARTS = (('bootloader.bin',0x1000,0x8000),('partition-table.bin',0x8000,0x9000),
         ('native_ble_reference.bin',0x10000,0x110000))


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files():
    actual={p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
    if actual!=set(FILES): raise ValueError('Unexpected native firmware source file set')
    return {name:sha(SOURCE/name) for name in FILES}


def source_tree_hash(files):
    return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_config(text):
    if any(line not in text.splitlines() for line in REQUIRED):
        raise ValueError('Generated configuration is not the observer-only native profile')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args(argv)
    sdk=Path(os.environ.get('IDF_PATH',''))
    provenance=nix_sdk_provenance(sdk)
    if not provenance: p.error('Use the pinned Nix firmware shell')
    if a.jobs<1: p.error('jobs must be positive')
    paths=[a.build.resolve(),a.output.resolve()]
    for path in paths:
        if path.exists() or not path.is_relative_to(ROOT/'.scratch') or path==ROOT/'.scratch':
            p.error('Build and artifact paths must be fresh ignored .scratch directories')
        if subprocess.run(['git','-C',str(ROOT),'check-ignore','--quiet',str(path)],capture_output=True).returncode:
            p.error('Build and artifact paths must be ignored')
    subprocess.run(['git','-C',str(ROOT),'diff','--exit-code','HEAD','--','firmware/native-ble-reference',
                    'tools/build_native_ble_reference.py'],check=True,capture_output=True)
    for name in FILES:
        subprocess.run(['git','-C',str(ROOT),'ls-files','--error-unmatch',str(SOURCE/name)],check=True,capture_output=True)
    files=source_files();revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    old_umask=os.umask(0o077)
    try:
        a.build.mkdir(parents=True,mode=0o700);a.output.mkdir(parents=True,mode=0o700)
        command=[str(sdk/'bin/idf.py'),'-C',str(SOURCE),'-B',str(a.build.resolve()),
                 '-DIDF_TARGET=esp32','-DSDKCONFIG='+str((a.build/'sdkconfig').resolve()),
                 '-DSDKCONFIG_DEFAULTS='+str(SOURCE/'sdkconfig.defaults'),'-DPROJECT_VER='+VERSION,'build']
        env=dict(os.environ,IDF_COMPONENT_MANAGER='0',IDF_PY_BUILD_JOBS=str(a.jobs))
        with (a.output/'build.log').open('wb') as log:
            subprocess.run(command[:-1]+['reconfigure'],check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
            validate_config((a.build/'sdkconfig').read_text())
            subprocess.run(command,check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
        config=(a.build/'sdkconfig').read_text();validate_config(config)
        shutil.copyfile(a.build/'sdkconfig',a.output/'sdkconfig')
        folder=a.output/'esp32';folder.mkdir(mode=0o700)
        locations=[a.build/'bootloader/bootloader.bin',a.build/'partition_table/partition-table.bin',
                   a.build/'native_ble_reference.bin']
        parts=[]
        for src,(name,offset,end) in zip(locations,PARTS):
            target=folder/name;shutil.copyfile(src,target)
            if not 0<target.stat().st_size<=end-offset:raise ValueError('Native artifact exceeds reviewed partition layout')
            parts.append(dict(name=name,offset=offset,size=target.stat().st_size,sha256=sha(target)))
        info=dict(kind=KIND,target='esp32',version=VERSION,source_commit=revision,source_files=files,
                  source_tree_sha256=source_tree_hash(files),idf_commit=SDK,nix_sdk_provenance=provenance,
                  sdkconfig_sha256=sha(a.output/'sdkconfig'),required_sdkconfig_lines=list(REQUIRED),
                  compiler_version=subprocess.check_output(['xtensa-esp-elf-gcc','--version'],text=True).splitlines()[0],
                  profile=dict(scan_ms=90000,passive=True,filter_duplicates=False,interval_units=160,window_units=160,uart_baud=115200))
        (a.output/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
        manifest=dict(schema=1,kind=KIND,target='esp32',version=VERSION,parts=parts,
                      source_tree_sha256=info['source_tree_sha256'],build_info_sha256=sha(a.output/'build-info.json'))
        (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        for name in ('bootloader.bin','native_ble_reference.bin'):
            image=subprocess.check_output(['esptool','--chip','esp32','image-info',str(folder/name)],text=True)
            (a.output/(name+'.image-info.log')).write_text(image)
        print('Native passive reference artifact built; no hardware accessed.')
    finally:os.umask(old_umask)


if __name__=='__main__':main()

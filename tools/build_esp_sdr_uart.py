#!/usr/bin/env python3
"""Build the pinned original ESP32 receiver with a board-compatible UART default.

Activate the pinned SDK first. This tool builds/exports artifacts only; no flash.
Source and SDK checkouts plus output/build directories stay in ignored scratch.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE='550fadea4d00a9e26ce921c5832167becb3dc20c'
SDK='25fe69f946311abdaf9ad56591f25fedbc20ac98'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--baud',type=int,default=1000000,choices=[115200,460800,921600,1000000,2000000])
    parser.add_argument('--jobs',type=int,default=4)
    args=parser.parse_args()
    source=args.source.resolve();sdk=args.sdk.resolve();build=args.build.resolve();output=args.output.resolve()
    for path,revision in [(source,SOURCE),(sdk,SDK)]:
        actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
        if actual!=revision:parser.error(f'Pinned checkout mismatch: expected {revision}, found {actual}')
        if subprocess.run(['git','-C',str(path),'diff','--quiet','HEAD'],check=False).returncode:
            parser.error('Tracked source or SDK modifications are not allowed in this configuration-only recipe')
    if not os.environ.get('IDF_PATH') or Path(os.environ['IDF_PATH']).resolve()!=sdk:
        parser.error('Activate this pinned SDK export.sh before building')
    if build.exists() or output.exists() or args.evidence.exists():
        parser.error('Build/output/evidence destinations must be fresh for reproducibility')
    if args.jobs<1:parser.error('jobs must be positive')
    build.mkdir(parents=True)
    defaults=(source/'sdkconfig.defaults.esp32').read_text()
    assert defaults.count('CONFIG_ESP_SDR_UART_BAUD=2000000')==1
    defaults=defaults.replace('CONFIG_ESP_SDR_UART_BAUD=2000000',f'CONFIG_ESP_SDR_UART_BAUD={args.baud}')
    (build/'defaults.esp32').write_text(defaults)
    suffix = f'{args.baud//1000000}m' if args.baud % 1000000 == 0 else str(args.baud)
    version=f'550fade-uart{suffix}'
    env=dict(os.environ, IDF_PY_BUILD_JOBS=str(args.jobs), IDF_COMPONENT_MANAGER='0')
    command=[sys.executable,str(sdk/'tools/idf.py'),'-C',str(source),'-B',str(build),
             '-DIDF_TARGET=esp32','-DSDKCONFIG='+str(build/'sdkconfig'),
             '-DSDKCONFIG_DEFAULTS='+str(build/'defaults.esp32'),'-DPROJECT_VER='+version,
             '-DRING_PROBE=OFF','-DSAMPLE_RATE_PROBE=OFF','-DFILTER_REGISTER_PROBE=OFF',
             '-DS3_RF_PROBE=OFF','-DC5_TUNE_PROBE=OFF','-DS2_RF_PROBE=OFF','build']
    subprocess.run(command,env=env,check=True)
    config=(build/'sdkconfig').read_text()
    required=['CONFIG_IDF_TARGET="esp32"',f'CONFIG_ESP_SDR_UART_BAUD={args.baud}',
              'CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ_240=y','CONFIG_FREERTOS_UNICORE=y']
    if any(line not in config.splitlines() for line in required):
        raise RuntimeError('Built target configuration does not match recipe')
    sys.path.insert(0,str(source/'tools'))
    from export_web_firmware import export
    export(build,output,'esp32','ESP32 custom UART default',version,True)
    info={'kind':'local pinned source build with UART configuration variant',
          'source_commit':SOURCE,'idf_commit':SDK,'target':'esp32','app_version':version,
          'configuration_difference_from_upstream_defaults':{'CONFIG_ESP_SDR_UART_BAUD':args.baud},
          'required_sdkconfig_lines':required,'generated_defaults_sha256':hashlib.sha256(defaults.encode()).hexdigest(),
          'source_code_patch':None,
          'compiler_version':subprocess.check_output(['xtensa-esp-elf-gcc','--version'],text=True).splitlines()[0],
          'source_submodules':subprocess.check_output(['git','-C',str(source),'submodule','status','--recursive'],text=True).strip().splitlines()}
    (output/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
    args.evidence.mkdir(parents=True)
    (args.evidence/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
    (args.evidence/'manifest.json').write_bytes((output/'manifest.json').read_bytes())
    image=subprocess.check_output([sys.executable,'-m','esptool','--chip','esp32','image-info',str(output/'esp32'/'2-esp_sdr.bin')],text=True)
    (args.evidence/'image-info.log').write_text(image)
    print(f'Artifact exported; application version {version}; target esp32; baud {args.baud}')


if __name__=='__main__':main()

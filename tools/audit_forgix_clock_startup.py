#!/usr/bin/env python3
"""Distinct saved observer layout/startup audit; no whole-boot admission."""
import argparse,hashlib,json,os,re,struct,subprocess,zlib
from pathlib import Path
from build_forgix_usb_ram import ROOT,SDK,TINY,fresh,sha
from build_forgix_clock_observer import FILES
from forgix_clock_artifact import inspect_elf
from forgix_clock_candidate import regular
from audit_forgix_synthetic_startup import linked_resets,NAR
EXPORTS={'build.log','period.pio.h','disassembly.txt','symbols.txt','forgix_clock_observer.map','forgix_clock_observer.elf'}

def require(ok,message):
 if not ok:raise ValueError(message)

def audit(folder):
 folder=Path(folder).absolute();require(folder.is_relative_to(ROOT/'.scratch') and folder!=ROOT/'.scratch' and '..' not in folder.parts,'Private observer artifact required')
 manifest=regular(folder/'manifest.json',512*1024);m=json.loads(manifest.read_bytes())
 require(m.get('kind')=='forgix-clock-observer-offline-build' and m.get('status')=='built_layout_guard_passed' and m.get('sdk_revision')==SDK and m.get('tinyusb_revision')==TINY and m.get('sdk_nar_hash')==NAR and m.get('linked_embedded_image_verified') is True and m.get('inputs_unchanged_after_build') is True and m.get('hardware_opened') is False and m.get('loading_admitted') is False,'Pinned complete observer build required')
 require(type(m.get('source_sha256')) is dict and set(m['source_sha256'])==set(FILES) and set(m.get('artifact_sha256',{}))==EXPORTS and re.fullmatch('[0-9a-f]{40}',m.get('source_commit','')),'Exact source/export inventory required')
 for n,h in m['source_sha256'].items():
  data=subprocess.check_output(['git','show',m['source_commit']+':'+n],cwd=ROOT,timeout=10)
  require(hashlib.sha256(data).hexdigest()==h,'Committed observer source differs')
 for n,h in m['artifact_sha256'].items():require(sha(regular(folder/n,16*1024**2))==h,'Observer export differs')
 data=(folder/'forgix_clock_observer.elf').read_bytes();layout=inspect_elf(data);require(layout==m['layout'],'Observer layout differs')
 def loaded(name,length):
  address=layout['symbols'][name];r=next(r for r in layout['load_segments'] if r['vaddr']<=address and address+length<=r['vaddr']+r['filesz']);off=r['offset']+address-r['vaddr'];return data[off:off+length]
 image=m['configuration'];count=struct.unpack('<I',loaded('bridge_fpga_image_bytes',4))[0];payload=loaded('bridge_fpga_image',count)
 require(count==image['decoded_bytes'] and hashlib.sha256(payload).hexdigest()==image['decoded_sha256'] and loaded('bridge_fpga_sha256',32)==bytes.fromhex(image['decoded_sha256']) and zlib.crc32(payload)==image['decoded_crc32']==struct.unpack('<I',loaded('bridge_fpga_crc32',4))[0],'Linked observer image identity differs')
 identity=hashlib.sha256(json.dumps({'sources':m['source_sha256'],'configuration':image},sort_keys=True).encode()).hexdigest()
 require(identity==m['build_source_sha256'] and any(bytes.fromhex(identity) in data[r['offset']:r['offset']+r['filesz']] for r in layout['load_segments']),'Linked build identity differs')
 sdk=Path(m['sdk_path']);require(sdk.is_absolute() and sdk.is_relative_to('/nix/store') and '..' not in sdk.parts and not any(p.is_symlink() for p in (sdk,*sdk.parents)),'Immutable SDK required')
 require(subprocess.check_output(['nix','hash','path',str(sdk)],text=True,timeout=60).strip()==NAR,'SDK NAR differs')
 return {'kind':'offline-clock-observer-linked-startup-audit','result':'recognized_reset_transition_requires_qualification',
  'source_commit':m['source_commit'],'elf_sha256':sha(folder/'forgix_clock_observer.elf'),'manifest_sha256':sha(manifest),
  'sdk_revision':SDK,'tinyusb_revision':TINY,'sdk_nar_hash':NAR,**linked_resets(data,layout,sdk),
  'hardware_opened':False,'loading_admitted':False,'whole_boot_path_qualified':False,
  'limits':'Recognized linked reset/table and pinned SDK metadata only; no whole ROM/initializer CFG, external levels, pad timing, clock calibration, image continuity or recovery proof.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();os.umask(0o077)
 try:
  report=audit(a.artifact);out=fresh(a.output);(out/'startup-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':report['result'],'hardware_opened':False,'loading_admitted':False}));return 0
 except Exception as error:print(json.dumps({'result':'failed','error_kind':type(error).__name__,'hardware_opened':False,'loading_admitted':False}));return 2
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Build only: committed, pinned finite RP2350 RAM USB diagnostic; never load."""
import argparse,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
from forgix_usb_ram_artifact import inspect_elf
ROOT=Path(__file__).resolve().parents[1]
SDK='a1438dff1d38bd9c65dbd693f0e5db4b9ae91779'
TINY='86ad6e56c1700e85f1c5678607a762cfe3aa2f47'
FILES=['firmware/forgix-usb-ram/'+f for f in ['CMakeLists.txt','main.c','usb_descriptors.c','tusb_config.h']]+['tools/build_forgix_usb_ram.py','tools/forgix_usb_ram_artifact.py','flake.nix','flake.lock','Taskfile.yml']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fresh(value):
 p=ROOT/value
 if not p.is_absolute():p=ROOT/p
 for ancestor in (p,*p.parents):
  if ancestor.is_symlink():raise ValueError('symlinked output path')
 p=p.resolve();p.relative_to(ROOT/'.scratch')
 if p.exists():raise ValueError('fresh build/output required')
 p.mkdir(parents=True,mode=0o700);return p

def execute(command,log,cwd,timeout=300):
 p=None
 with log.open('ab') as f:
  try:
   pending=[];saved={}
   # Assign ownership before delivering cancellation; no blocked signal mask
   # is inherited by the compiler process.
   try:
    for sig in (signal.SIGINT,signal.SIGTERM):
     saved[sig]=signal.signal(sig,lambda sig,frame:pending.append((sig,frame)))
    p=subprocess.Popen(command,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   finally:
    for sig,handler in saved.items():signal.signal(sig,handler)
   for sig,frame in pending:
    if callable(saved[sig]):saved[sig](sig,frame)
    elif saved[sig]!=signal.SIG_IGN:raise KeyboardInterrupt()
   code=p.wait(timeout=timeout)
   if code:raise RuntimeError('build command failed; private log retained')
  finally:
   if p is not None:
    if p.poll() is None:
     os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
    # An exited leader is insufficient if a descendant survived.
    try:os.killpg(p.pid,0)
    except ProcessLookupError:pass
    else:
     os.killpg(p.pid,signal.SIGKILL)
     deadline=time.monotonic()+5
     while time.monotonic()<deadline:
      try:os.killpg(p.pid,0)
      except ProcessLookupError:break
      time.sleep(.05)
     else:raise RuntimeError('build process group closure unverified')

def main():
 cli=argparse.ArgumentParser(description=__doc__)
 cli.add_argument('--build',default='.scratch/forgix-usb-ram-build-001');cli.add_argument('--output',default='.scratch/forgix-usb-ram-artifact-001');cli.add_argument('--jobs',type=int,default=2)
 a=cli.parse_args();os.umask(0o077)
 if a.jobs not in (1,2):raise ValueError('jobs must be 1 or2')
 if os.environ.get('PICO_SDK_REVISION')!=SDK or os.environ.get('PICO_TINYUSB_REVISION')!=TINY:raise ValueError('locked forgix-usb-ram shell required')
 sdk=Path(os.environ['PICO_SDK_PATH']).resolve()
 if not str(sdk).startswith('/nix/store/') or not (sdk/'lib/tinyusb/src/tusb.c').is_file():raise ValueError('complete immutable SDK/TinyUSB required')
 subprocess.run(['git','diff','--quiet','HEAD','--',*FILES],cwd=ROOT,check=True)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();hashes={name:sha(ROOT/name) for name in FILES}
 for name,digest in hashes.items():
  if hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)).hexdigest()!=digest:raise ValueError('source bytes differ from commit')
 build=fresh(Path(a.build));out=fresh(Path(a.output));log=out/'build.log';status={'kind':'Forgix synthetic USB RAM build only','status':'failed','hardware_opened':False,'source_commit':commit,'source_sha256':hashes,'sdk_revision':SDK,'tinyusb_revision':TINY,'sdk_path':str(sdk)}
 try:
  compiler=Path(shutil.which('arm-none-eabi-gcc')).resolve()
  if not str(compiler).startswith('/nix/store/'):raise ValueError('Nix ARM compiler required')
  status.update(compiler_executable=str(compiler),compiler_executable_sha256=sha(compiler),compiler_version=subprocess.check_output([str(compiler),'--version'],text=True).splitlines()[0],sdk_nar_hash=subprocess.check_output(['nix','hash','path',str(sdk)],text=True).strip())
  project=build/'source';project.mkdir(mode=0o700)
  for name in FILES[:4]:(project/Path(name).name).write_bytes((ROOT/name).read_bytes())
  source_hash=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
  (build/'build_identity.h').write_text('#define BUILD_SOURCE_SHA256 "'+source_hash+'"\n')
  execute(['cmake','-S',str(project),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release'],log,ROOT)
  execute(['cmake','--build',str(build),'--parallel',str(a.jobs)],log,ROOT)
  elf=build/'forgix_usb_ram.elf';data=elf.read_bytes()
  (out/elf.name).write_bytes(data)
  maps=list(build.glob('*.map'))
  if len(maps)!=1:raise ValueError('exact linked map required')
  (out/'forgix_usb_ram.map').write_bytes(maps[0].read_bytes())
  for name,args in [('symbols.txt',['arm-none-eabi-readelf','-W','-l','-S','-s',str(elf)]),('disassembly.txt',['arm-none-eabi-objdump','-d',str(elf)])]:
   with (out/name).open('wb') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
  if any(sha(ROOT/name)!=digest for name,digest in hashes.items()):raise ValueError('inputs changed during build')
  if any(sha(project/Path(name).name)!=hashes[name] for name in FILES[:4]):raise ValueError('staged project changed during build')
  status['inputs_unchanged_after_build']=True
  report=inspect_elf(data)
  status.update(status='built_layout_guard_passed',build_source_sha256=source_hash,layout=report)
 except BaseException as e:
  status['error_kind']=type(e).__name__;status['error']=str(e);raise
 finally:
  status['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
  (out/'manifest.json').write_text(json.dumps(status,indent=2)+'\n')
 print(json.dumps({k:status[k] for k in ('status','source_commit','hardware_opened')}))
if __name__=='__main__':main()

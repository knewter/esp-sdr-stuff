#!/usr/bin/env python3
"""Distinct offline observer compiler; no device/load/program interface."""
import argparse,ast,hashlib,json,os,re,shutil,stat,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
import efinity_bootstrap as b
import efinity_compile_smoke as smoke
import forgix_fpga_candidate as old
NAME='forgix_clock_candidate'
INPUTS=('tools/forgix_clock_candidate.py','tools/forgix_clock_observer.py',
 'tools/forgix_fpga_candidate.py','tools/efinity_bootstrap.py','tools/efinity_compile_smoke.py',
 'nix/forgix-toolchain.nix','flake.nix','flake.lock','Taskfile.yml')
GENERATED=(NAME+'.v',NAME+'.sdc','iface.py',NAME+'.xml',NAME+'.peri.xml',NAME+'_merged.sdc')
GPIO={'clk32':('input','B4'),'spibone_cs_n':('input','G3'),
 'spibone_clk':('input','F3'),'spibone0_mosi0':('inout','F2')}
PROFILE={'kind':'forgix-offline-clock-observer-candidate','schema':1,'device':'T8F49',
 'timing_model':'I2','requested_clock_hz':32000000,'configuration_mode':'passive',
 'configuration_width':1,'clock_route':'sys_clk directly from B4; no PLL',
 'divisor':1024,'burst_periods':1024,'arm_cycles':32,'physical_confirmation':False,
 'programming_admitted':False,'physical_timing_verified':False,'calibrated_absolute_frequency':False}

def regular(path,limit=1024**2,*,empty=False,fresh=None):
 path=Path(path)
 b.require(not any(p.is_symlink() for p in (path,*path.parents)),'Linked observer input')
 s=path.stat();b.require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and (0 if empty else 1)<=s.st_size<=limit,'Observer file bounds')
 if fresh is not None:b.require(s.st_mtime_ns>=fresh,'Stale observer output')
 return path

def sources():
 result={}
 for n in INPUTS:
  data=subprocess.check_output(['git','show','HEAD:'+n],cwd=b.ROOT,timeout=10)
  b.require(regular(b.ROOT/n).read_bytes()==data,'Commit observer compiler inputs')
  result[n]=hashlib.sha256(data).hexdigest()
 return result

def project(work):
 data=regular(work/(NAME+'.xml')).read_bytes()
 b.require(b'<!' not in data,'Unexpected XML metadata');root=ET.fromstring(data);ns=smoke.NS
 info=root.find(ns+'device_info')
 b.require(root.tag==ns+'project' and root.get('name')==NAME and info is not None and
  [(n.tag.removeprefix(ns),n.get('name')) for n in info]==[('family','Trion'),('device','T8F49'),('timing_model','I2')],'Observer device differs')
 files=[]
 for n in root.iter():
  tag=n.tag.removeprefix(ns)
  if tag.endswith('_file'):
   expected={'design_file':NAME+'.v','sdc_file':NAME+'_merged.sdc'}
   b.require(tag in expected and n.get('name') in (expected[tag],str(work/expected[tag]) if tag=='design_file' else expected[tag]),'Observer project source differs')
   files.append(tag)
 b.require(sorted(files)==['design_file','sdc_file'],'Missing/duplicate observer project input')
 sections=root.findall(ns+'bitstream_generation');b.require(len(sections)==1,'Observer configuration section')
 modes=[(n.get('name'),n.get('value')) for n in sections[0] if n.get('name') in ('mode','width')]
 b.require(sorted(modes)==[('mode','passive'),('width','1')],'Observer passive mode differs')
 b.require(regular(work/(NAME+'.sdc'),4096).read_text().strip()==old.CLOCK,'Observer direct clock constraint differs')
 text=regular(work/(NAME+'.v')).read_text()
 b.require('$readmem' not in text and not re.search(r'\b(?:Instance|EFX_PLL|EFX_RAM|spi_bone)\b',text),'Unexpected observer external core/memory/PLL')


def interface(work):
 tree=ast.parse(regular(work/'iface.py',65536).read_text());top={id(n.value) for n in tree.body if isinstance(n,ast.Expr)}
 created={};assigned={}
 for n in ast.walk(tree):
  if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute) or not isinstance(n.func.value,ast.Name) or n.func.value.id!='design':continue
  method=n.func.attr
  b.require(id(n) in top and method in {'create','set_iobank_voltage','set_property','create_input_gpio','create_inout_gpio','assign_pkg_pin','generate','save'},'Observer interface operation differs')
  if method not in ('create_input_gpio','create_inout_gpio','assign_pkg_pin'):continue
  b.require(not n.keywords and all(isinstance(a,ast.Constant) and type(a.value) is str for a in n.args),'Dynamic observer interface')
  args=[a.value for a in n.args]
  if method=='assign_pkg_pin':
   b.require(len(args)==2 and args[0] not in assigned,'Duplicate observer package pin');assigned[args[0]]=args[1]
  else:
   b.require(len(args)==1 and args[0] not in created,'Duplicate observer GPIO');created[args[0]]=method[7:-5]
 b.require({n:(mode,assigned.get(n)) for n,mode in created.items()}==GPIO and set(assigned)==set(GPIO),'Observer four-pin boundary differs')
 root=ET.parse(regular(work/(NAME+'.peri.xml'))).getroot();ns='{http://www.efinixinc.com/peri_design_db}'
 nodes=list(root.iter(ns+'gpio'))
 b.require(root.get('name')==NAME and root.get('device_def')=='T8F49' and len(nodes)==4 and {n.get('name'):n.get('mode') for n in nodes}==created,'Observer peripheral map differs')


def rewrite(before,work):
 b.require(type(before) is bytes and 0<len(before)<=1024**2 and b'<!' not in before and
  b'<?' not in re.sub(br'^<\?xml version="1\.0" \?>\n',b'',before,count=1),'Observer XML rewrite metadata')
 root=ET.fromstring(before)
 b.require(root.tag==smoke.NS+'project' and root.attrib.keys()=={'name','location','sw_version','last_change_date'} and
  root.get('name')==NAME and root.get('location')==str(work) and root.get('sw_version')==smoke.VERSION and
  re.fullmatch(r'Date : \d{4}-\d{2}-\d{2} \d{2}:\d{2}',root.get('last_change_date','')),'Observer XML root changed')
 del root.attrib['location'];del root.attrib['last_change_date'];ET.register_namespace('efx',smoke.NS[1:-1])
 return ET.tostring(root,encoding='us-ascii',short_empty_elements=True)


def generated(work):return {n:b.sha(regular(work/n)) for n in GENERATED}

def verify_generated(private,fixed):
 work=private/'work/gateware';before=regular(private/'project-before.xml').read_bytes();actual=generated(work)
 b.require(type(fixed) is dict and set(fixed)==set(GENERATED) and fixed[NAME+'.xml']==hashlib.sha256(before).hexdigest(),'Observer generated inventory differs')
 b.require(all(actual[n]==fixed[n] for n in GENERATED if n!=NAME+'.xml'),'Observer generated source changed')
 b.require((work/(NAME+'.xml')).read_bytes() in (before,rewrite(before,work)),'Observer XML changed beyond reviewed vendor rewrite')
 return actual


def worker(private):
 b.require(os.environ.get('FORGIX_INSIDE_EFINITY')=='1','Locked Efinity worker required');old.provenance();frozen=sources()
 from migen import Module,ClockDomain
 from litex.build.efinix.platform import EfinixPlatform
 from litex_boards.platforms import adiuvo_forgix as board
 from forgix_clock_observer import ClockObserver
 class Platform(board.Platform):
  default_clk_freq=32000000;default_clk_period=31.25
  def __init__(self):EfinixPlatform.__init__(self,'T8F49I2',board._io,board._connectors,iobank_info=board._bank_info,toolchain='efinity',spi_mode='passive',spi_width='1')
  def add_source(self,filename,language=None,library=None,copy=False):
   path=Path(filename).absolute()
   b.require(path==work/(NAME+'.v') and language in (None,'verilog') and library in (None,'work') and not copy,'Observer has no external HDL input')
   super().add_source(str(path),language='verilog',library='work')
 class Top(Module):
  def __init__(self,platform):
   self.clock_domains.cd_sys=ClockDomain('sys')
   self.comb += [self.cd_sys.clk.eq(platform.request('clk32')),self.cd_sys.rst.eq(0)]
   self.submodules.observer=ClockObserver(platform.request('spibone'))
 platform=Platform();top=Top(platform);work=private/'work/gateware';b.private_dir(work)
 platform.build(top,build_dir=str(work),build_name=NAME,run=False)
 project(work);interface(work)
 pt=regular(work/'outflow'/(NAME+'.pt.sdc'));(work/(NAME+'_merged.sdc')).write_bytes(pt.read_bytes()+b'\n#########################\n\n'+(work/(NAME+'.sdc')).read_bytes())
 fixed=generated(work);b.copy_frozen(work/(NAME+'.xml'),private/'project-before.xml',1024**2)
 b.save(private/'generated.json',{'source_sha256':frozen,'generated_sha256':fixed,'pins':GPIO,'profile':PROFILE})
 install=Path(platform.efinity_path);b.require(b.sha(install/'scripts/efx_run.py')==smoke.RUNNER_SHA,'Observer vendor runner differs')
 code=subprocess.run([str(install/'bin/python3'),str(install/'scripts/efx_run.py'),NAME+'.xml','--flow','compile','--timeout','300'],cwd=work,env=platform.toolchain.env,stderr=subprocess.STDOUT,timeout=305).returncode
 b.require(code==0 and sources()==frozen,'Observer vendor failed or inputs changed')
 b.save(private/'project-verification.json',verify_generated(private,fixed));project(work);interface(work)


def outputs(private,started,frozen):
 work=private/'work/gateware';project(work);interface(work)
 text=re.sub(r'\x1b\[[0-9;]*m','',regular(private/'console.log',smoke.MAX_LOG).read_text(errors='replace'))
 b.require(re.findall(r'^\s*(map|interface|pnr|pgm|export_bitstream)\s*:\s*(PASS|SKIP|FAIL)\s*$',text,re.M)==[(n,'PASS') for n in smoke.STAGES],'Observer compiler stages incomplete')
 log=regular(work/'outflow'/(NAME+'.log'),smoke.MAX_LOG,fresh=started)
 b.require(re.findall(r'^Stage completed: (\S+)\s*$',log.read_text(errors='replace'),re.M)==list(smoke.STAGES),'Observer compiler stage log incomplete')
 image=regular(work/'outflow'/(NAME+'.hex'),1024**2,fresh=started)
 record=json.loads(regular(private/'generated.json',65536).read_bytes())
 b.require(record=={'source_sha256':frozen,'generated_sha256':record.get('generated_sha256'),'pins':{n:list(v) for n,v in GPIO.items()},'profile':PROFILE},'Observer generated provenance differs')
 verified=verify_generated(private,record['generated_sha256'])
 b.require(json.loads(regular(private/'project-verification.json',65536).read_bytes())==verified,'Observer worker verification differs')
 reports={};total=0;entries=0;pending=[work/'outflow']
 while pending:
  with os.scandir(pending.pop()) as scan:
   for entry in scan:
    entries+=1;b.require(entries<=512 and not entry.is_symlink(),'Observer output traversal bound')
    path=Path(entry.path)
    if entry.is_dir(follow_symlinks=False):pending.append(path);continue
    regular(path,smoke.MAX_LOG,empty=True);total+=path.stat().st_size
    b.require(len(reports)<256 and total<=512*1024**2,'Observer output inventory bound')
    reports[str(path.relative_to(work/'outflow'))]={'bytes':path.stat().st_size,'sha256':b.sha(path)}
 return {'stages':list(smoke.STAGES),'bitstream_sha256':b.sha(image),'bitstream_bytes':image.stat().st_size,'generated':record,'outflow_reports':reports}


def compile_candidate(store,requested):
 old.provenance();fixed=sources();b.require(not (store.path/'runtime-unclosed.json').exists(),'Unclosed vendor runtime')
 private=smoke.private_path(store,requested);b.require(private.is_relative_to(store.root/'.scratch'),'Fresh ignored observer output required')
 installation,metadata=store.installed()
 b.require(metadata['version']==smoke.VERSION and metadata['software_sha256']==smoke.ARCHIVE_SHA and b.sha(installation/'scripts/efx_run.py')==smoke.RUNNER_SHA,'Reviewed Efinity release required')
 wrapper=shutil.which('forgix-efinity');envbin=shutil.which('env');python=os.environ.get('FORGIX_PYTHON')
 b.require(all(v and Path(v).resolve().is_relative_to('/nix/store') for v in (wrapper,envbin,python)),'Locked observer compiler dependencies')
 b.require(shutil.disk_usage(store.path).free>=1024**3,'Observer compile needs1GiB free');b.private_dir(private)
 began=time.monotonic();started=time.time_ns()
 record=dict(PROFILE,status='failed',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=store.root,text=True).strip(),source_sha256=fixed,
  version=smoke.VERSION,software_sha256=smoke.ARCHIVE_SHA,started_at_unix_ns=started,hardware_opened=False,owned_process_group_closed=False,private_generated_files_verified=False)
 try:
  env=os.environ.copy();env['LITEX_ENV_EFINITY']=str(installation)
  with (private/'console.log').open('xb') as output:
   os.fchmod(output.fileno(),0o600)
   code=b.run_owned([wrapper,envbin,'-u','PYTHONHOME','-u','PYTHONPATH',python,'-E','-s',str(store.root/'tools/forgix_clock_candidate.py'),'_worker','--private',str(private)],env,output,330,store,cwd=private)
  record.update(owned_process_group_closed=True,exit_code=code);b.require(code==0,'Observer worker failed; private outputs retained')
  record.update(outputs(private,started,fixed));b.require(sources()==fixed,'Observer compiler inputs changed');record['status']='passed'
 finally:
  record.update(finished_at_unix_ns=time.time_ns(),duration_seconds=time.monotonic()-began)
  safe=smoke.harden_outputs(private) if record['owned_process_group_closed'] else False
  record['private_generated_files_verified']=safe
  if not safe:record['status']='failed'
  b.save(private/'result.json',record)
  b.require(safe or not record['owned_process_group_closed'],'Unsafe observer generated outputs')
 return record

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('compile','_worker'),nargs='?',default='compile');p.add_argument('--private',type=Path,required=True)
 a=p.parse_args();os.umask(0o077);store=b.Store()
 if a.action=='_worker':
  path=a.private.absolute();b.require(path.is_relative_to(store.root/'.scratch') and path!=store.root/'.scratch' and '..' not in path.parts and path.is_dir() and not any(n.is_symlink() for n in (path,*path.parents)) and not (path/'work').exists(),'Fresh private observer worker required');worker(path);return 0
 with store.locked():record=compile_candidate(store,a.private)
 print(json.dumps({k:record[k] for k in ('status','bitstream_sha256','physical_confirmation','programming_admitted')}));return 0
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Compile a separate private synthetic-source candidate; never loads an image.

Run in the locked Forgix shell with --private .scratch/<fresh-directory>.
Fixed T8F49/I2 and 32MHz are software requests, not physical confirmation.
Existing candidate interfaces and qualification registries are untouched.
"""
import argparse
import ast
import csv
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
import xml.etree.ElementTree as ET

import efinity_bootstrap as b
import efinity_compile_smoke as smoke
import forgix_fpga_candidate as old
import forgix_synthetic_gateware as g

NAME = 'forgix_synthetic_candidate'
CORE_NAME = 'forgix_synthetic_source.v'
INPUTS = (*g.INPUTS, 'tools/forgix_synthetic_candidate.py', 'Taskfile.yml')
GENERATED = (NAME+'.v', CORE_NAME, NAME+'.sdc', 'iface.py', NAME+'_mem.init', NAME+'.xml', NAME+'.peri.xml', NAME+'_merged.sdc')
PROJECT_XML = NAME+'.xml'
PROJECT_BEFORE = 'project-before.xml'
PROJECT_REWRITE = 'efinity-2026.1.132-location-date-etree-v1'
PROFILE = dict(old.PROFILE, kind='forgix-offline-synthetic-candidate', schema=1,
               synthetic_abi=0x46534731, synthetic_base=0x10000,
               fifo_records=64, record_bytes=16, offered_record_bytes_s=[256,1024,2048],
               resource_fit_reviewed=False, timing_closure_reviewed=False)


def regular(path, limit=1024**2, fresh=None, *, allow_empty=False):
    for ancestor in (path, *path.parents):
        b.require(not ancestor.is_symlink(), 'Generated path contains a symlink')
    mode=path.stat()
    b.require(stat.S_ISREG(mode.st_mode) and mode.st_nlink==1 and
              (0 if allow_empty else 1)<=mode.st_size<=limit, 'Invalid generated file type or size')
    if fresh is not None:b.require(mode.st_mtime_ns>=fresh, 'Stale compiler output')
    return path


def source_hashes():
    result={}
    for name in INPUTS:
        committed=subprocess.check_output(['git','show','HEAD:'+name],cwd=b.ROOT,timeout=10)
        b.require(regular(b.ROOT/name).read_bytes()==committed, 'Commit synthetic compiler inputs before building')
        result[name]=hashlib.sha256(committed).hexdigest()
    return result


def source_path(work, filename):
    path=Path(filename).absolute()
    if path==b.ROOT/g.CORE:path=work/CORE_NAME
    b.require(path in (work/CORE_NAME,work/(NAME+'.v')), 'Unexpected synthetic HDL source')
    return path


def validate_project(work):
    path=regular(work/(NAME+'.xml'))
    data=path.read_bytes()
    b.require(b'<!ENTITY' not in data and b'<!DOCTYPE' not in data, 'Unexpected project XML metadata')
    root=ET.fromstring(data);ns=smoke.NS
    info=root.find(ns+'device_info')
    b.require(root.tag==ns+'project' and root.get('name')==NAME and info is not None and
              [(n.tag.removeprefix(ns),n.get('name')) for n in info]==[('family','Trion'),('device','T8F49'),('timing_model','I2')], 'Synthetic target changed')
    designs=[];constraints=[]
    for node in root.iter():
        tag=node.tag.removeprefix(ns)
        if tag.endswith('_file'):
            value=node.get('name')
            if tag=='design_file':
                name=next((n for n in (NAME+'.v',CORE_NAME) if value in (n,str(work/n))),None)
                b.require(name is not None, 'Unexpected project HDL input')
                designs.append(name)
            elif tag=='sdc_file':
                b.require(value==NAME+'_merged.sdc', 'Unexpected project constraint input');constraints.append(value)
            else:raise b.Refusal('Unexpected project input category')
    b.require(sorted(designs)==sorted((NAME+'.v',CORE_NAME)) and constraints==[NAME+'_merged.sdc'], 'Missing or duplicate synthetic project input')
    sections=root.findall(ns+'bitstream_generation')
    b.require(len(sections)==1, 'Missing or duplicate bitstream section')
    fields={}
    for node in sections[0]:
        if node.tag==ns+'param' and node.get('name') in ('mode','width'):
            key=node.get('name');b.require(key not in fields, 'Duplicate bitstream mode');fields[key]=node.get('value')
    b.require(fields=={'mode':'passive','width':'1'}, 'Synthetic configuration mode changed')
    b.require(regular(work/(NAME+'.sdc'),4096).read_text().strip()==old.CLOCK, 'Synthetic clock constraint changed')


def validate_interface(work):
    tree=ast.parse(regular(work/'iface.py',65536).read_text())
    calls={id(n.value) for n in tree.body if isinstance(n,ast.Expr)}
    created={};assigned={}
    allowed={'create','set_iobank_voltage','set_property','create_input_gpio','create_inout_gpio','assign_pkg_pin','generate','save'}
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute) or not isinstance(n.func.value,ast.Name) or n.func.value.id!='design':continue
        method=n.func.attr
        b.require(method in allowed and id(n) in calls, 'Unexpected interface operation')
        if method not in ('create_input_gpio','create_inout_gpio','assign_pkg_pin'):continue
        b.require(not n.keywords and all(isinstance(x,ast.Constant) and type(x.value) is str for x in n.args), 'Dynamic synthetic GPIO')
        args=[x.value for x in n.args]
        if method=='assign_pkg_pin':
            b.require(len(args)==2 and args[0] not in assigned, 'Duplicate synthetic pin');assigned[args[0]]=args[1]
        else:
            b.require(len(args)==1 and args[0] not in created, 'Duplicate synthetic GPIO');created[args[0]]=method.removeprefix('create_').removesuffix('_gpio')
    b.require({k:(v,assigned.get(k)) for k,v in created.items()}==old.GPIO and set(assigned)==set(old.GPIO), 'Synthetic physical pin boundary changed')
    root=ET.parse(regular(work/(NAME+'.peri.xml'))).getroot();ns='{http://www.efinixinc.com/peri_design_db}'
    nodes=list(root.iter(ns+'gpio'))
    b.require(root.get('name')==NAME and root.get('device_def')=='T8F49' and len(nodes)==4 and {n.get('name'):n.get('mode') for n in nodes}==created, 'Synthetic peripheral map changed')


def validate_csr(path):
    rows=list(csv.reader(regular(path,65536).read_text().splitlines()))
    expected={'registers_counter':0x1000,'registers_scratch':0x1004}
    found={};region=[]
    for row in rows:
        if len(row)>=3 and row[0]=='csr_register' and row[1] in expected:
            b.require(row[1] not in found, 'Duplicate original register');found[row[1]]=int(row[2],0)
        if len(row)>=4 and row[:2]==['memory_region','synthetic_source']:region.append((int(row[2],0),int(row[3],0)))
    b.require(found==expected and region==[(g.BASE,0x1000)], 'Synthetic or original address map changed')


def generated_hashes(work):
    result={name:b.sha(regular(work/name)) for name in GENERATED}
    b.require(result[CORE_NAME]==b.sha(b.ROOT/g.CORE), 'Copied synthetic core changed')
    text=(work/(NAME+'.v')).read_text()
    b.require(re.findall(r'\$readmemh\("([^"\n]+)"',text)==[NAME+'_mem.init'], 'Unexpected synthetic memory input')
    b.require(re.search(r"\.SYSTEM_HZ\(\d+'h1e84800\)",text.replace(' ','')), 'Synthetic system clock parameter changed')
    return result


def project_rewrite(before, work):
    """Reproduce only the pinned runner's exact location/date+serializer rewrite.

    Compare resulting bytes, never a lossy normalized subtree. Comments, PIs,
    DTDs and unexpected root metadata are absent from the pinned generator and
    refused before preparing an allowance. Child text/attributes/order survive.
    """
    b.require(type(before) is bytes and 0<len(before)<=1024**2 and b'<!' not in before,
              'Unexpected frozen project XML metadata')
    without_declaration=re.sub(br'^<\?xml version="1\.0" \?>\n',b'',before,count=1)
    b.require(b'<?' not in without_declaration, 'Unexpected frozen project XML instruction')
    try:
        parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True,insert_pis=True))
        root=ET.fromstring(before,parser=parser)
    except (ET.ParseError,ValueError) as error:
        raise b.Refusal('Malformed frozen project XML') from error
    b.require(all(type(node.tag) is str for node in root.iter()), 'Unexpected frozen project XML instruction')
    b.require(root.tag==smoke.NS+'project' and root.attrib.keys()=={'name','location','sw_version','last_change_date'} and
              root.get('name')==NAME and root.get('location')==str(work) and root.get('sw_version')==smoke.VERSION,
              'Frozen project metadata changed')
    date=root.get('last_change_date')
    b.require(re.fullmatch(r'Date : \d{4}-\d{2}-\d{2} \d{2}:\d{2}',date) is not None, 'Unexpected project generation date')
    # The reviewed runner prunes these two informational root fields. It also
    # sets the already-identical sw_version and calls tree.write(xmlfile).
    del root.attrib['location'];del root.attrib['last_change_date']
    ET.register_namespace('efx',smoke.NS[1:-1])
    return ET.tostring(root,encoding='us-ascii',short_empty_elements=True)


def project_contract(before, work):
    rewritten=project_rewrite(before,work)
    return {'schema':1,'policy':PROJECT_REWRITE,'before_file':PROJECT_BEFORE,
            'before_sha256':hashlib.sha256(before).hexdigest(),
            'rewritten_sha256':hashlib.sha256(rewritten).hexdigest()}


def verify_generated(private, fixed, contract):
    work=private/'work/gateware'
    b.require(type(fixed) is dict and set(fixed)==set(GENERATED), 'Synthetic generated inventory changed')
    before=regular(private/PROJECT_BEFORE).read_bytes()
    expected=project_contract(before,work)
    b.require(contract==expected and type(contract.get('schema')) is int and
              fixed[PROJECT_XML]==expected['before_sha256'], 'Frozen project provenance changed')
    current=generated_hashes(work)
    b.require(all(current[name]==fixed[name] for name in GENERATED if name!=PROJECT_XML),
              'Synthetic build inputs changed during compilation')
    actual=regular(work/PROJECT_XML).read_bytes()
    if actual==before:rewrite='unchanged'
    elif actual==project_rewrite(before,work):rewrite=PROJECT_REWRITE
    else:raise b.Refusal('Synthetic project changed beyond the exact vendor rewrite')
    return {'policy':rewrite,'before_sha256':expected['before_sha256'],
            'after_sha256':current[PROJECT_XML],
            'all_other_generated_sha256':{name:current[name] for name in GENERATED if name!=PROJECT_XML}}


def vendor_command(installation):
    return [str(installation/'bin/python3'),str(installation/'scripts/efx_run.py'),NAME+'.xml','--flow','compile','--timeout','300']


def worker(private):
    b.require(os.environ.get('FORGIX_INSIDE_EFINITY')=='1', 'Synthetic worker requires the locked FHS runtime')
    from litex.build.efinix.platform import EfinixPlatform
    from litex_boards.platforms import adiuvo_forgix as board
    from litex.soc.integration.builder import Builder
    from forgix_spi_guard import GuardedSPIBone
    old.provenance();frozen=source_hashes()
    work=private/'work/gateware';b.private_dir(work)
    b.copy_frozen(b.ROOT/g.CORE,work/CORE_NAME,1024**2)
    class Platform(board.Platform):
        default_clk_freq=32000000;default_clk_period=31.25
        def __init__(self):
            EfinixPlatform.__init__(self,'T8F49I2',board._io,board._connectors,iobank_info=board._bank_info,toolchain='efinity',spi_mode='passive',spi_width='1')
        def add_source(self,filename,language=None,library=None,copy=False):
            b.require(language in (None,'verilog') and library in (None,'work') and not copy, 'Unexpected synthetic source options')
            super().add_source(str(source_path(work,filename)),language='verilog',library='work')
    soc=g.make_soc(Platform)
    Builder(soc,output_dir=str(private/'work'),compile_software=False,csr_csv=str(private/'csr.csv')).build(build_name=NAME,run=False)
    validate_project(work);validate_interface(work);validate_csr(private/'csr.csv')
    # Exactly reproduce the pinned toolchain's SDC merge; no generic script
    # hook or candidate validator is replaced, and no compiler flag is inferred.
    peripheral=regular(work/'outflow'/(NAME+'.pt.sdc'))
    (work/(NAME+'_merged.sdc')).write_bytes(peripheral.read_bytes()+b'\n#########################\n\n'+(work/(NAME+'.sdc')).read_bytes())
    fixed=generated_hashes(work)
    b.copy_frozen(work/PROJECT_XML,private/PROJECT_BEFORE,1024**2)
    contract=project_contract(regular(private/PROJECT_BEFORE).read_bytes(),work)
    b.save(private/'generated.json',{'pins':old.PINS,'source_sha256':frozen,'generated_sha256':fixed,
        'project_xml_contract':contract,
        'registers':{k:g.BASE+v for k,v in g.REGISTERS.items()},'csr_sha256':b.sha(private/'csr.csv'),
        'guard':{'sha256':b.sha(Path(inspect.getfile(GuardedSPIBone))),'idle_cycles':32,'turnaround_cycles':64}})
    installation=Path(soc.platform.efinity_path)
    b.require(b.sha(installation/'scripts/efx_run.py')==smoke.RUNNER_SHA, 'Synthetic vendor runner changed')
    result=subprocess.run(vendor_command(installation),cwd=work,env=soc.platform.toolchain.env,stderr=subprocess.STDOUT,timeout=305)
    b.require(result.returncode==0, 'Synthetic vendor compiler failed')
    b.require(frozen==source_hashes(), 'Synthetic build inputs changed during compilation')
    project_verified=verify_generated(private,fixed,contract)
    validate_project(work);validate_interface(work);validate_csr(private/'csr.csv')
    b.save(private/'project-verification.json',project_verified)


def verify_outputs(private,started,frozen):
    work=private/'work/gateware'
    validate_project(work);validate_interface(work);validate_csr(private/'csr.csv')
    console=regular(private/'console.log',smoke.MAX_LOG)
    text=re.sub(r'\x1b\[[0-9;]*m','',console.read_text(errors='replace'))
    markers=re.findall(r'^\s*(map|interface|pnr|pgm|export_bitstream)\s*:\s*(PASS|SKIP|FAIL)\s*$',text,re.M)
    b.require(markers==[(stage,'PASS') for stage in smoke.STAGES], 'Incomplete synthetic compiler stages')
    stage_log=regular(work/'outflow'/(NAME+'.log'),smoke.MAX_LOG,started)
    b.require(re.findall(r'^Stage completed: (\S+)\s*$',stage_log.read_text(errors='replace'),re.M)==list(smoke.STAGES), 'Incomplete synthetic stage log')
    image=regular(work/'outflow'/(NAME+'.hex'),16*1024**2,started)
    generated=json.loads(regular(private/'generated.json',65536).read_text())
    project_verified=verify_generated(private,generated.get('generated_sha256'),generated.get('project_xml_contract'))
    b.require(json.loads(regular(private/'project-verification.json',65536).read_text())==project_verified,
              'Synthetic worker project verification changed')
    expected_guard={'sha256':b.sha(b.ROOT/'tools/forgix_spi_guard.py'),'idle_cycles':32,'turnaround_cycles':64}
    b.require(generated.get('guard')==expected_guard and type(generated['guard']['idle_cycles']) is int and type(generated['guard']['turnaround_cycles']) is int, 'Synthetic guard binding changed')
    b.require(generated.get('pins')==old.PINS and generated.get('registers')=={k:g.BASE+v for k,v in g.REGISTERS.items()} and
              generated.get('source_sha256')==frozen and generated.get('csr_sha256')==b.sha(private/'csr.csv'), 'Synthetic generated provenance changed')
    reports={};total=0;entries=0;pending=[work/'outflow']
    while pending:
        with os.scandir(pending.pop()) as directory:
            for entry in directory:
                entries+=1;b.require(entries<=512 and len(reports)<256, 'Synthetic report count exceeded')
                path=Path(entry.path)
                b.require(not entry.is_symlink(), 'Linked synthetic report directory')
                if entry.is_dir(follow_symlinks=False):pending.append(path);continue
                regular(path,smoke.MAX_LOG,allow_empty=True);total+=path.stat().st_size
                b.require(total<=512*1024**2, 'Synthetic report bytes exceeded')
                reports[str(path.relative_to(work/'outflow'))]={'bytes':path.stat().st_size,'sha256':b.sha(path)}
    return {'stages':list(smoke.STAGES),'bitstream_sha256':b.sha(image),'bitstream_bytes':image.stat().st_size,
            'generated':generated,'project_xml_verification':project_verified,'outflow_reports':reports}


def compile_candidate(store,requested):
    old.provenance();frozen=source_hashes()
    b.require(not (store.path/'runtime-unclosed.json').exists(), 'Inspect unverified vendor closure before compiling')
    private=smoke.private_path(store,requested)
    b.require(private.is_relative_to(store.root/'.scratch'), 'Synthetic builds require fresh ignored .scratch storage')
    installation,metadata=store.installed()
    b.require(metadata['version']==smoke.VERSION and metadata['software_sha256']==smoke.ARCHIVE_SHA and b.sha(installation/'scripts/efx_run.py')==smoke.RUNNER_SHA, 'Synthetic build requires the reviewed full Efinity release')
    wrapper=shutil.which('forgix-efinity');envbin=shutil.which('env');python=os.environ.get('FORGIX_PYTHON')
    b.require(all(p and Path(p).resolve().is_relative_to('/nix/store') for p in (wrapper,envbin,python)), 'Locked synthetic compiler runtime missing')
    b.require(shutil.disk_usage(store.path).free>=1024**3, 'Synthetic compiler needs 1 GiB free')
    b.private_dir(private);started=time.time_ns();mono=time.monotonic()
    receipt=dict(PROFILE,status='failed',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=store.root,text=True).strip(),
        source_sha256=frozen,toolchain=old.provenance(),version=smoke.VERSION,software_sha256=smoke.ARCHIVE_SHA,
        started_at_unix_ns=started,hardware_opened=False,owned_process_group_closed=False,private_generated_files_verified=False)
    try:
        env=os.environ.copy();env['LITEX_ENV_EFINITY']=str(installation)
        with (private/'console.log').open('xb') as output:
            os.fchmod(output.fileno(),0o600)
            code=b.run_owned([wrapper,envbin,'-u','PYTHONHOME','-u','PYTHONPATH',python,'-E','-s',str(store.root/'tools/forgix_synthetic_candidate.py'),'_worker','--private',str(private)],env,output,330,store,cwd=private)
        receipt.update(owned_process_group_closed=True,exit_code=code)
        b.require(code==0, 'Synthetic compiler worker failed; private output retained')
        receipt.update(verify_outputs(private,started,frozen))
        b.require(frozen==source_hashes(), 'Synthetic repository inputs changed during build')
        receipt.update(status='passed',compiler_execution_verified=True)
    except BaseException as error:
        receipt['failure_kind']=type(error).__name__
        if isinstance(error,b.Refusal):receipt['reason']=str(error)
        raise
    finally:
        receipt.update(finished_at_unix_ns=time.time_ns(),duration_seconds=time.monotonic()-mono)
        safe=smoke.harden_outputs(private) if receipt['owned_process_group_closed'] else False
        receipt['private_generated_files_verified']=safe
        unsafe_success=receipt['status']=='passed' and not safe
        if unsafe_success:receipt['status']='failed'
        b.save(private/'result.json',receipt)
        if unsafe_success:raise b.Refusal('Unsafe synthetic compiler output')
    return receipt


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('action',choices=('compile','_worker'),nargs='?',default='compile')
    cli.add_argument('--private',type=Path,required=True);args=cli.parse_args();os.umask(0o077)
    try:
        store=b.Store()
        if args.action=='_worker':
            path=args.private.absolute()
            b.require(path.is_relative_to(store.root/'.scratch') and path!=store.root/'.scratch' and '..' not in path.parts and path.is_dir(), 'Invalid synthetic worker path')
            for parent in (path,*path.parents):b.require(not parent.is_symlink(), 'Symlinked synthetic worker path')
            b.require(not (path/'work').exists(), 'Synthetic worker output must be fresh')
            worker(path);return 0
        with store.locked():receipt=compile_candidate(store,args.private)
        print(json.dumps({k:receipt[k] for k in ('kind','status','bitstream_sha256','bitstream_bytes','physical_confirmation','programming_admitted','resource_fit_reviewed','timing_closure_reviewed')}));return 0
    except Exception as error:
        print(json.dumps(dict(PROFILE,status='failed',failure_kind=type(error).__name__,reason=str(error) if isinstance(error,b.Refusal) else 'Inspect private synthetic compiler output',hardware_opened=False)));return 2


if __name__=='__main__':raise SystemExit(main())

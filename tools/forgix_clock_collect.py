"""Finite caller-owned clock collection. No device-opening CLI or retry."""
import hashlib,json,os,stat,time
from pathlib import Path
from forgix_synthetic_collect import PrivateRun
from forgix_usb_ram_capture import inherited_operator_lock
from forgix_clock_wire import command,result

def require(ok,message):
 if not ok:raise ValueError(message)

def collect(path,nonce,build,image,opened,admission,select,lockfd,lockpath,boot_ns,
            clock=time.monotonic_ns,pause=time.sleep,store_factory=PrivateRun):
 require(type(boot_ns) is int and boot_ns>=0,'Immutable conservative boot epoch required')
 raw_command=command(nonce,build,image);transport=None;store=None;problem=None;last=boot_ns;identity=None;held=None
 cutoff=boot_ns+30_000_000_000;until=boot_ns+34_000_000_000
 record={'kind':'forgix-clock-observer-capture','status':'failed','transport_closed':False,'persistence_verified':False,
  'raw_bytes':0,'raw_sha256':None,'observed_unpersisted_bytes':0,'physical_acceptance':False,'calibrated_absolute_frequency':False}
 def now():
  nonlocal last
  n=clock();require(type(n) is int and n>=last,'Invalid/reversed host clock');last=n;return n
 def check(deadline):
  require(now()<deadline,'Observer collector deadline expired')
  a=admission();require(type(a) is dict and a.get('clock_measurement_qualified') is True and a.get('lifecycle_admitted') is True and a.get('build_sha256')==build.hex() and a.get('image_sha256')==image.hex(),'Exact qualified clock lifecycle required')
  s=select();require(identity is None or s==identity,'Selected clock identity changed')
  l=inherited_operator_lock(lockfd,lockpath);require(held is None or held==l,'Inherited operator lock changed');require(now()<deadline,'Admission crossed deadline')
 def event(v):store.event(v)
 def retain(chunk):
  try:store.append(chunk)
  except BaseException:record['observed_unpersisted_bytes']+=len(chunk);raise
 try:
  check(cutoff);identity=select();held=inherited_operator_lock(lockfd,lockpath);check(cutoff)
  store=store_factory(path);check(cutoff);transport=opened(identity,cutoff/1e9);check(cutoff)
  store.command('observe-command',raw_command);event({'operation':'observe','phase':'intent','host_ns':now(),'deadline_ns':cutoff,'bytes':128,'sha256':hashlib.sha256(raw_command).hexdigest()});check(cutoff)
  began=now();written=transport.write(raw_command,cutoff/1e9);ended=now()
  event({'operation':'observe','phase':'write-returned','start_ns':began,'end_ns':ended,'count':written if type(written) is int else None})
  require(type(written) is int and written==128,'Ambiguous command write; never retry');check(cutoff)
  prefix=bytearray()
  while len(prefix)<512:
   check(until);before=now()
   try:chunk=transport.read(512-len(prefix),until/1e9)
   except BaseException as exc:
    chunk=getattr(exc,'consumed_prefix',b'');require(type(chunk) is bytes and len(chunk)<=512-len(prefix),'Invalid exception prefix')
    if chunk:retain(chunk);prefix.extend(chunk)
    event({'operation':'read','phase':'failed','start_ns':before,'end_ns':now(),'observed_prefix_bytes':len(prefix),'error_kind':type(exc).__name__});raise
   require(type(chunk) is bytes and len(chunk)<=512-len(prefix),'Bounded result read required');retain(chunk);prefix.extend(chunk)
   event({'operation':'read','phase':'prefix','start_ns':before,'end_ns':now(),'chunk_bytes':len(chunk),'observed_prefix_bytes':len(prefix)});check(until)
   if not chunk:pause(.001)
  record['validation']=result(bytes(prefix),nonce,build,image);check(until)
  require(record['validation']['observer_status']==0 and record['validation']['configuration_status']==0,'Retained failed clock result')
  record['status']='digital_ratio_observed'
 except BaseException as exc:problem=exc;record.update(status='failed',failure_kind=type(exc).__name__)
 finally:
  if transport is not None:
   try:
    before=now();transport.close();record['transport_closed']=True;record['close_bracket_ns']=[before,now()];require(last<until,'Late transport closure')
   except BaseException as exc:
    problem=problem or exc;record.update(status='failed',closure_failure_kind=type(exc).__name__)
  if store is not None:
   record.update(raw_bytes=store.bytes,raw_sha256=store.digest.hexdigest())
   try:
    event({'operation':'terminal','host_ns':now(),'status':'pending','transport_closed':record['transport_closed']})
    store.close();store.verify();record['persistence_verified']=not record['observed_unpersisted_bytes'];require(now()<until,'Late persistence')
   except BaseException as exc:
    problem=problem or exc;record.update(status='failed',persistence_failure_kind=type(exc).__name__)
    try:store.close()
    except BaseException:pass
   if not record['transport_closed'] or not record['persistence_verified']:record['status']='failed'
   try:
    store.result(record);require(now()<until,'Late final result persistence')
   except BaseException as exc:
    problem=problem or exc;record.update(status='failed',persistence_verified=False,result_failure_kind=type(exc).__name__)
    # A visible successful file whose required fsync/deadline failed must not
    # remain authoritative. Retain a separate pending blocker if correction fails.
    try:
     pending=store.path/'finalization-pending.json'
     with store._open(pending.name) as out:store.durable(out,b'{"status":"pending"}\n')
     temp=store.path/'result-failed.json'
     with store._open(temp.name) as out:store.durable(out,(json.dumps(record,sort_keys=True)+'\n').encode())
     os.replace(temp,store.path/'result.json');fd=os.open(store.path,os.O_RDONLY|os.O_DIRECTORY)
     try:os.fsync(fd)
     finally:os.close(fd)
    except BaseException:pass
 if problem is not None:problem.collection_result=record;raise problem
 return record

def replay(path,nonce,build,image):
 from forgix_clock_candidate import regular
 path=Path(path)
 require(not any(p.is_symlink() for p in (path,*path.parents)),'Linked private capture')
 info=path.stat();require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),'Owned private capture required')
 def private(name,limit):
  file=regular(path/name,limit);s=file.stat();require(stat.S_IMODE(s.st_mode)==0o600 and s.st_uid==os.getuid(),'Owned private capture file required');return file
 raw=private('raw.bin',512).read_bytes();saved=json.loads(private('result.json',65536).read_bytes())
 require(not (path/'finalization-pending.json').exists(),'Unfinished collector persistence')
 require(saved.get('status')=='digital_ratio_observed' and saved.get('transport_closed') is True and saved.get('persistence_verified') is True and saved.get('raw_bytes')==512 and saved.get('raw_sha256')==hashlib.sha256(raw).hexdigest(),'Complete retained clock capture required')
 require(private('observe-command.bin',128).read_bytes()==command(nonce,build,image),'Retained command differs')
 journal=[json.loads(line) for line in private('journal.jsonl',4*1024**2).read_bytes().splitlines()]
 intent=[x for x in journal if x.get('operation')=='observe' and x.get('phase')=='intent'];returned=[x for x in journal if x.get('operation')=='observe' and x.get('phase')=='write-returned']
 require(len(intent)==len(returned)==1 and intent[0]['host_ns']<=returned[0]['start_ns']<=returned[0]['end_ns']<intent[0]['deadline_ns'] and type(returned[0]['count']) is int and returned[0]['count']==128,'One finite saved command required')
 sizes=[x.get('chunk_bytes') for x in journal if x.get('phase')=='prefix'];require(all(type(n) is int and n>=0 for n in sizes) and sum(sizes)==512,'Full saved prefix ledger differs')
 validated=result(raw,nonce,build,image);require(validated==saved.get('validation') and validated['observer_status']==0,'Saved clock validation differs');return validated

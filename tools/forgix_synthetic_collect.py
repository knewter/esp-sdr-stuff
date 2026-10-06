"""Bounded caller-owned collection; no device discovery, load or hardware CLI.

The caller must contain potentially blocked transport calls in a bounded owned
worker and separately prove preservation/qualified loading/factory recovery.
No command line opens a device.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from forgix_synthetic_stream import Binding, Validator, Control, StreamError, require, CONTRACT_SHA256
from forgix_usb_ram_capture import inherited_operator_lock

class PrivateRun:
    def __init__(self, path):
        self.path=Path(path)
        require(not self.path.exists(), 'New exclusive private run directory required')
        # Do not follow a substituted ancestor while creating private evidence.
        for part in [self.path.parent,*self.path.parent.parents]:
            require(not part.is_symlink(), 'Symlink ancestor refused')
        self.path.mkdir(mode=0o700)
        require(self.path.stat().st_uid==os.getuid() and stat.S_IMODE(self.path.stat().st_mode)==0o700,
                'Owned private0700 directory required')
        self.raw=self._open('raw.bin')
        try:self.journal=self._open('journal.jsonl')
        except BaseException:
            self.raw.close()
            raise
        self.digest=hashlib.sha256();self.bytes=0;self.events=[];self.commands={}

    def _open(self, name):
        fd=os.open(self.path/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        return os.fdopen(fd,'wb',buffering=0)

    @staticmethod
    def durable(handle, data):
        view=memoryview(data)
        while view:
            n=handle.write(view)
            require(type(n) is int and n>0, 'Private write made no progress')
            view=view[n:]
        os.fsync(handle.fileno())

    def event(self, record):
        self.durable(self.journal,(json.dumps(record,sort_keys=True)+'\n').encode())
        self.events.append(record)

    def append(self, data):
        self.durable(self.raw,data)
        self.digest.update(data);self.bytes+=len(data)

    def command(self, name, data):
        with self._open(name+'.bin') as handle:self.durable(handle,data)
        self.commands[name+'.bin']=data

    def close(self):
        try:self.raw.close()
        finally:self.journal.close()

    def verify(self):
        info=(self.path/'raw.bin').stat()
        require(info.st_size==self.bytes and hashlib.sha256((self.path/'raw.bin').read_bytes()).hexdigest()==self.digest.hexdigest(),
                'Private raw readback differs')
        require([json.loads(line) for line in (self.path/'journal.jsonl').read_bytes().splitlines()]==self.events,
                'Private journal readback differs')
        for name,data in self.commands.items():require((self.path/name).read_bytes()==data, 'Private command readback differs')

    def result(self, value):
        with self._open('result.json') as h:self.durable(h,(json.dumps(value,indent=2)+'\n').encode())

ADMISSION_INTERVAL_NS=1_000_000_000

def collect(path, binding, open_transport, verify_admission, select_identity,
            lockfd, lockpath, boot_host_ns, clock_ns=time.monotonic_ns, pause=time.sleep,
            host_pause=True, store_factory=PrivateRun):
    """One CONFIG/START session using an admitted injected transport factory.

    Transport interface read(maxbytes, absolute_deadline_seconds),
    write(bytes, absolute_deadline_seconds)->actual count, close(). Read
    exceptions may attach bytes as consumed_prefix; adapters must not discard
    consumed bytes. No possibly consumed command is retried.
    """
    require(type(binding) is Binding, 'Exact run binding required')
    require(type(boot_host_ns) is int and boot_host_ns>=0, 'Caller boot-based monotonic epoch required')
    require(type(host_pause) is bool, 'Explicit host-reader pause required')
    lifetime=boot_host_ns+120_000_000_000;config_cutoff=boot_host_ns+30_000_000_000
    last_ns=boot_host_ns;transport=None;store=None;validator=Validator(binding)
    result={'status':'failed','transport_closed':False,'persistence_verified':False,
            'physical_acceptance':False,'contract_sha256':CONTRACT_SHA256,'host_pause':None,
            'raw_bytes':0,'raw_sha256':None,'failure':None,'operation':None,'observed_unpersisted_bytes':0}
    problem=None;close_problem=None;identity=None;initial_lock=None
    def now():
        nonlocal last_ns
        value=clock_ns()
        require(type(value) is int and value>=last_ns, 'Host clock reversed or invalid')
        last_ns=value
        return value
    last_admission=None
    def check(deadline,full=False):
        nonlocal last_admission
        require(now()<deadline, 'Absolute collector deadline expired')
        # Full admission re-hashes every frozen input (~250 ms on the reference
        # host). Run per frame it throttled physical episode 001 to ~2 frames/s,
        # overflowing the FPGA FIFO. It now runs on every command and at the end
        # (full=True) and at most once per second while streaming; identity,
        # lock and deadline stay checked on every call.
        if full or last_admission is None or now()-last_admission>=ADMISSION_INTERVAL_NS:
            admission=verify_admission()
            require(type(admission) is dict and admission.get('synthetic_stream_qualified') is True
                    and admission.get('lifecycle_admitted') is True
                    and admission.get('contract_sha256')==CONTRACT_SHA256
                    and admission.get('build_sha256')==binding.build.hex()
                    and admission.get('image_sha256')==binding.image.hex()
                    and admission.get('rp_drain_pause_enabled') is binding.rp_pause, 'Qualified synthetic lifecycle/artifacts required')
            last_admission=now()
        selected=select_identity()
        require(identity is None or selected==identity, 'Selected original identity changed')
        current=inherited_operator_lock(lockfd,lockpath)
        require(initial_lock is None or current==initial_lock, 'Inherited operator lock changed')
        require(now()<deadline, 'Checks crossed absolute deadline')
    def event(record):
        store.event(record)
    def retain(data):
        try:store.append(data)
        except BaseException:
            result['observed_unpersisted_bytes']+=len(data)
            raise
    def write_command(operation,deadline):
        raw=binding.command(operation);name='config' if operation==1 else 'start'
        check(deadline,full=True);result['operation']=name+'-intent'
        store.command(name+'-command',raw)
        event({'operation':name,'phase':'intent','host_ns':now(),'deadline_ns':deadline,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        check(deadline)
        began=now();result['operation']=name+'-write'
        # Single write even if a short count is returned. Never append/retry.
        count=transport.write(raw,deadline/1e9)
        ended=now()
        event({'operation':name,'phase':'write-returned','start_ns':began,'end_ns':ended,'count':count if type(count) is int else None})
        require(type(count) is int and count==128, 'Ambiguous short command write')
        check(deadline,full=True)
        return began
    def frame(deadline):
        prefix=bytearray();began=now();offset=store.bytes
        while len(prefix)<512:
            check(deadline);result['operation']='read-frame'
            before=now()
            try:chunk=transport.read(512-len(prefix),deadline/1e9)
            except BaseException as exc:
                consumed=getattr(exc,'consumed_prefix',b'')
                require(type(consumed) is bytes and len(consumed)<=512-len(prefix),'Invalid exception-attached read prefix')
                if consumed:
                    retain(consumed);prefix.extend(consumed)
                event({'operation':'read-frame','phase':'failed','start_ns':before,'end_ns':now(),
                       'frame_offset':offset,'observed_prefix_bytes':len(prefix),'error_kind':type(exc).__name__})
                raise
            require(type(chunk) is bytes and len(chunk)<=512-len(prefix), 'Bounded read bytes required')
            # Retain before checking a late return or parsing its bytes.
            retain(chunk);prefix.extend(chunk)
            ended=now()
            event({'operation':'read-frame','phase':'prefix','start_ns':before,'end_ns':ended,
                   'frame_offset':offset,'chunk_bytes':len(chunk),'observed_prefix_bytes':len(prefix)})
            require(store.bytes<=(binding.target+3)*512,'Finite raw byte bound exceeded')
            check(deadline)
            if not chunk:pause(min(.001,max(0,(deadline-now())/1e9)))
        event({'operation':'frame','phase':'complete','start_ns':began,'end_ns':now(),'frame_offset':offset})
        return bytes(prefix),now()
    try:
        # Admission/identity/lock refusal must precede opening or intents.
        check(config_cutoff);identity=select_identity();initial_lock=inherited_operator_lock(lockfd,lockpath)
        check(config_cutoff);store=store_factory(path)
        opened=now();result['operation']='open'
        check(config_cutoff);transport=open_transport(identity,config_cutoff/1e9);check(config_cutoff)
        event({'operation':'open','phase':'returned','start_ns':opened,'end_ns':now()})
        config_deadline=min(config_cutoff,now()+20_000_000_000)
        write_command(1,config_deadline)
        raw,stamp=frame(config_deadline);c=validator.accept(raw,stamp)
        require(type(c) is Control and c.kind==2 and c.values['status']==0,'CONFIG not verified')
        validator.mark_start()
        start_intent=write_command(2,config_cutoff)
        raw,stamp=frame(config_cutoff);c=validator.accept(raw,stamp)
        require(type(c) is Control and c.kind==3,'START not verified')
        started_ack=stamp;until=min(lifetime,start_intent+68_000_000_000)
        pause_due=started_ack+30_000_000_000;paused=False
        while validator.state!='ended':
            check(until)
            if host_pause and not paused and now()>=pause_due:
                paused=True;before=now();event({'operation':'host-reader-pause','phase':'intent','host_ns':before})
                pause(.1);after=now();result['host_pause']={'start_ns':before,'end_ns':after,'duration_ns':after-before}
                event({'operation':'host-reader-pause','phase':'returned',**result['host_pause']})
                require(after-before>=100_000_000, 'Host pause shorter than100ms')
                check(until)
            raw,stamp=frame(until);validator.accept(raw,stamp)
        result['validation']=validator.summary()
        if host_pause:require(paused,'Declared host pause did not run')
        check(until,full=True);result['status']='lossless' if result['validation']['lossless'] else 'forensic_failed'
    except BaseException as exc:
        problem=exc;result['status']='failed';result['failure']={'kind':type(exc).__name__,'operation':result['operation']}
        result['validation']=validator.summary()
    finally:
        if transport is not None:
            began=None
            try:began=now()
            except BaseException as exc:
                if problem is None:problem=exc
                result['status']='failed'
            try:
                transport.close();result['transport_closed']=True
                ended=now();result['close_bracket_ns']=[began,ended]
                require(ended<lifetime,'Closure crossed whole-run deadline')
            except BaseException as exc:
                close_problem=exc;result['status']='failed';result['closure_failure_kind']=type(exc).__name__
        if store is not None:
            result['raw_bytes']=store.bytes;result['raw_sha256']=store.digest.hexdigest()
            try:
                event({'operation':'terminal','host_ns':now(),'status':result['status'],'failure':result['failure'],
                       'transport_closed':result['transport_closed']})
                store.close();store.verify();result['persistence_verified']=not result['observed_unpersisted_bytes']
            except BaseException as exc:
                if problem is None:problem=exc
                result['persistence_failure_kind']=type(exc).__name__
                try:store.close()
                except BaseException:pass
            if not result['transport_closed'] or not result['persistence_verified']:result['status']='failed'
            try:store.result(result)
            except BaseException as exc:
                result['status']='failed';result['persistence_verified']=False
                result['result_persistence_failure_kind']=type(exc).__name__
                if problem is None:problem=exc
    if close_problem is not None:
        close_problem.collection_result=result
        raise close_problem
    if problem is not None:
        problem.collection_result=result
        raise problem
    return result

def replay(path, binding):
    """Verify saved private bytes/intents and parse every whole retained frame.

    Partial or invalid tails remain failed evidence. This read-only API cannot
    infer admission, worker closure, recovery or physical delivery from a file.
    """
    path=Path(path)
    require(path.is_dir() and not path.is_symlink() and path.stat().st_uid==os.getuid()
            and stat.S_IMODE(path.stat().st_mode)==0o700, 'Owned private replay directory required')
    def read(name,maximum):
        p=path/name;info=p.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid()
                and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=maximum, 'Bounded private replay file required')
        return p.read_bytes()
    raw=read('raw.bin',(binding.target+3)*512)
    original=json.loads(read('result.json',16*1024*1024))
    require(original['raw_bytes']==len(raw) and original['raw_sha256']==hashlib.sha256(raw).hexdigest(), 'Retained raw hash/count differs')
    journal=[json.loads(line) for line in read('journal.jsonl',128*1024*1024).splitlines()]
    intents=[event for event in journal if event.get('phase')=='intent' and event.get('operation') in ('config','start')]
    require([event['operation'] for event in intents] in ([],['config'],['config','start']), 'One-shot command order differs')
    for ix,event in enumerate(intents,1):
        command=read(event['operation']+'-command.bin',128)
        require(command==binding.command(ix) and event['bytes']==128
                and event['sha256']==hashlib.sha256(command).hexdigest(), 'Saved command intent differs')
    complete=[event for event in journal if event.get('operation')=='frame' and event.get('phase')=='complete']
    v=Validator(binding);error=None;consumed=0
    for event in complete:
        offset=event['frame_offset']
        require(type(offset) is int and offset==consumed and offset+512<=len(raw), 'Saved frame brackets differ')
        p=raw[offset:offset+512]
        if p[5]==2:
            require(len(intents)>=1 and intents[0]['host_ns']<=event['start_ns'], 'CONFIG lacks retained prior intent')
        if p[5]==3:
            require(len(intents)==2 and intents[1]['host_ns']<=event['start_ns'], 'START lacks its retained prior intent')
            v.mark_start()
        try:v.accept(p,event['end_ns'])
        except (ValueError,StreamError) as exc:
            error=type(exc).__name__
            break
        consumed+=512
    # No scan for another magic or hidden valid packet after a failure.
    summary=v.summary()
    summary.update({'replayed_bytes':consumed,'retained_bytes':len(raw),'unaccepted_prefix_bytes':len(raw)-consumed,
                    'parse_failure_kind':error,'collector_terminal_status':original['status'],
                    'saved_transport_closed':original['transport_closed'],
                    'saved_persistence_verified':original['persistence_verified'],
                    'physical_acceptance':False,'post_END_bytes_not_probed':True})
    summary['lossless']=(summary['lossless'] and consumed==len(raw) and original['status']=='lossless'
                         and original['transport_closed'] is True and original['persistence_verified'] is True)
    return summary

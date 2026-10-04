"""Pure finite stream controls/validation. No device or physical admission."""
from dataclasses import dataclass
import struct
import zlib
from forgix_synthetic_codec import Batch, SourceRecord, Stream, CodecError, PROFILES

CONTRACT_SHA256 = '54c62ab91d77a5d7a9b8cfc62c78528de825c6d7bde7cb512c35724c5a675897'
HEADER = struct.Struct('<4sBBHIHHHHQ16sIIIQ')
U64 = (1 << 64) - 1
FIELDS = {
    'status':(128,'I'), 'flags':(132,'I'), 'boot_age_us':(136,'Q'),
    'start_us':(144,'Q'), 'finalized_us':(152,'Q'), 'source_start':(160,'Q'),
    'source_tick':(168,'Q'), 'source_stop':(176,'Q'), 'source_state':(184,'I'),
    'snapshot_id':(188,'I'), 'generated':(192,'I'), 'enqueued':(196,'I'),
    'drops':(200,'I'), 'popped':(204,'I'), 'remaining':(208,'I'),
    'source_highwater':(212,'I'), 'refused_pop':(216,'I'), 'refused_command':(220,'I'),
    'confirmed':(224,'I'), 'staged':(228,'I'), 'encoded_frames':(232,'I'),
    'accepted_frames':(236,'I'), 'accepted_bytes':(240,'Q'), 'partial_writes':(248,'I'),
    'stall_intervals':(252,'I'), 'longest_stall_us':(256,'Q'), 'queue_highwater':(264,'I'),
    'uncertain_sequence':(268,'I'), 'pending_flags':(288,'I'), 'queued_data':(292,'I'),
    'partial_records':(296,'I'), 'stop_state':(300,'I'), 'pause_start_us':(304,'Q'),
    'pause_end_us':(312,'Q'),
}

class StreamError(ValueError):
    pass

def require(value, message):
    if not value:
        raise StreamError(message)

@dataclass(frozen=True)
class Binding:
    nonce: bytes
    period: int
    target: int
    build: bytes
    image: bytes
    rp_pause: bool = False

    def __post_init__(self):
        for value, length in [(self.nonce,16),(self.build,32),(self.image,32)]:
            require(type(value) is bytes and len(value)==length and any(value), 'Exact nonzero binding bytes required')
        require(type(self.period) is int and type(self.target) is int and PROFILES.get(self.period)==self.target,
                'Exact finite period/target pair required')
        require(type(self.rp_pause) is bool, 'Exact build-declared RP drain-pause policy required')

    def command(self, operation):
        require(type(operation) is int and operation in (1,2), 'CONFIG or START required')
        raw = bytearray(128)
        struct.pack_into('<4sBBH16sII32s32s',raw,0,b'FSQ1',1,operation,128,
                         self.nonce,self.period,self.target,self.build,self.image)
        struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
        return bytes(raw)

@dataclass(frozen=True)
class Control:
    kind: int
    timestamp_us: int
    values: dict
    uncertain_record: bytes

    @classmethod
    def decode(cls, raw, binding):
        require(type(raw) is bytes and len(raw)==512, 'Exact control length required')
        h = HEADER.unpack_from(raw)
        magic,version,kind,header,ordinal,length,count,nbytes,reserved,stamp,nonce,first,period,target,r64 = h
        require((magic,version,header,length)==(b'FSB1',1,64,512) and kind in (2,3,4), 'Unknown control header')
        require(ordinal==kind-2 and not any((count,nbytes,reserved,first,r64)) and not any(raw[320:508]),
                'Control ordinal/reserved fields differ')
        require(zlib.crc32(raw[:508])==struct.unpack_from('<I',raw,508)[0], 'Control CRC differs')
        require((nonce,period,target)==(binding.nonce,binding.period,binding.target), 'Control nonce/profile differs')
        require(raw[64:96]==binding.build and raw[96:128]==binding.image, 'Control build/image differs')
        v = {name:struct.unpack_from('<'+fmt,raw,offset)[0] for name,(offset,fmt) in FIELDS.items()}
        require(v['status']<=9 and v['flags']<=15 and v['pending_flags']<=7 and v['stop_state']<=2,
                'Reserved status/flags differ')
        require(v['source_state']<=127 and v['remaining']<=64 and v['source_highwater']<=64,
                'Source limits differ')
        require(v['queue_highwater']<=16 and v['queued_data']<=16 and v['partial_records']<=26,
                'RP queue limits differ')
        require(v['staged']<=v['confirmed']<=binding.target and v['accepted_frames']<=v['encoded_frames']<=binding.target,
                'RP counters are impossible')
        require(v['boot_age_us']<=stamp and v['boot_age_us']<120_000_000 and v['longest_stall_us']<=v['boot_age_us'],
                'Boot/lifetime/stall bounds differ')
        require(v['start_us']<=stamp and v['finalized_us']<=stamp, 'Control time is in the future')
        pause_start,pause_end=v['pause_start_us'],v['pause_end_us']
        require((pause_start==pause_end==0) or (v['start_us'] and pause_start>=v['start_us']+30_000_000
                and pause_end==pause_start+100_000), 'Declared RP drain pause differs')
        uncertain = raw[272:288]
        require(bool(v['flags']&8)==bool(v['pending_flags']&1), 'Pending POP validity differs')
        if v['pending_flags']:
            require(v['pending_flags'] in (1,3,7) and v['uncertain_sequence']<binding.target, 'POP flags/sequence differ')
            record=SourceRecord.decode(uncertain,binding.nonce)
            require(record.sequence==v['uncertain_sequence'], 'Uncertain record sequence differs')
        else:
            require(v['uncertain_sequence']==0 and not any(uncertain), 'Unbound uncertain record differs')
        if v['flags']&4:
            require(v['snapshot_id']>0 and v['generated']<=binding.target
                    and v['generated']==v['enqueued']+v['drops']
                    and v['enqueued']==v['popped']+v['remaining']
                    and v['remaining']<=v['source_highwater']<=v['enqueued'], 'Snapshot conservation differs')
            require(v['source_start']<=v['source_tick'] and
                    (not v['source_stop'] or v['source_start']<=v['source_stop']<=v['source_tick']), 'Snapshot tick bounds differ')
            s=v['source_state']
            require((not s&64 or (s&1 and s&6 in (2,4))) and (not s&6 or s&64)
                    and (not s&8 or (s&64 and v['remaining']>0))
                    and (not s&32 or s&4) and (not v['enqueued'] or v['source_highwater']>0),
                    'Source state contradicts snapshot')
        return cls(kind,stamp,v,uncertain)

class Validator:
    """Strict completeness is latched separately from forward-gap forensics."""
    def __init__(self, binding):
        require(type(binding) is Binding, 'Exact stream binding required')
        self.binding=binding
        self.state='config';self.controls=[];self.strict=None;self.strict_failure=None
        self.last_stamp=-1;self.boot_epoch=None;self.start=None;self.anchor=None
        self.next_frame=0;self.next_record=0;self.frames=0;self.records=0
        self.gaps=[];self.frame_gaps=[];self.arrivals=[];self.end=None
        self.start_host_ns=None;self.end_host_ns=None;self.last_host_ns=-1
        self.protocol_failure=None

    def mark_start(self):
        require(self.state=='start_required', 'START intent ordering differs')
        self.state='start'

    def accept(self, raw, host_ns):
        if self.protocol_failure is not None:
            raise self.protocol_failure
        try:
            return self._accept(raw,host_ns)
        except ValueError as exc:
            self.protocol_failure=exc
            if self.strict_failure is None:
                self.strict_failure=getattr(getattr(exc,'code',None),'name',type(exc).__name__)
            raise

    def _accept(self, raw, host_ns):
        require(type(host_ns) is int and host_ns>=0, 'Host monotonic timestamp required')
        require(host_ns>=self.last_host_ns, 'Host arrival clock reversed')
        require(type(raw) is bytes and len(raw)==512, 'Exact frame required')
        require(self.state!='ended', 'Bytes appeared after END')
        kind=raw[5]
        if kind==1:
            require(self.state=='data', 'DATA before verified START')
            b=Batch.decode(raw,self.binding.nonce)
            require((b.period_cycles,b.target_records)==(self.binding.period,self.binding.target), 'DATA profile differs')
            require(b.device_time_us>=self.last_stamp and b.device_time_us<self.start+68_000_000, 'DATA clock bounds differ')
            require(b.frame_sequence>=self.next_frame, 'Repeated/reordered DATA frame')
            cursor=self.next_record;new_gaps=[]
            for r in b.records:
                require(cursor<=r.sequence<self.binding.target, 'Repeated/reordered source record')
                if r.sequence>cursor:new_gaps.append({'first':cursor,'last':r.sequence-1,'count':r.sequence-cursor})
                tick=self.anchor+(r.sequence+1)*self.binding.period
                require(r.tick32==tick&0xffffffff, 'Anchored record tick differs')
                cursor=r.sequence+1
            if b.frame_sequence>self.next_frame:
                self.frame_gaps.append({'first':self.next_frame,'last':b.frame_sequence-1,'count':b.frame_sequence-self.next_frame})
            self.gaps.extend(new_gaps)
            if self.strict_failure is None:
                try:self.strict.accept(raw)
                except CodecError as exc:self.strict_failure=exc.code.name
            self.next_frame=b.frame_sequence+1;self.next_record=cursor
            self.frames+=1;self.records+=len(b.records);self.last_stamp=b.device_time_us
            self.arrivals.append({'host_ns':host_ns,'record_bytes':16*len(b.records),'pattern_bytes':4*len(b.records),'device_us':b.device_time_us})
            self.last_host_ns=host_ns
            return b
        c=Control.decode(raw,self.binding);v=c.values
        require(c.timestamp_us>=self.last_stamp, 'Control clock reversed')
        epoch=c.timestamp_us-v['boot_age_us']
        require(self.boot_epoch is None or self.boot_epoch==epoch, 'Boot epoch changed')
        if self.controls:
            prior=self.controls[-1].values
            for key in ('confirmed','staged','encoded_frames','accepted_frames','accepted_bytes','partial_writes','stall_intervals','longest_stall_us','queue_highwater'):
                require(v[key]>=prior[key], 'Control counters decreased')
        if c.kind==2:
            require(self.state=='config', 'Duplicate/late CONFIG')
            if v['status']==0:
                require(v['flags']==1 and v['start_us']==v['finalized_us']==0 and v['accepted_bytes']==0,
                        'Successful CONFIG already contains a run')
                require(v['boot_age_us']<30_000_000 and not any(value for key,value in v.items() if key not in ('status','flags','boot_age_us')),
                        'CONFIG source state differs')
                self.state='start_required'
            else:self.state='failed_config'
        elif c.kind==3:
            require(self.state=='start' and v['status']==0, 'START must follow its one intent')
            require(v['flags']==7 and v['source_state']==67 and v['start_us']>=epoch
                    and v['start_us']-epoch<30_000_000 and v['boot_age_us']<30_000_000
                    and v['accepted_bytes']==512 and not v['finalized_us'], 'Successful START fields differ')
            require(not any(v[k] for k in ('generated','enqueued','drops','popped','remaining','confirmed','staged','encoded_frames','accepted_frames','source_stop','pending_flags')), 'START already contains source records')
            require(v['source_start']<=U64-self.binding.period*self.binding.target, 'Finite FPGA tick range overflows')
            require(v['source_tick']<v['source_start']+self.binding.period, 'Empty START snapshot is past its first due record')
            self.start=v['start_us'];self.anchor=v['source_start'];self.state='data'
            self.strict=Stream(self.binding.nonce,self.binding.period,self.binding.target,self.anchor)
        else:
            require(self.state in ('start_required','failed_config','start','data'), 'END ordering differs')
            require(v['finalized_us']>0 and c.timestamp_us<v['finalized_us']+2_000_000, 'END finalization window differs')
            prior=self.controls[-1].values
            require(v['flags']&3==prior['flags']&3, 'END lost verified CONFIG/START flags')
            if prior['status'] not in (0,8):
                require(v['status']==prior['status'], 'END erased latched failure')
            snapshot_keys=('source_start','source_tick','source_stop','source_state','snapshot_id','generated','enqueued','drops','popped','remaining','source_highwater','refused_pop','refused_command')
            if v['flags']&4:
                require(v['snapshot_id']>prior['snapshot_id'], 'END reused an old coherent snapshot')
            else:
                require(all(v[k]==prior[k] for k in snapshot_keys), 'Invalid final snapshot changed historical fields')
            if self.start is not None:
                require(v['start_us']==self.start and v['source_start']==self.anchor, 'END anchor changed')
                if v['status']==0:
                    require(v['finalized_us']<self.start+65_000_000, 'Successful finalization exceeded run cap')
                if v['pending_flags']:
                    record=SourceRecord.decode(c.uncertain_record,self.binding.nonce)
                    require(record.tick32==(self.anchor+(record.sequence+1)*self.binding.period)&0xffffffff,
                            'Uncertain record tick differs from anchor')
            require(v['accepted_frames']*512+1024==v['accepted_bytes'] if self.start is not None else v['accepted_bytes']>=512,
                    'END prior CDC acceptance differs')
            require(v['accepted_frames']>=self.frames and v['staged']>=self.records, 'Host receipt exceeds RP accounting')
            if v['status']==0:
                require(self.state=='data' and v['flags']==7 and v['source_state'] in (69,101), 'Complete END state differs')
                require(v['generated']==v['enqueued']==v['popped']==v['confirmed']==v['staged']==self.binding.target,
                        'Complete END target counters differ')
                require(not any(v[k] for k in ('drops','remaining','refused_pop','refused_command','pending_flags','queued_data','partial_records','stop_state')), 'Complete END unresolved loss/intent differs')
                require(v['encoded_frames']==v['accepted_frames'] and v['source_stop']==self.anchor+self.binding.period*self.binding.target,
                        'Complete END frame/STOP counters differ')
                require(v['finalized_us']>=self.start+60_000_000, 'Complete END too early')
                require(bool(v['pause_start_us'])==self.binding.rp_pause, 'Complete END differs from build-declared RP pause')
            if self.next_record<self.binding.target:
                self.gaps.append({'first':self.next_record,'last':self.binding.target-1,'count':self.binding.target-self.next_record,'classification':'not received; cause unresolved unless final snapshot reconciles'})
            if self.strict_failure is None and self.strict is not None:
                try:self.strict.finish()
                except CodecError as exc:self.strict_failure=exc.code.name
            self.end=c;self.end_host_ns=host_ns;self.state='ended'
        if c.kind==3:self.start_host_ns=host_ns
        self.controls.append(c);self.last_stamp=c.timestamp_us;self.boot_epoch=epoch;self.last_host_ns=host_ns
        return c

    def summary(self):
        end=self.end.values if self.end else None
        lossless=(self.protocol_failure is None and self.state=='ended' and end['status']==0 and self.strict_failure is None
                  and self.records==self.binding.target and not self.gaps and not self.frame_gaps
                  and self.frames==end['encoded_frames']==end['accepted_frames'])
        bins={};gaps=[]
        began=self.start_host_ns
        finished=self.end_host_ns if self.end_host_ns is not None else (self.arrivals[-1]['host_ns'] if self.arrivals else None)
        span=(finished-began)/1e9 if began is not None and finished is not None else None
        if span is not None:
            bins={i:{'frames':0,'record_bytes':0,'pattern_bytes':0,'wire_bytes':0} for i in range(int(span)+1)}
        if self.arrivals:
            if began is None:began=self.arrivals[0]['host_ns']
            for previous,current in zip(self.arrivals,self.arrivals[1:]):gaps.append(current['host_ns']-previous['host_ns'])
            for a in self.arrivals:
                second=(a['host_ns']-began)//1_000_000_000
                b=bins.setdefault(second,{'frames':0,'record_bytes':0,'pattern_bytes':0,'wire_bytes':0})
                b['frames']+=1;b['record_bytes']+=a['record_bytes'];b['pattern_bytes']+=a['pattern_bytes'];b['wire_bytes']+=512
        reconciliation=None
        if end:
            reconciliation={'fresh_final_source_snapshot':bool(end['flags']&4),
                'RP_confirmed_not_received':end['confirmed']-self.records,
                'RP_confirmed_not_staged':end['confirmed']-end['staged'],
                'RP_encoded_not_API_accepted_frames':end['encoded_frames']-end['accepted_frames'],
                'API_accepted_DATA_frames_not_received':end['accepted_frames']-self.frames,
                'reported_source_remaining':end['remaining'] if end['flags']&4 else None,
                'reported_source_drops':end['drops'] if end['flags']&4 else None,
                'reported_source_generated':end['generated'] if end['flags']&4 else None}
        return {'lossless':lossless,'terminal_received':self.end is not None,'strict_failure':self.strict_failure,
                'received_frames':self.frames,'received_records':self.records,'source_record_bytes':self.records*16,
                'pattern_bytes':self.records*4,'source_sequence_gaps':self.gaps,'data_frame_gaps':self.frame_gaps,
                'arrival_gap_ns':gaps,'per_second_host_arrivals':bins,'end_counters':end,
                'host_start_to_END_seconds':span,
                'record_bytes_per_host_second':self.records*16/span if span and span>0 else None,
                'pattern_bytes_per_host_second':self.records*4/span if span and span>0 else None,
                'reconciliation':reconciliation,
                'unverified_complete_records':self.binding.target-self.records,
                'counter_scope':'RP CDC API acceptance is not independent host delivery; invalid final snapshot fields are retained historical values.'}

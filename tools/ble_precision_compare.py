#!/usr/bin/env python3
"""Frozen same-waveform digital precision diagnostic. No devices or RF claims."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import time
import zlib
import numpy as np
import scipy
from scipy.signal import resample_poly
import ble_decode_iq as decoder
from esp_sdr_capture import unpack, write_private

DECODER_SHA='834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128'
RATE=16_000_000
SAMPLES=16380
CHANNEL=37
LIMIT='Deterministic upper-bit conversion of saved waveforms only; no actual eight-bit RF acquisition, physical sensitivity, air-event denominator, detection rate or acceptance gate.'

def sha(data):return hashlib.sha256(data).hexdigest()

def independent_components(raw):
    """Firmware LE40 two-IQ packing, independent of production unpackbits."""
    if type(raw) is not bytes or len(raw)%5:raise ValueError('Whole LE40 groups required')
    bytes5=np.frombuffer(raw,dtype=np.uint8).reshape(-1,5).astype(np.uint64)
    words=np.sum(bytes5 << np.arange(0,40,8,dtype=np.uint64),axis=1)
    unsigned=((words[:,None] >> np.array([0,10,20,30],dtype=np.uint64))&1023).reshape(-1).astype(np.int16)
    return np.where(unsigned>=512,unsigned-1024,unsigned).astype(np.int16)

def upper8(raw,samples):
    if type(samples) is not int or samples<=0 or samples%2 or len(raw)!=samples*5//2:
        raise ValueError('Exact even-pair ten-bit payload required')
    iq=unpack(raw,samples,10)
    components=np.column_stack((iq.real,iq.imag)).reshape(-1).astype(np.int16)
    independent=independent_components(raw)
    if not np.array_equal(components,independent):raise ValueError('Independent ten-bit packing differs')
    derived=(components >> 2).astype(np.int8).tobytes()
    independent_upper=((independent.astype(np.uint16)&1023)>>2).astype(np.uint8).tobytes()
    if derived!=independent_upper:raise ValueError('Signed/unsigned upper-bit conversion differs')
    return derived

def independent_packet(raw,bits,translation,frame,samples=SAMPLES,channel=CHANNEL):
    """Re-slice AA-selected hypothesis; independent whitening/register CRC24.

    DSP anti-aliasing uses the same declared FIR. Bit packing, register CRC and
    whitening are independently expressed; no known payload trains a hypothesis.
    """
    if bits==10:c=independent_components(raw)
    elif bits==8:c=np.frombuffer(raw,dtype=np.int8).astype(np.int16)
    else:raise ValueError('Unsupported format')
    if len(c)!=samples*2:raise ValueError('Packet sample count differs')
    iq=c[::2].astype(float)+1j*c[1::2]
    if translation:iq=iq*np.exp(2j*np.pi*translation*np.arange(samples)/RATE)
    base=resample_poly(iq-iq.mean(),1,4)
    phase=np.angle(base[1:]*np.conj(base[:-1]))
    period=float(frame['samples_per_symbol_at_4msps']) if frame.get('refined') else 4.0
    offset=float(frame['access_address_sample_offset'])/4
    if not math.isfinite(period) or not 3.97<=period<=4.03:raise ValueError('Selected period differs')
    count=min(368,int((len(phase)-offset)//period))
    if offset<0 or count<56:raise ValueError('Packet header not within waveform')
    cumulative=np.r_[0,np.cumsum(phase)]
    edges=offset+np.arange(count+1)*period
    symbols=np.diff(np.interp(edges,np.arange(len(cumulative)),cumulative))/period
    aa=np.array([(b>>k)&1 for b in bytes.fromhex('d6be898e') for k in range(8)])
    pattern=aa*2-1;centered=pattern-pattern.mean()
    coefficient=float(np.dot(symbols[:32],centered)/np.dot(centered,centered))
    carrier=float(symbols[:32].mean()-coefficient*pattern.mean())
    bias=float(frame.get('threshold_bias_deviation_fraction',0))
    hard=((symbols-carrier-bias*abs(coefficient))*(1 if coefficient>=0 else -1)>0).astype(int)
    state=channel|64;decoded=[]
    for bit in hard[32:]:
        decoded.append(int(bit)^(state&1))
        feedback=state&1;state>>=1
        if feedback:state^=0x44
    def bts(data):return bytes(sum(int(v)<<k for k,v in enumerate(data[i:i+8])) for i in range(0,len(data),8))
    header=bts(decoded[:16]);kind=header[0]&15;length=header[1]&63;end=16+length*8
    if len(decoded)<end+24:raise ValueError('Independent packet truncated')
    register=0xaaaaaa  # reversed SIG initial0x555555
    for bit in decoded[:end]:
        feedback=(register&1)^bit;register>>=1
        if feedback:register^=0xda6000
    expected=[(register>>k)&1 for k in range(24)]
    crc_ok=expected==decoded[end:end+24]
    pdu=bts(decoded[:end]);ad=pdu[8:];cursor=0;owned=False
    while cursor<len(ad):
        size=ad[cursor]
        if size==0:break
        item=ad[cursor:cursor+size+1]
        if len(item)!=size+1:break
        owned|=item==decoder.MARKER_AD;cursor+=size+1
    duration=8+32+16+length*8+24
    begin=(offset-8*period)*4;finish=(offset+(duration-8)*period)*4
    return {'crc24_ok':crc_ok,'owned_manufacturer_ad_exact_match':bool(owned),
            'pdu_sha256':sha(pdu) if owned else None,'pdu_type':kind,'pdu_length':length,
            'nominal_packet_start_sample':begin,'nominal_packet_end_sample':finish,
            'complete_preamble_and_pdu_crc_within_capture_nominal':bool(begin>=0 and finish<=samples)}

def classify(frames,samples=SAMPLES):
    owned=[];other=0
    for f in frames:
        if f['status']=='valid_other_redacted':other+=1
        if f['status']!='valid_owned':continue
        period=f.get('samples_per_symbol_at_4msps') if f.get('refined') else 4.0
        if not isinstance(period,(int,float)) or not math.isfinite(period) or not 3.97<=period<=4.03:
            raise ValueError('Owned symbol bounds differ')
        begin=f['access_address_sample_offset']-8*period*4
        end=f['access_address_sample_offset']+(f['packet_duration_us']-8)*period*4
        full=begin>=0 and end<=samples
        q={**f,'nominal_packet_start_sample':begin,'nominal_packet_end_sample':end,
           'complete_preamble_and_pdu_crc_within_capture_nominal':bool(full)}
        if f.get('crc24_ok') is not True or f.get('owned_manufacturer_ad_exact_match') is not True or not f.get('pdu_sha256'):
            raise ValueError('Incomplete owned proof metadata')
        if full:owned.append(q)
    clusters=[]
    for f in sorted(owned,key=lambda x:x['access_address_sample_offset']):
        if clusters and f['access_address_sample_offset']-clusters[-1][0]['access_address_sample_offset']<64:
            clusters[-1].append(f)
        else:clusters.append([f])
    conflict=any(len({f['pdu_sha256'] for f in g})!=1 for g in clusters) or len(clusters)>1
    return {'full_owned_packets':[] if conflict else [max(g,key=lambda f:f['access_correlation']) for g in clusters],
            'owned_cluster_conflict':conflict,'full_owned_candidate_clusters':len(clusters),
            'foreign_CRC_packets_redacted':other,'candidate_status_counts':{s:sum(f['status']==s for f in frames) for s in sorted({f['status'] for f in frames})},
            'frames':frames}

def verify_row(raw,row,entry):
    if len(raw)!=entry['bytes'] or sha(raw)!=entry['sha256'] or sha(raw)!=row['private_payload_sha256']:
        raise ValueError('Frozen waveform hash/size differs')
    crc=f'{zlib.crc32(raw):08x}'
    valid=(len(raw)==SAMPLES*5//2 and int(row['returned_samples'])==SAMPLES and
           row['crc_ok']=='True' and row['sample_count_ok']=='True' and
           crc==row['actual_crc32']==row['expected_crc32'])
    return valid,crc

def run(frozen_path,output):
    os.umask(0o077)
    if output.exists() or '.scratch' not in output.resolve().parts or any(x in output.resolve().parts for x in ('site','docs')):
        raise ValueError('Fresh ignored private output required')
    frozen_bytes=frozen_path.read_bytes();frozen=json.loads(frozen_bytes)
    root=Path(__file__).resolve().parents[1]
    for name,digest in frozen['source_files'].items():
        if sha((root/name).read_bytes())!=digest:raise ValueError('Frozen runtime input differs: '+name)
    if sha(Path(decoder.__file__).read_bytes())!=DECODER_SHA:raise ValueError('Frozen decoder differs')
    output.mkdir(parents=True,mode=0o700);derived=output/'derived';derived.mkdir(mode=0o700)
    report={'schema':1,'kind':'same-waveform deterministic precision diagnostic','limitations':LIMIT,
            'frozen_input_receipt_sha256':sha(frozen_bytes),'decoder_sha256':DECODER_SHA,
            'script_sha256':sha(Path(__file__).read_bytes()),'rate':RATE,'samples':SAMPLES,'channel':CHANNEL,
            'blind_receiver_refinement':decoder.REFINEMENT,'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},'datasets':[]}
    # Recheck references before decoding without consulting prior packet labels.
    for name,digest in frozen.get('reference_files',{}).items():
        source=Path(frozen['datasets'][0]['csv']).parents[3]/name
        if sha(source.read_bytes())!=digest:raise ValueError('Frozen reference differs')
    phase_path=root/'docs/evidence/ble-matched-gain-001/manual-phases.csv'
    phase_rows=list(csv.DictReader(phase_path.open()))
    matched_phases={int(row['capture_index']):row['source_control_phase'] for row in phase_rows}
    if len(matched_phases)!=1010:raise ValueError('Frozen source-phase row count differs')
    script_bytes=Path(__file__).read_bytes()
    started=time.monotonic()
    for data in frozen['datasets']:
        csvbytes=Path(data['csv']).read_bytes();mb=Path(data['manifest']).read_bytes()
        if sha(csvbytes)!=data['csv_sha256'] or sha(mb)!=data['manifest_sha256']:raise ValueError('Frozen CSV/manifest differs')
        manifest=json.loads(mb)
        if manifest['nominal_rate_hz']!=RATE or manifest['bits_per_component']!=10:raise ValueError('Source format differs')
        rows=list(csv.DictReader(csvbytes.decode().splitlines()))
        if len(rows)!=len(data['rows']) or manifest['captures']!=len(rows):raise ValueError('Frozen row count differs')
        d={'name':data['name'],'csv_sha256':sha(csvbytes),'receiver_manifest_sha256':sha(mb),'rows':[]}
        folder=derived/data['name'];folder.mkdir(mode=0o700)
        for row,entry in zip(rows,data['rows']):
            index=int(row['capture_index'])
            if index!=entry['index']:raise ValueError('Frozen row order differs')
            lo=int(row.get('frequency_mhz',manifest.get('frequency_mhz',0)))
            if lo not in (2401,2402):raise ValueError('Predeclared LO differs')
            translation=(lo-2402)*1_000_000
            raw=Path(entry['path']).read_bytes();valid,crc=verify_row(raw,row,entry)
            item={'capture_index':index,'original_sha256':sha(raw),'original_bytes':len(raw),'original_crc32':crc,
                  'transport_valid':valid,'source_row':row,'frequency_translation_hz':translation,
                  'original_source_control_phase':row.get('phase',matched_phases.get(index) if data['name']=='matched_manual1010' else None)}
            if valid:
                reduced=upper8(raw,SAMPLES);write_private(folder/f'iq-{index:04d}.bin',reduced)
                item.update(derived_sha256=sha(reduced),derived_bytes=len(reduced),derived_crc32=f'{zlib.crc32(reduced):08x}')
                for label,bits,payload in [('original10',10,raw),('derived8',8,reduced)]:
                    frames=decoder.decode_iq(unpack(payload,SAMPLES,bits),RATE,CHANNEL,frequency_translation_hz=translation,refine=True)
                    item[label]=classify(frames)
                    # Independently reconstruct every known-owned full packet,
                    # including any lost/created result in the paired format.
                    for packet in item[label]['full_owned_packets']:
                        proof=independent_packet(payload,bits,translation,packet)
                        if not (proof['crc24_ok'] and proof['owned_manufacturer_ad_exact_match'] and proof['complete_preamble_and_pdu_crc_within_capture_nominal'] and proof['pdu_sha256']==packet['pdu_sha256']):
                            raise ValueError('Independent owned packet proof differs')
                        packet['independent_slicing_whitening_reflected_crc24']=proof
                item['paired_outcome']=[len(item[label]['full_owned_packets']) for label in ('original10','derived8')]
            else:item['paired_outcome']='transport_invalid_retained_not_decoded'
            d['rows'].append(item)
            write_private(output/f'row-{data["name"]}-{index:04d}.json',(json.dumps(item,indent=2)+'\n').encode())
        report['datasets'].append(d)
    # Complete post-run conservation/immutability; never discard null rows.
    for data in frozen['datasets']:
        if sha(Path(data['csv']).read_bytes())!=data['csv_sha256'] or sha(Path(data['manifest']).read_bytes())!=data['manifest_sha256']:
            raise ValueError('CSV/manifest changed during replay')
        for entry in data['rows']:
            if sha(Path(entry['path']).read_bytes())!=entry['sha256']:raise ValueError('Original changed during replay')
    for d in report['datasets']:
        for row in d['rows']:
            if row['transport_valid']:
                saved=(derived/d['name']/f'iq-{row["capture_index"]:04d}.bin').read_bytes()
                if len(saved)!=row['derived_bytes'] or sha(saved)!=row['derived_sha256'] or f'{zlib.crc32(saved):08x}'!=row['derived_crc32']:
                    raise ValueError('Derived private artifact changed during replay')
    for name,digest in frozen['source_files'].items():
        if sha((root/name).read_bytes())!=digest:raise ValueError('Runtime input changed during replay')
    if frozen_path.read_bytes()!=frozen_bytes or Path(__file__).read_bytes()!=script_bytes:
        raise ValueError('Freeze/script changed during replay')
    for name,digest in frozen.get('reference_files',{}).items():
        source=Path(frozen['datasets'][0]['csv']).parents[3]/name
        if sha(source.read_bytes())!=digest:raise ValueError('Reference changed during replay')
    for d in report['datasets']:
        d['summary']={'rows':len(d['rows']),'transport_invalid_rows':sum(not r['transport_valid'] for r in d['rows']),
                      'paired_full_owned_capture_counts':{str(pair):sum(r['paired_outcome']==list(pair) for r in d['rows']) for pair in [(0,0),(1,0),(0,1),(1,1)]},
                      'foreign_CRC_packets_redacted':{label:sum(r.get(label,{}).get('foreign_CRC_packets_redacted',0) for r in d['rows']) for label in ('original10','derived8')}}
    report['runtime_seconds']=time.monotonic()-started
    write_private(output/'results.json',(json.dumps(report,indent=2)+'\n').encode())
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frozen-inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=run(a.frozen_inputs,a.output)
    print(json.dumps({d['name']:d['summary'] for d in report['datasets']},indent=2))
if __name__=='__main__':main()

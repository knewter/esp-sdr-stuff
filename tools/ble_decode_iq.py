#!/usr/bin/env python3
"""Bounded offline LE1M legacy-advertisement decoder for owned SDR captures.

No hardware access. CRC verifies full packets; only known-marker match metadata
is published. Addresses, names and foreign payloads are not returned.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.signal import resample_poly
from esp_sdr_capture import unpack

ACCESS = np.unpackbits(np.frombuffer(bytes.fromhex('d6be898e'),dtype=np.uint8),bitorder='little')
SPEC = 'https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/low-energy-controller/link-layer-specification.html'
SAMPLES = 'https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/low-energy-controller/sample-data.html'
MARKER_AD = bytes.fromhex('0fffffff4553502d5344522d4556414c')


def bits_of(data):
    return np.unpackbits(np.frombuffer(data,dtype=np.uint8),bitorder='little')


def bytes_of(bits):
    return np.packbits(np.asarray(bits,dtype=np.uint8),bitorder='little').tobytes()


def crc_bits(bits,initial=0x555555):
    # Vol6 PartB3.1.1: input LSB-first; state positions0..23 initialized
    # conventionally; CRC is transmitted position23 first.
    register=initial
    for bit in bits:
        feedback=((register>>23)^int(bit))&1
        register=(register<<1)&0xffffff
        if feedback:register^=0x65b
    return np.array([(register>>(23-k))&1 for k in range(24)],dtype=np.uint8)


def whiten(bits,channel):
    # Vol6 PartB3.2: position0=1, positions1..6=channel MSB..LSB.
    state=[1]+[(channel>>(5-k))&1 for k in range(6)]
    out=[]
    for bit in bits:
        out.append(int(bit)^state[6])
        state=[state[6],state[0],state[1],state[2],state[3]^state[6],state[4],state[5]]
    return np.array(out,dtype=np.uint8)


def decode_packet(bits,channel,marker_ad=MARKER_AD):
    if len(bits)<16:return {'status':'truncated_header'}
    decoded=whiten(bits,channel)
    header=bytes_of(decoded[:16])
    kind=header[0]&15
    length=header[1]&63
    if kind not in {0,2,4,6} or not 6<=length<=37:
        return {'status':'unsupported_or_invalid_header'}
    end=16+8*length
    if len(decoded)<end+24:
        return {'status':'truncated_packet','pdu_length':length}
    pdu=decoded[:end]
    if not np.array_equal(crc_bits(pdu),decoded[end:end+24]):
        return {'status':'crc_failed','pdu_length':length}
    packet=bytes_of(pdu)
    advertising=packet[8:] # 2-byte header, 6-byte AdvA discarded.
    # Match a whole AD structure, not incidental substring bytes.
    offset=0;owned=False
    while offset<len(advertising):
        size=advertising[offset]
        if size==0:break
        item=advertising[offset:offset+size+1]
        if len(item)!=size+1:break
        if item==marker_ad:owned=True
        offset+=size+1
    return {'status':'valid_owned' if owned else 'valid_other_redacted',
            'pdu_type':kind,'pdu_length':length,'crc24_ok':True,
            'owned_manufacturer_ad_exact_match':owned,
            'packet_duration_us':(8+32+16+length*8+24),
            'pdu_sha256':hashlib.sha256(packet).hexdigest() if owned else None}


REFINEMENT = {'samples_per_symbol_min':3.97, 'samples_per_symbol_max':4.03,
              'samples_per_symbol_step':.005, 'start_search_half_width_samples_at_4msps':2,
              'start_search_step_samples_at_4msps':.25,
              'threshold_bias_min_deviation_fraction':-.45,
              'threshold_bias_max_deviation_fraction':.45,
              'threshold_bias_step_deviation_fraction':.025,
              'maximum_candidate_clusters_per_capture':32}


def refine_packet(phase,start,down,channel,marker_ad):
    """Blind bounded receiver hypotheses: public AA training, then full CRC.

    No known payload bit influences timing, threshold, symbol-clock or repair.
    Every hypothesis slices the original measured samples and checks full CRC.
    """
    pattern=ACCESS.astype(float)*2-1
    centered=pattern-pattern.mean()
    cumulative=np.r_[0,np.cumsum(phase)]
    coordinate=np.arange(len(cumulative))
    best=None;valid_count=0;attempts=0
    for period in np.linspace(3.97,4.03,13):
        for offset in np.linspace(start-2,start+2,17):
            count=min(368,int((len(phase)-offset)//period))
            if offset<0 or count<56:continue
            edges=offset+np.arange(count+1)*period
            symbols=np.diff(np.interp(edges,coordinate,cumulative))/period
            aa=symbols[:32]
            coefficient=float(np.dot(aa,centered)/np.dot(centered,centered))
            carrier=float(aa.mean()-coefficient*pattern.mean())
            variance=float(np.sum((aa-aa.mean())**2))
            correlation=float(np.dot(aa,centered)/np.sqrt(max(variance,1e-12)*np.dot(centered,centered)))
            if abs(correlation)<.78:continue
            polarity=1 if coefficient>=0 else -1
            for bias in np.linspace(-.45,.45,37):
                hard=((symbols-carrier-bias*abs(coefficient))*polarity>0).astype(np.uint8)
                errors=int(np.count_nonzero(hard[:32]!=ACCESS))
                if errors>2:continue
                attempts+=1
                decoded=decode_packet(hard[32:],channel,marker_ad)
                if not decoded['status'].startswith('valid'):continue
                valid_count+=1
                duration_symbols=decoded['packet_duration_us']
                beginning=(offset-8*period)*down
                ending=(offset+(duration_symbols-8)*period)*down
                # The preamble is before the AA and is not CRC-protected.
                # Retain its independent check and require its sample window.
                preamble_errors=None
                if beginning>=0:
                    pre_edges=offset+np.arange(-8,1)*period
                    pre=np.diff(np.interp(pre_edges,coordinate,cumulative))/period
                    pre_hard=((pre-carrier-bias*abs(coefficient))*polarity>0).astype(np.uint8)
                    expected=np.tile(ACCESS[:2],4)
                    preamble_errors=int(np.count_nonzero(pre_hard!=expected))
                candidate={**decoded,'access_address_hamming_errors':errors,
                           'access_address_sample_offset':offset*down,
                           'access_correlation':abs(correlation),
                           'estimated_carrier_offset_hz':carrier*4000000/(2*np.pi),
                           'iq_polarity':polarity,'samples_per_symbol_at_4msps':float(period),
                           'threshold_bias_deviation_fraction':float(bias),
                           'nominal_packet_start_sample':beginning,'nominal_packet_end_sample':ending,
                           'complete_preamble_and_pdu_crc_within_capture_nominal':bool(beginning>=0 and ending<=len(phase)*down),
                           'preamble_hamming_errors':preamble_errors,
                           'refined':True}
                # Selection uses AA correlation only, never marker agreement.
                if best is None or candidate['access_correlation']>best['access_correlation']:
                    best=candidate
    if best is not None:
        best['crc_valid_receiver_hypotheses']=valid_count
        best['receiver_hypotheses_checked']=attempts
    return best


def decode_iq(iq,rate,channel,marker_ad=MARKER_AD,frequency_translation_hz=0,refine=False):
    if rate not in {16000000,40000000,80000000}:
        raise ValueError('unsupported nominal ADC rate')
    # FIR antialias filtering + resampling to4samples/LE1Msymbol.
    # No rate calibration or clock-recovery guarantee is implied.
    if abs(frequency_translation_hz)>=rate/2:
        raise ValueError('frequency translation outside nominal Nyquist interval')
    if frequency_translation_hz:
        iq=iq*np.exp(2j*np.pi*frequency_translation_hz*np.arange(len(iq))/rate)
    down=rate//4000000
    base=resample_poly(iq-iq.mean(),1,down)
    phase=np.angle(base[1:]*np.conj(base[:-1]))
    results=[];seen=[];raw_candidates=[]
    pattern=ACCESS.astype(float)*2-1
    centered=pattern-pattern.mean()
    for timing in range(4):
        usable=(len(phase)-timing)//4*4
        if usable<128:continue
        symbols=phase[timing:timing+usable].reshape(-1,4).mean(axis=1)
        correlation=np.correlate(symbols,centered,'valid')
        sums=np.convolve(symbols,np.ones(32),'valid')
        squares=np.convolve(symbols*symbols,np.ones(32),'valid')
        variance=np.maximum(squares-sums*sums/32,1e-12)
        normalized=correlation/np.sqrt(variance*np.dot(centered,centered))
        candidates=np.flatnonzero(np.abs(normalized)>.78)
        # Bound noise work; preserve highest correlation candidates if dense.
        if len(candidates)>100:candidates=candidates[np.argsort(np.abs(normalized[candidates]))[-100:]]
        for index in candidates:
            window=symbols[index:index+32]
            coefficient=float(correlation[index]/np.dot(centered,centered))
            offset=float(window.mean()-coefficient*pattern.mean())
            polarity=1 if coefficient>=0 else -1
            hard=((symbols-offset)*polarity>0).astype(np.uint8)
            errors=int(np.count_nonzero(hard[index:index+32]!=ACCESS))
            if errors>2:continue
            position=(int(index)*4+timing)*down
            if any(abs(position-old)<rate//1000000*4 for old in seen):continue
            decoded=decode_packet(hard[index+32:],channel,marker_ad)
            # Keep CRC-failed candidates diagnostically, but do not suppress
            # later timing choices that might verify the same real waveform.
            if decoded['status'].startswith('valid'):seen.append(position)
            candidate={**decoded,'access_address_hamming_errors':errors,
                            'access_address_sample_offset':position,
                            'access_correlation':float(abs(normalized[index])),
                            'estimated_carrier_offset_hz':offset*4000000/(2*np.pi),
                            'iq_polarity':polarity,'timing_phase_at_4msps':timing}
            results.append(candidate)
            raw_candidates.append(candidate)
    if refine:
        groups=[]
        for candidate in sorted(raw_candidates,key=lambda c:c['access_address_sample_offset']):
            if groups and candidate['access_address_sample_offset']-groups[-1][-1]['access_address_sample_offset']<rate//1000000*4:
                groups[-1].append(candidate)
            else:groups.append([candidate])
        selected=sorted(groups,key=lambda g:-max(c['access_correlation'] for c in g))[:32]
        results=[]
        for group in selected:
            best=max(group,key=lambda c:c['access_correlation'])
            already_valid=[candidate for candidate in group if candidate['status'].startswith('valid')]
            if already_valid:
                results.append(max(already_valid,key=lambda c:c['access_correlation']))
                continue
            recovered=refine_packet(phase,best['access_address_sample_offset']/down,down,channel,marker_ad)
            results.append(recovered if recovered is not None else {**best,'refinement_attempted':True})
        results.sort(key=lambda c:c['access_address_sample_offset'])
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rate',type=int,default=16000000)
    parser.add_argument('--bits',type=int,default=8,choices=[8,10])
    parser.add_argument('--samples',type=int,default=16380)
    parser.add_argument('--channel',type=int,default=37,choices=[37,38,39])
    parser.add_argument('--marker-ad-hex',default=MARKER_AD.hex())
    parser.add_argument('--frequency-translation-hz',type=float,default=0)
    parser.add_argument('--refine',action='store_true',help='Blind bounded AA-trained timing/clock/slicer hypotheses, validated by CRC')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh output file')
    files=sorted(args.input.glob('*.bin')) if args.input.is_dir() else [args.input]
    started=time.monotonic()
    result={'schema':1,'decoder':'tools/ble_decode_iq.py','primary_protocol_source':SPEC,
            'independent_published_test_vectors':SAMPLES,'nominal_rate_hz':args.rate,
            'bits_per_component':args.bits,'samples_per_capture':args.samples,'channel':args.channel,
            'owned_marker_ad_hex':args.marker_ad_hex,'captures':[],
            'frequency_translation_hz':args.frequency_translation_hz,
            'blind_receiver_refinement':REFINEMENT if args.refine else None,
            'limitations':'Bounded LE1M legacy advertisement decoder only. No event-emission denominator, calibrated sample clock, guaranteed low-SNR decoding or foreign payload disclosure.'}
    for index,path in enumerate(files):
        payload=path.read_bytes();iq=unpack(payload,args.samples,args.bits)
        frames=decode_iq(iq,args.rate,args.channel,bytes.fromhex(args.marker_ad_hex),args.frequency_translation_hz,args.refine)
        result['captures'].append({'capture_index':index,'capture_filename':path.name,'payload_sha256':hashlib.sha256(payload).hexdigest(),'frames':frames})
    result['captures_analyzed']=len(files)
    result['crc_valid_owned_packets']=sum(f['status']=='valid_owned' for c in result['captures'] for f in c['frames'])
    result['crc_valid_other_packets_redacted']=sum(f['status']=='valid_other_redacted' for c in result['captures'] for f in c['frames'])
    result['runtime_seconds']=time.monotonic()-started
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['captures_analyzed','crc_valid_owned_packets','crc_valid_other_packets_redacted']},indent=2))


if __name__=='__main__':main()

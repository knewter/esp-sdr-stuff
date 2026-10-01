#!/usr/bin/env python3
"""Bounded offline LE1M legacy-advertisement decoder for owned SDR captures.

No hardware access. CRC verifies full packets; only known-marker match metadata
is published. Addresses, names and foreign payloads are not returned.
"""
import argparse
import hashlib
import json
from pathlib import Path
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


def decode_iq(iq,rate,channel,marker_ad=MARKER_AD):
    if rate not in {16000000,40000000,80000000}:
        raise ValueError('unsupported nominal ADC rate')
    # FIR antialias filtering + resampling to4samples/LE1Msymbol.
    # No rate calibration or clock-recovery guarantee is implied.
    down=rate//4000000
    base=resample_poly(iq-iq.mean(),1,down)
    phase=np.angle(base[1:]*np.conj(base[:-1]))
    results=[];seen=[]
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
            results.append({**decoded,'access_address_hamming_errors':errors,
                            'access_address_sample_offset':position,
                            'access_correlation':float(abs(normalized[index])),
                            'estimated_carrier_offset_hz':offset*4000000/(2*np.pi),
                            'iq_polarity':polarity,'timing_phase_at_4msps':timing})
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
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh output file')
    files=sorted(args.input.glob('*.bin')) if args.input.is_dir() else [args.input]
    result={'schema':1,'decoder':'tools/ble_decode_iq.py','primary_protocol_source':SPEC,
            'independent_published_test_vectors':SAMPLES,'nominal_rate_hz':args.rate,
            'bits_per_component':args.bits,'samples_per_capture':args.samples,'channel':args.channel,
            'owned_marker_ad_hex':args.marker_ad_hex,'captures':[],
            'limitations':'Bounded LE1M legacy advertisement decoder only. No event-emission denominator, calibrated sample clock, guaranteed low-SNR decoding or foreign payload disclosure.'}
    for index,path in enumerate(files):
        payload=path.read_bytes();iq=unpack(payload,args.samples,args.bits)
        frames=decode_iq(iq,args.rate,args.channel,bytes.fromhex(args.marker_ad_hex))
        result['captures'].append({'capture_index':index,'payload_sha256':hashlib.sha256(payload).hexdigest(),'frames':frames})
    result['captures_analyzed']=len(files)
    result['crc_valid_owned_packets']=sum(f['status']=='valid_owned' for c in result['captures'] for f in c['frames'])
    result['crc_valid_other_packets_redacted']=sum(f['status']=='valid_other_redacted' for c in result['captures'] for f in c['frames'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['captures_analyzed','crc_valid_owned_packets','crc_valid_other_packets_redacted']},indent=2))


if __name__=='__main__':main()

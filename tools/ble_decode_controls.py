#!/usr/bin/env python3
"""Replay mixed-LO controls captures through the same blind BLE decoder."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

from ble_decode_iq import decode_iq, MARKER_AD, REFINEMENT, SPEC, SAMPLES
from esp_sdr_capture import unpack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures',type=Path,required=True)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rate',type=int,default=16000000)
    parser.add_argument('--bits',type=int,default=10,choices=[8,10])
    parser.add_argument('--samples',type=int,default=16380)
    args=parser.parse_args()
    if args.output.exists():parser.error('Fresh output file required')
    started=time.monotonic()
    result={'schema':1,'kind':'blind BLE controls replay','decoder':'tools/ble_decode_iq.py',
            'primary_protocol_source':SPEC,'independent_published_test_vectors':SAMPLES,
            'nominal_rate_hz':args.rate,'bits_per_component':args.bits,'samples_per_capture':args.samples,
            'channel':37,'owned_marker_ad_hex':MARKER_AD.hex(),'blind_receiver_refinement':REFINEMENT,
            'captures':[],'limitations':'One owned packet per capture/access-start cluster. Digital translation from declared source2402MHz minus requested LO, not calibrated hardware tuning. Source air-event denominator unavailable.'}
    for row in csv.DictReader(args.captures.open()):
        index=int(row['capture_index']);path=args.private/f'iq-{index:04d}.bin';payload=path.read_bytes()
        digest=hashlib.sha256(payload).hexdigest()
        if digest!=row['private_payload_sha256']:raise ValueError('Private capture hash mismatch')
        translation=(int(row['frequency_mhz'])-2402)*1000000
        frames=decode_iq(unpack(payload,args.samples,args.bits),args.rate,37,MARKER_AD,translation,True)
        result['captures'].append({'capture_index':index,'capture_filename':path.name,
                                   'payload_sha256':digest,'frequency_translation_hz':translation,
                                   'condition':{k:row[k] for k in ['frequency_mhz','bandwidth_mhz','gain','phase']},
                                   'frames':frames})
    result['captures_analyzed']=len(result['captures'])
    result['crc_valid_owned_packets']=sum(f['status']=='valid_owned' for c in result['captures'] for f in c['frames'])
    result['crc_valid_other_packets_redacted']=sum(f['status']=='valid_other_redacted' for c in result['captures'] for f in c['frames'])
    result['runtime_seconds']=time.monotonic()-started
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['captures_analyzed','crc_valid_owned_packets','crc_valid_other_packets_redacted','runtime_seconds']},indent=2))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Join redacted decoder/source/capture records and plot an amplitude-only view."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from esp_sdr_capture import unpack


def source_phase(start,end,episodes,guard_ns=1000000000):
    for episode in episodes:
        begin=episode['registration_accepted_monotonic_ns']+guard_ns
        finish=episode['unregister_requested_monotonic_ns']-guard_ns
        if episode.get('release_monotonic_ns') is not None:
            finish=min(finish,episode['release_monotonic_ns']-guard_ns)
        if start>=begin and end<=finish:
            return f'source_on_episode_{episode["index"]}'
    first=episodes[0]['register_requested_monotonic_ns']-guard_ns
    if end<=first:return 'source_off_before'
    for previous,following in zip(episodes,episodes[1:]):
        if start>=previous['unregistration_accepted_monotonic_ns']+guard_ns and end<=following['register_requested_monotonic_ns']-guard_ns:
            return f'source_off_after_episode_{previous["index"]}'
    if start>=episodes[-1]['unregistration_accepted_monotonic_ns']+guard_ns:return 'source_off_after'
    return 'control_transition_guard_excluded'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decoder',type=Path,required=True)
    parser.add_argument('--captures',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    decoded=json.loads(args.decoder.read_text())
    episodes=json.loads(args.source.read_text())['episodes']
    rows=list(csv.DictReader(args.captures.open()))
    by_index={int(row['capture_index']):row for row in rows}
    phases={};owned=[]
    for capture in decoded['captures']:
        row=by_index[capture['capture_index']]
        if row['private_payload_sha256']!=capture['payload_sha256']:
            raise ValueError('Decoder input hash differs from physical capture manifest')
        phase=source_phase(int(row['command_start_ns']),int(row['header_received_ns']),episodes)
        capture['source_control_phase']=phase
        capture['command_start_ns']=int(row['command_start_ns'])
        capture['header_received_ns']=int(row['header_received_ns'])
        counts=phases.setdefault(phase,{'captures':0,'captures_with_access_address_candidates':0,'crc_valid_owned_packets':0})
        counts['captures']+=1
        if capture['frames']:counts['captures_with_access_address_candidates']+=1
        for frame in capture['frames']:
            if frame['status']=='valid_owned':
                counts['crc_valid_owned_packets']+=1
                owned.append((capture,frame))
    decoded['decoder_source_sha256']=hashlib.sha256(Path(__file__).with_name('ble_decode_iq.py').read_bytes()).hexdigest()
    decoded['physical_capture_csv_sha256']=hashlib.sha256(args.captures.read_bytes()).hexdigest()
    decoded['source_schedule_sha256']=hashlib.sha256(args.source.read_bytes()).hexdigest()
    decoded['source_control_phases']=phases
    decoded['phase_classification_guard_seconds']=1
    decoded['exact_over_air_emission_count']=None
    decoded['packet_counting_note']='One packet per capture/access-start cluster; receiver timing/slicing hypotheses are not emissions. Source phase is control-plane schedule with1s guards, not an independent RF timing reference.'
    (args.output/'decoder-manifest.json').write_text(json.dumps(decoded,indent=2)+'\n')
    if owned:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        capture,frame=owned[0]
        payload=(args.private/capture['capture_filename']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=capture['payload_sha256']:
            raise ValueError('Waveform differs from decoder input')
        iq=unpack(payload,decoded['samples_per_capture'],decoded['bits_per_component'])
        power=np.abs(iq-iq.mean())**2
        smooth=np.convolve(power,np.ones(256)/256,'same')
        x=np.arange(len(iq))/decoded['nominal_rate_hz']*1e6
        fig,axis=plt.subplots(figsize=(11,3.7),layout='constrained')
        axis.plot(x[::64],smooth[::64],color='#137d65',linewidth=1.4)
        axis.axvspan(frame['nominal_packet_start_sample']/decoded['nominal_rate_hz']*1e6,
                     frame['nominal_packet_end_sample']/decoded['nominal_rate_hz']*1e6,
                     color='#83d9ba',alpha=.3,label='Complete CRC-valid owned packet window')
        axis.set(xlabel='Time in snapshot (microseconds; nominal sample rate)',
                 ylabel='Mean AC power (ADC code²;16us smoothing)',xlim=(0,x[-1]),
                 title=f'Actual owned BLE reception · capture {capture["capture_index"]} · amplitude only')
        axis.legend(fontsize=8);axis.grid(alpha=.18)
        fig.savefig(args.output/'owned-envelope.svg');plt.close(fig)
    print(json.dumps({'phases':phases,'crc_valid_owned_packets':len(owned)},indent=2))


if __name__=='__main__':main()

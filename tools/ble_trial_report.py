#!/usr/bin/env python3
"""Join redacted decoder/source/capture records and plot an amplitude-only view."""
import argparse
import csv
import hashlib
import json
import math
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


def capture_phase(row, episodes):
    if row.get('payload_received_ns') in (None, ''):
        return 'capture_payload_timing_unknown_excluded'
    start = int(row['command_start_ns'])
    header = int(row['header_received_ns'])
    end = int(row['payload_received_ns'])
    if not start <= header <= end:
        raise ValueError('Invalid full capture bracket')
    return source_phase(start, end, episodes)


def complete_owned_packets(frames, samples, rate):
    """Require retained waveform bounds; a status label alone is insufficient.

    This does not reslice samples, repair bits or expand receiver hypotheses.
    Coarse CRC-valid candidates without independent preamble/window metadata
    remain excluded. Multiple hypotheses in one AA cluster count once.
    """
    accepted=[]; excluded=[]
    def finite(value):
        return type(value) in (int,float) and math.isfinite(value)
    def priority(frame):
        value=frame.get('access_correlation')
        return -value if finite(value) else 0
    def protected_owned(frame):
        digest=frame.get('pdu_sha256','')
        return (frame.get('status')=='valid_owned' and frame.get('crc24_ok') is True and
                frame.get('owned_manufacturer_ad_exact_match') is True and
                isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest))
    for frame in sorted(frames,key=priority):
        if frame.get('status')!='valid_owned':continue
        reasons=[]
        if frame.get('crc24_ok') is not True:reasons.append('protected_crc24_unverified')
        if frame.get('owned_manufacturer_ad_exact_match') is not True:reasons.append('whole_owned_ad_unverified')
        digest=frame.get('pdu_sha256','')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            reasons.append('protected_pdu_hash_unverified')
        if (type(frame.get('pdu_type')) is not int or frame['pdu_type'] not in (0,2,4,6) or
                type(frame.get('access_address_hamming_errors')) is not int or
                not 0<=frame['access_address_hamming_errors']<=2 or
                type(frame.get('preamble_hamming_errors')) is not int or
                not 0<=frame['preamble_hamming_errors']<=8):
            reasons.append('packet_type_or_aa_preamble_diagnostics_unverified')
        start=frame.get('nominal_packet_start_sample');end=frame.get('nominal_packet_end_sample')
        offset=frame.get('access_address_sample_offset');period=frame.get('samples_per_symbol_at_4msps')
        if frame.get('complete_preamble_and_pdu_crc_within_capture_nominal') is not True or not (
                finite(start) and finite(end) and 0<=start<end<=samples):
            reasons.append('complete_nominal_packet_window_unverified')
        duration=frame.get('packet_duration_us');length=frame.get('pdu_length')
        if not (finite(period) and 3.97<=period<=4.03 and finite(offset) and
                finite(duration) and type(length) is int and 6<=length<=37 and
                duration==8+32+16+8*length+24 and finite(start) and finite(end)):
            reasons.append('packet_window_receiver_metadata_unverified')
        elif not (math.isclose(start,offset-8*period*(rate/4000000),abs_tol=1e-6) and
                  math.isclose(end-start,duration*period*(rate/4000000),abs_tol=1e-6)):
            reasons.append('packet_window_inconsistent_with_receiver_period')
        if protected_owned(frame) and finite(offset) and any(
                protected_owned(other) and finite(other.get('access_address_sample_offset')) and
                abs(offset-other['access_address_sample_offset'])<=rate/1000000*4 and
                digest!=other['pdu_sha256'] for other in frames):
            reasons.append('conflicting_protected_pdu_hashes_in_access_address_cluster')
        if not reasons and any(abs(offset-other['access_address_sample_offset'])<=rate/1000000*4 for other in accepted):
            reasons.append('duplicate_access_address_receiver_hypothesis')
        if reasons:excluded.append({'frame':frame,'exclusion_reasons':reasons})
        else:accepted.append(frame)
    return accepted,excluded


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
    phases={};owned=[];excluded=[]
    for capture in decoded['captures']:
        row=by_index[capture['capture_index']]
        if row['private_payload_sha256']!=capture['payload_sha256']:
            raise ValueError('Decoder input hash differs from physical capture manifest')
        phase=capture_phase(row, episodes)
        capture['source_control_phase']=phase
        capture['command_start_ns']=int(row['command_start_ns'])
        capture['header_received_ns']=int(row['header_received_ns'])
        capture['payload_received_ns']=(int(row['payload_received_ns'])
                                        if row.get('payload_received_ns') not in (None, '') else None)
        counts=phases.setdefault(phase,{'captures':0,'captures_with_access_address_candidates':0,'crc_valid_owned_packets':0})
        counts['captures']+=1
        if capture['frames']:counts['captures_with_access_address_candidates']+=1
        accepted,rejected=complete_owned_packets(capture['frames'],decoded['samples_per_capture'],decoded['nominal_rate_hz'])
        counts['crc_valid_owned_packets']+=len(accepted)
        owned.extend((capture,frame) for frame in accepted)
        excluded.extend({'capture_index':capture['capture_index'],'source_control_phase':phase,
                         'waveform_sha256':capture['payload_sha256'],**record} for record in rejected)
    decoded['decoder_source_sha256']=hashlib.sha256(Path(__file__).with_name('ble_decode_iq.py').read_bytes()).hexdigest()
    decoded['physical_capture_csv_sha256']=hashlib.sha256(args.captures.read_bytes()).hexdigest()
    decoded['source_schedule_sha256']=hashlib.sha256(args.source.read_bytes()).hexdigest()
    decoded['source_control_phases']=phases
    decoded['phase_classification_guard_seconds']=1
    decoded['phase_classification_capture_bracket']='command_start_ns through payload_received_ns'
    decoded['exact_over_air_emission_count']=None
    decoded['decoder_valid_owned_candidates']=decoded.get('crc_valid_owned_packets')
    decoded['crc_valid_owned_packets']=len(owned)
    decoded['excluded_crc_valid_owned_candidates']=excluded
    decoded['reporter_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    decoded['packet_counting_note']='Only complete nominal preamble-through-protected-CRC windows with exact owned AD and retained PDU hash are counted, once per capture/access-start cluster. Excluded candidates remain waveform-unverified or duplicate hypotheses. Source phase uses whole-response control-plane brackets with1s guards, not an independent RF timing reference or emission denominator.'
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

#!/usr/bin/env python3
"""Offline numeric audit of preserved IQ; no hardware, alternate decode or payload export."""
import argparse,csv,hashlib,json,math,sys,time,zlib
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly

DECODER_SHA='834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128'
RATE=16000000;SAMPLES=16380
sha=lambda data:hashlib.sha256(data).hexdigest()

def independent_unpack(data,bits):
    assert len(data)==SAMPLES*2*bits//8
    if bits==8:
        components=np.frombuffer(data,dtype=np.int8).astype(np.float64)
    else:
        b=np.frombuffer(data,dtype=np.uint8).reshape(-1,5).astype(np.uint64)
        word=sum(b[:,i]<<(8*i) for i in range(5))
        components=np.column_stack([(word>>shift)&1023 for shift in (0,10,20,30)]).reshape(-1).astype(np.int64)
        components=np.where(components>=512,components-1024,components).astype(np.float64)
    return components[::2]+1j*components[1::2]

def quantiles(values):
    return {k:float(v) for k,v in zip(('min','q10','median','q90','q99','max'),np.quantile(values,[0,.1,.5,.9,.99,1]))}

METRICS=('ac_codes2','ac_fullscale2','dc_power_fraction','endpoint_fraction','unique_i','unique_q',
         'iq_correlation','decoder_minus1MHz_coherent_fraction','decoder_minus1MHz_coherent_codes2',
         'decoder_ac_codes2','channel_plus1MHz_fraction','historical_carrier_plus1_5_to2_5MHz_fraction',
         'block32_power_q90_over_median','adjacent_sample_correlation_abs','capture_roundtrip_ms')

def measure(iq,bits):
    full=2**(bits-1);mean=iq.mean();ac=iq-mean;acpower=float(np.mean(np.abs(ac)**2));rawpower=float(np.mean(np.abs(iq)**2))
    psd=np.abs(np.fft.fft(ac*np.hanning(len(iq))))**2
    freq=np.fft.fftfreq(len(iq),1/RATE);power=float(psd.sum())
    # Exactly the existing decoder's translation, mean-removal order and resampling.
    mixed=iq*np.exp(-2j*np.pi*1000000*np.arange(len(iq))/RATE)
    base=resample_poly(mixed-mixed.mean(),1,4)
    trimmed=base[64:-64];coordinate=np.arange(64,len(base)-64)
    tone=np.mean(trimmed*np.exp(2j*np.pi*1000000*coordinate/4000000))
    basepower=float(np.mean(np.abs(trimmed)**2));block=np.abs(ac[:len(ac)//32*32].reshape(-1,32))**2
    blockmeans=block.mean(axis=1);median=float(np.median(blockmeans))
    centeredcomponents=np.column_stack([ac.real,ac.imag]);corr=float(np.corrcoef(centeredcomponents.T)[0,1])
    result={'ac_codes2':acpower,'ac_fullscale2':acpower/full**2,'dc_power_fraction':abs(mean)**2/rawpower,
            'endpoint_fraction':float(np.mean((np.column_stack([iq.real,iq.imag])==-full)|(np.column_stack([iq.real,iq.imag])==full-1))),
            'unique_i':len(np.unique(iq.real)),'unique_q':len(np.unique(iq.imag)),'iq_correlation':corr,
            'decoder_minus1MHz_coherent_fraction':float(abs(tone)**2/basepower),
            'decoder_minus1MHz_coherent_codes2':float(abs(tone)**2),'decoder_ac_codes2':basepower,
            'channel_plus1MHz_fraction':float(psd[(freq>.5e6)&(freq<1.5e6)].sum()/power),
            'historical_carrier_plus1_5_to2_5MHz_fraction':float(psd[(freq>1.5e6)&(freq<2.5e6)].sum()/power),
            'block32_power_q90_over_median':float(np.quantile(blockmeans,.9)/median),
            'adjacent_sample_correlation_abs':float(abs(np.mean(ac[1:]*np.conj(ac[:-1])))/acpower),
            'mean_i':float(mean.real),'mean_q':float(mean.imag)}
    # Coarse 0.25MHz bins, scalar power only; no complex/bit/address exports.
    edges=np.linspace(-8e6,8e6,65)
    coarse=np.array([psd[(freq>=a)&(freq<b)].sum()/power for a,b in zip(edges,edges[1:])])
    return result,coarse

def main():
    cli=argparse.ArgumentParser();cli.add_argument('--root',type=Path,required=True);cli.add_argument('--output',type=Path,required=True);cli.add_argument('--private-output',type=Path,required=True)
    args=cli.parse_args();root=args.root.resolve();out=args.output.resolve();private=args.private_output.resolve()
    assert not out.exists() and not private.exists(),'fresh output paths required'
    assert private.is_relative_to(root/'.scratch') or private.is_relative_to(Path(__file__).resolve().parents[3]/'.scratch')
    out.mkdir(parents=True);private.mkdir(parents=True,mode=0o700)
    sys.path.insert(0,str(root/'tools'));import ble_decode_iq as decoder
    assert sha((root/'tools/ble_decode_iq.py').read_bytes())==DECODER_SHA
    started=time.monotonic();groups={};records=[];packetrows=[];input_hashes={};decode_totals={};verification={};raw_digest=hashlib.sha256()
    historical={}
    for evidence in ('ble-owned-decoding','ble-controls-decoding'):
        path=root/'docs/evidence'/evidence/'decoder-manifest.json';manifest=json.loads(path.read_text());input_hashes[str(path.relative_to(root))]=sha(path.read_bytes());historical[evidence]=manifest
    specifications=[('historical8','ble-reception-trial','.scratch/ble-reception-trial-raw',8,None,historical['ble-owned-decoding']),
                    ('historical10_matched','rf-controls-trial','.scratch/rf-controls-trial-raw',10,lambda r:r['frequency_mhz']=='2401' and r['bandwidth_mhz']=='20' and r['gain']=='48',historical['ble-controls-decoding']),
                    ('freshA','ble-bluez-control-001','.scratch/ble-bluez-control-001/iq',8,None,None),
                    ('freshC','ble-bluez-control-002','.scratch/ble-bluez-control-002/iq',10,None,None)]
    for name,evidence,rawdir,bits,select,oldmanifest in specifications:
        csvpath=root/'docs/evidence'/evidence/'captures.csv';rows=list(csv.DictReader(csvpath.open()));input_hashes[str(csvpath.relative_to(root))]=sha(csvpath.read_bytes())
        if oldmanifest:
            phases={c['capture_index']:c['source_control_phase'] for c in oldmanifest['captures']}
            oldby={c['capture_index']:c for c in oldmanifest['captures']}
        else:
            phasepath=root/'docs/evidence'/evidence/'phase-classification.csv';phases={int(r['capture_index']):r['source_control_phase'] for r in csv.DictReader(phasepath.open())};input_hashes[str(phasepath.relative_to(root))]=sha(phasepath.read_bytes());oldby={}
        decodedowned=decodedforeign=checked=totalbytes=0;first=None;last=None
        for row in rows:
            if select and not select(row):continue
            index=int(row['capture_index']);payload=(root/rawdir/f'iq-{index:04d}.bin').read_bytes();digest=sha(payload)
            assert digest==row['private_payload_sha256'];assert f'{zlib.crc32(payload)&0xffffffff:08x}'==row['expected_crc32']==row['actual_crc32'];assert row['crc_ok']==row['sample_count_ok']=='True' and int(row['returned_samples'])==SAMPLES
            iq=independent_unpack(payload,bits);assert np.array_equal(iq,decoder.unpack(payload,SAMPLES,bits))
            vals,spectrum=measure(iq,bits);vals['capture_roundtrip_ms']=float(row['round_trip_ms'])
            for key,csvkey in [('ac_codes2','ac_power_codes_squared'),('endpoint_fraction','component_endpoint_fraction'),('mean_i','mean_i'),('mean_q','mean_q'),('unique_i','unique_i_codes'),('unique_q','unique_q_codes')]:assert math.isclose(vals[key],float(row[csvkey]),rel_tol=1e-10,abs_tol=1e-10),(name,index,key)
            frames=decoder.decode_iq(iq,RATE,37,frequency_translation_hz=-1000000,refine=True)
            owned=[f for f in frames if f['status']=='valid_owned'];foreign=[f for f in frames if f['status']=='valid_other_redacted'];decodedowned+=len(owned);decodedforeign+=len(foreign)
            if oldmanifest:
                reference=[f for f in oldby[index]['frames'] if f['status']=='valid_owned'];assert owned==reference
            else:assert not owned and not foreign
            phase=phases[index];category='ON' if phase.startswith('source_on') else 'EXCLUDED' if 'excluded' in phase else 'OFF'
            item={'dataset':name,'capture_index':index,'bits':bits,'phase_category':category,'snapshot_crc24_owned':len(owned),**vals};records.append(item)
            memberships=[name+'_all',name+'_'+category]
            if owned:memberships.append(name+'_positive_whole')
            for member in memberships:groups.setdefault(member,[]).append((item,spectrum))
            for frame in owned:
                assert frame['crc24_ok'] is True and frame['owned_manufacturer_ad_exact_match'] is True and frame['complete_preamble_and_pdu_crc_within_capture_nominal'] is True
                begin=math.floor(frame['nominal_packet_start_sample']);end=math.ceil(frame['nominal_packet_end_sample']);packet,ps=measure(iq[begin:end],bits)
                packetrows.append({'dataset':name,'capture_index':index,'payload_sha256':digest,'packet_start_sample':frame['nominal_packet_start_sample'],'packet_end_sample':frame['nominal_packet_end_sample'],'fixed_decoder_carrier_after_minus1MHz_hz':frame['estimated_carrier_offset_hz'],'fixed_decoder_pdu_sha256':frame['pdu_sha256'],'packet_metrics':packet,'whole_snapshot_metrics':vals})
            checked+=1;totalbytes+=len(payload);raw_digest.update(name.encode()+index.to_bytes(4,'little')+bytes.fromhex(digest));first=int(row['command_start_ns']) if first is None else min(first,int(row['command_start_ns']));last=int(row['payload_received_ns']) if last is None else max(last,int(row['payload_received_ns']))
        assert checked=={'historical8':549,'historical10_matched':12,'freshA':1251,'freshC':997}[name]
        decode_totals[name]={'captures':checked,'crc24_owned':decodedowned,'crc24_foreign_redacted':decodedforeign}
        verification[name]={'captures':checked,'payload_bytes':totalbytes,'all_crc32_sha256_lengths_counts_and_independent_unpack_valid':True,'public_numerical_stats_reproduced':True,'nominal_sampled_seconds':checked*SAMPLES/RATE,'first_command_to_last_payload_seconds':(last-first)/1e9,'nominal_sampled_fraction_of_that_host_interval':checked*SAMPLES/RATE/((last-first)/1e9),'snapshot_seconds':SAMPLES/RATE}
    assert sum(t['crc24_owned'] for t in decode_totals.values())==5
    summarygroups={};spectra={}
    for name,items in groups.items():
        summarygroups[name]={'captures':len(items),'metrics':{key:quantiles([row[key] for row,_ in items]) for key in METRICS}}
        spectra[name]=np.median(np.stack([s for _,s in items]),axis=0).tolist()
    result={'schema':1,'kind':'offline preserved-waveform numeric comparison; not RF acceptance','reviewed_root_commit':'9d1b553db8327c0bab6da0e2f745d08495ba7f85','analysis_source_sha256':sha(Path(__file__).read_bytes()),'decoder_source_sha256':DECODER_SHA,'fixed_decoder_parameters':{'rate':RATE,'samples':SAMPLES,'channel':37,'translation_hz':-1000000,'refine':True,'search_bounds':decoder.REFINEMENT},'input_public_file_hashes':input_hashes,'ordered_dataset_index_payload_digest_sha256':raw_digest.hexdigest(),'verification':verification,'fixed_decoder_replay':decode_totals,'groups':summarygroups,'five_positive_packet_windows':packetrows,'coarse_PSD':{'bin_width_MHz':.25,'centers_MHz':np.linspace(-7.875,7.875,64).tolist(),'median_individual_snapshot_AC_power_fraction_per_bin':spectra},'runtime_seconds':time.monotonic()-started,'hardware_or_Docker_access':False,'waveform_bytes_published':False,'RF_acceptance_gates_closed':False,'SDR_repeatability_proven':False,'transmitted_event_denominator':None,'limits':['Retrospective unmatched physical sessions; placement/interference/source RF cadence and effective gain unmeasured.','Historical positive selection is conditioned on decoding; matched12cell and full549 background groups retained.','Code power/fullscale normalization is not dBm, calibrated SNR/sensitivity/range or gain-dB readback.','Scalar spectral/tone energy is not attributed to owned or foreign RF packets.','Snapshot coverage is sparse nominal sampled time divided by host interval, not RF event capture probability.','Original decoder preprocessing order and bounded search remain unchanged; no alternate decoder acceptance.']}
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    with (private/'per-capture-numerical.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    plot(result,out/'comparison.svg')
    print(json.dumps({'fixed_decoder_replay':decode_totals,'verification':verification,'output_numeric_files':2,'runtime_seconds':result['runtime_seconds']},indent=2))

def plot(result,path):
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    names=['historical8_all','freshA_all','historical10_matched_all','freshC_all'];labels=['Historical 8-bit: all549','Fresh A8: all1251','Historical 10-bit same settings:12','Fresh C10: all997'];colors=['#598ca4','#dd885b','#488060','#8266aa']
    fig,axes=plt.subplots(1,3,figsize=(13,4.3),layout='constrained')
    for name,label,color in zip(names,labels,colors):
        metrics=result['groups'][name]['metrics'];q=np.array([.1,.5,.9,.99]);x=[metrics['ac_fullscale2'][key] for key in ['q10','median','q90','q99']];axes[0].plot(x,q,'o-',label=label,color=color)
        x=[metrics['dc_power_fraction'][key] for key in ['q10','median','q90','q99']];axes[1].plot(x,q,'o-',color=color)
        axes[2].plot(result['coarse_PSD']['centers_MHz'],result['coarse_PSD']['median_individual_snapshot_AC_power_fraction_per_bin'][name],color=color)
    axes[0].set(xscale='log',xlabel='AC code power / signed full-scale²',ylabel='Observed quantile',title='Snapshot AC distribution');axes[0].legend(fontsize=7,loc='upper left')
    axes[1].set(xlabel='Raw DC power / total code power',title='DC fraction',xlim=(0,1))
    axes[2].set(xlabel='Nominal frequency relative to requested LO (MHz)',ylabel='AC power fraction per 0.25MHz bin',title='Median snapshot spectrum',yscale='log',ylim=(1e-5,1))
    fig.suptitle('Preserved ESP SDR snapshots: numeric differences, no calibrated RF or causal claim',fontsize=11)
    fig.text(.5,.01,'Exact fixed decoder: 5 historical owned CRC24 positives; 2248 fresh nulls · scalar derived power only · mismatched sessions, sparse windows',ha='center',fontsize=8)
    fig.get_layout_engine().set(rect=(0,.08,1,.92));fig.savefig(path,metadata={'Date':None})

if __name__=='__main__':main()

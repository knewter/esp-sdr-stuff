#!/usr/bin/env python3
"""Scalar saved-IQ audit; no hardware, decoding or payload/address export."""
import argparse,csv,hashlib,json,zlib
from pathlib import Path
import numpy as np
N=16380
sha=lambda b:hashlib.sha256(b).hexdigest()
def phase(a,b,eps):
 for e in eps:
  if a>=e['registration_accepted_monotonic_ns']+10**9 and b<=e['unregister_requested_monotonic_ns']-10**9:return 'ON'+str(e['index'])
 if b<=eps[0]['register_requested_monotonic_ns']-10**9:return 'OFF0'
 for e,f in zip(eps,eps[1:]):
  if a>=e['unregistration_accepted_monotonic_ns']+10**9 and b<=f['register_requested_monotonic_ns']-10**9:return 'OFF'+str(e['index']+1)
 if a>=eps[-1]['unregistration_accepted_monotonic_ns']+10**9:return 'OFF3'
 return 'TRANSITION'
def unpack(raw,bits):
 if bits==8:c=np.frombuffer(raw,dtype=np.int8).astype(float)
 else:
  b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,5).astype(np.uint64);w=sum(b[:,i]<<(8*i) for i in range(5));c=np.column_stack([(w>>s)&1023 for s in (0,10,20,30)]).reshape(-1).astype(np.int64);c=np.where(c>=512,c-1024,c)
 return c[::2]+1j*c[1::2]
def measure(x,bits):
 ac=x-x.mean();p=float(np.mean(abs(ac)**2));w=np.hanning(N);s=abs(np.fft.fft(ac*w))**2;f=np.fft.fftfreq(N,1/16000000);band=float(s[(f>1.5e6)&(f<2.5e6)].sum()/(N*np.sum(w*w)));blocks=np.mean(abs(ac[:N//32*32].reshape(-1,32))**2,axis=1)
 return [p,band,float(np.mean((x.real==-2**(bits-1))|(x.real==2**(bits-1)-1))+np.mean((x.imag==-2**(bits-1))|(x.imag==2**(bits-1)-1)))/2,float(np.quantile(blocks,.9)/np.median(blocks))]
def stat(rows):
 a=np.array([r['m'] for r in rows]);return [len(rows),*[[round(float(v),6) for v in np.quantile(a[:,i],[.5,.9])] for i in range(4)]]
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();root=args.root.resolve();assert not args.output.exists();result={'schema':1,'kind':'offline scalar ON/OFF audit; no owned-RF attribution','metrics_order':['AC_code2','Hann_band_1_5_to_2_5MHz_code2','component_endpoint_fraction','block32_q90_over_median'],'summary_order':['count','AC_median_q90','band_median_q90','endpoint_median_q90','block_median_q90'],'datasets':{},'inputs':{},'decoder_changed':False,'emission_denominator':None};dig=hashlib.sha256()
 for name,bits in [('001',8),('002',10)]:
  public=root/'docs/evidence'/('ble-bluez-control-'+name);paths=[public/x for x in ('captures.csv','phase-classification.csv','source.json')];result['inputs'].update({name+'/'+x.name:sha(x.read_bytes()) for x in paths});source=json.loads(paths[2].read_text());eps=source['episodes'];assert source['status']=='completed' and len(eps)==3 and all(not e['release_observed_before_unregister'] for e in eps);labels={int(r['capture_index']):r['source_control_phase'] for r in csv.DictReader(paths[1].open())};rows=[]
  for r in csv.DictReader(paths[0].open()):
   i=int(r['capture_index']);raw=(root/'.scratch'/('ble-bluez-control-'+name)/'iq'/f'iq-{i:04d}.bin').read_bytes();assert len(raw)==N*2*bits//8 and sha(raw)==r['private_payload_sha256'] and f'{zlib.crc32(raw)&0xffffffff:08x}'==r['actual_crc32']==r['expected_crc32'];assert int(r['returned_samples'])==N and r['crc_ok']==r['sample_count_ok']=='True';a,b=int(r['command_start_ns']),int(r['payload_received_ns']);assert a<int(r['header_received_ns'])<b;ph=phase(a,b,eps);expected=('source_on_episode_'+ph[-1] if ph.startswith('ON') else 'control_transition_guard_excluded' if ph=='TRANSITION' else 'source_off_before' if ph=='OFF0' else 'source_off_after' if ph=='OFF3' else 'source_off_after_episode_'+str(int(ph[-1])-1));assert labels[i]==expected;m=measure(unpack(raw,bits),bits);assert np.all(np.isfinite(m)) and np.isclose(m[0],float(r['ac_power_codes_squared']),rtol=1e-10,atol=1e-10) and np.isclose(m[2],float(r['component_endpoint_fraction']),rtol=1e-10,atol=1e-10);dig.update(name.encode()+i.to_bytes(4,'little')+bytes.fromhex(sha(raw)));rows.append(dict(a=a,b=b,p=ph,m=m))
  summaries={k:stat([r for r in rows if r['p']==k]) for k in ['OFF0','ON0','OFF1','ON1','OFF2','ON2','OFF3','TRANSITION']};edges=[]
  for e in eps:
   for typ,t in [('enable',e['register_requested_monotonic_ns']),('disable',e['unregister_requested_monotonic_ns'])]:
    pre=('OFF'+str(e['index'])) if typ=='enable' else 'ON'+str(e['index']);post='ON'+str(e['index']) if typ=='enable' else 'OFF'+str(e['index']+1);before=[r for r in rows if r['p']==pre and r['a']>=t-11*10**9 and r['b']<=t-10**9];after=[r for r in rows if r['p']==post and r['a']>=t+10**9 and r['b']<=t+11*10**9];edges.append([e['index'],typ,len(before),len(after),*[round(float(np.median([r['m'][i] for r in after])/np.median([r['m'][i] for r in before])),6) for i in (0,1)]])
  result['datasets'][name]={'bits':bits,'count':len(rows),'phases':summaries,'local_edges_order':['episode','edge','before_count','after_count','AC_after_before','band_after_before'],'local_edges':edges}
 assert result['datasets']['001']['count']==1251 and result['datasets']['002']['count']==997;result['ordered_payload_digest']=dig.hexdigest();args.output.write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

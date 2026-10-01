#!/usr/bin/env python3
"""Plot measured control-sweep clipping and anonymous amplitude spectra."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from esp_sdr_capture import unpack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    parser.add_argument('private',type=Path)
    args=parser.parse_args()
    rows=list(csv.DictReader((args.evidence/'captures.csv').open()))
    manifest=json.loads((args.evidence/'manifest.json').read_text())
    assert manifest['bits_per_component']==10 and manifest['nominal_rate_hz']==16000000
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    plt.rcParams.update({'svg.fonttype':'none'})
    gains=('hardware','24','48','72');filters=(12,20,40,67);grid=np.empty((4,4));summary=[]
    for fi,bandwidth in enumerate(filters):
        for gi,gain in enumerate(gains):
            selected=[r for r in rows if r['phase']=='source_registered_control_sweep' and
                      int(r['bandwidth_mhz'])==bandwidth and r['gain']==gain]
            spectra=[]
            for row in selected:
                payload=(args.private/f"iq-{int(row['capture_index']):04d}.bin").read_bytes()
                assert hashlib.sha256(payload).hexdigest()==row['private_payload_sha256']
                iq=unpack(payload,16380,10);iq=iq-iq.mean();window=np.hanning(len(iq))
                psd=np.abs(np.fft.fftshift(np.fft.fft(iq*window)))**2/np.sum(window**2)
                spectra.append(psd)
            endpoints=np.array([float(r['component_endpoint_fraction']) for r in selected])
            grid[fi,gi]=endpoints.mean()*100
            summary.append({'bandwidth_setting_mhz':bandwidth,'gain_setting':gain,'captures':len(selected),
                            'mean_component_endpoint_percent':float(grid[fi,gi]),
                            'maximum_component_endpoint_percent':float(endpoints.max()*100),
                            'median_ac_power_codes_squared':float(np.median([float(r['ac_power_codes_squared']) for r in selected]))})
            if gain=='hardware':
                frequencies=np.fft.fftshift(np.fft.fftfreq(16380,1/16000000))/1e6
                median=np.median(spectra,axis=0)
                # Average adjacent power bins only for a readable amplitude plot.
                n=16;trim=len(median)//n*n
                axes[0].plot(frequencies[:trim].reshape(-1,n).mean(axis=1),
                             10*np.log10(median[:trim].reshape(-1,n).mean(axis=1)+1e-20),label=f'{bandwidth} MHz setting',linewidth=1)
    axes[0].set(xlabel='Offset from requested 2401 MHz LO (MHz)',
                ylabel='Median FFT power (dB re ADC code²/bin)',title='Hardware AGC · mixed ambient + owned BLE')
    axes[0].legend(fontsize=8);axes[0].grid(alpha=.15)
    heat=axes[1].imshow(grid,aspect='auto',cmap='YlOrRd',vmin=0)
    axes[1].set_xticks(range(4),gains);axes[1].set_yticks(range(4),[str(f) for f in filters])
    axes[1].set(xlabel='Gain setting/code',ylabel='Filter setting (MHz)',title='Mean sample-component endpoints (%)')
    for fi in range(4):
        for gi in range(4):axes[1].text(gi,fi,f'{grid[fi,gi]:.3f}',ha='center',va='center',fontsize=9)
    fig.colorbar(heat,ax=axes[1],label='Endpoint percentage')
    fig.suptitle('Actual 10-bit snapshots · 12 captures per control condition')
    fig.savefig(args.evidence/'controls.svg',metadata={'Date':None})
    (args.evidence/'summary.json').write_text(json.dumps({'conditions':summary,
        'limitations':'Nominal rate/requested LO. Intermittent owned source plus uncontrolled ambient RF. Median spectra do not isolate owned packets or characterize calibrated filter transfer; endpoint values suggest code clipping, not absolute analog overload.'},indent=2)+'\n')


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Sweep advertised receive controls while a separate owned source runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time
from esp_sdr_capture import STABLE_PORT,open_board,synchronize,queries,settings,capture,numerical_stats,command


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--source-state',type=Path,required=True)
    args=parser.parse_args()
    private=args.private.resolve()
    if not any(p in {'.scratch','backups'} for p in private.parts) or any(p in {'docs','site'} for p in private.parts):
        parser.error('private IQ requires ignored scratch/backup directory outside publication')
    args.output.mkdir(parents=True,exist_ok=False)
    private.mkdir(parents=True,exist_ok=False,mode=0o700)
    record={'firmware_variant':'550fade-uart921600','baud':921600,'nominal_rate_hz':16000000,
            'bits_per_component':10,'samples_per_capture':16380,'source_frequency_mhz':2402,
            'kind':'physical control sweep with separately registered BLE source',
            'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'limitations':'Uncalibrated gain/filter settings. A command acceptance does not establish passband, sensitivity or PLL lock; known-source packet attribution requires separate CRC/owned-marker decoding. No independently counted RF events.'}
    rows=[]
    port=open_board(STABLE_PORT,baud=921600)
    def collect(phase,frequency,bandwidth,gain,count):
        settings(port,frequency,bandwidth,gain)
        for _ in range(count):
            payload,measured=capture(port,16380,16000000,10)
            index=len(rows)
            row={'capture_index':index,'phase':phase,'frequency_mhz':frequency,'bandwidth_mhz':bandwidth,
                 'gain':gain,**measured,'private_payload_sha256':hashlib.sha256(payload).hexdigest()}
            path=private/f'iq-{index:04d}.bin';path.write_bytes(payload);path.chmod(0o600)
            if measured['crc_ok'] and measured['sample_count_ok']:
                row.update(numerical_stats(payload,16380,10))
            rows.append(row)
        print(f'phase={phase} center={frequency} filter={bandwidth} gain={gain} captures={count}',flush=True)
    try:
        synchronize(port);record['queries']=queries(port)
        collect('source_off_before',2401,12,'hardware',30)
        print('BASELINE_DONE_WAITING_SOURCE',flush=True)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if args.source_state.exists():
                source=json.loads(args.source_state.read_text())
                if source.get('episodes') and 'registration_accepted_monotonic_ns' in source['episodes'][0]:
                    record['source_registration_accepted_monotonic_ns']=source['episodes'][0]['registration_accepted_monotonic_ns'];break
            time.sleep(.2)
        else:raise TimeoutError('Separate source did not register within60seconds')
        time.sleep(2)
        for bandwidth in (12,20,40,67):
            for gain in ('hardware','24','48','72'):
                collect('source_registered_control_sweep',2401,bandwidth,gain,12)
        collect('source_registered_LO_check',2402,12,'hardware',24)
        record['completed']=True
    finally:
        try:command(port,'RELEASE')
        except Exception:pass
        port.close()
        record['ended_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        record['captures']=len(rows);record['integrity_failures']=sum(not(r['crc_ok'] and r['sample_count_ok']) for r in rows)
        (args.output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
        with (args.output/'captures.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=sorted({k for r in rows for k in r}));writer.writeheader();writer.writerows(rows)


if __name__=='__main__':main()

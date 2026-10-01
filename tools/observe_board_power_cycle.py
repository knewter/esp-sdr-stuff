#!/usr/bin/env python3
"""Observe a user-performed USB disconnect/reconnect; capture restored boot."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import time
from esp_sdr_capture import STABLE_PORT,open_board


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--wait-seconds',type=int,default=600)
    args=parser.parse_args()
    if not 1<=args.wait_seconds<=1800:parser.error('bounded wait1..1800seconds required')
    stable=Path(STABLE_PORT)
    if not stable.exists():raise SystemExit('Selected restored board must be connected before observation starts')
    args.output.mkdir(parents=True,exist_ok=False)
    record={'started_utc':datetime.now(timezone.utc).isoformat(),
            'user_confirmed_actual_power_removal':False,'power_cycle_proven':False,
            'port_handle_closed_during_wait':True,
            'limitations':'USB disappearance/reappearance alone does not prove physical power removal. User confirmation is required. Opening UART may cause an additional reset.'}
    def save(): (args.output/'observation.json').write_text(json.dumps(record,indent=2)+'\n')
    save();print('READY_FOR_USER_USB_UNPLUG no serial handle open',flush=True)
    deadline=time.monotonic()+args.wait_seconds
    while stable.exists() and time.monotonic()<deadline:time.sleep(.05)
    if stable.exists():
        record['status']='no_disconnect_observed_before_timeout';save();return
    record['USB_disconnect_utc']=datetime.now(timezone.utc).isoformat()
    record['USB_disconnect_monotonic_ns']=time.monotonic_ns();save()
    print('SelectedUSBdisconnected',flush=True)
    while not stable.exists() and time.monotonic()<deadline:time.sleep(.05)
    if not stable.exists():record['status']='no_reconnect_observed_before_timeout';save();return
    record['USB_reconnect_utc']=datetime.now(timezone.utc).isoformat()
    record['USB_reconnect_monotonic_ns']=time.monotonic_ns()
    time.sleep(.1)
    port=open_board(STABLE_PORT,baud=115200,timeout=.1)
    data=bytearray()
    try:
        until=time.monotonic()+8
        while time.monotonic()<until:data.extend(port.read(8192))
    finally:port.close()
    boot=re.sub(r'\x1b\[[0-9;]*m','',data.decode(errors='replace'))
    boot=re.sub(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}','[redacted device address]',boot)
    (args.output/'boot.log').write_text(boot)
    record.update(status='USB_cycle_observed_boot_captured',boot_bytes=len(data),serial_handle_closed=True)
    save();print('USBcycleandbootrecorded; actualpowerremovalconfirmationstillrequired',flush=True)


if __name__=='__main__':main()

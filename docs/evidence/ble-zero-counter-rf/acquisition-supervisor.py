import asyncio
import csv
import json
from pathlib import Path
import select
import signal
import subprocess
import time
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType

ROOT = Path.cwd()
OUT = ROOT / '.scratch/ble-zero-counter-rf'

async def state():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        tree = await bus.introspect('org.bluez', '/org/bluez/hci0')
        obj = bus.get_proxy_object('org.bluez', '/org/bluez/hci0', tree)
        props = obj.get_interface('org.freedesktop.DBus.Properties')
        return {'powered': (await props.call_get('org.bluez.Adapter1', 'Powered')).value,
                'discovering': (await props.call_get('org.bluez.Adapter1', 'Discovering')).value,
                'active_instances': (await props.call_get('org.bluez.LEAdvertisingManager1', 'ActiveInstances')).value}
    finally:
        bus.disconnect()

def wait_ready(proc, prefix, sink, bound=8):
    deadline = time.monotonic()+bound
    while True:
        ready, _, _ = select.select([proc.stdout], [], [], max(0, deadline-time.monotonic()))
        assert ready, f'{prefix} timeout'
        line = proc.stdout.readline().decode()
        sink.write(line); sink.flush()
        if line.startswith(prefix): return
        assert line and time.monotonic() < deadline, line

before = asyncio.run(state())
assert before == {'powered': True, 'discovering': False, 'active_instances': 0}
(OUT/'preflight.json').write_text(json.dumps(before, indent=2)+'\n')
episodes = []
monitor = receiver = None
active_source_name = None
source = None
with (OUT/'monitor-operation.log').open('w') as mlog, (OUT/'receiver-operation.log').open('w') as rlog:
    try:
        monitor = subprocess.Popen(['python3','tools/ble_dumpcap_monitor.py','--seconds','90','--output',str(OUT/'hci-control.json')], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        wait_ready(monitor, 'MONITOR_READY', mlog)
        receiver = subprocess.Popen(['python3','tools/measure_owned_ble.py','--output',str(OUT/'receiver'),'--private',str(OUT/'iq'),'--seconds','80','--frequency','2401','--bandwidth','20','--gain','48'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        wait_ready(receiver, 'ACQUISITION_READY', rlog)
        time.sleep(5.1)
        for i in range(1, 11):
            episode = OUT / 'sources' / f'zero-counter-{i:02d}'
            episode.mkdir(parents=True, exist_ok=False)
            source_before = asyncio.run(state())
            assert source_before == before
            (episode/'preflight.json').write_text(json.dumps(source_before,indent=2)+'\n')
            active_source_name = f'esp-sdr-zero-counter-20261002-{i:02d}'
            with (episode/'source-control.jsonl').open('w') as log, (episode/'source-operation.log').open('w') as err:
                source = subprocess.Popen(['docker','run','--rm','--name',active_source_name,'--network','host','--read-only','--cap-drop','ALL','--cap-add','NET_ADMIN','--cap-add','NET_RAW','--mount',f'type=bind,src={ROOT / "tools/ble_direct_hci_source.py"},dst=/source.py,readonly','--entrypoint','/usr/bin/python3','8cae9cbe8e90','/source.py','--handle','1','--duration-ms','5000','--events','255','--interval-ms','20','--start-delay','0'], stdout=log, stderr=err)
                source.wait(timeout=30)
            active_source_name = None
            source_after = asyncio.run(state())
            (episode/'postflight.json').write_text(json.dumps(source_after,indent=2)+'\n')
            records = [json.loads(line) for line in (episode/'source-control.jsonl').read_text().splitlines()]
            summary = next(row for row in records if row['kind']=='source_closed')
            entry = {'episode_id':episode.name,'source_returncode':source.returncode,'summary':summary}
            episodes.append(entry)
            (OUT/'source-episodes.json').write_text(json.dumps(episodes,indent=2)+'\n')
            print(json.dumps(entry), flush=True)
            assert summary['cleanup_success'] and source_after == before
            if i != 10: time.sleep(1)
        stdout, stderr = receiver.communicate(timeout=30)
        rlog.write(stdout.decode()); rlog.write(stderr.decode())
        assert receiver.returncode == 0
        stdout, _ = monitor.communicate(timeout=15)
        mlog.write(stdout.decode())
        assert monitor.returncode == 0
    finally:
        if active_source_name is not None:
            # Stop only this named task-owned source. SIGINT gives the helper
            # its four-second bounded own-handle cleanup before forced stop.
            with (OUT/'source-container-stop.log').open('w') as stoplog:
                try:
                    subprocess.run(['docker','stop','--signal','SIGINT','--timeout','8',active_source_name],stdout=stoplog,stderr=stoplog,timeout=12)
                except subprocess.TimeoutExpired:
                    stoplog.write('Container supervisor timed out; source cleanup unverified.\n')
                    if source is not None and source.poll() is None:
                        source.send_signal(signal.SIGINT)
            if source is not None and source.poll() is None:
                try: source.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    source.kill(); source.wait(timeout=2)
        for proc in (receiver, monitor):
            if proc is None: continue
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try: proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=2)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()
after = asyncio.run(state())
(OUT/'postflight.json').write_text(json.dumps(after,indent=2)+'\n')
assert after == before
rows = list(csv.DictReader((OUT/'receiver/captures.csv').open()))
first_source = [json.loads(line) for line in (OUT/'sources/zero-counter-01/source-control.jsonl').read_text().splitlines()]
enable = next(row['monotonic_ns'] for row in first_source if row['kind']=='command_sent' and row['step']=='enable')
closed = episodes[-1]['summary']['monotonic_ns']
last_source = [json.loads(line) for line in (OUT/'sources/zero-counter-10/source-control.jsonl').read_text().splitlines()]
closed = next(row['monotonic_ns'] for row in last_source if row['kind']=='source_socket_closed')
baseline = (enable-int(rows[0]['command_start_ns']))/1e9
tail = (int(rows[-1]['payload_received_ns'])-closed)/1e9
receipt = {'captures':len(rows),'baseline_seconds':baseline,'tail_seconds':tail,'all_ten_episodes_retained':len(episodes)==10,'monitor_closed':monitor.returncode==0,'receiver_closed':receiver.returncode==0,'physical_RF_count':None,'no_capture_rate_claim':True}
(OUT/'schedule-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
assert baseline >= 5 and tail > 10

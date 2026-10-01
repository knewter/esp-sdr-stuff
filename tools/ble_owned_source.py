#!/usr/bin/env python3
"""Register a bounded owned BLE test advertisement through BlueZ D-Bus.

Never changes power, discoverability or pairings. Logs commanded episodes only;
controller repetitions and exact over-the-air packet count remain unknown.
"""
import argparse
import asyncio
import json
from pathlib import Path
import signal
import time
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method
from dbus_next import Variant

MARKER = b'ESP-SDR-EVAL'
PATH = '/org/espsdr/evaluation/advertisement'


class Advertisement(ServiceInterface):
    def __init__(self):
        super().__init__('org.bluez.LEAdvertisement1')
        self.released = False
    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> 's':
        return 'broadcast'
    @dbus_property(access=PropertyAccess.READ)
    def ManufacturerData(self) -> 'a{qv}':
        return {0xffff: Variant('ay', MARKER)}
    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'as':
        return []
    @method()
    def Release(self):
        self.released = True


async def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    record = {'schema':1, 'kind':'commanded owned BLE advertising episodes',
              'manufacturer_test_marker_hex': MARKER.hex(), 'manufacturer_id': 'ffff',
              'expected_manufacturer_ad_hex': (bytes([len(MARKER)+3, 0xff, 0xff, 0xff])+MARKER).hex(),
              'exact_over_air_emission_count': None, 'episodes':[],
              'limitations':'RegisterAdvertisement success establishes controller configuration acceptance, not an independently observed transmission count, packet timing, channel map or actual RF. No address or local network name is published.'}
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    registered = False
    adv = Advertisement()
    stop = asyncio.Event()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    def save():
        (args.output/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    try:
        adapter_path = '/org/bluez/hci0'
        tree = await bus.introspect('org.bluez', adapter_path)
        adapter = bus.get_proxy_object('org.bluez', adapter_path, tree)
        properties = adapter.get_interface('org.freedesktop.DBus.Properties')
        powered = (await properties.call_get('org.bluez.Adapter1','Powered')).value
        if not powered:
            raise RuntimeError('Controller is powered off; no power mutation authorized')
        active = (await properties.call_get('org.bluez.LEAdvertisingManager1','ActiveInstances')).value
        if active:
            raise RuntimeError('Other advertisements are active; stop to avoid source overlap')
        record['active_instances_before'] = active
        record['supported_instances'] = (await properties.call_get('org.bluez.LEAdvertisingManager1','SupportedInstances')).value
        manager = adapter.get_interface('org.bluez.LEAdvertisingManager1')
        bus.export(PATH, adv)
        for index in range(args.episodes):
            if stop.is_set():break
            episode = {'index':index,'register_requested_monotonic_ns':time.monotonic_ns()}
            record['episodes'].append(episode)
            await manager.call_register_advertisement(PATH,{})
            registered=True
            episode['registration_accepted_monotonic_ns']=time.monotonic_ns()
            episode['registered_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
            print(f'SOURCE_ON episode={index} marker={MARKER.hex()} accepted',flush=True)
            save()
            try: await asyncio.wait_for(stop.wait(), args.seconds)
            except asyncio.TimeoutError:pass
            episode['unregister_requested_monotonic_ns']=time.monotonic_ns()
            if not adv.released:
                await manager.call_unregister_advertisement(PATH)
            registered=False
            episode['unregistration_accepted_monotonic_ns']=time.monotonic_ns()
            episode['active_instances_after']=(await properties.call_get('org.bluez.LEAdvertisingManager1','ActiveInstances')).value
            print(f'SOURCE_OFF episode={index} accepted',flush=True)
            save()
            if index+1<args.episodes and not stop.is_set():
                try:await asyncio.wait_for(stop.wait(),args.off_seconds)
                except asyncio.TimeoutError:pass
        record['status']='completed' if len(record['episodes'])==args.episodes and not stop.is_set() else 'interrupted'
    except Exception as error:
        record['status']='failed';record['error_kind']=type(error).__name__;record['error']=str(error)[:240]
        print(f'SOURCE_FAILED {type(error).__name__}: {str(error)[:240]}',flush=True)
    finally:
        if registered and not adv.released:
            try:
                await manager.call_unregister_advertisement(PATH)
                record['cleanup_unregistration']='accepted'
            except Exception as error:
                record['cleanup_unregistration']=type(error).__name__
        bus.disconnect();save()
    return 0 if record['status']=='completed' else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=60)
    parser.add_argument('--episodes',type=int,default=1)
    parser.add_argument('--off-seconds',type=float,default=.1)
    args=parser.parse_args()
    if not 0.01 <= args.seconds <= 3600 or not 1 <= args.episodes <= 1000 or args.off_seconds <0:
        parser.error('bounded positive seconds/episode counts required')
    raise SystemExit(asyncio.run(run(args)))

if __name__=='__main__':main()

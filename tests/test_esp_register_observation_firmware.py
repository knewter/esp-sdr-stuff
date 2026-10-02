"""Actual receiver C acquisition exercised with offline synthetic MMIO only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_esp_register_observation as build
FIXTURE=ROOT/'tests/fixtures/esp_register_observation'


def parse_wire(wire):
    """Independent synthetic transcript reader, not the future host tool."""
    lines=[];payloads=[];pos=0
    while pos<len(wire):
        stop=wire.find(b'\n',pos)
        if stop<0:return lines,payloads,wire[pos:]
        line=wire[pos:stop];pos=stop+1
        if line.startswith(b'DATA '):
            tag,count,crc,elapsed=line.decode().split();size=(int(count)*20+7)//8
            if len(wire)-pos<size:return lines,payloads,wire[pos:]
            payload=wire[pos:pos+size];pos+=size
            if zlib.crc32(payload)!=int(crc,16):raise AssertionError('Synthetic DATA CRC mismatch')
            payloads.append(dict(count=int(count),elapsed=int(elapsed),crc=crc,data=payload))
            lines.append(('DATA',len(payloads)-1))
        elif line.startswith(b'REGOBS1 '):
            prefix,crc,body=line.split(b' ',2)
            if zlib.crc32(body)!=int(crc,16):raise AssertionError('Synthetic metadata CRC mismatch')
            if len(line)+1>=2048:raise AssertionError('Unbounded receipt')
            lines.append(('REGOBS1',json.loads(body)))
        else:lines.append(('text',line.decode()))
    return lines,payloads,b''


class ActualReceiverC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which(os.environ.get('CC','cc')):raise unittest.SkipTest('Use the Nix CI/compiler shell')
        cls.temp=tempfile.TemporaryDirectory();cls.path=Path(cls.temp.name)
        overlay=build.load_overlay()
        (cls.path/'receiver.c').write_text(overlay.receiver_text())
        (cls.path/'burst_serial.c').write_text(overlay.transport_text())
        for name in ('register_observation.h','register_commands.h'):shutil.copyfile(build.FIRMWARE/name,cls.path/name)
        for name in ('rx_bandwidth.h','rx_tuning.h','burst_serial.h'):shutil.copyfile(build.FIRMWARE/'base'/name,cls.path/name)
        for name in ('harness.c','harness_shim.h','transport_harness.c','transport_shim.h'):shutil.copyfile(FIXTURE/name,cls.path/name)
        (cls.path/'ring_probe.h').write_text('/* RING_PROBE disabled in diagnostic profile. */\n')
        # The pinned reply() body has an existing int/sizeof comparison. Keep
        # that body untouched while making other host compiler warnings fatal.
        for source,binary in (('harness.c','check'),('transport_harness.c','transport')):
            compiled=subprocess.run([os.environ.get('CC','cc'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-sign-compare','-I'+str(cls.path),
                        str(cls.path/source),'-o',str(cls.path/binary)],capture_output=True,text=True)
            if compiled.returncode:raise AssertionError(compiled.stderr)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def run_case(self,mode):
        done=subprocess.run([str(self.path/'check'),str(mode)],capture_output=True,check=True,timeout=5)
        return (*parse_wire(done.stdout),json.loads(done.stderr))

    def test_twenty_real_captures_metadata_crc_and_order(self):
        lines,payloads,partial,summary=self.run_case(0)
        receipts=[item for tag,item in lines if tag=='REGOBS1']
        self.assertEqual([r['kind'] for r in receipts],['config']+['capture']*20+['end'])
        self.assertEqual(len(payloads),20);self.assertFalse(partial)
        self.assertEqual(summary['triggers'],20);self.assertEqual(summary['selector_reads'],81)
        self.assertEqual(sum(len(p['data']) for p in payloads),819000)
        records=[r for receipt in receipts[:-1] for r in receipt['records']]
        self.assertEqual([r['sequence'] for r in records],list(range(81)))
        self.assertTrue(all(r['selector']==48 and r['bit23']==1 for r in records))
        self.assertTrue(all(r['read_begin_us']<=r['read_end_us'] for r in records))
        self.assertTrue(all(a['read_end_us']<=b['read_begin_us'] for a,b in zip(records,records[1:])))
        for i,receipt in enumerate(receipts[1:-1]):
            self.assertEqual(receipt['capture_ordinal'],i)
            self.assertEqual([r['stage'] for r in receipt['records']],['before_acquire','armed_before_trigger','dump_complete','restored_after_dump'])
            self.assertEqual(receipt['payload_crc32'],payloads[i]['crc'])
            idx=lines.index(('DATA',i));self.assertEqual(lines[idx+1],('REGOBS1',receipt))
        # Independent packing calculation for initial pairs; actual C packs all.
        a=0;b=(7<<10)|3
        self.assertEqual(payloads[0]['data'][:5],(a | (b<<20)).to_bytes(5,'little'))
        self.assertEqual(receipts[-1]['record_count'],81)

    def test_variant_readbacks_are_retained_not_repaired(self):
        lines,_,_,summary=self.run_case(1)
        receipts=[r for tag,r in lines if tag=='REGOBS1'];first=receipts[1]['records']
        self.assertEqual([r['selector'] for r in first],[48,47,46,45])
        self.assertEqual([r['bit23'] for r in first],[1,0,1,1])
        self.assertEqual(summary['gain_writes'],2)
        self.assertEqual(receipts[-1]['kind'],'end')

    def failure(self,mode,kind):
        lines,payloads,partial,summary=self.run_case(mode)
        failed=[r for tag,r in lines if tag=='REGOBS1' and r['kind']=='failed']
        self.assertEqual(len(failed),1);self.assertEqual(failed[0]['failure_kind'],kind)
        self.assertFalse(any(tag=='REGOBS1' and r['kind']=='end' for tag,r in lines))
        return failed[0],payloads,partial,summary

    def test_capture_timeout_restores_and_retains_actual_stages(self):
        r,p,_,s=self.failure(2,'capture_timeout')
        self.assertFalse(r['completion']);self.assertEqual(len(r['records']),4)
        self.assertFalse(p);self.assertEqual(s['triggers'],1)

    def test_wrong_hardware_count_is_not_timeout_success(self):
        r,p,_,_=self.failure(3,'capture_count');self.assertTrue(r['completion'])
        self.assertEqual(r['returned_samples'],16379);self.assertFalse(p)

    def test_sentinels_inside_and_outside_capture_fail_after_restoration(self):
        for mode in (4,5):
            with self.subTest(mode=mode):
                r,p,_,_=self.failure(mode,'capture_memory');self.assertEqual(len(r['records']),4);self.assertFalse(p)

    def test_partial_header_and_payload_never_receive_appended_metadata(self):
        for mode in (6,7):
            with self.subTest(mode=mode):
                lines,payloads,partial,s=self.run_case(mode)
                self.assertTrue(partial);self.assertFalse(payloads)
                self.assertEqual([r['kind'] for tag,r in lines if tag=='REGOBS1'],['config'])
                self.assertEqual(s['triggers'],1)

    def test_partial_metadata_has_no_terminal_success(self):
        lines,payloads,partial,s=self.run_case(8)
        self.assertEqual(len(payloads),1);self.assertTrue(partial)
        self.assertEqual(s['state'],2)

    def test_deadlines_before_and_during_capture_stop(self):
        r,p,_,s=self.failure(9,'session_deadline');self.assertFalse(p);self.assertEqual(s['triggers'],0)
        r,p,_,s=self.failure(17,'session_deadline');self.assertEqual(len(p),1);self.assertEqual(len(r['records']),4)

    def test_early_end_wrong_nonce_and_reapplication_do_not_capture(self):
        for mode in (10,11,12):
            with self.subTest(mode=mode):
                _,p,_,s=self.failure(mode,'session_state');self.assertFalse(p);self.assertEqual(s['triggers'],0)

    def test_capacity_guard_prevents_82nd_record_and_capture(self):
        _,p,_,s=self.failure(13,'record_capacity');self.assertFalse(p);self.assertEqual(s['records'],81)

    def test_profile_mismatch_cannot_begin(self):
        lines,p,_,s=self.run_case(14);self.assertFalse(p);self.assertEqual(s['triggers'],0)
        failed=[r for tag,r in lines if tag=='REGOBS1']
        self.assertEqual([r['kind'] for r in failed],['failed'])
        self.assertEqual(failed[0]['records'],[]);self.assertIsNone(failed[0]['completion'])

    def test_unarmed_cap20_stays_binary_only_but_identity_is_distinct(self):
        lines,p,_,s=self.run_case(15);self.assertEqual(len(p),1);self.assertEqual(s['records'],0)
        self.assertIn(('text','ESP32REGOBS1 regobs-v1 burst 16380'),lines)
        self.assertFalse(any(tag=='REGOBS1' for tag,_ in lines))

    def test_excess_capture_cannot_complete_or_restart(self):
        _,p,_,s=self.failure(16,'session_state');self.assertEqual(len(p),20);self.assertEqual(s['triggers'],20)

    def test_actual_common_parser_unarmed_baud_behavior_stays_unchanged(self):
        done=subprocess.run([str(self.path/'transport'),'0'],check=True,capture_output=True,timeout=5)
        lines,payloads,partial=parse_wire(done.stdout)
        self.assertIn(('text','BAUD 921600'),lines);self.assertIn(('text','OK BAUD 1000000'),lines)
        self.assertFalse(payloads);self.assertFalse(partial)

    def test_actual_common_parser_armed_baud_and_queries_fail_without_rate_change(self):
        for which in (1,2,3):
            with self.subTest(which=which):
                done=subprocess.run([str(self.path/'transport'),str(which)],check=True,capture_output=True,timeout=5)
                lines,payloads,partial=parse_wire(done.stdout)
                receipts=[r for tag,r in lines if tag=='REGOBS1']
                self.assertEqual([r['kind'] for r in receipts],['config','failed'])
                self.assertEqual(receipts[-1]['failure_kind'],'session_state')
                self.assertNotIn(('text','OK BAUD 1000000'),lines)
                self.assertFalse(payloads);self.assertFalse(partial)

    def test_actual_parser_and_app_dispatch_reject_armed_overlong_and_nul_bytes(self):
        for which in (4,7):
            with self.subTest(which=which):
                done=subprocess.run([str(self.path/'transport'),str(which)],check=True,capture_output=True,timeout=5)
                lines,payloads,partial=parse_wire(done.stdout)
                receipts=[r for tag,r in lines if tag=='REGOBS1']
                self.assertEqual([r['kind'] for r in receipts],['config','failed'])
                self.assertEqual(receipts[-1]['failure_kind'],'session_state')
                self.assertIsNone(receipts[-1]['capture_ordinal'])
                self.assertEqual(receipts[-1]['records'],[])
                self.assertNotIn(('text','ERR command_length'),lines)
                self.assertFalse(payloads);self.assertFalse(partial)

    def test_actual_parser_unarmed_overlong_and_nul_behavior_is_preserved(self):
        done=subprocess.run([str(self.path/'transport'),'5'],check=True,capture_output=True,timeout=5)
        lines,payloads,partial=parse_wire(done.stdout)
        self.assertIn(('text','ERR command_length'),lines)
        self.assertFalse(payloads);self.assertFalse(partial)
        done=subprocess.run([str(self.path/'transport'),'8'],check=True,capture_output=True,timeout=5)
        lines,payloads,partial=parse_wire(done.stdout)
        self.assertEqual(len(payloads),1);self.assertFalse(partial)
        self.assertFalse(any(tag=='REGOBS1' for tag,_ in lines))

    def test_actual_parser_rejects_nul_suffix_on_new_diagnostic_begin(self):
        done=subprocess.run([str(self.path/'transport'),'10'],check=True,capture_output=True,timeout=5)
        lines,payloads,partial=parse_wire(done.stdout)
        receipts=[r for tag,r in lines if tag=='REGOBS1']
        self.assertEqual([r['kind'] for r in receipts],['failed'])
        self.assertEqual(receipts[0]['failure_kind'],'session_state')
        self.assertEqual(receipts[0]['records'],[])
        self.assertFalse(payloads);self.assertFalse(partial)

    def test_actual_parser_after_partial_data_suppresses_overlong_and_nul_output(self):
        for which in (6,9):
            with self.subTest(which=which):
                done=subprocess.run([str(self.path/'transport'),str(which)],check=True,capture_output=True,timeout=5)
                lines,payloads,partial=parse_wire(done.stdout)
                self.assertEqual(len(partial),17);self.assertFalse(payloads)
                self.assertEqual([r['kind'] for tag,r in lines if tag=='REGOBS1'],['config'])
                self.assertNotIn(b'ERR',partial);self.assertNotIn(b'REGOBS1',partial)


class BuildGuards(unittest.TestCase):
    def test_exact_base_bytes_and_deterministic_overlay(self):
        files,profile=build.source_files();overlay=build.load_overlay()
        self.assertEqual(len(files),len(build.FILES));self.assertEqual(overlay.receiver_text(),overlay.receiver_text())
        with self.assertRaises(ValueError):overlay.receiver_text(b'wrong base')
        with self.assertRaises(ValueError):overlay.transport_text(b'wrong transport base')
        self.assertEqual(profile['reserved_sample_slab'],[0x3ffe8000,0x3fff8000])
        self.assertIn('        regobs_dispatch_status(status, line);',overlay.receiver_text())
        self.assertNotIn('if (status < 0) reply("ERR command_length',overlay.receiver_text())

    def test_security_duplicate_and_target_configuration_rejected(self):
        text='\n'.join(build.REQUIRED)+'\n';build.validate_config(text)
        for bad in ('CONFIG_SECURE_BOOT=y','CONFIG_IDF_TARGET="esp32s3"','CONFIG_ESP_SDR_UART_BAUD=2000000'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):build.validate_config(text+bad+'\n')

    def test_actual_symbol_bounds_reject_slab_overlap_missing_and_oversize(self):
        text='3ffb1000 00000800 B regobs_json\n3ffb1800 00000800 B regobs_wire\n3ffb2000 00000798 B regobs_records\n'
        self.assertEqual(len(build.validate_symbols(text)),3)
        for bad in (text.replace('3ffb2000','3ffe8000'),text.replace('00000798','00010000'),text.splitlines()[0],text+text.splitlines()[0]):
            with self.assertRaises(ValueError):build.validate_symbols(bad)


if __name__=='__main__':unittest.main()

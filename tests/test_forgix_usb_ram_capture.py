"""Exercise the actual parser/collector with synthetic byte streams; no devices."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SOURCE = Path(__file__).resolve().parents[1]/"tools/forgix_usb_ram_capture.py"
spec = importlib.util.spec_from_file_location("forgix_usb_capture", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SHA, NONCE = "a"*64, bytes(range(16))


def frame(kind, seq, us, *, dropped=0, nonce=None, rate=65536, start=100000, boot=1000, accepted=None, highwater=1, partial=0, stall=0, sha=SHA):
    nonce = bytes(16) if kind == 0 and nonce is None else NONCE if nonce is None else nonce
    payload = bytearray(460)
    if kind == 2:
        payload[:] = bytes(((seq*131+i*17)^nonce[i%16]) & 255 for i in range(460))
    else:
        enqueued = seq-dropped
        accepted = enqueued*512 if accepted is None else accepted
        m.STATS.pack_into(payload, 0, 0 if kind == 0 else rate, seq+1, enqueued, dropped, partial,
                          0 if kind == 0 else highwater, accepted, stall, boot, 0 if kind == 0 else start, 120000000)
        payload[64:128] = sha.encode()
        profile = m.PROFILE.encode()+b"\0"
        payload[128:128+len(profile)] = profile
    raw = m.HEADER.pack(b"FRAM", 1, kind, seq, 512, 460, us, nonce, 0)+payload
    return raw+struct.pack("<I", zlib.crc32(raw))


def repaired(data):
    return bytes(data[:508])+struct.pack("<I", zlib.crc32(data[:508]))


def decoded(raw):
    d = m.Decoder()
    d.feed(raw)
    return d.next_frame()


class FakeClock:
    def __init__(self):
        self.ns = 0

    def __call__(self):
        return self.ns

    def sleep(self, seconds):
        self.ns += int(seconds*1e9)


class FakeSerial:
    def __init__(self, clock, events, write_count=32):
        self.clock, self.events, self.closed, self.command = clock, iter(events), False, None
        self.write_count = write_count

    def read(self, length):
        try:
            when, data = next(self.events)
        except StopIteration:
            self.clock.sleep(.05)
            return b""
        self.clock.ns = max(self.clock.ns, int(when*1e9))
        if isinstance(data, BaseException):
            raise data
        return data

    def write(self, data):
        self.command = data
        return self.write_count

    def close(self):
        self.closed = True


def valid_events():
    return [(.05, frame(0,0,5000)), (.1, frame(1,1,100000)),
            (.2, frame(2,2,200000)), (30.1, frame(2,3,30100000)),
            (60.1, frame(4,4,60100000))]


class ProtocolTests(unittest.TestCase):
    def initial(self):
        v = m.Validator(SHA,65536,NONCE)
        v.accept(decoded(frame(0,0,5000)),0)
        v.mark_start()
        v.accept(decoded(frame(1,1,100000)),100000000)
        return v

    def test_start_exact_bytes_and_crc(self):
        command = m.start_command(262144,NONCE)
        self.assertEqual(len(command),32)
        self.assertEqual(struct.unpack("<4sHHI16s",command[:28]),(b"FRAM",1,1,262144,NONCE))
        self.assertEqual(struct.unpack("<I",command[28:])[0],zlib.crc32(command[:28]))
        for rate, nonce in [(0,NONCE),(65536,b""),(65536,bytes(16))]:
            with self.assertRaises(m.CaptureError):
                m.start_command(rate,nonce)

    def test_partial_reads_and_multiple_frames(self):
        first, second = frame(0,0,5000),frame(1,1,100000)
        d = m.Decoder()
        for byte in first[:511]:
            d.feed(bytes([byte]))
            self.assertIsNone(d.next_frame())
        d.feed(first[511:]+second)
        self.assertEqual(d.next_frame()["type"],0)
        self.assertEqual(d.next_frame()["type"],1)
        d.finish()

    def test_crc_and_damaged_prefix_not_discarded(self):
        for bad in (b"junk"+frame(0,0,5000), frame(0,0,5000)[:90]+b"x"+frame(0,0,5000)[91:]):
            d=m.Decoder(); d.feed(bad)
            with self.assertRaises(m.CaptureError): d.next_frame()
            self.assertEqual(bytes(d.pending),bad)
            self.assertEqual(d.byte_offset,0)

    def test_all_header_fields_are_validated_with_valid_crc(self):
        for offset, value in [(0,0),(4,2),(6,5),(13,0),(16,0),(44,1)]:
            raw=bytearray(frame(0,0,5000)); raw[offset]=value
            with self.subTest(offset=offset), self.assertRaises(m.CaptureError):
                decoded(repaired(raw))

    def test_truncation_retains_prefix(self):
        d=m.Decoder(); d.feed(frame(2,2,200000)[:123])
        with self.assertRaises(m.CaptureError): d.finish()
        self.assertEqual(len(d.pending),123)

    def test_config_requires_binding_zero_nonce_and_epoch(self):
        for raw in [frame(0,0,5000,sha="b"*64),frame(0,0,5000,nonce=NONCE),frame(0,0,0)]:
            with self.assertRaises(m.CaptureError):
                m.Validator(SHA,65536,NONCE).accept(decoded(raw),0)
        raw=bytearray(frame(0,0,5000)); raw[176]=ord("X")
        with self.assertRaises(m.CaptureError):
            m.Validator(SHA,65536,NONCE).accept(decoded(repaired(raw)),0)

    def test_ready_requires_start_and_nonce_rate_source(self):
        for kwargs in [{"nonce":b"z"*16},{"rate":262144},{"sha":"b"*64}]:
            v=m.Validator(SHA,65536,NONCE); v.accept(decoded(frame(0,0,5000)),0); v.mark_start()
            with self.assertRaises(m.CaptureError):v.accept(decoded(frame(1,1,100000,**kwargs)),1)
        v=m.Validator(SHA,65536,NONCE); v.accept(decoded(frame(0,0,5000)),0)
        with self.assertRaises(m.CaptureError):v.accept(decoded(frame(1,1,100000)),1)

    def test_data_checks_payload_nonce_sequence_and_time(self):
        raw=bytearray(frame(2,2,200000)); raw[100]^=1
        cases=[repaired(raw),frame(2,2,200000,nonce=b"z"*16),frame(2,1,200000),frame(2,2,99999),frame(2,2,60100000)]
        for raw in cases:
            with self.assertRaises(m.CaptureError):self.initial().accept(decoded(raw),2)

    def test_dropped_records_reconcile_and_are_retained(self):
        v=self.initial()
        v.accept(decoded(frame(2,2,200000)),200000000)
        v.accept(decoded(frame(3,5,1100000,dropped=2)),1100000000)
        v.accept(decoded(frame(4,6,60100000,dropped=2)),60100000000)
        v.finish()
        self.assertEqual(v.gaps,[{"first":3,"last":4,"count":2}])
        self.assertFalse(v.summary()["cdc_accepted_bytes_are_host_delivery"])

    def test_host_loss_is_not_relabelled_device_drop(self):
        v=self.initial();v.accept(decoded(frame(2,4,200000)),2)
        v.accept(decoded(frame(4,5,60100000)),60100000000)
        with self.assertRaises(m.CaptureError):v.finish()

    def test_counter_snapshots_highwater_monotonicity_and_early_end(self):
        for raw in [frame(3,2,1100000,highwater=17),frame(3,2,1100000,accepted=9999),frame(4,2,200000)]:
            with self.assertRaises(m.CaptureError):self.initial().accept(decoded(raw),2)
        v=self.initial();v.accept(decoded(frame(3,2,1100000,partial=4,accepted=1000,stall=1000)),2)
        with self.assertRaises(m.CaptureError):v.accept(decoded(frame(3,3,2100000,partial=3,accepted=1000,stall=1000)),3)
        raw=bytearray(frame(3,2,1100000));struct.pack_into("<I",raw,56,0)
        with self.assertRaises(m.CaptureError):self.initial().accept(decoded(repaired(raw)),2)


class CollectorTests(unittest.TestCase):
    def run_capture(self, events, *, write_count=32, nonce=NONCE):
        clock=FakeClock(); transport=FakeSerial(clock,events,write_count)
        root=Path(self.temp.name)
        store=m.PrivateCapture(root/"capture",root)
        result=m.collect(store,SHA,65536,nonce,lambda port: transport,
                         lambda:{"port":"synthetic-only"},lambda:{"ownership":"synthetic fixture"},clock,clock.sleep)
        return result,transport,store

    def setUp(self):self.temp=tempfile.TemporaryDirectory()
    def tearDown(self):self.temp.cleanup()

    def test_bounded_run_private_artifacts_pause_and_handle_close(self):
        result,transport,store=self.run_capture(valid_events())
        self.assertTrue(transport.closed)
        self.assertEqual(transport.command,m.start_command(65536,NONCE))
        self.assertEqual(result["status"],"complete_integrity_verified")
        self.assertEqual(result["verified_data_payload_bytes"],920)
        self.assertEqual(result["device_start_to_end_s"],60)
        self.assertAlmostEqual(result["actual_read_pause"]["actual_duration_s"],.1)
        self.assertLessEqual(result["actual_host_operation_s"],85)
        self.assertEqual(store.path.stat().st_mode & 0o777,0o700)
        for name in ("nonce.bin","raw.bin","manifest.json","receipts.jsonl"):
            self.assertEqual((store.path/name).stat().st_mode & 0o777,0o600)
        self.assertEqual((store.path/"raw.bin").read_bytes(),b"".join(data for _,data in valid_events()))

    def check_failed_closed(self, events, expected, *, write_count=32):
        clock=FakeClock(); transport=FakeSerial(clock,events,write_count)
        root=Path(self.temp.name);store=m.PrivateCapture(root/"capture",root)
        with self.assertRaises(expected):
            m.collect(store,SHA,65536,NONCE,lambda p:transport,lambda:{"port":"synthetic-only"},lambda:{},clock,clock.sleep)
        self.assertTrue(transport.closed)
        manifest=json.loads((store.path/"manifest.json").read_text())
        self.assertNotEqual(manifest["status"],"complete_integrity_verified")
        return manifest,store

    def test_corruption_kept_in_raw_and_pending(self):
        manifest,store=self.check_failed_closed([(.05,b"bad!"+frame(0,0,5000))],m.CaptureError)
        self.assertEqual(manifest["unparsed_prefix_bytes"],516)
        self.assertTrue((store.path/"raw.bin").read_bytes().startswith(b"bad!"))

    def test_cancel_keeps_receipt_and_closes(self):
        manifest,_=self.check_failed_closed(valid_events()[:3]+[(1,KeyboardInterrupt())],KeyboardInterrupt)
        self.assertEqual(manifest["status"],"cancelled")

    def test_transport_error_closes(self):
        self.check_failed_closed(valid_events()[:2]+[(1,OSError("synthetic"))],OSError)

    def test_partial_start_write_closes(self):
        self.check_failed_closed(valid_events(),m.CaptureError,write_count=31)

    def test_missing_end_hits_deadline_closes(self):
        manifest,_=self.check_failed_closed(valid_events()[:-1],m.CaptureError)
        self.assertGreaterEqual(manifest["actual_host_operation_s"],85)

    def test_config_startup_is_bounded(self):
        manifest,_=self.check_failed_closed([],m.CaptureError)
        self.assertLess(manifest["actual_host_operation_s"],21)

    def test_trailing_partial_record_is_failure(self):
        manifest,_=self.check_failed_closed(valid_events()+[(60.2,b"FRAM")],m.CaptureError)
        self.assertEqual(manifest["unparsed_prefix_bytes"],4)

    def test_records_after_end_are_failure(self):
        self.check_failed_closed(valid_events()+[(60.2,frame(2,5,200000))],m.CaptureError)

    def test_private_directory_refuses_existing_and_outside(self):
        root=Path(self.temp.name)
        m.PrivateCapture(root/"exists",root)
        with self.assertRaises(FileExistsError):m.PrivateCapture(root/"exists",root)
        with self.assertRaises(m.CaptureError):m.PrivateCapture(root,root)

    def test_private_directory_refuses_symlink_root_and_child_ancestors(self):
        root=Path(self.temp.name);real=root/"real";real.mkdir()
        alias=root/"alias";alias.symlink_to(real)
        with self.assertRaises(m.CaptureError):m.PrivateCapture(alias/"capture",alias)
        backups=root/"backups";backups.mkdir();(backups/"redirect").symlink_to(real)
        with self.assertRaises(m.CaptureError):m.PrivateCapture(backups/"redirect/capture",backups)

    def test_read_after_deadline_is_retained_then_fails(self):
        late=frame(2,3,30100000)
        manifest,store=self.check_failed_closed(valid_events()[:3]+[(85.1,late)],m.CaptureError)
        self.assertTrue((store.path/"raw.bin").read_bytes().endswith(late))
        self.assertEqual(manifest["unparsed_prefix_bytes"],512)
        self.assertTrue(manifest["raw_saved_matches_received_length"])

    def test_partial_storage_failure_reports_actual_saved_prefix(self):
        clock=FakeClock();transport=FakeSerial(clock,valid_events())
        root=Path(self.temp.name);store=m.PrivateCapture(root/"capture",root)
        original_open=store.open
        class FailedRaw:
            def __enter__(self):self.stream=original_open("raw.bin");return self
            def __exit__(self,*args):self.stream.close()
            def write(self,data):self.stream.write(data[:100]);raise OSError("synthetic partial write")
        store.open=lambda name:FailedRaw() if name=="raw.bin" else original_open(name)
        with self.assertRaises(OSError):
            m.collect(store,SHA,65536,NONCE,lambda p:transport,lambda:{"port":"synthetic-only"},lambda:{},clock,clock.sleep)
        manifest=json.loads((store.path/"manifest.json").read_text())
        self.assertTrue(transport.closed)
        self.assertEqual(manifest["host_received_bytes"],512)
        self.assertEqual(manifest["raw_bytes"],100)
        self.assertFalse(manifest["raw_saved_matches_received_length"])
        self.assertTrue(manifest["raw_persistence_verified"])

    def test_identity_change_after_open_closes_before_start(self):
        clock=FakeClock();transport=FakeSerial(clock,valid_events())
        root=Path(self.temp.name);store=m.PrivateCapture(root/"capture",root)
        identities=iter([{"port":"synthetic-only","enumeration":1},{"port":"synthetic-only","enumeration":2}])
        with self.assertRaises(m.CaptureError):
            m.collect(store,SHA,65536,NONCE,lambda p:transport,lambda:next(identities),lambda:{},clock,clock.sleep)
        self.assertTrue(transport.closed)
        self.assertIsNone(transport.command)

    def test_unheld_lifecycle_lock_refuses_transport_open(self):
        root=Path(self.temp.name);store=m.PrivateCapture(root/"capture",root)
        calls=[]
        def denied():raise m.CaptureError("synthetic missing lock")
        with self.assertRaises(m.CaptureError):
            m.collect(store,SHA,65536,NONCE,lambda p:calls.append(p),lambda:{"port":"synthetic-only"},denied)
        self.assertEqual(calls,[])


class IdentityLockTests(unittest.TestCase):
    def test_inspection_of_inherited_flock_never_unlocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"operator.lock"
            fd=os.open(path,os.O_CREAT|os.O_RDWR,0o600)
            other=os.open(path,os.O_RDWR)
            try:
                with self.assertRaises(m.CaptureError):m.inherited_operator_lock(fd,path)
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertIn("did not acquire",m.inherited_operator_lock(fd,path)["ownership"])
                with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
                link=Path(tmp)/"alias";link.symlink_to(path)
                with self.assertRaises(m.CaptureError):m.inherited_operator_lock(fd,link)
            finally:os.close(other);os.close(fd)

    def test_identity_exact_topology_product_and_tty_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);usb=root/"bus/usb/devices/3-3";usb.mkdir(parents=True)
            for name,value in {"idVendor":"cafe","idProduct":"4011","product":m.PRODUCT,"busnum":"3","devnum":"7"}.items():(usb/name).write_text(value)
            interface=usb/"3-3:1.0";interface.mkdir()
            tty=root/"class/tty/ttyACM9";tty.mkdir(parents=True);(tty/"device").symlink_to(interface)
            port=root/"ttyACM9";port.touch()
            self.assertEqual(m.select_diagnostic("3-3",port,root,False)["product"],m.PRODUCT)
            with self.assertRaises(m.CaptureError):m.select_diagnostic("3-4",port,root,False)
            (usb/"product").write_text("foreign project")
            with self.assertRaises(m.CaptureError):m.select_diagnostic("3-3",port,root,False)
            (usb/"product").write_text(m.PRODUCT)
            foreign=root/"foreign";foreign.mkdir();(foreign/"idVendor").write_text("cafe")
            (tty/"device").unlink();(tty/"device").symlink_to(foreign)
            with self.assertRaises(m.CaptureError):m.select_diagnostic("3-3",port,root,False)


if __name__ == "__main__":unittest.main()

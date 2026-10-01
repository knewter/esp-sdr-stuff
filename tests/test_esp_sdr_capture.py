import importlib.util
from pathlib import Path
import struct
import sys
import unittest
import zlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import esp_sdr_capture as capture
from esp_sdr_spectrum_bridge import spectrum_frame

class Port:
    def __init__(self,data,chunk=7):self.data=bytearray(data);self.chunk=chunk;self.writes=[]
    def write(self,data):self.writes.append(data);return len(data)
    def flush(self):pass
    def read(self,n):
        n=min(n,self.chunk,len(self.data));v=bytes(self.data[:n]);del self.data[:n];return v
    def read_until(self,terminator,size):
        out=bytearray()
        while len(out)<size:
            v=self.read(1)
            if not v:break
            out.extend(v)
            if out.endswith(terminator):break
        return bytes(out)

class ProtocolTests(unittest.TestCase):
    def test_fragmented_capture_crc_and_binary_newlines(self):
        payload=bytes(range(256))*2
        p=Port(f'DATA 256 {zlib.crc32(payload):08x} 4\n'.encode()+payload+b'OK\n')
        raw,result=capture.capture(p,256,80000000,8)
        self.assertEqual(raw,payload);self.assertTrue(result['crc_ok']);self.assertEqual(capture.line(p),'OK')
        self.assertEqual(p.writes,[b'CAP16 256 0\n'])
    def test_crc_failure_is_counted(self):
        raw,result=capture.capture(Port(b'DATA 256 00000000 4\n'+b'x'*512),256,16000000,8)
        self.assertFalse(result['crc_ok'])
    def test_short_payload_is_failure(self):
        with self.assertRaises(TimeoutError):capture.capture(Port(b'DATA 256 00000000 4\nshort'),256,40000000,8)
    def test_count_mismatch_is_not_silently_accepted(self):
        payload=b'x'*514
        _,result=capture.capture(Port(f'DATA 257 {zlib.crc32(payload):08x} 4\n'.encode()+payload),256,80000000,8)
        self.assertFalse(result['sample_count_ok'])
    def test_error_reply_rejected(self):
        with self.assertRaises(capture.ProtocolError):capture.command(Port(b'ERR capture_timeout\n'),'CAP16 256 0')
    def test_odd_10bit_packing(self):
        values=[(-512,511),(-1,0),(17,-22)]
        packed=sum(((i&1023)|((q&1023)<<10))<<(20*k) for k,(i,q) in enumerate(values)).to_bytes(8,'little')
        iq=capture.unpack(packed,3,10)
        np.testing.assert_array_equal(iq,[-512+511j,-1+0j,17-22j])
    def test_8bit_signed_codes(self):
        np.testing.assert_array_equal(capture.unpack(bytes([128,127,255,0]),2,8),[-128+127j,-1+0j])
    def test_exact_signed_endpoints(self):
        stats=capture.numerical_stats(bytes([128,127,129,126]),2,8)
        self.assertEqual(stats['component_endpoint_fraction'],.5)
    def test_spectrum_frame_crc_shape(self):
        bins=256;raw=bytearray(28+bins);raw[:4]=b'SPC1';raw[26]=8;raw[27]=2;raw[22]=8
        raw[8:16]=(100).to_bytes(8,'little');raw[20:22]=(1).to_bytes(2,'little')
        raw+=zlib.crc32(raw).to_bytes(4,'little')
        frame,_=spectrum_frame(Port(raw),bins)
        self.assertEqual(frame['sample_index'],100);self.assertEqual(len(frame['power_codes']),bins)
        raw[44]^=1
        with self.assertRaises(capture.ProtocolError):spectrum_frame(Port(raw),bins)
    def test_spectrum_end_status_retained(self):
        f,_=spectrum_frame(Port(b'SPECEND 7 1 2 3 4 5 6 7 8 9 10 11\n'),256)
        self.assertEqual(f['report'][0],7)


class StartupSynchronizationTests(unittest.TestCase):
    class Clock:
        def __init__(self):self.now=0
        def monotonic(self):return self.now
        def monotonic_ns(self):return int(self.now*1e9)
    class StartupPort(Port):
        def __init__(self,clock,lost_requests=2,delay=.4,silent=False):
            super().__init__(b'\xffboot startup\r\n',chunk=5)
            self.clock=clock;self.lost_requests=lost_requests;self.delay=delay
            self.silent=silent;self.pending=[];self.timeout=3;self.sync_writes=0
        def write(self,data):
            super().write(data)
            request=data.strip()
            if request.startswith(b'SYNC '):
                self.sync_writes+=1
                if self.sync_writes>self.lost_requests and not self.silent:
                    self.pending.append((self.clock.now+self.delay,request+b'\r\n'))
            elif request==b'INFO':
                self.data.extend(b'ESP32SDR 6 burst 16380\n')
            return len(data)
        def read(self,n):
            self.clock.now+=min(self.timeout,.025)
            while self.pending and self.pending[0][0]<=self.clock.now:
                _,reply=self.pending.pop(0);self.data.extend(reply)
            return super().read(n)
    def test_boot_loses_requests_then_fence_drains_retries(self):
        from unittest.mock import patch
        clock=self.Clock();port=self.StartupPort(clock)
        with patch.object(capture.time,'monotonic',clock.monotonic),patch.object(capture.time,'monotonic_ns',clock.monotonic_ns):
            capture.synchronize(port,seconds=5)
        self.assertGreaterEqual(port.sync_writes,4)
        self.assertEqual(port.pending,[])
        self.assertEqual(port.data,bytearray())
        self.assertEqual(port.timeout,3)
        self.assertEqual(capture.command(port,'INFO'),'ESP32SDR 6 burst 16380')
    def test_silent_boot_deadline_restores_timeout(self):
        from unittest.mock import patch
        clock=self.Clock();port=self.StartupPort(clock,silent=True)
        with patch.object(capture.time,'monotonic',clock.monotonic),patch.object(capture.time,'monotonic_ns',clock.monotonic_ns):
            with self.assertRaises(TimeoutError):capture.synchronize(port,seconds=1)
        self.assertLessEqual(clock.now,1.025)
        self.assertEqual(port.timeout,3)
        self.assertGreaterEqual(port.sync_writes,3)

if __name__=='__main__':unittest.main()

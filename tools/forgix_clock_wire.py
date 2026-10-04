"""Strict finite clock wire codec. No devices, calibration or admission."""
import struct
import zlib
from forgix_clock_observer import ratio_interval

def identity(value, length):
    if type(value) is not bytes or len(value)!=length or not any(value):
        raise ValueError('Exact nonzero binary identity required')
    return value

def command(nonce, build, image):
    p=bytearray(128);p[:6]=b'FGCQ\1\1'
    p[8:24]=identity(nonce,16);p[24:56]=identity(build,32);p[56:88]=identity(image,32)
    struct.pack_into('<I',p,124,zlib.crc32(p[:124]))
    return bytes(p)

def result(raw,nonce,build,image):
    if type(raw) is not bytes or len(raw)!=512 or raw[:8]!=b'FGCR\1\1\0\0':
        raise ValueError('Complete clock result envelope required')
    if raw[8:24]!=identity(nonce,16) or raw[24:56]!=identity(build,32) or raw[56:88]!=identity(image,32):
        raise ValueError('Clock result identity differs')
    if zlib.crc32(raw[:508])!=struct.unpack_from('<I',raw,508)[0] or any(raw[236:508]):
        raise ValueError('Clock result CRC/reserved bytes')
    config,status,count=struct.unpack_from('<3I',raw,88)
    samples=list(struct.unpack_from('<16I',raw,100));times=struct.unpack_from('<8Q',raw,164)
    cleanup,attempted=struct.unpack_from('<2I',raw,228)
    if config>5 or status>5 or count>16 or cleanup>1 or attempted>1 or any(samples[count:]):
        raise ValueError('Clock result typed status/sample range')
    boot,request,begin,end,capture,finished,encoded,drain=times
    if not boot<=request<boot+30_000_000 or not request<=encoded<boot+120_000_000 or drain!=min(encoded+2_000_000,boot+120_000_000):
        raise ValueError('Clock result immutable lifetime')
    if attempted:
        if not request<=begin<=end<=encoded or end>=min(begin+20_000_000,boot+30_000_000) and status==0:
            raise ValueError('Clock configuration timestamps')
    elif begin or end or count or config==0:
        raise ValueError('Clock configuration never attempted')
    if count or capture or finished:
        if not end<=capture<=finished<=encoded or finished>=min(capture+2_000_000,boot+120_000_000) and status==0:
            raise ValueError('Clock capture timestamps')
    if status==0 and (config!=0 or count!=16 or cleanup!=1 or attempted!=1):
        raise ValueError('Clock successful status contradicts observed work')
    out={'configuration_status':config,'observer_status':status,'sample_count':count,
         'decrements':samples[:count],'timestamps_us':dict(zip(('boot','request','configuration_begin','configuration_end','capture_begin','capture_end','encoded','drain_deadline'),times)),
         'cleanup_verified':bool(cleanup),'configuration_attempted':bool(attempted),
         'physical_timing_qualified':False,'calibrated_absolute_frequency':False}
    if status==0:out['digital_ratio']=ratio_interval(samples)
    return out

import ctypes,json,os
class Control(ctypes.Structure):
    _fields_=[('request_type',ctypes.c_ubyte),('request',ctypes.c_ubyte),('value',ctypes.c_ushort),('index',ctypes.c_ushort),('length',ctypes.c_ushort),('timeout_ms',ctypes.c_uint),('data',ctypes.c_void_p)]
assert ctypes.sizeof(Control)==24
libc=ctypes.CDLL(None,use_errno=True)
libc.ioctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_void_p]
libc.ioctl.restype=ctypes.c_int
out=[]
for path,typ in (('/dev/esp-hub-usb2',0x29),('/dev/esp-hub-usb3',0x2a)):
    data=ctypes.create_string_buffer(255)
    # The only transfer is GET_DESCRIPTOR, IN direction, class-device request.
    transfer=Control(0xa0,6,typ<<8,0,255,1000,ctypes.cast(data,ctypes.c_void_p))
    assert transfer.request_type & 0x80 and transfer.request==6
    fd=os.open(path,os.O_RDWR|os.O_CLOEXEC)
    try:count=libc.ioctl(fd,0xc0185500,ctypes.byref(transfer))
    finally:os.close(fd)
    if count<0:raise OSError(ctypes.get_errno(),'read-only hub GET_DESCRIPTOR failed')
    raw=data.raw[:count]
    expected_length=9 if typ==0x29 else 12
    assert len(raw)==expected_length and raw[0]==expected_length and raw[1]==typ and raw[2]==4
    chars=int.from_bytes(raw[3:5],'little')
    out.append({'device_scope':path,'request':'GET_DESCRIPTOR (IN/class/device)','descriptor_type':typ,'returned_bytes':count,'descriptor_hex':raw.hex(),'hub_ports':raw[2],'hub_characteristics_hex':f'0x{chars:04x}','logical_power_switching_mode':{0:'ganged',1:'individual',2:'none',3:'reserved'}[chars&3],'power_on_delay_ms':raw[5]*2,'electrical_power_removal_measured':False})
print(json.dumps({'read_only_control_transfers':True,'no_port_state_changed':True,'hubs':out},indent=2))

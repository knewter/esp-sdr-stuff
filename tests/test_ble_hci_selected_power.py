"""Actual HCI v1 acknowledgements, compatibility/redaction and pcap chunks."""
from pathlib import Path
import sys,struct,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ble_hci_monitor import sanitized_packet
from ble_dumpcap_monitor import MonitorPcap
from ble_direct_hci_source import parse_event

def ack(power=0,status=0,opcode=0x2036,extra=b'',omit=False):
    payload=bytes([1])+struct.pack('<H',opcode)+bytes([status])
    if not omit:payload+=struct.pack('b',power)
    payload+=extra;return bytes([14,len(payload)])+payload

def kernel(event):return struct.pack('<HHH',3,0,len(event))+event

class SelectedPower(unittest.TestCase):
    def test_every_selected_signed_byte_native_monitor_agreement(self):
        for power in range(-128,128):
            wire=ack(power);actual=sanitized_packet(kernel(wire))
            with self.subTest(power=power):
                if -127<=power<=20:
                    self.assertEqual(actual,{'kind':'advertising_command_complete','hci_opcode_hex':'2036','status':0,'controller_selected_tx_power_dbm':power})
                    native=parse_event(b'\x04'+wire,1)
                    self.assertEqual(native['controller_selected_tx_power_dbm'],actual['controller_selected_tx_power_dbm'])
                else:self.assertIsNone(actual)
    def test_strict_success_length_and_failed_return_envelope(self):
        for event in [ack(omit=True),ack(extra=b'\x00'),ack(extra=b'\x00\x00')]:
            self.assertIsNone(sanitized_packet(kernel(event)))
        self.assertEqual(sanitized_packet(kernel(ack(status=12,omit=True))),{'kind':'advertising_command_complete','hci_opcode_hex':'2036','status':12})
        for power in (-128,-7,127):
            self.assertEqual(sanitized_packet(kernel(ack(power=power,status=12))),{'kind':'advertising_command_complete','hci_opcode_hex':'2036','status':12})
        self.assertIsNone(sanitized_packet(kernel(ack(status=12,extra=b'\x00'))))
    def test_actual_truncation_and_wrong_controller_refused(self):
        frame=kernel(ack(-6))
        for end in range(len(frame)):self.assertIsNone(sanitized_packet(frame[:end]))
        bad=bytearray(frame);bad[2]=1;self.assertIsNone(sanitized_packet(bytes(bad)))
    def test_other_ack_shapes_stay_unchanged_without_power(self):
        for opcode in [0x2006,0x2008,0x200a,0x2037,0x2039,0x203c]:
            for extra in [b'',b'PRIVATE-RETURN']:
                result=sanitized_packet(kernel(ack(opcode=opcode,omit=True,extra=extra)))
                self.assertEqual(result,{'kind':'advertising_command_complete','hci_opcode_hex':f'{opcode:04x}','status':0})
                self.assertNotIn('PRIVATE',str(result))
    def test_chunked_DLT254_selected_power_no_raw_payload(self):
        event=ack(-17);packet=struct.pack('>HH',0,3)+event
        payload=bytes.fromhex('d4c3b2a1')+struct.pack('<HHIIII',2,4,0,0,65539,254)+struct.pack('<IIII',1,2,len(packet),len(packet))+packet
        for step in [1,2,3,7,31,65536]:
            p=MonitorPcap();records=[]
            for i in range(0,len(payload),step):records+=p.feed(payload[i:i+step])
            p.finish();self.assertEqual(len(records),1)
            self.assertEqual(records[0]['controller_selected_tx_power_dbm'],-17)
            self.assertNotIn('payload',records[0]);self.assertNotIn('address',str(records[0]))
if __name__=='__main__':unittest.main()

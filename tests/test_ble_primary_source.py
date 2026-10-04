"""Primary-header source preparation: no devices/Docker, strict separate mode."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ble_direct_hci_source as source
import ble_source_container as container
from test_ble_direct_hci_source import FakeSocket

ARGS=['--handle','1','--interval-ms','20','--events','100','--duration-ms','5000',
      '--start-delay','0','--extended-mode-diagnostic','--primary-zero-data-diagnostic']


class PrimarySourceTests(unittest.TestCase):
    def test_zero_data_complete_fragment_wire_and_original_default(self):
        self.assertEqual(source.advertising_data(1,True),bytes.fromhex('01030100'))
        self.assertEqual(source.advertising_data(1),bytes.fromhex('01030110')+source.OWNED_AD)
        self.assertEqual(source.parameters(20,1,True)[1:3],bytes(2))
        self.assertEqual(source.enable(True,100,5000,1),bytes.fromhex('010101f40164'))

    def test_profile_validation_rejects_legacy_and_wrong_fields_before_commands(self):
        options=dict(interval_ms=20,count=100,start_delay=0,duration_ms=5000,handle=1,
                     unlimited_events=False,extended=True,zero_data=True)
        for kwargs in [dict(extended=False),dict(count=255),dict(count=True),dict(handle=239),
                       dict(duration_ms=0),dict(interval_ms=100),dict(unlimited_events=True),dict(zero_data=1)]:
            sock=FakeSocket()
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                source.Source(sock,lambda record:None).run(**dict(options,**kwargs))
            self.assertEqual(sock.sent,[])

    def test_actual100_termination_and_cleanup_with_empty_data(self):
        sock=FakeSocket(termination=bytes.fromhex('043e06124301ffff64'))
        records=[]
        result=source.Source(sock,records.append).run(20,100,0,5000,1,False,True,True)
        self.assertEqual(result['status'],'controller_count_verified')
        self.assertTrue(result['primary_zero_data_diagnostic_requested'])
        self.assertEqual(result['advertising_data_length'],0)
        self.assertTrue(result['cleanup_success'])
        self.assertIsNone(result['independently_observed_air_emission_count'])
        self.assertEqual(sock.sent[1],bytes.fromhex('0137200401030100'))
        self.assertEqual(sock.sent[-2][4:],bytes.fromhex('000101000000'))
        self.assertEqual(sock.sent[-1][4:],b'\x01')

    def test_duration_zero_wrong_count_missing_and_duplicate_termination_fail(self):
        for term in [bytes.fromhex('043e06123c01ffff00'),bytes.fromhex('043e06124301ffff63'),None]:
            clock=[0.]
            class AdvanceOnEmpty(FakeSocket):
                def recv(self,size):
                    if not self.pending:clock[0]+=30
                    return super().recv(size)
            sock=AdvanceOnEmpty(termination=term)
            with patch.object(source.time,'monotonic',lambda:clock[0]):
                result=source.Source(sock,lambda record:None).run(20,100,0,5000,1,False,True,True)
            self.assertEqual(result['status'],'trial_failed')
            self.assertFalse(result['controller_completed_count_verified'])
            self.assertTrue(result['cleanup_success'])
        sock=FakeSocket(termination=bytes.fromhex('043e06124301ffff64'),duplicate=True)
        result=source.Source(sock,lambda record:None).run(20,100,0,5000,1,False,True,True)
        self.assertEqual(result['status'],'trial_failed')
        self.assertTrue(result['cleanup_success'])

    def test_public_configuration_does_not_claim_manufacturer_or_primary_ownership(self):
        sock=FakeSocket(termination=bytes.fromhex('043e06124301ffff64'))
        output=io.StringIO()
        with patch.object(sys,'argv',['source',*ARGS]),patch.object(source.socket,'socket',return_value=sock),patch.object(source,'bind_raw'),redirect_stdout(output):
            self.assertEqual(source.main(),0)
        configuration=json.loads(output.getvalue().splitlines()[0])
        self.assertEqual(configuration['advertising_data_length'],0)
        self.assertFalse(configuration['owned_manufacturer_ad_exact_match'])
        self.assertFalse(configuration['primary_header_ownership_observed'])
        self.assertEqual(configuration['source_profile'],'extended-primary-zero-data-v1')
        self.assertIsNone(configuration['independently_observed_air_emission_count'])
        self.assertTrue(sock.closed)

    def test_wrapper_passes_profile_and_rejects_incomplete_mode_before_docker(self):
        with patch.object(container.subprocess,'run') as run:
            self.assertTrue(container.validate_options(ARGS).primary_zero_data_diagnostic)
            with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                container.validate_options(['--primary-zero-data-diagnostic'])
            run.assert_not_called()
        command=container.source_command('esp-sdr-ble-source-'+'a'*32,'sha256:'+'b'*64,
             '/nix/store/synthetic/bin/python3',ARGS)
        self.assertEqual(command[-len(ARGS):],ARGS)


if __name__=='__main__':unittest.main()

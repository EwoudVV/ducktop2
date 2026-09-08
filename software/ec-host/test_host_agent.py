import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('agent',Path(__file__).with_name('host_agent.py'))
agent=importlib.util.module_from_spec(spec); spec.loader.exec_module(agent)
class HostTests(unittest.TestCase):
    def test_report_and_limits(self):
        wire=bytearray(64); wire[:4]=b'DT2\1'; struct.pack_into('<I',wire,4,8); struct.pack_into('<I',wire,36,30000)
        report=agent.decode_report(wire)
        packet=agent.encode_ack(report,25000,5000,0)
        self.assertEqual(struct.unpack_from('<I',packet,4)[0],8)
        with self.assertRaises(ValueError): agent.encode_ack(report,30001,0,0)
        packet=agent.encode_ack(report,25000,5000,128,0x65)
        self.assertEqual(packet[28],0x65)
        self.assertEqual(struct.unpack_from('<I',packet,20)[0],128)
        self.assertEqual(packet[29:],bytes(35))
        with self.assertRaises(ValueError): agent.encode_ack(report,25000,0,0,128)
        with self.assertRaises(ValueError): agent.encode_ack(report,25000,0,256)
        with self.assertRaises(ValueError): agent.decode_report(wire[:63])
    def test_real_sysfs_write_readback_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); power=root/'rapl'; light=root/'light'; power.mkdir(); light.mkdir()
            for i,name in enumerate(('long_term','short_term')):
                (power/f'constraint_{i}_name').write_text(name)
                (power/f'constraint_{i}_power_limit_uw').write_text('45000000')
            (power/'enabled').write_text('0')
            for name,value in {'max_brightness':100,'brightness':80,'bl_power':0}.items(): (light/name).write_text(str(value))
            p=dict(qualified=True,evidence='fixture only',powercap_path=str(power),backlight_path=str(light),
                   mu_non_package_mw=5000,display_max_mw=5000,package_max_mw=15000,package_min_mw=5000,brightness_ceiling=70)
            self.assertEqual(agent.apply_limits(p,22000,True),22000)
            self.assertEqual((power/'constraint_1_power_limit_uw').read_text(),'12000000')
            self.assertEqual((light/'bl_power').read_text(),'4')
            p['qualified']=False
            with self.assertRaises(ValueError): agent.apply_limits(p,22000,False)
if __name__=='__main__': unittest.main()

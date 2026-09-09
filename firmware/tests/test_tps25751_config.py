#!/usr/bin/env python3
"""Reject independently chosen policy and image failures on both ports."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]/'tps25751a'
spec=importlib.util.spec_from_file_location('pd_config',ROOT/'verify_config.py')
pd=importlib.util.module_from_spec(spec);spec.loader.exec_module(pd)

class PortConfigTests(unittest.TestCase):
    def source(self,port='PD1'):
        return json.loads((ROOT/f'ducktop2_{port.lower()}_config.json').read_text())
    def check_bad(self,reg,offset,value,port='PD1'):
        source=self.source(port);pd.register_map(source)[reg][offset]=value;errors=[]
        pd.verify_policy(source,'mutated',errors,port);self.assertTrue(errors)
    def test_both_actual_sources(self):
        for port in ('PD1','PD2'):
            errors=[];pd.verify_policy(self.source(port),port,errors,port);self.assertEqual(errors,[])
        self.assertEqual(pd.verify_release(),[])
    def test_images_cannot_exchange_ports(self):
        errors=[];pd.verify_policy(self.source('PD1'),'wrong right',errors,'PD2');self.assertTrue(errors)
        errors=[];pd.verify_policy(self.source('PD2'),'wrong left',errors,'PD1');self.assertTrue(errors)
    def test_reject_5a_sink(self):self.check_bad(0x33,13,0xf4)
    def test_reject_fifth_sink(self):self.check_bad(0x33,0,5)
    def test_reject_3a_source(self):self.check_bad(0x32,3,0x2c)
    def test_reject_second_source(self):self.check_bad(0x32,0,2)
    def test_reject_dual_role_data(self):self.check_bad(0x32,6,6)
    def test_reject_device_swap(self):self.check_bad(0x29,1,0xd1)
    def test_reject_advertised_rp_3a(self):self.check_bad(0x29,0,0x72)
    def test_reject_pphv_source(self):self.check_bad(0x27,2,1)
    def test_reject_vconn_limit_change(self):self.check_bad(0x27,1,1)
    def test_reject_wrong_sink_pdp(self):self.check_bad(0x7e,10,45)
    def test_reject_duplicate_register(self):
        source=self.source();entries=source['configuration']['data']['selected_ace'];entries.append(copy.deepcopy(entries[0]))
        with self.assertRaises(ValueError):pd.register_map(source)
    def test_vif_rejects_unsupported_paths(self):
        for tag,value in [('USB4_Supported','true'),('Type_C_Can_Act_As_Device','true'),
                          ('Modal_Operation_Supported_SOP','true'),('Host_Speed','4')]:
            tree=ET.parse(ROOT/'ducktop2_pd1_vif.xml');pd.xml_value(tree.getroot(),tag).set('value',value)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'mutant.xml';tree.write(path);errors=[];pd.verify_vif(path,errors)
                self.assertTrue(errors,tag)
    def test_c_array_must_equal_binary(self):
        with tempfile.TemporaryDirectory() as folder:
            c=Path(folder)/'x.c';b=Path(folder)/'x.bin';b.write_bytes(bytes([0,128,255]))
            c.write_text('const char image[] = {0x00,0x80,0xff};');errors=[]
            pd.verify_c_array(c,b,errors);self.assertEqual(errors,[])
            c.write_text('const char image[] = {0x00,0x81,0xff};');errors=[]
            pd.verify_c_array(c,b,errors);self.assertTrue(errors)
    def test_binary_requires_whole_record(self):
        source=self.source();regs=pd.register_map(source)
        image=b''.join(bytes([15,r,0,len(regs[r])-1])+bytes(regs[r]) for r in pd.BINARY_REGISTERS)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test_lowRegion.bin';path.write_bytes(image);errors=[]
            pd.verify_binary_registers(path,source,errors);self.assertEqual(errors,[])
            # Same register payload at the wrong write address must fail.
            broken=bytearray(image);broken[1]^=1;path.write_bytes(broken);errors=[]
            pd.verify_binary_registers(path,source,errors);self.assertTrue(errors)

if __name__=='__main__':unittest.main()

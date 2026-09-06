"""Regression cases for physical pad comparisons and the 5.10 V rail check."""
import unittest
import xml.etree.ElementTree as ET
from report_schematic_pcb_eco import compare
from verify_electrical_calculations import system_5v_checks


def schematic(pins, excluded=False):
    root=ET.Element('export');components=ET.SubElement(root,'components');comp=ET.SubElement(components,'comp',ref='R1')
    ET.SubElement(comp,'value').text='1k';ET.SubElement(comp,'footprint').text='Resistor_SMD:R_0603'
    if excluded:ET.SubElement(comp,'property',name='exclude_from_board')
    nets=ET.SubElement(root,'nets')
    for n,(pin,name) in enumerate(pins):
        net=ET.SubElement(nets,'net',code=str(n),name=name);ET.SubElement(net,'node',ref='R1',pin=pin)
    return root


def board(pads):
    return '(kicad_pcb (footprint "Resistor_SMD:R_0603" (property "Reference" "R1") (property "Value" "1k") '+''.join(
        f'(pad "{pin}" smd rect (layers "F.Cu" "F.Mask") (net "{net}") (uuid "{n}"))'
        for n,(pin,net) in enumerate(pads))+'))'


class BoardParity(unittest.TestCase):
    def test_every_repeated_pad_is_checked(self):
        result=compare(board([('1','GND'),('1','wrong')]),schematic([('1','GND')]))
        self.assertEqual(len(result['pad_net_changes']),1)
        self.assertEqual(result['pad_net_changes'][0]['uuid'],'1')
        self.assertFalse(result['passed'])

    def test_xml_encoding_is_not_silently_accepted(self):
        result=compare(board([('1','/Power &amp; Battery/VIN')]),schematic([('1','/Power & Battery/VIN')]))
        self.assertTrue(result['pad_net_changes'][0]['xml_encoding_only'])
        self.assertFalse(result['passed'])
        self.assertTrue(compare(board([('1','/Power & Battery/VIN')]),schematic([('1','/Power & Battery/VIN')]))['passed'])

    def test_excluded_component_on_board_is_reported(self):
        result=compare(board([('1','GND')]),schematic([('1','GND')],excluded=True))
        self.assertEqual(result['extra_components'],['R1'])

    def test_missing_physical_pin_is_reported(self):
        result=compare(board([('1','GND')]),schematic([('1','GND'),('2','VCC')]))
        self.assertEqual(result['missing_pin_pads'],[{'ref':'R1','pin':'2'}])

    def test_missing_values_do_not_pass(self):
        result=compare(board([('1','GND')]).replace('(property "Value" "1k")',''),schematic([('1','GND')]))
        self.assertEqual(len(result['value_changes']),1)

    def test_no_connect_names_are_not_live_nets(self):
        result=compare(board([('1','unconnected-(R1-Pad1)')]),schematic([('1','unconnected-(R1-Pad1)')]))
        self.assertTrue(result['passed'])

    def test_5v_target_update_keeps_hdmi_failure(self):
        checks=system_5v_checks(75000,10000)
        self.assertTrue(all(c.passed for c in checks[:3]))
        self.assertFalse(checks[3].passed)
        self.assertEqual(round(checks[3].value,6),4.757644)
        self.assertEqual(checks[3].low,4.8)

    def test_old_feedback_resistor_fails_current_target(self):
        self.assertFalse(system_5v_checks(76800,10000)[0].passed)


if __name__=='__main__':
    unittest.main()

"""Primary-drawing regressions for the USB5 inductor and long-terminal shunts."""
import unittest
from generate_usb5_passive_footprints import xgl1060_text, erj8cw_text, envelope


class USB5PassiveFootprintTests(unittest.TestCase):
    def test_coilcraft_marked_short_lead_is_switch_pad_one(self):
        text=xgl1060_text()
        self.assertIn('(pad "1" smd rect (at 3.325 0) (size 2.38 8.5)',text)
        self.assertIn('(pad "2" smd rect (at -3.325 0) (size 2.38 8.5)',text)
        self.assertIn('(start 4.5 -3.6) (end 4.5 3.6)',text)
        self.assertNotIn('(size 2.38 9)',text)

    def test_panasonic_land_uses_long_terminals(self):
        text=erj8cw_text()
        self.assertIn('(at -1.475 0) (size 1.75 1.8)',text)
        self.assertIn('(at 1.475 0) (size 1.75 1.8)',text)
        self.assertAlmostEqual(2*1.475-1.75,1.2)
        self.assertAlmostEqual(2*1.475+1.75,4.7)

    def test_mechanical_envelope_has_correct_vrml_units_and_height(self):
        text=envelope(10.5,11.8,6)
        self.assertIn('size 4.13385827 4.64566929 2.36220472',text)
        self.assertIn('translation 0 0 1.18110236',text)


if __name__=='__main__':unittest.main()

"""Pin and geometry regressions for the reviewed TI/Vishay library additions."""
import copy
import json
import re
import unittest

import genlib
from generate_lm706a0_library import DATA, footprint_text, symbol_text, validate_geometry, shunt_footprint_text


class LM706LibraryTests(unittest.TestCase):
    def test_electrical_pin_assignments_from_ti_table(self):
        symbol=genlib.extract_symbol_block(symbol_text(),"LM706A0")
        pins=genlib.parse_pins(symbol)
        self.assertEqual(set(pins),{str(i) for i in range(1,31)})
        for number,name in {"4":"CBOOT","5":"SW4","11":"ISNS+","12":"VOUT",
                            "15":"EXTCOMP","17":"AGND","18":"VDDA","19":"VCC",
                            "20":"SW1","23":"PGND1","30":"PGND"}.items():
            self.assertEqual(pins[number]['name'],name)

    def test_copper_pins_do_not_disappear_in_shared_lands(self):
        numbers=re.findall(r'\(pad "(\d+)"',footprint_text())
        self.assertEqual(len(numbers),30)
        self.assertEqual(set(numbers),{str(i) for i in range(1,31)})

    def test_stencil_and_exposed_metal_are_separate(self):
        data=json.loads(DATA.read_text())
        self.assertEqual(len(data['paste']),36)
        self.assertEqual(len(data['exposed_mask']),2)
        self.assertEqual(len(data['copper_under_mask']),2)
        self.assertIn('(at 0.0375 1.308) (size 3.125 1.584)',footprint_text())

    def test_self_crossing_is_rejected_before_kicad_load(self):
        data=copy.deepcopy(json.loads(DATA.read_text()))
        data['copper_under_mask'][0]=[(0,0),(1,1),(0,1),(1,0)]
        with self.assertRaisesRegex(ValueError,'self-crossing'):
            validate_geometry(data)

    def test_low_ohm_shunt_uses_vishay_lands(self):
        footprint=shunt_footprint_text()
        self.assertIn('(at -1.88 0) (size 2.36 3.05)',footprint)
        self.assertIn('(at 1.88 0) (size 2.36 3.05)',footprint)
        self.assertAlmostEqual(2*1.88-2.36,1.40)


if __name__=='__main__':unittest.main()

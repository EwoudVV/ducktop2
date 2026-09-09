import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_main_pcb_from_netlist as sync


SHEET = "11111111-1111-4111-8111-111111111111"
FIRST = "22222222-2222-4222-8222-222222222222"
SECOND = "33333333-3333-4333-8333-333333333333"


class NetlistUnitPaths(unittest.TestCase):
    def read_component(self, stamps):
        xml = f'''<export><components><comp ref="U1"><value>dual gate</value>
        <footprint>Package_TO_SOT_SMD:SOT-23-6</footprint>
        <sheetpath names="/" tstamps="/{SHEET}/"/><tstamps>{stamps}</tstamps>
        </comp></components><nets><net name="GND"><node ref="U1" pin="3"/></net></nets></export>'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "board.xml"
            path.write_text(xml)
            with patch.object(sync, "NETLIST", path):
                return sync.parse_netlist()["U1"]

    def block(self, path):
        return f'''(footprint "Package_TO_SOT_SMD:SOT-23-6"
          (layer "F.Cu") (at 10 10)
          (property "Reference" "U1" (at 0 -2) (layer "F.SilkS"))
          (property "Value" "dual gate" (at 0 2) (layer "F.Fab"))
          (path "{path}") (attr smd))'''

    def test_single_unit_keeps_a_valid_path(self):
        comp = self.read_component(FIRST)
        self.assertEqual(comp.path, f"/{SHEET}/{FIRST}")
        self.assertEqual(comp.pin_nets, {"3": "GND"})

    def test_multi_unit_export_produces_individual_paths(self):
        comp = self.read_component(f"{FIRST} {SECOND}")
        self.assertEqual(comp.path, f"/{SHEET}/{FIRST}")
        self.assertEqual(comp.unit_paths, (f"/{SHEET}/{FIRST}", f"/{SHEET}/{SECOND}"))
        self.assertNotIn(" ", comp.path)

    def test_valid_second_unit_link_is_preserved(self):
        comp = self.read_component(f"{FIRST} {SECOND}")
        current = f"/{SHEET}/{SECOND}"
        result = sync.update_metadata(self.block(current), comp)
        self.assertIn(f'(path "{current}")', result)

    def test_joined_or_stale_link_is_repaired(self):
        comp = self.read_component(f"{FIRST} {SECOND}")
        for current in (f"/{SHEET}/{FIRST} {SECOND}", "/old/path"):
            with self.subTest(current=current):
                result = sync.update_metadata(self.block(current), comp)
                self.assertIn(f'(path "{comp.path}")', result)

    def test_missing_or_invalid_uuid_is_rejected(self):
        for stamps in ("", "not-a-uuid", f"{FIRST} invalid"):
            with self.subTest(stamps=stamps), self.assertRaises(ValueError):
                self.read_component(stamps)


if __name__ == "__main__":
    unittest.main()

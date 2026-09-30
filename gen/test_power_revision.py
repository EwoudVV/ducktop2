"""Regression mutations against compact snapshots of native power netlists."""

from pathlib import Path
import unittest

from verify_electrical_calculations import component_values
from verify_power_revision import check


FIXTURES = Path(__file__).parent / "testdata/power_revision"
CAPS = ((0, "C2685"), (0, "C740"), (0, "C749"),
        (1, "C2682"), (1, "C2683"), (1, "C2684"),
        (2, "C2680"), (2, "C2681"))
FETS = ("Q2600", "Q2601", "Q2602", "Q2603", "Q2610", "Q2611")


class PowerRevisionContracts(unittest.TestCase):
    def setUp(self):
        self.boards = [component_values(FIXTURES / f"{name}.xml")
                       for name in ("center", "left", "right")]

    def assert_ref_fails(self, ref):
        self.assertTrue(any(f.startswith((ref + ":", ref + "."))
                            for f in check(*self.boards)["failures"]), ref)

    def test_reviewed_native_snapshot_passes(self):
        self.assertEqual(check(*self.boards)["failures"], [])

    def test_center_only_call_does_not_require_side_boards(self):
        self.assertEqual(check(self.boards[0])["failures"], [])

    def test_each_new_bypass_is_required(self):
        for board, ref in CAPS:
            with self.subTest(ref=ref):
                self.setUp()
                values = self.boards[board]
                del values[ref]
                del values.parts[ref]
                del values.pins[ref]
                self.assert_ref_fails(ref)

    def test_each_bypass_requires_both_supply_and_ground(self):
        for board, ref in CAPS:
            for pin in ("1", "2"):
                with self.subTest(ref=ref, pin=pin):
                    self.setUp()
                    self.boards[board].pins[ref][pin] = "/WRONG_RAIL"
                    self.assert_ref_fails(ref)

    def test_ic_supply_pins_cannot_move_off_the_bypass_rail(self):
        for board, ref, pins in ((0, "U15", ("10", "16")), (0, "U16", ("10",)),
                                 (2, "U55", ("1", "2", "4")),
                                 (2, "U2016", ("5",)), (1, "U2006", ("5",)),
                                 (1, "U1800", ("1",)), (1, "U1803", ("1",))):
            for pin in pins:
                with self.subTest(ref=ref, pin=pin):
                    self.setUp()
                    self.boards[board].pins[ref][pin] = "/WRONG_RAIL"
                    self.assert_ref_fails(ref)

    def test_same_capacitance_with_wrong_voltage_code_is_rejected(self):
        for board, ref in CAPS:
            with self.subTest(ref=ref):
                self.setUp()
                values = self.boards[board]
                mpn, footprint = values.parts[ref]
                values.parts[ref] = (mpn.replace("1H", "1C"), footprint)
                self.assert_ref_fails(ref)

    def test_bypass_label_and_population_must_match(self):
        for board, ref in CAPS:
            self.setUp()
            for value in ("1n 50V", "DNP " + self.boards[board][ref]):
                with self.subTest(ref=ref, value=value):
                    self.setUp()
                    self.boards[board][ref] = value
                    self.assert_ref_fails(ref)

    def test_bypass_package_cannot_shrink_to_0402(self):
        for board, ref in CAPS:
            with self.subTest(ref=ref):
                self.setUp()
                values = self.boards[board]
                values.parts[ref] = (values.mpn(ref), "Capacitor_SMD:C_0402_1005Metric")
                self.assert_ref_fails(ref)

    def test_all_six_fets_require_the_reviewed_dnh_footprint(self):
        for ref in FETS:
            with self.subTest(ref=ref):
                self.setUp()
                values = self.boards[0]
                values.parts[ref] = (values.mpn(ref), "Package_DFN_QFN:VSON-8-1EP_3.3x3.3mm")
                self.assert_ref_fails(ref)

    def test_all_six_fets_require_the_reviewed_mpn(self):
        for ref in FETS:
            with self.subTest(ref=ref):
                self.setUp()
                values = self.boards[0]
                values.parts[ref] = ("CSD18540Q5B", values.parts[ref][1])
                self.assert_ref_fails(ref)


if __name__ == "__main__":
    unittest.main()

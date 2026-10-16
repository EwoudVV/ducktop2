"""Regression mutations against compact snapshots of native power netlists."""

from pathlib import Path
import copy
import unittest

from verify_electrical_calculations import component_values
from verify_power_revision import check


FIXTURES = Path(__file__).parent / "testdata/power_revision"
CAPS = ((0, "C2685"), (0, "C740"), (0, "C749"),
        (0, "C2686"), (0, "C2687"), (0, "C2688"),
        (1, "C2682"), (1, "C2683"), (1, "C2684"),
        (2, "C2680"), (2, "C2681"))
FETS = ("Q2600", "Q2601", "Q2602", "Q2603", "Q2610", "Q2611")


def monitor_center_fixture():
    """New interface layered onto the independently captured power fixture."""
    center = component_values(FIXTURES / "center.xml")
    for ref in ("C2260", "R2260", "R2261", "R719", "U2210"):
        center.pop(ref, None)
        center.parts.pop(ref, None)
        center.pins.pop(ref, None)
    for ref, value, mpn, footprint, pins in (
        ("J2073", "isolated bms control", "SM05B-SRSS-TB(LF)(SN)",
         "Connector_JST:JST_SH_SM05B-SRSS-TB_1x05-1MP_P1.00mm_Horizontal",
         {"1":"/PACK_MONITOR_READY","2":"/I2C_SCL","3":"/MCU_3V3","4":"/I2C_SDA","5":"GND","MP":"GND"}),
        ("U44", "TCA9539PWR", "TCA9539PWR", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
         {"10":"/PACK_MONITOR_READY","13":"unconnected-(U44-IO1_0-Pad13)"}),
        ("TP10", "PACK_MONITOR_READY test", "", "TestPoint:TestPoint_Pad_D1.0mm",
         {"1":"/PACK_MONITOR_READY"}),
    ):
        center[ref] = value
        center.parts[ref] = (mpn, footprint)
        center.pins[ref] = pins
    center.pins["Q702"]["1"] = "/CHG_ENABLE"
    center.pins["R2262"]["1"] = "/CHG_ENABLE"
    center.pins["R2263"]["1"] = "/PACK_MONITOR_READY"
    center.pins["U2635"]["3"] = "unconnected-(U2635-IO2-Pad3)"
    return center


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
        for board, ref, pins in ((0, "U15", ("10", "15", "16")), (0, "U16", ("10", "14", "17")),
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

    def test_monitor_interface_passes_without_retired_parts(self):
        result = check(monitor_center_fixture())
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["bms_main_interface"], "bq76922-ready-i2c")

    def test_legacy_fixture_still_requires_thermal_permission(self):
        self.boards[0].pins["U2210"]["2"] = "/WRONG_PERMISSION"
        self.assert_ref_fails("U2210")

    def test_monitor_status_spelling_cannot_revert_to_alarm_or_fault(self):
        for ref, pin in (("J2073","1"),("U44","10"),("TP10","1"),("R2263","1")):
            for wrong in ("/PACK_ALARM_HEALTH","/PACK_FAULT_N"):
                with self.subTest(ref=ref, pin=pin, wrong=wrong):
                    center = monitor_center_fixture()
                    center.pins[ref][pin] = wrong
                    self.assertTrue(check(center)["failures"])

    def test_monitor_bus_and_return_are_literal(self):
        for pin, wrong in (("2","/I2C_SDA"),("4","/I2C_SCL"),("2","/PACK_I2C_SCL"),
                           ("3","/PACK_NEG_RAW"),("5","/FG_VSS"),("MP","/CTRL_GND")):
            with self.subTest(pin=pin, wrong=wrong):
                center = monitor_center_fixture()
                center.pins["J2073"][pin] = wrong
                self.assertTrue(check(center)["failures"])

    def test_monitor_nc_pins_cannot_be_old_permit_retry_or_ground(self):
        for ref, pin in (("U44","13"),("U2635","3")):
            for wrong in ("GND","/PACK_RETRY_PULSE","/Power & Battery/PACK_CHG_TEMP_OK_IN"):
                with self.subTest(ref=ref, pin=pin, wrong=wrong):
                    center = monitor_center_fixture()
                    center.pins[ref][pin] = wrong
                    self.assertTrue(check(center)["failures"])

    def test_monitor_direct_charge_request_cannot_reuse_thermal_and_output(self):
        for ref in ("Q702","R2262"):
            with self.subTest(ref=ref):
                center = monitor_center_fixture()
                center.pins[ref]["1"] = "/Power & Battery/CHG_ENABLE_THERM"
                self.assertTrue(check(center)["failures"])

    def test_monitor_removed_parts_cannot_reappear(self):
        legacy = component_values(FIXTURES / "center.xml")
        for ref in ("C2260","R2260","R2261","R719","U2210"):
            with self.subTest(ref=ref):
                center = monitor_center_fixture()
                center[ref] = legacy[ref]
                center.parts[ref] = legacy.parts[ref]
                center.pins[ref] = copy.deepcopy(legacy.pins[ref])
                self.assertTrue(any(f.startswith(ref + ":") for f in check(center)["failures"]))


if __name__ == "__main__":
    unittest.main()

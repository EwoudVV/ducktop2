"""Native BQ thermal, shutdown-source, probe, and fail-off regressions."""

import copy
from pathlib import Path
from types import SimpleNamespace
import unittest

import fpc_contract
import genlib
from generate_bms_controls import add_bms_controls
from generate_bms_guards import add_bms_guards
from generate_bms_support_library import library as support_library
from generate_bms_thermal import add_bms_thermal
from verify_bq76922_calculations import optional_storage_checks, supply_metrics
from verify_design_contracts import CheckFailure, expect_unconnected
from verify_electrical_calculations import component_values


FIXTURE = Path(__file__).resolve().parent / "testdata/bms_monitor.xml"


class Capture:
    def __init__(self):
        self.parts = {}

    def place(self, ref, symbol, value, x, y, **kwargs):
        if ref in self.parts:
            raise ValueError("duplicate reference " + ref)
        self.parts[ref] = {"symbol": symbol, "value": value, **kwargs}

    def text(self, *args):
        pass

    def pwrflag(self, *args):
        pass


def net(parts, ref, pin):
    return parts[ref]["pin_nets"][str(pin)][0]


def validate_native_thermal(parts):
    assert parts["R2200"]["extra_props"]["MPN"] == "RC2010FK-071KL"
    assert net(parts, "R2200", 1) == "PACK_POS_RAW"
    assert net(parts, "R2200", 2) == "THERM_RAW_PRE"
    assert parts["U2217"]["extra_props"]["MPN"] == "TPS22810DBVR"
    assert {pin: net(parts, "U2217", pin) for pin in (1, 2, 3, 5, 6)} == {
        1: "THERM_RAW_PRE", 2: "PACK_NEG_RAW", 3: "BQ_ALERT_AWAKE",
        5: "THERM_RAW_IN", 6: "THERM_RAW_IN",
    }
    assert net(parts, "R2290", 1) == "BQ_ALERT_AWAKE"
    assert net(parts, "R2290", 2) == "PACK_NEG_RAW"
    assert parts["R2290"]["extra_props"]["MPN"] == "RC0603FR-07390KL"
    assert net(parts, "C2281", 1) == "THERM_RAW_PRE"
    assert net(parts, "C2281", 2) == "PACK_NEG_RAW"
    assert net(parts, "C2200", 1) == "THERM_RAW_IN"
    assert net(parts, "U2200", 1) == "THERM_RAW_IN"
    assert net(parts, "U2200", 5) == "THERM_3V3"

    for cell in range(1, 4):
        sense = f"THERM_SENSE_{cell}"
        assert net(parts, f"R{2210 + 3 * (cell - 1)}", 1) == "THERM_3V3"
        assert net(parts, f"R{2210 + 3 * (cell - 1)}", 2) == sense
        assert net(parts, f"R{2211 + 3 * (cell - 1)}", 1) == sense
        assert net(parts, f"R{2211 + 3 * (cell - 1)}", 2) == f"THERM_PROBE_{cell}_A"
        assert net(parts, f"R{2212 + 3 * (cell - 1)}", 1) == f"THERM_PROBE_{cell}_B"
        assert net(parts, f"R{2212 + 3 * (cell - 1)}", 2) == "PACK_NEG_RAW"
        comparator = f"U{2200 + cell}"
        assert net(parts, comparator, 4) == "THERM_3V3"
        assert net(parts, comparator, 11) == "PACK_NEG_RAW"
        assert {net(parts, comparator, pin) for pin in (1, 7)} == {"THERM_CHG_HEALTH"}
        assert {net(parts, comparator, pin) for pin in (8, 14)} == {"THERM_DSG_HEALTH"}

    assert net(parts, "U2205", 1) == "BMS_PERMIT_READY"
    assert net(parts, "U2205", 7) == "BMS_PERMIT_READY"
    assert net(parts, "U2215", 1) == "THERM_READY"
    assert net(parts, "U2215", 2) == "CURRENT_READY"
    assert net(parts, "U2215", 4) == "BMS_PERMIT_READY"
    for q, gate_pull, off_pull, off_pin in (
        ("Q2200", "R2235", "R2236", "BMS_CFETOFF"),
        ("Q2201", "R2238", "R2239", "BMS_DFETOFF"),
    ):
        assert net(parts, q, 2) == "PACK_NEG_RAW"
        assert net(parts, q, 3) == off_pin
        assert net(parts, gate_pull, 2) == "PACK_NEG_RAW"
        assert net(parts, off_pull, 1) == "BMS_OFF_BIAS"
        assert net(parts, off_pull, 2) == off_pin
    assert net(parts, "D2220", 2) == "THERM_3V3"
    assert net(parts, "D2221", 2) == "BQ_REG1"
    assert net(parts, "D2220", 1) == net(parts, "D2221", 1) == "BMS_OFF_BIAS"


def validate_monitor_ready(parts):
    assert parts["U2208"]["extra_props"]["MPN"] == "SN74LVC1G17DBVR"
    assert net(parts, "U2208", 2) == "THERM_READY"
    assert net(parts, "U2208", 3) == "PACK_NEG_RAW"
    assert net(parts, "U2208", 4) == "BMS_MONITOR_READY_RAW"
    assert net(parts, "U2208", 5) == "BQ_REG1"
    assert net(parts, "R2251", 1) == "BMS_MONITOR_READY_RAW"
    assert net(parts, "R2251", 2) == "PACK_NEG_RAW"
    assert net(parts, "U2209", 3) == "BMS_MONITOR_READY_RAW"
    assert net(parts, "U2209", 6) == "CTRL_MONITOR_READY"
    assert net(parts, "R2258", 1) == "CTRL_MONITOR_READY"
    assert net(parts, "R2258", 2) == "PACK_MONITOR_READY"
    assert net(parts, "U2216", 3) == "PACK_MONITOR_READY"


class BmsThermalTests(unittest.TestCase):
    def setUp(self):
        capture = Capture()
        add_bms_thermal(capture)
        add_bms_guards(capture)
        add_bms_controls(capture)
        self.parts = capture.parts

    def test_native_temperature_storage_and_ready_contract(self):
        validate_native_thermal(self.parts)
        validate_monitor_ready(self.parts)
        self.assertEqual(fpc_contract.BMS_CONTROL_PINMAP[1], "PACK_MONITOR_READY")
        self.assertEqual(fpc_contract.BMS_CONTROL_PINMAP[5], "CTRL_GND")
        self.assertEqual(fpc_contract.BMS_CONTROL_CENTER_PINMAP[5], "GND")

    def test_tps22810_primary_pin_map_and_qod_tie(self):
        pins = genlib.parse_pins(genlib.extract_symbol_block(support_library(), "TPS22810DBV"))
        self.assertEqual({number: pins[number]["name"] for number in pins}, {
            "1": "VIN", "2": "GND", "3": "EN_UVLO", "4": "CT",
            "5": "QOD", "6": "VOUT",
        })
        self.assertEqual(net(self.parts, "U2217", 5), net(self.parts, "U2217", 6))
        self.assertEqual(net(self.parts, "U2217", 4), "")

    def test_shutdown_source_fault_mutations_are_rejected(self):
        mutations = [
            ("U2217", "3", "BQ_REG1"),
            ("R2290", "2", "THERM_RAW_IN"),
            ("U2217", "5", "THERM_RAW_PRE"),
            ("C2281", "1", "THERM_RAW_IN"),
        ]
        for ref, pin, wrong in mutations:
            with self.subTest(ref=ref, pin=pin):
                parts = copy.deepcopy(self.parts)
                parts[ref]["pin_nets"][pin] = (wrong, "local")
                with self.assertRaises(AssertionError):
                    validate_native_thermal(parts)

    def test_probe_open_short_and_return_mutations_are_rejected(self):
        mutations = [
            ("R2210", "2", "PACK_NEG_RAW"),
            ("R2211", "2", "PACK_NEG_RAW"),
            ("R2212", "2", "FG_VSS"),
            ("U2201", "1", "THERM_DSG_HEALTH"),
        ]
        for ref, pin, wrong in mutations:
            with self.subTest(ref=ref, pin=pin):
                parts = copy.deepcopy(self.parts)
                parts[ref]["pin_nets"][pin] = (wrong, "local")
                with self.assertRaises(AssertionError):
                    validate_native_thermal(parts)

    def test_reg1_loss_and_temperature_loss_fail_off_mutations_are_rejected(self):
        mutations = [
            ("U2215", "2", "THERM_3V3"),
            ("R2235", "2", "THERM_3V3"),
            ("R2236", "1", "BQ_REG1"),
            ("D2220", "2", "BQ_REG1"),
            ("Q2200", "3", "BMS_DFETOFF"),
        ]
        for ref, pin, wrong in mutations:
            with self.subTest(ref=ref, pin=pin):
                parts = copy.deepcopy(self.parts)
                parts[ref]["pin_nets"][pin] = (wrong, "local")
                with self.assertRaises(AssertionError):
                    validate_native_thermal(parts)

    def test_monitor_ready_cannot_revert_to_alarm_clear_semantics(self):
        for ref, pin, wrong in (
            ("U2208", "2", "BQ_ALERT_AWAKE"),
            ("R2251", "2", "CTRL_GND"),
            ("U2209", "3", "BQ_ALERT_AWAKE"),
            ("R2258", "2", "PACK_ALARM_HEALTH"),
        ):
            with self.subTest(ref=ref, pin=pin):
                parts = copy.deepcopy(self.parts)
                parts[ref]["pin_nets"][pin] = (wrong, "local")
                with self.assertRaises(AssertionError):
                    validate_monitor_ready(parts)

    def test_only_i2c_and_readiness_isolators_cross_raw_control_domains(self):
        raw = {"PACK_NEG_RAW", "BQ_REG1", "BMS_RAW_SCL", "BMS_RAW_SDA",
               "BMS_MONITOR_READY_RAW"}
        control = {"CTRL_GND", "CTRL_3V3", "ISO_CTRL_SCL", "ISO_CTRL_SDA",
                   "CTRL_MONITOR_READY", "PACK_MONITOR_READY"}
        spanning = []
        for ref, part in self.parts.items():
            nets = {entry[0] for entry in part["pin_nets"].values()} - {""}
            if nets & raw and nets & control:
                spanning.append(ref)
        self.assertEqual(sorted(spanning), ["U2206", "U2209"])
        self.assertEqual(net(self.parts, "J2200", "MP"), "PACK_NEG_RAW")

    def test_external_probes_and_both_lead_limits_remain_present(self):
        for cell in range(1, 4):
            probe = self.parts[f"TH{2200 + cell}"]
            self.assertFalse(probe["on_board"])
            self.assertEqual(probe["extra_props"]["MPN"], "104JT-025")
            self.assertEqual(net(self.parts, "J2200", 2 * cell - 1), f"THERM_PROBE_{cell}_A")
            self.assertEqual(net(self.parts, "J2200", 2 * cell), f"THERM_PROBE_{cell}_B")

    def test_canonical_numeric_fixture_includes_enabled_switch_draw(self):
        values = component_values(FIXTURE)
        supply = supply_metrics(values)
        self.assertGreater(supply["thermal_demand_A"], .0015)
        storage = optional_storage_checks(values)
        self.assertEqual(len(storage), 3)
        self.assertTrue(all(row.passed for row in storage))

    def test_exact_kicad_mounting_pad_no_connect_names(self):
        for name in ("unconnected-(J2072-PadMP)", "unconnected-(J2072-MountingPin-PadMP)"):
            expect_unconnected({"J2072": SimpleNamespace(pin_nets={"MP": name})}, "J2072", "MP")
        for name in ("GND", "/CTRL_GND", "unconnected-(J2072-Pad1)", None):
            with self.assertRaises(CheckFailure):
                expect_unconnected({"J2072": SimpleNamespace(pin_nets={"MP": name})}, "J2072", "MP")


if __name__ == "__main__":
    unittest.main()

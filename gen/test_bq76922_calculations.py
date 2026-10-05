"""Focused tests for the BQ76922 candidate numeric verifier."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from verify_bq76922_calculations import (
    PROFILE, bq76922_checks, charge_voltage_metrics, optional_storage_checks, render_bq76922_report, startup_metrics,
    supply_metrics, trip_envelopes,
)
from verify_electrical_calculations import component_values


NETLIST = Path(__file__).resolve().parent / "testdata/bms_monitor.xml"


class Bq76922CalculationTests(unittest.TestCase):
    def setUp(self):
        self.values = component_values(NETLIST)

    def test_current_candidate_passes_every_numeric_row(self):
        checks = bq76922_checks(self.values)
        self.assertGreaterEqual(len(checks), 40)
        self.assertTrue(all(check.passed for check in checks),
                        [(check.name, check.value, check.low, check.high)
                         for check in checks if not check.passed])
        expected_storage_rows = 3 if "U2217" in self.values else 0
        self.assertEqual(sum(check.name.startswith("optional storage") for check in checks),
                         expected_storage_rows)

    def test_signed_precision_guard_envelopes_match_selected_review(self):
        result = trip_envelopes(self.values)
        self.assertAlmostEqual(result["discharge_nominal_A"], 9.089848577235772)
        self.assertAlmostEqual(result["charge_nominal_A_signed"], -4.096549072164948)
        self.assertAlmostEqual(result["discharge_A"][0], 8.296582900315812)
        self.assertAlmostEqual(result["discharge_A"][1], 9.973094320055434)
        self.assertAlmostEqual(result["charge_A_signed"][0], -4.608431385916699)
        self.assertAlmostEqual(result["charge_A_signed"][1], -3.6364620700080232)
        self.assertAlmostEqual(result["discharge_all_stress_A"][0], 8.164505729012644)
        self.assertAlmostEqual(result["discharge_all_stress_A"][1], 10.154982589805675)
        self.assertAlmostEqual(result["charge_all_stress_A_signed"][0], -4.692479484144494)
        self.assertAlmostEqual(result["charge_all_stress_A_signed"][1], -3.5785715348890843)

    def test_low_common_mode_guarantee_is_separate_from_acceptance_allowance(self):
        result = trip_envelopes(self.values)
        self.assertAlmostEqual(result["guaranteed_low_cm_offset_V"], 333.15478672240097e-6)
        self.assertAlmostEqual(result["acceptance_offset_V"], 358.154786722401e-6)
        self.assertAlmostEqual(result["acceptance_offset_V"] - result["guaranteed_low_cm_offset_V"], 25e-6)

    def test_selected_silicon_shunt_and_filter_parts_are_mandatory(self):
        for ref, replacement in (
            ("U719", "BQ7791500PWR"),
            ("RS11", "CSS4J-4026K-5L00F"),
            ("U2210", "INA381A2IDGSR"),
            ("U2211", "INA381A3IDGSR"),
            ("U2213", "REF3420IDBVR"),
            ("R2280", "RC0603FR-074R99L"),
        ):
            with self.subTest(ref=ref):
                values = copy.deepcopy(self.values)
                values.parts[ref] = (replacement, values.parts[ref][1])
                with self.assertRaises(ValueError):
                    trip_envelopes(values)

    def test_regin_thermal_and_isolated_control_loads_are_real_netlist_values(self):
        result = supply_metrics(self.values)
        self.assertAlmostEqual(result["regin_feed_ohm"], 215.0)
        self.assertLess(result["reg1_selected_load_A"], .012)
        self.assertGreater(result["regin_input_at_8v4_V"], 5.5)
        self.assertGreater(result["thermal_input_at_8v4_V"], 4.6)
        self.assertGreater(result["thermal_demand_A"], .0015)
        self.assertGreater(result["isolated_control_load_A"], .019)
        self.assertLess(result["isolated_control_load_A"], .021)

    def test_tps26600_uses_selected_parallel_ilim_and_dvdt(self):
        result = startup_metrics(self.values)
        self.assertAlmostEqual(result["ilim_ohm"], 8000)
        self.assertAlmostEqual(result["current_A"][0], 1.4108910891089108)
        self.assertAlmostEqual(result["current_A"][1], 1.5909090909090908)
        self.assertAlmostEqual(result["cdvdt_F"], 100e-9)
        self.assertAlmostEqual(result["startup_time_s"], 0.014342191687196113)
        self.assertIn("no guaranteed maximum", result["timer_status"])

    def test_wrong_tps26600_network_is_rejected(self):
        values = copy.deepcopy(self.values)
        values["R888"] = "22k 0.1% 25ppm ILIM"
        values.parts["R888"] = ("TNPW060322K0BEEN", values.parts["R888"][1])
        with self.assertRaises(ValueError):
            startup_metrics(values)

    def test_storage_rows_are_optional_until_ecos_land(self):
        rows = optional_storage_checks(self.values)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.passed for row in rows))
        shutdown = next(row for row in rows if "shutdown EN" in row.name)
        self.assertAlmostEqual(shutdown.value, .45045)
        pre_eco = copy.deepcopy(self.values)
        for ref in ("U2217", "R2290", "C2281"):
            pre_eco.pop(ref, None)
            pre_eco.parts.pop(ref, None)
            pre_eco.pins.pop(ref, None)
        self.assertEqual(optional_storage_checks(pre_eco), [])

    def test_numeric_pass_cannot_override_profile_release_gate(self):
        profile = json.loads(PROFILE.read_text())
        profile["released_for_assembly"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(profile))
            with self.assertRaises(ValueError):
                bq76922_checks(self.values, path)

    def test_charge_corner_margin_and_taper_reachability(self):
        p = json.loads(PROFILE.read_text());r = charge_voltage_metrics(p)
        self.assertAlmostEqual(r["minimum_cov_margin_V"], .024)
        self.assertAlmostEqual(r["charge_ceiling_rise_room_V"], .0092)
        self.assertGreaterEqual(r["taper_min_measured_cell_V"]*1000, 3980)
        self.assertGreaterEqual(r["taper_min_measured_sum_V"]*1000, 12000)
        p["admission"]["charge_voltage_mv"] = 12528
        self.assertLess(charge_voltage_metrics(p)["minimum_cov_margin_V"], 0)
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"p.json";f.write_text(json.dumps(p))
            self.assertTrue(any(not c.passed for c in bq76922_checks(self.values,f)))

    def test_cv_dwell_metadata_is_cumulative_not_whole_session(self):
        p=json.loads(PROFILE.read_text())
        self.assertNotIn("session_max_ms",p["host_charge"])
        self.assertEqual(p["host_charge"]["cv_dwell_max_ms"],7200000)
        row=next(c for c in bq76922_checks(self.values) if c.name=="host cumulative qualified CV dwell")
        self.assertTrue(row.passed)
        self.assertIn("bulk and interruptions",row.equation)

    def test_charge_measurement_gate_cannot_be_enabled_by_numeric_pass(self):
        p=json.loads(PROFILE.read_text());p["termination_qualified"]=True
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"p.json";f.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError,"cannot qualify"):
                bq76922_checks(self.values,f)

    def test_candidate_report_does_not_carry_legacy_breaker_sources(self):
        report = render_bq76922_report(bq76922_checks(self.values), NETLIST)
        self.assertIn("BQ76922 Candidate", report)
        self.assertIn("INA381", report)
        self.assertNotIn("LTC4368", report)
        self.assertNotIn("BQ77915", report)


if __name__ == "__main__":
    unittest.main()

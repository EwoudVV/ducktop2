"""Regression tests for calculation gaps found in the independent audit."""
import math
from pathlib import Path
import tempfile
import unittest

from verify_electrical_calculations import (
    NetlistValues, buck_currents, boost_currents, capacitor_retention_required,
    component_values, direct_capacitance, divider_corners, left_5v_checks,
    procurement_checks, resistor, source_window_checks,
    lm706_checks, usb5_shunt_bounds,
)


def parts(*rows):
    values = NetlistValues()
    for ref, value, mpn in rows:
        values[ref] = value
        values.parts[ref] = (mpn, "Resistor_SMD:R_0603_1608Metric")
    return values


class ElectricalCalculationTests(unittest.TestCase):
    def lm_values(self, inductor="XAL7070-682MEC"):
        values=parts(("R1712","54.9k 0.1%","TNPU060354K9HZEN00"),
                     ("R1713","10.2k 0.1%","TNPU060310K2HZEN00"),
                     ("R1860","49.9k 0.1%","TNPU060349K9HZEN00"),
                     ("RS1860","5.6mOhm 1%","WSL20105L600FEA"),
                     ("L1701","6.8uH",inductor),
                     ("C1864","330u","T520X337M010ATE010"),
                     ("C1865","330u","T520X337M010ATE010"),
                     ("U1703","LM706A0RRXR","LM706A0RRXR"))
        return values

    def test_lm_divider_and_current_limit_corners(self):
        values=self.lm_values()
        self.assertAlmostEqual(left_5v_checks(values)[1].value,5.048744514468825)
        self.assertTrue(all(check.passed for check in lm706_checks(values)))

    def test_lm_old_inductor_loses_transient_current_margin(self):
        checks=lm706_checks(self.lm_values("XAL7070-332MEC"))
        headroom=next(check for check in checks if 'headroom' in check.name)
        self.assertFalse(headroom.passed)

    def test_usb5_parallel_shunt_life_temperature_and_layout_bounds(self):
        values=self.lm_values("XGL1060-682MEC")
        values.parts["R1712"]=("TNPU060355K6HZEN00",values.parts["R1712"][1])
        values["R1712"]="55.6k 0.1%"
        for ref in ("RS1860","RS1861"):
            values[ref]="10mOhm 1%"
            values.parts[ref]=("ERJ8CWFR010V","ducktop2:Panasonic_ERJ8CW_10to16m")
        values["R1860"]="22.1k 0.02%"
        values.parts["R1860"]=("TNPU060322K1HZEN00",values.parts["R1860"][1])
        nominal,low,high=usb5_shunt_bounds(values)
        self.assertAlmostEqual(nominal,.005)
        self.assertAlmostEqual(low,.00469483)
        self.assertAlmostEqual(high,.00530583)
        self.assertTrue(all(check.passed for check in lm706_checks(values)))
        self.assertAlmostEqual(left_5v_checks(values)[1].value,5.102994474221816)
        values.parts["RS1861"]=("ERJ8BWFR010V",values.parts["RS1861"][1])
        with self.assertRaisesRegex(ValueError,"unreviewed parallel"):
            usb5_shunt_bounds(values)

    def test_old_left_wrong_order_code_changes_actual_voltage_and_fails(self):
        values = parts(("R1712", "74.3k 0.1%", "RT0603BRD0743KL"),
                       ("R1713", "10k 0.1%", "RT0603BRD0710KL"))
        checks = left_5v_checks(values)
        self.assertAlmostEqual(checks[0].value, 3.18)
        self.assertFalse(checks[0].passed)
        self.assertFalse(procurement_checks("left", values)[0].passed)

    def test_correct_left_setpoint_and_tolerances(self):
        values = parts(("R1712", "75k 0.1%", "RT0603BRD0775KL"),
                       ("R1713", "10k 0.1%", "RT0603BRD0710KL"))
        self.assertTrue(all(check.passed for check in left_5v_checks(values)))
        self.assertAlmostEqual(values.temperature_tolerance("R1712"), .002625)

    def test_tolerance_comes_from_order_code(self):
        values = parts(("R1712", "75k 0.1%", "RC0603FR-0775KL"),
                       ("R1713", "10k 0.1%", "RT0603BRD0710KL"))
        self.assertEqual(values.tolerance("R1712"), .01)
        self.assertFalse(procurement_checks("left", values)[0].passed)

    def test_unknown_tolerance_does_not_default_to_precision_part(self):
        values = parts(("R1", "10k 0.1%", "unknown"))
        with self.assertRaises(ValueError):
            values.tolerance("R1")

    def test_netlist_reader_keeps_capacitors_on_each_board(self):
        xml = '''<export><components><comp ref="C1"><value>100u</value>
        <fields><field name="MPN">T520D107M010ATE070</field></fields>
        </comp></components><nets><net name="/USB_PORT_5V"><node ref="C1" pin="1"/>
        </net><net name="GND"><node ref="C1" pin="2"/></net></nets></export>'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"board.xml"
            path.write_text(xml)
            left, right = component_values(path), component_values(path)
        self.assertAlmostEqual(direct_capacitance([left, right], "/USB_PORT_5V", True, True), 160e-6)
        self.assertGreater(direct_capacitance([left, right], "/USB_PORT_5V", True, True), 100e-6)

    def test_reservoir_behind_switch_is_not_miscounted_as_direct(self):
        values = parts(("C1", "150u", "T520D157M010ATE025"))
        values.pins["C1"] = {"1": "/J22_5V_PRE", "2": "GND"}
        self.assertEqual(direct_capacitance([values], "/USB_PORT_5V"), 0)

    def test_buck_maximum_input_cap_current_near_half_duty(self):
        ripple, peak, rms, input_rms = buck_currents(10, 5, 6, 3.3e-6, 500e3)
        self.assertAlmostEqual(ripple, 1.5151515151515151)
        self.assertAlmostEqual(peak, 6+ripple/2)
        self.assertGreater(rms, 6)
        self.assertGreater(input_rms, 3)

    def test_boost_efficiency_and_ripple_are_separate(self):
        average, ripple, peak, rms = boost_currents(9, 12, 3, 4.7e-6, 400e3, .9)
        self.assertAlmostEqual(average, 4.444444444444445)
        self.assertAlmostEqual(ripple, 1.196808510638298)
        self.assertAlmostEqual(peak, average+ripple/2)
        self.assertGreater(rms, average)

    def test_invalid_model_operating_point_is_rejected(self):
        with self.assertRaises(ValueError):
            buck_currents(5, 12, 1, 1e-6, 1e6)
        with self.assertRaises(ValueError):
            boost_currents(12, 5, 1, 1e-6, 1e6, .9)

    def test_retention_is_requirement_not_nominal_capacitance_pass(self):
        retention = capacitor_retention_required(47e-6, .2, .15, .1, 20e-6)
        self.assertAlmostEqual(retention, .6953135864278265)
        self.assertGreater(retention, .69)

    def test_old_pd_window_rejects_20v(self):
        values = parts(("R1", "1M 0.1%", "RT0603BRD071ML"),
                       ("R2", "19.6k 0.1%", "RT0603BRD0719K6L"),
                       ("R3", "63.4k 0.1%", "RT0603BRD0763K4L"))
        checks = source_window_checks("pd", values, ("R1", "R2", "R3"), True)
        self.assertFalse(checks[1].passed)

    def test_recovery_includes_hysteresis_and_independent_tcr(self):
        values = parts(("R1", "1M 0.1%", "RT0603BRD071ML"),
                       ("R2", "35.7k 0.02%", "TNPU060335K7HZEN00"),
                       ("R3", "47.5k 0.02%", "TNPU060347K5HZEN00"))
        checks = source_window_checks("pd", values, ("R1", "R2", "R3"), True)
        self.assertTrue(all(check.passed for check in checks))
        self.assertAlmostEqual(checks[1].value, 21.12991560187165)


if __name__ == "__main__":
    unittest.main()

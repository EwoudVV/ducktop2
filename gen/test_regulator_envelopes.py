"""Regressions for the reviewed startup and distributed endpoint circuits."""
import copy
from types import SimpleNamespace
import unittest

from generate_pcie_power import add_pcie_power
from generate_sys5_power import add_sys5_power
from verify_design_contracts import CheckFailure, check_sys5_converter
from verify_electrical_calculations import (
    NetlistValues, endpoint_checks, sys5_checks, sys3_distribution_checks, mu_operating_checks,
)


class Capture:
    def __init__(self):
        self.components = {}
        self.values = NetlistValues()

    def place(self, ref, symbol, value, *position, footprint, pin_nets=None,
              extra_props=None, **unused):
        if ref in self.components:
            raise AssertionError(f"duplicate reference {ref}")
        def absolute(pin, connection):
            name, kind = connection
            if kind == 'nc':
                return f'unconnected-({ref}-Pad{pin})'
            if name == 'GND':
                return name
            return '/' + name if kind == 'hier' else '/Mu Carrier/' + name
        nets = {str(pin): absolute(pin, connection)
                for pin, connection in (pin_nets or {}).items()}
        props = extra_props or {}
        self.components[ref] = SimpleNamespace(value=value, footprint=footprint,
                                                pin_nets=nets, properties=props)
        self.values[ref] = value
        self.values.parts[ref] = (props.get('MPN', ''), footprint)
        self.values.pins[ref] = nets

    def text(self, *args, **kwargs):
        pass

    def pwrflag(self, *args, **kwargs):
        pass


class RegulatorEnvelopeTests(unittest.TestCase):
    def mu(self):
        values=NetlistValues()
        for ref,label,mpn in (
            ('L750','6.8uH','XGL1060-682MEC'),
            ('RS750','13mOhm','ERJ8CWFR013V'),
            ('R752','49.9R','RC0603FR-0749R9L'),
            ('R753','102k','TNPW0603102KBYEA'),
            ('R754','11.3k','TNPU060311K3HZEN00'),
            ('R756','49.9k','TNPU060349K9HZEN00'),
            ('C771','330n','CGA3E3X7R1H334K080AB'),
        ):
            values[ref]=label;values.parts[ref]=(mpn,'')
        return values

    def test_mu_33a_allocation_keeps_current_and_fault_margins(self):
        checks=mu_operating_checks(self.mu())
        self.assertTrue(all(check.passed for check in checks),checks)

    def test_mu_old_inductor_fails_the_current_clamp_screen(self):
        values=self.mu();values.parts['L750']=('XAL7070-682MEC','')
        checks=mu_operating_checks(values)
        self.assertFalse(next(x for x in checks if 'average-clamp' in x.name).passed)
        self.assertFalse(next(x for x in checks if 'peak-clamp' in x.name).passed)

    def test_mu_old_shunt_cannot_guarantee_the_33a_allocation(self):
        values=self.mu();values.parts['RS750']=('ERJ8BWFR015V','')
        checks=mu_operating_checks(values)
        self.assertFalse(next(x for x in checks if 'allocation below' in x.name).passed)

    def sys5(self):
        capture = Capture()
        add_sys5_power(capture)
        for ref, value, mpn in (
            ('R773', '43.2k', 'RC0603FR-0743K2L'),
            ('R252', '43.2k', 'RC0603FR-0743K2L'),
            ('R388', '66.5k', 'RC0603FR-0766K5L'),
            ('R2301', '1.65k', 'RT0603BRD071K65L'),
        ):
            capture.values[ref] = value
            capture.values.parts[ref] = (mpn, 'Resistor_SMD:R_0603_1608Metric')
        return capture

    def endpoint(self):
        capture = Capture()
        add_pcie_power(capture)
        return capture

    def test_sys5_actual_source_has_full_pin_and_procurement_contract(self):
        check_sys5_converter(self.sys5().components)

    def test_sys5_bootstrap_cannot_be_returned_through_the_power_switch_node(self):
        capture = self.sys5()
        capture.components['C43'].pin_nets['2'] = '/Mu Carrier/BUCK5_SW'
        with self.assertRaises(CheckFailure):
            check_sys5_converter(capture.components)

    def test_sys5_actual_parts_keep_25_percent_during_complete_bank_startup(self):
        checks = sys5_checks(self.sys5().values)
        self.assertTrue(all(check.passed for check in checks), checks)
        startup = next(check for check in checks if 'startup peak margin' in check.name)
        self.assertGreater(startup.value, 1.25)

    def test_old_small_sys5_inductor_fails_the_startup_margin(self):
        values = self.sys5().values
        values.parts['L4'] = ('XAL7070-332MEC', values.parts['L4'][1])
        checks = sys5_checks(values)
        startup = next(check for check in checks if 'startup peak margin' in check.name)
        self.assertFalse(startup.passed)

    def test_reservoir_substitution_outside_model_is_detected(self):
        values = self.sys5().values
        values.parts['C2364'] = ('T520X337M010ATE010', values.parts['C2364'][1])
        ceiling = next(check for check in sys5_checks(values) if 'environment ceiling' in check.name)
        self.assertFalse(ceiling.passed)

    def test_endpoint_damping_only_feeds_nvme(self):
        parts = self.endpoint().components
        self.assertEqual(parts['U772'].pin_nets['6'], '/PCIE_3V3')
        self.assertEqual(parts['R2292'].pin_nets,
                         {'1': '/PCIE_3V3', '2': '/Mu Carrier/NVME_3V3'})
        self.assertEqual(parts['C834'].pin_nets['1'], '/Mu Carrier/NVME_3V3')
        self.assertNotEqual(parts['R2292'].pin_nets['2'], parts['U772'].pin_nets['6'])

    def test_endpoint_actual_parts_keep_25_percent_with_inrush(self):
        checks = endpoint_checks(self.endpoint().values)
        self.assertTrue(all(check.passed for check in checks), checks)

    def test_endpoint_fast_slew_is_rejected_for_2mf_bank(self):
        values = self.endpoint().values
        del values.parts['C2289']
        values['C2289'] = '0'
        checks = endpoint_checks(values)
        startup = next(check for check in checks if 'startup current screen' in check.name)
        self.assertFalse(startup.passed)

    def test_sys3_precision_divider_keeps_2a_distribution_above_3v(self):
        values = NetlistValues()
        for ref, value, mpn in (('R43', '45.3k', 'TNPU060345K3HZEN00'),
                                ('R44', '10k', 'TNPU060310K0HZEN00')):
            values[ref] = value
            values.parts[ref] = (mpn, 'Resistor_SMD:R_0603_1608Metric')
        checks = sys3_distribution_checks(values)
        self.assertTrue(all(check.passed for check in checks), checks)
        self.assertAlmostEqual(checks[0].value, 3.02299970176535)
        values.parts['R43'] = ('RC0603FR-0745K3L', values.parts['R43'][1])
        self.assertFalse(sys3_distribution_checks(values)[0].passed)


if __name__ == '__main__':
    unittest.main()

"""Fault mutations for the revised standby, charger and Mu calculations."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from verify_aon_power import AonLimits, inspect
from verify_100w_calculations import (
    aon_buck, aon_window, charger, mu_operating, mu_rail, pd_power_good, pd_switch,
    current_transfer_bounds, adapter_current_screen, charge_current_screen,
)
from verify_electrical_calculations import (
    boost_currents, component_values, metal_strip_bounds, procurement_checks,
    NetlistValues, pack_breaker_environment_checks,
)

FIXTURES = Path(__file__).parent/'testdata/power_100w'


def change(values, ref, value, mpn):
    values[ref] = value
    values.parts[ref] = (mpn, values.parts[ref][1])


def named(checks, fragment):
    return next(check for check in checks if fragment in check.name)


class RevisionCalculations(unittest.TestCase):
    def setUp(self):
        self.center = component_values(FIXTURES/'center.xml')
        self.left = component_values(FIXTURES/'left.xml')
        self.right = component_values(FIXTURES/'right.xml')

    def test_mu_operating_screen_has_margin_and_stays_a_screen(self):
        checks = mu_operating(self.center)
        self.assertTrue(all(check.passed for check in checks))
        self.assertGreater(named(checks, 'average-current margin').value, 1.25)
        self.assertIn('no guaranteed fault peak', named(checks, 'peak screen').equation)

    def test_old_27k_limit_fails_the_unchanged_margin_requirement(self):
        change(self.center, 'R758', '27k', 'RC0603FR-0727KL')
        self.assertFalse(named(mu_operating(self.center), 'average-current margin').passed)

    def test_smaller_inductor_fails_bias_and_minimum_inductance_screen(self):
        change(self.center, 'L750', '3.3uH', 'XAL7070-332MEC')
        self.assertFalse(named(mu_operating(self.center), 'minimum inductance').passed)

    def test_parallel_shunt_cannot_silently_fall_back_to_one_part(self):
        self.center.parts.pop('RS2670')
        with self.assertRaisesRegex(ValueError, 'both parallel'):
            mu_operating(self.center)

    def test_modern_inductor_labels_are_in_procurement_coverage(self):
        self.center['L750'] = '8.2uH'
        self.center['L3'] = '6.8uH'
        mu_operating(self.center)
        aon_buck(self.center)
        failures = procurement_checks('center', self.center)
        self.assertTrue(any('L750' in check.name for check in failures))
        self.assertTrue(any('L3' in check.name for check in failures))

    def test_wsl_fixed_ohm_drift_is_included_at_hot_case(self):
        low, high = metal_strip_bounds(self.center, 'RS2600')
        self.assertAlmostEqual(low, .0183875)
        self.assertAlmostEqual(high, .0216125)
        self.assertGreater(high, .020*1.08)

    def test_charger_precision_strap_and_filter_are_checked(self):
        checks = charger(self.center)
        self.assertTrue(all(check.passed for check in checks))
        change(self.center, 'R18', '2.21k 1%', 'RC0402FR-072K21L')
        checks = charger(self.center)
        self.assertFalse(named(checks, 'PROG environment minimum').passed)
        self.assertFalse(named(checks, 'PROG environment maximum').passed)

    def test_slow_prog_filter_cannot_pass_on_resistor_alone(self):
        change(self.center, 'C2602', '100n', 'GRM155R71H104ME14D')
        self.assertFalse(named(charger(self.center), 'filter settling').passed)

    def test_150k_pg_supports_unpowered_low_and_powered_high(self):
        for side, base in ((self.left,2080),(self.right,2090)):
            with self.subTest(base=base):
                checks = pd_power_good('PD',self.center,side,base)
                self.assertTrue(all(check.passed for check in checks))
                self.assertLess(named(checks,'sink-current').value,20)

    def test_pg_10k_and_one_meg_fail_different_logic_corners(self):
        change(self.left, 'R2086', '10k', 'RC0603FR-0710KL')
        self.assertFalse(named(pd_power_good('PD',self.center,self.left,2080), 'sink-current').passed)
        change(self.left, 'R2086', '1M', 'RC0603FR-071ML')
        self.assertFalse(named(pd_power_good('PD',self.center,self.left,2080), 'high margin').passed)

    def test_pg_receiver_identity_must_match_the_checked_part(self):
        self.center.parts['U44'] = ('TCA9537PWR',self.center.parts['U44'][1])
        with self.assertRaisesRegex(ValueError,'TCA9539'):
            pd_power_good('PD',self.center,self.left,2080)

    def test_efuse_equation_agrees_with_published_300ohm_typical_point(self):
        change(self.left,'R2083','300R','RC0603FR-07300RL')
        current = named(pd_switch('PD',self.left,2080),'nominal breaker').value
        self.assertAlmostEqual(current,4.98,delta=.005)

    def test_boost_rejects_nonphysical_passive_or_load_inputs(self):
        for inductance,frequency,load in ((0,400e3,5),(-1e-6,400e3,5),(6.8e-6,0,5),(6.8e-6,400e3,-1)):
            with self.subTest(inductance=inductance,frequency=frequency,load=load):
                with self.assertRaises(ValueError):
                    boost_currents(10,12,load,inductance,frequency,.85)

    def test_qualified_transfer_screen_encloses_named_silicon_points(self):
        # Renesas gives these three accuracy points, not a continuous bound.
        for current,error in ((.5,.10),(2,.025),(4,.0225)):
            with self.subTest(current=current):
                low,high=current_transfer_bounds(current,(1,1),(.975,1.025),.050)
                self.assertLessEqual(low,current*(1-error))
                self.assertGreaterEqual(high,current*(1+error))

    def test_current_envelope_proves_why_old_100w_command_is_not_a_limit(self):
        low,high=current_transfer_bounds(4.388,(.919,1.081),(.975,1.025),.050)
        self.assertGreater(high+.360,5)
        self.assertLess(low,4.388)

    def test_current_lower_bound_cannot_become_negative_near_zero(self):
        low,high=current_transfer_bounds(.020,(.919,1.081),(.975,1.025),.050)
        self.assertEqual(low,0)
        self.assertGreater(high,0)

    def test_adapter_model_cannot_drop_shunt_or_silicon_error_terms(self):
        profile=dict(sense_min=.919,sense_max=1.081,gain_min=.975,gain_max=1.025,offset=.050)
        self.assertTrue(all(check.passed for check in adapter_current_screen(self.center,profile)))
        for key,value,fragment in (('sense_min',.920,'shunt low'),
                                   ('sense_max',1.080,'shunt high'),
                                   ('offset',0,'0.5A named-point')):
            with self.subTest(key=key):
                modified={**profile,key:value}
                self.assertTrue(any(fragment in check.name and not check.passed
                                    for check in adapter_current_screen(self.center,modified)))

    def test_charge_model_encloses_the_named_accuracy_points(self):
        profile=dict(sense_min=.869,gain_max=1.020,offset=.060)
        checks=charge_current_screen(self.center,profile)
        self.assertTrue(all(check.passed for check in checks))
        profile['offset']=0
        self.assertFalse(named(charge_current_screen(self.center,profile),'0.5A named-point').passed)

    def test_pack_trip_uses_environment_bounds_beyond_initial_tolerance(self):
        values=NetlistValues()
        values['RS10']='11m 1% 2W'
        values.parts['RS10']=('WSL2512R0110FEA18','Resistor_SMD:R_2512_6332Metric')
        checks=pack_breaker_environment_checks(values)
        self.assertTrue(all(check.passed for check in checks))
        floor=named(checks,'trip floor').value
        self.assertLess(floor,.040/(.011*1.01))
        self.assertAlmostEqual(floor,3.2423,places=3)
        change(values,'RS10','15m','WSL2512R0150FEA18')
        self.assertFalse(named(pack_breaker_environment_checks(values),'trip floor').passed)


class StandbyMutations(unittest.TestCase):
    def mutate(self, callback):
        tree = ET.parse(FIXTURES/'center.xml')
        callback(tree.getroot())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'center.xml'
            tree.write(path)
            return inspect(path)

    def test_baseline_reports_conditional_limits_and_no_physical_pass(self):
        report = inspect(FIXTURES/'center.xml')
        self.assertFalse(report['failures'])
        self.assertEqual(report['status'],'PASS_WITH_UNMEASURED_LIMITS')
        self.assertEqual(report['physical_tests'],'NOT_RUN')
        self.assertGreater(report['gate_off_screen_s'],.0012)
        self.assertLess(report['fault_with_gate_off_s'],.100)
        self.assertGreater(report['active_to_fast_breaker_margin'],1)

    def test_180m_label_mutation_cannot_hide_behind_correct_mpn(self):
        result = self.mutate(lambda root: setattr(root.find('./components/comp[@ref="RS2660"]/value'),'text','18m 1%'))
        self.assertTrue(any('procurement identity' in x for x in result['failures']))

    def test_aon_cannot_bypass_the_charger_battery_shunt(self):
        def bypass(root):
            net = root.find('./nets/net[@name="/VSYS"]')
            node = net.find('node[@ref="U2650"][@pin="3"]')
            net.remove(node)
            root.find('./nets/net[@name="/PACK_POS_FUSED"]').append(node)
        result = self.mutate(bypass)
        self.assertTrue(any('U2650.3' in x for x in result['failures']))

    def test_retry_variant_is_rejected(self):
        def retry(root):
            root.find('./components/comp[@ref="U2660"]/fields/field[@name="MPN"]').text='LTC4231IMS-2#PBF'
        self.assertTrue(self.mutate(retry)['failures'])

    def test_smaller_timers_fail_recharge_even_if_identity_is_reviewed(self):
        def shrink(root):
            for ref in ('C2661','C2662'):
                root.find(f'./components/comp[@ref="{ref}"]/fields/field[@name="MPN"]').text='GRT188R61H104ME13D'
                root.find(f'./components/comp[@ref="{ref}"]/value').text='100n 50V'
        result = self.mutate(shrink)
        self.assertTrue(any('expire the current-limit timer' in x for x in result['failures']))

    def test_larger_timers_violate_the_soa_pulse_duration(self):
        def grow(root):
            for ref in ('C2661','C2662'):
                root.find(f'./components/comp[@ref="{ref}"]/fields/field[@name="MPN"]').text='GRT188R61H225ME13D'
                root.find(f'./components/comp[@ref="{ref}"]/value').text='2.2u 50V'
        result = self.mutate(grow)
        self.assertTrue(any('100 ms SOA' in x for x in result['failures']))

    def test_more_load_and_hotter_case_fail_their_actual_limits(self):
        for limits,needle in ((replace(AonLimits(),load_a=.600),'steady standby'),
                              (replace(AonLimits(),initial_case_c=125),'derated SOA')):
            with self.subTest(limits=limits):
                self.assertTrue(any(needle in x for x in inspect(FIXTURES/'center.xml',limits)['failures']))

    def test_larger_output_bank_cannot_exhaust_startup_silently(self):
        result=inspect(FIXTURES/'center.xml',replace(AonLimits(),load_capacitance_f=1e-3))
        self.assertTrue(result['failures'])
        self.assertTrue(any('timer' in x or 'ramp' in x for x in result['failures']))


if __name__ == '__main__':
    unittest.main()

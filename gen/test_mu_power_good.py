"""Reject broken bias networks and incompatible power-good receivers."""
from pathlib import Path
import unittest

from verify_electrical_calculations import component_values
from verify_100w_calculations import mu_power_good


class MuPowerGood(unittest.TestCase):
    def setUp(self):
        self.values = component_values(Path(__file__).parent / 'testdata/mu_power_good.xml')

    def test_saved_network_has_high_low_and_current_margin(self):
        checks = mu_power_good(self.values)
        self.assertEqual(len(checks), 6)
        self.assertTrue(all(c.passed for c in checks), checks)

    def test_always_on_pullup_is_rejected(self):
        self.values.pins['R762']['1'] = '/MCU_3V3'
        with self.assertRaisesRegex(ValueError, 'R762'):
            mu_power_good(self.values)

    def test_missing_off_state_return_is_rejected(self):
        del self.values.pins['R2671']
        with self.assertRaisesRegex(ValueError, 'R2671'):
            mu_power_good(self.values)

    def test_each_gate_input_and_supply_pin_is_checked(self):
        for pin in self.values.pins['U769']:
            self.setUp()
            self.values.pins['U769'][pin] = 'wrong'
            with self.assertRaisesRegex(ValueError, 'U769'):
                mu_power_good(self.values)

    def test_plain_cmos_gate_is_rejected(self):
        self.values.parts['U769'] = ('SN74LVC1G08DBVR', 'Package_TO_SOT_SMD:SOT-23-5')
        with self.assertRaisesRegex(ValueError, 'Schmitt'):
            mu_power_good(self.values)

    def test_old_resistance_cannot_pass_with_new_net_names(self):
        self.values.parts['R762'] = ('RC0603FR-07100KL', self.values.parts['R762'][1])
        self.assertFalse(mu_power_good(self.values)[0].passed)

    def test_excessive_filter_delay_is_rejected(self):
        self.values.parts['C774'] = ('C0603C104K5RACTU', self.values.parts['C774'][1])
        self.values['C774'] = '100n PG deglitch'
        self.assertFalse(mu_power_good(self.values)[4].passed)


if __name__ == '__main__':
    unittest.main()

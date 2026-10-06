"""Fault mutations for the center battery path and shared startup bank."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from verify_battery_path import inspect
from verify_electrical_calculations import NetlistValues


class BatteryPathTests(unittest.TestCase):
    def setUp(self):
        data = json.loads((Path(__file__).parent / 'testdata/battery_path.json').read_text())
        self.boards = []
        for name in ('center', 'left', 'right', 'bms'):
            values = NetlistValues()
            for ref, row in data[name].items():
                values[ref] = row['value']
                values.parts[ref] = (row['mpn'], row['footprint'])
                values.pins[ref] = row['pins']
            self.boards.append(values)

    def test_current_circuit_passes_static_checks_but_is_not_qualified(self):
        result = inspect(*self.boards)
        self.assertTrue(result['passed'], result['failures'])
        self.assertTrue(result['not_qualified'])
        self.assertAlmostEqual(result['metrics']['RS1_ohm'][1], .00620475)
        self.assertAlmostEqual(result['metrics']['center_component_drop_at_8A_mV'], 191.708)
        self.assertAlmostEqual(result['metrics']['startup_initial_bank_uF'], 512.252)

    def test_original_100k_return_exceeds_the_guaranteed_drive_test_point(self):
        center = self.boards[0]
        center['R2600'] = '100k BGATE to source'
        center.parts['R2600'] = ('RC0603FR-07100KL', center.parts['R2600'][1])
        result = inspect(*self.boards)
        self.assertFalse(result['passed'])
        self.assertIn('BGATE load at the 2 V drive test point', result['failures'])
        self.assertGreater(result['metrics']['gate_load_at_2V_uA'], 15)

    def test_longer_harness_cannot_reuse_the_old_voltage_drop(self):
        with patch('fpc_contract.BMS_POWER_WIRE_LENGTH_BUDGET_MM',130):
            short=inspect(*self.boards)['metrics']
        with patch('fpc_contract.BMS_POWER_WIRE_LENGTH_BUDGET_MM',260):
            long=inspect(*self.boards)['metrics']
        self.assertAlmostEqual(short['protected_wire_pair_drop_at_8A_mV'],62.4)
        self.assertAlmostEqual(short['protected_wire_pair_loss_at_8A_W'],.4992)
        self.assertAlmostEqual(long['protected_wire_pair_drop_at_8A_mV'],124.8)
        self.assertGreater(long['minimum_protected_pack_voltage_for_10V_VSYS_before_contacts_and_copper_V'],
                           short['minimum_protected_pack_voltage_for_10V_VSYS_before_contacts_and_copper_V'])

    def test_q25_body_diode_cannot_be_reversed(self):
        self.boards[0].pins['Q25']['5'] = '/PACK_POS_FUSED'
        self.assertFalse(inspect(*self.boards)['passed'])

    def test_gauge_pickup_cannot_move_to_system_ground(self):
        self.boards[0].pins['R183']['1'] = 'GND'
        self.assertIn('R183.1 must connect to /FG_VSS', inspect(*self.boards)['failures'])

    def test_ten_milliohm_gauge_substitution_is_rejected(self):
        self.boards[0]['RS1'] = '10m 1% 2W'
        self.boards[0].parts['RS1'] = ('WSLP2512R0100FEA', self.boards[0].parts['RS1'][1])
        self.assertFalse(inspect(*self.boards)['passed'])

    def test_protected_harness_pin_numbers_are_reversed_between_boards(self):
        self.boards[3].pins['J2072'] = copy.deepcopy(self.boards[0].pins['J2071'])
        self.assertFalse(inspect(*self.boards)['passed'])

    def test_extra_input_bulk_cannot_silently_exceed_the_startup_allocation(self):
        center = self.boards[0]
        for ref in ('C9990', 'C9991'):
            center[ref] = center['C2608']
            center.parts[ref] = center.parts['C2608']
            center.pins[ref] = dict(center.pins['C2608'])
        result = inspect(*self.boards)
        self.assertIn('direct input bank within startup allocation', result['failures'])

    def test_startup_limiter_substitution_cannot_reuse_the_same_calculation(self):
        bms = self.boards[3]
        bms.parts['U2218'] = ('TPS26601PWPR', bms.parts['U2218'][1])
        with self.assertRaises(ValueError):
            inspect(*self.boards)


if __name__ == '__main__':
    unittest.main()

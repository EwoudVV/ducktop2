"""Reject AUX fuse substitutions, bypasses and changed overload limits."""
from pathlib import Path
import unittest

from verify_aux_input import inspect
from verify_electrical_calculations import component_values

HERE = Path(__file__).parent / 'testdata/aux_input'


class AuxInput(unittest.TestCase):
    def setUp(self):
        self.center = component_values(HERE / 'center.xml')
        self.left = component_values(HERE / 'left.xml')

    def fails(self, text):
        failures = inspect(self.center, self.left)['failures']
        self.assertTrue(any(text in f for f in failures), failures)

    def test_native_snapshot_and_explicit_limits(self):
        report = inspect(self.center, self.left)
        self.assertEqual(report['failures'], [])
        self.assertGreater(report['normal_operation']['fuse_continuous_allocation_a'], 3)
        self.assertFalse(report['hardware_qualified'])
        self.assertFalse(report['manufacturing_ready'])
        self.assertFalse(report['fault_and_pulse_limits']['typical_melting_I2t_is_total_clearing_limit'])

    def test_each_fuse_requires_the_selected_part_and_land_pattern(self):
        for board, ref in [('center', 'F190'), ('left', 'F195')]:
            for field in [0, 1]:
                self.setUp()
                values = getattr(self, board)
                identity = list(values.parts[ref]);identity[field] = 'wrong part or footprint'
                values.parts[ref] = tuple(identity)
                self.fails(ref)

    def test_fuses_cannot_be_bypassed(self):
        for board, ref in [('center', 'F190'), ('left', 'F195')]:
            self.setUp();values = getattr(self, board)
            values.pins[ref]['2'] = values.pins[ref]['1']
            self.fails(ref)

    def test_both_center_branches_stay_after_the_fuse(self):
        for ref, pin in [('D190', '1'), ('D711', '2'), ('Q13', '5'), ('U12', '1')]:
            self.setUp();self.center.pins[ref][pin] = '/AUX_DC_RAW';self.fails(ref)

    def test_reverse_protection_pin_mapping_is_checked(self):
        self.center.pins['Q13']['1'], self.center.pins['Q13']['5'] = (
            self.center.pins['Q13']['5'], self.center.pins['Q13']['1'])
        self.fails('Q13')

    def test_current_limit_cannot_follow_the_new_fuse_rating(self):
        self.center['R710'] = '3.6k 1%';self.center.parts['R710'] = ('RC0603FR-073K6L', self.center.parts['R710'][1])
        self.fails('R710')

    def test_fault_outputs_and_soft_start_remain_connected(self):
        for ref, pin in [('U12', '14'), ('U12', '16'), ('C723', '1')]:
            self.setUp();self.center.pins[ref][pin] = 'unconnected-test';self.fails(ref)


if __name__ == '__main__':
    unittest.main()

"""Check that the pin review rejects the repaired power-path faults."""
import contextlib
import copy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import generate_pin_review_table as review


class PowerPinReviewTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).parent / 'fixtures/pin_review_power.xml'
        with patch.object(review, 'NETLIST', fixture):
            self.meta, self.pins = review.parse_netlist()

    def run_gate(self):
        review.contracts.clear()
        output = io.StringIO()
        with patch.object(review, 'CURRENT_REQUIRED_REFS', set(self.meta)), \
                patch.object(review, 'export_netlist'), \
                patch.object(review, 'parse_netlist', return_value=(copy.deepcopy(self.meta), copy.deepcopy(self.pins))), \
                patch.object(review, 'write_csv'), patch.object(review, 'write_md'), \
                patch.object(sys, 'argv', ['pin-review']), contextlib.redirect_stdout(output):
            result = review.main()
        return result, output.getvalue()

    def test_checked_export_has_no_unreviewed_pins(self):
        result, output = self.run_gate()
        self.assertEqual(result, 0, output)
        self.assertIn('fail=0 review=0', output)

    def test_efuse_return_cannot_be_bypassed(self):
        self.pins['U718']['15'] = 'GND'
        self.pins['U718']['25'] = 'GND'
        self.assertEqual(self.run_gate()[0], 1)

    def test_output_shunt_pickup_cannot_move_after_shunt(self):
        self.pins['U6']['11'] = '/SYS_5V'
        self.assertEqual(self.run_gate()[0], 1)

    def test_endpoint_enable_requires_the_power_good_gate(self):
        self.pins['U772']['8'] = '/MU_HOST_ACTIVE'
        self.assertEqual(self.run_gate()[0], 1)

    def test_output_and_timing_pins_cannot_be_swapped(self):
        self.pins['U772']['6'], self.pins['U772']['7'] = self.pins['U772']['7'], self.pins['U772']['6']
        self.assertEqual(self.run_gate()[0], 1)

    def test_rtc_diode_reversal_is_rejected(self):
        self.pins['D1824']['1'], self.pins['D1824']['2'] = self.pins['D1824']['2'], self.pins['D1824']['1']
        self.assertEqual(self.run_gate()[0], 1)

    def test_old_converter_identity_cannot_reuse_new_pin_map(self):
        self.meta['U6'].update(lib='TPS56637', part='TPS56637')
        result, output = self.run_gate()
        self.assertEqual(result, 1)
        self.assertIn('part identity mismatch on U6', output)

    def test_unexpected_load_switch_pin_is_not_exempt(self):
        self.meta['U772']['libpins']['9'] = {'pin_name': 'EP', 'pin_type': 'power_in'}
        self.pins['U772']['9'] = 'GND'
        result, output = self.run_gate()
        self.assertEqual(result, 1)
        self.assertIn('uncontracted pins remain in the selected review: U772', output)


if __name__ == '__main__':
    unittest.main()

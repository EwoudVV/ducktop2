"""Ensure intentional ERC warnings cannot hide changed symbols or real errors."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import genlib
from verify_electrical_calculations import NetlistValues
from verify_erc_warnings import classify


class ErcWarningsTests(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((Path(__file__).resolve().parents[1] /
                                  'verification/erc-symbols.json').read_text())['symbols']
        self.symbol = {'ref': 'R1', 'lib_id': 'Device:R',
                       'template': genlib.load_renamed_symbol('R')[1]}
        self.index = SimpleNamespace(symbols={'symbol-id': self.symbol}, pins={})
        self.values = NetlistValues()
        self.item = {'severity': 'warning', 'type': 'lib_symbol_mismatch',
                     'description': "Symbol 'R' doesn't match copy in library 'Device'",
                     'items': [{'uuid': 'symbol-id', 'description': 'Symbol R1 [R]'}]}

    def review(self, board='center', pd_ok=True):
        return classify([self.item], self.index, self.values, board,
                        records=self.records, pd_check=lambda: pd_ok)

    def gpio_fixture(self, redriver=False):
        ref, name = ('U2000', 'TUSB1142') if redriver else ('U41', 'TPS25751AD')
        pin = '22' if redriver else '5'
        lib, template = genlib.load_renamed_symbol(name)
        row = {'ref': ref, 'lib_id': lib + ':' + name, 'template': template}
        flag = {'ref': '#FLG1234', 'lib_id': 'power:PWR_FLAG',
                'template': genlib.load_renamed_symbol('PWR_FLAG')[1]}
        self.index.pins = {'io-pin': (row, pin), 'flag-pin': (flag, '1')}
        self.values.parts[ref] = ('TUSB1142IRNQR' if redriver else 'TPS25751ADREFR', '')
        self.values.pins[ref] = {pin: 'GND'}
        self.item = {'severity': 'warning', 'type': 'pin_to_pin',
                     'description': 'Pins of type Bidirectional and Power output are connected',
                     'items': [{'uuid': 'io-pin', 'description': f'Symbol {ref} Pin {pin} [I/O, Bidirectional, Line]'},
                               {'uuid': 'flag-pin', 'description': 'Symbol #FLG1234 Pin 1 [Power output, Line]'}]}
        if redriver:
            mode = '/PD1 Dual-Role/PD1_MUX_MODE'
            self.values.pins[ref]['17'] = mode
            self.values.pins['R2008'] = {'1': mode, '2': 'GND'}
            self.values.parts['R2008'] = ('RC0603FR-071KL', 'Resistor_SMD:R_0603_1608Metric')
            self.values['R2008'] = '1k MODE low'

    def test_verified_template_is_classified(self):
        self.assertTrue(self.review()['passed'])

    def test_cache_pin_type_change_is_not_covered_by_the_template_review(self):
        self.symbol['template'] = self.symbol['template'].replace('(pin passive line', '(pin output line', 1)
        self.assertFalse(self.review()['passed'])

    def test_changed_generator_reference_requires_another_review(self):
        self.records['Device:R']['generated_symbol_sha256'] = '0' * 64
        self.assertFalse(self.review()['passed'])

    def test_changed_stock_library_requires_another_review(self):
        self.records['Device:R']['stock_library_sha256'] = '0' * 64
        self.assertFalse(self.review()['passed'])

    def test_warning_reference_must_match_the_actual_uuid(self):
        self.item['items'][0]['description'] = 'Symbol R2 [R]'
        self.assertFalse(self.review()['passed'])

    def test_unreviewed_symbol_family_fails(self):
        self.records.pop('Device:R')
        self.assertFalse(self.review()['passed'])

    def test_old_error_exceptions_are_always_rejected(self):
        for kind, message in [('pin_not_driven', 'Input pin not driven by any Output pins'),
                              ('power_pin_not_driven', 'Input Power pin not driven by any Output Power pins'),
                              ('label_dangling', 'Label not connected')]:
            with self.subTest(kind=kind):
                self.item.update(severity='error', type=kind, description=message)
                self.assertFalse(self.review()['passed'])

    def test_verified_unused_pd_gpio_is_classified(self):
        self.gpio_fixture()
        self.assertTrue(self.review('left')['passed'])
        self.assertFalse(self.review('right')['passed'])

    def test_grounded_gpio_requires_the_matching_release_configuration(self):
        self.gpio_fixture()
        self.assertFalse(self.review('left', pd_ok=False)['passed'])

    def test_gpio_on_another_net_or_with_another_part_is_rejected(self):
        self.gpio_fixture()
        self.values.pins['U41']['5'] = '/MCU_3V3'
        self.assertFalse(self.review('left')['passed'])
        self.values.pins['U41']['5'] = 'GND'
        self.values.parts['U41'] = ('TPS25750D', '')
        self.assertFalse(self.review('left')['passed'])

    def test_power_flag_identity_is_required(self):
        self.gpio_fixture()
        self.index.pins['flag-pin'][0]['lib_id'] = 'Device:R'
        self.assertFalse(self.review('left')['passed'])

    def test_grounded_aeq_pin_requires_gpio_mode(self):
        self.gpio_fixture(redriver=True)
        self.assertTrue(self.review('left')['passed'])
        self.values.pins['R2008']['2'] = '/SYS_3V3'
        self.assertFalse(self.review('left')['passed'])

    def test_weaker_mode_strap_cannot_reuse_the_review(self):
        self.gpio_fixture(redriver=True)
        self.values.parts['R2008'] = ('RC0603FR-07100KL', 'Resistor_SMD:R_0603_1608Metric')
        self.values['R2008'] = '100k'
        self.assertFalse(self.review('left')['passed'])


if __name__ == '__main__':
    unittest.main()

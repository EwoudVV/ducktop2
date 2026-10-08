"""Catch missed overhead material and double-counted height allowances."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mechanical/case-prototype'))
from cad import box
from cooling_review import screen_component_heights


class CoolingHeightTests(unittest.TestCase):
    def setUp(self):
        self.part = {'board': 'center', 'reference': 'U1', 'mpn': 'example',
                     'footprint': 'example:part', 'side': 'front', 'dnp': False,
                     'height_kind': 'maximum', 'height_mm': 1.2,
                     'planning_allowance_mm': None, 'height_source_url': 'drawing',
                     'height_basis': 'maximum seated height',
                     'courtyards_installed_mm': {'front': [
                         {'outer': [[0,0],[2,0],[2,2],[0,2]], 'holes': []}]}}
        self.settings = {'manufacturer_assembly_allowance_mm': .3, 'reservations': {}}

    def screen(self, shape, part=None):
        return screen_component_heights([part or self.part], [{'name': 'cooler', 'shape': shape}],
                                        {'center': 6.7}, self.settings)

    def test_margin_includes_allowance_exactly_once(self):
        result = self.screen(box(0,0,8.7,2,2,1))
        self.assertAlmostEqual(result['component_height_crossings'][0]['planning_gap_mm'], .5)
        self.assertFalse(result['known_component_height_conflicts'])

    def test_larger_maximum_exposes_interference(self):
        self.part['height_mm'] = 1.8
        result = self.screen(box(0,0,8.7,2,2,1))
        self.assertAlmostEqual(result['known_component_height_conflicts'][0]['planning_gap_mm'], -.1)

    def test_nominal_stays_missing(self):
        self.part['height_kind'] = 'nominal'
        result = self.screen(box(0,0,8.7,2,2,1))
        self.assertFalse(result['component_height_crossings'])
        self.assertEqual(len(result['unverified_component_height_screens']), 1)

    def test_reservation_is_not_promoted_to_manufacturer_limit(self):
        self.settings['reservations']['center/U1'] = {
            'mpn': 'example', 'footprint': 'example:part', 'height_mm': 1.9,
            'basis': 'assembled target', 'source': 'assembly'}
        row = self.screen(box(0,0,8.7,2,2,1))['component_height_crossings'][0]
        self.assertAlmostEqual(row['planning_gap_mm'], .1)
        self.assertFalse(row['physical_fit_verified'])
        self.assertNotIn('manufacturer_maximum_mm', row)

    def test_empty_middle_of_cooler_is_not_material(self):
        shape = box(-1,-1,8.7,4,4,1).cut(box(-.1,-.1,8.6,2.2,2.2,1.2))
        self.assertFalse(self.screen(shape)['component_height_crossings'])

    def test_lowest_overhead_surface_controls_margin(self):
        shape = box(0,0,9.7,2,2,1).fuse(box(0,0,8.4,.2,.2,1.4))
        self.assertAlmostEqual(self.screen(shape)['component_height_crossings'][0]['planning_gap_mm'], .2)

    def test_courtyard_hole_is_empty(self):
        self.part['courtyards_installed_mm']['front'][0]['holes'] = [
            [[.5,.5],[1.5,.5],[1.5,1.5],[.5,1.5]]]
        self.assertFalse(self.screen(box(.6,.6,8.7,.8,.8,1))['component_height_crossings'])

    def test_dnp_and_backside_are_outside_this_screen(self):
        for changes in [{'dnp': True}, {'side': 'back'}]:
            part = {**copy.deepcopy(self.part), **changes}
            self.assertFalse(self.screen(box(0,0,8.7,2,2,1), part)['component_height_crossings'])


if __name__ == '__main__':
    unittest.main()

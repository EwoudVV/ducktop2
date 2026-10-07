"""Keep nominal dimensions and assembly space out of guaranteed-height claims."""
import copy
import sys
import unittest
from pathlib import Path

import numpy as np
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mechanical/case-prototype'))
from component_heights import guide_samples, guided_points, height_limit, resolve, screen_routes


class ComponentHeightTests(unittest.TestCase):
    def setUp(self):
        self.part = {'board': 'center', 'reference': 'J1', 'mpn': 'example',
                     'footprint': 'example:part', 'height_kind': 'nominal',
                     'height_mm': 4.2, 'planning_allowance_mm': None,
                     'height_source_url': 'manufacturer drawing', 'height_basis': 'drawing A'}
        self.settings = {'manufacturer_assembly_allowance_mm': .3,
                         'wire_position_allowance_mm': .2, 'guide_curve_allowance_mm': .025,
                         'sampling_step_mm': .05, 'reservations': {}}

    def test_nominal_height_stays_unverified_without_reservation(self):
        self.assertIsNone(resolve(self.part, self.settings))

    def test_reservation_does_not_claim_manufacturer_maximum(self):
        self.settings['reservations']['center/J1'] = {
            'mpn': 'example', 'footprint': 'example:part', 'height_mm': 5,
            'basis': 'fit sample', 'source': 'assembly drawing'}
        result = resolve(self.part, self.settings)
        self.assertEqual(result['basis'], 'assembly_reservation')
        self.assertFalse(result['physical_fit_verified'])
        self.assertNotIn('manufacturer_maximum_mm', result)
        changed = copy.deepcopy(self.part)
        changed['mpn'] = 'replacement'
        with self.assertRaises(ValueError):
            resolve(changed, self.settings)

    def test_maximum_keeps_assembly_space(self):
        self.part.update(height_kind='maximum', height_mm=1.1)
        self.assertAlmostEqual(resolve(self.part, self.settings)['height_mm'], 1.4)

    def test_reservation_cannot_hide_larger_manufacturer_part(self):
        self.part.update(height_kind='maximum', height_mm=6)
        self.settings['reservations']['center/J1'] = {
            'mpn': 'example', 'footprint': 'example:part', 'height_mm': 5,
            'basis': 'old envelope', 'source': 'old assembly drawing'}
        with self.assertRaises(ValueError):
            resolve(self.part, self.settings)

    def test_side_of_round_guide_uses_actual_vertical_extent(self):
        area = box(-.1, .6, .1, .8)
        result = height_limit(np.array([[0., 0., 10.]]), 1., area, 0.)
        self.assertAlmostEqual(result, 9.2)

    def test_short_crossing_between_original_stations_is_not_missed(self):
        route = {'points': [[0, 0, 10], [10, 0, 10]], 'wire_od_mm': 1}
        config = {'guide_radial_clearance': .15, 'guide_wall': .4}
        samples, radius = guide_samples(route, config, self.settings)
        result = height_limit(samples, radius, box(4.999, -.001, 5.001, .001), 0)
        self.assertIsNotNone(result)
        expected = 10 - (.5 + .15 + .4 + .2 + .025)
        self.assertLessEqual(result, expected)
        self.assertGreaterEqual(result, expected - .025001)

    def test_guide_end_override_does_not_move_wire_stations(self):
        route = {'name': 'power', 'points': [[x, 0, 3] for x in np.arange(0, 15.01, .25)]}
        original = copy.deepcopy(route)
        trimmed = guided_points(route, {'guide_end_trim_by_route_mm': {'power': 5}})
        self.assertAlmostEqual(trimmed[0, 0], 3)
        self.assertAlmostEqual(trimmed[-1, 0], 10)
        self.assertEqual(route, original)

    def test_wire_is_still_screened_beyond_the_guide_end(self):
        route = {'name': 'power', 'group': 'main', 'ends': [], 'wire_od_mm': 1,
                 'points': [[x, 0, 3] for x in np.arange(0, 15.01, .25)]}
        part = {**self.part, 'side': 'front', 'dnp': False, 'height_kind': 'maximum',
                'height_mm': 2.5, 'height_status': 'verified_maximum',
                'courtyards_installed_mm': {'front': [{'outer': [[13.9,-.1],[14.1,-.1],[14.1,.1],[13.9,.1]], 'holes': []}]}}
        config = {'guide_radial_clearance': .15, 'guide_wall': .4,
                  'guide_end_trim_by_route_mm': {'power': 5}}
        result = screen_routes([route], [part], {'center': 0}, config, self.settings)
        self.assertEqual(len(result['known_height_clearance_conflicts']), 1)
        self.assertEqual(result['known_height_clearance_conflicts'][0]['limiting_surface'], 'wire')


if __name__ == '__main__':
    unittest.main()

"""Regression checks for pair geometry and complete signal paths."""
import copy
import math
import unittest

from shapely.geometry import box
from check_center_pcie_coupling import check, automatic_corners
from center_pcie_geometry import Curve
from center_pcie_paths import check_paths


def track(key, polarity, start, end):
    return dict(id=key, type='PCB_TRACK', net='TEST_'+polarity, start=start,
                end=end, width=.183, layers=['F.Cu'],
                length=math.dist(start, end), neighbors=[])


def arc(key, polarity, radius, start=0., end=math.pi/2):
    point = lambda angle: [radius*math.cos(angle), radius*math.sin(angle)]
    return dict(id=key, type='PCB_ARC', net='TEST_'+polarity,
                start=point(start), mid=point((start+end)/2), end=point(end),
                center=[0., 0.], width=.183, layers=['F.Cu'])


def limits():
    return dict(schema_version=1, scope='test pair', nominal_gap_mm=.1524,
                maximum_rounding_tolerance_mm=.000002,
                paired_corner_leg_tolerance_mm=.000025,
                maximum_sample_step_mm=.005,
                outside_uncoupled_rounding_length_mm=.000001,
                pairs=[dict(stem='TEST', widths_by_layer={'F.Cu': [.183]})],
                regions=[])


class CouplingTests(unittest.TestCase):
    def setUp(self):
        self.data = dict(source_sha256='synthetic', items=[
            track('p', 'P', [0, 0], [10, 0]),
            track('n', 'N', [0, .3354], [10, .3354])])

    def test_nominal_pair(self):
        self.assertEqual(check(self.data, limits())['status'], 'passed')

    def inner_layer_pair(self, gap=.203):
        data = copy.deepcopy(self.data)
        for polarity, y in [('P', 0.), ('N', .111+gap)]:
            item = track('inner_'+polarity, polarity, [20., y], [30., y])
            item.update(width=.111, layers=['In2.Cu'])
            data['items'].append(item)
        spec = limits()
        spec['pairs'][0]['widths_by_layer']['In2.Cu'] = [.111]
        spec['nominal_gap_by_layer_mm'] = {'In2.Cu': .203}
        return data, spec

    def test_inner_layer_can_use_its_own_nominal_gap(self):
        data, spec = self.inner_layer_pair()
        result = check(data, spec)
        self.assertEqual(result['status'], 'passed')
        measured = {row['layer']: row['minimum_gap_floor_mm']
                    for row in result['minimum_gaps']}
        self.assertAlmostEqual(measured['F.Cu'], .1524-.000025)
        self.assertAlmostEqual(measured['In2.Cu'], .203-.000025)

    def test_outer_gap_does_not_pass_for_inner_tracks(self):
        data, spec = self.inner_layer_pair(.2032)
        result = check(data, spec)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['outside_region_uncoupled'])
        self.assertTrue(all(row['layer'] == 'In2.Cu'
                            for row in result['outside_region_uncoupled']))

    def test_inner_minimum_gap_is_still_enforced(self):
        data, spec = self.inner_layer_pair(.202)
        result = check(data, spec)
        self.assertTrue(any(row['kind'] == 'minimum_gap'
                            for row in result['blocking_findings']))

    def test_layer_gap_rejects_invalid_values_and_unknown_layers(self):
        data, spec = self.inner_layer_pair()
        for mapping in [{'In2.Cu': 0}, {'In2.Cu': -1}, {'In2.Cu': float('nan')},
                        {'In2.Cu': True}, {'In4.Cu': .203}, []]:
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                check(data, dict(spec, nominal_gap_by_layer_mm=mapping))

    def test_paired_corner_uses_the_layer_gap(self):
        pitch = .111+.203
        points = {
            'P': [[0, 0], [5, 0], [10, 5]],
            'N': [[0, pitch], [5-pitch*(math.sqrt(2)-1), pitch],
                  [10-pitch/math.sqrt(2), 5+pitch/math.sqrt(2)]],
        }
        items = []
        for polarity, vertices in points.items():
            for index, (a, b) in enumerate(zip(vertices, vertices[1:])):
                item = track(polarity+str(index), polarity, a, b)
                item.update(width=.111, layers=['In2.Cu'])
                items.append(item)
        self.assertEqual(automatic_corners(items, .1524, .000025), [])
        corners = automatic_corners(items, .1524, .000025, {'In2.Cu': .203})
        self.assertEqual(len(corners), 2)
        for corner in corners:
            self.assertAlmostEqual(corner['automatic_corner_radius_mm'],
                                   pitch*math.tan(math.pi/8)+.008)

    def test_explicit_usb_names_keep_the_full_gap_check(self):
        self.data['items'][0]['net'] = 'TEST_DP'
        self.data['items'][1]['net'] = 'TEST_DN'
        spec = limits()
        spec['pairs'][0]['nets'] = {'P': 'TEST_DP', 'N': 'TEST_DN'}
        before = copy.deepcopy(self.data)
        self.assertEqual(check(self.data, spec)['status'], 'passed')
        self.assertEqual(self.data, before)
        self.data['items'][1]['start'][1] = .4
        self.data['items'][1]['end'][1] = .4
        result = check(self.data, spec)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['outside_region_uncoupled'])

    def corner_with_nearby_via_approach(self):
        pitch = .3354
        vertices = {
            'P': [[0., 0.], [5., 0.], [10., 5.]],
            'N': [[0., pitch], [5.-pitch*(math.sqrt(2)-1), pitch],
                  [10.-pitch/math.sqrt(2), 5.+pitch/math.sqrt(2)]],
        }
        items = [track(pol+str(i), pol, a, b)
                 for pol, points in vertices.items()
                 for i, (a, b) in enumerate(zip(points, points[1:]))]
        items.append(track('via approach', 'P', [4.90, -.12], [5.10, -.12]))
        spec = limits()
        spec['regions'] = [dict(name='local via approach', category='via_fanout',
            stem='TEST', layer='F.Cu', bounds_mm=[4.89, -.131, 5.111, -.109],
            max_nearest_gap_mm=.4, max_total_length_mm={'P': .201, 'N': 0.},
            max_uncoupled_length_mm={'P': .201, 'N': 0.})]
        return dict(source_sha256='corner and via', items=items), spec

    def test_explicit_via_region_overlapping_automatic_corner(self):
        data, spec = self.corner_with_nearby_via_approach()
        self.assertEqual(check(data, spec)['status'], 'passed')
        spec['regions'] = []
        result = check(data, spec)
        self.assertTrue(any(v['kind'] == 'region_maximum_gap'
                            for v in result['blocking_findings']))

    def test_explicit_region_only_clips_its_actual_overlap(self):
        data, spec = self.corner_with_nearby_via_approach()
        spec['regions'][0]['bounds_mm'][2] = 5.
        result = check(data, spec)
        self.assertTrue(any(v['kind'] == 'region_maximum_gap'
                            and v['region'].startswith('paired corner')
                            for v in result['blocking_findings']))

    def test_explicit_region_keeps_its_own_length_and_gap_limits(self):
        data, spec = self.corner_with_nearby_via_approach()
        spec['regions'][0]['max_total_length_mm']['P'] = .1
        spec['regions'][0]['max_nearest_gap_mm'] = .1
        kinds = {v['kind'] for v in check(data, spec)['blocking_findings']}
        self.assertIn('region_length', kinds)
        self.assertIn('region_maximum_gap', kinds)

    def test_explicit_region_does_not_relax_the_minimum_gap(self):
        data, spec = self.corner_with_nearby_via_approach()
        data['items'][-1]['start'][1] = .1
        data['items'][-1]['end'][1] = .1
        spec['regions'][0]['bounds_mm'][1::2] = [.09, .11]
        result = check(data, spec)
        self.assertTrue(any(v['kind'] == 'minimum_gap'
                            for v in result['blocking_findings']))

    def test_explicit_region_cannot_impersonate_an_inferred_corner(self):
        data, spec = self.corner_with_nearby_via_approach()
        corners = automatic_corners(data['items'], spec['nominal_gap_mm'],
                                    spec['paired_corner_leg_tolerance_mm'])
        self.assertTrue(corners)
        spec['regions'][0]['name'] = corners[0]['name']
        with self.assertRaisesRegex(ValueError, 'unique names'):
            check(data, spec)

    def test_duplicate_explicit_regions_are_rejected(self):
        data, spec = self.corner_with_nearby_via_approach()
        spec['regions'].append(copy.deepcopy(spec['regions'][0]))
        with self.assertRaisesRegex(ValueError, 'unique names'):
            check(data, spec)

    def test_explicit_usb_names_require_both_polarities(self):
        self.data['items'][0]['net'] = 'TEST_DP'
        self.data['items'][1]['net'] = 'DIFFERENT_DN'
        spec = limits()
        spec['pairs'][0]['nets'] = {'P': 'TEST_DP', 'N': 'TEST_DN'}
        result = check(self.data, spec)
        self.assertTrue(any(row['kind'] == 'missing_polarity'
                            for row in result['blocking_findings']))

    def test_window_does_not_exempt_the_rest_of_a_long_track(self):
        self.data['items'][1]['start'][1] = .4
        self.data['items'][1]['end'][1] = .4
        spec = limits()
        spec['regions'] = [dict(name='middle two millimetres', category='via_fanout',
            stem='TEST', layer='F.Cu', bounds_mm=[4, -.1, 6, .6],
            max_nearest_gap_mm=.3, max_total_length_mm={'P': 2.01, 'N': 2.01},
            max_uncoupled_length_mm={'P': 2.01, 'N': 2.01})]
        result = check(self.data, spec)
        self.assertEqual(result['status'], 'failed')
        for polarity in ['P', 'N']:
            length = sum(row['length_mm'] for row in result['outside_region_uncoupled']
                         if row['net'] == 'TEST_'+polarity)
            self.assertAlmostEqual(length, 8.)

    def test_width_change_fails_inside_a_window(self):
        self.data['items'][0]['width'] = .2
        self.assertTrue(any(row['kind'] == 'width_or_layer'
                            for row in check(self.data, limits())['blocking_findings']))

    def test_exact_arc_pair_and_rectangle_clip(self):
        first = arc('p', 'P', 10)
        second = arc('n', 'N', 10.3354)
        self.assertEqual(check(dict(source_sha256='arcs', items=[first, second]),
                               limits())['status'], 'passed')
        clipped = Curve(first).inside(box(-.1, -.1, 10/math.sqrt(2), 10.1))
        self.assertAlmostEqual(clipped[0][0], .5, places=11)
        self.assertEqual(clipped[0][1], 1.)

    def test_finite_arc_endpoint_coverage(self):
        first = Curve(arc('p', 'P', 10))
        second = Curve(arc('n', 'N', 10, math.pi/6, math.pi/3))
        actual = first.capsule_coverage(second, .1)[0]
        angle = 2*math.asin(.1/20)
        self.assertAlmostEqual(actual[0], (math.pi/6-angle)/(math.pi/2), places=11)
        self.assertAlmostEqual(actual[1], (math.pi/3+angle)/(math.pi/2), places=11)

    def test_widened_arc_fails_over_its_full_length(self):
        data = dict(source_sha256='bad arcs', items=[arc('p', 'P', 10),
                                                    arc('n', 'N', 10.4)])
        result = check(data, limits())
        self.assertEqual(result['status'], 'failed')
        for row in result['outside_region_uncoupled']:
            radius = 10 if row['net'] == 'TEST_P' else 10.4
            self.assertAlmostEqual(row['length_mm'], radius*math.pi/2, places=8)

    def test_incomplete_arc_fails(self):
        self.data['items'][0]['type'] = 'PCB_ARC'
        self.assertTrue(any(row['kind'] == 'invalid_curve'
                            for row in check(self.data, limits())['blocking_findings']))


class PathTests(unittest.TestCase):
    def setUp(self):
        self.data = dict(source_sha256='paths', items=[])
        self.definition = [dict(name='test signal', nets={'P': ['TEST_P'], 'N': ['TEST_N']},
            endpoints={'TEST_P': ['A1.1', 'J10.1'], 'TEST_N': ['A1.2', 'J10.2']},
            max_pn_difference_mm=.127, via_transition_count=0)]
        for polarity, number, y in [('P', '1', 0.), ('N', '2', .3354)]:
            key = polarity.lower()
            copper = track(key, polarity, [0, y], [10, y])
            copper['neighbors'] = [key+'a', key+'b']
            self.data['items'].append(copper)
            for suffix, ref, x in [('a', 'A1', 0.), ('b', 'J10', 10.)]:
                self.data['items'].append(dict(id=key+suffix, type='PAD', net='TEST_'+polarity,
                    ref=ref, number=number, start=[x, y], end=[x, y], layers=['F.Cu'],
                    length=0., neighbors=[key], native_component_pad_ids=[key+'a', key+'b'],
                    box=[x-.1, y-.1, x+.1, y+.1]))

    def test_complete_signal(self):
        self.assertEqual(check_paths(self.data, self.definition)['status'], 'passed')

    def test_missing_leg_fails(self):
        self.data['items'] = [row for row in self.data['items'] if row['id'] != 'p']
        for row in self.data['items']:
            if row['type'] == 'PAD' and row['net'] == 'TEST_P':
                row['neighbors'] = []
                row['native_component_pad_ids'] = [row['id']]
        result = check_paths(self.data, self.definition)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(any(row['kind'] == 'incomplete_signal_path'
                            for row in result['blocking_findings']))

    def test_wrong_endpoint_fails(self):
        next(row for row in self.data['items'] if row['id'] == 'pb')['number'] = '9'
        self.assertEqual(check_paths(self.data, self.definition)['status'], 'failed')

    def test_duplicate_copper_fails(self):
        duplicate = copy.deepcopy(self.data['items'][0])
        duplicate['id'] = 'duplicate'
        self.data['items'].append(duplicate)
        result = check_paths(self.data, self.definition)
        self.assertTrue(any(row['kind'] == 'duplicate_copper'
                            for row in result['blocking_findings']))


if __name__ == '__main__':
    unittest.main()

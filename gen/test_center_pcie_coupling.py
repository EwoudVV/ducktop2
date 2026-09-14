"""Regression checks for local PCIe limits and complete signal paths."""
import copy
import math
import unittest

from shapely.geometry import box
from check_center_pcie_coupling import check
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

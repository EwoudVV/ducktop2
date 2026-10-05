"""Force-path failures that electrical connectivity cannot detect."""
import unittest

from shapely.geometry import box
from shapely.ops import unary_union

from bms_power_paths import check_bulk_path


class ForcePaths(unittest.TestCase):
    def setUp(self):
        self.path = [(0, 0), (10, 0)]
        self.pour = box(-1, -1.5, 11, 1.5)

    def test_continuous_three_mm_pour_passes(self):
        result = check_bulk_path(self.pour, self.path, 3, 'VIN')
        self.assertAlmostEqual(result['sampled_width_mm'], 3)

    def test_connected_neck_fails_width(self):
        copper = unary_union([box(-1, -1.5, 4, 1.5), box(4, -.2, 6, .2), box(6, -1.5, 11, 1.5)])
        self.assertTrue(copper.covers(box(0, -.1, 10, .1)))
        with self.assertRaisesRegex(RuntimeError, 'too narrow'):
            check_bulk_path(copper, self.path, 3, 'VIN')

    def test_foreign_via_clearance_cut_fails(self):
        from shapely.geometry import Point
        copper = self.pour.difference(Point(5, 0).buffer(.4))
        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            check_bulk_path(copper, self.path, 3, 'COMMON')

    def test_gap_smaller_than_sample_spacing_fails(self):
        copper = self.pour.difference(box(5.031, -2, 5.032, 2))
        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            check_bulk_path(copper, self.path, 3, 'VIN')

    def test_native_rounding_is_allowed(self):
        copper = box(-1, -1.4999995, 11, 1.4999995)
        check_bulk_path(copper, self.path, 3, 'VIN')

    def test_broad_pour_beside_path_cannot_hide_a_thin_route(self):
        copper = unary_union([box(-1, -.1, 11, .1), box(-1, 1, 11, 4)])
        with self.assertRaisesRegex(RuntimeError, 'too narrow'):
            check_bulk_path(copper, self.path, 3, 'VIN')


if __name__ == '__main__':
    unittest.main()

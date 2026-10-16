import re
import unittest
from generate_tpd1s514_footprint import footprint
from verify_tpd1s514_footprint import validate


class TPD1S514FootprintTests(unittest.TestCase):
    def test_manufacturer_land_mask_and_stencil_pattern(self):
        self.assertTrue(validate(footprint())["passed"])

    def test_old_half_mm_grid_is_rejected(self):
        old = re.sub(r'\(at\s+([-\d.]+)\s+([-\d.]+)',
                     lambda m: f'(at {float(m[1])*1.25:g} {float(m[2])*1.25:g}', footprint())
        self.assertFalse(validate(old)["passed"])

    def test_old_copper_diameter_is_rejected(self):
        self.assertFalse(validate(footprint().replace('(size 0.225 0.225)', '(size 0.24 0.24)'))["passed"])

    def test_missing_corner_ball_is_rejected(self):
        self.assertFalse(validate(footprint().replace('(pad "A1"', '(pad "A9"'))["passed"])

    def test_merged_mask_openings_are_rejected(self):
        self.assertFalse(validate(footprint().replace('(solder_mask_margin 0.0375)', '(solder_mask_margin 0.1)'))["passed"])

    def test_paste_does_not_follow_the_smaller_copper_disc(self):
        self.assertFalse(validate(footprint().replace('(size 0.25 0.25)', '(size 0.225 0.225)'))["passed"])


if __name__ == "__main__": unittest.main()

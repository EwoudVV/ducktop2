"""Check real lining material, cap stops and the guard screw withdrawal."""
import unittest

import cadquery as cq
import display_hinge_study as study
import display_grips as grips
from review import intersection_volume


class DisplayGrips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts, _ = study.geometry()
        cls.by_name = {p['name']: p for p in cls.parts}

    def test_liners_have_material_and_clear_the_nominal_cable(self):
        for role, x in [('base', 225), ('lid', 163)]:
            gauge = grips.nominal_gauge(x)
            for p in self.parts:
                if p.get('grip_liner') != role:
                    continue
                self.assertTrue(p['shape'].isValid())
                self.assertEqual(len(p['shape'].Solids()), 1)
                self.assertGreater(p['shape'].Volume(), 10)
                self.assertLess(intersection_volume(p['shape'], gauge), 1e-6)
                self.assertAlmostEqual(p['shape'].distance(gauge), .05, places=6)

    def test_position_allowance_is_distinct_from_nominal_cable(self):
        p = self.by_name['display-base-liner-upper']
        c = self.by_name['display-axis-flex-space']
        self.assertGreater(intersection_volume(p['shape'], c['shape']), 1)
        self.assertTrue(grips.allocated_liner_overlap(p, c))
        self.assertFalse(grips.allocated_liner_overlap(p, self.by_name['display-rear-guard']))
        self.assertFalse(grips.allocated_liner_overlap(p, self.by_name['display-lid-tail-space']))

    def test_caps_close_against_their_saddles(self):
        for role, sign in [('base', -1), ('lid', 1)]:
            cap = self.by_name[f'display-{role}-anchor-cap']['shape']
            saddle = self.by_name[f'display-{role}-anchor-saddle']['shape']
            self.assertLess(cap.distance(saddle), 1e-6)
            self.assertLess(intersection_volume(cap, saddle), 1e-6)
            self.assertGreater(intersection_volume(cap.translate((0, 0, sign*.1)), saddle), 1)

    def test_guard_hardware_can_clear_the_cable_on_removal(self):
        cable = [p for p in self.parts if p['name'] in ['display-base-bundle-space', 'display-axis-flex-space']]
        for p in self.parts:
            if not p['name'].startswith(('display-guard-screw-', 'display-guard-washer-')):
                continue
            for travel in range(0, 13):
                shape = p['shape'].translate((0, 0, travel))
                for q in cable:
                    self.assertLess(study.overlap(shape, q['shape'])[0], .01, (p['name'], travel, q['name']))

    def test_cap_screws_clear_the_jaw_material(self):
        for role in ['base', 'lid']:
            host = [self.by_name[f'display-{role}-anchor-{part}']['shape'] for part in ['cap', 'saddle']]
            for i in range(2):
                screw = self.by_name[f'display-{role}-cap-screw-{i}']['shape']
                for body in host:
                    self.assertLess(intersection_volume(screw, body), 1e-6)

    def test_moving_mount_screws_finish_inside_the_tongue(self):
        for i in range(2):
            screw = self.by_name[f'display-lid-mount-screw-{i}']['shape'].BoundingBox()
            self.assertGreater(screw.zmin, 25.3+.7)
            self.assertLess(screw.zmin, 29.3-3)

    def test_liner_can_lift_past_the_rear_wall(self):
        wall=study.box(210,-18,1.2,40,1.2,22.6)
        changed,_=study.study_case_parts([{'name':'base-walls','shape':wall}])
        liner=self.by_name['display-base-liner-upper']['shape']
        self.assertGreater(intersection_volume(liner.translate((0,0,4)),wall),.1)
        for half_mm in range(0,17):
            self.assertLess(intersection_volume(liner.translate((0,0,half_mm/2)),changed[0]['shape']),1e-6)

    def test_guard_removal_finishes_outside_the_case(self):
        guard=self.by_name['display-rear-guard']['shape']
        removed=guard.translate((0,grips.config()['guard_rearward_removal_mm'],0)).BoundingBox()
        self.assertLess(-removed.ymin,-18)


if __name__ == '__main__':
    unittest.main()

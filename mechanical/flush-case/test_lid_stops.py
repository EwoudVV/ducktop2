"""Catch early stop contact, screw clashes and missing mounting reliefs."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_cooler
import lid_stops
from cad import box, cylinder
from review import intersection_volume


class LidStops(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = lid_stops.make_parts()
        cls.by_name = {p['name']: p for p in cls.parts}
        cls.case = json.loads((HERE/'assembly.json').read_text())

    def test_both_stops_contact_at_the_requested_angle(self):
        for side in ['left', 'right']:
            tab = self.by_name[side+'-lid-stop-tab']
            stop = self.by_name[side+'-lid-stop-block']['shape']
            before = lid_stops.pose(tab, 134.9)['shape']
            at = lid_stops.pose(tab, 135)['shape']
            after = lid_stops.pose(tab, 135.1)['shape']
            self.assertGreater(before.distance(stop), .01)
            self.assertLess(at.distance(stop), 1e-6)
            self.assertLess(intersection_volume(at, stop), 1e-6)
            self.assertGreater(intersection_volume(after, stop), .1)

    def test_mounting_hardware_clears_the_opposite_half(self):
        for p in self.parts:
            if not p.get('moving'):
                continue
            for q in self.parts:
                if q.get('moving') or q['name'].split('-')[0] != p['name'].split('-')[0]:
                    continue
                for angle in [0, 44, 50, 90, 130, 135]:
                    self.assertLess(intersection_volume(lid_stops.pose(p, angle)['shape'], q['shape']), .01,
                                    (p['name'], q['name'], angle))

    def test_old_underside_head_is_not_accepted(self):
        head = {'shape': cylinder(63, -3, 22, 2.85, 1.8), 'moving': True}
        self.assertGreater(intersection_volume(lid_stops.pose(head, 44)['shape'],
                                              self.by_name['left-lid-stop-block']['shape']), .01)

    def test_endpoint_is_included_with_two_degree_steps(self):
        samples = lid_stops.angles(self.case)
        self.assertEqual(samples[-2:], [134, 135])
        self.assertEqual(len(samples), 69)
        self.assertNotIn(136, samples)

    def test_thread_bores_do_not_hollow_the_curved_tab(self):
        lower_arc = cylinder(64, -3, 19, .2, 1)
        tab = self.by_name['left-lid-stop-tab']['shape']
        self.assertAlmostEqual(intersection_volume(lower_arc, tab), lower_arc.Volume(), places=6)

    def test_screw_tips_stay_inside_their_supports(self):
        s = lid_stops.fastener_stacks()
        self.assertGreater(s['base_tip_to_floor_after_screw_and_washer_tolerances_mm'], 1)
        self.assertGreater(s['lid_tip_to_root_bottom_minimum_mm'], 1)
        self.assertGreater(s['base_engagement_screw_and_washer_range_mm'][0], 4)
        self.assertGreater(s['lid_engagement_with_length_and_seating_budget_mm'][0], 2)

    def test_reliefs_and_thread_cavities_remove_material(self):
        originals = [
            {'name': 'base-walls', 'shape': box(0, -18, 1.2, 358, 1.2, 22.6)},
            {'name': 'deck', 'shape': box(0, -18, 23.8, 358, 32, 1.2)},
            {'name': 'rear-base-reinforcement', 'shape': box(0, -16, 1.2, 358, 14, 3)},
            {'name': 'rear-lid-backing-member', 'shape': box(0, -18, 29.3, 358, 31, 3)}]
        adapted, changes = lid_stops.adapt_case(originals, self.case)
        by_name = {p['name']: p['shape'] for p in adapted}
        self.assertEqual(len(changes), 4)
        for change in changes:
            self.assertNotAlmostEqual(change['volume_before_mm3'], change['volume_after_mm3'])
        for x in [68, 290]:
            self.assertLess(intersection_volume(box(x-2, -18, 5, 4, 1, 10), by_name['base-walls']), 1e-6)
            for xx, yy in lid_stops.mount_positions(x)['base']:
                self.assertLess(intersection_volume(cylinder(xx, yy, 1.2, 1.5, 6), by_name['rear-base-reinforcement']), 1e-6)
                self.assertGreater(intersection_volume(cylinder(xx, yy, 4.2, 4, 3), by_name['rear-base-reinforcement']), 100)
            for xx, yy in lid_stops.mount_positions(x)['lid']:
                self.assertLess(intersection_volume(cylinder(xx, yy, 29.3, 1.5, 3), by_name['rear-lid-backing-member']), 1e-6)


if __name__ == '__main__':
    unittest.main()

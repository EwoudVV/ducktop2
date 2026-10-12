"""Regression checks for releasing the keyboard carrier past the fixed fan loom."""
import unittest
import check_cooler
import fan_harness
import fan_guide_mounts as mounts
import remote_cooler
import usb_harness
from cad import box
from review import intersection_volume


class FanGuideMounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=box(41.25,19,20,275.5,82,1).cut(box(306,50,19.9,24,23,1.2))
        cls.base=remote_cooler.carrier_reliefs(usb_harness.carrier_tabs(base))
        cls.carrier=mounts.carrier_shape(cls.base)

    def test_each_guide_remains_one_connected_solid(self):
        self.assertEqual(len(mounts.guides()),5)
        for shape in mounts.guides():
            self.assertTrue(shape.isValid())
            self.assertEqual(len(shape.Solids()),1)

    def test_old_lip_snags_stationary_wire_during_lift(self):
        lip=fan_harness.clip_profiles().Solids()[0].translate((0,0,1))
        wire=fan_harness.geometry()['shape'].intersect(box(144,65,11,8,10,6))
        self.assertGreater(intersection_volume(lip,wire),.05)

    def test_carrier_releases_locating_keys_without_moving_guides(self):
        for lift in [0,.25,.5,.7,1,2]:
            carrier=self.carrier.translate((0,0,lift))
            for guide in mounts.guides():
                self.assertLess(intersection_volume(carrier,guide),.01)

    def test_longest_screw_and_thread_runout_are_included(self):
        c=mounts.config()['screw'];s=mounts.screw(148,105.5).BoundingBox()
        self.assertAlmostEqual(s.zmin,16.96,places=5)
        self.assertAlmostEqual(s.zmax,23.2,places=5)
        seat=mounts.config()['carrier_top_H']
        usable=min(20,seat-c['underhead_thread_runout_allocation_mm'])-(seat-c['nominal_shank_length_mm']+c['length_tolerance_mm'])
        self.assertAlmostEqual(usable,c['minimum_full_thread_overlap_mm'],places=5)
        self.assertGreater(usable,2.5)
        for guide,(x,y) in zip(mounts.guides(),mounts.config()['mounts_xy_mm']):
            self.assertLess(intersection_volume(guide,mounts.screw(x,y)),.01)

    def test_heads_clear_the_existing_keyboard_board(self):
        board=box(42.25,20,21.327,273.5,80,.8)
        for x,y in mounts.config()['mounts_xy_mm']:
            self.assertLess(intersection_volume(board,mounts.screw(x,y)),.01)


if __name__=='__main__':unittest.main()

"""Protect thermal contacts, pipe space and mounting material beside the port."""
import json
import unittest
import display_hinge_study as study
import remote_cooler
from cooling import spreader
from cad import box,cylinder
from review import intersection_volume


class DisplayPlateRelief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=remote_cooler.config()
        cls.d=json.loads((study.ROOT/'mechanical/case-prototype/cooling-datums.json').read_text())
        cls.original=spreader({'spreader_thickness_mm':cls.c['plate']['thickness_mm']},5.5)
        cls.relief=remote_cooler.plate_connector_relief(cls.original)
        cls.removed=cls.original.cut(cls.relief)

    def test_contacts_and_pipe_allowances_are_preserved(self):
        self.assertTrue(self.relief.isValid())
        self.assertEqual(len(self.relief.Solids()),1)
        self.assertGreater(self.removed.Volume(),100)
        self.assertLess(self.removed.Volume(),103)
        for x,y,w,d in [self.d['CPU_contact_xy_mm'],*self.d['memory_regions_xy_mm']]:
            self.assertLess(intersection_volume(self.removed,box(x,y,10,w,d,15)),1e-6)
        for offset in self.c['pipes']['lane_offsets_mm']:
            shape=remote_cooler.pipe_solid(self.c['pipes'],offset,envelope=True,upper_clearance=True)
            self.assertLess(intersection_volume(self.removed,shape),1e-6)

    def test_mounting_reservations_and_hole_ligament_remain(self):
        for x,y in self.d['cooler_mount_centers_xy_mm']:
            self.assertLess(intersection_volume(self.removed,cylinder(x,y,15.737,3.25,3.5)),1e-6)
        x,y=self.d['cooler_mount_centers_xy_mm'][2]
        self.assertGreater(self.removed.distance(cylinder(x,y,15.737,1.1,2)),2.6)


if __name__=='__main__':unittest.main()

"""Check real fan openings, mounting geometry and the base intake."""
import json
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import remote_cooler
import cooler_hardware
from cad import box,cylinder


class CoolerHardware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=remote_cooler.config();cls.h=cooler_hardware.config()
        cls.case=json.loads((HERE/'assembly.json').read_text())
        cls.fan=remote_cooler.fan_model(cls.c)
        cls.floor=cooler_hardware.floor_shape(box(290,110,0,74,76,cls.case['base']['floor']),cls.case)

    def test_outlet_points_toward_fins(self):
        f=self.c['fan'];x,y=f['xy'];h=f['bottom_H']
        port=box(x+43.3,y+2.5,h+1.3,2,34,7.5)
        self.assertLess(port.intersect(self.fan).Volume(),1e-5)
        pivot=(x+22.5,-y-22.5,h+5.15)
        wrong=self.fan.rotate(pivot,(pivot[0],pivot[1]+1,pivot[2]),180)
        self.assertGreater(port.intersect(wrong).Volume(),1)

    def test_inlet_is_open_at_bottom(self):
        x,y=self.h['intake']['centre_xy'];h=self.c['fan']['bottom_H']
        mouth=cylinder(x,y,h-.02,15,.32)
        self.assertLess(mouth.intersect(self.fan).Volume(),1e-5)

    def test_posts_follow_manufacturer_holes(self):
        found=set()
        for face in self.fan.Faces():
            if face.geomType()!='CYLINDER':continue
            s=face._geomAdaptor().Cylinder();b=face.BoundingBox()
            if abs(s.Axis().Direction().Z())>.999 and abs(s.Radius()-1.4)<1e-5 and abs(b.zlen-3.5)<1e-5:
                p=s.Axis().Location();found.add((round(p.X(),4),round(-p.Y(),4),round(b.zmin,4)))
        expected={(x,y,self.h['fan_posts']['top_H']) for x,y in self.h['fan_posts']['centres_xy']}
        self.assertEqual(found,expected)

    def test_separate_spacers_clear_fan(self):
        p=self.h['fan_posts']
        for x,y in p['centres_xy']:
            s=cooler_hardware.annulus(x,y,p['base_top_H'],p['spacer_radius_mm'],1.1,p['spacer_height_mm'])
            self.assertLess(s.intersect(self.fan).Volume(),1e-5)

    def test_fan_thread_engagement_and_floor_margin(self):
        p=self.h['fan_posts'];seat=self.c['fan']['mount_ear_upper_H']+p['washer_thickness_mm']
        tip=seat-p['screw_length_mm'];engagement=p['base_top_H']-tip
        self.assertAlmostEqual(engagement,p['nominal_thread_engagement_mm'])
        self.assertGreaterEqual(engagement-.5,2)
        self.assertGreater(tip-.5,self.case['base']['floor'])

    def test_grille_and_under_fan_space(self):
        a=self.h['intake'];x,y=a['centre_xy'];disc=cylinder(x,y,.1,a['floor_opening_radius_mm'],.1)
        area=disc.cut(self.floor).Volume()/.1
        self.assertGreater(area,400)
        self.assertGreaterEqual(a['fan_bottom_range_H'][0]-a['cross_rib_top_H'],3)
        self.assertTrue(self.floor.isValid())
        self.assertEqual(len(self.floor.Solids()),1)


if __name__=='__main__':unittest.main()

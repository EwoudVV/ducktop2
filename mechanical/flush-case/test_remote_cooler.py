"""Check stock length, fit envelopes and wire-bound rejection for the cooler."""
import sys
import unittest
from pathlib import Path

import numpy as np
from shapely import covers, points

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import remote_cooler as cooler
from usb_collision import Checks


class CoolerGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=cooler.config()['pipes']
        cls.nominal=[cooler.pipe_solid(cls.spec,d) for d in cls.spec['lane_offsets_mm']]
        cls.limits=[cooler.pipe_solid(cls.spec,d,envelope=True) for d in cls.spec['lane_offsets_mm']]
        cls.parts=[{'name':f'pipe-{i}','shape':s,'remote_pipe_offset':d,'remote_pipe_envelope':True}
                   for i,(s,d) in enumerate(zip(cls.limits,cls.spec['lane_offsets_mm']))]
        cooler.register_shapes(cls.parts)

    def test_full_stock_volume(self):
        expected=self.spec['stock_length_mm']*self.spec['width_mm']*self.spec['height_mm']
        for s in self.nominal:
            self.assertTrue(s.isValid())
            self.assertEqual(len(s.Solids()),1)
            self.assertAlmostEqual(s.Volume(),expected,places=4)

    def test_maximum_envelope_contains_nominal_pipe(self):
        for actual,limit in zip(self.nominal,self.limits):
            self.assertLess(actual.cut(limit).Volume(),1e-5)

    def test_lanes_do_not_intersect(self):
        self.assertLess(self.limits[0].intersect(self.limits[1]).Volume(),1e-5)

    def test_pipe_end_tolerance_is_retained(self):
        for offset in self.spec['lane_offsets_mm']:
            ends=[]
            for delta in [-5,0,5]:
                p,r=cooler.pipe_path(self.spec,offset,250+delta)
                self.assertAlmostEqual(r['analytic_length_mm'],250+delta)
                self.assertLess(abs(r['sampled_length_mm']-(250+delta)),.001)
                ends.append(p[-1][1])
            self.assertAlmostEqual(ends[1]-ends[0],5)
            self.assertAlmostEqual(ends[2]-ends[1],5)

    def test_plan_bound_covers_CAD_surface_samples(self):
        for s in self.limits:
            vertices,_=s.tessellate(.01,.025)
            xy=np.array([[v.x,-v.y] for v in vertices])
            self.assertTrue(covers(cooler.planar_bound(s),points(xy)).all())

    def test_wire_rejection_keeps_real_contacts(self):
        target=self.parts[0]
        checker=Checks.__new__(Checks);checker.pieces={};checker.rigid={};checker.old={}
        shape=checker.get_pieces(target)[0]['shape']
        # All three cubes lie inside the pipe's broad XYZ box. Only the first
        # touches its actual route; this catches loss of the registered plan.
        samples=[([275,-94.5,18],True),([275,-120,18],False),([275,-94.5,13],False)]
        for center,expected in samples:
            point=np.array([center],dtype=float)
            checker.envelope=lambda *args,p=point:(p-.6,p+.6)
            self.assertEqual(checker.curve_might_meet({'curve':'test','guide':False,'clip':None},shape),expected)


if __name__=='__main__':unittest.main()

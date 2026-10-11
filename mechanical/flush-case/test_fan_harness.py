"""Keep the swept soft liner hollow without a tube-subtraction Boolean."""
import math,sys,unittest
from pathlib import Path
import numpy as np
import cadquery as cq

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'case-prototype'))
import fan_harness
from cables import path_edge


class FanLiner(unittest.TestCase):
    def test_straight_liner_has_open_core(self):
        p=[[0,0,0],[5,0,0],[10,0,0]]
        s=fan_harness.hollow_sweep(p,1.9,1.65)
        core=cq.Solid.makeCylinder(1.6,8,cq.Vector(1,0,0),cq.Vector(1,0,0))
        self.assertTrue(s.isValid())
        self.assertEqual(len(s.Solids()),1)
        self.assertLess(s.intersect(core).Volume(),1e-6)
        self.assertAlmostEqual(s.Volume(),math.pi*(1.9**2-1.65**2)*10,places=5)

    def test_curved_liner_retains_annular_volume(self):
        p=[[20*math.sin(t),20*(1-math.cos(t)),0] for t in np.linspace(0,math.pi/4,25)]
        s=fan_harness.hollow_sweep(p,1.9,1.65)
        expected=math.pi*(1.9**2-1.65**2)*path_edge(p).Length()
        self.assertTrue(s.isValid())
        self.assertEqual(len(s.Solids()),1)
        self.assertAlmostEqual(s.Volume(),expected,delta=.02)

    def test_floor_clipping_keeps_real_overlap(self):
        from fan_harness_checks import floor_cable_overlap
        from cad import box
        floor=box(0,0,0,30,20,1.2).fuse(box(10,5,1.2,5,5,10))
        wire=box(0,6,8,25,1,1)
        self.assertAlmostEqual(floor_cable_overlap(floor,wire),floor.intersect(wire).Volume(),places=5)
        self.assertGreater(floor_cable_overlap(floor,wire),4.9)

    def test_floor_clipping_keeps_clear_route_clear(self):
        from fan_harness_checks import floor_cable_overlap
        from cad import box
        floor=box(0,0,0,30,20,1.2).fuse(box(10,5,1.2,5,5,10))
        wire=box(0,14,8,25,1,1)
        self.assertLess(floor_cable_overlap(floor,wire),1e-6)

    def test_carrier_bounds_include_added_crossover_guide(self):
        from usb_collision import Checks
        from cad import box
        checker=Checks.__new__(Checks);checker.pieces={};checker.case={'fan_harness':True};checker.old={};checker.rigid={}
        part={'name':'keyboard-carrier-reservation','shape':box(41.25,19,20,275.5,82,1)}
        probe=box(276.9,102.9,20.7,.2,.2,.2)
        self.assertTrue(any(p['shape'].intersect(probe).Volume()>.007 for p in checker.get_pieces(part)))

    def test_translated_liner_core_and_volume(self):
        p=[[310,179,11.5],[314,179,11.5],[318,179,11.5]]
        s=fan_harness.hollow_sweep(p,1.9,1.65)
        core=cq.Solid.makeCylinder(1.6,6,cq.Vector(311,-179,11.5),cq.Vector(1,0,0))
        self.assertLess(s.intersect(core).Volume(),1e-6)
        self.assertAlmostEqual(s.Volume(),math.pi*(1.9**2-1.65**2)*8,places=5)

    def test_actual_clamp_liner_retains_material(self):
        route=fan_harness.route_points()
        p=route[(route[:,0]>=310.5)&(route[:,0]<=318.5)&(abs(route[:,1]-179)<1e-6)][::5]
        s=fan_harness.hollow_sweep(p,1.9,1.65)
        expected=math.pi*(1.9**2-1.65**2)*path_edge(p).Length()
        self.assertTrue(s.isValid())
        self.assertEqual(len(s.Solids()),1)
        self.assertAlmostEqual(s.Volume(),expected,delta=.02)


if __name__=='__main__':unittest.main()

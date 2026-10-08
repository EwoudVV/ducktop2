"""Keep a sealed stock pipe's length and tolerances in the cooler fit model."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mechanical/case-prototype'))
from cooling import heatpipe, heatpipe_path
from cooling_selection import verify_pipe_config


class PipeGeometryTests(unittest.TestCase):
    def setUp(self):
        self.c={'heatpipe':[58.44355,7.4,19.037,181.55645,53.2,3.5],
                'heatpipe_width_mm':11.2,'heatpipe_turn_radius_mm':27,
                'heatpipe_turn_angle_deg':60,'heatpipe_hot_end_xy':[240,55],
                'heatpipe_bend_start_xy':[202,55],'heatpipe_end_y_mm':13,
                'heatpipe_nominal_length_mm':200,'heatpipe_length_tolerance_mm':4,
                'heatpipe_width_tolerance_mm':.5,'heatpipe_height_tolerance_mm':.5,
                'heatpipe_position_allowance_mm':.2,'heatpipe_upper_clearance_mm':.3}

    def test_full_stock_length_is_retained(self):
        pts,data=heatpipe_path(self.c)
        length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        self.assertEqual(data['length_mm'],200)
        self.assertAlmostEqual(length,200,delta=.002)
        self.assertAlmostEqual(pts[-1][0],58.4435499981)

    def test_length_variation_stays_at_cold_end(self):
        nominal,_=heatpipe_path(self.c)
        longer,_=heatpipe_path(self.c,204)
        self.assertEqual(nominal[:-1],longer[:-1])
        self.assertAlmostEqual(nominal[-1][0]-longer[-1][0],4)

    def test_short_stock_does_not_get_stretched(self):
        with self.assertRaises(ValueError):heatpipe_path(self.c,70)

    def test_bends_cannot_overlap(self):
        bad=copy.deepcopy(self.c);bad['heatpipe_end_y_mm']=50
        with self.assertRaises(ValueError):heatpipe_path(bad)

    def test_tolerance_volume_contains_nominal_part(self):
        nominal=heatpipe(self.c);envelope=heatpipe(self.c,tolerance=True)
        self.assertLess(abs(nominal.cut(envelope).Volume()),1e-6)
        self.assertAlmostEqual(envelope.BoundingBox().zmax,23.337,places=5)
        self.assertAlmostEqual(envelope.BoundingBox().xmin,54.24355,places=4)

    def test_inside_radius_has_space_for_maximum_width(self):
        data={'heatpipe':{'part':'test','length_mm':200,'width_mm':11.2,'height_mm':3.5,
                         'length_tolerance_mm':4,'width_tolerance_mm':.5,'height_tolerance_mm':.5,
                         'catalogue_bend_radius_for_7mm_mm':21}}
        self.c['heatpipe_part']='test'
        self.assertGreaterEqual(verify_pipe_config(self.c,data),21)
        self.c['heatpipe_turn_radius_mm']=18
        with self.assertRaises(ValueError):verify_pipe_config(self.c,data)


if __name__=='__main__':unittest.main()

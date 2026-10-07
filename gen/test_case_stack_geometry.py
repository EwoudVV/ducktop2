"""Keep remote wire peaks and closed-tube assumptions out of the local stack."""
import copy
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mechanical/case-prototype'))
from stack_geometry import trackpad_cable_ceiling


class StackGeometryTests(unittest.TestCase):
    def setUp(self):
        self.config={'trackpad':{'x':40,'y':40,'width':20,'depth':20},
                     'cables':{'guide_radial_clearance':.15,'guide_wall':.4}}
        self.route={'name':'test','group':'main','wire_od_mm':2,
                    'points':[[float(x),50.,10.] for x in np.arange(0,101,.25)]}

    def test_distant_high_point_does_not_set_trackpad_height(self):
        outside=copy.deepcopy(self.route)
        outside.update(name='remote',points=[[float(x),0.,30.] for x in np.arange(0,101,.25)])
        a=trackpad_cable_ceiling(self.config,{'routes':[self.route]})
        b=trackpad_cable_ceiling(self.config,{'routes':[self.route,outside]})
        self.assertEqual(a['limiting_crossing'],b['limiting_crossing'])

    def test_guide_upper_lips_are_below_a_closed_tube_top(self):
        a=trackpad_cable_ceiling(self.config,{'routes':[self.route]})
        top=a['limiting_crossing']['top_height_mm']
        self.assertGreater(top,11.2)
        self.assertLess(top,11.4)
        self.assertLess(top,10+1+.15+.4+.2)

    def test_lowering_wire_in_support_area_lowers_local_stack(self):
        route=copy.deepcopy(self.route)
        route['points']=[[x,y,z-1] for x,y,z in route['points']]
        a=trackpad_cable_ceiling(self.config,{'routes':[self.route]})
        b=trackpad_cable_ceiling(self.config,{'routes':[route]})
        self.assertAlmostEqual(a['limiting_crossing']['top_height_mm']-b['limiting_crossing']['top_height_mm'],1)


if __name__=='__main__':unittest.main()

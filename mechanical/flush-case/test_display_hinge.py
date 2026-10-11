"""Regression checks for the partial display-cable geometry."""
import json
import unittest

import cadquery as cq
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
import display_hinge_study as study


class DisplayHingeGeometry(unittest.TestCase):
    def test_free_span_excludes_both_grips(self):
        c=study.config()
        fixed=study.anchor(c['fixed_anchor_xyH'][0],False)[1]['shape'].BoundingBox()
        moving=study.anchor(c['lid_anchor_xyH_closed'][0],True)[1]['shape'].BoundingBox()
        self.assertAlmostEqual(fixed.xmin-moving.xmax,50,places=6)
        self.assertAlmostEqual(c['axial_free_span_mm'],fixed.xmin-moving.xmax,places=6)

    def test_first_lid_bend_is_outside_the_grip(self):
        c=study.config();p=study.lid_tail()
        end=c['lid_anchor_xyH_closed'][0]-c['anchor_grip_length_mm']/2
        gripped=p[p[:,0]>=end]
        self.assertTrue(np.allclose(gripped[:,1:],[-15,19.3]))
        bent=p[np.abs(p[:,2]-19.3)>1e-6]
        self.assertLessEqual(float(bent[:,0].max()),end-1)

    def test_axis_section_stays_on_axis_when_the_lid_rotates(self):
        c=study.config();x=c['lid_anchor_xyH_closed'][0]
        length=c['axial_anchor_pitch_mm']
        s=cq.Solid.makeCylinder(1.8,length,cq.Vector(x,15,19.3),cq.Vector(1,0,0))
        b=s.BoundingBox();expected=np.array([b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax])
        for angle in [0,17,60,105,140]:
            moved=study.pose({'shape':s,'moving':True},angle)['shape'].BoundingBox()
            actual=[moved.xmin,moved.xmax,moved.ymin,moved.ymax,moved.zmin,moved.zmax]
            self.assertTrue(np.allclose(actual,expected,atol=1e-6),angle)

    def test_module_route_joins_the_fixed_grip_tangentially(self):
        p=study.route_points()
        self.assertTrue(np.allclose(p[-1],study.config()['fixed_anchor_xyH']))
        d=p[-1]-p[-2]
        self.assertLess(d[0],0)
        self.assertAlmostEqual(d[1],0,places=8)
        self.assertAlmostEqual(d[2],0,places=8)

    def test_last_base_bend_is_outside_the_grip(self):
        p=study.route_points();c=study.config()
        edge=c['fixed_anchor_xyH'][0]+c['anchor_grip_length_mm']/2
        bending=p[(np.abs(p[:,1]+15)>1e-6)|(np.abs(p[:,2]-19.3)>1e-6)]
        self.assertGreater(float(bending[:,0].min()),edge+1)

    def test_cad_cable_sections_touch_at_the_fixed_grip(self):
        parts,_=study.geometry();by_name={p['name']:p['shape'] for p in parts}
        gap=by_name['display-base-bundle-space'].distance(by_name['display-axis-flex-space'])
        self.assertLess(gap,1e-6)

    def test_rear_connectors_are_not_under_the_round_bundle(self):
        p=study.route_points()
        # Includes the 0.3 mm position allowance, 0.05 mm curve allowance
        # and half the 0.2 mm polyline sampling interval.
        corridor=LineString(p[:,:2]).buffer(1.5+.3+.05+.1)
        parts=json.loads((study.ROOT/'mechanical/component-placement.json').read_text())['parts']
        for ref in ['J901','J422']:
            part=next(v for v in parts if v['board']=='center' and v['reference']==ref)
            area=unary_union([Polygon(r['outer'],r['holes']) for r in part['courtyards_installed_mm']['front']])
            self.assertFalse(corridor.intersects(area),ref)

    def test_overlapping_cutters_actually_remove_the_wall(self):
        wall=study.box(129,-18,1.2,109,1.2,22.6)
        changed,_=study.study_case_parts([{'name':'base-walls','shape':wall}])
        remaining=changed[0]['shape']
        probe=study.box(160,-17.7,18,1,.8,1)
        self.assertGreater(wall.intersect(probe).Volume(),.7)
        self.assertAlmostEqual(remaining.intersect(probe).Volume(),0,places=6)
        self.assertGreater(remaining.Volume(),0)
        self.assertLess(remaining.Volume(),wall.Volume())


if __name__=='__main__':unittest.main()

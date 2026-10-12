"""Connector placement, cable continuity and narrowly scoped mating exclusions."""
import unittest

import cadquery as cq
import numpy as np
import display_hinge_study as study
import display_plug as plug
from cad import box, compound
from review import intersection_volume


class DisplayPlug(unittest.TestCase):
    def test_reference_alignment_matches_the_port_plan(self):
        b=plug.reference_envelope().BoundingBox()
        self.assertAlmostEqual(b.xmin,235.82,places=5)
        self.assertAlmostEqual(b.xmax,239.77,places=5)
        self.assertAlmostEqual(b.ymin,-71.665,places=5)
        self.assertAlmostEqual(b.ymax,-45.415,places=5)
        self.assertAlmostEqual(b.zmin,12.237,places=5)
        self.assertAlmostEqual(b.zmax,13.237,places=5)

    def test_placement_is_a_rotation_without_mirroring(self):
        points=[plug.place(cq.Vertex.makeVertex(*p)).Center() for p in [(0,0,0),(1,0,0),(0,1,0),(0,0,1)]]
        a,b,c=[p-points[0] for p in points[1:]]
        self.assertAlmostEqual(a.cross(b).dot(c),1,places=6)
        ref=plug.references()['plug-body']
        self.assertAlmostEqual(ref.Volume(),plug.body().Volume(),places=5)

    def test_only_the_identified_port_is_removed(self):
        native=plug.references()['native-port'];neighbor=box(236,58,14,2,2,2)
        source={'name':'center-pcb-and-available-models','shape':compound([native,neighbor])}
        result=plug.strip_native_port(source)['shape']
        self.assertEqual(len(result.Solids()),1)
        self.assertAlmostEqual(result.Volume(),neighbor.Volume(),places=5)
        self.assertAlmostEqual(intersection_volume(result,neighbor),neighbor.Volume(),places=5)
        duplicate={'name':source['name'],'shape':compound([native,native.copy(),neighbor])}
        with self.assertRaises(AssertionError):plug.strip_native_port(duplicate)

    def test_five_mm_withdrawal_clears_the_port(self):
        moved=plug.body(5).BoundingBox();port=plug.references()['native-port'].BoundingBox()
        self.assertGreater(moved.xmin-port.xmax,2.2)

    def test_cable_stubs_meet_the_fanout_space(self):
        parts,_=study.geometry()
        fanout=next(p['shape'] for p in parts if p['name']=='display-flat-fanout-space')
        self.assertLess(plug.body().distance(fanout),1e-5)
        points=study.route_points();start=np.array(study.config()['fanout_start_xyH'])
        self.assertTrue(np.allclose(points[0],plug.config()['reference_cable_stub_end_xyH_mm']))
        stop=int(np.argmin(np.linalg.norm(points-start,axis=1)))
        self.assertGreater(points[stop,0]-points[0,0],1)
        self.assertTrue(np.allclose(points[:stop+1,1:],points[0,1:]))

    def test_fanout_height_transition_has_no_sharp_bend(self):
        c=study.config();points=study.route_points()
        start=int(np.argmin(np.linalg.norm(points-np.array(c['fanout_start_xyH']),axis=1)))
        end=int(np.argmin(np.linalg.norm(points-np.array(c['fanout_end_xyH']),axis=1)))
        p=points[start:end+1];x=p[:,0];h=p[:,2]
        first=np.gradient(h,x);second=np.gradient(first,x)
        curvature=np.abs(second)/(1+first**2)**1.5
        self.assertGreater(1/curvature.max(),40)
        self.assertLess(first[0],.003)
        self.assertLess(first[-1],.003)

    def test_upper_room_contains_the_bar_above_the_connector(self):
        room=plug.upper_swing_space();above=box(220,30,13.4,45,65,12)
        for angle in range(0,181,15):
            section=plug.bar(angle).intersect(above)
            if not section.Solids():continue
            outside=section.cut(room)
            self.assertLess(sum(s.Volume() for s in outside.Solids()),1e-5,angle)


if __name__=='__main__':unittest.main()

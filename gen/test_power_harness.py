"""Regressions for board-edge clearance and the fixed connector approaches."""
import unittest
import numpy as np
from shapely.geometry import box,Polygon
from check_power_harness import prism_distance
from bms_harness_geometry import power_loop


class PowerHarnessTests(unittest.TestCase):
    def test_old_positive_wire_crosses_the_bms_substrate(self):
        board=box(145,151,225,186.348)
        point=np.array([[145.01,174.567,9.615]])
        self.assertLess(prism_distance(point,board,9.1,10.7)[0],0)
        point[0,2]=12.5
        self.assertGreater(prism_distance(point,board,9.1,10.7)[0],1.7)

    def test_outline_holes_are_not_solid_board_material(self):
        board=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(3,3),(7,3),(7,7),(3,7)]])
        self.assertAlmostEqual(prism_distance(np.array([[5.,5.,.8]]),board,0,1.6)[0],2.)

    def test_fixed_ports_keep_straight_horizontal_entry_and_exit(self):
        for net,a,b in [('FG_VSS',[118,171.848,10.3],[177.15,150.398,14.3]),
                        ('PACK_POS_FUSED',[118,175.848,10.3],[173.15,150.398,14.3])]:
            p=power_loop(a,b,net)
            np.testing.assert_allclose(p[0],a);np.testing.assert_allclose(p[-1],b)
            start=p[1]-p[0];finish=p[-1]-p[-2]
            np.testing.assert_allclose(start/np.linalg.norm(start),[1,0,0],atol=1e-8)
            np.testing.assert_allclose(finish/np.linalg.norm(finish),[0,1,0],atol=1e-8)

    def test_relative_board_height_change_requires_a_new_route(self):
        with self.assertRaisesRegex(ValueError,'mounting height'):
            power_loop([118,175.848,10.3],[173.15,150.398,15.3],'PACK_POS_FUSED')


if __name__=='__main__':unittest.main()

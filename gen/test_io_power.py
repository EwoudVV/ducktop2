from dataclasses import replace
import math
import unittest
from calculate_io_power import Limits,calculate,constant_power_current

class IOCurrentTests(unittest.TestCase):
    def test_constant_power_loss_is_solved(self):
        r=calculate();self.assertAlmostEqual(r['usb_input_a'],4.189979949035503)
        self.assertAlmostEqual(r['regulator_input_min_v'],8.237482165504165)
        self.assertGreater(r['usb_input_a'],5.238866489*5.6/(8.7*.85))
        self.assertAlmostEqual(r['usb_input_a']*r['regulator_input_min_v'],5.238866489*5.6/.85)
    def test_actual_signed_cut_bounds(self):
        r=calculate();self.assertEqual(r['status'],'PASS_CONDITIONAL')
        self.assertAlmostEqual(r['worst_ground_edge_a'],7.765979949035502)
        self.assertAlmostEqual(r['signed_cut_absolute_bounds_a']['left_negative'],7.615)
        self.assertAlmostEqual(r['left_sys3_min_v'],3.022999702)
        self.assertGreater(r['whole_path_efficiency_min'],.80)
    def test_previous_loss_free_efficiency_assumption_fails(self):
        self.assertEqual(calculate(replace(Limits(),converter_efficiency_min=.80))['status'],'FAIL')
    def test_load_or_supply_drift_fails(self):
        self.assertEqual(calculate(replace(Limits(),left_sys3_a=2.3))['status'],'FAIL')
        self.assertEqual(calculate(replace(Limits(),center_vsys_min_v=8.2))['status'],'FAIL')
        with self.assertRaises(ValueError):constant_power_current(100,2,.1,0)
    def test_unequal_three_node_network_and_one_open_strap(self):
        # Two non-ground nodes connected to the center and each other. Solve
        # nodal voltages over extreme resistance ratios, then compare every
        # edge with max(|gL|, |gR|, |gL+gR|), the complete three-node cut bound.
        for gl,gr in [(6.4,1.4),(6,-5),(-7.6,3.3),(-4,-1.5)]:
            bound=max(abs(gl),abs(gr),abs(gl+gr))
            for rl in [.00001,.0005,.001]:
                for rr in [.00001,.0005,.001]:
                    for lr in [.00001,.019,1]:
                        a=1/rl+1/lr;b=-1/lr;d=1/rr+1/lr;det=a*d-b*b
                        vl=(d*gl-b*gr)/det;vr=(a*gr-b*gl)/det
                        self.assertLessEqual(max(abs(vl/rl),abs(vr/rr),abs((vl-vr)/lr)),bound+1e-8)

if __name__=='__main__':unittest.main()

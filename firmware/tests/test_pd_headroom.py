import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('headroom',Path(__file__).parents[1]/'tools/calculate_pd_headroom.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BoundsTests(unittest.TestCase):
    def test_explicit_corners(self):
        r=m.calculate(19000,3000,2250,2750,200)
        self.assertEqual(r['raw_aon_current_bound_ma'],250)
        self.assertEqual(r['raw_aon_power_bound_mw'],4700)
        self.assertEqual(r['charger_input_power_lower_bound_mw'],42300)
        self.assertFalse(r['overcommitted'])
    def test_current_tolerance_and_missing_margin(self):
        self.assertEqual(m.calculate(14250,2900,2250,2750)['raw_aon_current_bound_ma'],150)
        self.assertTrue(m.calculate(19000,2700,2250,2750)['overcommitted'])
        with self.assertRaises(ValueError):m.calculate(19000,3000,0,0)
if __name__=='__main__':unittest.main()

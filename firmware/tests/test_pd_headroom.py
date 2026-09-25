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

    def budget(self, bounds, **overrides):
        values=dict(raw_aon_max_mw=1000, efficiency_permille=900,
                    vsys_min_mv=10000, converter_output_limit_ma=10000,
                    system_load_max_mw=30000, reserve_mw=2000,
                    requested_charge_mw=10000, pack_min_mv=9000,
                    pack_discharge_limit_ma=3000, pack_path_efficiency_permille=950)
        values.update(overrides)
        return m.operating_budget(bounds, **values)

    def test_running_and_charging_from_large_source(self):
        b=self.budget(m.calculate(19000,5000,4400,4600,200))
        self.assertEqual(b['external_system_power_mw'],74448)
        self.assertEqual(b['charge_budget_mw'],10000)
        self.assertEqual(b['battery_assistance_needed_mw'],0)

    def test_small_source_charges_at_light_load_and_assists_at_heavy_load(self):
        source=m.calculate(4750,3000,2400,2600,250)
        light=self.budget(source, system_load_max_mw=5000)
        self.assertEqual(light['charge_budget_mw'],2720)
        self.assertEqual(light['battery_assistance_needed_mw'],0)
        heavy=self.budget(source)
        self.assertEqual(heavy['charge_budget_mw'],0)
        self.assertEqual(heavy['battery_assistance_needed_mw'],22280)
        self.assertEqual(heavy['load_reduction_needed_mw'],0)
        limited=self.budget(source, pack_discharge_limit_ma=2000)
        self.assertEqual(limited['load_reduction_needed_mw'],5180)

    def test_output_current_limit_is_separate_from_pd_watts(self):
        b=self.budget(m.calculate(19000,5000,4400,4600,200),
                      converter_output_limit_ma=6000, system_load_max_mw=59000)
        self.assertEqual(b['external_system_power_mw'],60000)
        self.assertEqual(b['charge_budget_mw'],0)
        self.assertEqual(b['battery_assistance_needed_mw'],1000)

    def test_aon_overload_invalidates_external_budget(self):
        b=self.budget(m.calculate(19000,5000,4400,4990,200))
        self.assertFalse(b['input_and_aon_fit'])
        self.assertEqual(b['charge_budget_mw'],0)
        self.assertEqual(b['external_system_power_mw'],0)
        b=self.budget(m.calculate(19000,4500,4400,4600,200))
        self.assertFalse(b['input_and_aon_fit'])

    def test_missing_or_impossible_operating_bounds(self):
        bounds=m.calculate(19000,5000,4400,4600,200)
        for change in ({'efficiency_permille':0}, {'efficiency_permille':1001},
                       {'converter_output_limit_ma':0}, {'reserve_mw':-1},
                       {'pack_path_efficiency_permille':1001}):
            with self.assertRaises(ValueError):self.budget(bounds, **change)
if __name__=='__main__':unittest.main()

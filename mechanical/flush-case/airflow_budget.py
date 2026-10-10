#!/usr/bin/env python3
"""Calculate a delivered-airflow test target, not a cooler performance rating."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    c=json.loads((HERE/'cooler.json').read_text())
    heat=c['thermal_screen']['heat_W'];rho=1.145;cp=1006.;rise=30.
    fan_heat=c['fan']['power_W']['maximum'];total_heat=heat+fan_heat
    flow_s=total_heat/(rho*cp*rise);flow=flow_s*60;head=None
    curve=c['fan']['typical_curve_m3_min_mmH2O']
    for (x1,y1),(x2,y2) in zip(curve,curve[1:]):
        if x1<=flow<=x2:head=(y1+(y2-y1)*(flow-x1)/(x2-x1))*9.80665
    d={'date':c['date'],'heat_W':heat,'fan_electrical_budget_W':fan_heat,'total_exhaust_air_heat_budget_W':total_heat,'assumed_inlet_C':35,'assumed_air_density_kg_m3':rho,
       'assumed_air_specific_heat_J_kgK':cp,'selected_maximum_bulk_air_rise_K':rise,
       'required_delivered_flow_m3_min':flow,'required_delivered_flow_CFM':flow_s/.00047194745,
       'approximate_typical_fan_pressure_at_required_flow_Pa':head,'fan_curve_test_temperature_C':25,
       'fan_curve_temperature_derated':False,
       'basis':'Q = mass flow times specific heat times bulk air temperature rise. The 40 W cooler budget and maximum 3.12 W fan input are both counted in the exhaust air. Fan pressure is interpolated from an approximate reading of the supplier plot.',
       'scope':'An airflow acceptance target only. This does not predict the installed operating point, heatpipe transport, sink temperature, junction temperature, noise or throttling. Test the complete duct and fin stack.',
       'installed_flow_measured':False,'thermal_performance_verified':False,
       'source_hashes':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['cooler.json','airflow_budget.py']}}
    (HERE/'cooler-airflow.json').write_text(json.dumps(d,indent=2)+'\n')
    print('Delivered-airflow target:',round(d['required_delivered_flow_CFM'],2),'CFM')


if __name__=='__main__':main()

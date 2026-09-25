#!/usr/bin/env python3
"""Calculate PD/AON bounds from explicitly supplied hardware limits."""
import argparse
import json

def calculate(source_min_mv,source_min_ma,iindpm_min_ma,iindpm_max_ma,cable_drop_mv=0):
    if min(source_min_mv,source_min_ma,iindpm_min_ma,iindpm_max_ma)<=0 or cable_drop_mv<0:
        raise ValueError('positive qualified limits are required')
    if iindpm_min_ma>iindpm_max_ma or cable_drop_mv>=source_min_mv:
        raise ValueError('inconsistent current or voltage bounds')
    rail_min_mv=source_min_mv-cable_drop_mv
    reserve_ma=max(0,source_min_ma-iindpm_max_ma)
    return {'source_at_board_min_mv':rail_min_mv,'raw_aon_current_bound_ma':reserve_ma,
            'raw_aon_power_bound_mw':rail_min_mv*reserve_ma//1000,
            'charger_input_power_lower_bound_mw':rail_min_mv*iindpm_min_ma//1000,
            'overcommitted':iindpm_max_ma>source_min_ma,
            'note':'arithmetic only; supplied limits require independent qualification'}

def operating_budget(input_bounds, *, raw_aon_max_mw, efficiency_permille,
                     vsys_min_mv, converter_output_limit_ma, system_load_max_mw,
                     reserve_mw, requested_charge_mw, pack_min_mv,
                     pack_discharge_limit_ma, pack_path_efficiency_permille):
    """Screen simultaneous loads at the converter output, including charging.

    Every argument is an explicit design bound. Neither a PDO rating nor a
    converter's switch-current headline supplies a missing output rating.
    Battery assistance is a deficit only; it cannot also count as charging.
    """
    if min(raw_aon_max_mw, system_load_max_mw, reserve_mw, requested_charge_mw,
           pack_discharge_limit_ma) < 0:
        raise ValueError('loads, reserves and current limits cannot be negative')
    if min(vsys_min_mv, converter_output_limit_ma, pack_min_mv) <= 0:
        raise ValueError('positive voltage and converter output bounds are required')
    if not (0 < efficiency_permille <= 1000 and
            0 < pack_path_efficiency_permille <= 1000):
        raise ValueError('efficiency must be between 1 and 1000 permille')
    input_fits = not input_bounds['overcommitted'] and (
        raw_aon_max_mw <= input_bounds['raw_aon_power_bound_mw'])
    converted_mw = (input_bounds['charger_input_power_lower_bound_mw'] *
                    efficiency_permille // 1000)
    output_ceiling_mw = vsys_min_mv * converter_output_limit_ma // 1000
    available_mw = min(converted_mw, output_ceiling_mw) if input_fits else 0
    demand_mw = system_load_max_mw + reserve_mw
    deficit_mw = max(0, demand_mw - available_mw)
    pack_budget_mw = (pack_min_mv * pack_discharge_limit_ma *
                      pack_path_efficiency_permille // 1000000)
    return {
        'input_and_aon_fit': input_fits,
        'converter_output_ceiling_mw': output_ceiling_mw,
        'external_system_power_mw': available_mw,
        'system_and_reserve_mw': demand_mw,
        'charge_budget_mw': min(requested_charge_mw, max(0, available_mw-demand_mw)),
        'battery_assistance_needed_mw': deficit_mw,
        'battery_assistance_available_mw': pack_budget_mw,
        'load_reduction_needed_mw': max(0, deficit_mw-pack_budget_mw),
        'note': 'arithmetic only; verify temperatures, losses, current limits and transients on hardware',
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-min-mv','source-min-ma','iindpm-min-ma','iindpm-max-ma'):
        p.add_argument('--'+name,type=int,required=True)
    p.add_argument('--cable-drop-mv',type=int,default=0)
    budget_names = ('raw-aon-max-mw', 'efficiency-permille', 'vsys-min-mv',
                    'converter-output-limit-ma', 'system-load-max-mw', 'reserve-mw',
                    'requested-charge-mw', 'pack-min-mv', 'pack-discharge-limit-ma',
                    'pack-path-efficiency-permille')
    for name in budget_names:
        p.add_argument('--'+name, type=int)
    a=p.parse_args()
    result=calculate(a.source_min_mv,a.source_min_ma,a.iindpm_min_ma,a.iindpm_max_ma,a.cable_drop_mv)
    budget={name.replace('-', '_'):getattr(a,name.replace('-', '_')) for name in budget_names}
    if any(value is not None for value in budget.values()):
        if any(value is None for value in budget.values()):
            p.error('the operating budget needs every load, converter and battery bound')
        result['operating_budget']=operating_budget(result, **budget)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

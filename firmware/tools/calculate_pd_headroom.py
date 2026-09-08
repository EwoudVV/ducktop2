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

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-min-mv','source-min-ma','iindpm-min-ma','iindpm-max-ma'):
        p.add_argument('--'+name,type=int,required=True)
    p.add_argument('--cable-drop-mv',type=int,default=0)
    a=p.parse_args();print(json.dumps(calculate(a.source_min_mv,a.source_min_ma,a.iindpm_min_ma,a.iindpm_max_ma,a.cable_drop_mv),indent=2))
if __name__=='__main__':main()

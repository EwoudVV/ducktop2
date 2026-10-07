"""Compare lower USB runs without changing the selected case arrangement."""
import json
import math
from cad import HERE
from build import load_config
from harness_geometry import paths
from stack_geometry import stack_limits


def main():
    c=load_config();t=c['trackpad'];fan=c['cooling']['blower']
    bridge_drop=t['thickness']+t['click_travel']+t['under_clearance']+2.5
    deck_offset=c['base']['deck_top']-c['boards']['keyboard']['bottom_height']
    fan_limit=fan[2]+fan[5]+c['cooling'].get('blower_height_tolerance',.3)+c['cooling'].get('intake_plenum',3)+deck_offset
    rows=[]
    for drop in (0,.5,1.,1.5,2.):
        c['cables']['usb_front_drop']=drop;h=paths(c)
        limits,local=stack_limits(c,h)
        wire_limit=limits['power_wires_and_guides_under_trackpad']
        rows.append({'usb_front_drop_mm':drop,
            **{k:v for k,v in h.items() if k.startswith('all_') or k=='minimum_wire_separation_mm'},
            'lowest_pair':min(h['pairs'],key=lambda p:p['surface_gap_after_position_and_sampling_mm']),
            'wire_stack_deck_limit_mm':wire_limit,'blower_stack_deck_limit_mm':fan_limit,
            'half_mm_stack_candidate':math.ceil(max(limits.values())*2)/2,
            'local_trackpad_cable_envelope':local})
    result={'status':'wire-only trials; lower variants were not adopted as case geometry','trials':rows,
        'conclusion':'These trials use the cable and open-guide surfaces beneath the trackpad support. A lower stack still needs complete carrier, component, service and cooling checks.'}
    (HERE/'harness-height-study.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()

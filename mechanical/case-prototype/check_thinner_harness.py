"""Compare lower USB runs without changing the selected case arrangement."""
import json
import math
from cad import HERE
from build import load_config
from harness_geometry import paths


def main():
    c=load_config();t=c['trackpad'];fan=c['cooling']['blower']
    bridge_drop=t['thickness']+t['click_travel']+t['under_clearance']+2.5
    deck_offset=c['base']['deck_top']-c['boards']['keyboard']['bottom_height']
    fan_limit=fan[2]+fan[5]+c['cooling'].get('blower_height_tolerance',.3)+c['cooling'].get('intake_plenum',3)+deck_offset
    rows=[]
    for drop in (0,.5,1.,1.5,2.):
        c['cables']['usb_front_drop']=drop;h=paths(c)
        wire_limit=max(r['max_wire_height_mm'] for r in h['routes'])+.5+bridge_drop
        rows.append({'usb_front_drop_mm':drop,
            **{k:v for k,v in h.items() if k.startswith('all_') or k=='minimum_wire_separation_mm'},
            'lowest_pair':min(h['pairs'],key=lambda p:p['surface_gap_after_position_and_sampling_mm']),
            'wire_stack_deck_limit_mm':wire_limit,'blower_stack_deck_limit_mm':fan_limit,
            'half_mm_stack_candidate':math.ceil(max(wire_limit,fan_limit)*2)/2})
    result={'status':'wire-only trials; lower variants were not adopted as case geometry','trials':rows,
        'conclusion':'The present blower intake stack still needs a 33.5 mm deck in half-millimeter steps. Lower cable variants also need fresh guide/body checks before use.'}
    (HERE/'harness-height-study.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()

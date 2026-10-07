#!/usr/bin/env python3
"""Trace the active stack and reject unsupported claims of a complete minimum."""
import json
import math
from cad import HERE
from build import CONFIG
from stack_geometry import stack_limits


def main():
    c=CONFIG;b=c['base'];t=c['trackpad'];h=c['hinges'];k=c['keyboard']
    wires=json.loads((HERE/'installed-power-harness.json').read_text())
    limits,local=stack_limits(c,wires)
    wiretop=local['limiting_crossing']['top_height_mm']
    bridge_drop=t['thickness']+t['click_travel']+t['under_clearance']+2.5
    fan=c['cooling']['blower'];fan_top=fan[2]+fan[5]+c['cooling'].get('blower_height_tolerance',.3)
    keyboard_to_deck=b['deck_top']-c['boards']['keyboard']['bottom_height']
    tests=[]
    for height in [30,31,32,33,33.5,34,35]:
        tests.append({'base_deck_height_mm':height,'stack_budget_pass':height>=max(limits.values()),
                      'wire_envelope_to_bridge_mm':height-bridge_drop-wiretop,
                      'fan_tolerance_envelope_to_keyboard_mm':height-keyboard_to_deck-fan_top})
    result={'units':'mm','status':'conditional stack budget, not a certified complete arrangement',
            'active_base_height':b['deck_top'],'smallest_half_mm_stack_candidate':math.ceil(max(limits.values())*2)/2,
            'limiting_deck_heights':limits,'trials':tests,
            'local_trackpad_cable_envelope':local,
            'main_top_height':c['boards']['center']['bottom_height']+1.6,
            'bms_top_height':c['boards']['bms']['bottom_height']+1.6,
            'floor':b['floor'],'minimum_planned_main_board_underside_component_gap':c['boards']['center']['bottom_height']-2.1-b['floor'],
            'left_modeled_pin_tail_gap_after_0_3_allowance':c['boards']['left']['bottom_height']-1.863-b['floor']-.3,
            'key_top_height':c['boards']['keyboard']['bottom_height']+.8+k['key_height_above_pcb'],
            'closed_outer_height_without_feet':h['pivot_height']+17,'closed_outer_height_with_5mm_feet':h['pivot_height']+22,
            'panel_to_keys':h['pivot_height']+c['lid']['panel_back_height_from_axis']-c['lid']['panel_thickness']-(c['boards']['keyboard']['bottom_height']+.8+k['key_height_above_pcb']),
            'panel_to_radio_screw_heads':h['pivot_height']+c['lid']['panel_back_height_from_axis']-c['lid']['panel_thickness']-(b['deck_top']+2),
            'battery_finished_thickness_measured':False,
            'maximum_cell_thickness_under_trackpad_budget':b['deck_top']-bridge_drop-b['floor']-c['cells']['pad_thickness']-c['cells']['swelling_gap']-.5,
            'maximum_cell_thickness_under_radio_budget':c['boards']['radio']['bottom_height']-2.1-b['floor']-c['cells']['pad_thickness']-c['cells']['swelling_gap']-.5,
            'complete_minimum_supported':False,
            'unresolved':['complete cells, lead exits and usable lengths','trackpad thickness, click mechanism and connector','panel thickness, mass and harness endpoint',
                          'Ultra cold plate and fastening','226V and 256V thermal/airflow tests','guide deflection and clamp pull tests','signal cable dressing and hinge flex behavior']}
    (HERE/'thickness-study.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

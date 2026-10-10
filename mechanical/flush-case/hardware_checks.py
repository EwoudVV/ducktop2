"""Open-air sections, fastener stacks and sampled cooler assembly movements."""
import math

import cooler_hardware
from cad import box, cylinder, compound
from review import bbox_overlap, intersection_volume


def evaluate(parts,case,c):
    h=cooler_hardware.config();by_name={p['name']:p for p in parts}
    floor=by_name['base-floor']['shape'];fan=by_name['delta-blower']['shape']
    a=h['intake'];x,y=a['centre_xy'];r=a['floor_opening_radius_mm']
    sections=[]
    for height in [.1,1.5]:
        section=cylinder(x,y,height,r,.1)
        free=section.cut(floor).Volume()/.1
        sections.append({'H_mm':height,'open_area_mm2':round(free,3),
                         'fraction_of_floor_opening':round(free/(math.pi*r*r),4)})
    q=h['duct'];x0,y0,z0,width,height=q['fan_outlet_window_xyzh']
    # These are real open sections, not areas taken from outer bounding boxes.
    mouth=box(x0-.1,y0,z0,.2,width,height)
    outlet_free=mouth.cut(fan).Volume()/.2
    fx,fy,fw,fd=c['fins']['xywh'];bottom=c['fins']['bottom_H'];top=c['fins']['top_H']
    exit_slice=box(fx+fw-.1,fy,bottom,.09,fd,top-bottom)
    fin_free=exit_slice.cut(by_name['slotted-copper-fin-stack']['shape']).Volume()/.09
    walls=by_name['base-walls']['shape']
    case_slice=box(case['outline']['x_max']-.1,fy,bottom,.09,fd,top-bottom)
    case_free=case_slice.cut(walls).Volume()/.09
    boundary_gaps=[]
    solid_parts=[p['shape'] for p in parts if p.get('remote_cooler') and p['group']=='cooling']
    for label,yy in [('rear',q['rear_Y']+.1),('front',q['front_Y']-.2)]:
        section=box(q['baffle_x'],yy,q['bottom_H'],fx+fw-q['baffle_x'],.1,q['roof_bottom_H']+q['roof_thickness_mm']-q['bottom_H'])
        for solid in solid_parts:
            if not section.Solids():break
            if bbox_overlap(section,solid):section=section.cut(solid)
        boundary_gaps.append({'wall':label,'uncovered_area_mm2':round(max(0,section.Volume()/.1),6)})
    f=h['fan_posts'];seat=c['fan']['mount_ear_upper_H']+f['washer_thickness_mm']
    tip=seat-f['screw_length_mm'];engagement=f['base_top_H']-tip
    mount=h['fin_mounts'];stack=case['base']['floor']+mount['spacer_height_mm']+q['floor_thickness_mm']+mount['upper_washer_thickness_mm']

    # Assemble the fin/pipe/contact unit into the open exhaust side of the
    # cowl on the bench, before attaching the baffle and installing the unit.
    names=['slotted-copper-fin-stack','stepped-copper-plate','heatpipe-1','heatpipe-2']
    cowl=by_name['fin-cowl']['shape'];slide=[]
    for half_mm in range(0,41):
        dx=half_mm*.5
        for name in names:
            s=by_name[name]['shape'].translate((dx,0,0))
            if not bbox_overlap(s,cowl):continue
            volume=intersection_volume(s,cowl)
            if volume>.01:slide.append({'offset_X_mm':dx,'part':name,'overlap_mm3':round(volume,5)})

    # This only checks fan replacement, not removal of the complete CPU unit.
    remove={'deck','oled-1-module','oled-2-module','fan-outlet-foil-bridge'}
    remove.update(f'fan-{kind}-{i}' for kind in ['screw','washer'] for i in range(1,4))
    fixed=[p for p in parts if not p.get('moving') and p['group'] not in ['keepout','changes']
           and p['name'] not in remove|{'delta-blower'}]
    lift=[]
    for rise in range(0,31,2):
        s=fan.translate((0,0,rise))
        for p in fixed:
            if not bbox_overlap(s,p['shape']):continue
            volume=intersection_volume(s,p['shape'])
            if volume>.01:lift.append({'lift_mm':rise,'part':p['name'],'overlap_mm3':round(volume,5)})
    gap=a['fan_bottom_range_H'][0]-a['cross_rib_top_H']
    result={
        'intake_sections':sections,
        'minimum_internal_inlet_gap_mm':round(gap,3),
        'required_external_inlet_gap_mm':a['minimum_external_gap_mm'],
        'external_gap_provided_by_selected_feet':False,
        'nominal_fan_outlet_open_area_mm2':round(outlet_free,3),
        'nominal_fin_exit_open_area_mm2':round(fin_free,3),
        'nominal_case_exit_open_area_mm2':round(case_free,3),
        'nominal_duct_end_wall_gaps':boundary_gaps,
        'fan_screw_nominal_engagement_mm':round(engagement,3),
        'fan_screw_engagement_after_0_5_mm_stack_budget_mm':round(engagement-.5,3),
        'fin_support_stack_top_H':round(stack,3),
        'fin_support_to_tab_gap_mm':round(bottom-stack,6),
        'fin_screw_nominal_engagement_mm':mount['nominal_thread_engagement_mm'],
        'bench_cowl_assembly':{'axis':'+X out / -X in','positions':41,'step_mm':.5,'travel_mm':20,'conflicts':slide},
        'fan_replacement':{'remove_first':sorted(remove),'disconnect_first':'fan lead extension; route and connector still to be defined',
                           'positions':16,'step_mm':2,'vertical_travel_mm':30,'conflicts':lift},
        'CPU_clamp_hardware_available':False,'CPU_clamp_load_verified':False,
        'fastener_strength_verified':False,'duct_pressure_drop_verified':False,
        'seal_material_qualified':False,'manufacturing_ready':False,
        'limits':['Movement checks are nominal sampled positions, not continuous swept-volume or tolerance proofs.',
                  'The cowl slide is a bench assembly operation before the baffle, seals and CPU unit are installed.',
                  'The complete cooler removal path remains dependent on the CPU clamp and keyboard-support assembly.',
                  'Open areas do not establish installed airflow, cooling capacity or noise.',
                  'The printed base uses installed insert cavities. A smaller heat-set pilot needs a separate tested print derivative.']}
    result['nominal_geometry_pass']=bool(min(s['open_area_mm2'] for s in sections)>400 and gap>=3 and
        outlet_free>250 and fin_free>0 and case_free>0 and engagement-.5>=2 and abs(bottom-stack)<1e-6 and
        not any(row['uncovered_area_mm2']>.01 for row in boundary_gaps) and not slide and not lift)
    return result

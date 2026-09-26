"""Reproducible packaging checks; physical and cable qualifications stay separate."""
import json
import math
import cadquery as cq
from shapely.geometry import Polygon
from shapely.ops import unary_union
from cad import HERE,box,compound


def bbox_overlap(a,b,tol=.001):
    a=a.BoundingBox();b=b.BoundingBox()
    return all(min(getattr(a,k+'max'),getattr(b,k+'max'))-max(getattr(a,k+'min'),getattr(b,k+'min'))>tol for k in ['x','y','z'])


def review(m):
    from build import CONFIG,INVENTORY,installed
    from deliver import posed
    b=CONFIG['base'];report={'profile':CONFIG['selected_profile'],'status':CONFIG['status'],'checks':{},'collisions':[], 'limitations':m.findings}
    outlines={}
    for name,row in INVENTORY.items():
        outlines[name]=unary_union([Polygon([installed(name,q) for q in o['outer']],
                                           [[installed(name,q) for q in ring] for ring in o['holes']]) for o in row['outlines']])
    gaps={f'{a}-{z}':outlines[a].distance(outlines[z]) for a,z in [('left','center'),('center','right'),('center','bms')]}
    assert abs(gaps['left-center']-1.5)<1e-5 and abs(gaps['center-right']-1.5)<1e-5
    assert gaps['center-bms']>=1.49
    report['checks']['board_gaps_mm']=gaps
    report['checks']['main_board_span_mm']=outlines['right'].bounds[2]-outlines['left'].bounds[0]
    report['checks']['base_outside_mm']=[b['x_max']-b['x_min'],b['y_max']-b['y_min'],b['deck_top']]
    report['checks']['main_chassis_mounts']=len([r for r in m.mounts if r['reference'].split('/')[0] in ['left','center','right'] and 'standoff' in r['mating_part']])
    report['checks']['BMS_supports']=len([r for r in m.mounts if r['reference'].startswith('bms/edge')])
    report['checks']['radio_supports']=len([r for r in m.mounts if r['reference'].startswith('radio/H')])
    assert report['checks']['main_chassis_mounts']==13
    assert report['checks']['BMS_supports']==4
    assert report['checks']['radio_supports']==4
    hardware=[p for p in m.parts if p.get('manufactured') and not p.get('moving')]
    for p in hardware:
        for name,s in m.board_material.items():
            if bbox_overlap(p['shape'],s):
                v=p['shape'].intersect(s).Volume()
                if v>.01:report['collisions'].append({'part':p['name'],'board':name,'substrate_overlap_mm3':round(v,4)})
    print('board-to-support checks complete',flush=True)
    # Moving case/adapter solids against fixed manufactured solids. Hinge internal
    # bearing contacts are intentional and checked in check_hinges.py instead.
    fixed=[p for p in m.parts if (p.get('manufactured') or 'bolt-head-' in p['name']) and not p.get('moving')]
    moving=[p for p in m.parts if p.get('moving') and (p.get('manufactured') or p['group']=='panel')]
    sweep=[]
    for angle in range(0,181,CONFIG['hinges']['sweep_step_deg']):
        hits=[]
        for p in moving:
            s=posed(p,angle)['shape']
            for q in fixed:
                if bbox_overlap(s,q['shape']):
                    v=s.intersect(q['shape']).Volume()
                    if v>.1:hits.append({'moving':p['name'],'fixed':q['name'],'volume_mm3':round(v,3)})
        if hits:sweep.append({'angle':angle,'hits':hits})
    report['checks']['case_sweep']={'range':[0,180],'step_deg':CONFIG['hinges']['sweep_step_deg'],'collisions':sweep,
                                  'covers':'manufactured case parts and panel envelope; cable flex and joint friction are not validated'}
    report['checks']['maximum_sampled_collision_free_angle_from_closed']=next((x['angle']-CONFIG['hinges']['sweep_step_deg'] for x in sweep),180)
    print('case sweep complete',flush=True)
    obstacles=[p for p in m.parts if p.get('manufactured') or p['group'] in ['inputs','panel']]
    cable_clashes=[]
    for p in [x for x in m.parts if x['group']=='cables' and ('loom-wire' in x['name'] or 'BMS-proposed' in x['name'])]:
        for q in obstacles:
            if bbox_overlap(p['shape'],q['shape']):
                v=p['shape'].intersect(q['shape']).Volume()
                if v>.1:cable_clashes.append({'wire':p['name'],'part':q['name'],'closed_overlap_mm3':round(v,3)})
    report['checks']['current_power_wires_vs_closed_case']=cable_clashes
    report['checks']['eDP_bend_corridor_vs_moving_parts_closed']=[]
    corridor=next(p['shape'] for p in m.parts if p['name']=='eDP-dynamic-bend-corridor')
    for p in moving:
        if bbox_overlap(corridor,p['shape']):
            v=corridor.intersect(p['shape']).Volume()
            if v>.1:report['checks']['eDP_bend_corridor_vs_moving_parts_closed'].append({'part':p['name'],'overlap_mm3':round(v,3)})
    report['checks']['eDP_corridor_note']='annulus is rotationally invariant about the hinge axis; this checks its space, not constant-length cable behavior'
    report['checks']['known_component_model_vs_support']=[]
    for board in [p for p in m.parts if p['group']=='boards']:
        for p in hardware:
            if bbox_overlap(board['shape'],p['shape']):
                v=board['shape'].intersect(p['shape']).Volume()
                if v>.1:report['checks']['known_component_model_vs_support'].append({'board':board['name'],'part':p['name'],'overlap_mm3':round(v,3)})
    # Mass from actual manufactured CAD volumes, plus explicit component assumptions.
    rho={'PETG':1.27e-6,'aluminum':2.70e-6,'steel':7.85e-6,'OEM steel':7.85e-6}
    masses=[]
    hy=CONFIG['hinges']['pivot_y'];hh=CONFIG['hinges']['pivot_height']
    for p in m.parts:
        if not p.get('moving'):continue
        if p['material'] in rho:
            mass=p['shape'].Volume()*rho[p['material']];center=p['shape'].Center()
            masses.append({'name':p['name'],'kg':mass,'lever_s_mm':-center.y-hy,'height_above_axis_mm':center.z-hh,'basis':'CAD volume and assumed density'})
    l=CONFIG['lid'];masses.append({'name':'display panel','kg':l['panel_mass_kg'],'lever_s_mm':l['panel_s']+l['panel_depth']/2,'height_above_axis_mm':11,'basis':'unmeasured mass assumption'})
    masses.append({'name':'cable, gasket and fasteners','kg':.04,'lever_s_mm':100,'height_above_axis_mm':10,'basis':'allowance'})
    mass=sum(p['kg'] for p in masses);lever=sum(p['kg']*p['lever_s_mm'] for p in masses)/mass
    height=sum(p['kg']*p['height_above_axis_mm'] for p in masses)/mass
    torque=[]
    for a in [0,15,30,45,60,90,105,120,135,150,180]:
        r=math.radians(a);horizontal=(lever*math.cos(r)-height*math.sin(r))/1000
        torque.append({'angle_deg':a,'gravity_Nm':mass*9.80665*horizontal})
    report['lid_mass_and_loads']={'items':masses,'total_kg':mass,'COM_distance_along_lid_mm':lever,'COM_height_above_axis_closed_mm':height,
        'gravity_torque':torque,'conditional_pair_open_Nm':2*3.3*.0980665,'conditional_pair_close_Nm':2*4.3*.0980665,
        'conditional_aged_low_open_Nm':2*(3.3-.5)*.0980665*.85,'conditional_aged_low_close_Nm':2*(4.3-.5)*.0980665*.85,
        'unit_condition':'drawing says kg-f/cm; multiplication-unit interpretation must be confirmed or replaced with measurement',
        'result':'do not assume original 3.3 kit holds this larger lid near horizontal; use prop and dummy-mass test',
        'screen_mount_design_torque_Nm':2,'screen_note':'2 Nm total handling screen, not an impact specification or material qualification',
        'per_hinge_load_at_15mm_load_path_N':1/.015}
    # Table stability is a separate moment balance about the rear feet.
    base_mass=2.0;base_com_y=125;rear=-19;front=249
    stability=[]
    for a in [90,105,120,135,150,180]:
        r=math.radians(a);lid_y=hy+lever*math.cos(r)-height*math.sin(r)
        total_y=(base_mass*base_com_y+mass*lid_y)/(base_mass+mass)
        stability.append({'angle_deg':a,'combined_COM_y_mm':total_y,'rear_margin_mm':total_y-rear,
                          'minimum_base_kg_against_rear_tip':max(0,mass*(rear-lid_y)/(base_com_y-rear))})
    report['stability']={'assumed_base_kg':base_mass,'assumed_base_COM_y_mm':base_com_y,'rear_foot_y_mm':rear,'front_foot_y_mm':front,'angles':stability,
                         'status':'static table screen only; actual mass/COM, hand opening, rubber friction and lap use pending'}
    c=CONFIG['cells'];t=CONFIG['trackpad'];bridge_h=b['deck_top']-t['thickness']-t['click_travel']-t['under_clearance']-2.5
    report['checks']['cell_to_trackpad_bridge_gap_mm']=bridge_h-(b['floor']+c['pad_thickness']+c['thickness']+c['swelling_gap'])
    report['checks']['closed_key_to_panel_gap_mm']=hh+l['panel_back_height_from_axis']-l['panel_thickness']-(CONFIG['boards']['keyboard']['bottom_height']+.8+CONFIG['keyboard']['key_height_above_pcb'])
    report['physical_tests_complete']=False
    if cable_clashes:report['limitations'].append('current power wires collide with the selected case profile; compact profile requires a harness/connector change')
    (HERE/'assembly-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'support_board_collisions':report['collisions'],'sweep_collision_angles':[r['angle'] for r in sweep],
                      'lid_estimated_kg':round(mass,3),'lid_COM_mm':round(lever,2)},indent=2),flush=True)

"""Reproducible packaging checks; physical and cable qualifications stay separate."""
import json
import math
import hashlib
import numpy as np
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from shapely.geometry import Polygon
from shapely.ops import unary_union
from cad import HERE,box,compound
_BOXES={}
_SOLIDS={}
_PRIMITIVES={}
_GUIDE_IDS=set()
_WIRE_IDS=set()
_ANALYTIC_GUIDE_PAIRS=False
_ANALYTIC_WIRE_GUIDES=False
_CURVES={}
_VOLUMES={}


def cached_box(shape):
    key=id(shape)
    if key not in _BOXES:
        b=Bnd_Box();BRepBndLib.Add_s(shape.wrapped,b,False)
        _BOXES[key]=(shape,cq.BoundBox(b))
    return _BOXES[key][1]


def bbox_overlap(a,b,tol=.001):
    a=cached_box(a);b=cached_box(b)
    return all(min(getattr(a,k+'max'),getattr(b,k+'max'))-max(getattr(a,k+'min'),getattr(b,k+'min'))>tol for k in ['x','y','z'])


def intersection_volume(a,b):
    if not bbox_overlap(a,b):return 0
    key=tuple(sorted((id(a),id(b))))
    if key not in _VOLUMES:_VOLUMES[key]=(a,b,_intersection_volume(a,b))
    return _VOLUMES[key][2]


def _intersection_volume(a,b):
    if not bbox_overlap(a,b):return 0
    for curve,obstacle in [(a,b),(b,a)]:
        if id(curve) in _CURVES:
            points,radius=_CURVES[id(curve)];bb=cached_box(obstacle)
            low=np.array([bb.xmin,bb.ymin,bb.zmin]);high=np.array([bb.xmax,bb.ymax,bb.zmax])
            distance=np.linalg.norm(np.maximum(np.maximum(low-points,points-high),0),axis=1)
            if distance.min()>radius:return 0
    if id(a) in _GUIDE_IDS and id(b) in _GUIDE_IDS and _ANALYTIC_GUIDE_PAIRS:return 0
    if _ANALYTIC_WIRE_GUIDES and ((id(a) in _GUIDE_IDS and id(b) in _WIRE_IDS) or (id(b) in _GUIDE_IDS and id(a) in _WIRE_IDS)):return 0
    if id(a) in _PRIMITIVES or id(b) in _PRIMITIVES:
        aa=_PRIMITIVES.get(id(a),[a]);bb=_PRIMITIVES.get(id(b),[b])
        # Conservative superset: pre-fusion guide and pedestal pieces contain
        # the final carrier. A zero proves no overlap; a hit needs review of
        # the final relief cuts. Do not spend minutes intersecting high-order
        # swept faces that cannot meet once these smaller pieces are culled.
        return sum(intersection_volume(x,y) for x in aa for y in bb if bbox_overlap(x,y))
    for shape in [a,b]:
        if id(shape) not in _SOLIDS:_SOLIDS[id(shape)]=(shape,shape.Solids())
    aa=_SOLIDS[id(a)][1];bb=_SOLIDS[id(b)][1]
    if len(aa)==1 and len(bb)==1:return max(0,a.intersect(b).Volume())
    if id(a) in _CURVES and len(aa)==1:_CURVES[id(aa[0])]=_CURVES[id(a)]
    if id(b) in _CURVES and len(bb)==1:_CURVES[id(bb[0])]=_CURVES[id(b)]
    # Cull each imported component before asking the exact kernel to intersect.
    # The number is a sum over solids, used for clash detection, not union mass.
    return sum(intersection_volume(x,y) for x in aa for y in bb if bbox_overlap(x,y))


def review(m):
    global _ANALYTIC_GUIDE_PAIRS,_ANALYTIC_WIRE_GUIDES
    from build import CONFIG,INVENTORY,installed
    from deliver import posed
    b=CONFIG['base'];report={'profile':CONFIG['selected_profile'],'status':CONFIG['status'],'checks':{},'collisions':[], 'limitations':m.findings}
    for p in m.parts:
        if p.get('power_wire'):
            _WIRE_IDS.add(id(p['shape']))
            r=next(q for q in m.harness['routes'] if q['name']==p['wire_name'])
            pts=np.array(r['points']);pts[:,1]*=-1
            _CURVES[id(p['shape'])]=(pts,r['wire_od_mm']/2+.5)
        if p['name'] in getattr(m,'collision_primitives',{}):
            pieces=m.collision_primitives[p['name']];_PRIMITIVES[id(p['shape'])]=pieces
            if p.get('primitives_are_full_parts'):
                continue
            # integrate_guides retains creation order: guide sections precede
            # their pedestal and middle rib. These are exact pre-fusion solids.
            n=sum('-guide' in name for name in p['integrated_from'])
            _GUIDE_IDS.update(id(s) for s in pieces[:n])
            routes=[r for r in m.harness['routes'] if any(name.startswith(r['name']+'-guide') for name in p['integrated_from'])]
            if routes:
                points=np.vstack([np.array(r['points']) for r in routes]);points[:,1]*=-1
                radius=max(r['wire_od_mm']/2 for r in routes)+CONFIG['cables']['guide_radial_clearance']+CONFIG['cables']['guide_wall']+.5
                for s in pieces[:n]:_CURVES[id(s)]=(points,radius)
    family={r['name']:('right-main' if r['group'] in ['right-J2432','right-J2452'] else
                      'left-main' if r['group'] in ['left-J2430','left-J2460'] else r['group']) for r in m.harness['routes']}
    outer=CONFIG['cables']['guide_radial_clearance']+CONFIG['cables']['guide_wall']
    foreign=[p['surface_gap_after_position_and_sampling_mm']+.4-2*outer-.016 for p in m.harness['pairs'] if family[p['a']]!=family[p['b']]]
    wire_guide=min(p['surface_gap_after_position_and_sampling_mm']+.2-outer-.016 for p in m.harness['pairs'])
    _ANALYTIC_GUIDE_PAIRS=min(foreign)>0
    _ANALYTIC_WIRE_GUIDES=wire_guide>0
    report['checks']['analytic_guide_clearances']={'different_carriers_minimum_outer_envelope_gap_mm':min(foreign),
        'wire_to_other_guide_minimum_gap_mm':wire_guide,'CAD_approximation_allowance_mm':.016,
        'method':'continuous-path sampling bound plus circular enclosing radii; same-carrier guide walls are intentionally fused; pedestal and rib checks still use BRep geometry'}
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
    from clearance_review import check
    detailed=check(m)
    if detailed['power_wire_collisions']:
        m.findings.append('The saved protected-power BMS loops hit the BMS board/connector assembly, including J2074. This is an unresolved physical conflict, despite passing bend, length and wire-separation checks.')
    if detailed['service_conflicts']:
        m.findings.append('Connector service paths remain obstructed after removing the deck and clamp caps. The one-piece USB carriers need a detachable upper section; their seam feet are captured beneath the boards. See harness-case-checks.json before treating this as serviceable.')
    if detailed['unverified_height_limits']:
        m.findings.append(str(len(detailed['unverified_height_limits']))+' wire/component height limits remain unverified; nominal STEP coverage is incomplete.')
    if not detailed['braid_joint_clearance_conflicts'] and not any(
            'ground-braid' in p.get('part','') for p in detailed['guide_case_collisions']):
        m.findings[:]=[line for line in m.findings if not line.startswith('All four required Alpha 1230 seam braids')]
        m.findings.append('All four seam braids and their 1 mm solder reservations clear the guide carriers. Confirm the formed braid shape, soldered joints and retention under case flex on a sample.')
    hardware=[p for p in m.parts if p.get('manufactured') and not p.get('moving')]
    for p in hardware:
        for name,s in m.board_material.items():
            if bbox_overlap(p['shape'],s):
                v=intersection_volume(p['shape'],s)
                if v>.01:report['collisions'].append({'part':p['name'],'board':name,'substrate_overlap_mm3':round(v,4)})
    print('board-to-support checks complete',flush=True)
    # Moving case/adapter solids against fixed manufactured solids. Hinge internal
    # bearing contacts are intentional and checked in check_hinges.py instead.
    fixed=[p for p in m.parts if p['group'] not in ['keepout','routes'] and not p.get('moving')]
    moving=[p for p in m.parts if p.get('moving') and (p.get('manufactured') or p['group']=='panel' or p.get('material')=='OEM steel')]
    sweep=[]
    for angle in range(0,181,CONFIG['hinges']['sweep_step_deg']):
        if angle%30==0:print('hinge sweep '+str(angle)+' degrees',flush=True)
        hits=[]
        for p in moving:
            s=posed(p,angle)['shape']
            for q in fixed:
                if p.get('material')=='OEM steel' and q.get('material')=='OEM steel':continue
                if bbox_overlap(s,q['shape']):
                    v=intersection_volume(s,q['shape'])
                    if v>.1:hits.append({'moving':p['name'],'fixed':q['name'],'volume_mm3':round(v,3)})
        if hits:sweep.append({'angle':angle,'hits':hits})
    report['checks']['case_sweep']={'range':[0,180],'step_deg':CONFIG['hinges']['sweep_step_deg'],'collisions':sweep,
                                  'covers':'moving case, panel and actual OEM hinge leaves versus fixed case, available PCB models, inputs, wires and guides. OEM-to-OEM bearing contacts excluded. eDP flex and joint friction not validated.'}
    report['checks']['maximum_sampled_collision_free_angle_from_closed']=next((x['angle']-CONFIG['hinges']['sweep_step_deg'] for x in sweep),180)
    print('case sweep complete',flush=True)
    obstacles=[p for p in m.parts if p.get('manufactured') or p['group'] in ['inputs','panel']]
    cable_clashes=[]
    for p in [x for x in m.parts if x.get('power_wire')]:
        for q in obstacles:
            if q.get('intentional_wire_grip'):continue
            if bbox_overlap(p['shape'],q['shape']):
                v=intersection_volume(p['shape'],q['shape'])
                if v>.1:cable_clashes.append({'wire':p['name'],'part':q['name'],'closed_overlap_mm3':round(v,3)})
    report['checks']['current_power_wires_vs_closed_case']=cable_clashes
    report['checks']['eDP_bend_corridor_vs_moving_parts_closed']=[]
    corridor=next(p['shape'] for p in m.parts if p['name']=='eDP-dynamic-bend-corridor')
    for p in moving:
        if bbox_overlap(corridor,p['shape']):
            v=intersection_volume(corridor,p['shape'])
            if v>.1:report['checks']['eDP_bend_corridor_vs_moving_parts_closed'].append({'part':p['name'],'overlap_mm3':round(v,3)})
    report['checks']['eDP_corridor_note']='annulus is rotationally invariant about the hinge axis; this checks its space, not constant-length cable behavior'
    report['checks']['known_component_model_vs_support']=[]
    for board in [p for p in m.parts if p['group']=='boards']:
        for p in hardware:
            if bbox_overlap(board['shape'],p['shape']):
                v=intersection_volume(board['shape'],p['shape'])
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
    if any(p['name'].startswith('radio-H') and p['name'].endswith('-screw-envelope') for p in m.parts):
        report['checks']['closed_radio_screw_to_panel_gap_mm']=hh+l['panel_back_height_from_axis']-l['panel_thickness']-(b['deck_top']+2)
    report['physical_tests_complete']=False
    if cable_clashes:report['limitations'].append('power-wire/case clashes remain; see exact part pairs before accepting this candidate')
    report['checks']['detailed_harness_report']='harness-case-checks.json'
    report['complete_arrangement_supported']=False
    report['not_ready_reason']='owned-part measurements, guide pull/fit tests, signal-cable dressing and both Ultra thermal qualifications remain outstanding'
    report['config_sha256']=hashlib.sha256((HERE/'assembly.json').read_bytes()).hexdigest()
    report['inventory_sha256']=hashlib.sha256((HERE/'board-inventory.json').read_bytes()).hexdigest()
    (HERE/'assembly-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'support_board_collisions':report['collisions'],'sweep_collision_angles':[r['angle'] for r in sweep],
                      'lid_estimated_kg':round(mass,3),'lid_COM_mm':round(lever,2)},indent=2),flush=True)

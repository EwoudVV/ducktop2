"""Low feet and a conditional loaded-clearance budget for the bottom intake."""
import json,math
from pathlib import Path
from cad import cylinder
from review import bbox_overlap,intersection_volume

HERE=Path(__file__).resolve().parent


def config():return json.loads((HERE/'feet.json').read_text())


def gap_budget():
    c=config()
    return c['height_mm']-c['dimension_tolerance_mm']-c['compression_budget_mm']-c['local_floor_deflection_budget_mm']


def parts():
    c=config()
    return [dict(name=f'base-foot-{i}',shape=cylinder(x,y,-c['height_mm'],c['diameter_mm']/2,c['height_mm']),
                 group='supports',color=(.56,.60,.61),moving=False,external_foot=True)
            for i,(x,y) in enumerate(c['centres_xy'],1)]


def check(parts,case):
    c=config();o=case['outline'];floor=next(p['shape'] for p in parts if p['name']=='base-floor')
    a=json.loads((HERE/'cooler-hardware.json').read_text())['intake'];ix,iy=a['centre_xy']
    radius=(c['diameter_mm']+c['dimension_tolerance_mm'])/2+c['position_allowance_mm']
    rows=[];service=[]
    for i,(x,y) in enumerate(c['centres_xy'],1):
        bond=cylinder(x,y,0,radius,.1)
        missing=max(0,bond.cut(floor).Volume()/.1)
        edge=min(x-radius-o['x_min'],o['x_max']-x-radius,y-radius-o['y_min'],o['y_max']-y-radius)
        intake_gap=math.hypot(x-ix,y-iy)-radius-a['floor_opening_radius_mm']
        rows.append({'foot':i,'centre_xy':[x,y],'minimum_edge_margin_mm':round(edge,3),
                     'missing_floor_bond_area_mm2':round(missing,6),'plan_gap_to_intake_mm':round(intake_gap,3)})
        limit=cylinder(x,y,-c['height_mm']-c['dimension_tolerance_mm'],radius,c['height_mm']+c['dimension_tolerance_mm'])
        for p in parts:
            if not p.get('service') or not bbox_overlap(limit,p['shape']):continue
            v=intersection_volume(limit,p['shape'])
            if v>.01:service.append({'foot':i,'access':p['name'],'overlap_mm3':round(v,4)})
    minimum=gap_budget();body=case['hinges']['pivot_height']+case['lid']['back_inner_height_from_axis']+case['lid']['skin']
    return {'part':c['part'],'configuration':c,'foot_checks':rows,'service_conflicts':service,
            'conditional_minimum_intake_gap_mm':round(minimum,3),
            'nominal_closed_height_with_feet_mm':round(body+c['height_mm'],3),
            'foot_height_tolerance_only_max_closed_height_mm':round(body+c['height_mm']+c['dimension_tolerance_mm'],3),
            'nominal_geometry_pass':bool(minimum>=a['minimum_external_gap_mm'] and not service and all(r['minimum_edge_margin_mm']>=0 and r['missing_floor_bond_area_mm2']<.01 and r['plan_gap_to_intake_mm']>0 for r in rows)),
            'loaded_gap_verified':False,'adhesion_verified':False,'structural_load_verified':False,
            'limits':['The 0.25 mm compression and 0.25 mm local floor-deflection budgets require loaded measurements.',
                      'Clearance is for a hard flat surface; soft surfaces can block the inlet.',
                      'Foot adhesion, rocking, case stiffness and the complete mass distribution need a physical test.']}

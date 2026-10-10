#!/usr/bin/env python3
"""Check the proposed cooler against the saved thin case without editing a PCB."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import cadquery as cq
from shapely.geometry import LineString, box as rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'mechanical/case-prototype'
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(HERE))
# Import the earlier build first: both case folders contain a build.py.
sys.path.remove(str(HERE))
import build as baseline
sys.path.insert(0, str(HERE))
import remote_cooler
import usb_harness
from cad import bounds, render, export_step, compound
from review import bbox_overlap, intersection_volume
from cooling_review import screen_component_heights
from component_heights import resolve
from usb_collision import Checks
from shapely.geometry import Polygon
from shapely.ops import unary_union


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_case():
    spec = importlib.util.spec_from_file_location('flush_build', HERE / 'build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parts, sources, mounts = module.load_model()
    return parts, module.C, sources


def screen_heights(table, targets, tops, settings):
    flat=[p for p in targets if 'remote_pipe_offset' in p]
    others=[p for p in targets if 'remote_pipe_offset' not in p]
    result=screen_component_heights(table,others,tops,settings)
    reservations=set(result['assembly_height_reservations'])
    for part in table:
        if part['dnp'] or part['side']!='front' or (part['board']=='center' and part['reference']=='A1'):continue
        rings=part['courtyards_installed_mm']['front']
        if not rings:continue
        area=unary_union([Polygon(r['outer'],r['holes']) for r in rings])
        height=resolve(part,settings);name=part['board']+'/'+part['reference']
        for target in flat:
            if not cooler_plan(target).intersects(area):continue
            available=target['shape'].BoundingBox().zmin-tops[part['board']]
            row={'part':name,'mpn':part['mpn'],'near':target['name'],'available_height_mm':round(available,4),
                 'screen':'saved courtyard against the conservative plan of a constant-height pipe extrusion'}
            if height is None:
                result['unverified_component_height_screens'].append(row)
            else:
                row.update(height,planning_gap_mm=round(available-height['height_mm'],4))
                result['component_height_crossings'].append(row)
                if row['planning_gap_mm']<0:result['known_component_height_conflicts'].append(row)
                if height['basis']=='assembly_reservation':reservations.add(name)
    result['assembly_height_reservations']=sorted(reservations)
    return result


def cooler_plan(part):
    plan=remote_cooler.planar_bound(part['shape'])
    assert plan is not None,'unregistered pipe extrusion'
    return plan


def evaluate(parts, case, sources, draw=True):
    c = remote_cooler.config()
    for p in [HERE/'cooler.json',HERE/'remote_cooler.py',HERE/'check_cooler.py',
              HERE/'reference/delta-fan-source.json',HERE/'reference/BFB04512HHA-DV52.step',
              ROOT/'mechanical/component-placement.json',BASE/'cooling-datums.json',
              HERE/'usb-part-heights.json',HERE/'cooler-part-heights.json',BASE/'height-allowances.json']:
        sources[str(p.relative_to(ROOT))] = digest(p)
    new = [p for p in parts if p.get('remote_cooler')] or remote_cooler.make_parts(case)
    remote_cooler.register_shapes(new)
    print('cooler solids built',flush=True)
    fixed = [p for p in parts if not p.get('moving') and not p.get('remote_cooler') and p['group'] not in ['cooling','changes','keepout']]
    rigid=[];allowances=[];internal=[]
    pieces=[]
    for p in fixed:
        if not p['name'].startswith(('usb5-','harness-USB-')) or p.get('power_wire') or p.get('intentional_wire_grip'):continue
        if p['name'].endswith('-carrier'):
            from cad import box
            side='left' if '-left-' in p['name'] else 'right'
            seam=70.75 if side=='left' else 299.25;bracket=130 if side=='left' else 225
            for region in [box(seam-4.5,0,0,9,260,26),box(bracket-5.1,100.9,0,10.2,25,26)]:
                cropped=p['shape'].intersect(region)
                if cropped.Volume()>.001:pieces.append({**p,'shape':cropped})
        else:pieces.append(p)
    cable_data=json.loads((HERE/'usb-harness.json').read_text())
    wire_checks=Checks(parts+new,case,cable_data,pieces)
    for p in new:
        if p['name'].startswith('CPU-mount'):continue
        for q in fixed:
            if not bbox_overlap(p['shape'],q['shape']):continue
            if q['group']=='wiring':volume=wire_checks.volume(q,p)
            else:volume=intersection_volume(p['shape'],q['shape'])
            if volume>.01:
                row={'cooler':p['name'],'other':q['name'],'overlap_mm3':round(volume,5)}
                (allowances if p['group']=='keepout' else rigid).append(row)
        print('checked',p['name'],flush=True)
    physical=[p for p in new if p['group']=='cooling']
    for i,p in enumerate(physical):
        for q in physical[i+1:]:
            if not bbox_overlap(p['shape'],q['shape']):continue
            v=intersection_volume(p['shape'],q['shape'])
            if v>.01:internal.append({'a':p['name'],'b':q['name'],'overlap_mm3':round(v,5)})
    table,settings=usb_harness.height_inputs()
    extra=json.loads((HERE/'cooler-part-heights.json').read_text())
    for part in table:
        if part.get('mpn') in extra['manufacturer_maximums']:
            h=extra['manufacturer_maximums'][part['mpn']]
            part.update(height_mm=h['height_mm'],height_kind='maximum',height_status='verified_maximum',height_source_url=h['source'],height_basis=h['basis'])
    settings['reservations'].update(extra['reservations'])
    targets=[p for p in new if p['name'].endswith('-upper-clearance') or p['name'] in ['blower-size-and-position-allowance','blower-inlet-space','stepped-copper-plate','slotted-copper-fin-stack']]
    print('checking component heights',flush=True)
    heights=screen_heights(table,targets,{b:case['boards']['main_bottom_H']+1.6 for b in ['left','center','right']},settings)
    pipe=c['pipes'];routes=[]
    plate=json.loads((BASE/'cooling-datums.json').read_text())
    hx,hy,hw,hd=plate['spreader_xy_mm'];fx,fy,fw,fd=c['fins']['xywh']
    for offset in pipe['lane_offsets_mm']:
        points,row=remote_cooler.pipe_path(pipe,offset)
        path=LineString(points)
        hot=path.intersection(rectangle(hx,hy,hx+hw,hy+hd)).length
        cold=path.intersection(rectangle(fx,fy,fx+fw,fy+fd)).length
        effective=pipe['stock_length_mm']-(hot+cold)/2
        radius=min(row['bend_radii_mm'])-(pipe['width_mm']+pipe['width_tolerance_mm'])/2
        assert abs(row['analytic_length_mm']-row['sampled_length_mm'])<.001
        assert radius>=pipe['catalogue_minimum_radius_for_6mm_mm']
        routes.append({**row,'lane_offset_mm':offset,'minimum_inside_radius_mm':radius,
                       'ideal_hot_contact_span_mm':hot,'ideal_cold_contact_span_mm':cold,
                       'ideal_effective_length_mm':effective,'straight_catalogue_comparison_W':pipe['catalogue_Qt_W_m']*1000/effective})
    mount_conflicts=[]
    for p in new:
        if not p['name'].startswith('heatpipe') or 'allowance' not in p['name']:continue
        for q in new:
            if not q['name'].startswith('CPU-mount'):continue
            v=intersection_volume(p['shape'],q['shape']) if bbox_overlap(p['shape'],q['shape']) else 0
            if v>.001:mount_conflicts.append({'pipe':p['name'],'mount':q['name'],'overlap_mm3':v})
    report={'date':c['date'],'source_hashes':sources,'configuration':c,
            'nominal_rigid_conflicts':rigid,'size_position_and_inlet_conflicts':allowances,
            'internal_cooler_conflicts':internal,'component_height_screen':heights,
            'pipe_routes':routes,'pipe_mount_space_conflicts':mount_conflicts,
            'nominal_geometry_pass':not(rigid or allowances or internal or mount_conflicts or heights['known_component_height_conflicts'] or heights['unverified_component_height_screens']),
            'part_bounds_construction_frame':{p['name']:bounds(p['shape']) for p in new},
            'PCB_changes_applied':False,'fan_endpoint_schematic_updated':False,
            'physical_fit_verified':False,'formed_pipe_capacity_verified':False,
            'CPU_clamp_load_verified':False,'thermal_performance_verified':False,
            'manufacturing_ready':False,
            'limits':['Nominal PCB models do not replace the component-height screen.',
                      'The keyboard carrier is a reservation; openings need structural and underside-component checks.',
                      'Continuous hot/cold spans are assumed only for the catalogue heatpipe comparison.',
                      'The fan harness, cooler mounts, duct, inlet supply and final joint geometry are unfinished.']}
    (HERE/'cooler-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['nominal_rigid_conflicts','size_position_and_inlet_conflicts','internal_cooler_conflicts','pipe_mount_space_conflicts']},indent=2),flush=True)
    print('Height conflicts:',len(heights['known_component_height_conflicts']),'missing:',len(heights['unverified_component_height_screens']),flush=True)
    for row in heights['known_component_height_conflicts']+heights['unverified_component_height_screens']:print(row,flush=True)
    if draw:
        out=HERE/'views';out.mkdir(exist_ok=True)
        visible=[p for p in fixed if p['group'] in ['boards','wiring'] and not p['name'].startswith('keyboard')]+physical
        render(visible,out/'remote-cooler.png','right-side cooler / mounting and thermal tests still needed',direction=(.15,-.3,1.6),size=(1700,1100),focus=((272,-103,11),112))
        render(physical,out/'remote-cooler-parts.png','two uncut 250 mm pipes / recessed copper contact plate',direction=(1,-1,1.5),size=(1700,1100))
        export_step(compound(p['shape'] for p in physical),HERE/'exports/remote-cooler.step')
        reopened=cq.importers.importStep(str(HERE/'exports/remote-cooler.step')).val()
        assert reopened.isValid()
    for path,sha in sources.items():assert digest(ROOT/path)==sha,path
    return report


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--no-render',action='store_true');args=a.parse_args()
    parts,case,sources=load_case()
    evaluate(parts,case,sources,not args.no_render)

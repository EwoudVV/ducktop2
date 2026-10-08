"""Check cooling solids and the reserved inlet space against the saved case."""
import json
import hashlib
from cad import HERE,box,cylinder


def screen_component_heights(parts, targets, board_tops, settings):
    """Compare each courtyard with actual overhead material, including holes.

    A courtyard is a conservative plan envelope. A positive margin is a
    packaging screen, not proof of physical fit or connector service access.
    """
    from review import bbox_overlap
    from component_heights import resolve
    from shapely.geometry import Polygon, box as planar_box
    from cables import polygon_prism
    missing, crossings, conflicts = [], [], []
    reservations = set()
    for part in parts:
        if part['dnp'] or part['side'] != 'front':
            continue
        if part['board'] == 'center' and part['reference'] == 'A1':
            continue  # Separate module/contact tolerance study.
        top = board_tops[part['board']]
        rings = part['courtyards_installed_mm']['front']
        resolved = resolve(part, settings)
        name = part['board'] + '/' + part['reference']
        for target in targets:
            shape = target['shape']; bb = shape.BoundingBox()
            if bb.zmax <= top:
                continue
            region = planar_box(bb.xmin, -bb.ymax, bb.xmax, -bb.ymin)
            bottoms = []
            for ring in rings:
                if not region.intersects(Polygon(ring['outer'], ring['holes'])):
                    continue
                column = polygon_prism(ring['outer'], top, bb.zmax - top + 1)
                for hole in ring['holes']:
                    column = column.cut(polygon_prism(hole, top - .1, bb.zmax - top + 1.2))
                if not bbox_overlap(column, shape):
                    continue
                hit = shape.intersect(column)
                if hit.Volume() > .001:
                    bottoms.append(hit.BoundingBox().zmin)
            if not bottoms:
                continue
            available = min(bottoms) - top
            row = {'part': name, 'mpn': part['mpn'], 'near': target['name'],
                   'available_height_mm': round(available, 4),
                   'screen': 'saved courtyard below actual cooling material; assembly space is included in the resolved height'}
            if resolved is None:
                missing.append({**row,
                    'conservative_height_limit_mm': round(available - settings['manufacturer_assembly_allowance_mm'], 4),
                    'basis': 'missing maximum height or explicit assembly reservation'})
                continue
            margin = available - resolved['height_mm']
            row.update(resolved, planning_gap_mm=round(margin, 4))
            crossings.append(row)
            if resolved['basis'] == 'assembly_reservation':
                reservations.add(name)
            if margin < -1e-5:
                conflicts.append(row)
    return {'unverified_component_height_screens': missing,
            'component_height_crossings': crossings,
            'known_component_height_conflicts': conflicts,
            'assembly_height_reservations': sorted(reservations)}


def check(m):
    from build import CONFIG
    from review import bbox_overlap
    cold=[p for p in m.parts if p['group']=='cooling']
    fixed=[p for p in m.parts if not p.get('moving') and p['group'] not in ['cooling','keepout','routes']]
    clashes=[]
    def overlap(a,b):
        if not bbox_overlap(a,b):return 0
        # Native board compounds contain many remote solids. Screen each
        # bounding box before doing the exact intersection.
        return sum(max(0,s.intersect(a).Volume()) for s in b.Solids() if bbox_overlap(a,s))
    for a in cold:
        for b in fixed:
            v=overlap(a['shape'],b['shape'])
            if v>.02:clashes.append({'cooling':a['name'],'part':b['name'],'overlap_mm3':round(v,4)})
    internal=[]
    for i,a in enumerate(cold):
        for b in cold[i+1:]:
            v=overlap(a['shape'],b['shape'])
            if v>.02:internal.append({'a':a['name'],'b':b['name'],'overlap_mm3':round(v,4)})
    c=CONFIG['cooling'];x,y,h,w,d,t=c['blower'];start=h+t+c.get('blower_height_tolerance',.3)
    inlet=box(x,y,start,w,d,c.get('intake_plenum',3))
    for xx,yy in [(x+41.75,y+3.25),(x+41.75,y+41.75),(x+3.25,y+41.75)]:
        inlet=inlet.cut(cylinder(xx,yy,start-.1,2.75,c.get('intake_plenum',3)+.2))
    blocked=[]
    for p in fixed+[p for p in cold if 'blower' not in p['name']]:
        v=overlap(inlet,p['shape'])
        if v>.02:blocked.append({'part':p['name'],'overlap_mm3':round(v,4)})
    result={'units':'mm','cooling_body_collisions':clashes,'internal_cooling_collisions':internal,
            'inlet_obstructions':blocked,'inlet_gap_mm':c.get('intake_plenum',3),
            'inlet_start_above_bottom_mm':start,
            'scope':'nominal solids and a conservative inlet volume excluding the three corner fasteners; fan orientation, exact inlet shape and installed airflow need physical confirmation',
            'spreader_hardware_selected':False,'heatpipe_supplier_qualified':False,
            'TIM_compression_verified':False,'both_CPU_thermal_tests_complete':False,
            'manufacturing_ready':False}
    # Absent maximum-height data stays visible even when the native nominal
    # models fit. Confirm the XY screen against real cooling material so a
    # cradle opening or empty space inside a bent pipe is not counted as solid.
    from case_inputs import path as input_path
    from build import pcb_top
    settings=json.loads((HERE/'height-allowances.json').read_text())
    parts=json.loads(input_path('component-placement.json').read_text())['parts']
    targets=cold+[p for p in fixed if p['name'].startswith(('blower-','fan-through'))]
    result.update(screen_component_heights(parts,targets,
                  {p['board']:pcb_top(p['board']) for p in parts},settings))
    result['module_contact_basis']='A1 uses nominal official module and cooler geometry in cooling-datums.json; package tolerances, TIM compression and clamping loads remain unqualified.'
    result['source_sha256']={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                             for name in ['assembly.json','cooling.py','cooling-datums.json','cooling_review.py','height-allowances.json',
                                          'component_heights.py','reference/pcb-snapshot/manifest.json',
                                          'reference/pcb-snapshot/inputs/component-placement.json']}
    (HERE/'cooling-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print('cooling checks', {k:len(result[k]) for k in ['cooling_body_collisions','internal_cooling_collisions','inlet_obstructions',
                                                     'known_component_height_conflicts','unverified_component_height_screens']},flush=True)
    return result

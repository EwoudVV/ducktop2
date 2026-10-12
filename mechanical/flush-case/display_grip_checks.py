"""Liner fit, screw extraction and rear-cover removal in the cable study."""
import json
from pathlib import Path

import cadquery as cq
import display_grips
from cad import bounds
from review import bbox_overlap, intersection_volume


def component_heights(new, case, pose, additions):
    import usb_harness
    from cooling_review import screen_component_heights
    table,settings=usb_harness.height_inputs()
    here=Path(__file__).resolve().parent
    for filename in ['cooler-part-heights.json','fan-harness-heights.json','display-part-heights.json']:
        extra=json.loads((here/filename).read_text());settings['reservations'].update(extra.get('reservations',{}))
        for p in table:
            h=extra.get('manufacturer_maximums',{}).get(p.get('mpn'))
            if h:p.update(height_mm=h['height_mm'],height_kind='maximum',height_source_url=h['source'],height_basis=h['basis'])
    targets=[]
    for a in sorted(set(range(0,136,2))|{135}):
        for p in [q for q in new if q.get('display_grip')]+additions:
            if a and not p.get('moving'):continue
            targets.append({**pose(p,a),'name':p['name']+f' at {a} degrees'})
    bbs=[p['shape'].BoundingBox() for p in targets]
    limits=(min(b.xmin for b in bbs),min(-b.ymax for b in bbs),max(b.xmax for b in bbs),max(-b.ymin for b in bbs))
    candidates=[]
    for p in table:
        if p['dnp'] or p['side']!='front' or p['board']=='radio':continue
        for r in p['courtyards_installed_mm']['front']:
            xs,ys=zip(*r['outer'])
            if max(xs)>=limits[0] and min(xs)<=limits[2] and max(ys)>=limits[1] and min(ys)<=limits[3]:
                candidates.append(p);break
    tops={name:case['boards']['main_bottom_H']+1.6 for name in ['left','center','right']}
    tops.update(bms=case['boards']['bms_bottom_H']+1.6,keyboard=case['boards']['keyboard_bottom_H']+.8)
    report=screen_component_heights(candidates,targets,tops,settings)
    for key in ['component_height_crossings','unverified_component_height_screens','known_component_height_conflicts']:
        for row in report[key]:row['screen']='saved courtyard below actual display hardware at the recorded opening angle'
    report['front_courtyards_in_plan_bounds']=len(candidates)
    return report


def evaluate(saved, adapted, new, case, pose, overlap):
    c = display_grips.config(); angle = c['service_opening_deg']
    physical = [p for p in adapted if not p.get('service') and p['group'] not in ['keepout', 'changes']]
    all_parts = physical+new
    guard_names = {p['name'] for p in new if p['name'].startswith(('display-guard-', 'display-rear-guard'))}
    fasteners = [p for p in new if p.get('fastener')]
    driver_hits = []; extraction_hits = []; cap_hits = []; guard_hits = []

    def removed_for(p):
        removed = {'deck'}
        if p['name'].startswith('display-lid-mount-'):
            removed.add('lid-skin')
        if p['name'].startswith('display-base-mount-'):
            removed |= guard_names
        return removed

    def compare(shape, obstacles, record, output):
        for q in obstacles:
            if not bbox_overlap(shape, q['shape']):
                continue
            volume, where = overlap(shape, q['shape'])
            if volume > .01:
                output.append({**record, 'part': q['name'], 'overlap_mm3': round(volume, 5), 'where': where})

    access = []
    for p in fasteners:
        removed = removed_for(p)
        tool = display_grips.driver(p)
        obstacles = [pose(q, angle) for q in all_parts if q['name'] not in removed]
        compare(pose(tool, angle)['shape'], obstacles, {'tool': tool['name']}, driver_hits)
        lifted = [p]
        if p['fastener_kind'] == 'guard':
            lifted.append(next(q for q in new if q['name'] == p['name'].replace('-screw-', '-washer-')))
        excluded = removed | {q['name'] for q in lifted}
        obstacles = [pose(q, angle) for q in all_parts if q['name'] not in excluded]
        for half_mm in range(0, 25):
            travel=half_mm/2
            for q in lifted:
                moved = {**q, 'shape': q['shape'].translate((0, 0, p['driver_sign']*travel))}
                compare(pose(moved, angle)['shape'], obstacles,
                        {'fastener': q['name'], 'withdrawal_mm': travel}, extraction_hits)
        access.append({'fastener': p['name'], 'opening_deg': angle, 'remove_first': sorted(removed),
                       'driver_origin_xyH': p['driver_origin_xyH'], 'local_direction_H': p['driver_sign']})
        print('display screw access', p['name'], flush=True)

    cap_records = []
    for role, sign in [('base', 1), ('lid', -1)]:
        cap = next(p for p in new if p['name'] == f'display-{role}-anchor-cap')
        half = 'upper' if role == 'base' else 'lower'
        liner = next(p for p in new if p['name'] == f'display-{role}-liner-{half}')
        removed = {'deck', cap['name'], liner['name']} | {p['name'] for p in new if p['name'].startswith(f'display-{role}-cap-screw-')}
        obstacles = [p for p in all_parts if p['name'] not in removed]
        x = c['fixed_X_mm'] if role == 'base' else c['lid_X_mm']
        gauge = pose({'shape': display_grips.nominal_gauge(x), 'moving': role == 'lid'}, angle)['shape']
        for half_mm in range(0, 17):
            travel=half_mm/2
            for p in [cap, liner]:
                moved = pose({**p, 'shape': p['shape'].translate((0, 0, sign*travel))}, angle)['shape']
                for q in obstacles:
                    if p.get('grip_liner') and display_grips.allocated_liner_overlap(p, q):
                        continue
                    compare(moved, [pose(q, angle)], {'cap_part': p['name'], 'travel_mm': travel}, cap_hits)
                if p.get('grip_liner'):
                    volume = intersection_volume(moved, gauge)
                    if volume > .001:
                        cap_hits.append({'cap_part': p['name'], 'travel_mm': travel, 'part': 'nominal cable', 'overlap_mm3': volume})
        cap_records.append({'role': role, 'opening_deg': angle, 'travel_mm': 8, 'step_mm': .5,
                            'local_direction_H': sign, 'removed_parts': sorted(removed)})

    guard = next(p for p in new if p['name'] == 'display-rear-guard')
    removed = {'deck', guard['name']} | {p['name'] for p in new if p['name'].startswith(('display-guard-screw-', 'display-guard-washer-'))}
    obstacles = [pose(p, c['guard_removal_opening_deg']) for p in all_parts if p['name'] not in removed]
    for half_mm in range(0, c['guard_rearward_removal_mm']*2+1):
        travel=half_mm/2
        moved = guard['shape'].translate((0, travel, 0))
        compare(moved, obstacles, {'guard_rearward_travel_mm': travel}, guard_hits)

    # Modified reinforcement solids contain new posts. Check their added
    # material against everything except the exact solid they belong to.
    old = {p['name']: p for p in saved}; added_hits = []; added_rows = []; additions=[]
    samples = sorted(set(range(0, 136, 2)) | {135})
    for p in adapted:
        if p['name'] not in ['rear-base-reinforcement', 'rear-lid-backing-member']:
            continue
        extra = p['shape'].cut(old[p['name']]['shape'])
        if not extra.Solids() or extra.Volume() < .01:
            continue
        added_rows.append({'host': p['name'], 'added_volume_mm3': round(extra.Volume(), 4)})
        additions.append({**p,'shape':extra})
        for a in samples:
            shape = pose({**p, 'shape': extra}, a)['shape']
            obstacles = [pose(q, a) for q in all_parts if q['name'] != p['name'] and
                         (not a or q.get('moving', False) != p.get('moving', False))]
            compare(shape, obstacles, {'added_host': p['name'], 'angle_deg': a}, added_hits)

    liner_rows = []
    for role, x in [('base', c['fixed_X_mm']), ('lid', c['lid_X_mm'])]:
        gauge = display_grips.nominal_gauge(x)
        for p in [p for p in new if p.get('grip_liner') == role]:
            liner_rows.append({'part': p['name'], 'cable_overlap_mm3': round(intersection_volume(p['shape'], gauge), 7),
                               'nominal_radial_gap_mm': round(p['shape'].distance(gauge), 7),
                               'solids': len(p['shape'].Solids()), 'valid': p['shape'].isValid()})
    liner_ok = all(p['valid'] and p['solids'] == 1 and p['cable_overlap_mm3'] == 0 and
                   p['nominal_radial_gap_mm'] >= .049 for p in liner_rows)
    heights=component_heights(new,case,pose,additions)
    height_ok=not heights['unverified_component_height_screens'] and not heights['known_component_height_conflicts']
    outline=case['outline'];outside=[]
    ceiling=case['hinges']['pivot_height']+case['lid']['back_inner_height_from_axis']+case['lid']['skin']
    for p in new:
        b=p['shape'].BoundingBox()
        excess=max(outline['x_min']-b.xmin,b.xmax-outline['x_max'],outline['y_min']+b.ymax,-b.ymin-outline['y_max'],b.zmax-ceiling,-b.zmin)
        if excess>.001:outside.append({'part':p['name'],'excess_mm':round(excess,5)})
    # Required movement/contact space is checked without assuming friction
    # or a safe clamping pressure for the still-unselected cable construction.
    return {'driver_access': access, 'driver_conflicts': driver_hits, 'screw_extraction_conflicts': extraction_hits,
            'screw_extraction_travel_mm': 12, 'screw_extraction_step_mm': .5,
            'cap_removal': cap_records, 'cap_removal_conflicts': cap_hits,
            'guard_removal': {'opening_deg': c['guard_removal_opening_deg'], 'rearward_travel_mm': c['guard_rearward_removal_mm'],
                              'step_mm': .5, 'remove_first': sorted(removed), 'conflicts': guard_hits,
                              'sequence': 'Open to 105 degrees, remove the deck and both guard screws/washers, then close the lid before sliding the guard rearward. Reopen to work on the jaws.'},
            'added_reinforcement_material': added_rows, 'added_material_conflicts': added_hits,
            'liner_fit': liner_rows, 'liner_fit_pass': liner_ok,
            'liner_collision_scope': 'The 0.3 mm cable-position allowance overlaps the lining inside its two defined jaws. Those exact pairs use the separate 3 mm nominal cable gauge; all other solid pairs remain checked.',
            'mount_stack_mm': {'cap_screw_nominal_engagement': 5.1, 'base_mount_nominal_engagement': 3,
                               'lid_mount_nominal_engagement': 3, 'guard_screw_nominal_engagement': 4.5,
                               'lid_mount_engagement_after_length_and_seating_budget': 2.46,
                               'lid_mount_tip_to_tongue_bottom_after_length_and_seating_budget': .46},
            'closed_outline_or_height_excess': outside, 'component_height_screen': heights,
            'nominal_hardware_geometry_pass': liner_ok and height_ok and not(driver_hits or extraction_hits or cap_hits or guard_hits or added_hits or outside),
            'pull_retention_verified': False, 'cable_crush_limit_verified': False, 'manufacturing_ready': False,
            'limits': ['Nominal sampled movements do not prove continuous clearance or fit across manufacturing tolerances.',
                       'The lining currently has clearance; friction, compression, material and pull retention must be established with the selected cable.',
                       'Thread engagement does not include incomplete lead threads and does not establish joint strength.',
                       'The cable guard covers the straight section; the moving-tail opening is not sealed.']}


def draw(parts, new, pose, render, here):
    from cad import box
    for role, x in [('base',225),('lid',163)]:
        group = [p for p in new if p['name'].startswith(f'display-{role}-') and p.get('display_grip')]
        region=box(x-17,-18,0,34,21,33)
        for p in parts:
            if p['name'] not in ['rear-base-reinforcement','rear-lid-backing-member']:continue
            if not bbox_overlap(p['shape'],region):continue
            shape=p['shape'].intersect(region)
            if shape.Solids():group.append({**p,'shape':shape,'color':(.58,.64,.67,.2)})
        direction = (.6, -1, .75) if role == 'base' else (.6, -1, -.75)
        render(group, here/f'views/display-{role}-grip.png', f'{role} cable grip / flush screws and replaceable lining / fit prototype', direction, (1550, 1050))
    hardware = [p for p in new if p.get('display_grip')]
    hardware.append({'name':'nominal-cable-gauge','shape':cq.Solid.makeCylinder(1.5,62,cq.Vector(163,15,19.3),cq.Vector(1,0,0)),'color':(.65,.28,.7)})
    render(hardware, here/'views/display-grips-and-guard.png', 'removable cable jaws and rear guard / 50 mm free span', (.25, -1, .7), (1650, 1000))

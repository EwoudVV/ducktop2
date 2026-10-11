"""Check stop contact, mounting clearances and access with the case open."""
import json
from pathlib import Path

import cadquery as cq
import lid_stops
from cad import box, bounds, compound, export_step
from review import bbox_overlap, intersection_volume

HERE = Path(__file__).resolve().parent


def physical(parts):
    return [p for p in parts if not p.get('service') and p['group'] not in ['keepout', 'changes']]


def height_screen(parts, case):
    import usb_harness
    from cooling_review import screen_component_heights
    table, settings = usb_harness.height_inputs()
    tops = {k: case['boards']['main_bottom_H']+1.6 for k in ['left', 'center', 'right']}
    tops.update(bms=case['boards']['bms_bottom_H']+1.6,
                keyboard=case['boards']['keyboard_bottom_H']+.8)
    table = [p for p in table if p['board'] in tops]
    for name in ['cooler-part-heights.json', 'fan-harness-heights.json', 'display-part-heights.json']:
        extra = json.loads((HERE/name).read_text()); settings['reservations'].update(extra.get('reservations', {}))
        for p in table:
            h = extra.get('manufacturer_maximums', {}).get(p.get('mpn'))
            if h:
                p.update(height_mm=h['height_mm'], height_kind='maximum', height_source_url=h['source'], height_basis=h['basis'])
    # Retain the worst clearance for each component/stop part over the sweep.
    rows = {}; missing = {}; conflicts = {}
    for angle in lid_stops.angles(case):
        targets = [{**lid_stops.pose(p, angle), 'sample_angle_deg': angle}
                   for p in parts if p.get('lid_stop') and (p.get('moving') or angle == 0)]
        result = screen_component_heights(table, targets, tops, settings)
        for label, output in [('component_height_crossings', rows),
                              ('unverified_component_height_screens', missing),
                              ('known_component_height_conflicts', conflicts)]:
            for row in result[label]:
                key = (row['part'], row['near'])
                if key not in output or row['available_height_mm'] < output[key]['available_height_mm']:
                    output[key] = {**row, 'angle_deg': angle,
                                   'screen': 'saved courtyard below actual stop material at sampled opening angles'}
    return {'component_height_crossings': list(rows.values()), 'unverified_height_limits': list(missing.values()),
            'height_conflicts': list(conflicts.values()), 'scope': 'Front courtyards and resolved heights; no physical fit or tolerance proof.'}


def evaluate(parts, case, sources):
    c = lid_stops.config(); all_parts = physical(parts); new = [p for p in all_parts if p.get('lid_stop')]
    by_name = {p['name']: p for p in parts}; hits = []; seen = set()
    # The main case sweep covers moving-versus-fixed pairs. Include all
    # same-frame pairs here, including new screws, washers and cut supports.
    for p in new:
        for q in all_parts:
            key = tuple(sorted([p['name'], q['name']]))
            if p['name'] == q['name'] or key in seen or p.get('moving') != q.get('moving'):
                continue
            seen.add(key)
            if not bbox_overlap(p['shape'], q['shape']):
                continue
            volume = intersection_volume(p['shape'], q['shape'])
            if volume > .01:
                hits.append({'a': p['name'], 'b': q['name'], 'overlap_mm3': round(volume, 5)})
    contact = []
    for side in ['left', 'right']:
        tab = by_name[side+'-lid-stop-tab']; block = by_name[side+'-lid-stop-block']['shape']
        for angle in [0, 90, 130, 134, 134.9, 135, 135.1, 136, 140]:
            shape = lid_stops.pose(tab, angle)['shape']
            contact.append({'side': side, 'angle_deg': angle,
                            'gap_mm': round(shape.distance(block), 7),
                            'overlap_mm3': round(intersection_volume(shape, block), 7)})
    service = []; remove = c['service']['remove_first']; angle = c['service']['lid_angle_deg']
    installed = [lid_stops.pose(p, angle) for p in all_parts if p['name'] not in remove]
    for driver in lid_stops.driver_envelopes():
        tool = lid_stops.pose(driver, angle)['shape']
        for p in installed:
            if not bbox_overlap(tool, p['shape']):
                continue
            volume = intersection_volume(tool, p['shape'])
            if volume > .01:
                service.append({'tool': driver['name'], 'part': p['name'], 'overlap_mm3': round(volume, 5)})
    heights = height_screen(parts, case)
    stacks = lid_stops.fastener_stacks()
    expected = all((v['gap_mm'] > 0 and v['overlap_mm3'] == 0) if v['angle_deg'] < 135 else
                   (v['gap_mm'] == 0 and v['overlap_mm3'] == 0) if v['angle_deg'] == 135 else
                   v['overlap_mm3'] > 0 for v in contact)
    result = {'date': c['date'], 'source_hashes': sources, 'configuration': c,
              'requested_opening_deg': 135, 'nominal_first_contact_deg': 135 if expected else None,
              'same_frame_conflicts': hits, 'contact_samples': contact, 'fastener_stacks': stacks,
              'driver_access': {'opening_deg': angle, 'remove_first': remove, 'tools': 12, 'conflicts': service},
              'component_height_screen': heights,
              'stop_geometry_pass': expected and not (hits or service or heights['unverified_height_limits'] or heights['height_conflicts']),
              'physical_fit_verified': False, 'stop_load_verified': False, 'manufacturing_ready': False,
              'limits': ['The main case report contains the full rigid movement check through 135 degrees, including the endpoint.',
                         'Overtravel contact is checked only for each intended tab/block pair; it is not an allowed opening range.',
                         'Screw shapes are clearance envelopes. Threads, countersink seating, locking, preload and torque need physical qualification.',
                         'No impact rating, hand load, fatigue life, hinge holding capacity or tolerance-qualified maximum angle is established.']}
    (HERE/'lid-stop-checks.json').write_text(json.dumps(result, indent=2)+'\n')
    print('lid stops: static', len(hits), 'access', len(service), 'height', len(heights['height_conflicts']),
          'unknown', len(heights['unverified_height_limits']), 'contact', expected, flush=True)
    return result


def draw(parts):
    from draw_cooler import render
    new = [p for p in parts if p.get('lid_stop')]
    crops = []
    region = box(45, -19, 0, 47, 31, 35)
    for p in physical(parts):
        if p.get('lid_stop') or p['name'] not in ['base-floor', 'base-walls', 'deck', 'rear-base-reinforcement', 'rear-lid-backing-member', 'lid-skin', 'lid-rim']:
            continue
        if not bbox_overlap(p['shape'], region):
            continue
        s = p['shape'].intersect(region)
        if s.Solids():
            crops.append({**p, 'shape': s, 'color': (*p['color'][:3], .22)})
    left = [p for p in new if p['name'].startswith('left-')]
    for angle in [0, 105, 135]:
        render([lid_stops.pose(p, angle) for p in crops+left], HERE/f'views/lid-stop-{angle}.png',
               f'left lid stop / {angle} degrees / metal prototype', (.9, -1.3, .75), (1550, 1050))
    access = [lid_stops.pose(p, 105) for p in crops+left if p['name'] not in lid_stops.config()['service']['remove_first']]
    access += [lid_stops.pose(p, 105) for p in lid_stops.driver_envelopes() if p['name'].startswith('left-')]
    render(access, HERE/'views/lid-stop-access.png', 'stop fastener access / deck and lid skin removed', (1, -1.5, .8), (1550, 1050))
    path = HERE/'exports/lid-stops.step'
    export_step(compound(p['shape'] for p in new+crops), path)
    reopened = cq.importers.importStep(str(path)).val()
    assert reopened.isValid()
    return {'path': str(path.relative_to(HERE)), 'solids': len(reopened.Solids()), 'reopens': True}

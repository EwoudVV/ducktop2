"""Rear-mounted opening stops and their installed fastener envelopes."""
import json
import math
from pathlib import Path

import cadquery as cq
from cad import box, cylinder

HERE = Path(__file__).resolve().parent


def config():
    return json.loads((HERE/'lid-stop-hardware.json').read_text())


def angles(case):
    maximum = case['hinges']['requested_opening_deg']
    assert maximum == config()['requested_opening_deg'] == 135
    return sorted(set(range(0, maximum + 1, case['hinges']['check_step_deg'])) | {maximum})


def pose(part, angle):
    if not part.get('moving'):
        return part
    c = config(); pivot = (0, -c['axis_y_mm'], c['axis_H_mm'])
    return {**part, 'shape': part['shape'].rotate(pivot, (1, pivot[1], pivot[2]), -angle)}


def sector(x, width, inner, outer, start, end):
    c = config()
    def point(radius, theta):
        return (-(c['axis_y_mm'] + radius * math.cos(theta)),
                c['axis_H_mm'] + radius * math.sin(theta))
    w = cq.Workplane('YZ').moveTo(*point(outer, start))
    w = w.threePointArc(point(outer, (start+end)/2), point(outer, end))
    if inner:
        w = w.lineTo(*point(inner, end)).threePointArc(point(inner, (start+end)/2), point(inner, start))
    else:
        w = w.lineTo(-c['axis_y_mm'], c['axis_H_mm'])
    return w.close().extrude(width).val().translate((x-width/2, 0, 0))


def mount_positions(x, c=None):
    c = c or config()
    return {kind: [(x+dx, y) for dx, y in c[kind+'_mounts_relative_XY']]
            for kind in ['base', 'lid']}


def make_parts():
    c = config(); result = []
    face = math.atan2(c['contact_face_direction_YH'][1], c['contact_face_direction_YH'][0])
    closed = face-math.radians(c['requested_opening_deg'])
    def add(name, shape, moving, role, color):
        assert shape.isValid() and len(shape.Solids()) == 1, name
        result.append({'name': name, 'shape': shape, 'moving': moving, 'group': 'supports',
                       'lid_stop': True, 'stop_role': role, 'color': color})
    for side, x in zip(['left', 'right'], c['centres_X_mm']):
        width = c['tab_width_mm']; outer = c['tab_outer_radius_mm']
        hook = sector(x, width, c['tab_inner_radius_mm'], outer, math.radians(-100), math.radians(50))
        hook = hook.fuse(sector(x, width, c['contact_inner_radius_mm'], outer, math.radians(-100), closed))
        hook = hook.fuse(sector(x, width, c['tab_inner_radius_mm'], c['tab_upper_outer_radius_mm'], 0, math.radians(50)))
        hook = hook.intersect(box(x-10, -30, 0, 20, 29.5, c['backing_bottom_H']))
        dx, y, w, d = c['root_foot_xywh_relative_to_centre']
        hook = hook.fuse(box(x+dx, y, c['root_foot_bottom_H'], w, d, c['root_foot_thickness_mm']))
        mounts = mount_positions(x, c)
        for xx, yy in mounts['lid']:
            hook = hook.cut(cylinder(xx, yy, c['root_foot_bottom_H']-.1,
                                     c['assembly_thread_cavity_diameter_mm']/2,
                                     c['root_foot_thickness_mm']+.2))
        add(side+'-lid-stop-tab', hook, True, 'tab', (.64, .65, .69))
        stop = sector(x, 26, 0, c['block_outer_radius_mm'], face, math.pi).intersect(box(x-13, -18, 19.3, 26, 14, 9.2))
        window = width+1.2
        rear = box(x-13, -18, 4.2, 26, 2.8, 22.3).cut(box(x-window/2, -18.1, 4.1, window, 3, 15.2))
        stop = stop.fuse(rear, box(x-13, -18, 1.2, 26, 16, 3))
        for xmin in [x-13, x+7]:
            stop = stop.fuse(box(xmin, -15.2, 4.2, 6, 5.2, 22.3))
        for xmin in [x-21, x+13]:
            stop = stop.fuse(box(xmin, -16.5, 7.2, 8, 16, 3))
        for xx, yy in mounts['base']:
            stop = stop.cut(cylinder(xx, yy, 7.1, c['clearance_hole_diameter_mm']/2, 3.2))
        stop = stop.cut(box(x-13.1, -18.1, 26.6, 26.2, 1.7, 4))
        add(side+'-lid-stop-block', stop, False, 'block', (.26, .52, .61))
        for i, (xx, yy) in enumerate(mounts['base']):
            washer = cylinder(xx, yy, 10.2, 3, .5).cut(cylinder(xx, yy, 10.1, 1.6, .7))
            head = cylinder(xx, yy, 10.7, c['base_screw']['head_max_diameter_mm']/2,
                            c['base_screw']['head_height_allocation_mm'])
            # Maximum screw length is retained in the installed envelope.
            length = c['base_screw']['length_mm']+c['base_screw']['length_tolerance_mm']
            shaft = cylinder(xx, yy, 10.7-length, 1.5, length)
            add(f'{side}-stop-base-screw-{i}', head.fuse(shaft), False, 'base-screw', (.48, .49, .52))
            add(f'{side}-stop-base-washer-{i}', washer, False, 'washer', (.58, .59, .62))
        for i, (xx, yy) in enumerate(mounts['lid']):
            screw = c['lid_screw']; top = c['backing_top_H']
            head = cq.Solid.makeCone(screw['theoretical_head_diameter_allocation_mm']/2, 1.5,
                                    screw['maximum_head_height_mm'], cq.Vector(xx, -yy, top), cq.Vector(0, 0, -1))
            length = screw['length_mm']+screw['length_tolerance_mm']
            shaft = cylinder(xx, yy, top-length, 1.5, length)
            add(f'{side}-stop-lid-screw-{i}', head.fuse(shaft), True, 'lid-screw', (.48, .49, .52))
    return result


def adapt_case(parts, case):
    c = config()
    assert case['hinges']['pivot_y'] == c['axis_y_mm'] and case['hinges']['pivot_height'] == c['axis_H_mm']
    result = []; changes = []
    names = {'base-walls', 'rear-base-reinforcement', 'deck', 'rear-lid-backing-member'}
    for part in parts:
        if part['name'] not in names:
            result.append(part); continue
        shape = part['shape']; before = shape.Volume()
        for x in c['centres_X_mm']:
            if part['name'] == 'base-walls':
                shape = shape.cut(box(x-13.2, -18.1, 1.1, 26.4, 1.5, 22.9))
            elif part['name'] == 'rear-base-reinforcement':
                shape = shape.cut(box(x-13.2, -16.1, 1.1, 26.4, 14.2, 3.3))
                for xx, yy in mount_positions(x, c)['base']:
                    shape = shape.fuse(cylinder(xx, yy, 4.2, c['base_boss_radius_mm'], 3))
                    shape = shape.cut(cylinder(xx, yy, 1.1, c['assembly_thread_cavity_diameter_mm']/2, 6.2))
            elif part['name'] == 'deck':
                shape = shape.cut(box(x-14, -19, 23.5, 28, 27.5, 2))
            else:
                for xx, yy in mount_positions(x, c)['lid']:
                    shape = shape.cut(cylinder(xx, yy, 29.2, 1.6, 3.2))
                    shape = shape.cut(cq.Solid.makeCone(3.46, 1.6, 1.86, cq.Vector(xx, -yy, 32.3), cq.Vector(0, 0, -1)))
        assert shape.isValid() and shape.Solids(), part['name']
        changes.append({'part': part['name'], 'volume_before_mm3': round(before, 4),
                        'volume_after_mm3': round(shape.Volume(), 4), 'solids': len(shape.Solids())})
        result.append({**part, 'shape': shape})
    assert {v['part'] for v in changes} == names
    return result+make_parts(), changes


def fastener_stacks():
    c = config(); b = c['base_screw']; w = c['base_washer']; l = c['lid_screw']
    base_stack = c['base_wing_top_H']-c['base_boss_top_H']
    base_min = b['length_mm']-b['length_tolerance_mm']-w['thickness_range_mm'][1]-base_stack
    base_max = b['length_mm']+b['length_tolerance_mm']-w['thickness_range_mm'][0]-base_stack
    backing = c['backing_top_H']-c['backing_bottom_H']
    lid_min = l['length_mm']-l['length_tolerance_mm']-backing-l['seating_and_stack_budget_mm']
    lid_max = l['length_mm']+l['length_tolerance_mm']-backing+l['seating_and_stack_budget_mm']
    return {'base_nominal_engagement_mm': b['length_mm']-w['thickness_mm']-base_stack,
            'base_engagement_screw_and_washer_range_mm': [round(base_min, 4), round(base_max, 4)],
            'base_tip_to_floor_after_screw_and_washer_tolerances_mm': round(c['base_boss_top_H']-base_max-1.2, 4),
            'lid_nominal_engagement_mm': l['length_mm']-backing,
            'lid_engagement_with_length_and_seating_budget_mm': [round(lid_min, 4), round(lid_max, 4)],
            'lid_tip_to_root_bottom_minimum_mm': round(c['root_foot_thickness_mm']-lid_max, 4),
            'limits': 'Engagement excludes thread lead-in loss. Base machining tolerances, preload, thread strength and locking method still need qualification.'}


def driver_envelopes():
    c = config(); s = c['service']; parts = []
    for side, x in zip(['left', 'right'], c['centres_X_mm']):
        for kind, points in mount_positions(x, c).items():
            for i, (xx, yy) in enumerate(points):
                top = c['backing_top_H'] if kind == 'lid' else 12.5
                shaft = cylinder(xx, yy, top+.01, s['driver_shaft_diameter_mm']/2, s['driver_shaft_length_mm'])
                handle = cylinder(xx, yy, top+s['driver_shaft_length_mm'], s['handle_diameter_mm']/2, s['handle_length_mm'])
                parts.append({'name': f'{side}-{kind}-driver-{i}', 'shape': shaft.fuse(handle),
                              'moving': kind == 'lid', 'color': (.9, .61, .18, .4)})
    return parts

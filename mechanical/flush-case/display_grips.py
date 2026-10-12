"""Detachable display cable jaws, lining and rear guard for the fit study."""
import json
from pathlib import Path

import cadquery as cq
from cad import box, cylinder

HERE = Path(__file__).resolve().parent


def config():
    return json.loads((HERE/'display-grip-hardware.json').read_text())


def axial(x, y, h, radius, length, sign=1):
    return cq.Solid.makeCylinder(radius, length, cq.Vector(x, -y, h), cq.Vector(0, 0, sign))


def countersunk(x, y, h, length, sign):
    c = config(); allowance = c['screw_length_tolerance_8_mm'] if length == 8 else c['screw_length_tolerance_5_6_mm']
    head = cq.Solid.makeCone(c['countersunk_head_theoretical_diameter_mm']/2, 1,
                            c['countersunk_head_height_mm'], cq.Vector(x, -y, h), cq.Vector(0, 0, sign))
    return head.fuse(axial(x, y, h, 1, length+allowance, sign))


def seat(shape, x, y, face_H, sign, depth):
    shape = shape.cut(axial(x, y, face_H-sign*.1, 1.1, depth+.2, sign))
    return shape.cut(cq.Solid.makeCone(2.45, 1.1, 1.35, cq.Vector(x, -y, face_H), cq.Vector(0, 0, sign)))


def row(name, shape, moving, **extra):
    assert shape.isValid() and len(shape.Solids()) == 1, name
    return {'name': name, 'shape': shape, 'moving': moving, 'color': (.17, .51, .65),
            'display_grip': True, **extra}


def liners(x, moving):
    c = config(); length = c['grip_length_mm']; start = x-length/2
    def tube(radius, l, at, direction=1):
        return cq.Solid.makeCylinder(radius, l, cq.Vector(at, 15, 19.3), cq.Vector(direction, 0, 0))
    sleeve = tube(c['liner_outside_diameter_mm']/2, length, start)
    sleeve = sleeve.cut(tube(c['liner_inside_diameter_mm']/2, length+.2, start-.1))
    for at, sign in [(start, 1), (start+length, -1)]:
        tool = cq.Solid.makeCone(c['liner_end_mouth_diameter_mm']/2, c['liner_inside_diameter_mm']/2,
                                c['liner_end_relief_length_mm'], cq.Vector(at, 15, 19.3), cq.Vector(sign, 0, 0))
        sleeve = sleeve.cut(tool)
    role = 'lid' if moving else 'base'
    return [row(f'display-{role}-liner-{label}', sleeve.intersect(box(start-.1, -20, h, length+.2, 10, 4)),
                moving, grip_liner=role, liner_half=label, color=(.26, .28, .3))
            for label, h in [('lower', 15.3), ('upper', 19.3)]]


def anchor(x, moving):
    c = config(); bore = cq.Solid.makeCylinder(c['liner_outside_diameter_mm']/2, 12.2,
                                              cq.Vector(x-6.1, 15, 19.3), cq.Vector(1, 0, 0))
    if moving:
        saddle = box(x-6, -17.5, 19.3, 12, 12, 2.6).cut(bore)
        saddle = saddle.fuse(box(x-6, -11.5, 21.9, 12, 6, 5.9), box(x-9, -12, 27.8, 18, 12, 1.5),
                             box(x-9, -5.5, 25.3, 18, 5.5, 2.5))
        cap = box(x-6, -17.5, 16.4, 12, 12, 2.9).cut(bore)
        face = 16.4; sign = 1
    else:
        saddle = box(x-6, -17.5, 16.7, 12, 12, 2.6).cut(bore)
        saddle = saddle.fuse(box(x-6, -11.5, 9.2, 12, 6, 7.5), box(x-12, -13.5, 6.2, 24, 10, 3))
        cap = box(x-6, -17.5, 19.3, 12, 12, 2.9).cut(bore)
        face = 22.2; sign = -1
    rear = box(x-14, -30, 0, 28, 13.5, 35)
    saddle = saddle.cut(rear); cap = cap.cut(rear)
    hardware = []; role = 'lid' if moving else 'base'
    for i, xx in enumerate([x-3, x+3]):
        cap = seat(cap, xx, -8.5, face, sign, 2.9)
        saddle = saddle.cut(axial(xx, -8.5, 19.3-sign*.1, 1.025, 6, sign))
        hardware.append(row(f'display-{role}-cap-screw-{i}', countersunk(xx, -8.5, face, 8, sign), moving,
                            fastener=True, fastener_kind='cap', driver_origin_xyH=[xx, -8.5, face],
                            driver_sign=-sign, color=(.46, .48, .5)))
    for i, xx in enumerate([x-5, x+5] if moving else [x-8.5, x+8.5]):
        yy = -2.8 if moving else -8.5
        if moving:
            saddle = saddle.cut(cylinder(xx, yy, 25.2, 1.025, 4.2)); top = 32.3; length = 6
        else:
            saddle = seat(saddle, xx, yy, 9.2, -1, 3); top = 9.2; length = 6
        hardware.append(row(f'display-{role}-mount-screw-{i}', countersunk(xx, yy, top, length, -1), moving,
                            fastener=True, fastener_kind='mount', driver_origin_xyH=[xx, yy, top],
                            driver_sign=1, color=(.46, .48, .5)))
    if not moving:
        saddle = saddle.cut(cylinder(239, -3.5, 6.1, 3.3, 3.2))
    return [row(f'display-{role}-anchor-saddle', saddle, moving, grip_role=role),
            row(f'display-{role}-anchor-cap', cap, moving, grip_role=role, removable_cap=True, color=(.33, .68, .77))]+hardware+liners(x, moving)


def guard():
    c = config(); parts = []
    panel = box(174, -18, 14, 70, .85, 9.1)
    panel = panel.fuse(box(174, -18, 14, 70, 17.5, 1.2))
    # Keep the fixed jaw's pedestal independent of the removable cover.
    panel = panel.cut(box(218.5, -12, 13.9, 13, 11.6, 1.4))
    panel = cq.Workplane(obj=panel).edges("|X").fillet(.2).val()
    for i, (x, y) in enumerate(c['guard_mounts_XY_mm']):
        panel = panel.cut(cylinder(x, y, 13.9, 1.1, 1.4))
        washer = cylinder(x, y, 15.2, 2.25, .3).cut(cylinder(x, y, 15.1, 1.1, .5))
        screw = cylinder(x, y, 9.26, 1, 6.24).fuse(cylinder(x, y, 15.5, 1.9, 2.1))
        parts += [row(f'display-guard-washer-{i}', washer, False, color=(.5, .52, .54)),
                  row(f'display-guard-screw-{i}', screw, False, fastener=True, fastener_kind='guard',
                      driver_origin_xyH=[x, y, 17.6], driver_sign=1, color=(.46, .48, .5))]
    return [row('display-rear-guard', panel, False, removable_guard=True, color=(.45, .51, .56))]+parts


def adapt_case(parts):
    c = config(); result = []; records = []
    for p in parts:
        s = p['shape']; before = s.Volume()
        if p['name'] == 'rear-base-reinforcement':
            for x in [c['fixed_X_mm']-8.5, c['fixed_X_mm']+8.5]:
                s = s.fuse(cylinder(x, -8.5, 4.2, 3.3, 2))
                s = s.cut(cylinder(x, -8.5, 1.1, 1.025, 5.2))
            for x, y in c['guard_mounts_XY_mm']:
                s = s.fuse(cylinder(x, y, 4.2, 3, 9.8))
                s = s.cut(cylinder(x, y, 8.9, 1.025, 5.2))
        elif p['name'] == 'rear-lid-backing-member':
            for x in [c['lid_X_mm']-5, c['lid_X_mm']+5]:
                s = seat(s, x, -2.8, 32.3, -1, 3)
        elif p['name'] == 'base-walls':
            s = s.cut(box(173.8, -18.1, 13.8, 70.4, 1.6, 10.2))
        else:
            result.append(p); continue
        assert s.isValid() and s.Solids(), p['name']
        records.append({'part': p['name'], 'volume_before_mm3': round(before, 4), 'volume_after_mm3': round(s.Volume(), 4)})
        result.append({**p, 'shape': s})
    return result, records


def nominal_gauge(x):
    return cq.Solid.makeCylinder(config()['maximum_bundle_diameter_mm']/2, 12,
                                cq.Vector(x-6, 15, 19.3), cq.Vector(1, 0, 0))


def allocated_liner_overlap(a, b):
    liner, cable = (a, b) if a.get('grip_liner') else (b, a)
    role = liner.get('grip_liner')
    if not role:
        return False
    allowed = {'base': ['display-base-bundle-space', 'display-axis-flex-space'],
               'lid': ['display-lid-tail-space', 'display-axis-flex-space']}
    return cable['name'] in allowed[role]


def driver(part):
    c = config(); x, y, h = part['driver_origin_xyH']; sign = part['driver_sign']
    shaft = axial(x, y, h+sign*.01, c['driver_shaft_diameter_mm']/2, c['driver_shaft_length_mm'], sign)
    handle = axial(x, y, h+sign*c['driver_shaft_length_mm'], c['driver_handle_diameter_mm']/2,
                   c['driver_handle_length_mm'], sign)
    return {'name': part['name']+'-driver', 'shape': shaft.fuse(handle), 'moving': part['moving'], 'color': (.9, .6, .2, .35)}

"""A stepped contact plate and two full-length pipes for the right-side cooler."""
import json
import hashlib
import math
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
from shapely.geometry import LineString

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'mechanical/case-prototype'
sys.path.insert(0, str(BASE))
from cad import box, cylinder, compound
from cooling import spreader
_PLANS = {}


def config():
    return json.loads((HERE / 'cooler.json').read_text())


def pipe_path(spec, offset, length=None):
    """Two tangent quarter circles, with equal total length for both lanes."""
    radius = spec['centerline_radius_mm']
    hot = spec['hot_center_x']
    cold = spec['cold_center_x']
    start = spec['hot_start_y']
    turn = spec['first_tangent_y']
    r1, r2 = radius - offset, radius + offset
    mid = cold - hot - 2 * radius
    assert mid > 0 and start < turn and min(r1, r2) > 0
    count = math.ceil(max(r1, r2) * math.pi / 2 / .15) + 1
    points = [(hot + offset, start), (hot + offset, turn)]
    for a in np.linspace(math.pi, math.pi / 2, count)[1:]:
        points.append((hot + radius + r1 * math.cos(a), turn + r1 * math.sin(a)))
    points.append((cold - radius, turn + radius - offset))
    for a in np.linspace(-math.pi / 2, 0, count)[1:]:
        points.append((cold - radius + r2 * math.cos(a), turn + 2 * radius + r2 * math.sin(a)))
    used = turn - start + (r1 + r2) * math.pi / 2 + mid
    stock = spec['stock_length_mm'] if length is None else length
    tail = stock - used
    assert tail > 0, 'the uncut stock pipe cannot reach the condenser'
    points.append((cold + offset, turn + 2 * radius + tail))
    return points, {'analytic_length_mm': stock, 'bend_radii_mm': [r1, r2],
                    'cold_straight_mm': tail, 'cold_end_xy_mm': points[-1],
                    'sampled_length_mm': LineString(points).length}


def pipe_plan(spec, offset, envelope=False):
    length = spec['stock_length_mm'] + (spec['length_tolerance_mm'] if envelope else 0)
    points, _ = pipe_path(spec, offset, length)
    width = spec['width_mm']
    if envelope:
        width += spec['width_tolerance_mm'] + 2 * spec['position_allowance_mm']
        points[0] = (points[0][0], points[0][1] - spec['position_allowance_mm'])
        points[-1] = (points[-1][0], points[-1][1] + spec['position_allowance_mm'])
    return LineString(points).buffer(width / 2, cap_style='flat', join_style='round', quad_segs=32)


def pipe_solid(spec, offset, envelope=False, upper_clearance=False):
    bottom = spec['bottom_H']
    height = spec['height_mm']
    if envelope:
        bottom -= spec['vertical_position_allowance_mm']
        height += spec['height_tolerance_mm'] + 2 * spec['vertical_position_allowance_mm']
    if upper_clearance:
        height += spec['clearance_above_maximum_mm']
    length=spec['stock_length_mm']+(spec['length_tolerance_mm'] if envelope else 0)
    _,data=pipe_path(spec,offset,length)
    width=spec['width_mm']+(spec['width_tolerance_mm']+2*spec['position_allowance_mm'] if envelope else 0)
    half=width/2;radius=spec['centerline_radius_mm'];hot=spec['hot_center_x'];cold=spec['cold_center_x']
    turn=spec['first_tangent_y'];start=spec['hot_start_y'];end=data['cold_end_xy_mm'][1]
    if envelope:start-=spec['position_allowance_mm'];end+=spec['position_allowance_mm']
    r1,r2=radius-offset,radius+offset;c1=hot+radius;c2=cold-radius;cy2=turn+2*radius;k=math.sqrt(.5)
    # Four exact arcs keep the sweep tangent without hundreds of tiny faces.
    s=cq.Workplane('XY').moveTo(hot+offset-half,-start).lineTo(hot+offset-half,-turn)
    s=s.threePointArc((c1-(r1+half)*k,-turn-(r1+half)*k),(c1,-turn-r1-half))
    s=s.lineTo(c2,-cy2+r2-half).threePointArc((c2+(r2-half)*k,-cy2+(r2-half)*k),(cold+offset-half,-cy2))
    s=s.lineTo(cold+offset-half,-end).lineTo(cold+offset+half,-end).lineTo(cold+offset+half,-cy2)
    s=s.threePointArc((c2+(r2+half)*k,-cy2+(r2+half)*k),(c2,-cy2+r2+half)).lineTo(c1,-turn-r1+half)
    s=s.threePointArc((c1-(r1-half)*k,-turn-(r1-half)*k),(hot+offset+half,-turn))
    s=s.lineTo(hot+offset+half,-start).close().extrude(height).val().translate((0,0,bottom))
    assert s.isValid() and len(s.Solids())==1
    return s


def register_shapes(parts):
    spec = config()['pipes']
    for part in parts:
        if 'remote_pipe_offset' not in part:continue
        s=part['shape'];poly=pipe_plan(spec,part['remote_pipe_offset'],part['remote_pipe_envelope'])
        # This is the exact extrusion plan with a small outward numeric margin.
        assert abs(s.Volume()-poly.area*s.BoundingBox().zlen)<.05
        _PLANS[id(s)]=(s,poly.buffer(.002))


def planar_bound(shape):
    saved=_PLANS.get(id(shape))
    return saved[1] if saved and saved[0] is shape else None


def fan_model(c):
    record=json.loads((HERE/'reference/delta-fan-source.json').read_text())
    path=HERE/'reference'/record['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
    s=cq.importers.importStep(str(path)).val()
    assert s.isValid()
    x,y=c['fan']['xy']
    s=s.rotate((0,0,0),(1,0,0),90).translate((x+22.5,-y-22.5,c['fan']['bottom_H']))
    if c['fan'].get('inlet_direction')=='down':
        pivot=(x+22.5,-y-22.5,c['fan']['bottom_H']+c['fan']['body_mm'][2]/2)
        s=s.rotate(pivot,(pivot[0],pivot[1]+1,pivot[2]),180)
    return s


def carrier_reliefs(carrier):
    spec=config()['pipes']
    for offset in spec['lane_offsets_mm']:
        carrier=carrier.cut(pipe_solid(spec,offset,envelope=True,upper_clearance=True))
    return carrier


def make_parts(case, fan_shape=None):
    c = config(); fan = c['fan']; pipe = c['pipes']; fin = c['fins']
    parts = []
    def add(name, shape, color, group='cooling', **extra):
        assert shape.isValid(), name
        parts.append(dict(name=name, shape=shape, group=group, moving=False, color=color, remote_cooler=True, **extra))
    x, y = fan['xy']; h = fan['bottom_H']; w, d, t = fan['body_mm']
    nominal_fan = fan_model(c) if fan_shape is None else fan_shape
    add('delta-blower', nominal_fan, (.22, .24, .26))
    allowance = fan['position_allowance_mm']
    mw, md, mt = fan['maximum_body_mm']
    lower=fan.get('bottom_tolerance_H',[h-allowance,h+allowance])[0]
    upper=fan.get('bottom_tolerance_H',[h-allowance,h+allowance])[1]+mt
    maximum_fan = box(x-(mw-w)/2-allowance, y-(md-d)/2-allowance, lower,
                      mw+2*allowance, md+2*allowance, upper-lower)
    add('blower-size-and-position-allowance', maximum_fan, (.8,.4,.2,.22), 'keepout')
    if fan.get('inlet_direction')=='down':
        import cooler_hardware
        hardware=cooler_hardware.config();a=hardware['intake'];ix,iy=a['centre_xy']
        inlet=cylinder(ix,iy,a['cross_rib_top_H'],fan['inlet_radius_mm'],lower-a['cross_rib_top_H'])
    else:
        inlet = box(x-.45, y-.45, h+mt+allowance, mw+.4, md+.4, fan['upper_inlet_space_mm'])
    add('blower-inlet-space', inlet, (.3,.6,.9,.2), 'keepout')
    datums = json.loads((BASE / 'cooling-datums.json').read_text())
    plate = spreader({'spreader_thickness_mm': c['plate']['thickness_mm']}, case['boards']['main_bottom_H']+1.6)
    slots = []
    for i, offset in enumerate(pipe['lane_offsets_mm'], 1):
        nominal = pipe_solid(pipe, offset)
        limit = pipe_solid(pipe, offset, envelope=True)
        clearance = pipe_solid(pipe, offset, envelope=True, upper_clearance=True)
        add(f'heatpipe-{i}', nominal, (.76,.45,.24), remote_pipe_offset=offset, remote_pipe_envelope=False)
        add(f'heatpipe-{i}-size-and-position-allowance', limit, (.8,.45,.2,.22), 'keepout', remote_pipe_offset=offset, remote_pipe_envelope=True)
        add(f'heatpipe-{i}-upper-clearance', clearance, (.8,.45,.2,.15), 'keepout', remote_pipe_offset=offset, remote_pipe_envelope=True)
        bb = limit.BoundingBox()
        # Extend the slot down to its stated floor. The 0.7 mm remaining web
        # and the CPU clamp still need stiffness/load checks before machining.
        slot = limit.translate((0,0,c['plate']['groove_floor_H']-bb.zmin))
        slots.append(slot)
        plate = plate.cut(slot)
    add('stepped-copper-plate', plate, (.68,.39,.22))
    fx, fy, fw, fd = fin['xywh']
    pitch = (fd-fin['thickness_mm'])/(fin['count']-1)
    fins = []
    for i in range(fin['count']):
        s = box(fx, fy+i*pitch, fin['bottom_H'], fw, fin['thickness_mm'], fin['top_H']-fin['bottom_H'])
        for offset in pipe['lane_offsets_mm']:
            # Every fin lies on the straight condenser leg. A rectangular
            # slot avoids repeating a whole curved-pipe Boolean for each fin.
            _, route = pipe_path(pipe, offset, pipe['stock_length_mm']+pipe['length_tolerance_mm'])
            low_y = pipe['first_tangent_y']+2*pipe['centerline_radius_mm']
            high_y = route['cold_end_xy_mm'][1]+pipe['position_allowance_mm']
            width = pipe['width_mm']+pipe['width_tolerance_mm']+2*pipe['position_allowance_mm']
            bottom = pipe['bottom_H']-pipe['vertical_position_allowance_mm']
            height = pipe['height_mm']+pipe['height_tolerance_mm']+2*pipe['vertical_position_allowance_mm']
            s = s.cut(box(pipe['cold_center_x']+offset-width/2,low_y,bottom,width,high_y-low_y,height))
        assert s.isValid()
        fins.append(s)
    # A continuous collector connects the fins beyond the pipe end, including
    # the shorter stock-length limit. Every fin has a conductive path.
    collector=box(fx,fy,c['plate']['groove_floor_H']-1,fw,fd,1)
    stack=compound(fins).fuse(collector)
    if c.get('hardware_enabled'):
        import cooler_hardware
        stack=cooler_hardware.fin_retention(stack,fin)
        for offset in pipe['lane_offsets_mm']:
            stack=stack.cut(pipe_solid(pipe,offset,envelope=True))
    assert stack.isValid() and len(stack.Solids())==1, 'fin stack needs one connected collector'
    add('slotted-copper-fin-stack', stack, (.67,.40,.23))
    # The stock cooler provides the three-point pattern, but the spring
    # rate, travel stops and package-load limit are not publicly specified.
    for i,(mx,my) in enumerate(datums['cooler_mount_centers_xy_mm'], 1):
        add(f'CPU-mount-{i}-space', cylinder(mx,my,15.737,3.25,3.5), (.3,.5,.8,.25), 'keepout')
    if c.get('hardware_enabled'):
        parts.extend(cooler_hardware.parts(case,fan,fin,pipe,fin_shape=stack,
                     pipe_shapes=[p['shape'] for p in parts if p['name'] in ['heatpipe-1','heatpipe-2']]))
    register_shapes(parts)
    return parts

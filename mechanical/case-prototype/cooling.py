"""Stepped Mu Ultra contact study and a rearward heatpipe corridor."""
import json
import math
import cadquery as cq
from cad import HERE,box,cylinder,compound


def spreader(config,board_top):
    data=json.loads((HERE/'cooling-datums.json').read_text())
    from build import INVENTORY
    if INVENTORY['center']['sha256'] != data['center_PCB_sha256']:
        raise ValueError('review the Mu cooling datums after changing the center PCB')
    x,y,w,d=data['spreader_xy_mm'];low=board_top+data['spreader_underface_above_board_mm']
    thickness=config['spreader_thickness_mm']
    plate=box(x,y,low,w,d,thickness)
    cx,cy,cw,cd=data['CPU_contact_xy_mm'];cpu=board_top+data['CPU_contact_above_board_mm']
    plate=plate.fuse(box(cx,cy,cpu,cw,cd,low-cpu+.05))
    memory=board_top+data['memory_contact_above_board_mm']
    for mx,my,mw,md in data['memory_regions_xy_mm']:
        plate=plate.fuse(box(mx,my,memory,mw,md,low-memory+.05))
    # Clearance holes identify the existing three-point pattern. No spring
    # preload or screw engagement is inferred from the source model.
    for mx,my in data['cooler_mount_centers_xy_mm']:
        plate=plate.cut(cylinder(mx,my,low-.1,1.1,thickness+.2))
    if not plate.isValid() or len(plate.Solids())!=1:
        raise ValueError('spreader study must be one valid solid')
    return plate


def heatpipe(config):
    """Flat section following a tangent path around, rather than across, the fan."""
    bottom=config['heatpipe'][2];width=config.get('heatpipe_width_mm',config['heatpipe'][4]);thickness=config['heatpipe'][5]
    radius=config['heatpipe_turn_radius_mm']
    # Two 90-degree, tangent bends in the plane. The specified radius and
    # cross section need the chosen heatpipe supplier's capacity/bend review.
    start_x,start_y=config.get('heatpipe_bend_start_xy',[147.,49.])
    points=[(212.,start_y),(start_x,start_y)]
    for i in range(1,25):
        a=math.pi/2+math.pi/2*i/24
        points.append((start_x+radius*math.cos(a),start_y-radius+radius*math.sin(a)))
    second_y=config.get('heatpipe_end_y_mm',13.)+radius
    if second_y>start_y-radius+1e-6:
        raise ValueError('heatpipe bends need more longitudinal space')
    if second_y<start_y-radius-1e-6:points.append((start_x-radius,second_y))
    for i in range(1,25):
        a=-math.pi/2*i/24
        points.append((start_x-2*radius+radius*math.cos(a),second_y+radius*math.sin(a)))
    points.append((config.get('heatpipe_end_x_mm',105.),second_y-radius))
    # Planar union gives a continuous flat route and a conservative bend
    # envelope; it is a fit volume, not a heat-transfer simulation.
    from shapely.geometry import LineString
    polygon=LineString(points).buffer(width/2,join_style='round')
    return cq.Workplane('XY').polyline([(x,-y) for x,y in polygon.exterior.coords]).close().extrude(thickness).val().translate((0,0,bottom))

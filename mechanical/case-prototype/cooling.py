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


def heatpipe_path(config, length=None):
    """Two tangent turns joined by a straight, retaining the sealed pipe length."""
    radius=config['heatpipe_turn_radius_mm']
    angle=math.radians(config.get('heatpipe_turn_angle_deg',90))
    if not 0 < angle <= math.pi/2:
        raise ValueError('heatpipe turns must be between zero and 90 degrees')
    sx,sy=config.get('heatpipe_hot_end_xy',[212.,config.get('heatpipe_bend_start_xy',[190.,49.])[1]])
    bx,by=config.get('heatpipe_bend_start_xy',[190.,49.])
    end_y=config.get('heatpipe_end_y_mm',13.)
    if abs(sy-by)>1e-8 or sx<bx:
        raise ValueError('hot end and first tangent must form a westward straight')
    straight=(sy-end_y-2*radius*(1-math.cos(angle)))/math.sin(angle)
    if straight < -1e-8:
        raise ValueError('heatpipe bends need more longitudinal space')
    straight=max(0.,straight)
    points=[(sx,sy),(bx,by)]
    for i in range(1,49):
        a=math.pi/2+angle*i/48
        points.append((bx+radius*math.cos(a),by-radius+radius*math.sin(a)))
    x,y=points[-1]
    points.append((x-straight*math.cos(angle),y-straight*math.sin(angle)))
    x,y=points[-1];cx=x-radius*math.sin(angle);cy=y+radius*math.cos(angle)
    for i in range(1,49):
        a=-math.pi/2+angle-angle*i/48
        points.append((cx+radius*math.cos(a),cy+radius*math.sin(a)))
    used=sx-bx+2*radius*angle+straight
    length=config.get('heatpipe_nominal_length_mm') if length is None else length
    if length is None:
        length=used+points[-1][0]-config.get('heatpipe_end_x_mm',59.)
    last=length-used
    if last<=0:
        raise ValueError('stock heatpipe is too short for the specified bends')
    points.append((points[-1][0]-last,end_y))
    return points,{'length_mm':length,'radius_mm':radius,
                   'bend_angle_deg':math.degrees(angle),'middle_straight_mm':straight,
                   'hot_straight_mm':sx-bx,'cold_straight_mm':last,'cold_end_xy_mm':points[-1]}


def heatpipe(config, tolerance=False):
    """Flat-pipe fit volume; nominal shape and tolerance envelope stay separate."""
    bottom=config['heatpipe'][2];width=config.get('heatpipe_width_mm',config['heatpipe'][4]);thickness=config['heatpipe'][5]
    length=config.get('heatpipe_nominal_length_mm')
    if tolerance:
        width+=config.get('heatpipe_width_tolerance_mm',0)+2*config.get('heatpipe_position_allowance_mm',0)
        thickness+=config.get('heatpipe_height_tolerance_mm',0)+config.get('heatpipe_upper_clearance_mm',0)
        if length is not None:length+=config.get('heatpipe_length_tolerance_mm',0)
    points,_=heatpipe_path(config,length)
    if tolerance:
        margin=config.get('heatpipe_position_allowance_mm',0)
        points[0]=(points[0][0]+margin,points[0][1])
        points[-1]=(points[-1][0]-margin,points[-1][1])
    from shapely.geometry import LineString
    # Square end planes retain the stated stock length. The extra end space
    # belongs to the tolerance envelope, not to a fictitious pipe extension.
    polygon=LineString(points).buffer(width/2,join_style='round',cap_style='flat')
    return cq.Workplane('XY').polyline([(x,-y) for x,y in polygon.exterior.coords]).close().extrude(thickness).val().translate((0,0,bottom))

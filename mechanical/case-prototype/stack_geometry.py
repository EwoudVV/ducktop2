"""Local cable and guide heights beneath the trackpad support."""
import numpy as np
from shapely import distance, points
from shapely.geometry import box
from component_heights import guide_samples, guided_points


def trackpad_cable_ceiling(config, harness):
    t=config['trackpad'];c=config['cables']
    region=box(t['x']-6,t['y']-5,t['x']+t['width']+6,t['y']+t['depth']+5)
    sampling={'wire_position_allowance_mm':.2,'guide_curve_allowance_mm':.025,
              'sampling_step_mm':.05}
    rows=[]
    for route in harness['routes']:
        xyz,radius=guide_samples(route,c,sampling,include_guide=False)
        d=distance(points(xyz[:,:2]),region);near=d<=radius
        if near.any():
            top=float((xyz[near,2]+np.sqrt(np.maximum(0,radius**2-d[near]**2))).max())
            rows.append({'wire':route['name'],'surface':'wire','top_height_mm':top})
        guide_route={**route,'points':guided_points(route,c)}
        xyz,radius=guide_samples(guide_route,c,sampling)
        d=distance(points(xyz[:,:2]),region);near=d<=radius
        if near.any():
            # The guide is open between 45 and 135 degrees. Its upper lips
            # reach at most R/sqrt(2) above the centreline. The local vertical
            # component of the profile basis is <=1, including sloping runs.
            outer=route['wire_od_mm']/2+c['guide_radial_clearance']+c['guide_wall']
            allowance=radius-outer
            top=float(xyz[near,2].max()+outer/np.sqrt(2)+allowance)
            rows.append({'wire':route['name'],'surface':'open_guide','top_height_mm':top})
    return {'trackpad_support_xy_mm':list(region.bounds),'crossings':rows,
            'limiting_crossing':max(rows,key=lambda row:row['top_height_mm']) if rows else None,
            'position_allowance_mm':.2,'curve_allowance_mm':.025,
            'sampling_step_mm':.05,
            'scope':'power wires and open guides beneath the support; full carriers, fasteners, parts and signal cables require separate solid checks'}


def stack_limits(config,harness):
    local=trackpad_cable_ceiling(config,harness)
    t=config['trackpad'];fan=config['cooling']['blower'];b=config['base']
    offset=b['deck_top']-config['boards']['keyboard']['bottom_height']
    bridge_drop=t['thickness']+t['click_travel']+t['under_clearance']+2.5
    ceiling=local['limiting_crossing']['top_height_mm']
    pipe=config['cooling']['heatpipe']
    limits={'power_wires_and_guides_under_trackpad':ceiling+.5+bridge_drop,
            'blower_intake_under_keyboard':fan[2]+fan[5]+config['cooling'].get('blower_height_tolerance',.3)+config['cooling'].get('intake_plenum',3)+offset,
            'heatpipe_under_carrier':pipe[2]+pipe[5]+.5+4.5+offset}
    return limits,local

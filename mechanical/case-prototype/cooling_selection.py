"""Bind the cooler fit model to the selected catalogue part and its limits."""
import json
import math
from cad import HERE,cylinder
from cooling import heatpipe,heatpipe_path


def verify_pipe_config(config,parts):
    source=parts['heatpipe']
    if config['heatpipe_part']!=source['part']:
        raise ValueError('heatpipe identity differs from the part selection')
    for field in ['length','width','height','length_tolerance','width_tolerance','height_tolerance']:
        key='heatpipe_'+field+'_mm'
        value=config['heatpipe'][5] if field=='height' else config['heatpipe_nominal_length_mm'] if field=='length' else config[key]
        if abs(value-source[field+'_mm'])>1e-8:
            raise ValueError('heatpipe '+field+' differs from the catalogue input')
    inside=config['heatpipe_turn_radius_mm']-(source['width_mm']+source['width_tolerance_mm'])/2
    if inside<source['catalogue_bend_radius_for_7mm_mm']:
        raise ValueError('heatpipe inside radius is below the reserved bend limit')
    return inside


def check(config):
    from shapely.geometry import LineString,box as planar_box
    parts=json.loads((HERE/'cooling-parts.json').read_text())
    c=config['cooling'];inside=verify_pipe_config(c,parts)
    points,data=heatpipe_path(c)
    # Leff is a catalogue comparison using idealized contact spans. Actual
    # seals, discrete fin joints, bends and working angle need supplier data.
    path=LineString(points);plate=json.loads((HERE/'cooling-datums.json').read_text())
    x,y,w,d=plate['spreader_xy_mm'];hot=path.intersection(planar_box(x,y,x+w,y+d)).length
    x,y,_,w,d,_=c['fins'];cold=path.intersection(planar_box(x,y,x+w,y+d)).length
    effective=data['length_mm']-(hot+cold)/2
    envelope=heatpipe(c,tolerance=True);mount=parts['processor_mount'];clashes=[]
    for i,(x,y) in enumerate(plate['cooler_mount_centers_xy_mm'],1):
        reserved=cylinder(x,y,mount['hardware_envelope_bottom_H_mm'],mount['hardware_envelope_radius_mm'],
                          mount['hardware_envelope_top_H_mm']-mount['hardware_envelope_bottom_H_mm'])
        overlap=envelope.intersect(reserved).Volume()
        if overlap>.001:clashes.append({'mount':i,'overlap_mm3':round(overlap,4)})
    return {'part':parts['heatpipe']['part'],**data,
            'sampled_centerline_length_mm':round(path.length,6),
            'minimum_inside_radius_at_maximum_width_mm':inside,
            'maximum_envelope_width_mm':c['heatpipe_width_mm']+c['heatpipe_width_tolerance_mm']+2*c['heatpipe_position_allowance_mm'],
            'maximum_envelope_height_mm':c['heatpipe'][5]+c['heatpipe_height_tolerance_mm']+c['heatpipe_upper_clearance_mm'],
            'condenser_end_extension_for_length_tolerance_mm':c['heatpipe_length_tolerance_mm'],
            'ideal_hot_region_overlap_mm':round(hot,4),'ideal_cold_region_overlap_mm':round(cold,4),
            'ideal_effective_length_mm':round(effective,4),
            'straight_catalogue_comparison_W':round(parts['heatpipe']['catalogue_Qt_W_m']*1000/effective,2),
            'capacity_scope':'catalogue comparison only; continuous contact spans are assumed. Forming, orientation, actual bond area, sealed ends, temperature and fin/airflow losses are not qualified.',
            'pipe_mount_envelope_conflicts':clashes,
            'mount_scope':'three 6.5 mm diameter upper reservations, not selected fasteners or complete access paths',
            'formed_pipe_capacity_verified':False,'module_clamp_load_verified':False}

"""Component limits and explicitly chosen assembly space for the case."""
import math

import numpy as np
from shapely import distance, points
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def resolve(part, settings):
    key = part['board'] + '/' + part['reference']
    reservation = settings['reservations'].get(key)
    if reservation is not None:
        for field in ['mpn', 'footprint']:
            if part.get(field) != reservation[field]:
                raise ValueError(key + ': assembly reservation belongs to a different ' + field)
        height = reservation['height_mm']
        if part['height_kind'] == 'maximum' and height < part['height_mm']:
            raise ValueError(key + ': reservation is below the manufacturer maximum')
        return {'height_mm': height, 'basis': 'assembly_reservation',
                'physical_fit_verified': False, 'note': reservation['basis'],
                'source': reservation['source']}
    if part['height_kind'] != 'maximum':
        return None
    allowance = max(part.get('planning_allowance_mm') or 0,
                    settings['manufacturer_assembly_allowance_mm'])
    return {'height_mm': part['height_mm'] + allowance,
            'manufacturer_maximum_mm': part['height_mm'],
            'assembly_allowance_mm': allowance, 'basis': 'manufacturer_maximum',
            'source': part['height_source_url'], 'note': part['height_basis']}


def guided_points(route, config):
    xyz = np.asarray(route['points'], dtype=float)
    lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))]
    trim = 6 if route.get('group') == 'usb5' else 3
    end_trim = config.get('guide_end_trim_by_route_mm', {}).get(route['name'], trim)
    result = xyz[(lengths >= trim) & (lengths <= lengths[-1] - end_trim)]
    if len(result) < 3:
        raise ValueError(route['name'] + ': guide trimmed below three source stations')
    return result


def guide_samples(route, config, settings, include_guide=True):
    """Cover a round swept guide by overlapping, conservatively enlarged balls.

    Including every original vertex preserves the source polyline. Half the
    maximum sample spacing expands the balls enough to cover the intervals;
    the separate curve allowance covers the fitted CAD spline deviation.
    """
    xyz = np.asarray(route['points'], dtype=float)
    lengths = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    samples = []
    maximum_step = 0.0
    for start, end, length in zip(xyz[:-1], xyz[1:], lengths):
        count = max(1, math.ceil(length / settings['sampling_step_mm']))
        maximum_step = max(maximum_step, length / count)
        fractions = np.arange(count) / count
        samples.append(start + fractions[:, None] * (end - start))
    sample_xyz = np.vstack(samples + [xyz[-1:]])
    guide_radius = config['guide_radial_clearance'] + config['guide_wall'] if include_guide else 0
    radius = (route['wire_od_mm'] / 2 + guide_radius + settings['wire_position_allowance_mm']
              + settings['guide_curve_allowance_mm'] + maximum_step / 2)
    return sample_xyz, radius


def height_limit(samples, radius, area, board_top):
    """Lowest covered guide surface above a component's conservative XY area."""
    separation = distance(points(samples[:, :2]), area)
    near = separation <= radius
    if not near.any():
        return None
    bottom = samples[near, 2] - np.sqrt(np.maximum(0, radius**2 - separation[near]**2))
    return float(bottom.min() - board_top)


def screen_routes(routes, parts, board_tops, config, settings):
    crossings, unknown, conflicts = [], [], []
    front = []
    for part in parts:
        if part['side'] != 'front' or part['dnp']:
            continue
        rings = part['courtyards_installed_mm']['front']
        if rings:
            front.append((part, unary_union([Polygon(r['outer'], r['holes']) for r in rings])))
    for route in routes:
        wire_samples, wire_radius = guide_samples(route, config, settings, include_guide=False)
        guide_route = {**route, 'points': guided_points(route, config)}
        samples, radius = guide_samples(guide_route, config, settings)
        line = LineString(route['points']).buffer(radius)
        for part, area in front:
            if any(e['board'] == part['board'] and e['ref'] == part['reference'] for e in route['ends']):
                continue
            if not line.intersects(area):
                continue
            limits = [('wire', height_limit(wire_samples, wire_radius, area, board_tops[part['board']])),
                      ('guide', height_limit(samples, radius, area, board_tops[part['board']]))]
            limits = [(surface, value) for surface, value in limits if value is not None]
            if not limits:
                continue
            surface, allowed = min(limits, key=lambda row: row[1])
            record = {'wire': route['name'], 'part': part['board'] + '/' + part['reference'],
                      'maximum_component_height_below_guide_mm': round(allowed, 4),
                      'limiting_surface': surface,
                      'courtyard_screen_not_exact_body': True}
            limit = resolve(part, settings)
            if limit is None:
                unknown.append({**record, 'height_status': part['height_status']})
                continue
            gap = allowed - limit['height_mm']
            record.update(limit, planning_gap_mm=round(gap, 4))
            crossings.append(record)
            if gap < 0:
                conflicts.append(record)
    return {'component_height_crossings': crossings,
            'unverified_height_limits': unknown,
            'known_height_clearance_conflicts': conflicts}

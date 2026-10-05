"""Check the filled force paths of the 80 mm BMS before plotting it."""
from collections import defaultdict

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union


# These centre lines belong to the saved Q11/Q12, RS11 and terminal placement.
# Changing that placement requires reviewing the paths as well as the netlist.
PATHS = {
    'PACK_POS_RAW': (2.8, [(174.65, 82), (165.4, 82), (165.4, 85.5), (162.4, 88.5), (157.5, 88.5)]),
    'BAT_PROT_VIN': (3, [(149.5, 88.5), (146, 88.5), (146, 86.2), (143.495, 86.2)]),
    'PACK_POS_FUSED': (3, [(128.905, 88.135), (126, 88.135), (123.75, 85.885), (123.75, 75.8), (125.8, 73.75), (125.8, 63.05)]),
    'PACK_NEG_RAW': (6.25, [(159.375, 69.45), (161, 69.45), (165.4, 73.85), (165.4, 78), (174.65, 78)]),
    'FG_VSS': (3, [(129.8, 63.05), (129.8, 72.3), (129.8, 66), (131.1, 66), (144, 69.45), (151.325, 69.45)]),
    'BAT_PROT_FET_COMMON': (5, [(133.336, 87.5), (139.064, 87.5)]),
}


def check_bulk_path(copper, points, minimum, net):
    """Use only filled pours and force lands; thin bias tracks cannot pass."""
    tolerance = .00005  # native polygon rounding, in mm
    path = LineString(points)
    if not copper.buffer(tolerance).covers(path):
        raise RuntimeError('force path interrupted: ' + net)
    narrowest = float('inf')
    for a, b in zip(points, points[1:]):
        length = Point(a).distance(Point(b))
        dx, dy = (b[0]-a[0])/length, (b[1]-a[1])/length
        count = max(3, int(length/.15)+1)
        for i in range(count):
            fraction = .03 + .94*i/(count-1)
            x, y = a[0]+(b[0]-a[0])*fraction, a[1]+(b[1]-a[1])*fraction
            cut = LineString([(x-dy*20, y+dx*20), (x+dy*20, y-dx*20)]).intersection(copper)
            pieces = [cut] if cut.geom_type == 'LineString' else list(getattr(cut, 'geoms', []))
            width = max((p.length for p in pieces if p.distance(Point(x, y)) < .001), default=0)
            narrowest = min(narrowest, width)
    if narrowest + tolerance < minimum:
        raise RuntimeError(f'force path too narrow: {net}, {narrowest:.6f} mm < {minimum:g} mm')
    return {'minimum_width_mm': minimum, 'sampled_width_mm': narrowest,
            'continuous_front_copper': True}


def check_power_paths(geometry):
    filled, all_copper = defaultdict(list), defaultdict(list)
    for row in geometry['copper']:
        net = row['net'].lstrip('/')
        shape = unary_union([Polygon(p['outer'], p.get('holes', [])) for p in row['polygons']])
        all_copper[(net, row['layer'])].append(shape)
        if row['kind'] in ('zone', 'pad') and row['layer'] == 'F.Cu':
            filled[net].append(shape)
    result = {net: check_bulk_path(unary_union(filled[net]), points, width, net)
              for net, (width, points) in PATHS.items()}
    copper = {key: unary_union(shapes) for key, shapes in all_copper.items()}
    returns = ['PACK_NEG_RAW', 'FG_VSS', 'CTRL_GND', 'PDSG_RTN']
    barrier = box(103.1, 75.9, 104.9, 91.1)
    for layer in geometry['copper_layers']:
        for i, a in enumerate(returns):
            for b in returns[i+1:]:
                if copper.get((a, layer), Polygon()).intersection(copper.get((b, layer), Polygon())).area > 1e-8:
                    raise RuntimeError(f'return domains overlap: {a}, {b}, {layer}')
        if sum(shape.intersection(barrier).area for (_, side), shape in copper.items() if side == layer) > 1e-8:
            raise RuntimeError('isolator barrier contains copper: ' + layer)
    return {'paths': result, 'return_domain_overlap_mm2': 0, 'isolator_barrier_overlap_mm2': 0,
            'current_and_temperature_testing': 'required on the finished board'}

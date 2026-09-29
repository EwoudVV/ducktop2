#!/usr/bin/env python3
"""Export the saved BMS and check the files intended for PCBWay."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'bms/bms.kicad_pcb'
LAYERS = {'F.Cu': 'gtl', 'In1.Cu': 'g1', 'In2.Cu': 'g2', 'B.Cu': 'gbl',
          'F.Mask': 'gts', 'B.Mask': 'gbs', 'F.Silkscreen': 'gto',
          'B.Silkscreen': 'gbo', 'Edge.Cuts': 'gm1'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def electrical_geometry_hash(geometry):
    keys = ('copper', 'drills', 'tracks', 'vias', 'edge_primitives')
    return hashlib.sha256(json.dumps({k: geometry[k] for k in keys},
                         sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def compare_refill_geometry(source, refilled):
    """Check refill rounding without accepting moved copper or changed topology."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    for key in ('tracks', 'vias', 'drills', 'edge_primitives'):
        require(source[key] == refilled[key], 'refill changed ' + key)
    require(len(source['copper']) == len(refilled['copper']), 'refill changed copper population')
    report = {'maximum_boundary_difference_mm': .00005, 'zones': []}
    old_outline = unary_union([Polygon(p['outer'], p['holes']) for p in source['outline']])
    new_outline = unary_union([Polygon(p['outer'], p['holes']) for p in refilled['outline']])
    require(len(source['outline']) == len(refilled['outline']) and
            sorted(len(p['holes']) for p in source['outline']) ==
            sorted(len(p['holes']) for p in refilled['outline']), 'outline topology changed')
    outline_difference = old_outline.boundary.hausdorff_distance(new_outline.boundary)
    require(outline_difference <= .005, 'outline polygon exceeds native curve tolerance')
    report['outline'] = {'edge_primitives_identical': True,
                         'polygon_boundary_difference_mm': outline_difference,
                         'native_curve_tolerance_mm': .005}
    for a, b in zip(source['copper'], refilled['copper']):
        if a == b:
            continue
        require(a['kind'] == b['kind'] == 'zone', 'non-zone copper changed during refill')
        require({k: v for k, v in a.items() if k != 'polygons'} ==
                {k: v for k, v in b.items() if k != 'polygons'}, 'zone identity changed')
        require(len(a['polygons']) == len(b['polygons']) and
                sorted(len(p['holes']) for p in a['polygons']) ==
                sorted(len(p['holes']) for p in b['polygons']), 'zone topology changed')
        old = unary_union([Polygon(p['outer'], p['holes']) for p in a['polygons']])
        new = unary_union([Polygon(p['outer'], p['holes']) for p in b['polygons']])
        distance = old.boundary.hausdorff_distance(new.boundary)
        area = old.symmetric_difference(new).area
        require(distance <= .00005 and area <= .00001,
                'refill changed a zone beyond rounding: ' + a['id'])
        report['zones'].append({'id': a['id'], 'net': a['net'], 'layer': a['layer'],
                               'boundary_difference_mm': distance, 'changed_area_mm2': area})
    return report


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def write_csv(path, columns, rows):
    with Path(path).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def ref_key(ref):
    return ''.join(c for c in ref if not c.isdigit()), int(''.join(c for c in ref if c.isdigit()) or 0)


def source_hashes():
    files = ['bms/bms' + suffix for suffix in ('.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_dru')]
    files += ['gen/generate_bms_pcbway_package.py', 'gen/bms_fabrication_geometry.py',
              'gen/check_release_candidate.py', 'gen/report_schematic_pcb_eco.py',
              'gen/export_bms_assembly.py',
              'gen/requirements-bms-fabrication.txt',
              'manufacturing/bms/front-assembly.svg', 'manufacturing/bms/back-assembly.svg',
              'manufacturing/bms/test-points.csv', 'manufacturing/bms/assembly-source.json',
              'verification/bms-layout.json']
    return {f: digest(ROOT / f) for f in files}


def zip_files(path, entries):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as out:
        for file, name in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, file.read_bytes())


def check_drc(path):
    d = json.loads(Path(path).read_text())
    require(not d['unconnected_items'], 'unconnected pads')
    # Generic Fuse and Conn_01x02 symbols filter library names. The exact
    # project footprints are checked below, and netlist parity is independent.
    require(all(v['severity'] == 'warning' and v['type'] == 'footprint_filters_mismatch'
                and len(v['items']) == 1 and v['items'][0]['description'] in
                ('Footprint F1', 'Footprint J2072') for v in d['schematic_parity']),
            'schematic mismatch; review ' + str(path))
    allowed = {'lib_footprint_mismatch', 'track_not_centered_on_via'}
    require(all(v['severity'] == 'warning' and v['type'] in allowed for v in d['violations']),
            'new DRC finding; review ' + str(path))
    counts = dict(Counter(v['type'] for v in d['violations']))
    require(max(counts.values(), default=0) < 499, 'DRC report may have reached its limit')
    return {'errors': 0, 'unconnected': 0, 'schematic_mismatches': 0, 'warnings': counts,
            'footprint_filter_warnings': d['schematic_parity']}


def assembly_files(out, geometry):
    from report_schematic_pcb_eco import parse_schematic
    components = parse_schematic(ET.parse(out / 'checks/netlist.xml').getroot())
    footprints = {f['ref']: f for f in geometry['footprints']}
    require(len(footprints) == len(components) == 149, 'BMS population changed; review it before export')
    populated = {c['ref']: c for c in components if not c['attributes']}
    require(len(populated) == 125, 'assembly population changed')
    require(all(c['attributes'] == {'exclude_from_bom'} and c['ref'].startswith('TPB')
                for c in components if c['attributes']), 'unexpected DNP or BOM exclusion')
    groups = defaultdict(list)
    for ref, c in populated.items():
        maker, mpn = c['fields'].get('Manufacturer'), c['fields'].get('MPN')
        require(maker and mpn, 'missing manufacturer or MPN: ' + ref)
        if ref == 'F1':
            require(mpn == '3-101-056' and footprints[ref]['attributes'] & 2,
                    'review the Schurter 5 A SMT fuse before export')
        if ref == 'J2':
            require(mpn == '43045-0400', 'review the raw-pack connector before export')
        mount = 'THT' if ref == 'J2' else 'SMT'
        groups[maker, mpn, c['footprint'], mount].append(ref)
    rows = []
    for (maker, mpn, footprint, mount), refs in sorted(groups.items()):
        refs = sorted(refs, key=ref_key)
        description = populated[refs[0]]['value']
        rows.append({'Designator': ','.join(refs), 'Quantity': len(refs), 'Manufacturer': maker,
                     'MPN': mpn, 'Description': description, 'Footprint': footprint,
                     'Mount': mount, 'Notes': 'exact part; no unapproved substitutions'})
    write_csv(out / 'BOM.csv', list(rows[0]), rows)
    positions = list(csv.DictReader((out / 'checks/raw-positions.csv').open()))
    expected_smt = set(populated) - {'J2'}
    require(Counter(r['Ref'] for r in positions) == Counter(expected_smt), 'SMT position population differs')
    cpl = []
    for row in sorted(positions, key=lambda r: ref_key(r['Ref'])):
        f = footprints[row['Ref']]
        require(abs(float(row['PosX']) - f['position'][0]) < 1e-6 and
                abs(float(row['PosY']) + f['position'][1]) < 1e-6 and
                abs((float(row['Rot']) - f['rotation'] + 180) % 360 - 180) < 1e-5 and
                row['Side'].lower() == ('bottom' if f['layer'] == 'B.Cu' else 'top'),
                'placement coordinates differ: ' + row['Ref'])
        cpl.append({'Ref Des': row['Ref'], 'Footprint': row['Package'],
                    'X (mm)': row['PosX'], 'Y (mm)': row['PosY'],
                    'Rotation': f"{float(row['Rot']) % 360:.4f}", 'Side': row['Side']})
    write_csv(out / 'CPL.csv', list(cpl[0]), cpl)
    tht = [{'Designator': ref, 'X (mm)': footprints[ref]['position'][0],
            'Y (mm)': -footprints[ref]['position'][1],
            'Rotation': footprints[ref]['rotation'] % 360, 'Side': 'top'} for ref in ('J2',)]
    write_csv(out / 'through-hole-positions.csv', list(tht[0]), tht)
    exclusions = [{'Designator': c['ref'], 'Reason': 'bare copper test point; no component to fit'}
                  for c in components if c['attributes']]
    write_csv(out / 'not-fitted.csv', list(exclusions[0]), exclusions)
    return {'board_components': len(populated), 'smt_components': len(expected_smt), 'through_hole_components': 1,
            'unique_board_parts': len(groups), 'loose_fuses_per_board': 0,
            'top_smt_components': sum(r['Side'].lower() == 'top' for r in cpl),
            'bottom_smt_components': sum(r['Side'].lower() == 'bottom' for r in cpl),
            'smt_pads': sum(bool(p['polygons']) for ref in expected_smt for p in footprints[ref]['pads']),
            'soldered_through_holes': sum(d['plated'] and d['ref'] != 'VIA' for d in geometry['drills'])}


def gerber_geometry(file):
    import shapely
    from shapely.geometry import Polygon, Point, LineString, box
    from shapely.ops import unary_union
    from shapely import affinity
    from gerbonara import graphic_primitives as gp
    from gerbonara.utils import MM
    def primitive_shape(prim):
        if isinstance(prim, gp.Circle):
            s = Point(prim.x, prim.y).buffer(prim.r, quad_segs=96)
        elif isinstance(prim, gp.Rectangle):
            s = affinity.translate(affinity.rotate(box(-prim.w/2, -prim.h/2, prim.w/2, prim.h/2),
                    prim.rotation, origin=(0, 0), use_radians=True), prim.x, prim.y)
        elif isinstance(prim, gp.Line):
            s = LineString([(prim.x1, prim.y1), (prim.x2, prim.y2)]).buffer(prim.width/2, quad_segs=64)
        else:
            s = shapely.make_valid(Polygon(prim.to_arc_poly().approximate_arcs(max_error=.0002).outline))
        return affinity.scale(s, 1, -1, origin=(0, 0))
    batches, pending, polarity = [], [], True
    for obj in file.objects:
        for prim in obj.to_primitives(unit=MM):
            if prim.polarity_dark != polarity:
                batches.append((polarity, unary_union(pending)))
                pending, polarity = [], prim.polarity_dark
            pending.append(primitive_shape(prim))
    batches.append((polarity, unary_union(pending)))
    total = Polygon()
    for dark, shape in batches:
        total = total.union(shape) if dark else total.difference(shape)
    return total


def check_exports(out, geometry):
    from gerbonara import GerberFile, ExcellonFile
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    result = {'copper': {}, 'drills': {}, 'mask': {}, 'paste': {}}
    outline = unary_union([Polygon(p['outer'],p['holes']) for p in geometry['outline']])
    plotted_edge = gerber_geometry(GerberFile.open(next((out/'gerbers').glob('*.gm1'))))
    require(len(geometry['outline']) == 1 and len(geometry['outline'][0]['holes']) == 4,
            'board outline or mounting-hole count changed')
    require(outline.boundary.difference(plotted_edge.buffer(.006)).length < 1e-5 and
            plotted_edge.difference(outline.boundary.buffer(.031)).area < 1e-6,
            'plotted outline differs from native contour')
    result['outline'] = {'outer_contours': 1, 'unplated_mounting_cutouts': 4,
                         'native_curve_tolerance_mm': .005, 'gerber_line_width_mm': .05}
    for layer in geometry['copper_layers']:
        actual = gerber_geometry(GerberFile.open(next((out/'gerbers').glob('*.' + LAYERS[layer]))))
        expected = unary_union([Polygon(q['outer'], q['holes']) for item in geometry['copper']
                               if item['layer'] == layer for q in item['polygons']])
        # Native circular polygons use 0.5 um outward approximation. Allow 2 um
        # at their boundaries, never a missing track, pad, plane or wrong layer.
        missing = expected.difference(actual.buffer(.002)).area
        extra = actual.difference(expected.buffer(.002)).area
        result['copper'][layer] = {'missing_beyond_2um_mm2': missing, 'extra_beyond_2um_mm2': extra,
                                  'native_area_mm2': expected.area, 'gerber_area_mm2': actual.area}
        require(missing < 1e-6 and extra < 1e-6, 'plotted copper differs from saved board: ' + layer)
        print('checked copper', layer, flush=True)
    for mode, plated in [('PTH', True), ('NPTH', False)]:
        file = ExcellonFile.open(next((out/'gerbers').glob('*-' + mode + '.drl')))
        require(all(type(x).__name__ == 'Flash' for x in file.objects), 'slotted drill needs a reviewed check')
        drills = [d for d in geometry['drills'] if d['plated'] == plated]
        require(all(d['size'][0] == d['size'][1] for d in drills), 'slotted native hole needs a reviewed check')
        remaining = list(drills)
        max_error = 0
        require(len(file.objects) == len(remaining), mode + ' drill count differs')
        for hit in file.objects:
            matches = [d for d in remaining if abs(hit.x-d['position'][0]) <= .0005001
                       and abs(-hit.y-d['position'][1]) <= .0005001
                       and abs(hit.aperture.diameter-d['size'][0]) < 1e-6]
            require(len(matches) == 1, mode + ' drill position or diameter differs')
            d = matches[0]
            max_error = max(max_error, abs(hit.x-d['position'][0]), abs(-hit.y-d['position'][1]))
            remaining.remove(d)
        require(not remaining, mode + ' native drill omitted')
        result['drills'][mode] = {'holes': len(drills), 'mismatches': 0,
                                  'coordinate_quantum_mm': .001, 'max_coordinate_error_mm': max_error}
    for side, layer, mask_ext, paste_ext in [('top','F.Cu','gts','gtp'), ('bottom','B.Cu','gbs','gbp')]:
        mask = gerber_geometry(GerberFile.open(next((out/'gerbers').glob('*.'+mask_ext))))
        exposed = [v['id'] for v in geometry['vias']
                   if mask.intersection(Point(v['position']).buffer(v['drill']/2)).area > 1e-5]
        require(not exposed, side + ' has mask-exposed via holes: ' + ','.join(exposed))
        smt_copper = unary_union([Polygon(q['outer'],q['holes']) for f in geometry['footprints']
                                 if f['attributes'] & 2 for p in f['pads']
                                 for q in p['polygons'].get(layer,[])])
        shifted_smt_mask = mask.intersection(smt_copper.buffer(.051)).buffer(.05)
        exposed_with_shift = [v['id'] for v in geometry['vias']
            if shifted_smt_mask.intersection(Point(v['position']).buffer(v['drill']/2)).area > 1e-5]
        require(not exposed_with_shift, side + ' SMT mask shift can expose a via hole')
        paste = gerber_geometry(GerberFile.open(next((out/'paste').glob('*.'+paste_ext))))
        pad_copper = unary_union([Polygon(q['outer'],q['holes']) for f in geometry['footprints']
                                 for p in f['pads'] for q in p['polygons'].get(layer,[])])
        outside = paste.difference(pad_copper.buffer(.002)).area
        require(outside < 1e-6, side + ' paste extends beyond native copper lands')
        for f in geometry['footprints']:
            if not f['attributes'] & 2 or f['ref'].startswith('TPB'):
                continue
            for pad in f['pads']:
                if ('F.Paste' if side == 'top' else 'B.Paste') not in pad['layers']:
                    continue
                require(paste.intersects(Point(pad['position'])), 'missing paste: '+f['ref']+'.'+pad['number'])
        result['mask'][side] = {'exposed_via_holes': 0, 'smt_mask_shift_screen_mm': .05,
                               'via_holes_exposed_by_shifted_smt_mask': 0}
        result['paste'][side] = {'outside_pad_copper_mm2': outside, 'area_mm2': paste.area}
    return result


def check_ipc(path, geometry):
    """Match KiCad's fixed-width IPC records to native pads and vias."""
    expected = []
    for f in geometry['footprints']:
        for p in f['pads']:
            if p['polygons'] or p['attribute'] == 3:
                expected.append({'ref': f['ref'], 'pin': p['number'], 'net': p['net'],
                                 'position': p['position'], 'via': False})
    expected += [{'ref': 'VIA', 'pin': '', 'net': v['net'], 'position': v['position'], 'via': True}
                 for v in geometry['vias']]
    remaining = list(expected)
    native_to_ipc, ipc_to_native = defaultdict(set), defaultdict(set)
    for line in Path(path).read_text().splitlines():
        if not line.startswith(('317','327','367')):
            continue
        ref, pin, net = line[20:26].strip(), line[27:31].strip(), line[3:17].strip()
        # KiCad uses 0.0001 inch coordinates in this export, P UNITS CUST 0.
        coordinates = re.search(r'X([+-][0-9]+)Y([+-][0-9]+)', line)
        require(coordinates is not None, 'missing IPC coordinates')
        x, y = int(coordinates[1])*.00254, -int(coordinates[2])*.00254
        matches = [e for e in remaining if e['ref'] == ref and (e['via'] or e['pin'] == pin)
                   and abs(e['position'][0]-x) <= .0012701 and abs(e['position'][1]-y) <= .0012701]
        require(len(matches) == 1, 'IPC reference/coordinate differs: '+line)
        e = matches[0]
        remaining.remove(e)
        if e['net']:
            native_to_ipc[e['net']].add(net)
            ipc_to_native[net].add(e['net'])
    require(not remaining, 'native pads or vias missing from electrical test file')
    require(all(len(x) == 1 for x in native_to_ipc.values()) and all(len(x) == 1 for x in ipc_to_native.values()),
            'electrical test net names merge or split native nets')
    return {'records': len(expected), 'nets': len(native_to_ipc), 'missing_records': 0,
            'ambiguous_net_names': 0, 'coordinate_quantum_mm': .00254}


def verify_package(out):
    manifest = json.loads((out / 'manifest.json').read_text())
    require(manifest['source_sha256'] == source_hashes(), 'package no longer matches the source')
    listed = {}
    for line in (out / 'SHA256SUMS.txt').read_text().splitlines():
        sha, name = line.split('  ', 1)
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'invalid checksum path')
        require(name not in listed and digest(out / name) == sha, 'package file changed: ' + name)
        listed[name] = sha
    actual = {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt'}
    require(set(listed) == actual, 'checksum file list differs')
    print('package source hashes and files match')


def write_order_notes(out):
    manifest = json.loads((out/'manifest.json').read_text())
    assembly = manifest['assembly']
    exports = json.loads((out/'checks/export-check.json').read_text())
    warnings = ', '.join(f'{count} {kind}' for kind, count in
                         manifest['checks']['refilled']['warnings'].items()) or 'none'
    (out/'README.md').write_text(f'''# bms order files

this is the pcbway package for the four-layer bms. the exact source files,
checks and output hashes are recorded in `manifest.json` and `SHA256SUMS.txt`.
these are checked prototype files. pcbway has not reviewed or quoted this
package yet, and no order has been submitted.

## uploads

- `bms_GERBERS.zip`: bare-board fabrication files, including separate plated
  and unplated drills. all four copper layers are included.
- `BOM.csv`: {assembly['board_components']} fitted parts, grouped into {assembly['unique_board_parts']} part numbers.
- `CPL.csv`: {assembly['smt_components']} smt placements, {assembly['top_smt_components']} on top and {assembly['bottom_smt_components']} underneath.
- `through-hole-positions.csv`: J2, fitted from the top.
- `paste/`: top and bottom stencil artwork. the power-fet stencil windows
  are intentional. the assembler should review stencil thickness and process.
- `bms.ipc`: the bare-board electrical test netlist, with {exports['electrical_test']['records']} records and {exports['electrical_test']['nets']} nets.
- `assembly/`: both assembly drawings and the test-point map.
- `previews/`: rendered gerbers for inspection. the gerbers control fabrication.

the cpl uses millimetres, the same absolute origin as the gerbers, positive x
to the right and positive y up. bottom x coordinates are not mirrored.
rotations follow kicad. match pin 1 and polarity against the assembly drawings
when pcbway checks the placement preview. the bottom drawing is viewed from
underneath; it is not the coordinate convention used by the cpl.

## board settings

| setting | value |
| --- | --- |
| outline | 61.900 x 36.148 mm, routed contour |
| layers, top to bottom | F.Cu, In1.Cu, In2.Cu, B.Cu |
| material and nominal thickness | standard FR-4, 1.6 mm |
| copper | 1 oz on all four layers, including the inner layers |
| finish | ENIG |
| mask and printing | green mask, white printing on both sides |
| smallest track | 0.10 mm |
| smallest via hole / land | 0.20 / 0.50 mm |
| via annular ring | at least 0.15 mm |
| vias | through vias, tented on both sides |
| filled or capped vias | not required by this layout |
| impedance control | not required |
| electrical test | flying probe against the supplied IPC-D-356 netlist |

the four support holes are unplated circular cutouts in Edge.Cuts. the
NPTH drill file also contains J2's 3 mm locating hole. retain all five.

the cad dielectric entries total about 1.626 mm. they are indicative, not a
custom impedance stackup. quote a standard 1.6 mm build with 1 oz copper on
every layer. the power checks used 35 um copper and 20 um barrel plating;
confirm the finished copper and minimum hole plating before releasing it.
report any lower guaranteed thickness so the power checks can be revisited.

## assembly

fit the exact BOM, including the 0.1% thermal resistors and both current
shunts. substitutions need review. do not replace BQ7791500 with another
threshold option, or LTC4368-1 with the -2 variant.

F1 is the SCHURTER 3-101-056 HCF fuse, 5 A, fast acting, with a 1000 A
interrupt rating at 125 VDC under the specified L/R condition. it is an SMT
part, not a holder or a removable fuse. use the exact part. test pads are
exposed copper, not components to fit.

the smt count is {assembly['smt_pads']} copper lands. the extra power-fet stencil windows
are apertures within those lands, not extra components or solder joints.
there are {assembly['soldered_through_holes']} soldered through holes, excluding vias and locating holes.
use the supplied paste apertures, check polarity and inspect the power-fet
joints. use lead-free assembly and component-appropriate reflow profiles.

keep the raw, protected and isolated grounds separate. use insulating board
supports. batteries, probe wiring and the mating cable harnesses are not
included in this pcb assembly order. no programming is required on the bms.
powered protection tests will be done during bring-up with simulated cells.

J2 is the right-angle Molex 43045-0400 Micro-Fit header. its mating cable
uses 43025-0400 and tin 43030-0038 contacts. the plug drawing gives a
10.81 mm mated height and 11 mm latch envelope above the PCB. reserve the
plug and cable space shown in the harness notes, including 12.7 mm of free
wire before bending. the front pin row is 9.80 mm from the board edge;
Molex allows 10.16 mm maximum. keep the combined header/edge positioning
error within 0.25 mm toward the edge-clearance limit.

J2072 is the two-pole WAGO 2060-452/998-404. the assembler must solder both
lands for each contact. its body is 4.5 mm high; the wire and release-tool
space are separate. the two bottom JST connectors also need cable access.

pcbway can add process rails and fiducials if their assembly setup needs
them. send the panel drawing for review; do not change the finished outline,
mounting holes or component positions. return the unused bare boards.

## quantity and quote

compare five bare pcbs with one assembled against five bare pcbs with two
assembled. keep the stackup, parts and shipping choices identical. one is
enough to start testing; two gives me a spare. there is no confirmed total
yet. the price needs the parts, assembly setup, attrition, shipping and tax.

check the sourced BOM, part availability, placement preview, finished copper,
hole plating and any panel changes before paying. this package records the
design checks; it does not claim factory acceptance or powered testing.

## checks and regeneration

the saved and refilled boards passed connectivity, schematic parity and the
0.10 mm fabrication checks. footprint pads and drills match the libraries.
all four plotted copper layers match the native geometry within a 2 um
boundary approximation. drill coordinates match their 1 um export grid.
mask openings expose no via holes, including a 0.05 mm outward-margin screen
around the smt mask openings. the stencil openings stay on pads. confirm
the actual mask registration with pcbway; this screen is a design check.

the refilled report retains these warnings: {warnings}.
no electrical errors, dangling copper or silkscreen violations were waived.
the existing ERC warnings are recorded separately in the manifest.
the generic fuse and two-pin connector symbols also retain their library-name
filter warnings for F1 and J2072. their exact footprints, pads and pin maps
are checked separately; no netlist mismatch is accepted.
`checks/layout-checks.json` holds the power-path review. the 3 A pack
qualification limit remains in force; a 5 A fuse does not raise it.

install `gen/requirements-bms-fabrication.txt` in a local virtual environment.
run `python gen/generate_bms_pcbway_package.py --output NEW_PACKAGE --work
NEW_SCRATCH_DIRECTORY` from the project root. both paths should be in this
project. kicad cli and its pcbnew python are required. keep an old package
until its replacement has passed. verify a retained package with
`python gen/generate_bms_pcbway_package.py --output manufacturing/bms/pcbway --verify`.
a source edit makes the old package stale.

## supplier references

- [pcbway fabrication limits](https://www.pcbway.com/capabilities.html)
- [pcbway assembly files](https://www.pcbway.com/assembly-file-requirements.html)
- [pcbway confirms assembly from one piece](https://www.pcbway.com/blog/PCB_Basic_Information/PCBWay_Q_A_003___Common_Questions_for_PCBA_Ordering_01.html)
- [molex 43045-0400 header](https://www.molex.com/en-us/products/part-detail/430450400)
- [molex 43025-0400 plug drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43025/430250400_sd.pdf)
- [schurter HCF fuse](https://www.schurter.com/en/datasheet/typ_HCF.pdf)
- [WAGO 2060-452](https://www.wago.com/2060-452/998-404)
''')
    (out/'PCBA_ORDER_REMARK.txt').write_text(
        'please quote 5 bare pcbs with 1 assembled, and the same build with 2 assembled. '
        'both-side smt plus top-side J2 through-hole assembly. exact BOM, no unapproved substitutions. '
        'F1 is the soldered SCHURTER 3-101-056 5 A fuse; no loose fuse insert. '
        'J2 is Molex 43045-0400; keep the front pin row within 10.16 mm of the routed edge. '
        'the design is 9.80 mm, allowing at most 0.25 mm combined header/edge positioning error. '
        '1.6 mm FR-4, ENIG, green mask, white printing, 1 oz copper on all four layers. '
        'confirm finished copper and minimum barrel plating against the 35 um / 20 um design basis. '
        'use the supplied paste files and electrical test netlist. all vias tented; no filled vias requested. '
        'review bottom-side placement orientation, power-fet paste windows and all polarity marks. '
        'send any panel/rail/fiducial proposal for review. return unused bare pcbs.\n')


def build(out, work):
    from check_release_candidate import find_kicad_cli, find_kicad_python, stage_pcb_project
    from report_schematic_pcb_eco import compare
    import importlib.metadata
    require(importlib.metadata.version('shapely') == '2.1.2' and
            importlib.metadata.version('gerbonara') == '1.6.3', 'use the pinned fabrication dependencies')
    require(out.is_relative_to(ROOT) and work.is_relative_to(ROOT), 'keep the package and scratch work in this project')
    require(not out.exists(), 'output exists; keep the old package and choose a new output')
    out.mkdir(parents=True)
    for name in ('checks', 'gerbers', 'paste', 'previews'):
        (out/name).mkdir()
    work.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    cli, native_python = find_kicad_cli(), find_kicad_python()
    def run(*args):
        proc = subprocess.run([cli, *map(str, args)], capture_output=True, text=True, cwd=ROOT)
        with (out/'checks/export.log').open('a') as log:
            log.write(' '.join(map(str, args)) + '\n' + proc.stdout + proc.stderr + '\n')
        require(proc.returncode == 0, 'KiCad export failed: ' + str(args[:3]))
    board = stage_pcb_project(BOARD, BOARD.with_suffix('.kicad_sch'), work/'design')
    project = board.with_suffix('.kicad_pro')
    settings = json.loads(project.read_text())
    design = settings['board']['design_settings']
    require(not design['drc_exclusions'], 'review exclusions before export')
    restored = [k for k, v in design['rule_severities'].items() if v == 'ignore']
    for k in restored:
        design['rule_severities'][k] = 'warning'
    design['rules'].update(min_track_width=.1, min_clearance=.1,
                           min_via_annular_width=.15, min_text_thickness=.15)
    design['defaults'].update(silk_line_width=.15, silk_text_thickness=.15)
    write_json(project, settings)
    for name, extra in [('saved', []), ('refilled', ['--refill-zones', '--save-board'])]:
        run('pcb', 'drc', '--severity-all', '--all-track-errors', '--schematic-parity',
            '--format', 'json', '--output', out/'checks'/(name+'-drc.json'), *extra, board)
        check_drc(out/'checks'/(name+'-drc.json'))
    run('sch', 'erc', '--severity-all', '--format', 'json', '--output', out/'checks/erc.json', board.with_suffix('.kicad_sch'))
    erc = json.loads((out/'checks/erc.json').read_text())
    erc_findings = [v for sheet in erc['sheets'] for v in sheet['violations']]
    require(all(v['severity'] == 'warning' and v['type'] in ('lib_symbol_mismatch', 'ground_pin_not_ground')
                for v in erc_findings), 'new schematic ERC finding')
    run('sch', 'export', 'netlist', '--format', 'kicadxml', '--output', out/'checks/netlist.xml', board.with_suffix('.kicad_sch'))
    parity = compare(board.read_text(), ET.parse(out/'checks/netlist.xml').getroot(), standalone_root_prefix=True)
    require(parity['passed'], 'netlist and board differ')
    write_json(out/'checks/parity.json', parity)
    geometry_path = work/'geometry.json'
    proc = subprocess.run([native_python, str(ROOT/'gen/bms_fabrication_geometry.py'), str(board), str(geometry_path), '--headless'],
                          capture_output=True, text=True, cwd=ROOT)
    (out/'checks/native.log').write_text(proc.stdout + proc.stderr)
    require(proc.returncode == 0, 'native geometry export failed')
    geometry = json.loads(geometry_path.read_text())
    require(geometry['native_airwires'] == 0 and not geometry['library_pad_differences'], 'native pad or connectivity check failed')
    require(geometry['copper_layers'] == ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], 'wrong copper layers')
    layout = json.loads((ROOT/'verification/bms-layout.json').read_text())
    require(layout['source_sha256']['bms/bms.kicad_pcb'] == before['bms/bms.kicad_pcb'],
            'layout evidence belongs to a different saved board')
    if layout['manufacturing_geometry_sha256'] != electrical_geometry_hash(geometry):
        original_geometry_path = work/'saved-geometry.json'
        proc = subprocess.run([native_python, str(ROOT/'gen/bms_fabrication_geometry.py'),
                               str(BOARD), str(original_geometry_path), '--headless'],
                              capture_output=True, text=True, cwd=ROOT)
        (out/'checks/saved-native.log').write_text(proc.stdout + proc.stderr)
        require(proc.returncode == 0, 'saved geometry export failed')
        original_geometry = json.loads(original_geometry_path.read_text())
        require(layout['manufacturing_geometry_sha256'] == electrical_geometry_hash(original_geometry),
                'power-path evidence does not match the saved geometry')
        refill_check = compare_refill_geometry(original_geometry, geometry)
    else:
        refill_check = {'maximum_boundary_difference_mm': 0, 'zones': []}
    write_json(out/'checks/refill-geometry.json', refill_check)
    run('pcb', 'export', 'gerbers', '--output', out/'gerbers', '--layers', ','.join(LAYERS), '--precision', '6', board)
    run('pcb', 'export', 'drill', '--output', out/'gerbers', '--format', 'excellon', '--drill-origin', 'absolute',
        '--excellon-units', 'mm', '--excellon-zeros-format', 'decimal', '--excellon-separate-th',
        '--generate-report', '--report-path', out/'checks/drills.txt', board)
    run('pcb', 'export', 'gerbers', '--output', out/'paste', '--layers', 'F.Paste,B.Paste', '--precision', '6', board)
    run('pcb', 'export', 'ipcd356', '--output', out/'bms.ipc', board)
    run('pcb', 'export', 'pos', '--output', out/'checks/raw-positions.csv', '--format', 'csv', '--units', 'mm',
        '--side', 'both', '--smd-only', '--exclude-dnp', board)
    run('pcb', 'export', 'stats', '--output', out/'checks/board-stats.json', '--format', 'json', '--units', 'mm', board)
    assembly = assembly_files(out, geometry)
    exports = check_exports(out, geometry)
    exports['electrical_test'] = check_ipc(out/'bms.ipc', geometry)
    write_json(out/'checks/export-check.json', exports)
    from gerbonara import GerberFile
    for layer, suffix in LAYERS.items():
        plotted = GerberFile.open(next((out/'gerbers').glob('*.'+suffix)))
        (out/'previews'/(layer+'.svg')).write_text(str(plotted.to_svg(margin=1)))
    files = sorted((out/'gerbers').iterdir())
    require(len(files) == 12, 'unexpected Gerber/drill package file count')
    zip_files(out/'bms_GERBERS.zip', [(p, p.name) for p in files])
    require(source_hashes() == before, 'source changed during export')
    manifest = {'schema': 1, 'status': 'CHECKED_FILES_PENDING_FACTORY_REVIEW',
        'board': 'bms/bms.kicad_pcb', 'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'working_tree': bool(subprocess.check_output(['git','status','--porcelain','--','bms'],cwd=ROOT,text=True).strip()),
        'source_sha256': before, 'refilled_board_sha256': digest(board),
        'restored_warning_categories': restored, 'audit_minimums_mm': {'track': .1, 'clearance': .1, 'via_annular_ring': .15, 'silk_stroke': .15},
        'checks': {'saved': check_drc(out/'checks/saved-drc.json'), 'refilled': check_drc(out/'checks/refilled-drc.json'),
                   'native_airwires': 0, 'library_pad_differences': [], 'parity_passed': True,
                   'erc_errors': 0, 'erc_warnings': dict(Counter(v['type'] for v in erc_findings)),
                   'power_path_evidence_matches_geometry': True},
        'library_sha256': geometry['library_sha256'], 'assembly': assembly,
        'kicad_version': subprocess.check_output([cli, 'version'], text=True).strip(),
        'export_checker_versions': {'shapely': '2.1.2', 'gerbonara': '1.6.3'},
        'order_submitted': False, 'hardware_testing': 'pending'}
    write_json(out/'manifest.json', manifest)
    write_order_notes(out)
    (out/'assembly').mkdir()
    for name in ('front-assembly.svg', 'back-assembly.svg', 'test-points.csv', 'assembly-source.json'):
        shutil.copyfile(ROOT/'manufacturing/bms'/name, out/'assembly'/name)
    shutil.copyfile(ROOT/'verification/bms-layout.json', out/'checks/layout-checks.json')
    source_files = [(ROOT/f, f) for f in before if f.startswith('bms/')]
    zip_files(out/'design-source.zip', source_files)
    # Keep local account and scratch paths out of the supplier's reports.
    for report in (out/'checks').iterdir():
        if report.suffix in ('.json', '.xml', '.log', '.txt', '.csv'):
            text = report.read_text().replace(str(board.parent), 'bms')
            text = text.replace(str(out), 'package').replace(str(work), 'build')
            text = text.replace(str(ROOT) + '/', '')
            report.write_text(text.rstrip() + '\n')
    (out/'SHA256SUMS.txt').write_text(''.join(
        f'{digest(p)}  {p.relative_to(out).as_posix()}\n'
        for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS.txt'))
    verify_package(out)
    zip_files(out.parent/'bms_PCBWAY.zip', [(p, p.relative_to(out).as_posix())
              for p in sorted(out.rglob('*')) if p.is_file()])
    print(json.dumps(assembly, indent=2))
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--work', type=Path)
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    out = args.output.resolve()
    if args.verify:
        verify_package(out)
    else:
        require(args.work is not None, '--work is required for an export')
        build(out, args.work.resolve())


if __name__ == '__main__':
    main()

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
RELEASE_LINKS = {'R870', 'R871', 'R872'}
OFFBOARD_PROBES = {'TH2201', 'TH2202', 'TH2203'}
QUALIFICATION_KEYS = {'monitor', 'otp', 'current_transfer', 'thermal_windows',
                      'cells', 'pack', 'gauge', 'charging', 'discharge'}


def is_test_point(component):
    return component['ref'].startswith('TP') or component['footprint'].startswith('TestPoint:')


def assembly_contract(netlist):
    """Select a reviewed population by its controller and exact shunts."""
    from report_schematic_pcb_eco import parse_schematic
    components = parse_schematic(netlist)
    by_ref = {c['ref']: c for c in components}
    require(len(by_ref) == len(components), 'duplicate schematic reference')
    mpn = lambda ref: by_ref.get(ref, {}).get('fields', {}).get('MPN')
    monitor = by_ref.get('U719', {})
    if 'BQ76922' in str(monitor):
        name, counts = 'BQ76922_2m_UNARMED_PROTOTYPE', (204, 201, 168, 30)
        parts = {'U719': 'BQ76922RSNR', 'RS11': 'CSS4J-4026K-2L00F',
                 'F1': '3-101-051', 'J2': '2060-452/998-404',
                 'J2072': '2060-452/998-404', 'U2210': 'INA381A3IDGSR',
                 'U2211': 'INA381A4IDGSR', 'U2213': 'REF3425IDBVR',
                 'U2214': 'TPS3808G30DBVR', 'U2218': 'TPS26600PWPR'}
        require('RS10' not in by_ref, 'obsolete second current shunt on BQ76922 board')
        require(by_ref.get('RS11', {}).get('fields', {}).get('Height') == '2.93 mm',
                'RS11 must use the reviewed 2.93 mm maximum height')
        require(by_ref.get('RS11', {}).get('value', '').startswith('2mOhm 1% 6W'),
                'RS11 must retain the 2 mOhm, 6 W rating')
        for ref in RELEASE_LINKS:
            require(by_ref.get(ref, {}).get('attributes') == {'dnp', 'exclude_from_bom'},
                    ref + ' must remain DNP and excluded from the BOM')
    elif mpn('U719') == 'BQ7791500PWR' and mpn('RS10') == 'CSS2H-2512K-3L00F':
        name, counts = 'LEGACY_BQ77915_3m_5m', (165, 162, 138, 24)
        parts = {'U719': 'BQ7791500PWR', 'RS10': 'CSS2H-2512K-3L00F',
                 'RS11': 'CSS4J-4026K-5L00F', 'F1': '3-101-051',
                 'J2': '2060-452/998-404'}
    else:
        name, counts = 'LEGACY_BQ77915_11m_8m', (152, 149, 125, 24)
        parts = {'U719': 'BQ7791500PWR', 'RS10': 'WSL2512R0110FEA18',
                 'RS11': 'WSLP25128L000FEA', 'F1': '3-101-056', 'J2': '43045-0400'}
    for ref, expected in parts.items():
        require(mpn(ref) == expected, ref + ' differs from reviewed ' + name + ' part')
    require(len(netlist.findall('./components/comp')) == counts[0] and len(components) == counts[1],
            'BMS schematic or onboard population changed; review it before export')
    require(sum(not c['attributes'] for c in components) == counts[2], 'assembly population changed')
    require(sum(is_test_point(c) for c in components) == counts[3], 'test-point population changed')
    offboard = [c for c in netlist.findall('./components/comp')
                if any(p.get('name') == 'exclude_from_board' for p in c.findall('property'))]
    require({c.get('ref') for c in offboard} == OFFBOARD_PROBES and len(offboard) == 3,
            'offboard cell probes changed')
    require(all(not c.findtext('footprint') and c.findtext("fields/field[@name='MPN']") == '104JT-025'
                for c in offboard), 'cell probes must remain offboard parts')
    for c in components:
        if is_test_point(c):
            require(c['attributes'] == {'exclude_from_bom'}, c['ref'] + ' is a bare test point, not an assembly part')
        elif c['attributes']:
            require(name.startswith('BQ76922') and c['ref'] in RELEASE_LINKS and
                    c['attributes'] == {'dnp', 'exclude_from_bom'}, 'unexpected DNP or BOM exclusion: ' + c['ref'])
    return {'name': name, 'components': components, 'offboard': offboard,
            'schematic_components': counts[0], 'onboard_footprints': counts[1],
            'fitted_components': counts[2], 'test_points': counts[3],
            'unarmed': name.startswith('BQ76922')}


def check_prototype_profile(profile):
    import importlib.util
    spec = importlib.util.spec_from_file_location('bms_fixture_profile', ROOT/'firmware/bq76922/fixture_profile.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.check_profile(profile)
    require(set(profile.get('qualification', {})) == QUALIFICATION_KEYS and
            all(v is False for v in profile['qualification'].values()), 'prototype qualification must remain false')
    require(all(profile.get(k) is False for k in ('released_for_ram_test', 'released_for_otp',
            'released_for_assembly', 'calibration_qualified', 'recovery_charging_enabled')),
            'prototype release and recovery flags must remain false')
    require(profile.get('unit_factory_trim_capture_required') is True,
            'per-unit factory trim capture must remain required')
    return {'part': profile['part'], 'qualification': profile['qualification'],
            'released_for_ram_test': False, 'released_for_otp': False, 'released_for_assembly': False,
            'calibration_qualified': False, 'recovery_charging_enabled': False,
            'unit_factory_trim_capture_required': True,
            'fixture_programming': 'pending per-unit factory capture, RAM tests, OTP approval and CRC readback'}


def check_native_gate(geometry, parity, contract):
    from report_schematic_pcb_eco import normalize_net
    require(geometry['native_airwires'] == 0, 'native board has open airwires')
    require(not geometry['library_pad_differences'], 'footprint pads or drills differ from libraries')
    require(geometry['copper_layers'] == ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'], 'wrong copper layers')
    require(parity['passed'], 'netlist and board differ')
    components = {c['ref']: c for c in contract['components']}
    footprints = {f['ref']: f for f in geometry['footprints']}
    require(len(footprints) == len(geometry['footprints']) and set(footprints) == set(components),
            'native footprint population differs')
    electrical = non_electrical = 0
    def net(name):
        value = normalize_net(name)
        return value.lstrip('/') if value else None
    for ref, f in footprints.items():
        c = components[ref]
        require(f['footprint'] == c['footprint'] and f['value'] == c['value'], 'native identity differs: ' + ref)
        native_flags = {name for name, bit in [('dnp', 64), ('exclude_from_bom', 8)] if f['attributes'] & bit}
        require(native_flags == c['attributes'], 'native assembly flags differ: ' + ref)
        for pad in f['pads']:
            number = pad['number']
            if number in c['pin_nets']:
                require(net(pad['net']) == net(c['pin_nets'][number]), 'native pad net differs: ' + ref + '.' + number)
                require(bool(pad['polygons']), 'numbered electrical pad has no copper: ' + ref + '.' + number)
                electrical += 1
            else:
                aperture = (not number and not pad['polygons'] and bool(pad['layers']) and
                            set(pad['layers']) <= {'F.Paste', 'B.Paste', 'F.Mask', 'B.Mask'} and pad['drill'] == [0, 0])
                locating_hole = (not contract['unarmed'] and not number and pad['attribute'] == 3 and
                                 not pad['polygons'] and min(pad['drill']) > 0)
                require(not net(pad['net']) and (aperture or locating_hole),
                        'unreviewed non-electrical pad: ' + ref + '.' + number)
                non_electrical += 1
    total = electrical + non_electrical
    require(parity['counts']['physical_pads_checked'] == electrical, 'electrical parity coverage differs')
    if contract['unarmed']:
        require((len(footprints), electrical, non_electrical, total) == (201, 567, 41, 608),
                'BQ76922 full native pad population changed')
        require({f['layer'] for f in footprints.values()} == {'F.Cu', 'B.Cu'}, 'both-side assembly changed')
        points = [xy for poly in geometry['outline'] for xy in poly['outer']]
        size = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(2)]
        require(abs(size[0]-80) < .005 and abs(size[1]-36.148) < .005, 'BQ76922 outline must be 80 x 36.148 mm')
    return {'all_physical_pads_checked': total, 'electrical_pads_checked': electrical,
            'non_electrical_pad_objects_checked': non_electrical, 'native_airwires': 0}


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
    files += ['gen/generate_bms_pcbway_package.py', 'gen/bms_fabrication_geometry.py', 'gen/bms_power_paths.py',
              'gen/check_release_candidate.py', 'gen/report_schematic_pcb_eco.py',
              'gen/export_bms_assembly.py', 'gen/part_identity.py',
              'gen/requirements-bms-fabrication.txt',
              'firmware/bq76922/profile.json', 'firmware/bq76922/fixture_profile.py',
              'firmware/ec_target/bq76922_profile.c', 'firmware/ec_target/bq76922_profile.h',
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
    # Only these literal library-name filters are benign. Full native library
    # geometry, exact parts and every physical pad are checked independently.
    filters = {
        'Footprint F1': "ducktop2:Schurter_HCF_8.05x5mm doesn't match symbol's footprint filters (*Fuse*)",
        'Footprint J2': "ducktop2:WAGO_2060_452_SMD doesn't match symbol's footprint filters (Connector*:*_1x??_*)",
        'Footprint J2072': "ducktop2:WAGO_2060_452_SMD doesn't match symbol's footprint filters (Connector*:*_1x??_*)",
    }
    findings = d['schematic_parity']
    require(all(v['severity'] == 'warning' and v['type'] == 'footprint_filters_mismatch' and
                len(v['items']) == 1 and filters.get(v['items'][0]['description']) == v['description']
                for v in findings) and len({v['items'][0]['description'] for v in findings}) == len(findings),
            'schematic mismatch; review ' + str(path))
    require(not d['violations'],
            'new DRC finding; review ' + str(path))
    return {'errors': 0, 'unconnected': 0, 'schematic_mismatches': 0, 'warnings': {},
            'footprint_filter_warnings': findings}


def check_erc(erc, contract):
    findings = [v for sheet in erc['sheets'] for v in sheet['violations']]
    allowed = {
        'Symbol U2209 Pin 4 [GND1, Power input, Line]': ('Pin GND1 not connected to ground net', 'U2209', '4'),
        'Symbol U2206 Pin 5 [GND2, Power input, Line]': ('Pin GND2 not connected to ground net', 'U2206', '5'),
    } if contract['unarmed'] else {}
    components = {c['ref']: c for c in contract['components']}
    seen = set()
    for v in findings:
        item = v['items'][0]['description'] if len(v['items']) == 1 else ''
        expected = allowed.get(item)
        require(expected is not None and item not in seen and v['severity'] == 'warning' and
                v['type'] == 'ground_pin_not_ground' and v['description'] == expected[0],
                'new schematic ERC finding: ' + v['description'])
        require(components[expected[1]]['pin_nets'][expected[2]] in ('PACK_NEG_RAW', '/PACK_NEG_RAW'),
                'accepted ground-name warning is not on PACK_NEG_RAW')
        seen.add(item)
    return {'errors': 0, 'warnings': dict(Counter(v['type'] for v in findings)), 'accepted_findings': findings}


def assembly_files(out, geometry):
    from part_identity import identity_errors
    contract = assembly_contract(ET.parse(out / 'checks/netlist.xml').getroot())
    components = contract['components']
    footprints = {f['ref']: f for f in geometry['footprints']}
    require(len(footprints) == len(geometry['footprints']) and
            set(footprints) == {c['ref'] for c in components}, 'BMS footprint population differs')
    populated = {c['ref']: c for c in components if not c['attributes']}
    for c in components:
        f = footprints[c['ref']]
        flags = {name for name, bit in [('dnp', 64), ('exclude_from_bom', 8)] if f['attributes'] & bit}
        require(flags == c['attributes'], 'PCB assembly flags differ: ' + c['ref'])
    mounts = {}
    groups = defaultdict(list)
    for ref, c in populated.items():
        maker, mpn = c['fields'].get('Manufacturer'), c['fields'].get('MPN')
        require(maker and mpn, 'missing manufacturer or MPN: ' + ref)
        errors = identity_errors(c['value'], c['footprint'], mpn)
        require(not errors, ref + ': ' + '; '.join(errors))
        kind = footprints[ref]['attributes'] & 3
        require(kind in (1, 2), 'missing or mixed assembly mount: ' + ref)
        mount = 'SMT' if kind == 2 else 'THT'
        if contract['unarmed']:
            require(mount == 'SMT', 'BQ76922 prototype has no through-hole assembly parts')
        mounts[ref] = mount
        groups[maker, mpn, c['footprint'], mount].append(ref)
    rows = []
    for (maker, mpn, footprint, mount), refs in sorted(groups.items()):
        refs = sorted(refs, key=ref_key)
        description = populated[refs[0]]['value']
        rows.append({'Designator': ','.join(refs), 'Quantity': len(refs), 'Manufacturer': maker,
                     'MPN': mpn, 'Description': description, 'Footprint': footprint,
                     'Mount': mount, 'Notes': 'exact part; no unapproved substitutions'})
    write_csv(out / 'BOM.csv', list(rows[0]), rows)
    with (out / 'checks/raw-positions.csv').open() as handle:
        positions = list(csv.DictReader(handle))
    require(len({r['Ref'] for r in positions}) == len(positions), 'duplicate SMT position reference')
    excluded = {c['ref'] for c in components if is_test_point(c)}
    require(all(r['Ref'] in populated or r['Ref'] in excluded for r in positions),
            'DNP or offboard part in SMT position output')
    positions = [r for r in positions if r['Ref'] not in excluded]
    expected_smt = {ref for ref in populated if mounts[ref] == 'SMT'}
    require(Counter(r['Ref'] for r in positions) == Counter(expected_smt), 'SMT position population differs')
    cpl = []
    for row in sorted(positions, key=lambda r: ref_key(r['Ref'])):
        f = footprints[row['Ref']]
        require(row['Package'] == f['footprint'].split(':', 1)[1] and
                abs(float(row['PosX']) - f['position'][0]) < 1e-6 and
                abs(float(row['PosY']) + f['position'][1]) < 1e-6 and
                abs((float(row['Rot']) - f['rotation'] + 180) % 360 - 180) < 1e-5 and
                row['Side'].lower() == ('bottom' if f['layer'] == 'B.Cu' else 'top'),
                'placement coordinates differ: ' + row['Ref'])
        cpl.append({'Ref Des': row['Ref'], 'Footprint': row['Package'],
                    'X (mm)': row['PosX'], 'Y (mm)': row['PosY'],
                    'Rotation': f"{float(row['Rot']) % 360:.4f}", 'Side': row['Side']})
    write_csv(out / 'CPL.csv', list(cpl[0]), cpl)
    expected_tht = sorted(set(populated) - expected_smt, key=ref_key)
    tht = [{'Designator': ref, 'X (mm)': footprints[ref]['position'][0],
            'Y (mm)': -footprints[ref]['position'][1],
            'Rotation': footprints[ref]['rotation'] % 360,
            'Side': 'bottom' if footprints[ref]['layer'] == 'B.Cu' else 'top'} for ref in expected_tht]
    write_csv(out / 'through-hole-positions.csv', ['Designator', 'X (mm)', 'Y (mm)', 'Rotation', 'Side'], tht)
    exclusions = [{'Designator': c['ref'], 'Reason': 'DNP gate-drive release link; do not bridge or fit' if
                   c['ref'] in RELEASE_LINKS else 'bare copper test point; no component to fit'}
                  for c in components if c['attributes']]
    exclusions += [{'Designator': c.get('ref'), 'Reason': 'offboard cell probe; not part of PCB assembly'}
                   for c in contract['offboard']]
    exclusions.sort(key=lambda c: ref_key(c['Designator']))
    write_csv(out / 'not-fitted.csv', list(exclusions[0]), exclusions)
    return {'controller_profile': contract['name'], 'unarmed_prototype': contract['unarmed'],
            'schematic_components': contract['schematic_components'], 'onboard_footprints': len(footprints),
            'bare_test_points': contract['test_points'], 'offboard_probes': sorted(OFFBOARD_PROBES),
            'dnp_release_links': sorted(RELEASE_LINKS) if contract['unarmed'] else [],
            'board_components': len(populated), 'smt_components': len(expected_smt), 'through_hole_components': len(expected_tht),
            'unique_board_parts': len(groups), 'loose_fuses_per_board': 0,
            'top_smt_components': sum(r['Side'].lower() == 'top' for r in cpl),
            'bottom_smt_components': sum(r['Side'].lower() == 'bottom' for r in cpl),
            'smt_pads': sum(bool(p['polygons']) and p['attribute'] == 1
                            for ref in expected_smt for p in footprints[ref]['pads']),
            'footprint_thermal_holes': sum(d['plated'] and d['ref'] in expected_smt for d in geometry['drills']),
            'soldered_through_holes': sum(d['plated'] and d['ref'] in expected_tht for d in geometry['drills'])}


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


def exposed_pad_via_review(geometry, via, front_mask, back_paste):
    """Recognize the one reviewed BQ76922 ground via; factory review is required."""
    from shapely.geometry import Polygon, Point
    from shapely.ops import unary_union
    part = next((f for f in geometry['footprints'] if f['ref'] == 'U719'), None)
    if not part or part['footprint'] != 'ducktop2:TI_RSN0032B_WQFN32_4x4mm' or part['layer'] != 'B.Cu':
        return None
    pad = next((p for p in part['pads'] if p['number'] == '33'), None)
    if not pad or via['net'] != pad['net'] or via['net'].lstrip('/') != 'PACK_NEG_RAW':
        return None
    if abs(via['drill']-.2) > 1e-6 or abs(via['diameter']-.5) > 1e-6:
        return None
    dx, dy = (via['position'][i]-pad['position'][i] for i in (0, 1))
    if abs(dx) > .005 or abs(dy+.15) > .005:
        return None
    land = unary_union([Polygon(p['outer'], p['holes']) for p in pad['polygons'].get('B.Cu', [])])
    hole = Point(via['position']).buffer(via['drill']/2)
    if not land.covers(Point(via['position']).buffer(via['diameter']/2)):
        return None
    require(front_mask.intersection(hole.buffer(.05)).area < 1e-7,
            'BQ76922 exposed-pad via lacks opposite-face mask coverage')
    require(back_paste.intersection(hole).area < 1e-7,
            'BQ76922 exposed-pad via overlaps nominal paste')
    return {'id': via['id'], 'reference': 'U719', 'pad': '33',
            'position_mm': via['position'], 'drill_mm': via['drill'],
            'front_mask_hole_edge_margin_mm': front_mask.distance(hole),
            'front_mask_shift_screen_mm': .05,
            'nominal_paste_hole_overlap_mm2': back_paste.intersection(hole).area,
            'paste_hole_edge_margin_mm': back_paste.distance(hole),
            'factory_review_required': True,
            'required_review': 'confirm front tent closure, stencil alignment and solder wicking/voiding; fill or plug if this process is not qualified',
            'source': 'https://www.ti.com/lit/ds/symlink/bq76922.pdf, RSN0032B board-layout note 5'}


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
    masks = {side: gerber_geometry(GerberFile.open(next((out/'gerbers').glob('*.'+ext))))
             for side, ext in [('top', 'gts'), ('bottom', 'gbs')]}
    pastes = {side: gerber_geometry(GerberFile.open(next((out/'paste').glob('*.'+ext))))
              for side, ext in [('top', 'gtp'), ('bottom', 'gbp')]}
    reviewed = [r for v in geometry['vias']
                if (r := exposed_pad_via_review(geometry, v, masks['top'], pastes['bottom']))]
    require(len(reviewed) <= 1, 'multiple exposed-pad PCB vias need a new review')
    reviewed_ids = {r['id'] for r in reviewed}
    result['exposed_pad_via_review'] = reviewed
    for side, layer, mask_ext, paste_ext in [('top','F.Cu','gts','gtp'), ('bottom','B.Cu','gbs','gbp')]:
        mask = masks[side]
        exposed = [v['id'] for v in geometry['vias']
                   if mask.intersection(Point(v['position']).buffer(v['drill']/2)).area > 1e-5]
        allowed = reviewed_ids if side == 'bottom' else set()
        require(not (set(exposed)-allowed), side + ' has unintended mask-exposed via holes: ' + ','.join(set(exposed)-allowed))
        smt_copper = unary_union([Polygon(q['outer'],q['holes']) for f in geometry['footprints']
                                 if f['attributes'] & 2 for p in f['pads']
                                 for q in p['polygons'].get(layer,[])])
        shifted_smt_mask = mask.intersection(smt_copper.buffer(.051)).buffer(.05)
        exposed_with_shift = [v['id'] for v in geometry['vias']
            if shifted_smt_mask.intersection(Point(v['position']).buffer(v['drill']/2)).area > 1e-5]
        require(not (set(exposed_with_shift)-allowed), side + ' SMT mask shift can expose an unintended via hole')
        paste = pastes[side]
        pad_copper = unary_union([Polygon(q['outer'],q['holes']) for f in geometry['footprints']
                                 for p in f['pads'] for q in p['polygons'].get(layer,[])])
        outside = paste.difference(pad_copper.buffer(.002)).area
        require(outside < 1e-6, side + ' paste extends beyond native copper lands')
        for f in geometry['footprints']:
            if not f['attributes'] & 2 or is_test_point(f) or f['attributes'] & 64:
                continue
            for pad in f['pads']:
                if ('F.Paste' if side == 'top' else 'B.Paste') not in pad['layers']:
                    continue
                require(paste.intersects(Point(pad['position'])), 'missing paste: '+f['ref']+'.'+pad['number'])
        result['mask'][side] = {'exposed_via_holes': len(exposed), 'smt_mask_shift_screen_mm': .05,
                               'via_holes_exposed_by_shifted_smt_mask': len(exposed_with_shift),
                               'unintended_exposed_via_holes': 0,
                               'reviewed_exposed_pad_vias': sorted(set(exposed) & allowed)}
        result['paste'][side] = {'outside_pad_copper_mm2': outside, 'area_mm2': paste.area}
    return result


def check_ipc(path, geometry):
    """Match KiCad's fixed-width IPC records to native pads and vias."""
    expected = []
    layers = geometry['copper_layers']
    def access_code(item_layers):
        if 'F.Cu' in item_layers and 'B.Cu' in item_layers:
            return 0
        return next(i + 1 for i, name in enumerate(layers) if name in item_layers)
    for f in geometry['footprints']:
        for p in f['pads']:
            if p['polygons'] or p['attribute'] == 3:
                expected.append({'ref': f['ref'], 'pin': p['number'], 'net': p['net'],
                                 'position': p['position'], 'via': False,
                                 'record': '367' if p['attribute'] == 3 else
                                           '327' if p['attribute'] in (1, 2) else '317',
                                 'access': access_code(p['layers']), 'drill': min(p['drill'])})
    expected += [{'ref': 'VIA', 'pin': '', 'net': v['net'], 'position': v['position'], 'via': True,
                  'record': '317', 'access': access_code(v['layers']), 'drill': v['drill']}
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
        access = re.search(r'A([0-9]{2})X', line)
        require(access is not None, 'missing IPC access layer')
        hole = re.search(r'D([0-9]{4})[PU]', line)
        drill = int(hole[1])*.00254 if hole else 0
        matches = [e for e in remaining if e['ref'] == ref and (e['via'] or e['pin'] == pin)
                   and e['record'] == line[:3] and e['access'] == int(access[1])
                   and abs(e['drill']-drill) <= .0012701
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
    contract = assembly_contract(ET.parse(out/'checks/netlist.xml').getroot())
    assembly = manifest.get('assembly', {})
    require(assembly.get('unarmed_prototype') is contract['unarmed'] and
            assembly.get('controller_profile') == contract['name'], 'assembly controller state differs from netlist')
    if contract['unarmed']:
        require(manifest.get('assembly_state') == 'UNARMED_PROTOTYPE' and
                manifest.get('operating_ready') is False and manifest.get('order_submitted') is False,
                'prototype package must remain unarmed and unordered')
        checks = manifest['checks']
        require(checks.get('native_airwires') == 0 and checks.get('all_physical_pads_checked') == 608 and
                checks.get('electrical_pads_checked') == 567 and checks.get('non_electrical_pad_objects_checked') == 41 and
                checks.get('parity_passed') is True and checks.get('erc_errors') == 0 and
                checks.get('library_pad_differences') == [], 'incomplete native prototype proof')
        for name in ('saved', 'refilled'):
            report = check_drc(out/'checks'/(name+'-drc.json'))
            require(report == checks[name], name + ' DRC manifest differs')
        erc = check_erc(json.loads((out/'checks/erc.json').read_text()), contract)
        require(erc['warnings'] == checks['erc_warnings'] and
                erc['accepted_findings'] == checks['erc_accepted_findings'], 'ERC manifest differs')
        profile = json.loads((out/'programming/profile-template.json').read_text())
        require(check_prototype_profile(profile) == manifest['programming'], 'prototype programming manifest differs')
        for filename, field in [('BOM.csv', 'Designator'), ('CPL.csv', 'Ref Des')]:
            with (out/filename).open() as handle:
                rows = list(csv.DictReader(handle))
            refs = [ref for row in rows for ref in row[field].split(',')]
            fitted = {c['ref'] for c in contract['components'] if not c['attributes']}
            require(Counter(refs) == Counter(fitted), filename + ' population differs')
            if filename == 'BOM.csv':
                components = {c['ref']: c for c in contract['components']}
                for row in rows:
                    require(int(row['Quantity']) == len(row['Designator'].split(',')), 'BOM group quantity differs')
                    for ref in row['Designator'].split(','):
                        c = components[ref]
                        require(row['MPN'] == c['fields']['MPN'] and row['Manufacturer'] == c['fields']['Manufacturer'] and
                                row['Footprint'] == c['footprint'] and row['Mount'] == 'SMT',
                                'BOM exact part differs: ' + ref)
        require((assembly.get('schematic_components'), assembly.get('onboard_footprints'),
                 assembly.get('board_components'), assembly.get('smt_components'),
                 assembly.get('through_hole_components'), assembly.get('bare_test_points')) == (204, 201, 168, 168, 0, 30) and
                assembly.get('dnp_release_links') == sorted(RELEASE_LINKS) and
                assembly.get('offboard_probes') == sorted(OFFBOARD_PROBES), 'assembly population manifest differs')
        with (out/'not-fitted.csv').open() as handle:
            excluded = {r['Designator']: r['Reason'] for r in csv.DictReader(handle)}
        wanted = {c['ref'] for c in contract['components'] if c['attributes']} | OFFBOARD_PROBES
        require(set(excluded) == wanted and all('DNP gate-drive release' in excluded[ref] for ref in RELEASE_LINKS),
                'prototype not-fitted list differs')
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
    current = assembly['unarmed_prototype']
    outline = '80.000 x 36.148' if current else 'see checked contour in the fabrication files'
    state = 'unarmed BQ76922 prototype' if current else 'legacy prototype'
    ep_notes = "the BQ76922's single 0.2 mm exposed-pad ground via is open within the\nbottom pad's mask opening. its front face is tented, and nominal paste\ndoes not overlap the hole. the paste edge has no registration margin at\nthat location. confirm front-tent closure, stencil alignment and the\nsolder-wicking/voiding process before assembly; quote filling or plugging\nif that process cannot be qualified. this is the only intentional\nPCB-via mask opening. its measured geometry is in\n`checks/export-check.json`. the [TI package notes](https://www.ti.com/lit/ds/symlink/bq76922.pdf)\ncover thermal-pad soldering and via treatment.\n" if exports.get('exposed_pad_via_review') else ''
    via_fill_note = 'see the exposed-pad review below' if ep_notes else 'not requested'
    through_hole = ('header-only file; no through-hole assembly parts' if not assembly['through_hole_components']
                    else f"{assembly['through_hole_components']} through-hole parts, with positions and sides recorded")
    assembly_notes = ("""U719 is BQ76922RSNR. RS11 is Bourns CSS4J-4026K-2L00F,
2 milliohms, 1%, 6 W, with a 2.93 mm maximum body height. F1 is the
soldered SCHURTER 3-101-051 10 A fuse. J2 and J2072 are SMT WAGO
2060-452/998-404 terminals. solder both lands for every terminal contact.
J2 pin 1 is raw negative and pin 2 is raw positive; follow the top-side
polarity marks. all five cable connectors are on top. keep their edge-facing
wire exits, plug withdrawal and terminal-button access clear.

leave R870, R871 and R872 unpopulated. these are the CHG, DSG and PDSG
gate-drive release links. do not bridge them, fit substitutes, or treat
bare pads as completed assembly. every test point is exposed copper.
TH2201, TH2202 and TH2203 are insulated probes fitted to the cells later;
they are offboard and are not parts for PCB assembly.

there is no permanent MCU on this board. the BQ76922 needs a per-unit
configuration image in its one-time-programmable memory. the supplied
`programming/profile-template.json` is a prototype template, not a released
programming image. capture the actual unit's factory trims before any RAM
or OTP write. prepare and calibrate that unit's image, test it in RAM with
simulated cells and faults, and record the image hash, checksum and I2C CRC
readback. programming, OTP burn and release-link fitting need a separate
fixture release. this exporter performs none of those actions.

read back the complete approved image with CRC after programming and after
repeated cold starts. prove autonomous startup, protection timing, the
latched startup path, regulator headroom, harness integrity, cell limits,
current transfer and all three thermal windows before fitting any release
link. the EC's expected image must match the unit's programmed bytes; load
its matching firmware image and record that image hash too. the EC runtime
does not program OTP, configure the monitor or enable the FETs automatically.
all operating and calibration qualification flags remain false. recovery
charging remains disabled.
""" if current else """this package retains its reviewed legacy controller and shunts. use the
exact BOM and source-bound assembly drawings. no substitutions or operating
qualification are implied by a successful fabrication-file check.
""")
    (out/'README.md').write_text(f"""# bms prototype files

this package contains checked files for an {state}. source hashes,
checks and output hashes are recorded in `manifest.json` and `SHA256SUMS.txt`.
factory review and physical qualification are pending. no order has been
submitted, and this is not an operating release.

## uploads

- `bms_GERBERS.zip`: all four copper layers, masks, printing, routed outline,
  and separate plated and unplated drill files.
- `BOM.csv`: {assembly['board_components']} fitted parts, grouped into {assembly['unique_board_parts']} part numbers.
- `CPL.csv`: {assembly['smt_components']} SMT placements, {assembly['top_smt_components']} on top and {assembly['bottom_smt_components']} underneath.
- `through-hole-positions.csv`: {through_hole}.
- `not-fitted.csv`: DNP links, bare test points and offboard cell probes.
- `paste/`: top and bottom stencil artwork. review stencil thickness and
  power-FET aperture windows before assembly. do not fit the DNP links.
- `bms.ipc`: electrical test netlist, with {exports['electrical_test']['records']} records and {exports['electrical_test']['nets']} nets.
- `assembly/`: both assembly drawings and the test-point map.
- `previews/`: rendered Gerbers for inspection; Gerbers control fabrication.

the CPL uses millimetres, the Gerber absolute origin, positive X right and
positive Y up. bottom X is not mirrored. rotations follow KiCad. check pin 1
and polarity against the assembly drawings. the bottom drawing is viewed
from underneath; that view is separate from the CPL coordinate convention.

## board settings

| setting | value |
| --- | --- |
| outline | {outline} mm, routed contour |
| layers, top to bottom | F.Cu, In1.Cu, In2.Cu, B.Cu |
| material and nominal thickness | standard FR-4, 1.6 mm |
| copper | 1 oz on all four layers, including the inner layers |
| finish | ENIG |
| mask and printing | green mask, white printing on both sides |
| smallest track | 0.10 mm |
| smallest via hole / land | 0.20 / 0.50 mm |
| via annular ring | at least 0.15 mm |
| vias | through vias; see the exposed-pad note for U719 |
| filled or capped vias | {via_fill_note} |
| impedance control | not requested |
| electrical test | flying probe against the supplied IPC-D-356 netlist |

the four support holes are unplated circular cutouts in Edge.Cuts. retain
all outline cutouts and all holes in the supplied drill files. the dielectric
entries are indicative, not a custom impedance stackup. quote a standard
1.6 mm build with 1 oz copper on every layer. the design basis is 35 um
copper and 20 um barrel plating. confirm the finished copper and minimum
hole plating; report lower guaranteed thickness for review.

## assembly and programming

{ep_notes}

fit the exact BOM, including the precision thermal resistors and shunt.
substitutions need review. {assembly_notes}
the fitted SMT count is {assembly['smt_pads']} copper lands. stencil windows within a
land are not extra components. there are {assembly['soldered_through_holes']} soldered through holes,
excluding vias and locating holes. inspect the power-FET joints and use
lead-free assembly with component-appropriate reflow profiles.
the {assembly['footprint_thermal_holes']} plated holes within SMT footprints are thermal features,
not through-hole component placements.

keep PACK_NEG_RAW, FG_VSS and CTRL_GND separate. use insulating board
supports. batteries, probe wiring and mating cable harnesses are not
included in the PCB assembly. powered protection tests start with simulated
cells and the release links absent.

PCBWay can propose process rails and fiducials. send the panel drawing for
review without changing the finished outline, support holes or component
positions. return the unused bare boards.

## quantity and quote

compare five bare PCBs with one assembled against five bare PCBs with two
assembled. keep the stackup, parts and shipping choices identical. one is
enough to start testing; two gives me a spare. the quote needs the parts,
assembly setup, attrition, shipping and tax. no total or order is confirmed.

check sourced parts, availability, placement preview, finished copper,
hole plating and proposed panel changes before payment. the design targets
8 A discharge and at most 3 A charge; these are unqualified allocations.
a 10 A fuse does not establish a safe pack operating limit.

## checks and regeneration

both saved and refilled boards passed the full native zero-airwire gate,
complete schematic parity, library pad/drill checks and 0.10 mm fabrication
checks. this package records {manifest['checks']['all_physical_pads_checked']} physical pad objects, including
{manifest['checks']['electrical_pads_checked']} electrical pads and {manifest['checks']['non_electrical_pad_objects_checked']} non-electrical paste/mask objects.
all four plotted copper layers match native geometry within the 2 um
boundary allowance. drill coordinates match their 1 um export grid. mask
openings expose no unintended via holes, including the 0.05 mm outward-margin
screen around SMT openings. the intentional U719 exposed-pad opening is
recorded separately with its required assembly review. paste stays on pads.
confirm factory mask and stencil registration.

physical DRC errors and warnings are zero. only literal footprint-name
filter messages for the reviewed fuse and WAGO connectors are allowed;
exact parts, library geometry and pad assignments are checked separately.
ERC errors are zero. any accepted raw-ground naming warnings are recorded
with their exact pins in the manifest. `checks/layout-checks.json` is the
source-bound power-path evidence. none of these checks enables operation.

install `gen/requirements-bms-fabrication.txt` in a local virtual environment.
run `python gen/generate_bms_pcbway_package.py --output NEW_PACKAGE --work
NEW_SCRATCH_DIRECTORY` from the project root after the finished canonical
board is promoted and its layout evidence and assembly drawings are refreshed.
keep both paths in this project and keep an old package until its replacement
passes. verify a retained package with
`python gen/generate_bms_pcbway_package.py --output manufacturing/bms/pcbway --verify`.
any source edit makes the retained package stale.

## supplier references

- [PCBWay fabrication limits](https://www.pcbway.com/capabilities.html)
- [PCBWay assembly files](https://www.pcbway.com/assembly-file-requirements.html)
- [PCBWay assembly quantities](https://www.pcbway.com/blog/PCB_Basic_Information/PCBWay_Q_A_003___Common_Questions_for_PCBA_Ordering_01.html)
- [Bourns CSS4J-4026](https://www.bourns.com/docs/product-datasheets/css4j-4026.pdf)
- [TI BQ76922](https://www.ti.com/lit/ds/symlink/bq76922.pdf)
- [SCHURTER HCF fuse](https://www.schurter.com/en/datasheet/typ_HCF.pdf)
- [WAGO 2060-452](https://www.wago.com/2060-452/998-404)
""")
    (out/'PCBA_ORDER_REMARK.txt').write_text(
        'please quote 5 bare PCBs with 1 assembled, and the same build with 2 assembled. '
        'both-side SMT; use the through-hole list only if populated. exact BOM, no unapproved substitutions. '
        'leave every not-fitted item absent. R870, R871 and R872 are DNP release links; do not bridge or fit. '
        'test points are bare copper and cell probes are offboard. '
        '1.6 mm FR-4, ENIG, green mask, white printing, 1 oz copper on all four layers. '
        'confirm finished copper and minimum barrel plating against the 35 um / 20 um design basis. '
        'use supplied paste and electrical test files. ordinary vias are tented. '
        'U719 has one 0.2 mm exposed-pad via with zero nominal paste-edge margin; '
        'confirm opposite-face tent closure, stencil registration and solder-wicking/voiding control, '
        'or quote filling/plugging. '
        'review bottom-side orientation, power-FET windows and polarity marks. '
        'send panel/rail/fiducial proposals for review and return unused bare PCBs. '
        'unarmed prototype; fixture configuration, CRC readback, OTP and physical qualification remain pending. '
        'no programming or operating release is authorized by these files.\n')


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
    run('sch', 'export', 'netlist', '--format', 'kicadxml', '--output', out/'checks/netlist.xml', board.with_suffix('.kicad_sch'))
    netlist = ET.parse(out/'checks/netlist.xml').getroot()
    contract = assembly_contract(netlist)
    erc_check = check_erc(erc, contract)
    programming = check_prototype_profile(json.loads((ROOT/'firmware/bq76922/profile.json').read_text())) if contract['unarmed'] else None
    parity = compare(board.read_text(), netlist, standalone_root_prefix=True)
    require(parity['passed'], 'netlist and board differ')
    write_json(out/'checks/parity.json', parity)
    geometry_path = work/'geometry.json'
    proc = subprocess.run([native_python, str(ROOT/'gen/bms_fabrication_geometry.py'), str(board), str(geometry_path), '--headless'],
                          capture_output=True, text=True, cwd=ROOT)
    (out/'checks/native.log').write_text(proc.stdout + proc.stderr)
    require(proc.returncode == 0, 'native geometry export failed')
    geometry = json.loads(geometry_path.read_text())
    native_check = check_native_gate(geometry, parity, contract)
    original_geometry_path = work/'saved-geometry.json'
    proc = subprocess.run([native_python, str(ROOT/'gen/bms_fabrication_geometry.py'),
                           str(BOARD), str(original_geometry_path), '--headless'],
                          capture_output=True, text=True, cwd=ROOT)
    (out/'checks/saved-native.log').write_text(proc.stdout + proc.stderr)
    require(proc.returncode == 0, 'saved geometry export failed')
    original_geometry = json.loads(original_geometry_path.read_text())
    saved_parity = compare(BOARD.read_text(), netlist, standalone_root_prefix=True)
    saved_native_check = check_native_gate(original_geometry, saved_parity, contract)
    if contract['unarmed']:
        from bms_power_paths import check_power_paths
        write_json(out/'checks/power-paths.json', {
            'saved': check_power_paths(original_geometry),
            'refilled': check_power_paths(geometry),
        })
    require(native_check == saved_native_check, 'saved and refilled pad coverage differs')
    write_json(out/'checks/native-pad-parity.json', {'saved': saved_native_check, 'refilled': native_check})
    assembly_source = json.loads((ROOT/'manufacturing/bms/assembly-source.json').read_text())
    require(assembly_source['sha256'] == before['bms/bms.kicad_pcb'], 'assembly drawings belong to a different saved board')
    layout = json.loads((ROOT/'verification/bms-layout.json').read_text())
    require(layout['source_sha256']['bms/bms.kicad_pcb'] == before['bms/bms.kicad_pcb'],
            'layout evidence belongs to a different saved board')
    if layout['manufacturing_geometry_sha256'] != electrical_geometry_hash(geometry):
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
                   **native_check, 'library_pad_differences': [], 'parity_passed': True,
                   'erc_errors': 0, 'erc_warnings': erc_check['warnings'],
                   'erc_accepted_findings': erc_check['accepted_findings'],
                   'power_path_evidence_matches_geometry': True},
        'library_sha256': geometry['library_sha256'], 'assembly': assembly,
        'kicad_version': subprocess.check_output([cli, 'version'], text=True).strip(),
        'export_checker_versions': {'shapely': '2.1.2', 'gerbonara': '1.6.3'},
        'order_submitted': False, 'hardware_testing': 'pending'}
    if contract['unarmed']:
        manifest.update(assembly_state='UNARMED_PROTOTYPE', operating_ready=False, programming=programming)
        (out/'programming').mkdir()
        shutil.copyfile(ROOT/'firmware/bq76922/profile.json', out/'programming/profile-template.json')
        shutil.copyfile(ROOT/'firmware/bq76922/fixture_profile.py', out/'programming/fixture_profile.py')
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

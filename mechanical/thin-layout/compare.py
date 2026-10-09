#!/usr/bin/env python3
"""Compare alternative cooler reservations against the saved Ducktop2 layout."""
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon as PatchPolygon, Rectangle, Circle
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box as rect
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = ROOT / 'mechanical/case-prototype'
sys.path.insert(0, str(BASELINE))
from build import CONFIG, INVENTORY, installed
from cad import box, cylinder, compound, export_step, render

STUDY = json.loads((HERE / 'study.json').read_text())
PARTS = json.loads((ROOT / 'mechanical/component-placement.json').read_text())['parts']
DATUMS = json.loads((BASELINE / 'cooling-datums.json').read_text())
C = STUDY['budget_assumptions_mm']
COPPER = ROOT / '.workbench/thin-layout-20261008/center-track-geometry.json'
BG = '#faf9f5'
GREEN = '#659d80'
RED = '#bd4938'
BLUE = '#376b93'
GOLD = '#d7b862'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_inputs():
    inputs = {}
    for name, record in INVENTORY.items():
        path = ROOT / record['file']
        digest = sha(path)
        if digest != record['sha256']:
            raise ValueError(f'{name} differs from the case snapshot; refresh the study inputs first')
        inputs[record['file']] = digest
    for part in PARTS:
        if part['source_board_sha256'] != INVENTORY[part['board']]['sha256']:
            raise ValueError('component placement belongs to a different PCB')
    for path in [ROOT / 'mechanical/component-placement.json', BASELINE / 'assembly.json',
                 BASELINE / 'board-inventory.json', BASELINE / 'cooling-datums.json',
                 BASELINE / 'thickness-study.json', HERE / 'study.json',
                 HERE / 'compare.py', HERE / 'extract_copper.py',
                 HERE / 'reference/framework-thermal-plan.json']:
        inputs[str(path.relative_to(ROOT))] = sha(path)
    return inputs


def outline(name):
    polygons = []
    for ring in INVENTORY[name]['outlines']:
        polygons.append(Polygon([installed(name, xy) for xy in ring['outer']],
                                [[installed(name, xy) for xy in h] for h in ring.get('holes', [])]))
    return unary_union(polygons)


def courtyard(part):
    rings = part['courtyards_installed_mm'][part['side']]
    return unary_union([Polygon(r['outer'], r['holes']) for r in rings]) if rings else None


def pocket(key):
    spec = STUDY[key]
    return Point(spec['center']).buffer(spec['radius'], quad_segs=128)


def arc_points(row):
    a, b, c = [np.array(row[k], dtype=float) for k in ['start', 'mid', 'end']]
    system = 2 * np.stack([b - a, c - a])
    if abs(np.linalg.det(system)) < 1e-12:
        return [a.tolist(), b.tolist(), c.tolist()]
    center = np.linalg.solve(system, np.array([b @ b - a @ a, c @ c - a @ a]))
    start, middle, end = [math.atan2(*(p - center)[::-1]) for p in [a, b, c]]
    span = (end - start) % (2 * math.pi)
    if (middle - start) % (2 * math.pi) > span + 1e-10:
        span -= 2 * math.pi
    radius = float(np.linalg.norm(a - center))
    count = max(3, math.ceil(abs(span) * radius / .025) + 1)
    return [(center + radius * np.array([math.cos(t), math.sin(t)])).tolist()
            for t in np.linspace(start, start + span, count)]


def copper_shapes():
    if not COPPER.exists():
        raise FileNotFoundError('run extract_copper.py with KiCad Python first')
    data = json.loads(COPPER.read_text())
    if data['pcb_sha256'] != INVENTORY['center']['sha256']:
        raise ValueError('copper snapshot is stale')
    result = []
    for row in data['items']:
        if row['kind'] == 'PCB_VIA':
            shape = Point(row['start']).buffer(row['width_mm'] / 2 + .001)
        else:
            points = arc_points(row) if 'mid' in row else [row['start'], row['end']]
            shape = LineString(points).buffer(row['width_mm'] / 2 + .001)
        result.append((row, shape))
    return result


def impacts(area, copper):
    parts = [p for p in PARTS if p['board'] in ['left', 'center', 'right']
             and courtyard(p) is not None and area.intersects(courtyard(p))]
    tracks = [r for r, shape in copper if area.intersects(shape)]
    return {'scope': 'plan overlap only; courtyards on both sides, center tracks/vias; zones and structural strength are not checked',
            'footprints': len(parts), 'populated_footprints': sum(not p['dnp'] for p in parts),
            'front': sum(p['side'] == 'front' for p in parts),
            'back': sum(p['side'] == 'back' for p in parts),
            'references': [{'board': p['board'], 'ref': p['reference'], 'dnp': p['dnp'],
                            'side': p['side'], 'value': p['value'], 'height_mm': p['height_mm'],
                            'height_status': p['height_status']} for p in parts],
            'center_copper_items': len(tracks),
            'center_copper_by_layer': dict(sorted(Counter(r['layer'] for r in tracks).items())),
            'center_copper_nets': sorted(set(r['net'] for r in tracks)),
            'copper': tracks}


def budgets():
    saved = json.loads((BASELINE / 'thickness-study.json').read_text())
    b, t, k = CONFIG['cells'], CONFIG['trackpad'], CONFIG['keyboard']
    top = C['hybrid_floor'] + C['main_board_bottom_to_floor'] + INVENTORY['center']['thickness']
    cpu = top + DATUMS['CPU_top_above_board_mm']
    battery = C['hybrid_floor'] + b['pad_thickness'] + b['thickness'] + b['swelling_gap']
    front = battery + C['cell_to_trackpad_support_gap'] + C['trackpad_support'] + C['trackpad_under_clearance'] + t['thickness'] + t['click_travel']
    radio_battery = battery + .5 + C['radio_backside_below_PCB_bottom'] + C['radio_nominal_top_above_PCB_bottom'] + C['radio_top_clearance'] + C['hybrid_deck_skin']
    fan_top = C['hybrid_floor'] + C['remote_fan_bottom_gap'] + C['remote_fan_body'] + C['remote_fan_height_allowance']
    radio_forward = fan_top + C['remote_fan_upper_intake'] + C['radio_backside_reservation'] + C['radio_nominal_top_above_PCB_bottom'] + C['radio_top_clearance'] + C['hybrid_deck_skin']
    keyboard_extra = C['cooler_to_carrier_clearance'] + C['keyboard_carrier'] + C['keyboard_bottom_to_deck']
    # Preserve the modeled key-top offset, 2 mm key/display gap and 0.5 mm panel-back gap.
    lid = (INVENTORY['keyboard']['thickness'] + k['key_height_above_pcb'] - C['keyboard_bottom_to_deck']
           + saved['panel_to_keys'] + CONFIG['lid']['panel_thickness'] + .5 + C['hybrid_lid_skin'])
    framework = cpu + C['framework_adapter'] + STUDY['framework_reference']['drawing_local_height_mm'] + C['framework_height_allowance'] + keyboard_extra
    custom = cpu + C['custom_cooler_above_CPU'] + keyboard_extra
    swap = dict(saved['limiting_deck_heights'])
    swap['blower_intake_under_keyboard'] -= 10.3 - 5.5
    rows = []

    def add(key, name, limits, lid_height, status, below_floor=0, **extra):
        maximum = max(limits.values())
        deck = math.ceil(maximum * 2) / 2
        rows.append({'id': key, 'name': name, 'status': status,
                     'required_deck_heights_mm': limits, 'controlling_stack': max(limits, key=limits.get),
                     'rounded_deck_budget_mm': deck, 'lid_increment_mm': lid_height,
                     'below_floor_structure_mm':below_floor,
                     'closed_budget_without_feet_mm': round(deck + lid_height + below_floor, 3),
                     'full_fit_verified': False, 'thermal_performance_verified': False, **extra})

    add('saved', 'saved printed case', saved['limiting_deck_heights'], 11.3,
        'saved fit model; no complete thermal or physical qualification',below_floor=saved['below_base_bottom_without_feet_mm'])
    add('fan_only', 'thin fan at the same position', swap, 11.3,
        'local fan-height substitution only; no assembly change',below_floor=saved['below_base_bottom_without_feet_mm'])
    add('framework', 'complete Framework cooler + thin structure',
        {'cooler_and_keyboard_budget': framework, 'battery_and_trackpad': front, 'radio_over_cell': radio_battery}, lid,
        'coarse reservation; missing Mu contact datum and formed cooler geometry')
    add('remote_radio_kept', 'right-side cooler; radio stays over cell',
        {'cooler_and_keyboard_budget': custom, 'battery_and_trackpad': front, 'radio_over_cell': radio_battery}, lid,
        'target requiring new pipe/fin/duct, front cable routing, thin supports and recessed radio fasteners')
    add('remote_radio_moved', 'right-side cooler; radio moved forward',
        {'cooler_and_keyboard_budget': custom, 'battery_and_trackpad': front, 'radio_above_fan': radio_forward}, lid,
        'target; radio RF connector and heatpipe corridor conflict unresolved')
    add('lower_socket', 'right-side cooler + optional lower socket',
        {'cooler_and_keyboard_budget': custom - C['lower_socket_optional_drop'], 'battery_and_trackpad': front, 'radio_above_fan': radio_forward}, lid,
        'target; lower socket compatibility unverified, plus forward-radio conflicts')
    # Separate the panel/support savings from the cooler-layout change.
    hybrid_saved = dict(saved['limiting_deck_heights'])
    hybrid_saved['power_wires_and_guides_under_trackpad'] -= 1.2 + (2.5 - C['trackpad_support']) + (t['under_clearance'] - C['trackpad_under_clearance'])
    hybrid_saved['blower_intake_under_keyboard'] -= 1.2
    hybrid_saved['heatpipe_under_carrier'] -= 1.2 + (4.5 - C['keyboard_carrier'])
    hybrid_fan = dict(hybrid_saved)
    hybrid_fan['blower_intake_under_keyboard'] -= 10.3 - 5.5
    return {'rows': rows, 'hybrid_host_top_H_mm': top, 'CPU_top_H_mm': cpu,
            'battery_envelope_top_H_mm': battery, 'thin_lid_increment_mm': lid,
            'radio_forward_PCB_bottom_H_mm': fan_top + C['remote_fan_upper_intake'] + C['radio_backside_reservation'],
            'fan_envelope_top_H_mm': fan_top,
            'isolated_structure_comparison': {
                'scope': 'arithmetic only: same cooler position and crossing wires, lowered with the 1.2 mm thinner floor and proposed supports; not checked assemblies',
                'saved_cooler_and_thin_structure_limits_mm': hybrid_saved,
                'saved_cooler_and_thin_structure_closed_budget_mm': round(math.ceil(max(hybrid_saved.values()) * 2) / 2 + lid, 3),
                'thin_fan_same_position_and_thin_structure_limits_mm': hybrid_fan,
                'thin_fan_same_position_and_thin_structure_closed_budget_mm': round(math.ceil(max(hybrid_fan.values()) * 2) / 2 + lid, 3)},
            'height_sensitivity': 'each extra mm of cell or trackpad thickness adds one mm to the front stack; each extra mm of panel adds one mm to every closed budget',
            'complete_minimum_established': False}


def polygon_patch(ax, shape, **kwargs):
    shapes = list(shape.geoms) if hasattr(shape, 'geoms') else [shape]
    for p in shapes:
        if p.geom_type == 'Polygon':
            ax.add_patch(PatchPolygon(list(p.exterior.coords), **kwargs))


def plan_axis(ax, title):
    ax.set_facecolor(BG)
    ax.add_patch(Rectangle((-6, -26), 370, 282, fill=False, ec='#333333', lw=1.5))
    for name in ['left', 'center', 'right', 'bms']:
        polygon_patch(ax, outline(name), facecolor='#e1ece4', edgecolor=GREEN, lw=.65)
    for p in PARTS:
        if p['board'] in ['left', 'center', 'right'] and not p['dnp']:
            shape = courtyard(p)
            if shape is not None:
                polygon_patch(ax, shape, facecolor='#688976', edgecolor='none', alpha=.25)
    for x in CONFIG['cells']['x']:
        ax.add_patch(Rectangle((x, 188), 100, 60, fc=GOLD, ec='#876d2e', alpha=.8))
        ax.text(x + 50, 233, '100 × 60 cell', ha='center', fontsize=9)
    ax.add_patch(Rectangle((42.25, 20), 273.5, 80, fc='none', ec='#555555', ls=':', lw=1.1))
    ax.text(44, 24, 'keyboard above', fontsize=8, va='top')
    ax.add_patch(Rectangle((183.3, 10.2), 60, 69.6, fc='#6383a8', alpha=.75))
    ax.text(213.3, 29, 'Mu Ultra', ha='center', fontsize=10, color='white')
    x, y, w, h = DATUMS['CPU_contact_xy_mm']
    ax.add_patch(Rectangle((x, y), w, h, fc='#c0cfdf', ec=BLUE))
    ax.set(xlim=(-12, 373), ylim=(263, -33), aspect='equal', xlabel='X / mm', ylabel='Y / mm')
    ax.set_title(title, loc='left', fontsize=14, fontweight='bold', pad=12)
    ax.tick_params(labelsize=8)


def draw_plans(impact, budget):
    fig, axes = plt.subplots(1, 2, figsize=(17, 8.6), facecolor=BG)
    left, right = axes
    plan_axis(left, 'A / complete Framework reference assembly')
    plan_axis(right, 'B / remote fan and fin reservations')
    data = json.loads((HERE / 'reference/framework-thermal-plan.json').read_text())
    cx, cy = data['pocket_circle_center']
    paths = [[[x - cx + 139, 50 - (y - cy)] for x, y in p] for p in data['paths']]
    left.add_collection(LineCollection(paths, colors='#9b4c24', linewidths=.75))
    left.add_patch(Circle((139, 50), 34, fc='none', ec=RED, lw=1.4, ls='--'))
    left.annotate('sinking this fan into the board:\n' + str(impact['left']['populated_footprints']) + ' populated footprints in the pocket',
                  (118, 72), (8, 106), fontsize=10, arrowprops={'arrowstyle': '->', 'color': RED}, color=RED)
    left.text(8, 138, 'Cooler outline is registered to the fan pocket.\nMu contact alignment and local heights\nare not established by the reference drawing.', fontsize=10, va='top')
    for ax in axes:
        ax.add_patch(Rectangle((286, 110), 70, 120, fc='none', ec='#845693', ls='--', lw=1.1))
    left.text(292, 153, 'radio over\nright cell', fontsize=9, color='#754087')
    left.add_patch(Rectangle((109, 143), 140, 105, fc='#a6bac2', alpha=.2, ec=BLUE, lw=1.5))
    left.text(178, 177, 'trackpad above\ncenter cell', fontsize=10, color=BLUE, ha='center')
    for p in impact['right']['references']:
        actual = next(q for q in PARTS if q['board'] == p['board'] and q['reference'] == p['ref'])
        polygon_patch(right, courtyard(actual), fc=RED, ec='none', alpha=.9)
    polygon_patch(right, pocket('right_pocket'), fc='#99bdd7', ec=BLUE, alpha=.6)
    right.text(309, 146, '68 mm\npocket', ha='center', fontsize=10, color=BLUE)
    x, y, w, h = STUDY['right_fins']
    right.add_patch(Rectangle((x, y), w, h, fc='#bd8354', ec='#733c20'))
    for yy in np.arange(y + 1, y + h, 3):
        right.plot([x, x+w], [yy, yy], color='#733c20', lw=.5)
    right.annotate('', (371, 158), (353, 158), arrowprops={'arrowstyle': '->', 'lw': 2, 'color': '#733c20'})
    right.add_patch(Rectangle((242, 117.5), 120, 70, fc='#a68db2', ec='#704582', alpha=.18, hatch='//'))
    # This line reserves a direction of travel. It is not a manufacturable heatpipe centerline.
    route = np.array([[213, 45], [255, 80], [290, 108], [350, 128]])
    right.plot(route[:,0], route[:,1], color='#a26033', lw=10, alpha=.4, solid_capstyle='round')
    right.plot(route[:,0], route[:,1], color='#804921', lw=1.2, ls='--')
    right.annotate('pipe corridor crosses radio area;\nheight transition still needs designing', (287, 110), (84, 112),
                   fontsize=9, arrowprops={'arrowstyle': '->'}, va='center')
    right.text(237, 202, 'forward radio needs different\nRF exits and service access', fontsize=9, color='#704582', ha='left')
    right.add_patch(Rectangle((99, 143), 140, 105, fc='#a6bac2', alpha=.2, ec=BLUE, lw=1.5))
    right.text(169, 177, 'trackpad shifted\n10 mm left', fontsize=10, color=BLUE, ha='center')
    right.text(15, 145, f"{impact['right']['populated_footprints']} populated footprints\nin the right fan pocket\n\n{impact['right']['center_copper_items']} existing copper items\nintersect the pocket", fontsize=10, color=RED, va='top')
    fig.suptitle('cooling layout comparison / saved board geometry', x=.06, ha='left', fontsize=21, fontweight='bold')
    fig.text(.06, .065, 'Concept reservations only. No PCB, wiring or case changes applied. Both sides of the boards are screened.', fontsize=10)
    fig.text(.06, .036, 'Framework linework adapted from Framework Computer, CC BY 4.0. Fan-pocket alignment is illustrative, not a fitted Mu cooler.', fontsize=9, color='#555555')
    fig.subplots_adjust(top=.88, bottom=.16, left=.055, right=.98, wspace=.13)
    fig.savefig(HERE / 'views/cooling-layouts.png', dpi=145)
    plt.close(fig)


def draw_heights(budget):
    rows = budget['rows']
    fig, (ax, side) = plt.subplots(1, 2, figsize=(15, 8.3), gridspec_kw={'width_ratios': [1.35, 1]}, facecolor=BG)
    names = ['saved printed case', 'thin fan only', 'complete Framework cooler\n+ thin structure', 'remote cooler\nradio over cell', 'remote cooler\nradio moved forward', 'optional lower socket\n+ forward radio']
    for i, row in enumerate(rows):
        value = row['closed_budget_without_feet_mm']
        color = '#727f88' if i < 2 else BLUE
        ax.barh(i, value, height=.60, color=color, alpha=.82, hatch='' if i == 0 else '//')
        ax.text(value+.4, i, f'{value:.1f}', va='center', fontsize=12, fontweight='bold')
    ax.set_yticks(range(len(rows)), names, fontsize=10)
    ax.set(xlim=(0, 50), ylim=(5.6, -.7), xlabel='closed height budget without feet / mm')
    ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True); ax.set_facecolor(BG)
    side.set_facecolor(BG)
    pieces = [
        ('floor', 1.2, '#7b8991'), ('padding', 1, '#d8c992'), ('cell: nominal only', 11, GOLD),
        ('swelling space', 3, '#eadcaf'), ('gap', .5, '#ffffff'), ('thin support', 1, '#7b8991'),
        ('underside gap', .5, '#ffffff'), ('trackpad: assumed', 5, '#719aab'), ('click travel', 1, '#c5dce3')]
    h = 0
    for label, height, color in pieces:
        side.add_patch(Rectangle((0,h), 14, height, fc=color, ec='#666666', lw=.6))
        if height >= 1:
            side.text(15, h+height/2, f'{label}: {height:g}', va='center', fontsize=10)
        h += height
    side.axhline(h, color=RED, ls='--'); side.text(0, h+1, f'{h:.1f} mm to the deck', color=RED, fontsize=12, fontweight='bold')
    side.set(xlim=(-1, 54), ylim=(-.5, 29.5), ylabel='height above case bottom / mm', xticks=[])
    side.set_title('front stack after moving the crossing wires', fontsize=12, loc='left')
    fig.suptitle('what actually limits the thickness', x=.06, ha='left', fontsize=21, fontweight='bold')
    fig.text(.06, .092, 'Hatched bars are conditional budgets, not measured or collision-free assemblies. No thermal rating has been established for either adaptation.', fontsize=10)
    fig.text(.06, .059, 'The thin options also need new panels/supports, harness routes and radio mounting. The 33.3 / 32.8 mm options still have RF and pipe conflicts.', fontsize=10)
    fig.text(.06, .029, 'Cell, trackpad and panel measurements can raise these numbers. The lower socket is not an approved replacement.', fontsize=10)
    fig.subplots_adjust(left=.22, right=.985, bottom=.20, top=.84, wspace=.36)
    fig.savefig(HERE / 'views/thickness-comparison.png', dpi=145)
    plt.close(fig)


def extrude_polygon(poly, h, thickness):
    wire = cq.Wire.makePolygon([cq.Vector(x, -y, h) for x, y in poly.exterior.coords])
    holes = [cq.Wire.makePolygon([cq.Vector(x, -y, h) for x, y in r.coords]) for r in poly.interiors]
    return cq.Solid.extrudeLinear(wire, holes, cq.Vector(0, 0, thickness))


def concept_cad(kind, budget):
    parts = []

    def add(name, shape, color):
        if not shape.isValid():
            raise ValueError('invalid concept solid: '+name)
        parts.append({'name': name, 'shape': shape, 'color': color})

    add('floor-reservation', box(-6,-26,0,370,282,1.2), (.72,.75,.76))
    for name in ['left','center','right','bms']:
        h = CONFIG['boards'][name]['bottom_height'] - 1.2
        shape = outline(name)
        if kind == 'remote' and name == 'center':
            removed = shape.intersection(pocket('right_pocket'))
            add('center-board-material-to-remove', extrude_polygon(removed,h,1.6), (.85,.24,.18,.65))
            shape = shape.difference(pocket('right_pocket'))
        add(name+'-substrate-only', extrude_polygon(shape,h,1.6), (.18,.47,.33))
    for x in CONFIG['cells']['x']:
        add(f'cell-{x}-nominal-body', box(x,188,2.2,100,60,11), (.78,.66,.32))
        add(f'cell-{x}-swelling-space', box(x,188,13.2,100,60,3), (.91,.80,.49,.17))
    module_bottom = budget['hybrid_host_top_H_mm'] + DATUMS['module_model_zero_above_board_mm']
    add('Mu-board-reservation', box(183.3,10.2,module_bottom,60,69.6,1.2), (.18,.32,.5))
    x,y,w,d = DATUMS['CPU_contact_xy_mm']
    add('Mu-CPU-contact-datum', box(x,y,budget['CPU_top_H_mm']-.4,w,d,.4), (.7,.76,.82))
    if kind == 'framework':
        # This deliberate full-height reservation does not pretend to reproduce the formed cooler.
        h = budget['CPU_top_H_mm'] + C['framework_adapter']
        height = STUDY['framework_reference']['drawing_local_height_mm'] + C['framework_height_allowance']
        add('Framework-fan-height-budget', cylinder(139,50,h,32.5,height), (.31,.35,.39))
        add('Framework-fin-height-budget', box(106.5,-1.2,h,64.8,18.06,height), (.65,.38,.20))
        add('Framework-contact-height-budget', box(196,28,h,30,50,height), (.68,.42,.23))
        add('radio-existing-plan-reservation', box(286,110,18.8,70,120,1.6), (.50,.31,.57,.6))
    else:
        h = C['hybrid_floor'] + C['remote_fan_bottom_gap']
        add('remote-fan-body-and-height-allowance', cylinder(309,152,h,32.5,6), (.25,.34,.4))
        add('remote-fan-upper-inlet-space', cylinder(309,152,h+6,32.5,3), (.34,.64,.80,.3))
        add('remote-fin-reservation', box(343,119.6,h,19,64.8,6.54), (.69,.42,.25))
        add('Mu-custom-contact-transport-budget', box(193,30,budget['CPU_top_H_mm'],33,31,6), (.70,.42,.23))
        add('radio-forward-substrate-reservation', box(242,117.5,budget['radio_forward_PCB_bottom_H_mm'],120,70,1.6), (.50,.31,.57,.6))
    out = HERE / 'concepts' / (kind+'-reservations.step')
    export_step(compound(p['shape'] for p in parts), out)
    reopened = cq.importers.importStep(str(out)).val()
    if not reopened.isValid() or len(reopened.Solids()) != sum(len(p['shape'].Solids()) for p in parts):
        raise ValueError('STEP reopen failed')
    render(parts, HERE / 'views' / (kind+'-reservations.png'),
           kind+' / layout reservations only / components and pipe transitions incomplete',
           direction=(1,-1,1.4), size=(1650,1100))
    return {'file': str(out.relative_to(HERE)), 'sha256': sha(out),
            'solids': len(reopened.Solids()), 'reopens': True,
            'scope': 'substrates and named reservations only; not a complete assembly or clearance check',
            'omissions': ['most PCB bodies', 'signal and power harnesses', 'heatpipe formed route',
                          'pad and mounting drills in substrate slabs', 'mounting tabs and fasteners',
                          'deck and lid', 'radio RF terminations'],
            'coordinates': 'X,Y,Z with Z=-H; matches case assembly STEP frame'}


def main():
    before = bound_inputs()
    (HERE/'views').mkdir(exist_ok=True)
    (HERE/'concepts').mkdir(exist_ok=True)
    copper = copper_shapes()
    r = STUDY['radio_forward']; f = STUDY['right_fins']
    screen = {
        'left': impacts(pocket('left_pocket'), copper),
        'right': impacts(pocket('right_pocket'), copper),
        'right_fins': impacts(rect(f[0], f[1], f[0]+f[2], f[1]+f[3]), copper),
        'radio_forward': impacts(rect(r[0], r[1], r[0]+r[2], r[1]+r[3]), copper)
    }
    for name in ['left','right']:
        area = pocket(name+'_pocket')
        screen[name]['center_board_area_removed_mm2'] = round(outline('center').intersection(area).area,3)
        screen[name]['center_board_components_after_cut'] = len(getattr(outline('center').difference(area),'geoms',[None]))
    budget = budgets()
    draw_plans(screen,budget)
    draw_heights(budget)
    cad = [concept_cad(name,budget) for name in ['framework','remote']]
    report = {'date':STUDY['date'], 'source_hashes':before, 'study':STUDY,
              'plan_screen':screen, 'height_budgets':budget, 'cad':cad,
              'saved_design_unchanged':before==bound_inputs(),
              'manufacturing_ready':False, 'complete_fit_verified':False}
    assert report['saved_design_unchanged']
    (HERE/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    with (HERE/'affected-footprints.csv').open('w') as out:
        writer=csv.writer(out);writer.writerow(['reservation','board','reference','side','dnp','value','height_mm','height_status'])
        for key in ['left','right','right_fins','radio_forward']:
            for p in screen[key]['references']:
                writer.writerow([key,p['board'],p['ref'],p['side'],p['dnp'],p['value'],p['height_mm'],p['height_status']])
    print(json.dumps({'populated_footprints':{k:v['populated_footprints'] for k,v in screen.items()},
                      'copper_items':{k:v['center_copper_items'] for k,v in screen.items()},
                      'closed_height_budgets_mm':{r['id']:r['closed_budget_without_feet_mm'] for r in budget['rows']},
                      'cad':cad,'saved_design_unchanged':True},indent=2))


if __name__=='__main__':
    main()

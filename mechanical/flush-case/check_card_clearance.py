"""Screen the saved host component placement against the two M.2 card areas."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PlotPolygon
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PCB = ROOT / 'ducktop2-center.kicad_pcb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_capacitor(python):
    """Read C837's saved Fab rectangle and pad bounds without saving the board."""
    query = '''
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
f = next(f for f in b.GetFootprints() if f.GetReference() == 'C837')
def xy(v): return [pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)]
rects = []
for g in f.GraphicalItems():
    if isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == pcbnew.F_Fab:
        if g.GetShapeStr() == 'Rect': rects.append([xy(g.GetStart()), xy(g.GetEnd())])
pads = [{'number': p.GetNumber(), 'center': xy(p.GetPosition()),
         'size': xy(p.GetSize()), 'rotation': p.GetOrientationDegrees()}
        for p in f.Pads()]
print(json.dumps({'reference': f.GetReference(), 'position': xy(f.GetPosition()),
                  'fab_rectangles': rects, 'pad_boxes': pads}))
'''
    before = sha(PCB)
    result = subprocess.run([python, '-c', query, str(PCB)],
                            capture_output=True, text=True, check=True)
    if sha(PCB) != before:
        raise RuntimeError('The PCB changed during the read-only screen.')
    data = json.loads(result.stdout)
    if len(data['fab_rectangles']) != 1:
        raise ValueError('Inspect C837 again: its saved Fab geometry changed.')
    return data


def draw(cards, front, cap, fab, pads):
    fig, axes = plt.subplots(1, 2, figsize=(16, 4.7),
                             gridspec_kw={'width_ratios': [2.7, 1]})
    fig.patch.set_facecolor('#f3f5f7')
    for ax in axes:
        ax.set_facecolor('#ffffff')
        for part, area in front:
            if part['reference'] in ['J10', 'J40']:
                continue
            for p in getattr(area, 'geoms', [area]):
                ax.add_patch(PlotPolygon(p.exterior.coords, facecolor='#dde3e8',
                                        edgecolor='#81909a', lw=0.5))
        for card, area in cards:
            ax.add_patch(PlotPolygon(area.exterior.coords, facecolor='#c7dced',
                                    edgecolor='#206794', alpha=0.65, lw=1.5))
        ax.add_patch(PlotPolygon(cap.exterior.coords, fill=False,
                                edgecolor='#d97816', lw=2, ls='--'))
        for pad in pads:
            ax.add_patch(PlotPolygon(pad.exterior.coords, facecolor='#77848c',
                                    edgecolor='#37464f', lw=0.6))
        ax.add_patch(PlotPolygon(fab.exterior.coords, facecolor='#a73936',
                                edgecolor='#782a28', lw=1.1))
        ax.set_aspect('equal')
        ax.set_xlabel('installed X (mm)')
        ax.set_ylabel('installed Y (mm)')
        ax.grid(alpha=0.15)
    axes[0].set_xlim(136, 283)
    axes[0].set_ylim(114, 81)
    axes[0].set_title('saved M.2 card spaces and nearby host components', loc='left')
    for card, area in cards:
        x, y, w, h = card['xywh']
        axes[0].text(x + w / 2, y + h / 2, card['name'], ha='center', fontsize=12)
    for part, _ in front:
        if part['reference'] in ['H3', 'H4']:
            axes[0].annotate(part['reference'],
                             (part['installed_x_mm'], part['installed_y_mm']),
                             xytext=(0, 16), textcoords='offset points', ha='center')
    axes[0].annotate('C837', (191.35, 109.516667), xytext=(202, 111.8),
                     ha='center', arrowprops={'arrowstyle': '->'})
    axes[1].set_xlim(188.7, 194)
    axes[1].set_ylim(111.35, 107.6)
    axes[1].set_title('C837 beside the expanded SSD space', loc='left')
    axes[1].text(191.3, 108.35, 'SSD selection space', ha='center', fontsize=10)
    axes[1].text(191.35, 110.85, 'orange: courtyard\nred: nominal Fab body',
                 ha='center', va='center', fontsize=10)
    axes[1].annotate('', (193.15, 108.85), (193.15, fab.bounds[1]),
                     arrowprops={'arrowstyle': '<->', 'lw': 1})
    axes[1].text(193.27, 109.05, '0.27 mm', fontsize=9, rotation=90, va='center')
    fig.text(0.5, 0.035,
             'plan view from the saved PCB and placement data; nominal geometry, not a measured card assembly',
             ha='center', fontsize=11)
    fig.tight_layout(rect=[0, 0.09, 1, 1])
    out = HERE / 'views/m2-card-clearance.png'
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-python', default=
        '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3')
    args = parser.parse_args()
    files = [Path(__file__), PCB, ROOT / 'mechanical/component-placement.json',
             ROOT / 'mechanical/board-placement.json', HERE / 'fan-harness.json']
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in files}
    table = json.loads(files[2].read_text())
    source = table['sources']['boards']['center']
    if source['sha256'] != sha(PCB):
        raise ValueError('Regenerate component placement from the current center PCB first.')
    if table['sources']['board_placement']['sha256'] != sha(files[3]):
        raise ValueError('The installed board placement changed.')
    placement = source['installed_placement']
    if placement['rotation'] != 0 or placement['components'] != 'up':
        raise ValueError('Review the native-to-installed transform.')
    tx, ty = placement['translation']
    front = []
    for p in table['parts']:
        if p['board'] != 'center' or p['side'] != 'front' or p['dnp']:
            continue
        rings = p['courtyards_installed_mm']['front']
        if not rings:
            raise ValueError(p['reference'] + ': missing courtyard')
        area = unary_union([Polygon(r['outer'], r['holes']) for r in rings])
        if not area.is_valid:
            raise ValueError(p['reference'] + ': invalid courtyard')
        front.append((p, area))
    native = native_capacitor(args.kicad_python)
    a, b = native['fab_rectangles'][0]
    fab = box(min(a[0], b[0]) + tx, min(a[1], b[1]) + ty,
              max(a[0], b[0]) + tx, max(a[1], b[1]) + ty)
    pads = []
    for p in native['pad_boxes']:
        w, h = p['size']
        shape = rotate(box(-w / 2, -h / 2, w / 2, h / 2), -p['rotation'], origin=(0, 0))
        pads.append(translate(shape, p['center'][0] + tx, p['center'][1] + ty))
    config = json.loads(files[4].read_text())
    cards, results = [], []
    interfaces = {'NVMe-2280': ['J10', 'H3'], 'WiFi-2230': ['J40', 'H4']}
    for card in config['card_spaces']:
        x, y, w, h = card['xywh']
        area = box(x, y, x + w, y + h)
        cards.append((card, area))
        overlaps = []
        for p, courtyard in front:
            overlap = courtyard.intersection(area).area
            if overlap <= 1e-6:
                continue
            record = {'reference': p['reference'], 'overlap_mm2': round(overlap, 6),
                      'mating_interface': p['reference'] in interfaces[card['name']]}
            if p['reference'] == 'C837':
                record.update(nominal_fab_gap_mm=round(fab.distance(area), 6),
                              pad_bbox_gap_mm=round(min(q.distance(area) for q in pads), 6),
                              nominal_fab_overlap_mm2=round(fab.intersection(area).area, 6),
                              maximum_body_and_assembly_tolerances_verified=False)
            overlaps.append(record)
        results.append({'card': card, 'courtyard_overlaps': overlaps})
    cap = next(area for p, area in front if p['reference'] == 'C837')
    image = draw(cards, front, cap, fab, pads)
    report = {
        'source_hashes': hashes,
        'screened_front_components': len(front),
        'missing_courtyards': [],
        'cards': results,
        'C837_native_geometry': native,
        'scope': 'Static plan screen using saved courtyards and nominal C837 Fab geometry. '
                 'The card boxes are selection limits, not measured modules.',
        'unqualified': ['C837 maximum body and assembly position',
                        'exact SSD and Wi-Fi models, underside parts and board thickness',
                        'socket, 2.5 mm retainer and screw assembly tolerances',
                        'Wi-Fi antenna plugs and lead bends',
                        'card insertion and removal motion'],
        'physical_fit_verified': False,
        'outputs': {str(image.relative_to(HERE)): sha(image)},
    }
    for p, h in hashes.items():
        if sha(ROOT / p) != h:
            raise RuntimeError(p + ': source changed during the screen')
    (HERE / 'm2-card-clearance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'screened_front_components': len(front), 'cards': results}, indent=2))


if __name__ == '__main__':
    main()

"""Bel 0678H land pattern and nominal body from the July 2026 drawing."""

import argparse
from pathlib import Path

from aux_input_contract import FUSE_DATASHEET

ROOT = Path(__file__).resolve().parents[1]


def footprint():
    # Manufacturer page 4: pads 3.81 x 4.06 mm, 5.6 mm between inner edges.
    lines = [
        '(footprint "Bel_0678H_3912" (version 20241229) (generator "pcbnew")',
        '  (layer "F.Cu")',
        '  (descr "Bel 0678H, 9.8 x 3.05 mm; manufacturer recommended land pattern, July 2026")',
        '  (tags "fuse Bel 0678H 3912")',
        '  (attr smd)',
    ]
    for name, value, y, layer, hide in [
        ('Reference', 'REF**', -3.1, 'F.SilkS', ''),
        ('Value', 'Bel_0678H', 3.1, 'F.Fab', ''),
        ('Datasheet', FUSE_DATASHEET, 0, 'F.Fab', '(hide yes)'),
    ]:
        lines.append(f'  (property "{name}" "{value}" (at 0 {y}) (layer "{layer}") {hide} (effects (font (size 1 1) (thickness 0.15))))')
    for x1, y1, x2, y2, width, layer in [
        (-4.9, -1.525, 4.9, 1.525, .1, 'F.Fab'),
        (-6.86, -2.28, 6.86, 2.28, .05, 'F.CrtYd'),
    ]:
        lines.append(f'  (fp_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width {width}) (type default)) (fill none) (layer "{layer}"))')
    for y in [-1.78, 1.78]:
        lines.append(f'  (fp_line (start -2.55 {y}) (end 2.55 {y}) (stroke (width 0.12) (type default)) (layer "F.SilkS"))')
    for number, x in [(1, -4.705), (2, 4.705)]:
        lines.append(f'  (pad "{number}" smd rect (at {x} 0) (size 3.81 4.06) (layers "F.Cu" "F.Paste" "F.Mask"))')
    lines += [
        '  (model "${KIPRJMOD}/ducktop2.3dshapes/Bel_0678H.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))',
        ')',
    ]
    return '\n'.join(lines) + '\n'


def model():
    import cadquery as cq
    # Nominal envelope, not a supplier STEP or internal fuse construction.
    body = cq.Workplane('XY').box(5.74, 2.85, 2.85, centered=(True, True, False)).translate((0, 0, .1))
    cap = cq.Workplane('XY').box(2.03, 3.05, 3.05, centered=(True, True, False))
    assembly = cq.Assembly(name='Bel_0678H_nominal')
    assembly.add(body, name='ceramic', color=cq.Color(.92, .91, .86))
    for name, x in [('end_1', -3.885), ('end_2', 3.885)]:
        assembly.add(cap.translate((x, 0, 0)), name=name, color=cq.Color(.68, .69, .72))
    output = ROOT / 'ducktop2.3dshapes/Bel_0678H.step'
    assembly.save(str(output))
    shape = cq.importers.importStep(str(output)).val()
    assert shape.isValid()
    b = shape.BoundingBox()
    assert abs(b.xlen - 9.8) < 1e-5 and abs(b.ylen - 3.05) < 1e-5 and abs(b.zlen - 3.05) < 1e-5


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', action='store_true')
    args = parser.parse_args()
    (ROOT / 'ducktop2.pretty/Bel_0678H_3912.kicad_mod').write_text(footprint())
    if args.model:
        model()

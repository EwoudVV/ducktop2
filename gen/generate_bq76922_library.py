#!/usr/bin/env python3
"""BQ76922 pin map and TI's RSN0032B land pattern."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASHEET = 'https://www.ti.com/lit/ds/symlink/bq76922.pdf'
FOOTPRINT = 'TI_RSN0032B_WQFN32_4x4mm'

# SLUSE86A, table 5-1 and figure 5-1. Pad 33 follows the EVM ground connection.
# BREG is tied to external REGIN with REG0 disabled, per table 8-3.
PINS = {
    1: ('BAT', 'power_in'), 2: ('VC5', 'input'),
    3: ('VC4A', 'input'), 4: ('VC4B', 'input'),
    5: ('VC3A', 'input'), 6: ('VC3B', 'input'),
    7: ('VC2', 'input'), 8: ('VC1', 'input'),
    9: ('VC0', 'input'), 10: ('VSS', 'power_in'),
    11: ('SRP', 'input'), 12: ('SRN', 'input'),
    13: ('TS1', 'bidirectional'), 14: ('TS2', 'bidirectional'),
    15: ('REG18', 'power_out'), 16: ('ALERT', 'bidirectional'),
    17: ('SCL', 'input'), 18: ('SDA', 'bidirectional'),
    19: ('CFETOFF', 'bidirectional'), 20: ('DFETOFF', 'bidirectional'),
    21: ('RST_SHUT', 'input'), 22: ('REG1', 'power_out'),
    23: ('REGIN', 'power_in'), 24: ('BREG', 'passive'),
    25: ('FUSE', 'bidirectional'), 26: ('PDSG', 'output'),
    27: ('PCHG', 'output'), 28: ('LD', 'input'),
    29: ('PACK', 'input'), 30: ('DSG', 'output'),
    31: ('CHG', 'output'), 32: ('CP1', 'passive'),
    33: ('EP', 'power_in'),
}


def symbol():
    text = ['(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor")',
            '  (symbol "BQ76922RSN" (exclude_from_sim no) (in_bom yes) (on_board yes)']
    for key, value, y, hidden in [
        ('Reference', 'U', 24.13, False), ('Value', 'BQ76922RSN', -24.13, False),
        ('Footprint', f'ducktop2:{FOOTPRINT}', 0, True),
        ('Datasheet', DATASHEET, 0, True),
        ('Description', '3-to-5-cell monitor and protector with high-side FET drivers', 0, True),
    ]:
        text.append(f'    (property "{key}" "{value}" (at 0 {y} 0) '
                    f'{"(hide yes) " if hidden else ""}(effects (font (size 1.27 1.27))))')
    text += ['    (symbol "BQ76922RSN_0_1"',
             '      (rectangle (start -12.7 22.86) (end 12.7 -22.86)',
             '        (stroke (width 0.254) (type default)) (fill (type background))))',
             '    (symbol "BQ76922RSN_1_1"']
    left = list(range(1, 16)) + [33]
    right = list(range(32, 15, -1))
    for numbers, x, angle in [(left, -15.24, 0), (right, 15.24, 180)]:
        for index, number in enumerate(numbers):
            name, kind = PINS[number]
            y = 20.32 - index * 2.54
            text.append(f'      (pin {kind} line (at {x} {y:.2f} {angle}) (length 2.54) '
                        f'(name "{name}" (effects (font (size 1.27 1.27)))) '
                        f'(number "{number}" (effects (font (size 1.27 1.27)))))')
    return '\n'.join(text + ['    )', '  )', ')', ''])


def footprint():
    # TI drawing 4219109/B: 0.55x0.20 pads, 3.85mm opposing pad centers,
    # 0.4mm pitch, 2.8mm exposed pad and four 1.23mm stencil windows.
    text = [f'(footprint "{FOOTPRINT}" (version 20260206)',
            '  (generator "pcbnew") (layer "F.Cu")',
            f'  (descr "TI RSN0032B; SLUSE86A land pattern; {DATASHEET}")',
            '  (attr smd)',
            '  (property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'  (property "Value" "{FOOTPRINT}" (at 0 3 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            '  (fp_rect (start -2 -2) (end 2 2) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
            '  (fp_line (start -2 -1.4) (end -1.4 -2) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
            '  (fp_rect (start -2.45 -2.45) (end 2.45 2.45) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
            '  (fp_circle (center -2.45 -1.9) (end -2.35 -1.9) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))']
    for i in range(32):
        side, offset = divmod(i, 8)
        along = -1.4 + .4 * offset
        x, y, w, h = [(-1.925, along, .55, .2),
                       (along, 1.925, .2, .55),
                       (1.925, -along, .55, .2),
                       (-along, -1.925, .2, .55)][side]
        text.append(f'  (pad "{i+1}" smd roundrect (at {x:.3f} {y:.3f}) (size {w} {h}) '
                    '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    text.append('  (pad "33" smd rect (at 0 0) (size 2.8 2.8) (layers "F.Cu" "F.Mask") (zone_connect 2))')
    for x in (-.715, .715):
        for y in (-.715, .715):
            text.append(f'  (pad "" smd roundrect (at {x} {y}) (size 1.23 1.23) '
                        '(layers "F.Paste") (roundrect_rratio 0.0406504))')
    text += ['  (model "${KIPRJMOD}/../ducktop2.3dshapes/BQ76922_RSN0032B.step"',
             '    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))', ')', '']
    return '\n'.join(text)


def package_model():
    """A package envelope from drawing4219109/B, with the maximum0.8mm height."""
    import cadquery as cq
    body = cq.Workplane('XY').box(4, 4, .75).translate((0, 0, .425))
    mark = cq.Workplane('XY').center(-1.5, -1.5).circle(.12).extrude(.015).translate((0, 0, .785))
    body = body.cut(mark)
    package = cq.Assembly(name='BQ76922_RSN0032B')
    package.add(body, name='body', color=cq.Color(.12, .12, .12))
    metal = cq.Color(.72, .72, .72)
    package.add(cq.Workplane('XY').box(2.8, 2.8, .05).translate((0, 0, .025)),
                name='exposed_pad', color=metal)
    for i in range(32):
        side, offset = divmod(i, 8)
        along = -1.4 + .4 * offset
        x, y, w, h = [(-1.775, along, .45, .2),
                       (along, 1.775, .2, .45),
                       (1.775, -along, .45, .2),
                       (-along, -1.775, .2, .45)][side]
        lead = cq.Workplane('XY').box(w, h, .05).translate((x, y, .025))
        package.add(lead, name=f'pin_{i+1}', color=metal)
    path = ROOT / 'ducktop2.3dshapes/BQ76922_RSN0032B.step'
    package.save(str(path), exportType='STEP')
    shape = cq.importers.importStep(str(path)).val()
    assert shape.isValid(), 'invalid package model'
    bounds = shape.BoundingBox()
    assert abs(bounds.xlen-4) < 1e-6 and abs(bounds.ylen-4) < 1e-6
    assert abs(bounds.zmin) < 1e-6 and abs(bounds.zmax-.8) < 1e-6


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', action='store_true', help='also rebuild the STEP package envelope')
    args = parser.parse_args()
    (ROOT / 'gen/BQ76922.kicad_sym').write_text(symbol())
    (ROOT / 'ducktop2.pretty' / (FOOTPRINT + '.kicad_mod')).write_text(footprint())
    if args.model:
        package_model()

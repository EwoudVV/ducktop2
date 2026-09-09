#!/usr/bin/env python3
"""Molex 503908 lands and signal connector symbols.

Land dimensions: 5039081002 PSD 000 revision A, sheet 2, 2016-08-28.
The body and rule-area outlines are conservative assembly envelopes.
The local origin is the centre of the numbered solder-pad row; the cable
enters from +Y. The shell pads share SH, not a numbered signal contact.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAWING = "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/503/503908/5039085120_sd.pdf"


def footprint_name(count):
    if count not in (41, 51):
        raise ValueError("only the two drawn circuit counts are supported")
    return f"Molex_503908{count}20_1x{count}_P0.50mm_Horizontal"


def pad_rows(count):
    span = .5 * (count - 1)
    rows = [(str(i + 1), -.5 * span + .5 * i, 0, .25, 1.55)
            for i in range(count)]
    # Six front shell tails, including those aligned with contacts 1 and N.
    rows += [("SH", -.5 * span + span * i / 5, 5.05, 1.3, 1.55)
             for i in range(6)]
    # Two rear shell tails and two retention tabs, all electrically common.
    rows += [("SH", sign * (span + 6) / 2, 0, 2.5, 1.55)
             for sign in (-1, 1)]
    rows += [("SH", sign * (span + 9.75 + 2.05) / 2, 3.075, 2.05, 2.5)
             for sign in (-1, 1)]
    return rows


def footprint_text(count):
    name = footprint_name(count)
    span = .5 * (count - 1)
    body_half_width = (span + 12.85 + .3) / 2
    # Includes the full housing, tabs, solder lands and side-lock access.
    courtyard_x = body_half_width + .5
    rows = [f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
            '(attr smd)',
            f'(descr "Molex 503908{count}20; 5039081002 PSD000 A; bottom-contact cable entry +Y; 10 common shell pads")',
            '(property "Reference" "REF**" (at 0 -2) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
            f'(property "Value" "503908{count}20" (at 0 8.8) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))))',
            '(property "Height_Max_mm" "3.9" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))',
            f'(property "Drawing" "{DRAWING}" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))',
            '(property "BodyEnvelope" "conservative; includes locks and tails; reserve side release access" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))',
            f'(fp_rect (start {-body_half_width} -0.8) (end {body_half_width} 7.5) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
            f'(fp_rect (start {-courtyard_x} -1.3) (end {courtyard_x} 8) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
            f'(fp_line (start {-span/2-.3} -1.1) (end {-span/2+.3} -1.1) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))',
            '(fp_text user "cable" (at 0 6.8) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))))']
    for number, x, y, w, h in pad_rows(count):
        rows.append(f'(pad "{number}" smd rect (at {x:g} {y:g}) (size {w:g} {h:g}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    # The drawing prohibits copper beneath the shell, apart from its lands.
    # Enclose the drawn 4.45 mm region with a small positional allowance.
    # Numbered pads break out toward -Y; shell tails break out away from it.
    half = (span + 10.4) / 2 + .05
    rows += ['(zone (net 0) (net_name "") (layer "F.Cu") (hatch edge 0.5)',
             '(name "503908 shell copper exclusion") (connect_pads (clearance 0)) (min_thickness 0.25)',
             '(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))',
             f'(polygon (pts (xy {-half:g} 0.24) (xy {half:g} 0.24) (xy {half:g} 4.8) (xy {-half:g} 4.8))))',
             ')']
    return '\n'.join(rows) + '\n'


def symbol_text(count):
    name = f"Conn_01x{count}_Signal_SH"
    bottom = -(count - 1) * 2.54
    rows = ['(kicad_symbol_lib (version 20251024) (generator "eeschema")',
            f'(symbol "{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
            '(property "Reference" "J" (at 0 5.08 0) (effects (font (size 1.27 1.27))))',
            f'(property "Value" "{name}" (at 0 {bottom-7.62:g} 0) (effects (font (size 1.27 1.27))))',
            f'(property "Footprint" "ducktop2:{footprint_name(count)}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            f'(property "Datasheet" "{DRAWING}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            f'(symbol "{name}_0_1" (rectangle (start -2.54 2.54) (end 2.54 {bottom-5.08:g}) (stroke (width 0.254) (type default)) (fill (type background))))',
            f'(symbol "{name}_1_1"']
    for i in range(count):
        rows.append(f'(pin passive line (at -5.08 {-i*2.54:g} 0) (length 2.54) (name "{i+1}" (effects (font (size 1.27 1.27)))) (number "{i+1}" (effects (font (size 1.27 1.27)))))')
    rows.append(f'(pin passive line (at 5.08 {bottom-2.54:g} 180) (length 2.54) (name "SH" (effects (font (size 1.27 1.27)))) (number "SH" (effects (font (size 1.27 1.27)))))')
    return '\n'.join(rows + [')))']) + '\n'


def main():
    for count in (41, 51):
        (ROOT / 'ducktop2.pretty' / (footprint_name(count) + '.kicad_mod')).write_text(footprint_text(count))
        (ROOT / 'gen' / f'Conn_01x{count}_Signal_SH.kicad_sym').write_text(symbol_text(count))
    for folder, counts in (('', (41, 51)), ('left_io', (41,)), ('right_io', (51,))):
        table = ROOT / folder / 'sym-lib-table'
        text = table.read_text()
        base = '${KIPRJMOD}/' + ('../' if folder else '') + 'gen/'
        for count in counts:
            name = f'Conn_01x{count}_Signal_SH'
            if f'(name "{name}")' in text:
                continue
            entry = f'  (lib (name "{name}") (type "KiCad") (uri "{base}{name}.kicad_sym") (options "") (descr "{count}-contact signal connector with separate shell return"))'
            text = text.replace('  (version 7)', '  (version 7)\n' + entry, 1)
        table.write_text(text)
    print('wrote the 41- and 51-contact signal connector libraries')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""AMASS XT30PW-F30.G.Y lands from specification 2025V0."""
from pathlib import Path
NAME='AMASS_XT30PW-F30_G_Y'
DATASHEET='https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf'

def footprint_text():
    lines=[f'(footprint "{NAME}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
        '(descr "AMASS XT30PW-F30.G.Y, 2025V0; pad 1 negative, pad 2 positive; 1.85/1.15 mm finished holes with +/-0.05 mm tolerance; mated courtyard")',
        '(attr through_hole)',
        '(property "Reference" "REF**" (at 2.5 -23.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        f'(property "Value" "{NAME}" (at 2.5 3) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        '(fp_rect (start -4.45 -14.35) (end 9.45 1.2) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
        '(fp_rect (start -4.7 -22.5) (end 9.7 2.3) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
        '(fp_text user "-" (at -2.5 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        '(fp_text user "+" (at 7.5 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        '(fp_line (start -4.45 -14.35) (end 9.45 -14.35) (stroke (width 0.12) (type default)) (layer "F.SilkS"))']
    for number,x in [('1',0),('2',5)]:
        lines.append(f'(pad "{number}" thru_hole {"rect" if number=="1" else "circle"} (at {x} 0) (size 3.5 3.5) (drill 1.85) (layers "*.Cu" "*.Mask"))')
    for x in [-3,8]:
        lines.append(f'(pad "" thru_hole circle (at {x} -5) (size 2.1 2.1) (drill 1.15) (layers "*.Cu" "*.Mask"))')
    lines.append(')');return '\n'.join(lines)+'\n'

if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'ducktop2.pretty'/f'{NAME}.kicad_mod'
    path.write_text(footprint_text());print(path)

#!/usr/bin/env python3
"""USB5 passive lands from Coilcraft 1735-3 and Panasonic DMM0000COL17.

The VRML files are conservative visual envelopes, not manufacturer CAD models.
They use KiCad's VRML convention of one model unit = 0.1 inch.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def header(name,description,height):
    return [f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
            f'(descr "{description}")','(attr smd)',
            f'(property "Height_Max_mm" "{height}" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))']


def xgl1060_text():
    name='Coilcraft_XGL1060'
    rows=header(name,'Coilcraft XGL1060, document1735-3 2026-02-19; marked short lead is pad1',6.0)
    rows += ['(property "Reference" "REF**" (at 0 -6.9) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
             f'(property "Value" "{name}" (at 0 6.9) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))))',
             '(fp_rect (start -5.25 -5.9) (end 5.25 5.9) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
             '(fp_line (start 4.5 -3.6) (end 4.5 3.6) (stroke (width 0.3) (type solid)) (layer "F.Fab"))',
             '(fp_rect (start -5.4 -6.05) (end 5.4 6.05) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
             '(fp_line (start 5.6 -4) (end 5.6 4) (stroke (width 0.2) (type solid)) (layer "F.SilkS"))',
             '(fp_rect (start -5.75 -6.3) (end 5.75 6.3) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))']
    for number,x in [(1,3.325),(2,-3.325)]:
        rows.append(f'(pad "{number}" smd rect (at {x} 0) (size 2.38 8.5) (layers "F.Cu" "F.Paste" "F.Mask"))')
    rows.append('(model "${KIPRJMOD}/../ducktop2.3dshapes/coilcraft_xgl1060_envelope.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    return '\n'.join(rows+[')'])+'\n'


def xgl6030_text():
    name='Coilcraft_XGL6030'
    rows=header(name,'Coilcraft1635-1 2026-02-19; drawing rotated so marked short lead is pad1; maximum body6.71x6.91x3.1mm',3.1)
    rows += ['(property "Reference" "REF**" (at 0 -4.5) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
             f'(property "Value" "{name}" (at 0 4.5) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))))',
             '(fp_rect (start -3.355 -3.455) (end 3.355 3.455) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
             '(fp_line (start -3 -2) (end -3 2) (stroke (width 0.2) (type solid)) (layer "F.Fab"))',
             '(fp_rect (start -3.5 -3.6) (end 3.5 3.6) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
             '(fp_line (start -3.5 -2) (end -3.5 2) (stroke (width 0.2) (type solid)) (layer "F.SilkS"))',
             '(fp_rect (start -3.65 -3.75) (end 3.65 3.75) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))']
    for number,x in [(1,-2.02),(2,2.02)]:
        rows.append(f'(pad "{number}" smd rect (at {x} 0) (size 1.43 5.5) (layers "F.Cu" "F.Paste" "F.Mask"))')
    rows.append('(model "${KIPRJMOD}/ducktop2.3dshapes/coilcraft_xgl6030_envelope.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    return '\n'.join(rows+[')'])+'\n'


def erj8cw_text():
    name='Panasonic_ERJ8CW_10to16m'
    rows=header(name,'Panasonic ERJ8CW 10..16mOhm; DMM0000COL17 2025-12-24; a1.2mm b4.7mm c1.8mm',.75)
    rows += ['(property "Reference" "REF**" (at 0 -1.8) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.1))))',
             f'(property "Value" "{name}" (at 0 1.8) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))',
             '(fp_rect (start -1.7 -0.9) (end 1.7 0.9) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
             '(fp_line (start -0.25 -1.05) (end 0.25 -1.05) (stroke (width 0.1) (type solid)) (layer "F.SilkS"))',
             '(fp_line (start -0.25 1.05) (end 0.25 1.05) (stroke (width 0.1) (type solid)) (layer "F.SilkS"))',
             '(fp_rect (start -2.65 -1.2) (end 2.65 1.2) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))']
    for number,x in [(1,-1.475),(2,1.475)]:
        rows.append(f'(pad "{number}" smd rect (at {x} 0) (size 1.75 1.8) (layers "F.Cu" "F.Paste" "F.Mask"))')
    rows.append('(model "${KIPRJMOD}/../ducktop2.3dshapes/panasonic_erj8cw_envelope.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    return '\n'.join(rows+[')'])+'\n'


def envelope(width,length,height):
    return ('#VRML V2.0 utf8\n# conservative maximum envelope, dimensions from manufacturer drawing\n'
            f'Transform {{ translation 0 0 {height/5.08:.8f} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor 0.16 0.17 0.18 }} }} geometry Box {{ size {width/2.54:.8f} {length/2.54:.8f} {height/2.54:.8f} }} }} ] }}\n')


if __name__=='__main__':
    (ROOT/'ducktop2.pretty/Coilcraft_XGL1060.kicad_mod').write_text(xgl1060_text())
    (ROOT/'ducktop2.pretty/Coilcraft_XGL1060_Center.kicad_mod').write_text(xgl1060_text().replace('Coilcraft_XGL1060','Coilcraft_XGL1060_Center').replace('${KIPRJMOD}/../','${KIPRJMOD}/'))
    (ROOT/'ducktop2.pretty/Panasonic_ERJ8CW_10to16m_Center.kicad_mod').write_text(erj8cw_text().replace('Panasonic_ERJ8CW_10to16m','Panasonic_ERJ8CW_10to16m_Center').replace('${KIPRJMOD}/../','${KIPRJMOD}/'))
    (ROOT/'ducktop2.pretty/Coilcraft_XGL6030.kicad_mod').write_text(xgl6030_text())
    (ROOT/'ducktop2.3dshapes/coilcraft_xgl6030_envelope.wrl').write_text(envelope(6.71,6.91,3.1))
    (ROOT/'ducktop2.pretty/Panasonic_ERJ8CW_10to16m.kicad_mod').write_text(erj8cw_text())
    (ROOT/'ducktop2.3dshapes/coilcraft_xgl1060_envelope.wrl').write_text(envelope(10.5,11.8,6))
    (ROOT/'ducktop2.3dshapes/panasonic_erj8cw_envelope.wrl').write_text(envelope(3.4,1.8,.75))

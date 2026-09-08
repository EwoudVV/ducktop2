#!/usr/bin/env python3
"""Build the LM706A0 symbol and TI RRX0029B copper/mask/paste pattern.

Source: TI drawing 4228757/D, 04/2024, in the LM706x0 datasheet.
The JSON retains the separately drawn copper-under-mask, exposed metal and
0.125mm stencil apertures. Via locations remain the board designer's choice.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
NAME = "Texas_RRX0029B_VQFN-29_6x6mm"
DATA = Path(__file__).with_name("lm706a0_rrx0029b.json")
PIN_NAMES = {
    1:"VIN4", 2:"VIN5", 3:"VIN6", 4:"CBOOT", 5:"SW4", 6:"BIAS",
    7:"PG/SYNCOUT", 8:"PFM/SYNCIN", 9:"EN/UVLO", 10:"NC", 11:"ISNS+",
    12:"VOUT", 13:"CONFIG", 14:"RT", 15:"EXTCOMP", 16:"FB", 17:"AGND",
    18:"VDDA", 19:"VCC", 20:"SW1", 21:"SW2", 22:"SW3", 23:"PGND1",
    24:"PGND2", 25:"PGND3", 26:"PGND4", 27:"VIN1", 28:"VIN2",
    29:"VIN3", 30:"PGND",
}
PIN_CENTERS = {
    **{n:(-2.9,y) for n,y in enumerate([-2.25,-1.75,-1.25,-.25,.25,1.25,1.75,2.25],1)},
    **{n:(x,2.9) for n,x in enumerate([-2,-1.5,-1,0,.5,1,1.5,2],9)},
    **{n:(2.9,y) for n,y in enumerate([1.75,1.25,.75,-.75,-1.25,-1.75],17)},
    **{n:(x,-2.9) for n,x in enumerate([2,1.5,1,.5,-1,-1.5,-2],23)},
    30:(.0375,1.308),
}


def points_text(points):
    return " ".join(f"(xy {x:.5f} {y:.5f})" for x,y in points)


def polygon(layer, points):
    return f'(fp_poly (pts {points_text(points)}) (stroke (width 0) (type solid)) (fill solid) (layer "{layer}"))'


def custom_copper(number, anchor, points):
    local=[(x-anchor[0],y-anchor[1]) for x,y in points]
    return (f'(pad "{number}" smd custom (at {anchor[0]} {anchor[1]}) (size 0.1 0.1) '
            '(layers "F.Cu") (options (clearance outline) (anchor rect)) '
            f'(primitives (gr_poly (pts {points_text(local)}) (width 0) (fill yes))))')


def footprint_text():
    data=json.loads(DATA.read_text())
    validate_geometry(data)
    rows=[f'(footprint "{NAME}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
          '(descr "TI RRX0029B, drawing 4228757/D 04/2024; separate mask-defined VIN/SW lands and 0.125mm stencil example")',
          '(tags "LM706A0 LM70660 RRX0029B 6x6")',
          '(property "Reference" "REF**" (at 0 -4.1) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
          f'(property "Value" "{NAME}" (at 0 4.1) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
          '(property "Height_Max_mm" "1.0" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))',
          '(attr smd)',
          '(fp_rect (start -3 -3) (end 3 3) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
          '(fp_line (start -3 -2.3) (end -2.3 -3) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
          '(fp_line (start -3.55 -3.2) (end -3.55 -3.55) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
          '(fp_line (start -3.55 -3.55) (end -3.2 -3.55) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
          '(fp_rect (start -3.6 -3.6) (end 3.6 3.6) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))']
    # Array order in the source data is SW, VIN. Mask openings are exact
    # exposed-metal shapes; the larger copper remains covered between fingers.
    rows.append(custom_copper(20,(1.3,-1.1),data['copper_under_mask'][0]))
    rows.append(custom_copper(1,(-1.5,-1.8),data['copper_under_mask'][1]))
    for points in data['exposed_mask']:
        rows.append(polygon('F.Mask',points))
    shared={1,2,20,21,22,27,28,29}
    for number,(x,y) in PIN_CENTERS.items():
        if number in (1,20):
            continue
        if number in shared:
            # Electrical aliases inside a common die-attach land. These do not
            # add mask or paste and cannot change its exterior geometry.
            rows.append(f'(pad "{number}" smd rect (at {x} {y}) (size 0.1 0.1) (layers "F.Cu"))')
        elif number==30:
            rows.append(f'(pad "30" smd roundrect (at {x} {y}) (size 3.125 1.584) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.03156566) (solder_mask_margin 0.07))')
        else:
            width,height=(.6,.25) if number<=8 or 17<=number<=22 else (.25,.6)
            rows.append(f'(pad "{number}" smd roundrect (at {x} {y}) (size {width} {height}) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.2) (solder_mask_margin 0.07))')
    for points in data['paste']:
        rows.append(polygon('F.Paste',points))
    return '\n'.join(rows+[')'])+'\n'


def validate_geometry(data):
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for layer in ('copper_under_mask','exposed_mask','paste'):
        for index,poly in enumerate(data[layer]):
            edges=list(zip(poly,poly[1:]+poly[:1]))
            for i,(a,b) in enumerate(edges):
                for j,(c,d) in enumerate(edges):
                    if j<=i+1 or (i==0 and j==len(edges)-1):
                        continue
                    if cross(a,b,c)*cross(a,b,d)<-1e-15 and cross(c,d,a)*cross(c,d,b)<-1e-15:
                        raise ValueError(f"self-crossing {layer} polygon {index}: edges {i}/{j}")


def symbol_text():
    rows=['(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor")',
          '(symbol "LM706A0" (exclude_from_sim no) (in_bom yes) (on_board yes)',
          '(property "Reference" "U" (at 0 22.86 0) (effects (font (size 1.27 1.27))))',
          '(property "Value" "LM706A0" (at 0 20.32 0) (effects (font (size 1.27 1.27))))',
          f'(property "Footprint" "ducktop2:{NAME}" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))',
          '(property "Datasheet" "https://www.ti.com/lit/gpn/LM706A0" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))',
          '(symbol "LM706A0_0_1" (rectangle (start -10.16 19.05) (end 10.16 -19.05) (stroke (width 0.254) (type default)) (fill (type background))))',
          '(symbol "LM706A0_1_1"']
    power_in={1,2,3,6,17,23,24,25,26,27,28,29,30}
    power_out={4,5,18,19,20}
    for number,name in PIN_NAMES.items():
        side=number>15
        x=12.7 if side else -12.7
        y=17.78-2.54*((number-1)%15)
        angle=180 if side else 0
        kind=('power_in' if number in power_in else 'power_out' if number in power_out
              else 'open_collector' if number==7 else 'no_connect' if number==10
              else 'output' if number==15 else 'passive' if number in (21,22) else 'input')
        rows.append(f'(pin {kind} line (at {x} {y:.2f} {angle}) (length 2.54) '
                    f'(name "{name}" (effects (font (size 1.0 1.0)))) '
                    f'(number "{number}" (effects (font (size 1.0 1.0)))))')
    return '\n'.join(rows+[')',')',')'])+'\n'


def shunt_footprint_text():
    # Vishay document 30100, 23-Nov-2023, page 2: WSL2010 1..6.9mohm.
    # Pad a=2.36mm, b=3.05mm, inner gap l=1.40mm.
    name="Vishay_WSL2010_1to6m9"
    rows=[f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
          '(descr "Vishay WSL2010 1 to 6.9mOhm, document30100 23-Nov-2023; 2.36x3.05mm lands, 1.40mm gap")',
          '(property "Reference" "REF**" (at 0 -2.3) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
          f'(property "Value" "{name}" (at 0 2.15) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
          '(attr smd)',
          '(fp_rect (start -2.54 -1.27) (end 2.54 1.27) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
          '(fp_line (start -0.35 -1.4) (end 0.35 -1.4) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
          '(fp_line (start -0.35 1.4) (end 0.35 1.4) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
          '(fp_rect (start -3.35 -1.8) (end 3.35 1.8) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))']
    for number,x in [(1,-1.88),(2,1.88)]:
        rows.append(f'(pad "{number}" smd rect (at {x} 0) (size 2.36 3.05) (layers "F.Cu" "F.Paste" "F.Mask"))')
    return '\n'.join(rows+[')'])+'\n'


def main():
    (ROOT/'ducktop2.pretty'/f'{NAME}.kicad_mod').write_text(footprint_text())
    (ROOT/'gen/LM706A0.kicad_sym').write_text(symbol_text())
    (ROOT/'ducktop2.pretty/Vishay_WSL2010_1to6m9.kicad_mod').write_text(shunt_footprint_text())


if __name__=='__main__':
    main()

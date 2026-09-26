#!/usr/bin/env python3
"""Low-profile power terminals and the pack fuse, from their land drawings."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def text_property(name,value,x,y,layer='F.Fab'):
    return f'(property "{name}" "{value}" (at {x} {y}) (layer "{layer}") (hide yes) (effects (font (size 1 1) (thickness 0.15))))'

def wago_2060(poles):
    if poles not in (1,2,3):raise ValueError('2060 has one, two or three poles')
    name=f'WAGO_2060_{450+poles}_SMD';width=poles*4-.1
    out=[f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
         '(descr "WAGO 2060: 4 mm pitch, 4.5 mm height; two solder contacts per potential. 150 um stencil per drawing.")',
         '(attr smd)','(duplicate_pad_numbers_are_jumpers yes)',text_property('Reference','REF**',0,-8,'F.SilkS'),text_property('Value',name,0,10),
         f'(fp_rect (start {-width/2} -6.55) (end {width/2} 6.55) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
         f'(fp_rect (start {-width/2-.3} -6.85) (end {width/2+.3} 8.85) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
         f'(fp_line (start {-width/2} -6.55) (end {width/2} -6.55) (stroke (width 0.12) (type default)) (layer "F.SilkS"))']
    for i in range(poles):
        x=(i-(poles-1)/2)*4
        # Recommended lands: 6 x 2 mm and 3.5 x 2 mm, 14 mm overall.
        # The forward 4 mm contact is centered on its land. Both stamped
        # contacts remain inside the manufacturer-sized lands.
        for y,length in [(-2.45,6.0),(6.8,3.5)]:
            out.append(f'(pad "{i+1}" smd rect (at {x} {y}) (size 2 {length}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(')');return '\n'.join(out)+'\n'

def hcf():
    name='Schurter_HCF_8.05x5mm'
    out=[f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
         '(descr "Schurter HCF: 8.05 x 5 x 5 mm; 4.2 x 7.5 mm lands with 3.8 mm inner gap.")',
         '(attr smd)',text_property('Reference','REF**',0,-5,'F.SilkS'),text_property('Value',name,0,5),
         '(fp_rect (start -4.025 -2.5) (end 4.025 2.5) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
         '(fp_rect (start -6.4 -4.05) (end 6.4 4.05) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
    for n,x in [(1,-4),(2,4)]:out.append(f'(pad "{n}" smd rect (at {x} 0) (size 4.2 7.5) (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(')');return '\n'.join(out)+'\n'

def main():
    for n in (1,2,3):(ROOT/f'ducktop2.pretty/WAGO_2060_{450+n}_SMD.kicad_mod').write_text(wago_2060(n))
    (ROOT/'ducktop2.pretty/Schurter_HCF_8.05x5mm.kicad_mod').write_text(hcf())
    print('wrote three terminal footprints and the HCF fuse footprint')
if __name__=='__main__':main()

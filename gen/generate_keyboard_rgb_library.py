#!/usr/bin/env python3
"""Keyboard RGB symbols and the two manufacturer land patterns."""
from pathlib import Path
from generate_bms_thermal_library import symbol_text
from keyboard_rgb_contract import *

ROOT = Path(__file__).resolve().parents[1]


def symbols():
    driver_names = {pin:net.removeprefix('RGB_') if net else '' for pin,net in DRIVER_PINS.items()}
    for pin, name in {5:'PVCC',22:'VCC',16:'PGND',23:'GND',41:'EP',
                      24:'ADDR2',25:'ADDR1',26:'SDB',27:'SCL',28:'SDA',
                      29:'ISET',30:'SYNC'}.items():
        driver_names[pin] = name
    specs = {
        'LED_19_337_C02': {'reference':'LED', 'footprint':LED_FOOTPRINT, 'url':LED_DATASHEET,
            'pins':[(n,name,'passive') for n,name in [(1,'B_A'),(3,'R_A'),(5,'G_A'),
                                                    (2,'B_K'),(4,'R_K'),(6,'G_K')]]},
        'IS31FL3743A': {'footprint':DRIVER_FOOTPRINT, 'url':DRIVER_DATASHEET,
            'pins':[(pin,driver_names[pin],
                     'power_in' if pin in (5,16,22,23,41) else
                     'bidirectional' if pin in (28,30) else
                     'input' if pin in (24,25,26,27) else
                     'passive' if pin == 29 else 'output') for pin in range(1,42)]},
        'TCA9517A': {'footprint':BUFFER_FOOTPRINT, 'url':BUFFER_DATASHEET,
            'pins':[(1,'VCCA','power_in'),(2,'SCLA','bidirectional'),(3,'SDAA','bidirectional'),
                    (4,'GND','power_in'),(5,'EN','input'),(6,'SDAB','bidirectional'),
                    (7,'SCLB','bidirectional'),(8,'VCCB','power_in')]},
    }
    return '(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor")\n' + \
           '\n'.join(symbol_text(n,s) for n,s in specs.items()) + '\n)\n'


def header(name, description):
    return [f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
            f'  (descr "{description}") (attr smd)',
            '  (fp_text reference "REF**" (at 0 -4) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.15))))',
            f'  (fp_text value "{name}" (at 0 4) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))']


def rect(x0,y0,x1,y1,layer,width=.05):
    return f'  (fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width {width}) (type solid)) (fill none) (layer "{layer}"))'


def pad(n,x,y,w,h,layers='F.Cu F.Paste F.Mask',mask=None):
    ls = ' '.join('"'+l+'"' for l in layers.split())
    extra='' if mask is None else f' (solder_mask_margin {mask})'
    return f'  (pad "{n}" smd rect (at {x} {y}) (size {w} {h}) (layers {ls}){extra})'


def led_footprint():
    lines=header('LED_Everlight_19-337_1616',
                 'Everlight 19-337/R6GHBHC-C02/2T; DSE-0002659 rev 4; top view B 1A/2K, R 3A/4K, G 5A/6K')
    lines += [rect(-.8,-.8,.8,.8,'F.Fab'),rect(-1.35,-1.175,1.35,1.175,'F.CrtYd')]
    lines += [pad(1,.675,-.725,.55,.4),pad(2,-.675,-.725,.55,.4),
              pad(3,.75,0,.7,.5),pad(4,-.75,0,.7,.5),
              pad(5,.675,.725,.55,.4),pad(6,-.675,.725,.55,.4)]
    lines += ['  (fp_line (start 0.4 -0.8) (end 0.8 -0.4) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
              '  (model "${KIPRJMOD}/../mechanical/models/keyboard-rgb-led.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))',')']
    return '\n'.join(lines)+'\n'


def driver_footprint():
    lines=header('IS31FL3743A_UQFN40',
                 'Lumissil IS31FL3743A UQFN40; rev C page 22 lands, 0.22 x 0.715 mm, 3.4 mm exposed pad')
    lines += [rect(-2.5,-2.5,2.5,2.5,'F.Fab'),rect(-3.03,-3.03,3.03,3.03,'F.CrtYd')]
    for i in range(10):
        v=round(-1.8+.4*i,4)
        lines += [pad(i+1,-2.4075,v,.715,.22,mask=.04),pad(i+11,v,2.4075,.22,.715,mask=.04),
                  pad(i+21,2.4075,-v,.715,.22,mask=.04),pad(i+31,-v,-2.4075,.22,.715,mask=.04)]
    lines.append(pad(41,0,0,3.4,3.4,'F.Cu F.Mask'))
    for x in (-.9,.9):
        for y in (-.9,.9):
            lines.append(pad('',x,y,1.4,1.4,'F.Paste'))
    lines += ['  (fp_line (start -2.5 -1.9) (end -1.9 -2.5) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
              '  (fp_circle (center -2.9 -2.9) (end -2.75 -2.9) (stroke (width 0.15) (type solid)) (fill solid) (layer "F.SilkS"))',
              '  (model "${KIPRJMOD}/../mechanical/models/keyboard-rgb-driver.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))',')']
    return '\n'.join(lines)+'\n'


def box_model(x,y,h,color):
    # KiCad VRML coordinates use 0.1 inch units.
    return ('#VRML V2.0 utf8\nTransform { translation 0 0 %.8f children [ Shape { '
            'appearance Appearance { material Material { diffuseColor %s } } '
            'geometry Box { size %.8f %.8f %.8f } } ] }\n') % \
            ((h/2+.025)/2.54,color,x/2.54,y/2.54,h/2.54)


def main():
    (ROOT/'gen/Keyboard_RGB.kicad_sym').write_text(symbols())
    (ROOT/'ducktop2.pretty/LED_Everlight_19-337_1616.kicad_mod').write_text(led_footprint())
    (ROOT/'ducktop2.pretty/IS31FL3743A_UQFN40.kicad_mod').write_text(driver_footprint())
    out=ROOT/'mechanical/models';out.mkdir(exist_ok=True)
    (out/'keyboard-rgb-led.wrl').write_text(box_model(1.6,1.6,.35,'0.85 0.85 0.80'))
    (out/'keyboard-rgb-driver.wrl').write_text(box_model(5,5,.55,'0.15 0.15 0.15'))


if __name__=='__main__':
    main()

"""Power-stage symbols and land patterns, from the manufacturer drawings."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]

ISL9241_PINS = [
    ('CSON', 'input'), ('CSOP', 'input'), ('NGATE', 'output'),
    ('BOOT2', 'passive'), ('UGATE2', 'output'), ('PHASE2', 'passive'),
    ('LGATE2', 'output'), ('VDDP', 'power_in'), ('LGATE1', 'output'),
    ('PHASE1', 'passive'), ('UGATE1', 'output'), ('BOOT1', 'passive'),
    ('BYPSRC', 'passive'), ('CSIN', 'input'), ('CSIP', 'input'),
    ('BYPSG', 'output'), ('DCIN', 'power_in'), ('VDD', 'power_out'),
    ('PROG', 'input'), ('OTGEN/CMIN', 'input'), ('SDA', 'bidirectional'),
    ('SCL', 'input'), ('~{PROCHOT}', 'open_collector'), ('ACOK', 'open_collector'),
    ('BATGONE/NTC', 'input'), ('CMOUT/~{INT}', 'open_collector'),
    ('COMPR', 'passive'), ('COMPF', 'passive'), ('AMON/BMON', 'output'),
    ('PSYS', 'output'), ('VBAT', 'input'), ('BGATE', 'output'), ('GND', 'power_in'),
]
TPS552882_PINS = [
    ('DR1L', 'output'), ('DR1H', 'output'), ('VIN', 'power_in'),
    ('EN/UVLO', 'input'), ('PG', 'open_collector'), ('~{CC}', 'open_collector'),
    ('DITH/SYNC', 'input'), ('FSW', 'input'), ('PGND', 'power_in'),
    ('AGND', 'power_in'), ('VOUT', 'power_out'), ('ISP', 'input'),
    ('ISN', 'input'), ('FB', 'input'), ('MODE', 'input'), ('CDC', 'passive'),
    ('ILIM', 'input'), ('COMP', 'passive'), ('VCC', 'power_out'),
    ('BOOT2', 'passive'), ('SW2', 'power_out'), ('BOOT1', 'passive'),
    ('SW1', 'passive'), ('PGND', 'power_in'), ('SW2', 'passive'), ('VOUT', 'passive'),
]
TPS25982_PINS = [
    ('IN','power_in'),('IN','passive'),('IN','passive'),('GND','power_in'),
    ('GND','passive'),('EN/UVLO','input'),('ITIMER','passive'),('ILIM','passive'),
    ('IMON','output'),('RETRY_DLY','passive'),('NRETRY','passive'),('LDSTRT','input'),
    ('PG','open_collector'),('GND','passive'),('dVdt','passive'),('IN','passive'),
    *[('OUT','power_out' if n==17 else 'passive') for n in range(17,25)],
    ('IN','passive'),('GND','passive'),
]
TPS3700_PINS = [('OUTA','open_collector'),('GND','power_in'),('INA+','input'),
                ('INB-','input'),('VDD','power_in'),('OUTB','open_collector')]


def symbol(name, pins, footprint, datasheet):
    rows = (len(pins) + 1) // 2
    height = rows * 1.27
    body = [f'(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor")',
            f'(symbol "{name}" (in_bom yes) (on_board yes)',
            f'(property "Reference" "U" (at 0 {height+3.81} 0) (effects (font (size 1.27 1.27))))',
            f'(property "Value" "{name}" (at 0 {height+1.27} 0) (effects (font (size 1.27 1.27))))',
            f'(property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
            f'(property "Datasheet" "{datasheet}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
            f'(symbol "{name}_0_1" (rectangle (start -10.16 {height}) (end 10.16 {-height})',
            '(stroke (width 0.254) (type default)) (fill (type background))))',
            f'(symbol "{name}_1_1"']
    for n, (label, kind) in enumerate(pins, 1):
        left = n <= rows
        row = n-1 if left else n-1-rows
        x, angle = (-12.7, 0) if left else (12.7, 180)
        y = height-1.27-row*2.54
        body.append(f'(pin {kind} line (at {x} {y:.4f} {angle}) (length 2.54) '
                    f'(name "{label}" (effects (font (size 1.016 1.016)))) '
                    f'(number "{n}" (effects (font (size 1.016 1.016)))))')
    return '\n'.join(body+[')))', ''])


def isl9241_footprint():
    name = 'Renesas_L32_4x4D_QFN32_EP2.7'
    text = [f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
            '(descr "Renesas L32.4x4D / QW0032AA Rev04; 4x4 mm, 0.4 mm pitch, 2.7 mm exposed pad")',
            '(attr smd)',
            '(property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
            f'(property "Value" "{name}" (at 0 3 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
            '(fp_rect (start -2 -2) (end 2 2) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
            '(fp_rect (start -2.4 -2.4) (end 2.4 2.4) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
            '(fp_circle (center -2.35 -1.85) (end -2.25 -1.85) (stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS"))']
    # QW0032AA: outer span 4.30, inner span 3.40, lands 0.45 x 0.20.
    for n in range(1, 33):
        side, slot = divmod(n-1, 8)
        v = -1.4 + slot*0.4
        x,y,w,h = [(-1.925,v,.45,.20),(v,1.925,.20,.45),
                   (1.925,-v,.45,.20),(-v,-1.925,.20,.45)][side]
        text.append(f'(pad "{n}" smd roundrect (at {x:.4f} {y:.4f}) (size {w} {h}) '
                    '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.2))')
    text.append('(pad "33" smd rect (at 0 0) (size 2.7 2.7) (layers "F.Cu" "F.Mask"))')
    for x in (-.7, .7):
        for y in (-.7, .7):
            text.append(f'(pad "" smd rect (at {x} {y}) (size 1.1 1.1) (layers "F.Paste"))')
    text.append(')')
    return name, '\n'.join(text)+'\n'


def rounded_polygon(vertices, radius=.05):
    result=[]
    for i,p in enumerate(vertices):
        before,after=vertices[i-1],vertices[(i+1)%len(vertices)]
        a=(p[0]-before[0],p[1]-before[1]);b=(after[0]-p[0],after[1]-p[1])
        al,bl=math.hypot(*a),math.hypot(*b)
        a=(a[0]/al,a[1]/al);b=(b[0]/bl,b[1]/bl)
        start=(p[0]-a[0]*radius,p[1]-a[1]*radius)
        center=(start[0]+b[0]*radius,start[1]+b[1]*radius)
        angle=math.atan2(start[1]-center[1],start[0]-center[0])
        turn=1 if a[0]*b[1]-a[1]*b[0]>0 else -1
        for n in range(9):
            t=angle+turn*n*math.pi/16
            result.append((center[0]+radius*math.cos(t),center[1]+radius*math.sin(t)))
    return result


def tps552882_footprint():
    name='Texas_RPM0026A_VQFN-HR26_4x3.5'
    text=[f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
          '(descr "TI RPM0026A, drawing 4224618/A 10/2018; three separate exposed lands")',
          '(attr smd)',
          '(property "Reference" "REF**" (at 0 -2.8 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
          f'(property "Value" "{name}" (at 0 2.8 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
          '(fp_rect (start -2 -1.75) (end 2 1.75) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
          '(fp_rect (start -2.5 -2.2) (end 2.5 2.2) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
          '(fp_circle (center -2.3 -1.9) (end -2.2 -1.9) (stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS"))']
    def pad(n,x,y,w,h):
        text.append(f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) '
                    f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio {min(.05/min(w,h),.25):.6f}))')
    for n,y in ((2,-1),(3,-.5),(4,0),(5,.5),(6,1)):
        small=n in (2,6)
        pad(n,-1.9 if small else -1.8375,y,.6 if small else .725,.25)
    for n,y in ((14,1),(15,.5),(16,0),(17,-.5),(18,-1)):
        small=n in (14,18)
        pad(n,1.9 if small else 1.8375,y,.6 if small else .725,.25)
    for n,x in ((8,-1.125),(9,-.625),(10,-.125),(11,.625),(12,1.125)):
        pad(n,x,1.6375,.25,.625)
    for n,x,y,h in ((20,1.05,-1.6125,.675),(21,.25,-1.65,.6),
                    (22,-.25,-1.65,.6),(23,-1.05,-1.6125,.675)):
        pad(n,x,y,.25,h)
    for n,x in ((24,-.625),(25,0),(26,.625)):
        pad(n,x,0,.375,1.425)
    top=[(-2.2,-1.6),(-1.825,-1.6),(-1.825,-1.95),
         (-1.425,-1.95),(-1.425,-1.375),(-2.2,-1.375)]
    bottom=[(-2.2,1.375),(-1.5,1.375),(-1.5,1.95),
            (-1.85,1.95),(-1.85,1.6),(-2.2,1.6)]
    for n,vertices,mirror,anchor in ((1,top,1,(-1.625,-1.4875)),
         (19,top,-1,(1.625,-1.4875)),(7,bottom,1,(-1.675,1.4875)),
         (13,bottom,-1,(1.675,1.4875))):
        pts=rounded_polygon(vertices)
        coords=' '.join(f'(xy {mirror*x-anchor[0]:.5f} {y-anchor[1]:.5f})' for x,y in pts)
        text.append(f'(pad "{n}" smd custom (at {anchor[0]} {anchor[1]}) (size .1 .1) '
                    '(layers "F.Cu" "F.Paste" "F.Mask") '
                    '(options (clearance outline) (anchor rect)) '
                    f'(primitives (gr_poly (pts {coords}) (width 0) (fill yes))))')
    text.append(')')
    return name,'\n'.join(text)+'\n'


def tps25982_footprint():
    name='Texas_RGE0024M_QFN24_4x4_2EP'
    text=[f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu")',
          '(descr "TI RGE0024M 4223975/B 03/2018. Exposed pad 25 is IN; pad 26 is GND.")',
          '(attr smd)',
          '(property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
          f'(property "Value" "{name}" (at 0 3 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
          '(fp_rect (start -2 -2) (end 2 2) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
          '(fp_rect (start -2.5 -2.5) (end 2.5 2.5) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
          '(fp_circle (center -2.35 -1.65) (end -2.25 -1.65) (stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS"))']
    for n in range(1,25):
        side,slot=divmod(n-1,6);v=-1.25+slot*.5
        x,y,w,h=[(-1.9125,v,.575,.24),(v,1.9125,.24,.575),
                 (1.9125,-v,.575,.24),(-v,-1.9125,.24,.575)][side]
        text.append(f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) '
                    '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.208333))')
    for n,y,h in ((25,-.625,1.45),(26,.925,.85)):
        text.append(f'(pad "{n}" smd roundrect (at 0 {y}) (size 2.7 {h}) '
                    '(layers "F.Cu" "F.Mask") (roundrect_rratio 0.04))')
        for x in (-.85,0,.85):
            text.append(f'(pad "" smd rect (at {x} {y}) (size .65 {h-.2}) (layers "F.Paste"))')
    return name,'\n'.join(text+[')',''])


def main():
    name, text = isl9241_footprint()
    (ROOT/'ducktop2.pretty'/f'{name}.kicad_mod').write_text(text)
    tps_name,tps_text=tps552882_footprint()
    (ROOT/'ducktop2.pretty'/f'{tps_name}.kicad_mod').write_text(tps_text)
    ef_name,ef_text=tps25982_footprint()
    (ROOT/'ducktop2.pretty'/f'{ef_name}.kicad_mod').write_text(ef_text)
    for part,pins,fp,url in [
        ('ISL9241',ISL9241_PINS,'ducktop2:'+name,
         'https://www.renesas.com/en/document/dst/isl9241-datasheet'),
        ('TPS552882',TPS552882_PINS,'ducktop2:Texas_RPM0026A_VQFN-HR26_4x3.5',
         'https://www.ti.com/lit/ds/symlink/tps552882.pdf'),
        ('TPS25982',TPS25982_PINS,'ducktop2:'+ef_name,
         'https://www.ti.com/lit/ds/symlink/tps25982.pdf'),
        ('TPS3700',TPS3700_PINS,'Package_TO_SOT_SMD:SOT-23-6',
         'https://www.ti.com/lit/ds/symlink/tps3700.pdf')]:
        (ROOT/'gen'/f'{part}.kicad_sym').write_text(symbol(part,pins,fp,url))


if __name__ == '__main__':
    main()

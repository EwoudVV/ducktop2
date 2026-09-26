#!/usr/bin/env python3
"""Dimensioned adapter drawings from the same parameters as the CAD."""
from cad import HERE
import hinges


def main():
    out=HERE/'drawings';out.mkdir(exist_ok=True)
    for side in ['left','right']:
        x=30;y=0;h=12
        base,bolts=hinges.base_plate(side,x,y,h)
        lid,seats,lb=hinges.lid_plate(side,x,y,h)
        rows=[]
        svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="950" viewBox="0 0 1400 950">',
             '<rect width="1400" height="950" fill="white"/>',
             '<g font-family="Arial,sans-serif" fill="#172b37">',
             f'<text x="50" y="55" font-size="30">ducktop2 / {side} hinge adapters</text>',
             '<text x="50" y="90" font-size="18">mm. hole positions relative to each plate\'s minimum X/Y corner in the installed top view.</text>',
             '<text x="50" y="120" font-size="18">3 mm steel plates. tap pilots shown; no screw thread inferred from hinge clearance holes.</text>']
        for index,(title,part,points) in enumerate([
            ('base',base,[(a,b,1.6,'M2 tap') for a,b in hinges.base_holes(side,x,y)]+[(a,b,3.2,'M3 clearance') for a,b in bolts]),
            ('lid, closed',lid,[(a,b,1.6 if t=='M2' else 1.25,t+' tap') for a,b,_,_,t,_,_ in hinges.lid_holes(side,x,y)]+[(a,b,3.2,'M3 clearance') for a,b in lb])]):
            bb=part.BoundingBox(); xmin=bb.xmin;ymin=-bb.ymax
            ox=75+index*680;oy=220;scale=10
            w=bb.xlen;d=bb.ylen
            svg.extend([f'<text x="{ox}" y="180" font-size="24">{title}</text>',
                f'<rect x="{ox}" y="{oy}" width="{w*scale}" height="{d*scale}" fill="#edf1f4" stroke="#172b37" stroke-width="2"/>',
                f'<text x="{ox+w*scale/2}" y="{oy-15}" text-anchor="middle" font-size="20">{w:.2f}</text>',
                f'<text x="{ox-12}" y="{oy+d*scale/2}" text-anchor="end" font-size="20">{d:.2f}</text>'])
            for i,(hx,hy,diam,name) in enumerate(points,1):
                px=ox+(hx-xmin)*scale;py=oy+(hy-ymin)*scale
                svg.extend([f'<circle cx="{px}" cy="{py}" r="{diam*scale/2}" fill="white" stroke="#172b37" stroke-width="1.5"/>',
                            f'<text x="{px+13}" y="{py-8}" font-size="15">{i}</text>'])
                svg.append(f'<text x="{ox}" y="{530+30*i}" font-size="18">{i}: X {hx-xmin:.3f}, Y {hy-ymin:.3f}, {name}</text>')
        lines=[f'base seat is {-hinges.BASE_SEAT[side]:.2f} below pivot. base plate sits immediately below that seat.',
               'lid backing plate: 10.00 to 13.00 above pivot when closed.',
               'lid main sleeves: 3.00 high. small-tab sleeve: 3.90 high. sleeves are separate, electrically neutral parts.',
               'base screws M2 x 4. lid screws M2 x 6 and M1.6 x 7. flat low heads, OEM diameters required.',
               'check owned hinge fit, tapped engagement, screw tips and tool access before a loaded test.']
        for i,line in enumerate(lines):svg.append(f'<text x="50" y="{770+30*i}" font-size="18">{line}</text>')
        svg.append('</g></svg>');(out/f'hinge-{side}.svg').write_text('\n'.join(svg))


if __name__=='__main__':main()

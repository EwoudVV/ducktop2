"""Explicit radio retention stack, independent of the battery supports."""
import math
import cadquery as cq
from cad import cylinder


def add(m):
    from build import CONFIG,INVENTORY,installed
    dt=CONFIG['base']['deck_top'];bottom=CONFIG['boards']['radio']['bottom_height']
    length=dt-bottom+2
    for hole in INVENTORY['radio']['holes']:
        if not (hole['reference'] or '').startswith('H'):continue
        ref=hole['reference'];x,y=installed('radio',hole['position'])
        screw=cylinder(x,y,dt-length,1,length).fuse(cylinder(x,y,dt,2,2))
        washer=cylinder(x,y,bottom-.5,3,.5).cut(cylinder(x,y,bottom-.6,1.1,.7))
        nut=cq.Workplane('XY').polygon(6,4/math.cos(math.pi/6)).extrude(1.6).val().translate((x,-y,bottom-2.1))
        nut=nut.cut(cylinder(x,y,bottom-2.2,.8,1.8))
        for suffix,shape in [('screw-envelope',screw),('washer-envelope',washer),('nut-envelope',nut)]:
            m.add(f'radio-{ref}-{suffix}',shape,'hardware','nylon',False,False)
        row=next(q for q in m.mounts if q['reference']=='radio/'+ref)
        row.update(fastener_length_mm=length,pcb_hole_mm=hole['drill'][0],washer_OD_mm=6,washer_thickness_mm=.5,
                   head_height_mm=2,nut_height_mm=1.6,thread_engagement_mm=1.5,
                   status=f'M2 x{math.ceil(length)} trimmed to {length:g}; nominal insulating hardware envelopes, sample fit and retention test pending',
                   mating_part='deck through insulating suspension tube and radio PCB, with washer and nut below')

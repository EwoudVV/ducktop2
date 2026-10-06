"""Removable USB guide rails with fixed feet below the boards and between cells."""
import math
from cad import box,cylinder


def split_usb_carrier(m,name,seam_x,post_x):
    from build import CONFIG
    from cables import nearest_x
    floor=CONFIG['base']['floor'];joint=8.5
    item=next(p for p in m.parts if p['name']==name+'-carrier')
    original=item['shape']
    original_pieces=m.collision_primitives[name+'-carrier']
    # Only the narrow locating blade passes through the board seam. The
    # wider foot stays below the PCB and outside the connector withdrawal.
    low=box(seam_x-4,0,floor-.1,8,260,5.5-floor+.1)
    slot=box(seam_x-.7,0,floor+1,1.4,260,3.3)
    blade=box(seam_x-.5,0,floor+1.3,1,260,3.)
    seam_foot=original.intersect(low).cut(slot)
    upper=original.cut(low).fuse(original.intersect(blade))
    post_region=box(post_x-6.1,189.9,floor-.1,12.2,12.2,joint-floor+.1)
    post=upper.intersect(post_region)
    upper=upper.cut(post_region)
    rows=[r for r in m.harness['routes'] if r['group']=='usb5']
    seat=min(nearest_x(r,post_x)[2]-r['wire_od_mm']/2-.55 for r in rows)-.15
    length=math.floor((seat-joint+3)*2)/2
    engagement=joint-(seat-length)
    if engagement<2.5:raise ValueError('USB carrier screw engagement below 2.5 mm')
    cuts=[]
    for x in (post_x-2.5,post_x+2.5):
        hole=cylinder(x,195,joint-.1,1.1,seat-joint+.2)
        cuts.append(hole);upper=upper.cut(hole)
        post=post.cut(cylinder(x,195,joint-3.3,.8,3.4))
        screw=cylinder(x,195,seat-length,1,length).fuse(cylinder(x,195,seat,2,2))
        m.add(name+f'-release-screw-{x:g}',screw,'hardware','nylon',False,False,
              harness_fastener=True,service_removable=True,
              thread_host=name+'-fixed-cell-post',thread_axis_xy_mm=[x,195],
              thread_height_range_mm=[seat-length,joint],thread_radius_mm=1.)
        m.mount(name+f'-release-{x:g}',x,195,seat,'removable USB guide to fixed cell-gap post',
                2.2,'M2',joint-floor,length,'insulating guide and nylon screw',
                'trim to listed length; verify pilot fit, pullout and guide deflection in coupons',
                minimum_thread_engagement_mm=round(engagement,3))
    item['shape']=upper;item['service_removable']=True
    item['service_note']='release both cell-gap screws and lift the upper rail; fixed feet stay in the case'
    for suffix,shape in [('fixed-seam-foot',seam_foot),('fixed-cell-post',post)]:
        if not shape.isValid() or len(shape.Solids())!=1:
            raise ValueError(name+' '+suffix+' is not one valid solid')
        m.add(name+'-'+suffix,shape,'supports',harness_part=True)
    if not upper.isValid() or len(upper.Solids())!=1:
        raise ValueError(name+' removable upper is not one valid solid')
    # Distribute the same cuts over the original guide, pedestal and rib
    # pieces. Their union contains the final carrier without the removed feet.
    # This keeps the exact checker from repeatedly intersecting one large
    # swept solid against parts that only approach a short section of it.
    cap=next(p for p in m.parts if p['name']==name+'-cap')['shape']
    pieces=[]
    for part in original_pieces:
        piece=part.cut(low).fuse(part.intersect(blade)).cut(post_region).cut(cap)
        for cut in cuts:piece=piece.cut(cut)
        for bore in m.clamp_bores[name]:piece=piece.cut(bore)
        pieces.append(piece)
    m.collision_primitives[name+'-carrier']=pieces

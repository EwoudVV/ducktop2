"""Supports and a bottom-fed air path for the removable right-side cooler."""
import json
from pathlib import Path

import cadquery as cq
from cad import box, cylinder, compound

HERE=Path(__file__).resolve().parent


def config():return json.loads((HERE/'cooler-hardware.json').read_text())


def annulus(x,y,h,outer,inner,height):
    return cylinder(x,y,h,outer,height).cut(cylinder(x,y,h-.05,inner,height+.1))


def slot(x,y,h,width,length,height):
    straight=length-width
    return box(x-width/2,y-straight/2,h,width,straight,height).fuse(
        cylinder(x,y-straight/2,h,width/2,height),cylinder(x,y+straight/2,h,width/2,height))


def floor_shape(body,case):
    c=config();p=c['fan_posts'];floor=case['base']['floor'];a=c['intake'];x,y=a['centre_xy'];r=a['floor_opening_radius_mm']
    opening=cylinder(x,y,-.1,r,floor+.2);body=body.cut(opening)
    disc=cylinder(x,y,0,r,floor)
    bars=[]
    pitch=a['grille_pitch_mm']
    for index in range(-int(r//pitch),int(r//pitch)+1):
        offset=index*pitch
        w=a['grille_bar_width_mm']
        bars.extend([box(x-r,y+offset-w/2,0,2*r,w,floor).intersect(disc),
                     box(x+offset-w/2,y-r,0,w,2*r,floor).intersect(disc)])
    # Fuse crossing bars as solids. An overlapping compound can make the
    # kernel heal the opening into a solid disc during the floor union.
    for bar in bars:body=body.fuse(bar)
    rib=cylinder(x,y,0,r,a['cross_rib_top_H'])
    w=a['cross_rib_width_mm']
    cross=box(x-r,y-w/2,0,2*r,w,a['cross_rib_top_H']).fuse(box(x-w/2,y-r,0,w,2*r,a['cross_rib_top_H'])).intersect(rib)
    body=body.fuse(cross,annulus(x,y,floor,a['boot_outer_radius_mm'],a['boot_inner_radius_mm'],a['boot_top_H']-floor))
    for mx,my in p['centres_xy']:
        post=cylinder(mx,my,floor-.05,p['radius_mm'],p['base_top_H']-floor+.05)
        post=post.cut(cylinder(mx,my,p['base_top_H']-p['insert_length_mm'],p['insert_body_allocation_mm']/2+.01,p['insert_length_mm']+.1))
        post=post.cut(cylinder(mx,my,floor,1.1,p['base_top_H']-floor+.1))
        body=body.fuse(post)
    for i,(mx,my) in enumerate(c['fin_mounts']['centres_xy']):
        hole=cylinder(mx,my,-.1,1.2,floor+.2) if i==0 else slot(mx,my,-.1,2.4,c['fin_mounts']['front_slot_length_mm'],floor+.2)
        # A conservative recess covers the screw's 3.8 mm maximum head.
        sink=cylinder(mx,my,-.05,2.05,.35).fuse(cq.Solid.makeCone(2.05,1.15,.9,cq.Vector(mx,-my,.3)))
        if i:sink=sink.fuse(sink.translate((0,.4,0)),sink.translate((0,-.4,0)))
        body=body.cut(hole.fuse(sink))
    assert body.isValid() and len(body.Solids())==1,'floor, grille and posts must remain connected'
    return body


def fin_retention(stack,fin):
    c=config()['fin_mounts'];x,y,w,d=fin['xywh'];h=fin['bottom_H'];t=c['end_plate_thickness_mm']
    stack=stack.fuse(box(x,y-t,h,w,t,fin['top_H']-h),box(x,y+d,h,w,t,fin['top_H']-h))
    for i,(mx,my) in enumerate(c['centres_xy']):
        low_y=y-t-4.5 if i==0 else y+d+.5
        tab=box(mx-c['tab_width_mm']/2,low_y,h,c['tab_width_mm'],5.5,c['tab_thickness_mm'])
        stack=stack.fuse(tab).cut(cylinder(mx,my,h-.1,1,c['tab_thickness_mm']+.2))
    assert stack.isValid() and len(stack.Solids())==1,'fin tabs need a continuous load path'
    return stack


def parts(case,fan,fin,pipe,fin_shape=None,pipe_shapes=None):
    c=config();rows=[]
    def add(name,shape,color=(.3,.45,.50),group='cooling',**extra):
        assert shape.isValid(),name
        rows.append(dict(name=name,shape=shape,color=color,group=group,moving=False,remote_cooler=True,cooler_hardware=True,**extra))
    p=c['fan_posts']
    for i,(x,y) in enumerate(p['centres_xy'],1):
        top=p['base_top_H'];length=p['insert_length_mm']
        add(f'fan-insert-{i}',annulus(x,y,top-length,p['insert_body_allocation_mm']/2,1,length),(.63,.49,.2))
        recess=p.get('spacer_recess_by_index_mm',{}).get(str(i),0) if case.get('fan_harness') else 0
        add(f'fan-spacer-{i}',annulus(x,y,top,p['spacer_radius_mm'],1.1,p['spacer_height_mm']-recess),(.45,.49,.5))
        seat=fan['mount_ear_upper_H'];washer_top=seat+p['washer_thickness_mm']
        add(f'fan-washer-{i}',annulus(x,y,seat,p['washer_diameter_mm']/2,1.1,p['washer_thickness_mm']),(.6,.62,.65))
        screw=cylinder(x,y,washer_top-p['screw_length_mm'],1,p['screw_length_mm']).fuse(cylinder(x,y,washer_top,p['head_diameter_allocation_mm']/2,p['head_height_allocation_mm']))
        add(f'fan-screw-{i}',screw,(.42,.44,.47))
        add(f'fan-driver-space-{i}',cylinder(x,y,washer_top+p['head_height_allocation_mm'],3.0,20),(.3,.6,.9,.15),'keepout',service=True,service_removes=['deck','oled-1-module','oled-2-module'])
    f=c['fin_mounts'];floor=case['base']['floor']
    for i,(x,y) in enumerate(f['centres_xy'],1):
        add(f'fin-insulating-spacer-{i}',annulus(x,y,floor,f['spacer_diameter_mm']/2,f['spacer_bore_mm']/2,f['spacer_height_mm']),(.56,.55,.31))
        add(f'fin-insulating-washer-{i}',annulus(x,y,fin['bottom_H']-f['upper_washer_thickness_mm'],f['spacer_diameter_mm']/2,f['spacer_bore_mm']/2,f['upper_washer_thickness_mm']),(.56,.55,.31))
        head=cylinder(x,y,0,f['head_diameter_max_mm']/2,.3).fuse(cq.Solid.makeCone(f['head_diameter_max_mm']/2,1,.9,cq.Vector(x,-y,.3)))
        screw=head.fuse(cylinder(x,y,1.2,1,6.8))
        add(f'fin-bottom-screw-{i}',screw,(.45,.47,.5))
        add(f'fin-driver-space-{i}',cylinder(x,y,-25,2.5,25),(.3,.6,.9,.15),'keepout',service=True,service_removes=[])
    a=c['intake'];x,y=a['centre_xy']
    add('fan-intake-gasket',annulus(x,y,a['boot_top_H'],a['boot_outer_radius_mm'],a['boot_inner_radius_mm'],fan['bottom_H']-a['boot_top_H']),(.2,.23,.25))
    # The rigid cowl clears the fin and pipe allowances. Thin separate baffles
    # and removable sealing tape close the short gap to the fan outlet.
    q=c['duct'];fx,fy,fw,fd=fin['xywh'];left=q['baffle_x'];right=fx+fw
    cowl=box(left,q['rear_Y'],q['bottom_H'],right-left,q['front_Y']-q['rear_Y'],q['floor_thickness_mm'])
    cowl=cowl.fuse(box(left,q['rear_Y'],q['roof_bottom_H'],right-left,q['front_Y']-q['rear_Y'],q['roof_thickness_mm']))
    for yy in [q['rear_Y'],q['front_Y']-q['wall_mm']]:
        wall=box(left,yy,q['bottom_H'],right-left,q['wall_mm'],q['roof_bottom_H']+q['roof_thickness_mm']-q['bottom_H'])
        wall=wall.cut(box(349.2,yy-.1,5.6,right-349.2+.1,q['wall_mm']+.2,3.1))
        if yy==q['rear_Y']:
            wall=wall.cut(box(344.35,yy-.1,pipe['bottom_H']-.4,18.3,q['wall_mm']+.2,4.3))
        cowl=cowl.fuse(wall)
    # These ears are clamped between the lower insulating spacers and the
    # upper washers by the fin screws. The cowl does not rely on sealing tape.
    for x,y in f['centres_xy']:
        cowl=cowl.fuse(cylinder(x,y,q['bottom_H'],f['spacer_diameter_mm']/2,q['floor_thickness_mm']))
        cowl=cowl.cut(cylinder(x,y,q['bottom_H']-.1,f['spacer_bore_mm']/2,q['floor_thickness_mm']+.2))
    assert cowl.isValid() and len(cowl.Solids())==1,'cowl mounting ears must join its floor'
    add('fin-cowl',cowl,(.3,.43,.49))
    for i,(x,y) in enumerate(f['centres_xy'],1):
        add(f'fin-screw-sealing-bead-{i}',annulus(x,y,q['bottom_H'],f['spacer_bore_mm']/2,1,q['floor_thickness_mm']),(.2,.23,.25))
    if fin_shape is not None:
        # Fit these split soft seals after the cooler has slid into the cowl.
        # The displayed holes follow nominal parts; compression and adhesive
        # overlap have to be qualified on the actual chosen seal material.
        for i,yy in enumerate([q['rear_Y'],q['front_Y']-q['wall_mm']],1):
            seal=box(349.2,yy,5.6,right-349.2,q['wall_mm'],3.1).cut(fin_shape)
            for row in rows:
                if row['name'].startswith(('fin-insulating-washer-','fin-bottom-screw-')):seal=seal.cut(row['shape'])
            for label,low,high in [('lower',5.6,7.1),('upper',7.1,8.7)]:
                s=seal.intersect(box(349,yy-.1,low,right-349+.1,q['wall_mm']+.2,high-low))
                add(f'fin-tab-seal-{i}-{label}',s,(.2,.23,.25))
        low=pipe['bottom_H']-.4;split=pipe['bottom_H']+pipe['height_mm']/2
        seal=box(344.35,q['rear_Y'],low,right-344.35,q['wall_mm'],4.3)
        for s in pipe_shapes or []:seal=seal.cut(s)
        for label,start,stop in [('lower',low,split),('upper',split,low+4.3)]:
            add(f'pipe-entry-seal-{label}',seal.intersect(box(344.3,q['rear_Y']-.1,start,right-344.3+.1,q['wall_mm']+.2,stop-start)),(.2,.23,.25))
    bottom_seal=box(fx,fy,q['bottom_H']+q['floor_thickness_mm'],fw,fd,fin['bottom_H']-q['bottom_H']-q['floor_thickness_mm'])
    for x,y in c['fin_mounts']['centres_xy']:
        bottom_seal=bottom_seal.cut(cylinder(x,y,0,f['spacer_diameter_mm']/2,6.1))
    add('fin-bottom-seal',bottom_seal,(.2,.23,.25))
    add('fin-top-seal',box(fx,fy,fin['top_H'],fw,fd,q['roof_bottom_H']-fin['top_H']),(.2,.23,.25))
    x0,y0,h0,width,height=q['fan_outlet_window_xyzh']
    baffle=box(left,q['rear_Y']+q['wall_mm'],q['bottom_H']+q['floor_thickness_mm'],q['baffle_thickness_mm'],q['front_Y']-q['rear_Y']-2*q['wall_mm'],q['roof_bottom_H']-q['bottom_H']-q['floor_thickness_mm'])
    baffle=baffle.cut(box(left-.1,y0,h0,q['baffle_thickness_mm']+.2,width,height))
    add('fan-to-fin-baffle',baffle,(.22,.29,.31))
    t=q['foil_bridge_thickness_mm']
    bridge=box(x0,y0-t,h0-t,left-x0,width+2*t,height+2*t)
    bridge=bridge.cut(box(x0-.1,y0,h0,left-x0+.2,width,height))
    add('fan-outlet-foil-bridge',bridge,(.53,.52,.45))
    seal=box(fx+fw,fy-.5,fin['bottom_H']-.25,case['outline']['x_max']-fx-fw,fd+1,fin['top_H']-fin['bottom_H']+.5)
    seal=seal.cut(box(fx+fw-.1,fy,fin['bottom_H'],case['outline']['x_max']-fx-fw+.2,fd,fin['top_H']-fin['bottom_H']))
    add('case-exhaust-seal',seal,(.2,.23,.25))
    return rows

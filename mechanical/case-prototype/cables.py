"""Current power wires, continuous guides and independent case-mounted clamps.

Inputs use installed X,Y,H (H up). geom() converts to construction X,-Y,H.
STEP export rotates the whole assembly, giving X,Y,-H. No parts are mirrored.
"""
import json
import math
import hashlib
from functools import wraps
import numpy as np
import cadquery as cq
from cad import HERE,ROOT,box,cylinder,compound,render
from harness_geometry import paths
from case_inputs import path as input_path


def cached_geometry(fn):
    @wraps(fn)
    def wrapper(*args):
        payload=json.dumps([np.asarray(a).tolist() for a in args],separators=(',',':'))
        key=hashlib.sha256((fn.__name__+'-v3'+payload).encode()).hexdigest()
        folder=ROOT/'.workbench/case-prototype/harness-brep';folder.mkdir(parents=True,exist_ok=True)
        path=folder/(key+'.brep')
        if path.exists():return cq.Shape.importBrep(str(path))
        result=fn(*args)
        if not result.isValid():raise ValueError(fn.__name__+' produced an invalid solid')
        result.exportBrep(str(path))
        return result
    return wrapper


def geom(points):
    return [cq.Vector(float(x),float(-y),float(h)) for x,y,h in points]


def path_edge(points):
    return cq.Edge.makeSplineApprox(geom(points),tol=.008,minDeg=3,maxDeg=6)


@cached_geometry
def tube(points,radius,inner=None):
    edge=path_edge(points);origin=edge.startPoint();direction=edge.tangentAt(0)
    outer=cq.Wire.makeCircle(radius,origin,direction)
    holes=[cq.Wire.makeCircle(inner,origin,direction)] if inner else []
    try:
        s=cq.Solid.sweep(outer,holes,edge,True,False,mode=cq.Wire.assembleEdges([edge.translate((0,0,10))]))
        if s.isValid():return s
    except Exception:pass
    a=loft_path(points,lambda o,n,h,u:cq.Wire.makeCircle(radius,o,n))
    if inner:a=a.cut(loft_path(points,lambda o,n,h,u:cq.Wire.makeCircle(inner,o,n)))
    return a


def loft_path(points,profile):
    # Ruled stations no farther than 1 mm apart. At the tightest 9 mm bend,
    # the centerline chord error is below 0.014 mm, within guide clearance.
    p=np.array(points);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    at=np.linspace(0,s[-1],int(math.ceil(s[-1]))+1)
    q=np.column_stack([np.interp(at,s,p[:,i]) for i in range(3)])
    v=geom(q);profiles=[]
    for i,o in enumerate(v):
        normal=(v[min(i+1,len(v)-1)]-v[max(0,i-1)]).normalized()
        horizontal=cq.Vector(-normal.y,normal.x,0).normalized();up=normal.cross(horizontal).normalized()
        profiles.append(profile(o,normal,horizontal,up))
    return cq.Solid.makeLoft(profiles,ruled=True)


def sweep_rect(points,x0,z0,width,height):
    edge=path_edge(points);normal=edge.tangentAt(0)
    horizontal=cq.Vector(-normal.y,normal.x,0).normalized()
    plane=cq.Plane(edge.startPoint(),xDir=horizontal,normal=normal)
    profile=cq.Workplane(plane).moveTo(x0,z0).rect(width,height,centered=False).val()
    return cq.Solid.sweep(profile,[],edge,True,False)


@cached_geometry
def guide(points,od,clearance,wall):
    r=od/2+clearance;outer=r+wall
    edge=path_edge(points);normal=edge.tangentAt(0)
    horizontal=cq.Vector(-normal.y,normal.x,0).normalized()
    up=normal.cross(horizontal).normalized();origin=edge.startPoint()
    def p(radius,angle):
        a=math.radians(angle)
        return origin+horizontal.multiply(radius*math.cos(a))+up.multiply(radius*math.sin(a))
    # Single closed C-profile avoids a coincident swept-slot boolean. Its
    # 90 degree opening faces up throughout the near-horizontal cable run.
    profile=cq.Wire.assembleEdges([
        cq.Edge.makeThreePointArc(p(outer,135),p(outer,270),p(outer,405)),
        cq.Edge.makeLine(p(outer,405),p(r,405)),
        cq.Edge.makeThreePointArc(p(r,405),p(r,270),p(r,135)),
        cq.Edge.makeLine(p(r,135),p(outer,135))])
    try:
        solid=cq.Solid.sweep(profile,[],edge,True,False,mode=cq.Wire.assembleEdges([edge.translate((0,0,10))]))
        if solid.isValid():return solid
    except Exception:pass
    def station(o,n,h,u):
        def v(R,a):return o+h.multiply(R*math.cos(math.radians(a)))+u.multiply(R*math.sin(math.radians(a)))
        return cq.Wire.assembleEdges([cq.Edge.makeThreePointArc(v(outer,135),v(outer,270),v(outer,405)),
            cq.Edge.makeLine(v(outer,405),v(r,405)),cq.Edge.makeThreePointArc(v(r,405),v(r,270),v(r,135)),
            cq.Edge.makeLine(v(r,135),v(outer,135))])
    return loft_path(points,station)


def polygon_prism(points,h,height):
    return cq.Workplane('XY').polyline([(x,-y) for x,y in points]).close().extrude(height).val().translate((0,0,h))


def nearest_x(route,x):
    p=np.array(route['points']);return p[np.argmin(abs(p[:,0]-x))]


def strain_clamp(m,name,route_rows,anchor_x,front_gap=False,foot_x=None,dogleg=False,width=6,y_bounds=None,low_screw_xy=None,low_screw_axis_x=None):
    """Split clamp on a separate insulating seam pedestal.

    Rigid bores clear maximum wire OD. Replaceable slit TPU liners provide
    grip; hard stops prevent uncontrolled screw compression. No PCB holes or
    copper hold-down pads carry cable pull loads.
    """
    from build import CONFIG
    print('building '+name,flush=True)
    foot_x=anchor_x if foot_x is None else foot_x
    pts=[nearest_x(r,anchor_x) for r in route_rows]
    ylo=min(p[1] for p in pts)-4.3;yhi=max(p[1] for p in pts)+4.3
    if y_bounds:
        ylo=min(ylo,y_bounds[0]);yhi=max(yhi,y_bounds[1])
    zlo=min(p[2]-r['wire_od_mm']/2 for p,r in zip(pts,route_rows))-1
    split=max(p[2] for p in pts)+.05;top=max(p[2]+r['wire_od_mm']/2 for p,r in zip(pts,route_rows))+1
    floor=CONFIG['base']['floor']
    screw_length=math.floor((top-zlo-.2)*2)/2
    # A stepped parting line opens each bore at its own wire height, including
    # the vertically separated USB pair. No wire is trapped in a closed bore.
    bands=sorted(zip(pts,route_rows),key=lambda q:q[0][1])
    body=None;cap=None
    for i,(pt,row) in enumerate(bands):
        low=ylo if i==0 else (bands[i-1][0][1]+pt[1])/2
        high=yhi if i==len(bands)-1 else (pt[1]+bands[i+1][0][1])/2
        level=float(pt[2])
        # The split follows the wire height through the clamp. A flat split
        # can leave a closed bore when the wire is climbing into a bend.
        arr=np.array(row['points']);xs=np.linspace(anchor_x-width/2,anchor_x+width/2,17)
        near=arr[(arr[:,0]>=anchor_x-width)&(arr[:,0]<=anchor_x+width)]
        xx,index=np.unique(near[:,0],return_index=True);zz=near[index,2]
        levels=np.interp(xs,xx,zz)
        def band(bottom,upper):
            sections=[]
            for x,z in zip(xs,levels):
                lo=zlo if bottom else z
                hi=z if upper else top
                sections.append(cq.Wire.makePolygon([cq.Vector(x,-low,lo),cq.Vector(x,-high,lo),
                    cq.Vector(x,-high,hi),cq.Vector(x,-low,hi)],close=True))
            return cq.Solid.makeLoft(sections,ruled=True)
        bs=band(True,True);cs=band(False,False)
        body=bs if body is None else body.fuse(bs)
        cap=cs if cap is None else cap.fuse(cs)
    screws=[(anchor_x,ylo+1.7),(anchor_x,yhi-1.7)]
    if low_screw_axis_x is not None:screws[0]=(low_screw_axis_x,ylo+1.7)
    if low_screw_xy:
        screws[0]=low_screw_xy
        x,y=low_screw_xy
        body=body.fuse(box(x-2.3,y-2.3,zlo,4.6,4.6,split-zlo))
        cap=cap.fuse(box(x-2.3,y-2.3,split,4.6,4.6,top-split))
        # Keep a finite cap wall beside the raised boss. A boss tangent to
        # the 4 mm clamp edge creates a pinched, non-manifold mesh edge.
        for x,y in screws:body=body.fuse(cylinder(x,y,zlo,1.6,split-zlo))
        cap=cap.cut(body)
    liners=[]
    for p,r in zip(pts,route_rows):
        arr=np.array(r['points']);take=arr[(arr[:,0]>=anchor_x-width/2-1)&(arr[:,0]<=anchor_x+width/2+1)]
        if len(take)<3:take=arr
        bore=tube(take,r['wire_od_mm']/2+.35)
        if not hasattr(m,'clamp_bores'):m.clamp_bores={}
        m.clamp_bores.setdefault(name,[]).append(bore)
        body=body.cut(bore);cap=cap.cut(bore)
        liner=tube(take,r['wire_od_mm']/2+.34,r['wire_od_mm']/2-.025)
        liner=liner.intersect(box(anchor_x-width/2+.4,ylo,zlo,width-.8,yhi-ylo,top-zlo))
        # Slit liner can open around an already terminated wire.
        liner=liner.cut(box(anchor_x-width/2,p[1]-.07,p[2],width,.14,4))
        liners.append(liner)
    footwidth=6 if dogleg else 7
    foot=box(foot_x-footwidth/2,190 if front_gap else ylo,floor,footwidth,10 if front_gap else yhi-ylo,2)
    web=box(foot_x-2,192,floor+1.8,4,4,zlo-floor-.8) if front_gap else box(foot_x-.5,ylo,floor+1.8,1,yhi-ylo,zlo-floor-1.8)
    if not front_gap and foot_x!=anchor_x:
        web=web.fuse(box(min(foot_x-.5,anchor_x-3),ylo,7.0,abs(anchor_x-foot_x)+1,yhi-ylo,split-7.0))
    if dogleg:
        body=body.fuse(box(anchor_x-width/2,yhi-3,zlo,width,187.5-yhi+3,1))
        body=body.fuse(box(foot_x-2,186,zlo,anchor_x+5-foot_x,1.5,1))
        body=body.fuse(box(foot_x-2,186,zlo,4,10,1))
    elif front_gap:body=body.fuse(box(anchor_x-3,yhi-3,zlo,6,196-yhi+3,1))
    body=body.fuse(web).fuse(foot)
    for sx,yy in screws:
        body=body.cut(cylinder(sx,yy,zlo-.1,.8,top-zlo+.2))
        cap=cap.cut(cylinder(sx,yy,zlo-.1,1.1,top-zlo+.2))
        m.mount(name+f'-cap-{yy:.2f}',sx,yy,top,'split clamp to insulating pedestal',2.2,'M2',split-zlo,screw_length,
                'TPU liner; dielectric pedestal; independent of PCB','trim nylon screw to listed length; verify blind engagement and pullout in coupon')
        m.add(name+f'-cap-screw-{yy:.2f}',cylinder(sx,yy,top-screw_length,1,screw_length).fuse(cylinder(sx,yy,top,2,2)),
              'hardware','nylon',False,False,harness_fastener=True,service_removable=True)
        m.add(name+f'-driver-access-{yy:.2f}',cylinder(sx,yy,top+2,2.5,18),'keepout','service reservation',False,False,service=True)
        fy=(192 if yy<=(ylo+yhi)/2 else 198) if front_gap else yy
        body=body.cut(cylinder(foot_x,fy,floor-.1,.8,2.2))
        for q in m.parts:
            if q['name'].startswith('base-') and q['group']=='structure':q['shape']=q['shape'].cut(cylinder(foot_x,fy,-.1,1.1,floor+.2))
        m.mount(name+f'-floor-{fy:.2f}',foot_x,fy,floor+2,'pedestal foot to base from underside',2.2,'M2',2,4,
                'insulating pedestal; heads outside electronics','2 mm pilot engagement; coupon pull test before fitting wires')
    m.add(name+'-pedestal',body,'supports',harness_part=True)
    m.add(name+'-cap',cap,'supports',harness_part=True,service_removable=True)
    for i,s in enumerate(liners):m.add(name+f'-liner-{i+1}',s,'supports','TPU',harness_part=True,intentional_wire_grip=True)
    return body


def middle_support(m,label,rows,x):
    """Ribbed cantilever from the gap between cells, not from their surfaces."""
    from build import CONFIG
    floor=CONFIG['base']['floor'];pts=[nearest_x(r,x) for r in rows]
    support_top=min(p[2]-r['wire_od_mm']/2-.55 for p,r in zip(pts,rows))-.15
    y0=min(p[1] for p in pts)-2
    beam=box(x-5,y0,support_top-4.5,10,198-y0,4.5)
    if label=='right':
        # Open-bottom crossing slots preserve the known J2 straight exit.
        # The residual beam ligament is a fit-test item, not a load approval.
        for yy in [169.448,173.448]:
            beam=beam.cut(box(x-6,yy-1.2,support_top-4.6,12,2.4,14.2-(support_top-4.6)))
    column=box(x-5,192,floor+1.8,10,6,support_top-floor-1.8)
    foot=box(x-6,190,floor,12,12,2)
    beam=beam.fuse(column).fuse(foot)
    for p,r in zip(pts,rows):
        bottom=p[2]-r['wire_od_mm']/2-.55
        boss=box(x-2,p[1]-2,support_top-.1,4,4,bottom-support_top+.6)
        arr=np.array(r['points']);local=arr[(arr[:,0]>=x-4)&(arr[:,0]<=x+4)]
        boss=boss.cut(tube(local,r['wire_od_mm']/2+.15))
        beam=beam.fuse(boss)
    for yy in [192,200]:
        beam=beam.cut(cylinder(x,yy,floor-.1,.8,2.2))
        for p in m.parts:
            if p['name'].startswith('base-') and p['group']=='structure':p['shape']=p['shape'].cut(cylinder(x,yy,-.1,1.1,floor+.2))
        m.mount(f'USB-{label}-middle-anchor-{yy}',x,yy,floor+2,'independent USB guide rib to floor in cell gap',2.2,'M2',2,4,
                'all dielectric; no cell contact','fit and deflection test under dressed-wire load required')
    m.add('harness-USB-'+label+'-middle-rib',beam,'supports',harness_part=True)


def integrate_guides(m,groups):
    """Turn intersecting guide/pedestal seats into real manufactured carriers.

    Only deliberate mating pairs are fused. Crossings between unrelated
    routes stay separate and are reported by the collision checks.
    """
    jobs=[]
    for group in ['left-main-power','left-J2450','right-main-power','right-J2462','bms-power']:
        prefix='harness-BMS' if group=='bms-power' else 'harness-'+group
        names={r['name'] for r in groups[group]}
        jobs.append((prefix,[p for p in m.parts if p.get('guide_for') in names or p['name']==prefix+'-pedestal']))
    for side,suffix in [('left','-1'),('right','-2')]:
        prefix='harness-USB-'+side
        jobs.append((prefix,[p for p in m.parts if (p.get('guide_for','').startswith('usb5-') and p['name'].endswith(suffix)) or p['name'] in [prefix+'-pedestal',prefix+'-middle-rib']]))
    for name,pieces in jobs:
        if not pieces:continue
        shape=pieces[0]['shape']
        for p in pieces[1:]:shape=shape.fuse(p['shape'])
        for bore in m.clamp_bores[name]:shape=shape.cut(bore)
        cap=next(p for p in m.parts if p['name']==name+'-cap')
        shape=shape.cut(cap['shape'])
        if name=='harness-USB-left':shape=clean_left_usb_trim(shape)
        if name=='harness-left-J2450':
            # Native center-board connector corner, plus 0.3 mm clearance.
            shape=shape.cut(box(72.9,116.25,6.4,18.7,6.2,2.637))
            for p in pieces:
                if p['name'].endswith('-pedestal'):
                    p['shape']=p['shape'].cut(box(72.9,116.25,6.4,18.7,6.2,2.637))
        # Leave a continuous bridge above each braid, with the supporting
        # legs on either side of its solder-joint reservation.
        braid_y={'harness-left-main-power':70.,'harness-right-main-power':42.5,
                 'harness-right-J2462':114.}.get(name)
        if braid_y is not None:
            gap=box(50 if name.startswith('harness-left') else 280,braid_y-2.78125,6.35,40,5.5625,1.75)
            shape=shape.cut(gap)
            for p in pieces:p['shape']=p['shape'].cut(gap)
        if name=='harness-right-main-power':
            from build import CONFIG
            from shapely.geometry import Polygon
            targets={('center','U904'),('right','C2069')}
            parts=json.loads(input_path('component-placement.json').read_text())['parts']
            for row in parts:
                if (row['board'],row['reference']) not in targets:continue
                if row['side']!='front' or row['height_kind']!='maximum':
                    raise ValueError('recheck the right carrier pocket for '+row['reference'])
                height=row['height_mm']+.3
                low=CONFIG['boards'][row['board']]['bottom_height']+row['board_thickness_mm']-.1
                for ring in row['courtyards_installed_mm']['front']:
                    region=Polygon(ring['outer'],ring['holes']).buffer(.3)
                    pocket=polygon_prism(list(region.exterior.coords),low,height+.1)
                    shape=shape.cut(pocket)
                    for p in pieces:p['shape']=p['shape'].cut(pocket)
        removed={p['name'] for p in pieces}
        m.parts=[p for p in m.parts if p['name'] not in removed]
        m.add(name+'-carrier',shape,'supports',harness_part=True,integrated_from=sorted(removed))
        if not hasattr(m,'collision_primitives'):m.collision_primitives={}
        m.collision_primitives[name+'-carrier']=[p['shape'] for p in pieces]
        if name.startswith('harness-USB-'):
            from service_carriers import split_usb_carrier
            split_usb_carrier(m,name,70.75 if name.endswith('left') else 299.25,
                              113 if name.endswith('left') else 237)


def clean_left_usb_trim(shape):
    """Remove only a tiny detached chip left by the cap-relief boolean."""
    solids=shape.Solids()
    if len(solids)==1:return shape
    main=[s for s in solids if s.Volume()>.2]
    chips=[s for s in solids if s.Volume()<=.2]
    if len(main)!=1 or not chips or any(s.BoundingBox().DiagonalLength>2 for s in chips):
        raise ValueError('USB carrier has a real disconnected piece, not a trim chip')
    return main[0]


def add_cables(m):
    from build import CONFIG,pcb_top,stroke
    data=paths(CONFIG);m.harness=data
    if not all(data[k] for k in ['all_bend_pass','all_length_pass','all_separation_pass']):
        raise ValueError('case harness variant fails bend, length or wire-separation checks; do not export its guides')
    (HERE/'installed-power-harness.json').write_text(json.dumps(data,indent=2)+'\n')
    c=CONFIG['cables'];dz=data['uniform_height_change_mm']
    m.cable_records.extend([{k:v for k,v in p.items() if k!='points'} for p in data['routes']])
    for t in data['terminals']:
        if not t['parts'].startswith('2060-'):continue
        x,y,z=t['pcb_anchor_xyz'];a=math.radians(t['rotation_deg']);n=int(t['parts'].split('-')[1][:3])-450
        width=3.9+4*(n-1);pts=[]
        for u,v in [(-width/2,-6.55),(width/2,-6.55),(width/2,6.55),(-width/2,6.55)]:
            pts.append([x+u*math.cos(a)+v*math.sin(a),y-u*math.sin(a)+v*math.cos(a)])
        m.add(t['board']+'-'+t['reference']+'-WAGO-body-envelope',polygon_prism(pts,z+dz,4.5),
              'hardware','manufacturer envelope',False,False,terminal=True)
        m.add(t['board']+'-'+t['reference']+'-button-tool-access',polygon_prism(pts,z+dz+4.5,18),
              'keepout','service reservation',False,False,service=True)
    for r in data['routes']:
        print('sweeping '+r['name'],flush=True)
        p=np.array(r['points']);wire=tube(p,r['wire_od_mm']/2)
        m.add(r['name']+'-power-wire',wire,'cables','Alpha 6716' if r['group']=='usb5' else 'Alpha 6715',
              False,False,power_wire=True,wire_name=r['name'])
        ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        trim=3 if r['group']!='usb5' else 6;useful=p[(ss>=trim)&(ss<=ss[-1]-trim)]
        g=guide(useful,r['wire_od_mm'],c['guide_radial_clearance'],c['guide_wall'])
        if r['group']=='usb5' or g.BoundingBox().xlen>244:
            for i,(xx,ww) in enumerate([(0,179),(179,250)]):
                piece=g.intersect(box(xx,0,0,ww,260,60))
                m.add(r['name']+f'-guide-{i+1}',piece,'supports',harness_part=True,guide_for=r['name'])
        else:m.add(r['name']+'-guide',g,'supports',harness_part=True,guide_for=r['name'])
    print('18 source wire sweeps and continuous open guides built',flush=True)
    groups={}
    for r in data['routes']:groups.setdefault(r['group'],[]).append(r)
    groups['right-main-power']=groups['right-J2432']+groups['right-J2452']
    groups['left-main-power']=groups['left-J2430']+groups['left-J2460']
    strain_clamp(m,'harness-left-main-power',groups['left-main-power'],74,foot_x=70.75)
    strain_clamp(m,'harness-left-J2450',groups['left-J2450'],70.75)
    strain_clamp(m,'harness-right-main-power',groups['right-main-power'],299.25,
                 y_bounds=(36.4,72.8),low_screw_axis_x=300.)
    strain_clamp(m,'harness-right-J2462',groups['right-J2462'],299.25,y_bounds=(109.5,120.))
    for xx,label in [(70.75,'left'),(299.25,'right')]:strain_clamp(m,'harness-USB-'+label,groups['usb5'],xx)
    strain_clamp(m,'harness-BMS',groups['bms-power'],129,front_gap=True,foot_x=124,
                 dogleg=True,width=4,y_bounds=(161.2,176.),low_screw_xy=(125.8,161.8))
    middle_support(m,'left',groups['usb5'],113)
    middle_support(m,'right',groups['usb5'],237)
    integrate_guides(m,groups)
    raw=[]
    for pin,yy in [(1,169.448),(2,173.448)]:
        pp=np.column_stack([np.linspace(224.9,253,121),np.full(121,yy),np.full(121,pcb_top('bms')+2.3)])
        row={'points':pp.tolist(),'wire_od_mm':1.7526}
        raw.append(row)
        m.add(f'raw-J2-pin-{pin}-partial-pigtail',tube(pp,1.7526/2),'routes','unmeasured full harness',False,False)
    strain_clamp(m,'harness-raw-J2',raw,247,front_gap=True)
    access=json.loads(input_path('bms-connector-access.json').read_text())
    for con in access['connectors']:
        if '2060' not in con['manufacturer_part_number']:
            m.add('bms-'+con['reference']+'-mated-envelope',polygon_prism(con['installed_mated_polygon_mm'],pcb_top('bms'),con['reserved_height_above_pcb_mm']),
                  'hardware','manufacturer envelope',False,False,terminal=True)
        if con['installed_withdrawal_polygon_mm']:
            m.add('bms-'+con['reference']+'-withdrawal',polygon_prism(con['installed_withdrawal_polygon_mm'],pcb_top('bms'),con['reserved_height_above_pcb_mm']),
                  'keepout','service reservation',False,False,service=True)
    for board,sign in [('left',1),('right',-1)]:
        e=next(e for e in groups['usb5'][0]['ends'] if e['board']==board);x,y,h=e['point']
        m.add(board+'-XT30-14mm-withdrawal',box(x if sign>0 else x-14,y-7,pcb_top(board),14,14,6),
              'keepout','service reservation',False,False,service=True)
    m.add('raw-pack-J2-wire-exit-reservation',box(224.9,167,pcb_top('bms'),24,10,8),'keepout','unmeasured raw pack route',False,False)
    m.findings.append('J2 pin 1 is raw negative and pin 2 raw positive. Raw-pack, taps and probes need battery lead/exit measurements; no completed route is claimed.')
    h=CONFIG['hinges'];hy=h['pivot_y'];hh=h['pivot_height'];r=max(10,c['edp_min_bend_radius'])
    m.add('eDP-dynamic-bend-corridor',cq.Solid.makeTorus(r,c['edp_bundle_diameter']/2+1,cq.Vector(63,-hy,hh),cq.Vector(1,0,0)),
          'keepout','reservation',False,False)
    m.add('eDP-service-slack-bay',box(66,2,16,52,21,6),'keepout','reservation',False,False)
    m.add('eDP-base-route-datum',stroke([(210,-10,17),(175,12,21),(95,10,19),(63,14,hh-10),(63,20,hh)],1.5),'routes','unverified route',False,False)
    m.add('eDP-lid-route-datum',stroke([(63,-hy-12,hh+7),(63,-hy-27,hh+12),(75,-hy-30,hh+12)],1.5),'routes','unverified route',True,False)
    m.cable_records.append({'loom':'eDP','minimum_bend_corridor_radius_mm':r,'required_slack_mm':math.pi*r+c['edp_service_slack'],
                            'status':'corridor only; actual cable, constant-length sweep and lid endpoint unknown'})
    for i,y in enumerate([133,198]):
        m.add(f'SMA-{i+1}-plug-and-wrench-access',cq.Solid.makeCylinder(10,45,cq.Vector(356,-y,pcb_top('radio')+.38),cq.Vector(1,0,0)),
              'keepout','service reservation',False,False,service=True)
    m.findings.extend(['Guide bores and TPU clamp liners require calibration and pull tests; +/-0.2 mm wire position is not a loose-wire guarantee.',
                       'The eDP corridor is not a constant-length flex simulation. No pinch-free cable qualification is claimed.',
                       'Small signal harnesses, keyboard FFC, OLED, speaker and trackpad cable ends still need measured dressing and independent retention.'])
    from ground_braids import add as add_ground_braids
    add_ground_braids(m)


if __name__=='__main__':
    from build import Model
    m=Model();add_cables(m)
    render([p for p in m.parts if p['group'] not in ['keepout','routes']],HERE/'views/harness-detail.png',
           'saved WAGO / Alpha harness with independent split clamps',direction=(.2,-.6,1.5))

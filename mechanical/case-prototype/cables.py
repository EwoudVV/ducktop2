"""Explicit plug envelopes, numbered wire curves and hinge cable reservations."""
import math
import numpy as np
import cadquery as cq
from cad import box, cylinder, compound


def arch(a,b,z1,z2,r,length,wire_radius,hidden=8):
    """Exact tangent circular arcs between upward vertical wire exits.

    Extra vertical lead accommodates unequal connector heights. The 2D curve
    lies in the plane joining the actual numbered pin locations.
    """
    a=np.array([a[0],-a[1]]);b=np.array([b[0],-b[1]])
    distance=float(np.linalg.norm(b-a));u=(b-a)/distance
    zbase=max(z1,z2);extra=abs(z2-z1);free=length-hidden-extra
    if distance>=2*r:
        minimum=math.pi*r+distance-2*r
        segments=[('arc',(r,0),math.pi,math.pi/2),('line',(r,r),(distance-r,r)),('arc',(distance-r,0),math.pi/2,0)]
    else:
        alpha=math.acos((distance/2+r)/(2*r));h=math.sqrt(4*r*r-(distance/2+r)**2)
        minimum=r*(math.pi+4*alpha)
        segments=[('arc',(-r,0),0,alpha),('arc',(distance/2,h),math.pi+alpha,-alpha),('arc',(distance+r,0),math.pi-alpha,math.pi)]
    if free<minimum:
        return None,[],{'fits_length':False,'minimum_cut_length_mm':minimum+hidden+extra,'requested_cut_length_mm':length,'pin_span_mm':distance,'bend_radius_mm':r}
    leg=(free-minimum)/2
    def pt(x,z):return cq.Vector(float(a[0]+u[0]*x),float(a[1]+u[1]*x),float(zbase+leg+z))
    edges=[];sample=[]
    first=cq.Vector(float(a[0]),float(a[1]),z1);start=pt(0,0)
    if (start-first).Length>1e-6:edges.append(cq.Edge.makeLine(first,start))
    sample.extend([first.toTuple(),start.toTuple()])
    for seg in segments:
        if seg[0]=='line':
            q1=pt(*seg[1]);q2=pt(*seg[2])
            if (q2-q1).Length>1e-6:edges.append(cq.Edge.makeLine(q1,q2))
            sample.extend([q1.toTuple(),q2.toTuple()])
        else:
            _,(cx,cz),ang1,ang2=seg
            f=lambda t:pt(cx+r*math.cos(t),cz+r*math.sin(t))
            edges.append(cq.Edge.makeThreePointArc(f(ang1),f((ang1+ang2)/2),f(ang2)))
            sample.extend(f(t).toTuple() for t in np.linspace(ang1,ang2,50))
    end=pt(distance,0);last=cq.Vector(float(b[0]),float(b[1]),z2)
    if (last-end).Length>1e-6:edges.append(cq.Edge.makeLine(end,last))
    sample.extend([end.toTuple(),last.toTuple()])
    path=cq.Wire.assembleEdges(edges)
    profile=cq.Wire.makeCircle(wire_radius,first,cq.Vector(0,0,1))
    solid=cq.Solid.sweep(profile,[],path,True,False)
    return solid,sample,{'fits_length':True,'cut_length_mm':length,'hidden_allowance_mm':hidden,
        'exposed_length_mm':path.Length(),'minimum_bend_radius_mm':r,'pin_span_mm':distance,
        'max_height_mm':solid.BoundingBox().zmax,'curve':'tangent circular arcs; bundle not independently routed'}


def add_cables(m):
    from build import CONFIG,fp,installed,pcb_top,stroke
    c=CONFIG['cables']
    for name,ends,count in [('left',[('center','J2430'),('left','J2431')],12),('right',[('center','J2432'),('right','J2433')],10)]:
        data=[]
        for board,ref in ends:
            f=fp(board,ref);pins={p['number']:installed(board,p['position']) for p in f['pads'] if p['number'].isdigit()}
            data.append(pins)
            pts=list(pins.values());xmin=min(p[0] for p in pts)-4.5;xmax=max(p[0] for p in pts)+4.5
            ymin=min(p[1] for p in pts)-4.5;ymax=max(p[1] for p in pts)+4.5
            plug=box(xmin,ymin,pcb_top(board),xmax-xmin,ymax-ymin,c['microfit_mated_height'])
            # Individual exit bores make pin numbering visible in the housing envelope.
            for px,py in pts:plug=plug.cut(cylinder(px,py,pcb_top(board)+10,1,8))
            m.add(ref+'-mated-housing-envelope',plug,'hardware','reference',False,False)
        wires=[]
        for pin in range(1,count+1):
            a=data[0][str(pin)];b=data[1][str(pin)]
            shape,samples,record=arch(a,b,pcb_top(ends[0][0])+c['microfit_mated_height'],pcb_top(ends[1][0])+c['microfit_mated_height'],
                          c['microfit_bend_radius'],c['microfit_wire_length'],c['microfit_wire_radius'],c['hidden_crimp_allowance'])
            record.update(loom=name,pin=pin,a_xy=a,b_xy=b,reference_parts=[x[1] for x in ends])
            m.cable_records.append(record)
            if shape:
                m.add(f'{name}-loom-wire-{pin}',shape,'cables','wire',False,False)
                wires.append((pin,np.array(samples)))
        # Conservative sampled centre-distance screen, excluding shared housing exits.
        conflicts=[]
        for i,(pin,a) in enumerate(wires):
            for pin2,b in wires[i+1:]:
                d=float(np.linalg.norm(a[:,None,:]-b[None,:,:],axis=2).min())
                if d<2*c['microfit_wire_radius']+.3:
                    conflicts.append({'pins':[pin,pin2],'sampled_center_distance_mm':round(d,3)})
        m.cable_records.append({'loom':name,'bundle_clearance_screen':conflicts,'passed':not conflicts,
                               'boundary':'sampled independently calculated wires; no bundle routing qualification'})
        if conflicts:m.findings.append(f'{name} Micro-Fit loom: {len(conflicts)} wire-pair clearance conflicts in independent arches; dress/replace harness before loaded assembly')
    # BMS connector bodies follow the retained drawing bounds, not a thin generic line.
    ends=[('center','J2071'),('bms','J2072')];pins=[]
    for board,ref in ends:
        f=fp(board,ref);x,y=installed(board,f['position'])
        plug=box(x-4.265,y-4.82,pcb_top(board),8.53,9.64,c['bms_mated_height'])
        m.add(ref+'-mated-envelope',plug,'hardware','reference',False,False)
        pins.append({p['number']:installed(board,p['position']) for p in f['pads'] if p['number'].isdigit()})
    for pin in ['1','2']:
        a=pins[0][pin];b=pins[1][pin]
        _,_,strict=arch(a,b,pcb_top('center')+17.56,pcb_top('bms')+17.56,17.78,75,.889)
        shape,samples,proposed=arch(a,b,pcb_top('center')+17.56,pcb_top('bms')+17.56,7,75,.925)
        proposed.update(loom='BMS',pin=pin,status='candidate 7 mm radius ONLY; wire selection and bend rating unresolved',alpha3253_screen=strict)
        m.cable_records.append(proposed)
        if shape:m.add('BMS-proposed-flex-wire-'+pin,shape,'cables','reference',False,False)
    m.findings.append('BMS 75 mm budget does not accommodate the 17.78 mm Alpha 3253 arch. Displayed 7 mm candidate requires a qualified flexible wire or connector/routing change.')
    # Six-position raw pack Mega-Fit and outgoing cable reservation.
    f=fp('bms','J2');x,y=installed('bms',f['position'])
    pts=[installed('bms',v) for ring in f['courtyards']['front'] for v in ring]
    if pts:
        xmin=min(v[0] for v in pts);xmax=max(v[0] for v in pts);ymin=min(v[1] for v in pts);ymax=max(v[1] for v in pts)
        m.add('BMS-MegaFit-plug-reservation',box(xmin,ymin,pcb_top('bms'),xmax-xmin,ymax-ymin,16.78),'hardware','reference',False,False)
        m.add('BMS-cell-tap-wire-bends',box(xmin,ymin,pcb_top('bms')+16.78,xmax-xmin,20,20),'keepout','reservation',False,False)
    # Underside control/raw probe sockets are separate, insulated routes below BMS.
    for ref in ['J2074','J2200']:
        f=fp('bms',ref);x,y=installed('bms',f['position'])
        m.add(ref+'-underside-plug-and-bend',box(x-5,y-4,3.4,10,12,7),'keepout','reservation',False,False)
    # Direct USB power route: real connector endpoints, rounded-corner budget remains in docs.
    a=installed('left',fp('left','J2434')['position']);b=installed('right',fp('right','J2435')['position'])
    m.add('USB5-direct-loom-corridor',compound([box(a[0],a[1]-2,16,270-a[0],4,5),box(268,b[1],16,4,a[1]-b[1],5),box(270,b[1]-2,16,b[0]-270,4,5)]),'keepout','reservation',False,False)
    # Hinge cable bend volume and slack bay. A 180-degree sweep pays out pi*R.
    h=CONFIG['hinges'];hx=63;hy=h['pivot_y'];hh=h['pivot_height'];r=max(10,c['edp_min_bend_radius'])
    torus=cq.Solid.makeTorus(r,c['edp_bundle_diameter']/2+1,cq.Vector(hx,-hy,hh),cq.Vector(1,0,0))
    m.add('eDP-dynamic-bend-corridor',torus,'keepout','reservation',False,False)
    m.add('eDP-service-slack-bay',box(66,2,17,52,21,6),'keepout','reservation',False,False)
    route=[(210,-10,18),(175,12,22),(95,-10,20),(63,14,max(8,hh-10)),(63,20,hh)]
    m.add('eDP-base-route-datum',stroke(route,1.5),'cables','reference',False,False)
    m.add('eDP-lid-route-datum',stroke([(63,-hy-12,hh+7),(63,-hy-27,hh+12),(75,-hy-30,hh+12)],1.5),'cables','reference',True,False)
    m.cable_records.append({'loom':'eDP','dynamic_bend_radius_mm':r,'bundle_diameter_mm':3,
        'sweep_length_change_bound_mm':math.pi*r,'required_service_slack_mm':math.pi*r+c['edp_service_slack'],
        'slack_bay_mm':[52,21,6],'status':'planar slack loop corridor and pay-out allowance only; connector datums, vendor flex radius and constant-length harness fit pending',
        'route_waypoints_are_not_a_released_harness':True})
    # Cable clamp bodies have a soft-lined channel; fastening never uses connector pads.
    dt=CONFIG['base']['deck_top'];rear=CONFIG['base']['rear_wall_top'];floor=CONFIG['base']['floor']
    for i,(x,y,z) in enumerate([(63,-16,max(floor+1,rear-6)),(93,-16,max(floor+1,min(30,rear-6))),(108,139,dt-16),(268,112,dt-19)]):
        clamp=box(x-6,y-3,z,12,6,3)
        clamp=clamp.cut(box(x-2,y-4,z-.1,4,8,2))
        for xx in [x-4.5,x+4.5]:clamp=clamp.cut(cylinder(xx,y,z-.1,1.1,3.2))
        m.add(f'cable-clamp-{i+1}',clamp,'supports')
        for xx in [x-4.5,x+4.5]:m.mount(f'cable-clamp-{i+1}-{xx}',xx,y,z+3,'soft-lined clamp to separate bracket',2.2,'M2',3,6,'insulating liner','bracket position and service loop fit pending')
        if i<2:
            stand=box(x-7,y-4,floor,14,8,z-floor)
            for xx in [x-4.5,x+4.5]:stand=stand.cut(cylinder(xx,y,floor-.1,.8,z-floor+.2))
            m.add(f'cable-clamp-{i+1}-pedestal',stand,'supports')
            m.mount(f'cable-clamp-{i+1}-pedestal',x,y,floor,'pedestal bonded to rear spine after cable fitting',0,'none',z-floor,'adhesive','insulating','bond preparation and pull test pending')
    m.findings.append('eDP lines are route datums, not a constant-length flex simulation; the annular corridor and slack bay must be fitted with the actual cable')
    # Other harnesses use actual board connector datums. Their module-side
    # ends and smooth dressing are still provisional and are labelled as routes.
    def guide(name,points,r=.7,detail='route corridor; exact cable and bend fit pending'):
        pts=[(x,-y,z) for x,y,z in points]
        m.add(name+'-route',stroke(pts,r),'routes','reference',False,False)
        length=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
        m.cable_records.append({'loom':name,'waypoints_X_Y_height_mm':points,'polyline_length_mm':length,
                               'status':detail,'not_a_cut_length':True})
    def anchor(board,ref,z):return [*installed(board,fp(board,ref)['position']),z]
    for name,a,b,width in [('left-signal',('left','FPC101'),('center','FPC102'),20.5),('right-signal',('center','FPC103'),('right','FPC104'),25.5)]:
        pa=anchor(*a,pcb_top(a[0])+4);pb=anchor(*b,pcb_top(b[0])+4)
        guide(name,[pa,[(pa[0]+pb[0])/2,pa[1],19],pb],.3,
              f'Molex 51 +/-2 mm shielded cable, {width} mm contact-span reference; exit/insertion and bend shape unmeasured')
        m.add(name+'-ribbon-width-envelope',box(min(pa[0],pb[0]),pa[1]-width/2,12,abs(pb[0]-pa[0]),width,7),'keepout','reservation',False,False)
    kh=CONFIG['boards']['keyboard']['bottom_height']
    guide('keyboard-30-pin',[anchor('center','J310',10),[110,49,14],[110,49,kh-5.5],[321,61,kh-5.5],[321,61,kh+2],anchor('keyboard','J320',kh+2)],.6,
          'route above cooling and below carrier, then through right-hand release window; FFC width, bends and continuity pending')
    guide('radio-30-pin',[anchor('center','J2300',10),[85,128,16],[274,128,16],[280,170,18],anchor('radio','J1',pcb_top('radio')+2)],.6,
          'FFC ends from saved boards; approach radio from its left edge; width, fold and exact length pending')
    guide('BMS-control',[anchor('center','J2073',10.95),[176.5,149.45,10.95],[176.5,149.45,6.5],anchor('bms','J2074',7.45)],.4,
          'under-board control route through 1.5 mm notch clearance; 75 mm budget, smooth bends and pin map require fit/continuity test')
    guide('trackpad-USB',[anchor('center','J58',9),[141,161,16],[108,139,dt-14],[100,181,dt-4],[109,190,dt-3]],1.3,
          'J58 solder lands are fixed; trackpad left-side USB-C endpoint is an explicit assumption; strain relief required before solder joints')
    for i,(ref,(x,y)) in enumerate(zip(['J41','J45'],CONFIG['oled']['xy'])):
        guide(f'oled-{i+1}',[anchor('center',ref,12),[235,140,16],[360,140,17],[360,150,dt-6.5],[x+13.65,y-2,dt-5]],.65,
              'four-wire GH harness, routed around radio edge; OLED connector location and tray entry pending')
    for i,x in enumerate(CONFIG['cells']['x']):
        guide(f'cell-temperature-{i+1}',[anchor('bms','J2200',7.45),[182.6,184,7.45],[x+50,185,15],[x+50,206,14.2]],.4,
              'insulated probe pair; dress along tray edges with a loose lead to the cell surface, pending full pack measurement')
    for i,y in enumerate([133,198]):
        wrench=cq.Solid.makeCylinder(10,45,cq.Vector(356,-y,pcb_top('radio')+.38),cq.Vector(1,0,0))
        m.add(f'SMA-{i+1}-plug-and-wrench-access',wrench,'keepout','reservation',False,False)

"""Fan-lead envelopes, a carrier guide and a separate floor clamp."""
import numpy as np,math
BASE_WIRE_H=14.0
CROSSOVER_H=21.15
FAN_EXIT_H=10.0

def route_points():
 p=[]
 def line(a,b):
  n=max(2,math.ceil(np.linalg.norm(np.array(b)-a)/.15)+1)
  p.extend(np.linspace(a,b,n).tolist()[1:] if p else np.linspace(a,b,n).tolist())
 def arc(cx,cy,r,start,stop,h):
  angles=np.linspace(start,stop,math.ceil(abs(stop-start)*r/.15)+1)
  a=[[cx+r*math.cos(t),cy+r*math.sin(t),h] for t in angles]
  p.extend(a[1:] if p else a)
 line([168,74.225,7.6],[168,70,7.6])
 r=10;ang=math.acos(1-(BASE_WIRE_H-7.6)/(2*r));north=r*math.sin(ang)
 for t in np.linspace(0,ang,101)[1:]:p.append([168,70-r*math.sin(t),7.6+r*(1-math.cos(t))])
 y0=70-north;h0=p[-1][2]
 for t in np.linspace(ang,0,101)[1:]:p.append([168,y0-r*(math.sin(ang)-math.sin(t)),h0+r*(math.cos(t)-math.cos(ang))])
 y=p[-1][1]
 arc(158,y,10,0,-math.pi,BASE_WIRE_H)
 line(p[-1],[148,85,BASE_WIRE_H]);arc(158,85,10,math.pi,math.pi/2,BASE_WIRE_H)
 line(p[-1],[220,95,BASE_WIRE_H])
 for x in np.linspace(220,250,201)[1:]:
  t=(x-220)/30;p.append([x,95+12*t*t*(3-2*t),BASE_WIRE_H])
 line(p[-1],[280,107,BASE_WIRE_H]);arc(280,119,12,-math.pi/2,0,BASE_WIRE_H)
 line(p[-1],[292,162,BASE_WIRE_H]);arc(309,162,17,math.pi,math.pi/2,BASE_WIRE_H)
 line(p[-1],[320.1,179,BASE_WIRE_H]);arc(320.1,169,10,math.pi/2,0,BASE_WIRE_H)
 p=np.array(p);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
 w=np.clip((s-(s[-1]-40))/40,0,1);w=w*w*(3-2*w);p[:,2]-=(BASE_WIRE_H-FAN_EXIT_H)*w
 def smooth(v):
  v=np.clip(v,0,1);return v*v*(3-2*v)
 p[:,2]+=(CROSSOVER_H-BASE_WIRE_H)*smooth((p[:,0]-250)/24)*smooth((150-p[:,1])/27)
 return p


import json,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'mechanical/case-prototype'))
import cadquery as cq
from cad import box,cylinder,compound
from cables import path_edge,tube,sweep_rect

_GEOMETRY=None


def config():return json.loads((HERE/'fan-harness.json').read_text())


def factory_exit_zone():
    return box(327.9,168.7,7.8,4.5,1.5,4.3)


def header_wire_entry_zone():return box(164.9,73.9,5.8,6.2,.65,3.8)


def hollow_sweep(points,outer,inner):
    # CadQuery's hollow sweep subtracts two close spline solids. Sweep the
    # annular face directly to avoid that expensive Boolean construction.
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
    offset=np.asarray(points[0],dtype=float)
    edge=path_edge(np.asarray(points,dtype=float)-offset);origin=edge.startPoint();normal=edge.tangentAt(0)
    face=cq.Face.makeFromWires(cq.Wire.makeCircle(outer,origin,normal),[cq.Wire.makeCircle(inner,origin,normal)])
    builder=BRepOffsetAPI_MakePipe(cq.Wire.assembleEdges([edge]).wrapped,face.wrapped)
    s=cq.Shape.cast(builder.Shape()).translate((offset[0],-offset[1],offset[2]))
    assert s.isValid() and len(s.Solids())==1
    return s


def geometry():
    global _GEOMETRY
    if _GEOMETRY is not None:return _GEOMETRY
    c=config();p=route_points();s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    def between(a,b):
        mid=p[(s>a)&(s<b)][::5]
        q=np.vstack([[np.interp(a,s,p[:,i]) for i in range(3)],mid,[np.interp(b,s,p[:,i]) for i in range(3)]])
        return q[np.r_[True,np.linalg.norm(np.diff(q,axis=0),axis=1)>1e-7]]
    model=np.vstack([p[::5],p[-1:]])
    model=model[np.r_[True,np.linalg.norm(np.diff(model,axis=0),axis=1)>1e-7]]
    edge=path_edge(model)
    half=c['heatshrink_length_each_mm']/2
    tails=[r['factory_run_to_splice_mm'] for r in c['pins']]
    splice=between(s[-1]-max(tails)-half,s[-1]-min(tails)+half)
    fanout=between(0,20)
    liner_stations=np.flatnonzero((p[:,0]>=310.5)&(p[:,0]<=318.5)&(abs(p[:,1]-179)<1e-6))
    assert len(liner_stations)>10
    print('building fan wire and splice envelopes',flush=True)
    # Separate overlapping reference envelopes avoid a fragile tangent
    # union. These are dressing limits, not a manufactured solid or mass.
    shape=compound([tube(model,1.6),tube(splice,2.6),sweep_rect(fanout,-2.6,-1.6,5.2,3.2)])
    limit=compound([tube(model,1.8),tube(splice,2.8),sweep_rect(fanout,-2.8,-1.8,5.6,3.6)])
    assert shape.isValid() and limit.isValid()
    _GEOMETRY={'config':c,'points':p,'stations':s,'model_points':model,'edge':edge,'shape':shape,'limit':limit,
               'splice_points':splice,'fanout_points':fanout,'between':between,
               'clamp_points':between(s[-1]-34,s[-1]-10),
               'liner_points':between(s[liner_stations[0]],s[liner_stations[-1]])}
    print('fan harness envelopes ready',flush=True)
    return _GEOMETRY


def carrier_guide():
    # Long independent arms can flex sideways; the central stop limits lift.
    def clip(x,y,length,rotation):
        s=box(-2.5,-length/2,19.5,5,length,.6)
        for arm,lip in [(-2.5,-2.5),(1.9,1.35)]:
            s=s.fuse(box(arm,-length/2,BASE_WIRE_H-1.9,.6,length,20.1-BASE_WIRE_H+1.9),box(lip,-length/2,BASE_WIRE_H-1.9,1.15,length,.6))
        s=s.fuse(box(-.6,-length/2,BASE_WIRE_H+1.9,1.2,length,20.1-BASE_WIRE_H-1.9))
        return s.rotate((0,0,0),(0,0,1),rotation).translate((x,-y,0))
    sections=[clip(148,70,6,0),clip(172,95,4,90),clip(214,95,4,90)]
    t=22/30;y=95+12*t*t*(3-2*t);angle=math.degrees(math.atan(2.4*t*(1-t)))
    forward=clip(242,y,2,90-angle).fuse(box(239.5,100,19.5,5,3,1))
    sections.append(forward)
    # The crossover guide cantilevers from the front of the carrier. Its
    # lower mouth keeps material away from the existing USB power guide.
    high=cq.Solid.makeCylinder(2.3,6,cq.Vector(274,-107,21.15),cq.Vector(1,0,0))
    high=high.cut(cq.Solid.makeCylinder(1.85,6.2,cq.Vector(273.9,-107,21.15),cq.Vector(1,0,0)))
    high=high.cut(box(273.9,105.6,18.5,6.2,2.8,2))
    high=high.fuse(box(274,100,20,6,5,1.5))
    sections.append(high)
    return compound(sections)


def carrier_shape(carrier):
    for shape in carrier_guide().Solids():carrier=carrier.fuse(shape)
    return carrier


def fan_wire_brace():
    # This one-millimetre plate replaces the top millimetre of spacer 2.
    # The long leg stays outside the fan's left wall, then supports the splices.
    from cooler_hardware import annulus
    s=annulus(301.75,165.75,12.2,2.4,1.1,1)
    s=s.fuse(box(300.95,165.75,12.2,1.6,6.75,1),box(295.5,147,12.2,2,21,1.5))
    s=s.fuse(box(300.95,170.5,13.1,1.6,2,4.9),box(295.5,166,13.6,2,2,4.4),
             box(295.5,166,16.5,2,6.5,1.5),box(295.5,170.5,16.5,7.05,2,1.5))
    h=BASE_WIRE_H+(CROSSOVER_H-BASE_WIRE_H)*((2/27)**2)*(3-2*(2/27))
    direction=cq.Vector(0,-1,-.11).normalized();centre=cq.Vector(292,-148,h)
    ring=cq.Solid.makeCylinder(3.4,2,centre-direction,direction)
    ring=ring.cut(cq.Solid.makeCylinder(2.9,2.2,centre-direction*1.1,direction))
    ring=ring.cut(box(289.75,145,h-3.9,4.5,6,2.8))
    s=s.fuse(ring,box(294.9,147,13.2,2.6,2,1))
    s=s.cut(cylinder(301.75,165.75,12.1,1.1,1.2))
    assert s.isValid() and len(s.Solids())==1
    return s


def fan_mount_zone():return box(299.1,163.1,11.9,5.3,6.8,1.6)


def clamp_base():
    g=geometry();c=g['config']['clamp']
    s=box(309,171.5,1.15,11,15,c['cap_bottom_H']-1.15)
    print('cutting fan clamp base',flush=True)
    s=s.cut(tube(g['clamp_points'],2.0))
    for y in c['screw_y']:
        s=s.cut(cylinder(c['x'],y,c['insert_top_H']-c['insert_length_mm'],c['insert_body_allocation_mm']/2+.01,c['insert_length_mm']))
        s=s.cut(cylinder(c['x'],y,6.5,1.1,10))
    return s


def floor_shape(floor):
    s=floor.fuse(clamp_base())
    print('fan clamp joined to floor',flush=True)
    assert s.isValid() and len(s.Solids())==1
    return s


def card_spaces():
    c=config();rows=[];top=c['layout_datums']['main_bottom_H']+1.6
    for r in c['card_spaces']:
        x,y,w,d=r['xywh'];low=top+r['bottom_above_host_PCB_mm'];high=top+r['top_above_host_PCB_mm']
        rows.append(dict(name=r['name']+'-selection-space',shape=box(x,y,low,w,d,high-low),group='keepout',
                         color=(.65,.4,.8,.15),moving=False,fan_card_space=True))
    return rows


def make_parts():
    g=geometry();c=g['config']['clamp'];rows=[]
    print('building fan plug and clamp hardware',flush=True)
    def add(name,shape,color=(.22,.27,.3),group='wiring',**extra):
        # The two long reference envelopes were validated in geometry().
        # They are not masses, so do not integrate their overlapping volumes.
        assert shape.Solids(),name
        if shape is not g['shape'] and shape is not g['limit']:assert shape.isValid(),name
        rows.append(dict(name=name,shape=shape,color=color,group=group,moving=False,fan_harness=True,**extra))
    add('fan-loom-envelope',g['shape'])
    add('fan-loom-position-space',g['limit'],(.3,.6,.9,.2),'keepout')
    add('fan-J52-plug-envelope',box(164.675,74.225,5.6,6.65,2.2,4.5),(.83,.84,.8))
    add('fan-J52-withdrawal-space',box(164.675,66.225,5.6,6.65,10.2,4.5),(.3,.6,.9,.2),'keepout',service=True,
        service_removes=['deck','keyboard-pcb-and-available-models','keyboard-carrier-reservation','key-travel-and-cap-envelopes'],
        service_moves=['fan-J52-plug-envelope','fan-loom-envelope'])
    cap=box(309,171.5,c['cap_bottom_H'],11,15,c['cap_top_H']-c['cap_bottom_H'])
    cap=cap.cut(tube(g['clamp_points'],2.0))
    for y in c['screw_y']:cap=cap.cut(cylinder(c['x'],y,11,1.1,6))
    add('fan-strain-cap',cap,(.28,.49,.55))
    print('building hollow fan clamp liner',flush=True)
    liner=hollow_sweep(g['liner_points'],1.9,1.65)
    add('fan-strain-liner',liner,(.15,.18,.2))
    add('fan-splice-support-brace',fan_wire_brace(),(.28,.49,.55),'cooling',remote_cooler=True,cooler_hardware=True)
    from cooler_hardware import annulus
    seat=c['cap_top_H']+c['washer_thickness_mm']
    for i,y in enumerate(c['screw_y'],1):
        x=c['x'];top=c['insert_top_H'];length=c['insert_length_mm']
        add(f'fan-clamp-insert-{i}',annulus(x,y,top-length,1.8,1,length),(.63,.49,.2))
        add(f'fan-clamp-washer-{i}',annulus(x,y,c['cap_top_H'],2.25,1.1,c['washer_thickness_mm']),(.6,.62,.65))
        screw=cylinder(x,y,seat-c['screw_length_mm'],1,c['screw_length_mm']).fuse(cylinder(x,y,seat,2,1.8))
        add(f'fan-clamp-screw-{i}',screw,(.42,.44,.47))
        add(f'fan-clamp-driver-{i}',cylinder(x,y,seat+1.8,3,20),(.3,.6,.9,.2),'keepout',service=True,
            service_removes=['deck','oled-1-module','oled-2-module'])
    rows.extend(card_spaces())
    return rows

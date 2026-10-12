"""Insulated metal keyboard carrier, edge retention and case supports."""
import json,math,functools
from pathlib import Path
import cadquery as cq
import remote_cooler,usb_harness,fan_guide_mounts
from cad import box,cylinder,compound
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def config():return json.loads((HERE/'keyboard-mounts.json').read_text())
SUPPORTS=config()['side_supports']['locations']
INV=json.loads((ROOT/'mechanical/case-prototype/board-inventory.json').read_text())['boards']['keyboard']
CLIPS=[(*p,True) for p in config()['retention']['rear_clip_xy_mm']]+[(*p,False) for p in config()['retention']['front_clip_xy_mm']]
FILM=.127

def hexagon(x,y,h,flat,t):
 return cq.Workplane('XY').polygon(6,flat/math.cos(math.pi/6)).extrude(t).val().translate((x,-y,h))
def clinch(x,y,h,shank):
 return cylinder(x,y,h-1.75,3.3,1.75).fuse(cylinder(x,y,h,2.1,shank)).cut(cylinder(x,y,h-1.85,1,1.95+shank))
def csk(x,y,top,length):
 return cylinder(x,y,top-length-.24,1,length+.24-1.2).fuse(cq.Solid.makeCone(1,2.2,1.2,cq.Vector(x,-y,top-1.2)))
def switch_cutters(extra,z,height):
 groups=[]
 for f in INV['footprints']:
  if not f['reference'].startswith('SW'):continue
  assert abs(f['rotation'])<1e-9
  holes=[h for h in INV['holes'] if h['reference']==f['reference']];assert len(holes)==3
  cs=[cylinder(h['position'][0]+24.75,h['position'][1]+19.7,z,h['drill'][0]/2+extra,height) for h in holes]
  x,y=f['position'][0]+24.75,f['position'][1]+19.7
  window=box(x-5.05-extra,y+2.2-extra,z,3.8+2*extra,2+2*extra,height)
  groups.append(cs[0].fuse(cs[1],cs[2],window))
 return compound(groups)
@functools.lru_cache(maxsize=1)
def plate_and_film():
 p=box(41.25,19,20,275.5,82,1.2).cut(box(306,50,19.9,24,23,1.4))
 for x in [130,225]:p=p.fuse(box(x-5,99,20,10,10,1.2)).cut(cylinder(x,105.5,19.9,1.1,1.4))
 for x,y in fan_guide_mounts.config()['mounts_xy_mm']:
  front=y+(2 if x==277 else 3.5)
  p=p.fuse(box(x-5,99,20,10,front-99,1.2)).cut(cylinder(x,y,19.9,1.1,1.4)).cut(box(x+2.6,y-1.1,19.9,1.8,2.2,1.4))
 for x,y,rear in CLIPS:p=p.fuse(cylinder(x,y,20,5.2,1.2))
 for side,y in SUPPORTS:
  x=37 if side=='left' else 321
  p=p.fuse(box(x-5.25,y-4,20,10.5,8,1.2)).cut(cylinder(x,y,19.9,1.1,1.4))
 for x,y,rear in CLIPS:p=p.cut(cylinder(x,y,19.9,2.11,1.4))
 pipe={**remote_cooler.config()['pipes'],'bottom_H':19.8,'height_mm':1.6,'position_allowance_mm':.5}
 for off in pipe['lane_offsets_mm']:p=p.cut(remote_cooler.pipe_solid(pipe,off,envelope=True))
 print('cutting carrier switch clearances',flush=True)
 p=p.cut(switch_cutters(.4,19.9,1.5))
 film=box(42.25,20,21.2,273.5,80,FILM).cut(switch_cutters(.25,21.1,.4))
 assert p.isValid() and len(p.Solids())==1,('plate',len(p.Solids()))
 assert film.isValid() and len(film.Solids())==1
 return p,film

@functools.lru_cache(maxsize=1)
def parts():
 rows=[]
 def add(n,s,col=(.35,.6,.65),group='supports'):rows.append({'name':n,'shape':s,'group':group,'color':col,'keyboard_mount':True,'moving':False})
 for i,(side,y) in enumerate(SUPPORTS,1):
  left=side=='left';root=-.5 if left else 358.5;seat=37 if left else 321
  lo,hi=(-3,41.5) if left else (316.5,361)
  bar=box(lo,y-4,18.5,hi-lo,8,1.5).fuse(cylinder(seat,y,18.5,5.2,1.5))
  bar=bar.cut(cylinder(root,y,18.4,1.1,1.7)).cut(cylinder(seat,y,18.4,2.11,1.7));add(f'keyboard-support-bar-{i}',bar,(.6,.63,.65))
  webx=-5 if left else 361;footx=-5 if left else 355
  block=box(footx,y-5.5,16,8,11,2.5).fuse(box(webx,y-5.5,16,2,11,7.5))
  block=block.cut(hexagon(root,y,16.8,4.2,1.8)).cut(cylinder(root,y,15.9,1.1,2.7))
  add(f'keyboard-root-block-{i}',block)
  add(f'keyboard-root-nut-{i}',hexagon(root,y,16.9,4,1.6).cut(cylinder(root,y,16.8,1,1.8)),(.6,.6,.62))
  for label,x,top,length in [('root',root,20.3,4.24),('carrier',seat,21.5,5.24)]:
   add(f'keyboard-{label}-screw-{i}',cylinder(x,y,top-length,1,length).fuse(cylinder(x,y,top,2,2)),(.4,.42,.43))
   add(f'keyboard-{label}-washer-{i}',cylinder(x,y,top-.3,2.25,.3).cut(cylinder(x,y,top-.31,1.1,.32)),(.6,.6,.62))
  add(f'keyboard-inner-nut-{i}',clinch(seat,y,18.5,.97),(.6,.5,.3))
 for i,(x,y,rear) in enumerate(CLIPS,1):
  stand=cylinder(x,y,21.2,2.7,1)
  body=box(x-3,y-3,22.2,6,6,1.2)
  toe=box(x-1,19.4 if rear else 99.4,22.2,2,1.8 if rear else y-102.2,1.2)
  locator=box(x-2.5,18.5 if rear else 100.25,21.2,5,1.25 if rear else y-102.25,.8)
  shape=stand.fuse(body,toe,locator).cut(csk(x,y,23.4,6)).cut(cylinder(x,y,21.1,1.1,2.4))
  if i==5:shape=shape.fuse(box(41,100.25,21.2,21.5,1.25,.8),box(41,97.5,21.2,1,4,.8))
  if i==8:shape=shape.fuse(box(302.5,100.25,21.2,14.5,1.25,.8),box(316,97.5,21.2,1,4,.8))
  add(f'keyboard-edge-clip-{i}',shape)
  add(f'keyboard-clip-screw-{i}',csk(x,y,23.4,6),(.4,.42,.43))
  add(f'keyboard-clip-nut-{i}',clinch(x,y,20,.97),(.6,.5,.3))
 # Centre stop replaces the ordinary mounting screw at the existing H22.
 x,y=105,70
 standoff=hexagon(x,y,5.5,4,12).fuse(cylinder(x,y,1.5,1,4)).cut(cylinder(x,y,13.4,1,4.2))
 add('keyboard-center-stop-spacer',standoff,(.6,.6,.62))
 cap=cylinder(x,y,17.5,3,2.2).cut(csk(x,y,19.7,5)).cut(cylinder(x,y,17.4,1.1,2.4))
 add('keyboard-center-stop-cap',cap)
 add('keyboard-center-stop-screw',csk(x,y,19.7,5),(.4,.42,.43))
 assert all(p['shape'].isValid() and len(p['shape'].Solids())==1 for p in rows)
 return rows


def wall_shape(walls):
 for p in parts():
  if p['name'].startswith('keyboard-root-block-'):walls=walls.fuse(p['shape'])
 assert walls.isValid() and len(walls.Solids())==1
 return walls


def hardware_parts():
 return [p for p in parts() if not p['name'].startswith('keyboard-root-block-')]

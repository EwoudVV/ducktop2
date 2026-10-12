"""Fan guide pieces that release from above without lifting the loom."""
import functools
import json
from pathlib import Path
from cad import box, cylinder, compound

HERE=Path(__file__).resolve().parent


def config():
    return json.loads((HERE/'fan-guide-mounts.json').read_text())


def tab_front(x,y):
    return y+(2.0 if x==277 else 3.5)


def carrier_shape(carrier):
    c=config();thickness=c['carrier_top_H']-c['carrier_bottom_H']
    for x,y in c['mounts_xy_mm']:
        carrier=carrier.fuse(box(x-5,99,20,10,tab_front(x,y)-99,thickness))
        carrier=carrier.cut(cylinder(x,y,19.9,1.1,thickness+.2))
        carrier=carrier.cut(box(x+2.6,y-1.1,19.9,1.8,2.2,thickness+.2))
    assert carrier.isValid() and len(carrier.Solids())==1
    return carrier


@functools.lru_cache(maxsize=1)
def guides():
    import fan_harness
    c=config();cuts=box(40,18,20,278,83.2,20)
    for x,y in c['mounts_xy_mm']:
        cuts=cuts.fuse(box(x-5.2,98.8,20,10.4,tab_front(x,y)+.2-98.8,20))
    profiles=fan_harness.clip_profiles().Solids()
    assert len(profiles)==len(c['mounts_xy_mm'])==len(c['guide_arm_ends_xy_mm'])==5
    result=[]
    for i,(profile,(x,y),(cx,cy)) in enumerate(zip(profiles,c['mounts_xy_mm'],c['guide_arm_ends_xy_mm']),1):
        assert cx==x
        lo,hi=min(y,cy),max(y,cy)
        arm=box(x-2.5,lo,19,5,max(.5,hi-lo),1)
        boss=cylinder(x,y,17,2.5,3)
        bore_bottom=c['carrier_top_H']-c['screw']['nominal_shank_length_mm']-c['screw']['length_tolerance_mm']-.1
        shape=profile.fuse(arm,boss).cut(cuts).cut(cylinder(x,y,bore_bottom,1,20.1-bore_bottom))
        shape=shape.fuse(box(x+1.8,y-1.3,19,2.7,2.6,1),box(x+2.7,y-1,19.9,1.6,2,.7))
        assert shape.isValid() and len(shape.Solids())==1,f'disconnected fan guide {i}'
        result.append(shape)
    return result


def screw(x,y):
    cfg=config();c=cfg['screw'];length=c['nominal_shank_length_mm']+c['length_tolerance_mm'];seat=cfg['carrier_top_H']
    return cylinder(x,y,seat-length,1,length).fuse(cylinder(x,y,seat,c['head_max_diameter_mm']/2,c['head_height_allocation_mm']))


def parts():
    rows=[]
    for i,(shape,(x,y)) in enumerate(zip(guides(),config()['mounts_xy_mm']),1):
        rows.append({'name':f'keyboard-fan-guide-{i}','shape':shape,'group':'supports',
                     'moving':False,'fan_harness':True,'color':(.26,.53,.59)})
        rows.append({'name':f'keyboard-fan-guide-screw-{i}','shape':screw(x,y),'group':'supports',
                     'moving':False,'fan_harness':True,'color':(.44,.45,.46)})
    return rows


def driver(x,y):
    cfg=config();c=cfg['service'];top=cfg['carrier_top_H']+cfg['screw']['head_height_allocation_mm']
    return cylinder(x,y,top,c['driver_shaft_diameter_mm']/2,20).fuse(
        cylinder(x,y,top+20,c['driver_handle_diameter_mm']/2,20))

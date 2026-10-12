"""Connector-family reference geometry placed at the saved module port."""
import functools
import hashlib
import json
from pathlib import Path

import cadquery as cq
from cad import box, cylinder, compound, bounds

HERE=Path(__file__).resolve().parent
REFERENCE=HERE/'reference/display-connector'
_STRIPPED={}


def config():
    return json.loads((HERE/'display-plug.json').read_text())


@functools.lru_cache(maxsize=1)
def references():
    data=json.loads((REFERENCE/'sources.json').read_text());result={}
    for row in data['files']:
        path=REFERENCE/row['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],path
        shape=cq.Shape.importBrep(str(path));assert shape.isValid() and len(shape.Solids())==1,path
        result[path.stem]=shape
    return result


def place(shape):
    c=config()
    return shape.rotate((0,0,0),(1,0,0),c['reference_rotations_deg']['X_first']).rotate(
        (0,0,0),(0,0,1),c['reference_rotations_deg']['Z_second']).translate(tuple(c['reference_origin_construction_xyz_mm']))


def reference_envelope():
    # Drawing-checked outer bounds, not the rejected supplier receptacle solid.
    return place(cq.Solid.makeBox(26.25,1.0,3.95,cq.Vector(-13.125,-.02,-1.45)))


def bar(angle=0, withdrawal=0):
    p=config()['bar_pivot_reference_xyz_mm']
    shape=references()['pull-bar'].rotate(tuple(p),(p[0]+1,p[1],p[2]),-angle)
    return place(shape).translate((withdrawal,0,0))


def body(withdrawal=0):
    return place(references()['plug-body']).translate((withdrawal,0,0))


def geometry():
    return [{'name':'display-module-plug-body','shape':body(),'moving':False,'display_plug':True,'color':(.71,.52,.23)},
            {'name':'display-module-lock-bar','shape':bar(),'moving':False,'display_plug':True,'color':(.42,.43,.45)}]


def strip_native_port(part):
    """Exclude only the documented port solid for the mating-system check."""
    if part['name']!='center-pcb-and-available-models':
        return part
    key=id(part['shape'])
    if key in _STRIPPED:
        assert _STRIPPED[key][0] is part['shape']
        return {**part,'shape':_STRIPPED[key][1]}
    c=config();remaining=[];found=[]
    for s in part['shape'].Solids():
        actual=bounds(s)
        if all(abs(a-b)<.001 for a,b in zip(actual,c['native_receptacle_bounds_construction_xyz_mm'])):
            found.append(s)
        else:
            remaining.append(s)
    assert len(found)==1,'the saved module receptacle must be identified exactly once'
    assert abs(found[0].Volume()-c['native_receptacle_volume_mm3'])<.001
    result=compound(remaining);_STRIPPED[key]=(part['shape'],result,found[0])
    return {**part,'shape':result}


def obstacle_for(candidate, obstacle):
    return strip_native_port(obstacle) if candidate.get('display_plug') else obstacle


def upper_swing_space():
    return box(*config()['upper_swing_space_xyHwhd_mm'])


def access_spaces():
    c=config();result=[]
    for name,(x,y,h) in c['access_points_xyH_mm'].items():
        shaft=cylinder(x,y,h,c['tool_shaft_diameter_mm']/2,c['tool_shaft_height_mm'])
        handle=cylinder(x,y,h+c['tool_shaft_height_mm'],c['tool_handle_diameter_mm']/2,c['tool_handle_height_mm'])
        result.append({'name':'display-plug-access-'+name,'shape':shaft.fuse(handle),'color':(.84,.48,.16,.25),'moving':False})
    return result

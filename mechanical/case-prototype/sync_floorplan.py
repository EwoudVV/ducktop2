#!/usr/bin/env python3
"""Update case-derived planner geometry, preserving unrelated free parts."""
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from cad import ROOT
from build import CONFIG,INVENTORY,installed
import hinges


def projection(shapes):
    triangles=[]
    for shape in shapes:
        points,faces=shape.tessellate(.03,.12)
        for f in faces:
            poly=Polygon([(points[i].x,-points[i].y) for i in f])
            if poly.area>1e-9:triangles.append(poly)
    return unary_union(triangles).buffer(.0001).buffer(-.0001).simplify(.01,preserve_topology=True)


def geometry(part,shape):
    polys=list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape]
    primary=max(polys,key=lambda p:p.area)
    x,y,x1,y1=shape.bounds
    local=lambda coords:[[round(a-x,5),round(b-y,5)] for a,b in list(coords)[:-1]]
    part.update(x=round(x,5),y=round(y,5),w=round(x1-x,5),h=round(y1-y,5),rot=0,locked=True,
                outline=local(primary.exterior.coords),outlineHoles=[local(r.coords) for r in primary.interiors])
    if len(polys)>1:part['additionalOutlines']=[local(p.exterior.coords) for p in polys if p!=primary]


def main():
    path=ROOT/'mechanical/floorplan.json';plan=json.loads(path.read_text());parts={p['id']:p for p in plan['parts']}
    h=CONFIG['hinges'];l=CONFIG['lid'];b=CONFIG['base']
    for side,x in zip(['left','right'],h['pivot_x']):
        values=hinges.parts(side,x,h['pivot_y'],h['pivot_height'],0)
        p=parts['hinge-'+side]
        geometry(p,projection(v['shape'] for v in values[3:]));p['name']='Framework 13 '+side+' base bracket, revision 00'
        p['caseSource']='case-prototype/hinges.py; original manufacturer STEP, 0.03 mm tessellation'
        q=parts['hinge-lid-'+side]
        geometry(q,projection(v['shape'].translate((0,h['pivot_y'],0)) for v in values[:3]))
        q['name']='Framework 13 '+side+' lid bracket, revision 00';q['caseSource']=p['caseSource']
    for name,identifier in [('keyboard','keyboard'),('radio','radio-daughterboard')]:
        p=parts[identifier]
        shape=unary_union([Polygon([installed(name,q) for q in row['outer']]) for row in INVENTORY[name]['outlines']])
        geometry(p,shape);p.update(zone='base',caseSource='case-prototype/assembly.json; proposed assembly transform',
                                  pcbSha256=INVENTORY[name]['sha256'],height=-CONFIG['boards'][name]['bottom_height'])
    for key in ['cold-plate','heatpipe','fin-stack','blower']:
        name={'cold-plate':'cold_plate','fin-stack':'fins'}.get(key,key)
        x,y,z,w,d,t=CONFIG['cooling'][name]
        parts[key].update(x=x,y=y,w=w,h=d,rot=0,name=key+' compact reservation, fit and thermal test pending')
    for i,(x,y) in enumerate(CONFIG['speakers']['xy']):
        parts['speaker-'+['left','right'][i]].update(x=x,y=y,w=18,h=38,rot=0,name='speaker '+['L','R'][i]+' depth and mounting pending')
    parts['panel-outline'].update(x=l['panel_x'],y=l['panel_s'],w=l['panel_width'],h=l['panel_depth'],name='B160QAN03.K recorded outline; thickness and connector pending')
    parts['panel-active'].update(x=l['panel_x']+3.5,y=l['panel_s']+6,name='active area approximation; verify owned panel')
    plan['planes']['base'].update(w=370,h=282,physicalBounds={'x':-6,'y':-26},label='Base / proposed outside envelope')
    plan['planes']['lid'].update(w=370,h=274,y=310,physicalBounds={'x':-6,'y':-8},label='Lid / s=0 at hinge axis, positive toward panel top')
    plan.update(version=6,parts=list(parts.values()),caseGeometrySource='case-prototype/assembly.json + original Framework hinge STEP; compact profile is not assembly-qualified')
    plan['view'].update(x=-25,y=-45,w=415,h=330)
    path.write_text(json.dumps(plan,indent=1)+'\n')
    planner=ROOT/'mechanical/layout-planner.html';html=planner.read_text()
    start=html.index('const defaultState = ')+len('const defaultState = ')
    _,length=json.JSONDecoder().raw_decode(html[start:])
    html=html[:start]+json.dumps(plan,indent=1)+html[start+length:]
    planner.write_text(html)
    print('planner: actual hinge silhouettes, six board poses, proposed case envelope; free unrelated parts preserved')


if __name__=='__main__':main()

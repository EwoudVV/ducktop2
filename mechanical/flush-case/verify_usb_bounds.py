#!/usr/bin/env python3
"""Compare the fast channel bounds with samples of the actual CAD surfaces."""
import hashlib
import json
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
from scipy.spatial import cKDTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'mechanical/case-prototype'))
import model_cache
import build as baseline
from cables import guide
from component_heights import guided_points
from usb_collision import Checks
import usb_harness


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def coverage(vertices,bounds):
    low,high=bounds;tree=cKDTree((low+high)/2)
    _,indices=tree.query(vertices,k=min(32,len(low)))
    if indices.ndim==1:indices=indices[:,None]
    margins=np.minimum(vertices[:,None,:]-low[indices],high[indices]-vertices[:,None,:]).min(axis=2)
    return margins.max(axis=1)


def main():
    files=[Path(__file__),HERE/'usb_collision.py',HERE/'usb_harness.py',HERE/'assembly.json',HERE/'usb-harness.json',
           ROOT/'mechanical/case-prototype/cables.py',ROOT/'mechanical/case-prototype/component_heights.py']
    before={str(p.relative_to(ROOT)):sha(p) for p in files}
    case=json.loads((HERE/'assembly.json').read_text());parts,data,_=usb_harness.load_parts()
    checker=Checks(parts,case,data,[]);rows=[]
    def test(name,shape,envelopes,regions=None):
        vertices,_=shape.tessellate(.05,.1)
        points=np.array([v.toTuple() for v in vertices]);assert len(points),name
        margin=np.maximum.reduce([coverage(points,e) for e in envelopes])
        if regions:
            for low,high in regions:
                margin=np.maximum(margin,np.minimum(points-low,high-points).min(axis=1))
        row={'part':name,'sampled_vertices':len(points),'minimum_box_margin_mm':round(float(margin.min()),6),
             'vertices_outside_bounds':int((margin < -1e-5).sum()),'pass':bool((margin >= -.00001).all())}
        rows.append(row);print(name,row['vertices_outside_bounds'],'outside',flush=True)
    for r in data['routes']:
        s=guide(guided_points(r,baseline.CONFIG['cables']),r['wire_od_mm'],.15,.4)
        test(r['name']+'-full-guide',s,[checker.envelope(r['name'],True)])
    old=checker.old;by_name={p['name']:p for p in old['parts']}
    for name,files in old.get('collision_primitives',{}).items():
        if name.startswith('harness-USB-'):continue
        part=by_name[name];names=part.get('integrated_from',[])
        selected=[r for r in data['other_routes'] if r['name']+'-guide' in names]
        count=sum('-guide' in n for n in names)
        assert len(selected)==count,name
        for file,route in zip(files[:count],selected):
            s=cq.Shape.importBrep(str(model_cache.CACHE/file)).translate((0,0,checker.dz))
            test(name+'/'+route['name'],s,[checker.envelope(route['name'],True)])
    for side,seam,bracket in [('left',70.75,130),('right',299.25,225)]:
        p=next(p for p in parts if p['name']=='harness-USB-'+side+'-carrier')
        b=p['shape'].BoundingBox()
        if side=='left':assert b.xmax<179.00001
        else:assert b.xmin>178.99999
        # These are the same physical crop regions checked against components.
        regions=[(np.array([seam-4.5,-260,0]),np.array([seam+4.5,0,26])),
                 (np.array([bracket-5.1,-125.9,0]),np.array([bracket+5.1,-100.9,26]))]
        test(p['name'],p['shape'],[checker.envelope(r['name'],True) for r in data['routes']],regions)
    assert before=={p:sha(ROOT/p) for p in before},'sources changed during bound verification'
    result={'date':'2026-10-09','source_hashes':before,'mesh_deflection_mm':.05,'angular_tolerance':.1,
            'checks':rows,'all_sampled_vertices_covered':all(r['pass'] for r in rows),
            'scope':'sampled CAD surface validation of channel bounds and non-channel crop coverage; not a continuous-surface or manufacturing-tolerance proof'}
    (HERE/'usb-bound-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['all_sampled_vertices_covered']


if __name__=='__main__':main()

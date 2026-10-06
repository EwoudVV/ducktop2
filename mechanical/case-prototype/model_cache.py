"""Private BRep cache for re-running checks and views without rebuilding CAD."""
import json
import hashlib
import cadquery as cq
from cad import ROOT,HERE
CACHE=ROOT/'.workbench/case-prototype/assembly-brep'


def save(m):
    from build import CONFIG,load_config
    assert CONFIG==load_config(CONFIG['selected_profile']),'configuration changed during the build; rebuild before caching'
    CACHE.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i,p in enumerate(m.parts):
        path=f'part-{i:04}.brep';p['shape'].exportBrep(str(CACHE/path))
        rows.append({**{k:v for k,v in p.items() if k!='shape'},'brep':path})
    boards={}
    for name,shape in m.board_material.items():
        path=name+'-substrate.brep';shape.exportBrep(str(CACHE/path));boards[name]=path
    payload={'configuration':CONFIG,'parts':rows,'board_material':boards,'mounts':m.mounts,'findings':m.findings,
             'cable_records':m.cable_records,'harness':m.harness,
             'config_sha256':hashlib.sha256((HERE/'assembly.json').read_bytes()).hexdigest(),
             'inventory_sha256':hashlib.sha256((HERE/'board-inventory.json').read_bytes()).hexdigest()}
    primitives={}
    for name,pieces in getattr(m,'collision_primitives',{}).items():
        primitives[name]=[]
        for i,shape in enumerate(pieces):
            path=f'{name}-check-{i}.brep';shape.exportBrep(str(CACHE/path));primitives[name].append(path)
    payload['collision_primitives']=primitives
    (CACHE/'model.json').write_text(json.dumps(payload)+'\n')
    print('assembly BRep checkpoint saved',flush=True)


def load():
    from build import Model,load_config
    d=json.loads((CACHE/'model.json').read_text())
    assert d.get('configuration')==load_config(),'CAD cache configuration must be rebuilt'
    for name,file in [('config','assembly.json'),('inventory','board-inventory.json')]:
        assert d[name+'_sha256']==hashlib.sha256((HERE/file).read_bytes()).hexdigest(), 'CAD cache is stale'
    m=Model()
    m.parts=[{**{k:v for k,v in p.items() if k!='brep'},'shape':cq.Shape.importBrep(str(CACHE/p['brep']))} for p in d['parts']]
    m.board_material={k:cq.Shape.importBrep(str(CACHE/v)) for k,v in d['board_material'].items()}
    for name in ['mounts','findings','cable_records','harness']:setattr(m,name,d[name])
    m.collision_primitives={name:[cq.Shape.importBrep(str(CACHE/p)) for p in paths] for name,paths in d.get('collision_primitives',{}).items()}
    return m

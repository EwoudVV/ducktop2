"""Private BRep cache for re-running checks and views without rebuilding CAD."""
import json
import hashlib
import cadquery as cq
from cad import ROOT,HERE
CACHE=ROOT/'.workbench/case-prototype/assembly-brep'


def geometry_inputs():
    paths=[HERE/name for name in ['build.py','cad.py','cables.py','service_carriers.py',
        'ground_braids.py','harness_geometry.py','hinges.py','radio_hardware.py','case_inputs.py',
        'component_heights.py','cooling.py','cooling-datums.json','cooling-parts.json']]
    paths += [HERE/'reference/pcb-snapshot/manifest.json']
    paths += list((HERE/'reference/pcb-snapshot/inputs').glob('*.json'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file()}


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
             'geometry_inputs_sha256':geometry_inputs(),
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
    assert all(d.get('geometry_inputs_sha256',{}).get(name)==digest for name,digest in geometry_inputs().items()),'CAD cache sources or mechanical inputs changed; rebuild'
    assert d.get('configuration')==load_config(),'CAD cache configuration must be rebuilt'
    for name,file in [('config','assembly.json'),('inventory','board-inventory.json')]:
        assert d[name+'_sha256']==hashlib.sha256((HERE/file).read_bytes()).hexdigest(), 'CAD cache is stale'
    m=Model()
    m.parts=[{**{k:v for k,v in p.items() if k!='brep'},'shape':cq.Shape.importBrep(str(CACHE/p['brep']))} for p in d['parts']]
    m.board_material={k:cq.Shape.importBrep(str(CACHE/v)) for k,v in d['board_material'].items()}
    for name in ['mounts','findings','cable_records','harness']:setattr(m,name,d[name])
    m.collision_primitives={name:[cq.Shape.importBrep(str(CACHE/p)) for p in paths] for name,paths in d.get('collision_primitives',{}).items()}
    return m


def bind_viewer_meshes(m=None):
    """Record the checked export for later image rendering, never CAD checks."""
    html=HERE/'inspection.html'
    sources=geometry_inputs()
    if m is None:
        model=json.loads((CACHE/'model.json').read_text())
        assert model['geometry_inputs_sha256']==sources,'staged geometry changed during export'
        config=model['configuration'];names={p['name'] for p in model['parts']}
        config_sha=model['config_sha256']
    else:
        from build import CONFIG,load_config
        assert CONFIG==load_config(),'configuration changed during export'
        config=CONFIG;names={p['name'] for p in m.parts}
        config_sha=hashlib.sha256((HERE/'assembly.json').read_bytes()).hexdigest()
    raw=html.read_bytes()
    data,_=json.JSONDecoder().raw_decode(raw.decode().split('const DATA=',1)[1])
    assert data['configuration']==config,'viewer configuration differs from exported CAD'
    assert {p['name'] for p in data['parts']}==names,'viewer parts differ from exported CAD'
    record={'html_sha256':hashlib.sha256(raw).hexdigest(),'geometry_inputs_sha256':sources,
            'config_sha256':config_sha}
    CACHE.mkdir(parents=True,exist_ok=True)
    (CACHE/'viewer-meshes.json').write_text(json.dumps(record)+'\n')


def preload_viewer_meshes(m):
    """Reuse display meshes only when their export and source hashes match."""
    from cad import _MESHES
    record=CACHE/'viewer-meshes.json'
    if not record.exists():return 0
    saved=json.loads(record.read_text());raw=(HERE/'inspection.html').read_bytes()
    if (saved['html_sha256']!=hashlib.sha256(raw).hexdigest()
        or saved['geometry_inputs_sha256']!=geometry_inputs()
        or saved['config_sha256']!=hashlib.sha256((HERE/'assembly.json').read_bytes()).hexdigest()):return 0
    data,_=json.JSONDecoder().raw_decode(raw.decode().split('const DATA=',1)[1])
    by_name={p['name']:p for p in data['parts']}
    if by_name.keys()!={p['name'] for p in m.parts}:return 0
    for part in m.parts:
        mesh=by_name[part['name']];shape=part['shape']
        _MESHES[id(shape)]=(shape,([cq.Vector(*v) for v in mesh['v']],[tuple(t) for t in mesh['f']]))
    print('reused',len(m.parts),'checked viewer meshes for image rendering',flush=True)
    return len(m.parts)

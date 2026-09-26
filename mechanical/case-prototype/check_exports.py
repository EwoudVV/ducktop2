#!/usr/bin/env python3
"""Reopen exported solids and check P1S mesh bounds, without editing source CAD."""
import json
from pathlib import Path
import cadquery as cq
import trimesh
from cad import HERE


def main():
    parts=json.loads((HERE/'parts.json').read_text())
    result={'scope':'export validity and size, not physical fit','manufactured_parts':{},'print_files':{}}
    for row in parts:
        if not row.get('manufactured'):continue
        path=HERE/'exports/parts'/(row['name']+'.step')
        shape=cq.importers.importStep(str(path)).val()
        valid=shape.isValid();solids=len(shape.Solids());delta=abs(shape.Volume()-row['volume_mm3'])
        assert valid and solids==1,(path.name,valid,solids)
        assert delta<.1,(path.name,delta)
        result['manufactured_parts'][row['name']]={'valid':valid,'solids':solids,'volume_delta_mm3':round(delta,6)}
    print('manufactured STEP round-trips passed',flush=True)
    for path in (HERE/'exports/parts').glob('*.stl'):
        mesh=trimesh.load(str(path),force='mesh')
        extents=mesh.extents.tolist()
        assert max(extents)<=244.01,(path.name,extents)
        assert mesh.is_watertight,(path.name,'open mesh')
        result['print_files'][path.name]={'watertight':True,'size_mm':[round(x,3) for x in extents]}
    print('P1S print bounds and watertight meshes passed',flush=True)
    assembly=cq.importers.importStep(str(HERE/'exports/ducktop2-assembly.step')).val()
    assert assembly.isValid(),'assembly STEP is invalid'
    expected=sum(p['solids'] for p in parts if p['group']!='keepout')
    actual=len(assembly.Solids())
    assert actual==expected,(actual,expected)
    result['assembly']={'valid':True,'solids':actual,'expected_solids':expected}
    (HERE/'export-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'manufactured_STEPs':len(result['manufactured_parts']),'STLs':len(result['print_files']),'assembly':result['assembly']},indent=2))


if __name__=='__main__':main()

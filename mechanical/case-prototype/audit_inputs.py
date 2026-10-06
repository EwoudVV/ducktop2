#!/usr/bin/env python3
"""Check current board bindings without saving a PCB or upstream mechanical input."""
import hashlib
import json
import subprocess
from cad import HERE,ROOT


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(row):
    result={k:row[k] for k in ['thickness','copper_layers','outlines','edges','holes','keepouts']}
    fps=[]
    for f in row['footprints']:
        q={k:v for k,v in f.items() if k not in ['footprint','value']}
        q['pads']=sorted(q['pads'],key=lambda p:(p['number'],p['position']))
        fps.append(q)
    result['footprints']=fps
    return result


def main():
    rows=json.loads((HERE/'board-inventory.json').read_text())['boards']
    approved=HERE/'input-audit.json'
    prior=json.loads(approved.read_text()) if approved.exists() else None
    oldpath=ROOT/'.workbench/case-refresh-20261005/inventory-before-metadata-refresh.json'
    old=json.loads(oldpath.read_text())['boards'] if oldpath.exists() else None
    result={'PCB_sources':{},'upstream_inputs':{},'manufacturing_ready':False,
            'coordinates':'X,Y,+height inputs -> X,-Y,+height CAD -> X,Y,-height STEP'}
    source=json.loads((ROOT/'mechanical/power-harness.json').read_text())['source_sha256']
    for name,r in rows.items():
        sha=digest(ROOT/r['file']);assert sha==r['sha256'],name+' changed: refresh inventory first'
        gh=hashlib.sha256(json.dumps(geometry(r),sort_keys=True).encode()).hexdigest()
        expected=source.get(r['file'],sha)
        if expected!=sha:
            proof=(old and old[name]['sha256']==expected and geometry(old[name])==geometry(r))
            proof=proof or (prior and prior['PCB_sources'][name]['geometry_sha256']==gh and prior['PCB_sources'][name]['upstream_harness_sha256']==expected)
            assert proof,name+' geometry differs from harness inputs; regenerate in electronics workflow'
        commit=subprocess.check_output(['git','log','-1','--format=%H','--',r['file']],cwd=ROOT,text=True).strip()
        result['PCB_sources'][name]={'file':r['file'],'sha256':sha,'last_file_commit':commit,
                                    'upstream_harness_sha256':expected,'geometry_sha256':gh,
                                    'uncommitted':bool(subprocess.check_output(['git','diff','--name-only','--',r['file']],cwd=ROOT,text=True).strip()),
                                    'harness_geometry_unchanged':True}
    for f in ['board-datums.json','component-placement.json','power-harness.json','bms-harness-routing.json',
              'power-harness-checks.json','bms-connector-access.json','bms-connector-clearances.json']:
        result['upstream_inputs'][f]=digest(ROOT/'mechanical'/f)
    result['notes']=['Upstream hash differences accepted only after exact saved outline, hole, footprint pose, model transform, pad position and courtyard comparison. Electrical value text is not a geometric datum. R2600 changed from 100k to 1M without a footprint or pose change. Electronics remain untouched.',
                     'board-placement.json BMS notch metadata is older than the current Edge.Cuts. The case uses the actual board geometry, not that stale rectangle.']
    approved.write_text(json.dumps(result,indent=2)+'\n')
    print('six saved boards bound; geometric equivalence verified for metadata-only changes')


if __name__=='__main__':main()

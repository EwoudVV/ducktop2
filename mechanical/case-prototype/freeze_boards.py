#!/usr/bin/env python3
"""Pin a reviewed inventory and native STEP exports for a reproducible case."""
import json,hashlib,shutil
from cad import HERE,ROOT


def main():
    data=json.loads((HERE/'board-inventory.json').read_text())
    cache=ROOT/'.workbench/case-prototype/pcb-step'
    target=HERE/'reference/pcb-snapshot';target.mkdir(parents=True,exist_ok=True)
    manifest={'status':'explicit frozen mechanical snapshot; not a claim that live PCB files stop changing','boards':{}}
    for name,row in data['boards'].items():
        assert (cache/(name+'.sha256')).read_text()==row['sha256'],name+' STEP does not match reviewed inventory'
        source=cache/(name+'.step');dest=target/source.name;shutil.copy2(source,dest)
        shutil.copy2(cache/(name+'.coverage.json'),target/(name+'.coverage.json'))
        manifest['boards'][name]={'pcb_file':row['file'],'pcb_sha256':row['sha256'],
                                'step_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    shutil.copy2(HERE/'board-inventory.json',target/'inventory.json')
    shutil.copy2(HERE/'input-audit.json',target/'input-audit.json')
    inputs=target/'inputs';inputs.mkdir(exist_ok=True)
    audit=json.loads((HERE/'input-audit.json').read_text())
    manifest['mechanical_inputs']={}
    for name,expected in audit['upstream_inputs'].items():
        source=ROOT/'mechanical'/name
        assert hashlib.sha256(source.read_bytes()).hexdigest()==expected,name+' changed since input review'
        shutil.copy2(source,inputs/name);manifest['mechanical_inputs'][name]=expected
    source=ROOT/'mechanical/board-placement.json';shutil.copy2(source,inputs/source.name)
    manifest['mechanical_inputs'][source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
    source=ROOT/'ducktop2.3dshapes/DRA818_Castellated.step';shutil.copy2(source,target/source.name)
    manifest['radio_module_model']={'file':'ducktop2.3dshapes/'+source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('six reviewed native PCB STEP snapshots pinned under reference/pcb-snapshot',flush=True)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Cache KiCad-native component exports without modifying the source boards."""
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CLI=Path('/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
CACHE=ROOT/'.workbench/case-prototype/pcb-step'


def export_one(item):
    name, row = item
    sha=hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()
    if sha!=row['sha256']:
        raise RuntimeError(f'{name} changed since inventory; refresh and review before rebuilding')
    target=CACHE/(name+'.step'); marker=CACHE/(name+'.sha256')
    if target.exists() and marker.exists() and marker.read_text()==sha:
        return name+' cached'
    cmd=[str(CLI),'pcb','export','step','--force','--subst-models',
         '--component-filter','A1,J*,FPC*,H*,L*,F*,SW*,MK*',
         '-o',str(target),str(ROOT/row['file'])]
    result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    (CACHE/(name+'.log')).write_text(result.stdout+'\n'+result.stderr)
    if not target.exists():
        raise RuntimeError(name+' STEP failed: '+result.stdout[-1500:]+result.stderr[-1500:])
    missing=[line.split('File not found: ',1)[1] for line in result.stdout.splitlines() if line.startswith('File not found: ')]
    report={'source_sha256':sha,'kicad_returncode':result.returncode,
            'missing_model_paths':missing,'vrml_models_omitted':result.stderr.count('Cannot use VRML'),
            'scope':'PCB material, fitted available connector/module/support/inductor/fuse/switch/microphone models; most small SMT components omitted',
            'complete_component_assembly':False}
    (CACHE/(name+'.coverage.json')).write_text(json.dumps(report,indent=2)+'\n')
    marker.write_text(sha)
    return name+f' exported; {len(missing)} missing STEP models recorded'


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    rows=json.loads((HERE/'board-inventory.json').read_text())['boards']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for msg in pool.map(export_one,rows.items()): print(msg,flush=True)


if __name__=='__main__': main()

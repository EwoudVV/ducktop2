"""Prefer the explicitly pinned mechanical inputs over the live PCB workspace."""
from cad import HERE,ROOT
import json,hashlib


def path(name):
    frozen=HERE/'reference/pcb-snapshot/inputs'/name
    manifest=HERE/'reference/pcb-snapshot/manifest.json'
    if manifest.exists():
        record=json.loads(manifest.read_text())['mechanical_inputs']
        if not frozen.exists():raise FileNotFoundError('frozen case input missing: '+name)
        assert hashlib.sha256(frozen.read_bytes()).hexdigest()==record[name],name+' differs from frozen input manifest'
        return frozen
    return ROOT/'mechanical'/name

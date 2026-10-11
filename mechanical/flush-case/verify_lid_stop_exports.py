"""Reopen the stop inspection STEP and tie the pictures to checked sources."""
import hashlib
import json
from pathlib import Path

import cadquery as cq
import check_cooler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parts, case, sources = check_cooler.load_case()
    checks = json.loads((HERE/'checks.json').read_text())
    stop = json.loads((HERE/'lid-stop-checks.json').read_text())
    assert checks['source_hashes'] == stop['source_hashes'] == sources
    assert checks['nominal_opening_geometry_pass'] and stop['stop_geometry_pass']
    assert checks['hinge_sweep']['sample_angles_deg'][-1] == 135
    raw = (HERE/'inspection.html').read_text()
    data, _ = json.JSONDecoder().raw_decode(raw.split('const DATA=', 1)[1])
    assert data['source_hashes'] == sources
    assert 'max="135"' in raw and 'setAngle(180)' not in raw
    assert 'Math.min(135,v)' in raw
    new = [p for p in parts if p.get('lid_stop')]
    assert len(new) == 24
    records = []
    for path in [HERE/'exports/lid-stops.step']:
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid() and shape.Solids(), path
        records.append({'file': str(path.relative_to(HERE)), 'sha256': sha(path),
                        'solids': len(shape.Solids()), 'reopens': True})
    for row in json.loads((HERE/'exports.json').read_text()):
        assert row['reopens'] and sha(HERE/row['file']) == row['sha256'], row['file']
        records.append({**row, 'verification': 'build.py reopened this exact saved file after export'})
    images = [f'views/lid-stop-{angle}.png' for angle in [0, 105, 135]]+['views/lid-stop-access.png']
    for path, digest in sources.items():
        assert sha(ROOT/path) == digest, path
    record = {'date': case['date'], 'source_hashes': {**sources, str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
                                                      'mechanical/flush-case/draw_cooler.py': sha(HERE/'draw_cooler.py')},
              'exports': records, 'images': {p: sha(HERE/p) for p in images},
              'stop_parts_in_full_case': len(new), 'viewer_maximum_opening_deg': 135,
              'scope': 'Inspection CAD only. Stop loads, screw seating and physical fit are unqualified.'}
    (HERE/'lid-stop-exports.json').write_text(json.dumps(record, indent=2)+'\n')
    print('reopened full case and stop exports; viewer stops at 135 degrees', flush=True)


if __name__ == '__main__':
    main()

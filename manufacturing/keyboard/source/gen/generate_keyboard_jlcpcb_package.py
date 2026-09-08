#!/usr/bin/env python3
"""Export and check the saved keyboard board in an isolated staging directory.

Requires KiCad 10 CLI/Python, Shapely 2.1.2 and gerbonara 1.6.3. No generator or
canonical design file is changed. Existing output is preserved unless
--replace is explicit; replacement keeps the previous package as a sibling.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import contextmanager
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

PROJECT_DIR = Path(__file__).resolve().parents[1]
BOARD = PROJECT_DIR / 'keyboard/12_keyboard_daughterboard.kicad_pcb'
OUTPUT = PROJECT_DIR / 'manufacturing/keyboard'
REFERENCE = OUTPUT / 'reference'
RAW = OUTPUT / 'gerbers'
KICAD_CLI = None
GERBER_LAYERS = 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts'
EXCLUSION_BOUNDS = (-5.05, 2.20, -1.25, 4.20)
EXCLUSION_SOURCE = 'CHERRY VS-10107 revision 03, PCB-MX-ULP; footprint origin at switch center, PCB Y downward'
SOURCE_FILES = (
    'keyboard/12_keyboard_daughterboard.kicad_pcb',
    'keyboard/12_keyboard_daughterboard.kicad_sch',
    'keyboard/12_keyboard_daughterboard.kicad_pro',
    'gen/generate_keyboard_daughterboard_sheet.py',
    'gen/generate_keyboard_daughterboard_pcb.py',
    'gen/apply_bom_keyboard_daughterboard.py',
    'gen/Cherry_MX_ULP.kicad_sym',
    'gen/Conn_01x30_FFC_MP.kicad_sym',
    'gen/genlib.py',
    'ducktop2.pretty/Cherry_MX_ULP_SMD.kicad_mod',
    'ducktop2.pretty/D_SOD-323_JSCJ_1N4148WS.kicad_mod',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def run(*args: str) -> None:
    from check_release_candidate import find_kicad_cli
    proc = subprocess.run([str(KICAD_CLI or find_kicad_cli()), *map(str, args)],
                          cwd=PROJECT_DIR, capture_output=True, text=True)
    if REFERENCE.is_dir():
        with (REFERENCE / 'export.log').open('a') as log:
            log.write(' '.join(map(str, args)) + '\n' + proc.stdout + proc.stderr + '\n')
    require(proc.returncode == 0, f'KiCad failed: {args}: {proc.stdout}{proc.stderr}')


def natural_ref_key(ref: str) -> tuple[str, int]:
    return ''.join(c for c in ref if not c.isdigit()), int(''.join(c for c in ref if c.isdigit()) or 0)


def comma_refs(prefix: str, first: int, last: int) -> str:
    return ','.join(f'{prefix}{n}' for n in range(first, last + 1))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_components(netlist):
    from report_schematic_pcb_eco import parse_schematic
    rows = parse_schematic(ET.parse(netlist).getroot())
    require(len({r['ref'] for r in rows}) == len(rows), 'duplicate schematic reference')
    components = {r['ref']: r for r in rows}
    expected = {f'D{n}' for n in range(320,385)} | {f'SW{n}' for n in range(320,385)} | {'J320'}
    require(set(components) == expected, 'keyboard population changed; review the assembly contract')
    for ref, comp in components.items():
        require(not comp['attributes'], f'{ref} has DNP/excluded assembly state')
        fields = comp['fields']
        expected_mpn = 'MX6C-T3NB' if ref.startswith('SW') else '1N4148WS' if ref.startswith('D') else 'FH12-30S-0.5SH(55)'
        require(fields.get('MPN') == expected_mpn and bool(fields.get('Manufacturer')), f'{ref} part identity differs or is incomplete')
        if not ref.startswith('SW'):
            require(fields.get('LCSC') == ('C2128' if ref.startswith('D') else 'C506793'), f'{ref} factory part changed')
    return components


def write_bom(path: Path) -> set[str]:
    """Write factory placements from the freshly exported schematic netlist."""
    components = load_components(REFERENCE / 'netlist.xml')
    groups = defaultdict(list)
    for ref, comp in components.items():
        if not ref.startswith('SW'):
            fields = comp['fields']
            groups[(fields['Manufacturer'], fields['MPN'], comp['footprint'], fields['LCSC'])].append(ref)
    rows = [{'Comment': f'{maker} {mpn}', 'Designator': ','.join(sorted(refs, key=natural_ref_key)),
             'Footprint': footprint, 'JLCPCB Part #': lcsc}
            for (maker,mpn,footprint,lcsc),refs in sorted(groups.items())]
    write_csv(path, ['Comment','Designator','Footprint','JLCPCB Part #'], rows)
    return {ref for refs in groups.values() for ref in refs}


def write_cpl(raw_positions: Path, path: Path, included_refs: set[str]) -> set[str]:
    with raw_positions.open(newline='', encoding='utf-8-sig') as handle:
        rows = [r for r in csv.DictReader(handle) if r['Ref'] in included_refs]
    require(Counter(r['Ref'] for r in rows) == Counter(included_refs), 'CPL is missing or duplicates a populated reference')
    result = []
    for row in sorted(rows, key=lambda r: natural_ref_key(r['Ref'])):
        require(row['Side'].lower() in ('top','bottom'), 'unknown placement side')
        require(all(math.isfinite(float(row[k])) for k in ('PosX','PosY','Rot')), 'invalid placement coordinate')
        result.append({'Designator':row['Ref'],'Mid X':f"{float(row['PosX']):.6f}mm",
                       'Mid Y':f"{float(row['PosY']):.6f}mm",'Rotation':f"{float(row['Rot'])%360:.4f}",
                       'Layer':'Top' if row['Side'].lower()=='top' else 'Bottom'})
    write_csv(path, ['Designator','Mid X','Mid Y','Rotation','Layer'], result)
    return {r['Ref'] for r in rows}


def copy_gerbers_to_upload_zip(zip_path: Path) -> list[str]:
    files = sorted(p for p in RAW.iterdir() if p.suffix.lower() in {'.gtl','.gbl','.gts','.gbs','.gto','.gbo','.gm1','.gbrjob','.drl'})
    suffixes = Counter(p.suffix.lower() for p in files)
    require(all(suffixes[s] == 1 for s in ('.gtl','.gbl','.gts','.gbs','.gto','.gbo','.gm1','.gbrjob')) and suffixes['.drl']==2,
            'fabrication export is incomplete or ambiguous')
    require(any('NPTH' in p.name for p in files) and any('-PTH' in p.name for p in files), 'separate plated and unplated drill files required')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in files:
            info = zipfile.ZipInfo(source.name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())
    return [p.name for p in files]


def write_readme(path: Path, gerber_files: list[str]) -> None:
    path.write_text('''# keyboard fabrication and assembly files

this package comes from the saved keyboard board and a fresh schematic
netlist. the manifest binds the source, staged board, checks and output files.
run `python3 gen/generate_keyboard_jlcpcb_package.py --verify-package manufacturing/keyboard`
before using a retained package. a source edit makes the old package stale.

to regenerate, install `shapely==2.1.2` and `gerbonara==1.6.3` in a Python
virtual environment, then run `python gen/generate_keyboard_jlcpcb_package.py
--output manufacturing/keyboard --replace` from the project root. KiCad 10
CLI and an interpreter with `pcbnew` are also required; use `--kicad-cli`
and `--kicad-python` if automatic discovery cannot find them. replacement
keeps the previous output as a sibling backup after the new checks pass.

- 273.5 x 80.0 mm, two copper layers, 0.8 mm FR-4.
- 65 CHERRY MX6C-T3NB switches, 65 JSCJ 1N4148WS diodes and one Hirose FH12-30S-0.5SH(55).
- `keyboard_GERBERS.zip` is the bare-board fabrication archive.
- `factory_BOM.csv` and `factory_CPL.csv` contain 66 placements. `complete_BOM.csv` contains all 131 parts. `switches_CPL.csv` contains the 65 later switch placements.
- `paste/factory/` excludes every switch land. `paste/switches/` contains 455 switch apertures, including all 325 fixation lands. the aperture and locating-hole CSVs use PCB coordinates with positive Y down. CPL Y follows the negative-Y KiCad export convention and shares the Gerber origin.

CHERRY VS-10107 revision 03, PCB-MX-ULP defines the contact exclusion used by
the public checker: local X -5.05 to -1.25 mm, local Y 2.20 to 4.20 mm. the
footprint's rule area prohibits tracks, vias, pads and filled copper on both
copper layers. the checker inspects native copper and the plotted Gerbers.

CHERRY VR00101_D specifies a lead-free process. its example uses a nitrogen
oven, gold-finished FR-4 and a 240 C maximum measured PCB-top temperature.
the classification table lists 217 C liquidus, at most 70 seconds above
liquidus, a 245 C recommended package peak and a 260 C absolute package peak.
follow the complete supplier process document and measure the actual profile.
stencil thickness, aperture reduction, finish and assembly fixtures still
need supplier review and a switch coupon. this package does not qualify a
hot plate process or a particular factory service.

review diode cathodes at pad 1, the connector opening and bottom contact,
the empty switch population in factory assembly, and the supplied separate
paste layers before ordering. no order or physical assembly test is recorded.

fabrication archive files:\n\n''' + '\n'.join('- '+name for name in gerber_files) + '\n')


def write_checksums(path: Path) -> None:
    files = sorted(p for p in OUTPUT.rglob('*') if p.is_file() and p != path)
    path.write_text(''.join(f'{digest(p)}  {p.relative_to(OUTPUT).as_posix()}\n' for p in files))


def source_snapshot():
    paths = set(SOURCE_FILES)
    for folder in ('keyboard',''):
        for name in ('fp-lib-table','sym-lib-table'):
            if (PROJECT_DIR/folder/name).is_file(): paths.add(str(Path(folder)/name))
    for suffix in ('.kicad_dru',):
        if BOARD.with_suffix(suffix).exists(): paths.add(str(BOARD.with_suffix(suffix).relative_to(PROJECT_DIR)))
    # Bind the implementation that produced and checked this package too.
    paths.update(('gen/generate_keyboard_jlcpcb_package.py','gen/report_schematic_pcb_eco.py','gen/check_release_candidate.py','gen/board_release_contract.py'))
    return {name:digest(PROJECT_DIR/name) for name in sorted(paths)}


def verify_package(package: Path, *, current_sources=True):
    manifest = json.loads((package/'manifest.json').read_text())
    require(manifest.get('schema')==1 and manifest.get('status')=='CHECKED_FABRICATION_FILES', 'package has no current checked manifest')
    require(manifest.get('board')==str(BOARD.relative_to(PROJECT_DIR)), 'package targets a different board')
    if current_sources:
        require(manifest['source_sha256']==source_snapshot(), 'package is stale for the current source or checker')
    entries = {}
    for line in (package/'SHA256SUMS.txt').read_text().splitlines():
        sha, name = line.split('  ',1)
        path = package/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and path.resolve().is_relative_to(package.resolve()), 'unsafe checksum path')
        require(name not in entries, 'duplicate checksum entry')
        require(path.is_file() and digest(path)==sha, f'package checksum mismatch: {name}')
        entries[name]=sha
    actual = {str(p.relative_to(package)) for p in package.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    require(set(entries)==actual, 'package manifest omits or adds a file')
    checks = manifest['checks']
    require(checks['saved_drc_findings']==0 and checks['refilled_drc_findings']==0 and checks['native_airwires']==0 and checks['parity_passed'] is True,
            'package does not have clean saved and refilled checks')
    require(checks['copper_exclusion_hits']==0 and checks['export_mismatches']==0 and checks['copper_layers']==2,
            'package lacks copper or export validation')
    return manifest


def guard_output(output: Path, replace: bool):
    output = output.expanduser().absolute()
    require(not output.is_symlink(), 'output must not be a symlink')
    for source in source_snapshot():
        require(not (PROJECT_DIR/source).resolve().is_relative_to(output.resolve()), 'output would contain a canonical source')
    require(output.resolve()!=PROJECT_DIR.resolve() and output.name not in ('', '.', '.git'), 'unsafe output directory')
    require(not output.exists() or (replace and output.is_dir()), 'output already exists; use --replace to preserve it as a sibling backup')
    return output


def promote(candidate: Path, output: Path, replace: bool):
    require(not output.exists() or replace, 'output appeared during export; refusing replacement')
    backup = None
    if output.exists():
        backup = output.with_name(output.name+'.previous-'+uuid.uuid4().hex[:12])
        output.rename(backup)
    try:
        candidate.rename(output)
    except BaseException:
        if backup is not None: backup.rename(output)
        raise
    return backup


def native_worker(board_path: Path, out: Path, library_root: Path):
    """This branch runs only under KiCad's Python. It saves paste copies only."""
    import wx
    app = wx.App(False)
    import pcbnew as p
    board = p.LoadBoard(str(board_path))
    board.BuildConnectivity()
    xy = lambda v: [v.x/1e6,v.y/1e6]
    def polys(poly):
        def ring(line): return [xy(line.CPoint(j)) for j in range(line.PointCount())]
        return [{'outer':ring(poly.COutline(i)), 'holes':[ring(poly.CHole(i,j)) for j in range(poly.HoleCount(i))]}
                for i in range(poly.OutlineCount())]
    def shape(item, layer):
        poly=p.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(poly,layer,0,1000,p.ERROR_OUTSIDE)
        return polys(poly)
    layers = list(board.GetEnabledLayers().CuStack())
    footprints=[];copper=[];rules=[];vias=[];library_diffs=[]
    for f in board.GetFootprints():
        ref=f.GetReference();pads=[]
        for q in f.Pads():
            row={'number':q.GetNumber(),'position':xy(q.GetPosition()),'size':xy(q.GetSize()),'drill':xy(q.GetDrillSize()),
                 'attribute':q.GetAttribute(),'net':q.GetNetname(),'layers':[board.GetLayerName(x) for x in q.GetLayerSet().Seq()],
                 'polygons':{board.GetLayerName(layer):shape(q,layer) for layer in layers if q.IsOnLayer(layer)}}
            pads.append(row)
            if q.GetAttribute()!=p.PAD_ATTRIB_NPTH:
                for layer,poly in row['polygons'].items(): copper.append({'id':q.m_Uuid.AsString(),'kind':'pad','layer':layer,'polygons':poly})
        footprints.append({'ref':ref,'position':xy(f.GetPosition()),'rotation':f.GetOrientationDegrees(),
                           'layer':board.GetLayerName(f.GetLayer()),'pads':pads})
        if ref.startswith('SW'):
            for z in f.Zones():
                rules.append({'ref':ref,'rule_area':z.GetIsRuleArea(),'layers':[board.GetLayerName(x) for x in z.GetLayerSet().Seq()],
                              'polygons':polys(z.Outline()),'forbidden':[z.GetDoNotAllowTracks(),z.GetDoNotAllowVias(),z.GetDoNotAllowPads(),z.GetDoNotAllowZoneFills()]})
        for item in f.GraphicalItems():
            for layer in layers:
                if item.IsOnLayer(layer):copper.append({'id':item.m_Uuid.AsString(),'kind':'footprint graphic','layer':board.GetLayerName(layer),'polygons':shape(item,layer)})
        lib=str(f.GetFPID().GetLibNickname());name=str(f.GetFPID().GetLibItemName())
        folder=PROJECT_DIR/(lib+'.pretty') if (PROJECT_DIR/(lib+'.pretty')).is_dir() else library_root/(lib+'.pretty')
        lf=p.FootprintLoad(str(folder),name)
        require(lf is not None, f'missing footprint library: {lib}:{name}')
        def signature(fp):
            copy=p.FOOTPRINT(fp);copy.SetOrientationDegrees(0);copy.SetPosition(p.VECTOR2I(0,0))
            return Counter((q.GetNumber(),q.GetAttribute(),q.GetShape(),tuple(xy(q.GetPosition())),tuple(xy(q.GetSize())),
                            tuple(xy(q.GetDrillSize())),round(q.GetOrientationDegrees()%180,4) if q.GetShape()!=0 else 0)
                           for q in copy.Pads())
        if signature(f)!=signature(lf):library_diffs.append(ref)
    for item in list(board.GetTracks())+list(board.GetDrawings()):
        if isinstance(item,p.PCB_VIA): vias.append({'position':xy(item.GetPosition()),'drill':item.GetDrillValue()/1e6})
        for layer in layers:
            if item.IsOnLayer(layer):copper.append({'id':item.m_Uuid.AsString(),'kind':'via' if isinstance(item,p.PCB_VIA) else 'track or drawing',
                                                   'layer':board.GetLayerName(layer),'polygons':shape(item,layer)})
    for z in board.Zones():
        if z.GetIsRuleArea():continue
        for layer in layers:
            if z.IsOnLayer(layer):copper.append({'id':z.m_Uuid.AsString(),'kind':'zone','layer':board.GetLayerName(layer),'polygons':polys(z.GetFilledPolysList(layer))})
    outline=p.SHAPE_POLY_SET();require(board.GetBoardPolygonOutlines(outline,False),'invalid board outline')
    result={'footprints':footprints,'copper':copper,'rules':rules,'vias':vias,'outline':polys(outline),
            'native_airwires':board.GetConnectivity().GetUnconnectedCount(False),'copper_layers':board.GetCopperLayerCount(),
            'thickness_mm':board.GetDesignSettings().GetBoardThickness()/1e6,'library_pad_differences':library_diffs,
            'board_sha256':digest(board_path)}
    (out/'geometry.json').write_text(json.dumps(result,indent=2)+'\n')
    for mode in ('factory','switches'):
        b=p.LoadBoard(str(board_path))
        for f in b.GetFootprints():
            keep=f.GetReference().startswith('SW') if mode=='switches' else not f.GetReference().startswith('SW')
            if not keep:
                for q in f.Pads():
                    ls=q.GetLayerSet();ls.RemoveLayer(p.F_Paste);q.SetLayerSet(ls)
        p.SaveBoard(str(out/(mode+'-paste.kicad_pcb')),b)


def geometry_checks(g):
    import shapely
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    from shapely import affinity
    require(g['native_airwires']==0 and g['copper_layers']==2 and abs(g['thickness_mm']-.8)<1e-6, 'native connectivity/layer/thickness gate failed')
    require(not g['library_pad_differences'], 'saved pads differ from the footprint libraries')
    def poly(rows): return unary_union([shapely.make_valid(Polygon(r['outer'],r['holes'])) for r in rows])
    outline=poly(g['outline']);bounds=outline.bounds
    require(abs(bounds[2]-bounds[0]-273.5)<1e-6 and abs(bounds[3]-bounds[1]-80)<1e-6, 'keyboard envelope changed')
    switches=[f for f in g['footprints'] if f['ref'].startswith('SW')]
    require(len(switches)==65 and len(g['footprints'])==131, 'native population differs')
    objects=[poly(item['polygons']) for item in g['copper']]
    tree=shapely.STRtree(objects);hits=[];restrictions=[]
    for f in switches:
        k=affinity.translate(affinity.rotate(box(*EXCLUSION_BOUNDS),-f['rotation'],origin=(0,0)),*f['position'])
        restrictions.append(k)
        rules=[r for r in g['rules'] if r['ref']==f['ref']]
        require(len(rules)==1,'each switch needs one native copper rule area')
        r=rules[0]
        require(r['rule_area'] and set(r['layers'])=={'F.Cu','B.Cu'} and all(r['forbidden']) and poly(r['polygons']).symmetric_difference(k).area<1e-8,
                f"{f['ref']} exclusion rule differs from the CHERRY bounds")
        require(sum(q['number']=='MP' and q['net']=='GND' for q in f['pads'])==5, f"{f['ref']} fixation lands are not all grounded")
        for i in tree.query(k,predicate='intersects'):
            area=objects[i].intersection(k).area
            if area>1e-8:hits.append({'ref':f['ref'],'id':g['copper'][i]['id'],'area_mm2':area})
    require(not hits,f'native copper enters a CHERRY exclusion: {hits[:5]}')
    return unary_union(restrictions)


def verify_exports(package, g, restricted):
    import shapely
    from shapely.geometry import Point, Polygon, LineString, box
    from shapely import affinity
    from shapely.ops import unary_union
    from gerbonara import GerberFile, ExcellonFile, graphic_primitives as gp
    from gerbonara.utils import MM
    import importlib.metadata
    def shape(prim):
        if isinstance(prim,gp.Circle):s=Point(prim.x,prim.y).buffer(prim.r,quad_segs=96)
        elif isinstance(prim,gp.Rectangle):s=affinity.translate(affinity.rotate(box(-prim.w/2,-prim.h/2,prim.w/2,prim.h/2),prim.rotation,origin=(0,0),use_radians=True),prim.x,prim.y)
        elif isinstance(prim,gp.Line):s=LineString([(prim.x1,prim.y1),(prim.x2,prim.y2)]).buffer(prim.width/2,quad_segs=64)
        else:s=shapely.make_valid(Polygon(prim.to_arc_poly().approximate_arcs(max_error=.0002).outline))
        return affinity.scale(s,1,-1,origin=(0,0))
    result={'gerbonara':importlib.metadata.version('gerbonara'),'shapely':shapely.__version__,'copper':{},'paste':{},'drill':{},'placement':{}}
    for layer,suffix in [('F.Cu','gtl'),('B.Cu','gbl')]:
        file=GerberFile.open(next((package/'gerbers').glob('*.'+suffix)));inside=Polygon()
        for obj in file.objects:
            for prim in obj.to_primitives(unit=MM):
                (x0,y0),(x1,y1)=prim.bounding_box()
                if not box(x0,-y1,x1,-y0).intersects(restricted):continue
                piece=shape(prim).intersection(restricted)
                inside=inside.union(piece) if prim.polarity_dark else inside.difference(piece)
        require(inside.area<1e-7,f'{layer} plotted copper enters the switch exclusion')
        result['copper'][layer]={'objects':len(file.objects),'restricted_copper_mm2':inside.area}
    for mode in ('factory','switches'):
        file=GerberFile.open(next((package/'paste'/mode).glob('*.gtp')));actual=Counter();expected=Counter()
        for obj in file.objects:
            require(type(obj).__name__=='Flash','paste is not an unambiguous flashed aperture')
            require(obj.polarity_dark,'negative paste aperture is unsupported')
            actual[tuple(round(x,5) for x in unary_union([shape(p) for p in obj.to_primitives(unit=MM)]).bounds)]+=1
        for f in g['footprints']:
            if f['ref'].startswith('SW') != (mode=='switches'):continue
            for q in f['pads']:
                if 'F.Paste' in q['layers']:
                    expected[tuple(round(x,5) for x in unary_union([Polygon(p['outer'],p['holes']) for p in q['polygons']['F.Cu']]).bounds)]+=1
        require(actual==expected,f'{mode} paste differs from the selected native pads')
        result['paste'][mode]={'apertures':sum(actual.values()),'mismatches':0}
    for mode in ('PTH','NPTH'):
        file=ExcellonFile.open(next((package/'gerbers').glob('*-'+mode+'.drl')))
        require(all(type(x).__name__=='Flash' for x in file.objects),'slotted drills need a reviewed exporter update')
        actual=Counter((round(x.x,3),round(-x.y,3),round(x.aperture.diameter,6)) for x in file.objects)
        if mode=='PTH':expected=Counter((round(v['position'][0],3),round(v['position'][1],3),round(v['drill'],6)) for v in g['vias'])
        else:
            require(all(abs(q['drill'][0]-q['drill'][1])<1e-9 for f in g['footprints'] for q in f['pads'] if q['attribute']==3),'nonround NPTH needs a reviewed exporter update')
            expected=Counter((round(q['position'][0],3),round(q['position'][1],3),round(q['drill'][0],6)) for f in g['footprints'] for q in f['pads'] if q['attribute']==3)
        require(actual==expected,f'{mode} drill positions/diameters differ')
        result['drill'][mode]={'holes':sum(actual.values()),'mismatches':0,'coordinate_quantum_mm':.001}
    for mode in ('factory','switches'):
        with (package/(mode+'_CPL.csv')).open(encoding='utf-8-sig') as handle:rows=list(csv.DictReader(handle))
        expected={f['ref']:f for f in g['footprints'] if f['ref'].startswith('SW')==(mode=='switches')}
        require(Counter(r['Designator'] for r in rows)==Counter(expected.keys()),'CPL population differs')
        for r in rows:
            f=expected[r['Designator']]
            require(abs(float(r['Mid X'][:-2])-f['position'][0])<1e-6 and abs(float(r['Mid Y'][:-2])+f['position'][1])<1e-6
                    and float(r['Rotation'])%360==f['rotation']%360 and r['Layer']=='Top' and f['layer']=='F.Cu','CPL placement differs')
        result['placement'][mode]={'placements':len(rows),'mismatches':0}
    return result


@contextmanager
def retained_staging(output):
    with tempfile.TemporaryDirectory(prefix='.keyboard-export-',dir=output.parent) as temp:
        try:
            yield temp
        except BaseException:
            failed=output.with_name(output.name+'.failed-'+uuid.uuid4().hex[:12])
            Path(temp).rename(failed)
            print(f'failed staging retained: {failed}',file=sys.stderr)
            raise


def build_package(output: Path, replace=False, python=None, cli=None):
    global OUTPUT,REFERENCE,RAW,KICAD_CLI
    from check_release_candidate import find_kicad_cli,find_kicad_python,stage_pcb_project,native_board_stats
    from report_schematic_pcb_eco import compare
    # Check optional dependencies before starting expensive native work.
    import shapely,gerbonara
    import importlib.metadata
    require(shapely.__version__=='2.1.2' and importlib.metadata.version('gerbonara')=='1.6.3',
            'this exporter requires shapely==2.1.2 and gerbonara==1.6.3 in the running Python environment')
    output=guard_output(output,replace);output.parent.mkdir(parents=True,exist_ok=True)
    before=source_snapshot();KICAD_CLI=cli or find_kicad_cli();python=python or find_kicad_python()
    with retained_staging(output) as temp:
        stage=Path(temp);candidate=stage/'package';candidate.mkdir()
        OUTPUT=candidate;REFERENCE=candidate/'reference';RAW=candidate/'gerbers'
        for folder in (REFERENCE,RAW,candidate/'paste/factory',candidate/'paste/switches'):folder.mkdir(parents=True,exist_ok=True)
        staged=stage_pcb_project(BOARD,BOARD.with_suffix('.kicad_sch'),stage/'design')
        project=staged.with_suffix('.kicad_pro');settings=json.loads(project.read_text())
        severities=settings['board']['design_settings']['rule_severities']
        restored=sorted(k for k,v in severities.items() if v=='ignore')
        for key in restored:severities[key]='warning'
        settings['board']['design_settings']['drc_exclusions']=[]
        project.write_text(json.dumps(settings,indent=2)+'\n')
        run('sch','export','netlist','--format','kicadxml','--output',REFERENCE/'netlist.xml',staged.with_suffix('.kicad_sch'))
        parity=compare(staged.read_text(),ET.parse(REFERENCE/'netlist.xml').getroot(),standalone_root_prefix=True)
        (REFERENCE/'parity.json').write_text(json.dumps(parity,indent=2)+'\n')
        require(parity['passed'],'independent schematic/PCB parity failed')
        saved_stats=native_board_stats(staged,python);require(saved_stats['native_airwires']==0,'saved board still has native airwires')
        for mode in ('saved','refilled'):
            extra=[] if mode=='saved' else ['--refill-zones','--save-board']
            run('pcb','drc',*extra,'--severity-all','--severity-exclusions','--schematic-parity','--format','json','--output',REFERENCE/(mode+'-drc.json'),staged)
            report=json.loads((REFERENCE/(mode+'-drc.json')).read_text())
            require(not any(report.get(key) for key in ('violations','unconnected_items','schematic_parity')),f'{mode} DRC is not clean; inspect the retained failed staging report')
        library_candidates=[os.environ.get('KICAD10_FOOTPRINT_DIR'),str(Path(KICAD_CLI).parent/'../SharedSupport/footprints'),'/usr/share/kicad/footprints']
        libraries=next((Path(p).resolve() for p in library_candidates if p and Path(p).is_dir()),None)
        require(libraries is not None,'set KICAD10_FOOTPRINT_DIR to the installed footprint library')
        native=subprocess.run([python,str(Path(__file__).resolve()),'--native',str(staged),str(stage),str(libraries),*(['-ApplePersistenceIgnoreState','YES'] if sys.platform=='darwin' else [])],capture_output=True,text=True,timeout=120,cwd=PROJECT_DIR)
        (REFERENCE/'native-export.log').write_text(native.stdout+native.stderr)
        require(native.returncode==0,'native geometry export failed; inspect native-export.log')
        g=json.loads((stage/'geometry.json').read_text());restricted=geometry_checks(g)
        shutil.copyfile(stage/'geometry.json',REFERENCE/'geometry.json')
        run('pcb','export','gerbers','--output',RAW,'--layers',GERBER_LAYERS,'--precision','6',staged)
        run('pcb','export','drill','--output',RAW,'--format','excellon','--drill-origin','absolute','--excellon-units','mm','--excellon-zeros-format','decimal','--excellon-separate-th',staged)
        run('pcb','export','pos','--output',REFERENCE/'raw_positions.csv','--format','csv','--units','mm','--side','both','--smd-only',staged)
        run('pcb','export','ipcd356','--output',REFERENCE/'keyboard.ipc',staged)
        run('pcb','export','stats','--output',REFERENCE/'board_stats.txt','--format','report','--units','mm',staged)
        for mode,layers in [('top_assembly','F.Fab,F.Silkscreen,Edge.Cuts'),('bottom_references','B.Silkscreen,Edge.Cuts')]:
            run('pcb','export','svg','--output',REFERENCE/(mode+'.svg'),'--layers',layers,'--mode-single',staged)
        for mode in ('factory','switches'):
            run('pcb','export','gerbers','--output',candidate/'paste'/mode,'--layers','F.Paste','--precision','6',stage/(mode+'-paste.kicad_pcb'))
        components=load_components(REFERENCE/'netlist.xml');factory=write_bom(candidate/'factory_BOM.csv');switches=set(components)-factory
        for mode,refs in [('factory',factory),('switches',switches)]:write_cpl(REFERENCE/'raw_positions.csv',candidate/(mode+'_CPL.csv'),refs)
        rows=[{'Reference':ref,'Value':c['value'],'Manufacturer':c['fields']['Manufacturer'],'MPN':c['fields']['MPN'],
               'LCSC':c['fields'].get('LCSC',''),'Footprint':c['footprint'],'Assembly':'customer switches' if ref in switches else 'factory'}
              for ref,c in sorted(components.items(),key=lambda x:natural_ref_key(x[0]))]
        write_csv(candidate/'complete_BOM.csv',list(rows[0]),rows)
        apertures=[];locators=[]
        for f in g['footprints']:
            if f['ref'] not in switches:continue
            for q in f['pads']:
                if 'F.Paste' in q['layers']:apertures.append({'Reference':f['ref'],'Pad':q['number'],'X_mm':q['position'][0],'Y_mm':q['position'][1],'Width_mm':q['size'][0],'Height_mm':q['size'][1],'Net':q['net']})
                elif q['attribute']==3:locators.append({'Reference':f['ref'],'X_mm':q['position'][0],'Y_mm':q['position'][1],'Drill_mm':q['drill'][0]})
        write_csv(candidate/'paste/switch_apertures.csv',list(apertures[0]),apertures)
        write_csv(candidate/'paste/locator_holes.csv',list(locators[0]),locators)
        exports=verify_exports(candidate,g,restricted);(REFERENCE/'export-check.json').write_text(json.dumps(exports,indent=2)+'\n')
        for suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro'):shutil.copyfile(staged.with_suffix(suffix),REFERENCE/('checked'+suffix))
        for name in before:
            dest=candidate/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PROJECT_DIR/name,dest)
        files=copy_gerbers_to_upload_zip(candidate/'keyboard_GERBERS.zip');write_readme(candidate/'README.md',files)
        (candidate/'PCBA_ORDER_REMARK.txt').write_text('fit D320-D384 and J320 only, using the exact supplied BOM. SW320-SW384 are customer-installed CHERRY MX6C-T3NB. no switch substitutions. print no paste on any switch contact or fixation land during factory assembly. use paste/factory only and retain flat switch lands. diode cathode stripe goes to pad 1.\n')
        require(source_snapshot()==before,'canonical source changed during export; no package promoted')
        manifest={'schema':1,'status':'CHECKED_FABRICATION_FILES','board':str(BOARD.relative_to(PROJECT_DIR)),
                  'source_sha256':before,'checked_board_sha256':digest(staged),'kicad_version':subprocess.check_output([str(KICAD_CLI),'version'],text=True).strip(),
                  'restored_drc_categories':restored,'exclusion_source':EXCLUSION_SOURCE,'exclusion_bounds_mm':EXCLUSION_BOUNDS,
                  'checks':{'saved_drc_findings':0,'refilled_drc_findings':0,'native_airwires':g['native_airwires'],'parity_passed':True,
                            'copper_exclusion_hits':0,'export_mismatches':0,'copper_layers':g['copper_layers'],'complete_parts':len(components),
                            'factory_parts':len(factory),'switch_parts':len(switches)},
                  'physical_assembly_qualification':'NOT_RUN','reproducibility':'same sources and tool versions regenerate the checked outputs; tool-generated timestamps are not byte reproducibility'}
        (candidate/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');write_checksums(candidate/'SHA256SUMS.txt')
        verify_package(candidate)
        backup=promote(candidate,output,replace)
        print(f'keyboard package checks passed: {output}')
        if backup:print(f'previous package retained: {backup}')
    OUTPUT=output;REFERENCE=output/'reference';RAW=output/'gerbers'
    return output


def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    if argv and argv[0]=='--native':
        native_worker(*map(Path,argv[1:4]));return 0
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--replace',action='store_true',help='retain existing package as a sibling backup after all new checks pass')
    parser.add_argument('--verify-package',type=Path,help='verify a retained package against current sources without exporting')
    parser.add_argument('--kicad-python');parser.add_argument('--kicad-cli')
    args=parser.parse_args(argv)
    try:
        if args.verify_package:
            verify_package(args.verify_package.resolve());print('keyboard package matches current sources and all bound artifacts')
        else:build_package(args.output,args.replace,args.kicad_python,args.kicad_cli)
    except (RuntimeError,OSError,ImportError,subprocess.SubprocessError,ValueError,KeyError) as exc:
        print(f'keyboard package: FAIL: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())

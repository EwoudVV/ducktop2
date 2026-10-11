"""Show the checked fan route, removable clamp and external feet."""
import hashlib,json
from pathlib import Path
import cadquery as cq
import check_cooler,fan_harness
from draw_cooler import render
from cad import box,compound,export_step,_MESHES,mesh
from review import bbox_overlap

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def crop_shape(shape,region):
    b=region.BoundingBox();pieces=[]
    for solid in shape.Solids():
        if not bbox_overlap(solid,region):continue
        a=solid.BoundingBox()
        if a.xmin>=b.xmin and a.xmax<=b.xmax and a.ymin>=b.ymin and a.ymax<=b.ymax and a.zmin>=b.zmin and a.zmax<=b.zmax:
            pieces.append(solid)
        else:pieces.extend(solid.intersect(region).Solids())
    return compound(pieces) if pieces else None


def main():
    parts,case,sources=check_cooler.load_case()
    report=json.loads((HERE/'fan-harness-checks.json').read_text())
    checks=json.loads((HERE/'checks.json').read_text())
    assert report['nominal_geometry_pass'] and checks['feet_checks']['nominal_geometry_pass']
    for path,h in report['source_hashes'].items():assert sha(ROOT/path)==h,path
    html=(HERE/'inspection.html').read_text();start=html.index('const DATA=')+len('const DATA=')
    viewer,_=json.JSONDecoder().raw_decode(html[start:]);assert viewer['source_hashes']==sources
    meshes={p['name']:p for p in viewer['parts']}
    for p in parts:
        m=meshes[p['name']];_MESHES[id(p['shape'])]=(p['shape'],([cq.Vector(*v) for v in m['v']],m['f']))
    route=[];region=box(138,43,0,205,145,25)
    for p in parts:
        if p['name']=='keyboard-carrier-reservation':
            s=crop_shape(p['shape'],region)
            if s is not None:route.append({**p,'shape':s,'color':(.55,.66,.7,.12)})
            continue
        if p.get('moving') or (p['group'] in ['keepout','changes','deck','inputs'] and not p.get('fan_card_space')) or p['name'].startswith(('keyboard','trackpad','base-')):continue
        if not bbox_overlap(region,p['shape']):continue
        s=crop_shape(p['shape'],region)
        if s is not None:route.append({**p,'shape':s,'color':(.90,.46,.12) if p['name']=='fan-loom-envelope' else p['color']})
    route.append({'name':'carrier-guide-highlights','shape':fan_harness.carrier_guide(),'color':(.17,.55,.73)})
    render(route,HERE/'views/fan-route.png','orange: fan leads / blue: supports / purple: card space / carrier shown faintly',direction=(.1,-.3,1.7),size=(1750,1150))
    close=[];region=box(287,143,-.1,50,46,24)
    for p in parts:
        if p.get('moving') or p['group'] in ['keepout','changes','deck','inputs'] or p['name'].startswith(('keyboard','trackpad','base-walls')):continue
        if not bbox_overlap(region,p['shape']):continue
        s=crop_shape(p['shape'],region)
        if s is not None:close.append({**p,'shape':s,'color':(.90,.46,.12) if p['name']=='fan-loom-envelope' else p['color']})
    render(close,HERE/'views/fan-clamp.png','removable lead clamp and splice support / prototype fit',direction=(.7,-1,1.2),size=(1550,1050))
    bottom=[p for p in parts if p['name']=='base-floor' or p.get('external_foot') or p['name'].startswith('fin-bottom-screw-')]
    bottom=[{**p,'color':(.2,.32,.37)} if p.get('external_foot') else p for p in bottom]
    render(bottom,HERE/'views/feet-underneath.png','five 4.1 mm nominal feet / intake and fin screws remain clear',direction=(.3,-.5,-1.5),size=(1650,1150))
    physical=[p for p in parts if p.get('fan_harness') and p['group']!='keepout']
    physical.extend([{'shape':fan_harness.clamp_base()},{'shape':fan_harness.carrier_guide()}])
    target=HERE/'exports/fan-harness.step';export_step(compound(p['shape'] for p in physical),target)
    reopened=cq.importers.importStep(str(target)).val();assert reopened.isValid()
    names=['views/fan-route.png','views/fan-clamp.png','views/feet-underneath.png','exports/fan-harness.step']
    result={'source_hashes':{**report['source_hashes'],str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),
                             str((HERE/'draw_cooler.py').relative_to(ROOT)):sha(HERE/'draw_cooler.py')},
            'outputs':{p:sha(HERE/p) for p in names},'STEP_reopens':True,'STEP_solids':len(reopened.Solids()),
            'scope':'CAD inspection views and dressing envelopes; not a fabrication or harness production release'}
    (HERE/'fan-harness-exports.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Saved three fan/foot views and a reopened harness inspection STEP.',flush=True)


if __name__=='__main__':main()

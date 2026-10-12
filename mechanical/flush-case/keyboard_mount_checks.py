"""Check keyboard supports, mounting access and the remaining pin-height space."""
import hashlib,json
from pathlib import Path
import cadquery as cq
import check_cooler
import keyboard_mounts as k
import display_plug_checks
import usb_harness
from component_heights import resolve
from cad import box,cylinder,compound,export_step,_MESHES
from review import bbox_overlap,intersection_volume
from cooling_review import screen_component_heights

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def pin_limits(parts):
    top=k.config()['carrier']['keyboard_bottom_H'];pool=[]
    excluded={'keyboard-carrier-reservation','keyboard-insulating-sheet','keyboard-pcb-and-available-models','key-travel-and-cap-envelopes'}
    for p in parts:
        if p.get('moving') or p.get('service') or p['name'] in excluded or p['group']=='changes':continue
        for s in p['shape'].Solids():
            b=s.BoundingBox()
            if b.zmin>=top or b.zmax<=5.5:continue
            pool.append((p['name'],s,b))
    rows=[]
    for hole in k.INV['holes']:
        x,y=hole['position'];x+=24.75;y+=19.7;r=hole['drill'][0]/2+.2
        column=cylinder(x,y,5.5,r,top-5.5);highest=5.5;limiting='motherboard top datum'
        for name,s,b in pool:
            if b.xmax<=x-r or b.xmin>=x+r or b.ymax<=-y-r or b.ymin>=-y+r or b.zmax<=highest:continue
            cut=s.intersect(column)
            if cut.Solids() and sum(v.Volume() for v in cut.Solids())>.001:
                level=cut.BoundingBox().zmax
                if level>highest:highest=level;limiting=name
        rows.append({'switch':hole['reference'],'hole_xy_mm':[round(x,5),round(y,5)],
                     'column_radius_mm':r,'space_below_PCB_mm':round(top-highest,5),
                     'projection_limit_after_0_2_mm_gap':round(top-highest-.2,5),'limiting_part':limiting})
    assert len(rows)==195
    return {'holes':rows,'minimum_space_below_PCB_mm':min(r['space_below_PCB_mm'] for r in rows),
            'minimum_projection_limit_mm':min(r['projection_limit_after_0_2_mm_gap'] for r in rows),
            'measured_pin_projection_mm':k.config()['carrier']['pin_projection_below_PCB_mm'],
            'pin_projection_verified':False,
            'scope':'Cylinders at the PCB locating holes use the hole radius plus 0.2 mm. The steel and film openings are checked separately. These are available-space limits, not measured switch pins; width, alignment and full mechanism motion still need the exact switch.'}


def evaluate(parts,case,sources):
    new=[p for p in parts if p.get('keyboard_mount')]
    fixed=[p for p in parts if not p.get('keyboard_mount') and not p.get('moving') and not p.get('service') and p['group'] not in ['keepout','changes']]
    checker=display_plug_checks.CollisionCheck(parts,case);hits=[];internal=[]
    for a in new:
        for b in fixed:
            v=checker.volume(a,b)
            if v>.01:hits.append({'new':a['name'],'part':b['name'],'overlap_mm3':round(v,5)})
        print('keyboard mount checked',a['name'],flush=True)
    for i,a in enumerate(new):
        for b in new[i+1:]:
            if not bbox_overlap(a['shape'],b['shape']):continue
            v=intersection_volume(a['shape'],b['shape'])
            if v>.01:internal.append({'a':a['name'],'b':b['name'],'overlap_mm3':round(v,5)})

    table,settings=usb_harness.height_inputs()
    for file in ['cooler-part-heights.json','fan-harness-heights.json','display-part-heights.json','keyboard-part-heights.json']:
        extra=json.loads((HERE/file).read_text());settings['reservations'].update(extra['reservations'])
        for p in table:
            if p.get('mpn') in extra['manufacturer_maximums']:
                h=extra['manufacturer_maximums'][p['mpn']]
                p.update(height_mm=h['height_mm'],height_kind='maximum',height_status='verified_maximum',height_source_url=h['source'],height_basis=h['basis'])
    targets=[p for p in new if p['name'] not in ['keyboard-carrier-reservation','keyboard-insulating-sheet']]
    targets += [p for p in k.parts() if p['name'].startswith('keyboard-root-block-')]
    plate=k.plate_and_film()[0]
    screened=[p for p in table if not(p['board']=='center' and p['reference']=='H22')]
    heights=screen_component_heights(screened,targets,{'left':5.5,'center':5.5,'right':5.5,'bms':9.5},settings)
    from shapely.geometry import Polygon,box as rectangle
    b=plate.BoundingBox();area=rectangle(b.xmin,-b.ymax,b.xmax,-b.ymin)
    tops={'left':5.5,'center':5.5,'right':5.5,'bms':9.5}
    for p in screened:
        if p['dnp'] or p['side']!='front' or p['board'] not in tops or (p['board']=='center' and p['reference']=='A1'):continue
        rings=p['courtyards_installed_mm']['front']
        if not any(Polygon(r['outer'],r['holes']).intersects(area) for r in rings):continue
        h=resolve(p,settings);available=b.zmin-tops[p['board']]
        if h is not None and h['height_mm']<=available:
            row={'part':p['board']+'/'+p['reference'],'mpn':p['mpn'],'near':'keyboard-carrier-reservation',
                 'available_height_mm':round(available,4),'planning_gap_mm':round(available-h['height_mm'],4),
                 'screen':'conservative carrier bounding rectangle at its lowest surface',**h}
            heights['component_height_crossings'].append(row)
            if h['basis']=='assembly_reservation':heights['assembly_height_reservations'].append(row['part'])
        else:
            exact=screen_component_heights([p],[{'name':'keyboard-carrier-reservation','shape':plate}],tops,settings)
            for key in heights:heights[key].extend(exact[key])
    heights['assembly_height_reservations']=sorted(set(heights['assembly_height_reservations']))
    fuse_parts=[p for p in screened if p['mpn']=='0297003.WXNV + 3568']
    fuse_targets=[p for p in parts if p['name'] in ['keyboard-pcb-and-available-models','keyboard-insulating-sheet']]
    fuse_heights=screen_component_heights(fuse_parts,fuse_targets,tops,settings)
    for key in heights:heights[key].extend(fuse_heights[key])
    heights['assembly_height_reservations']=sorted(set(heights['assembly_height_reservations']))

    access=[];byname={p['name']:p for p in parts}
    for i,(side,y) in enumerate(k.SUPPORTS,1):
        x=-.5 if side=='left' else 358.5
        tool=cylinder(x,y,20.3,2,20).fuse(cylinder(x,y,40.3,4,20));found=[]
        for p in parts:
            if p.get('moving') or p.get('service') or p['group'] in ['keepout','changes'] or p['name'] in ['deck',f'keyboard-root-screw-{i}']:continue
            v=checker.volume({'name':f'root-tool-{i}','shape':tool},p)
            if v>.01:found.append({'part':p['name'],'volume_mm3':round(v,5)})
        access.append({'fastener':f'keyboard-root-screw-{i}','remove_first':['deck'],'collisions':found})
    removed=['deck','keyboard-pcb-and-available-models','key-travel-and-cap-envelopes','keyboard-insulating-sheet','keyboard-carrier-reservation']
    removed += [p['name'] for p in new if p['name'].startswith(('keyboard-edge-clip-','keyboard-clip-screw-','keyboard-clip-nut-','keyboard-carrier-screw-','keyboard-carrier-washer-'))]
    for name,tool,extra in [
        ('center-cap',cylinder(105,70,19.7,2,20).fuse(cylinder(105,70,39.7,4,20)),['keyboard-center-stop-screw']),
        ('center-spacer',cylinder(105,70,5.5,3.5,35),['keyboard-center-stop-cap','keyboard-center-stop-screw','keyboard-center-stop-spacer']),
    ]:
        found=[]
        for p in parts:
            if p.get('moving') or p.get('service') or p['group'] in ['keepout','changes'] or p['name'] in removed+extra:continue
            v=checker.volume({'name':name+'-tool','shape':tool},p)
            if v>.01:found.append({'part':p['name'],'volume_mm3':round(v,5)})
        access.append({'fastener':name,'remove_first':removed+extra,'collisions':found})
    pins=pin_limits(parts)
    limits={'typing_stiffness_verified':False,'pin_projection_verified':False,'warm_fit_verified':False,'manufacturing_ready':False}
    result={'date':k.config()['date'],'source_hashes':sources,'configuration':k.config(),'solid_conflicts':hits,'internal_conflicts':internal,
            'component_heights':heights,'component_height_scope':'New hardware and the full carrier. Already-safe component heights use the conservative carrier bounding rectangle; potential conflicts or missing height limits receive exact material checks. A1 retains its separate official-model and cooler checks.',
            'installation_access':access,'switch_pin_space':pins,'carrier_volume_mm3':round(plate.Volume(),4),
            'carrier_mass_g':round(plate.Volume()/1000*k.config()['carrier']['density_g_cm3'],2),
            'screen_to_key_nominal_gap_mm':round(28.3-(case['boards']['keyboard_bottom_H']+.8+4.5),4),**limits,
            'nominal_hardware_geometry_pass':not hits and not internal and not any(p['collisions'] for p in access),
            'new_component_height_screen_clear':not heights['unverified_component_height_screens'] and not heights['known_component_height_conflicts'],
            'notes':['The insulator, clips and steel must be checked against the actual assembled keyboard before tightening.',
                     'Clinch installation needs the specified sheet hardness, thickness, hole size and press tooling; the CAD does not qualify the installation.',
                     'The spacer uses the existing H22 mounting hole and backed PCB pad. The cap is a local deflection stop, not proof of overall keyboard stiffness.',
                     'Root screws clamp the brackets to the case bosses. These are not qualified sliding joints for thermal expansion.',
                     'Switch projection is not known. The reported limits must exceed the measured pins and mechanism movement before making the carrier.',
                     'The metal carrier, case bonding and liner wear need electrical-isolation checks. No battery return-domain connection or PCB change is made here.']}
    return result


def draw(parts):
    from draw_cooler import render
    from draw_fan_harness import crop_shape
    selected=[p for p in parts if p.get('keyboard_mount')]
    visible=[p for p in selected if p['name']!='keyboard-insulating-sheet']
    render(visible,HERE/'views/keyboard-mounts.png','metal carrier / eight edge clips / four case supports',(.12,-.6,1.2),(1650,1050))
    scenes=[('keyboard-edge-clip',box(49,9,16,23,21,13),'edge capture / locating gap / switch clearances'),
            ('keyboard-case-support',box(-6,26,13,54,18,15),'carrier bracket / captured case nut / removable mount'),
            ('keyboard-center-stop',box(97,62,1,16,16,27),'H22 support stop / 0.3 mm nominal unloaded gap')]
    for name,region,title in scenes:
        scene=[]
        for p in parts:
            if p.get('moving') or p.get('service') or p['group'] in ['keepout','changes'] or p['name'] in ['deck','key-travel-and-cap-envelopes']:continue
            shape=crop_shape(p['shape'],region)
            if shape is not None:
                color=(*p['color'][:3],.25) if p['name'] in ['keyboard-carrier-reservation','keyboard-pcb-and-available-models'] else p['color']
                scene.append({**p,'shape':shape,'color':color})
        render(scene,HERE/f'views/{name}.png',title,(.5,-.8,.9),(1500,1050))
    from cables import polygon_prism
    footprints=json.loads((ROOT/'mechanical/component-placement.json').read_text())['parts']
    allocations=json.loads((HERE/'keyboard-part-heights.json').read_text())['reservations']
    for board,ref,region in [('center','F190',box(89,46,3,19,24,26)),('left','F195',box(31,15,3,23,15,26))]:
        p=next(p for p in footprints if p['board']==board and p['reference']==ref)
        scene=[]
        for item in parts:
            if item.get('moving') or item.get('service') or item['group'] in ['keepout','changes'] or item['name'] in ['deck','key-travel-and-cap-envelopes']:continue
            s=crop_shape(item['shape'],region)
            if s is not None:
                color=(*item['color'][:3],.25) if item['name'] in ['keyboard-carrier-reservation','keyboard-pcb-and-available-models'] else item['color']
                scene.append({**item,'shape':s,'color':color})
        height=allocations[board+'/'+ref]['height_mm']
        for ring in p['courtyards_installed_mm']['front']:
            scene.append({'name':ref+'-installed-height-allocation','shape':polygon_prism(ring['outer'],5.5,height),'color':(.9,.15,.1,.48)})
        render(scene,HERE/f'views/keyboard-fuse-{ref.lower()}.png',ref+' / red: provisional full fuse-height allowance',(.5,-.9,.75),(1400,1050))
    dest=HERE/'exports/keyboard-mounts.step'
    export_step(compound(p['shape'] for p in selected+[p for p in k.parts() if p['name'].startswith('keyboard-root-block-')]),dest)
    s=cq.importers.importStep(str(dest)).val();assert s.isValid()
    return {'file':str(dest.relative_to(HERE)),'reopens':True,'solids':len(s.Solids())}


def main():
    parts,case,sources=check_cooler.load_case();case_sources=dict(sources)
    files=[Path(__file__),HERE/'keyboard_mounts.py',HERE/'keyboard-mounts.json',HERE/'keyboard-part-heights.json',HERE/'cooler-part-heights.json',HERE/'fan-harness-heights.json',HERE/'display-part-heights.json',HERE/'draw_cooler.py',HERE/'draw_fan_harness.py',HERE/'display_plug_checks.py']
    for p in files:sources[str(p.relative_to(ROOT))]=sha(p)
    report=evaluate(parts,case,sources);out=HERE/'keyboard-mount-checks.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print('mount geometry',report['nominal_hardware_geometry_pass'],'height screen',report['new_component_height_screen_clear'],flush=True)
    raw=(HERE/'inspection.html').read_text();viewer,_=json.JSONDecoder().raw_decode(raw.split('const DATA=',1)[1]);assert viewer['source_hashes']==case_sources
    mesh={p['name']:p for p in viewer['parts']}
    for p in parts:
        m=mesh[p['name']];_MESHES[id(p['shape'])]=(p['shape'],([cq.Vector(*v) for v in m['v']],m['f']))
    report['STEP_export']=draw(parts)
    outputs=['views/keyboard-mounts.png','views/keyboard-edge-clip.png','views/keyboard-case-support.png','views/keyboard-center-stop.png','views/keyboard-fuse-f190.png','views/keyboard-fuse-f195.png','exports/keyboard-mounts.step']
    report['outputs']={p:sha(HERE/p) for p in outputs}
    for p,h in sources.items():assert sha(ROOT/p)==h,p
    out.write_text(json.dumps(report,indent=2)+'\n')
    if not (report['nominal_hardware_geometry_pass'] and report['new_component_height_screen_clear']):
        raise SystemExit('Keyboard fit is not released. See solid, height and access conflicts in keyboard-mount-checks.json.')


if __name__=='__main__':main()

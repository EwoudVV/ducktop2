"""Check the modeled removal order without lifting the fixed fan wiring."""
import hashlib
import json
from pathlib import Path

import cadquery as cq
import check_cooler
import display_hinge_study as display
import display_plug_checks
import fan_guide_mounts as mounts
import keyboard_mounts
from cad import box, cylinder, compound, export_step, _MESHES

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
KEYBOARD=['keyboard-pcb-and-available-models','key-travel-and-cap-envelopes']
SCREWS=[f'keyboard-fan-guide-screw-{i}' for i in range(1,6)]+[
    'harness-USB-left-keyboard-screw','harness-USB-right-keyboard-screw']
CLIPS=[f'keyboard-edge-clip-{i}' for i in range(1,9)]
CLIP_SCREWS=[f'keyboard-clip-screw-{i}' for i in range(1,9)]
CARRIER_SCREWS=[f'keyboard-carrier-screw-{i}' for i in range(1,5)]
CARRIER_WASHERS=[f'keyboard-carrier-washer-{i}' for i in range(1,5)]
CARRIER_NUTS=[f'keyboard-clip-nut-{i}' for i in range(1,9)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config():
    return json.loads((HERE/'keyboard-service.json').read_text())


def j320_spaces():
    c=config()['J320'];x,y,h=c['finger_center_start_xyH_mm']
    return [
        {'name':'J320-upper-actuator-space','shape':box(*c['upper_actuator_space_xyHwhd_mm']),'color':(.79,.45,.15,.3)},
        {'name':'J320-external-FFC-space','shape':box(*c['external_FFC_space_xyHwhd_mm']),'color':(.2,.5,.8,.3)},
        {'name':'J320-finger-space','shape':cq.Solid.makeCylinder(c['finger_radius_mm'],c['finger_length_mm'],cq.Vector(x,-y,h),cq.Vector(1,0,0)),'color':(.8,.45,.15,.2)},
    ]


def thread_obstacle(screw,obstacle):
    if screw.get('thread_host')!=obstacle['name']:
        return obstacle
    x,y=screw['thread_axis_xy_mm'];lo,hi=screw['thread_height_range_mm']
    cut=cylinder(x,y,lo-.01,screw['thread_radius_mm']+.01,hi-lo+.02)
    return {**obstacle,'name':obstacle['name']+'-thread-clearance','shape':obstacle['shape'].cut(cut)}


def evaluate(saved,case,sources):
    c=config();parts,reliefs=display.study_case_parts(saved);new,_=display.geometry()
    parts += [{**p,'group':'wiring'} for p in new]
    physical=[display.pose(p,c['lid_angle_deg']) for p in parts if not p.get('service') and p['group'] not in ['keepout','changes']]
    byname={p['name']:p for p in physical}
    checker=display_plug_checks.CollisionCheck(physical,case)
    hits=[];stages=[]

    def test(name,shape,obstacles,stage,**fields):
        found=[]
        for p in obstacles:
            v=checker.volume({'name':name,'shape':shape},p)
            if v>.01:
                row={'stage':stage,'candidate':name,'part':p['name'],'overlap_mm3':round(v,5),**fields}
                hits.append(row);found.append(row)
        return found

    steps=[round(i*c['lift_step_mm'],5) for i in range(round(c['lift_mm']/c['lift_step_mm'])+1)]
    for stage,names,removed in [
        ('deck',['deck'],[]),
        ('keyboard',KEYBOARD,['deck',*CLIPS,*CLIP_SCREWS]),
        ('film',['keyboard-insulating-sheet'],['deck',*KEYBOARD,*CLIPS,*CLIP_SCREWS]),
        ('carrier',['keyboard-carrier-reservation',*CARRIER_NUTS],['deck',*KEYBOARD,'keyboard-insulating-sheet',*CLIPS,*CLIP_SCREWS,*SCREWS,*CARRIER_SCREWS,*CARRIER_WASHERS]),
    ]:
        moving=compound(byname[n]['shape'] for n in names)
        obstacles=[p for p in physical if p['name'] not in names+removed]
        before=len(hits)
        for i,dz in enumerate(steps):
            test(f'{stage}-lift-{i}',moving.translate((0,0,dz)),obstacles,stage,lift_mm=dz)
        row={'stage':stage,'moving_parts':names,'remove_first':removed,'lift_samples_mm':steps,'collision_count':len(hits)-before}
        stages.append(row);print('service lift',stage,row['collision_count'],'collisions',flush=True)

    clip_removal=[]
    for name in CLIPS:
        before=len(hits);obstacles=[p for p in physical if p['name'] not in ['deck',name,*CLIP_SCREWS]]
        for i in range(21):test(name+f'-lift-{i}',byname[name]['shape'].translate((0,0,i*.5)),obstacles,'clip-lift',lift_mm=i*.5)
        clip_removal.append({'clip':name,'lift_mm':10,'samples':21,'collision_count':len(hits)-before})
    access=[]
    for name in [*SCREWS,*CLIP_SCREWS,*CARRIER_SCREWS]:
        screw=byname[name]
        companions=[];removed=['deck'];seat=mounts.config()['carrier_top_H'];travel=6
        if name.startswith('keyboard-fan-guide-screw-'):
            x,y=mounts.config()['mounts_xy_mm'][int(name.rsplit('-',1)[1])-1]
        elif name.startswith('keyboard-clip-screw-'):
            x,y,_=keyboard_mounts.CLIPS[int(name.rsplit('-',1)[1])-1];seat=23.4;travel=8
        elif name.startswith('keyboard-carrier-screw-'):
            i=int(name.rsplit('-',1)[1]);side,y=keyboard_mounts.SUPPORTS[i-1];x=37 if side=='left' else 321
            seat=21.5;companions=[f'keyboard-carrier-washer-{i}'];removed+=KEYBOARD+['keyboard-insulating-sheet',*CLIPS,*CLIP_SCREWS]
        else:
            x,y=screw['thread_axis_xy_mm']
        obstacles=[p for p in physical if p['name'] not in [*removed,name,*companions]]
        tool=cylinder(x,y,seat,2,20).fuse(cylinder(x,y,seat+20,4,20))
        found=test(name+'-driver',tool,obstacles,'driver-access')
        access.append({'screw':name,'remove_first':removed,'collisions':found})
        obstacles=[thread_obstacle(screw,p) for p in physical if p['name'] not in [*removed,name,*companions]]
        moving=compound([screw['shape'],*[byname[n]['shape'] for n in companions]])
        before=len(hits)
        for i in range(round(travel/.5)+1):
            test(name+f'-withdraw-{i}',moving.translate((0,0,i*.5)),obstacles,'screw-withdrawal',lift_mm=i*.5)
        access[-1]['withdrawal_mm']=travel
        access[-1]['withdrawal_collisions']=len(hits)-before
        print('service screw',name,len(found),len(hits)-before,flush=True)

    latch=[]
    for p in j320_spaces():
        found=test(p['name'],p['shape'],[v for v in physical if v['name']!='deck'],'J320-access')
        latch.append({'space':p['name'],'collisions':found})
    result={'date':c['date'],'source_hashes':sources,'configuration':c,'removal_stages':stages,
            'screw_access':access,'clip_removal':clip_removal,'J320_access':latch,'collisions':hits,
            'modeled_removal_sequence_clear':not hits,
            'display_study_context':{'proposed_reliefs':reliefs,'scope':'The display grip and rear-guard changes are applied locally, as in the separate display study. The fan-guide mounts are in the main case.'},
            'thread_contact_exclusion':'Only each original USB screw host cylinder at its recorded thread axis, radius and height is cleared for the unscrewing check. The rest of each guide rail remains an obstacle.',
            'physical_service_verified':False,'complete_keyboard_mounting_verified':False,'manufacturing_ready':False,
            'limits':['The keyboard FFC must be disconnected and parked before any keyboard lift. Its complete installed route and parking space are not modeled.',
                      'Deck retention and attached input-device cables are unfinished. The new keyboard retention still needs actual stack, keycap, load and warm-fit tests. This is not a full disassembly release.',
                      'Secure the detached guides and both USB rails on temporary insulating supports before lifting the carrier. Their unsupported weight and cable deflection are not qualified.',
                      'Removal is sampled at 0.5 mm intervals. This does not prove continuous-motion clearance or tolerance fit.',
                      'The J320 spaces are access allocations above and outside the closed connector. They do not simulate latch internals or establish hand fit.',
                      'The carrier insulation, printed clips and guide arms need stiffness, thread, pull and warm-service tests.',
                      'Driver envelopes cover access above the head. They do not simulate the bit/recess engagement of the countersunk screws.']}
    return result,parts


def draw(parts):
    from draw_cooler import render
    from draw_fan_harness import crop_shape
    region=box(139,63,10,147,49,43);context=[]
    for p in parts:
        if p.get('moving') or p.get('service') or p['group'] in ['keepout','changes'] or p['name'] in ['deck',*KEYBOARD,'keyboard-insulating-sheet',*CLIPS,*CLIP_SCREWS]:continue
        shape=crop_shape(p['shape'],region)
        if shape is not None:context.append({**p,'shape':shape})
    seated=[{**p,'color':(*p['color'][:3],.25)} if p['name']=='keyboard-carrier-reservation' else p for p in context]
    render(seated,HERE/'views/keyboard-guide-mounts.png','five removable fan guides / screws accessible at the front',(.2,-.6,1.1),(1550,1050))
    released=[]
    for p in context:
        if p['name'] in [*SCREWS,*CARRIER_SCREWS,*CARRIER_WASHERS]:continue
        if p['name'] in ['keyboard-carrier-reservation',*CARRIER_NUTS]:p={**p,'shape':p['shape'].translate((0,0,12)),'color':(*p['color'][:3],.3)}
        released.append(p)
    render(released,HERE/'views/keyboard-carrier-release.png','carrier lifted 12 mm / guides and loom remain in place',(.25,-.6,1),(1550,1050))
    close=box(142,65,11,14,47,17);scene=[]
    for p in seated:
        shape=crop_shape(p['shape'],close)
        if shape is not None:scene.append({**p,'shape':shape})
    render(scene,HERE/'views/keyboard-guide-detail.png','removable guide arm / M2 screw and locating key',(.45,-.6,.8),(1450,1050))
    region=box(294,44,18,44,36,24);scene=[]
    for p in parts:
        if p.get('moving') or p.get('service') or p['group'] in ['keepout','changes'] or p['name']=='deck':continue
        shape=crop_shape(p['shape'],region)
        if shape is not None:scene.append({**p,'shape':shape})
    render(scene+j320_spaces(),HERE/'views/keyboard-ffc-access.png','J320 latch and cable access / deck removed',(.5,-1,.8),(1550,1050))
    selected=[p for p in parts if p['name'] in ['keyboard-carrier-reservation',*CARRIER_NUTS] or p['name'].startswith('keyboard-fan-guide-')]
    dest=HERE/'exports/keyboard-service.step';export_step(compound(p['shape'] for p in selected),dest)
    reopened=cq.importers.importStep(str(dest)).val()
    assert reopened.isValid() and len(reopened.Solids())==19
    return {'file':str(dest.relative_to(HERE)),'reopens':True,'solids':len(reopened.Solids())}


def main():
    saved,case,sources=check_cooler.load_case()
    case_sources=dict(sources)
    for file in [Path(__file__),HERE/'keyboard-service.json',HERE/'display_hinge_study.py',HERE/'display-hinge-study.json',HERE/'display_grips.py',HERE/'display-grip-hardware.json',HERE/'display_plug.py',HERE/'display-plug.json',HERE/'display_plug_checks.py',HERE/'draw_cooler.py',HERE/'draw_fan_harness.py',*display.display_plug.REFERENCE.glob('*.brep'),display.display_plug.REFERENCE/'sources.json']:
        sources[str(file.relative_to(ROOT))]=sha(file)
    report,parts=evaluate(saved,case,sources)
    out=HERE/'keyboard-service-checks.json';out.write_text(json.dumps(report,indent=2)+'\n')
    raw=(HERE/'inspection.html').read_text();viewer,_=json.JSONDecoder().raw_decode(raw.split('const DATA=',1)[1])
    assert viewer['source_hashes']==case_sources,'rebuild the main case viewer first'
    meshes={p['name']:p for p in viewer['parts']}
    for p in saved:
        m=meshes[p['name']];_MESHES[id(p['shape'])]=(p['shape'],([cq.Vector(*v) for v in m['v']],m['f']))
    report['STEP_export']=draw(parts)
    files=['views/keyboard-guide-mounts.png','views/keyboard-carrier-release.png','views/keyboard-guide-detail.png','views/keyboard-ffc-access.png','exports/keyboard-service.step']
    report['outputs']={p:sha(HERE/p) for p in files}
    for p,h in sources.items():assert sha(ROOT/p)==h,p
    out.write_text(json.dumps(report,indent=2)+'\n')
    print('modeled removal sequence clear',report['modeled_removal_sequence_clear'],flush=True)
    assert report['modeled_removal_sequence_clear'],report['collisions']


if __name__=='__main__':main()

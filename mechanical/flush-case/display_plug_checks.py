"""External clearance and service-space checks for the connector reference."""
import json
from pathlib import Path

import cadquery as cq
import display_plug
from cad import box, bounds, compound, export_step
from review import bbox_overlap
from usb_collision import Checks

HERE=Path(__file__).resolve().parent


class CollisionCheck:
    def __init__(self, parts, case):
        rigid=[]
        for p in parts:
            if p['name'] not in ['harness-USB-left-carrier','harness-USB-right-carrier']:continue
            left='-left-' in p['name'];seam=70.75 if left else 299.25;bracket=130 if left else 225
            for region in [box(seam-4.5,0,0,9,260,26),box(bracket-5.1,100.9,0,10.2,25,26)]:
                shape=p['shape'].intersect(region)
                if shape.Solids() and shape.Volume()>.001:rigid.append({**p,'shape':shape})
        self.checker=Checks(parts,case,json.loads((HERE/'usb-harness.json').read_text()),rigid)
        self.box_rejections=0

    def volume(self, candidate, obstacle):
        s=candidate['shape'];q=obstacle['shape']
        if not bbox_overlap(s,q):return 0
        b=s.BoundingBox()
        cover=cq.Solid.makeBox(b.xlen,b.ylen,b.zlen,cq.Vector(b.xmin,b.ymin,b.zmin))
        # This box contains the candidate. A clear box proves the detailed
        # connector clear; a box hit still needs the actual geometry below.
        coarse=self.checker.volume({'name':candidate['name']+'-bounds','shape':cover},obstacle)
        if coarse<=.01:
            self.box_rejections+=1;return 0
        total=0
        for piece in q.Solids():
            if not bbox_overlap(cover,piece):continue
            clipped=piece.intersect(cover)
            for local in clipped.Solids():
                if not bbox_overlap(s,local):continue
                hit=s.intersect(local)
                if hit.Solids():total+=max(0,hit.Volume())
        return total


def evaluate(parts, case, pose):
    c=display_plug.config()
    physical=[p for p in parts if not p.get('service') and p['group'] not in ['keepout','changes']]
    physical=[display_plug.strip_native_port(p) for p in physical]
    closed_checker=CollisionCheck(physical,case)
    opened=[pose(p,c['service_lid_angle_deg']) for p in physical]
    service_checker=CollisionCheck(opened,case)
    hits=[];sweep_bounds=[]
    def check(candidate, obstacles, checker, stage, **extra):
        for p in obstacles:
            volume=checker.volume(candidate,p)
            if volume>.01:hits.append({'stage':stage,'candidate':candidate['name'],'part':p['name'],
                                      'overlap_mm3':round(volume,5),**extra})
    for part in display_plug.geometry():check(part,physical,closed_checker,'seated')
    angles=list(range(c['bar_swing_study_deg'][0],c['bar_swing_study_deg'][1]+1,c['bar_swing_step_deg']))
    for angle in angles:
        part={'name':f'display-lock-bar-{angle}','shape':display_plug.bar(angle)}
        check(part,opened,service_checker,'bar-swing',bar_angle_deg=angle)
        sweep_bounds.append({'angle_deg':angle,'bounds_construction_xyz':bounds(part['shape'])})
    allocation={'name':'display-upper-bar-space','shape':display_plug.upper_swing_space()}
    check(allocation,physical,closed_checker,'upper-swing-room')
    count=round(c['withdrawal_distance_mm']/c['withdrawal_step_mm'])
    for i in range(count+1):
        travel=i*c['withdrawal_step_mm']
        for name,s in [('body',display_plug.body(travel)),('bar',display_plug.bar(c['withdrawal_bar_angle_deg'],travel))]:
            check({'name':f'display-unplug-{name}-{i}','shape':s},opened,service_checker,'withdrawal',travel_mm=travel)
    remove=set(c['service_remove'])
    access_obstacles=[p for p in opened if p['name'] not in remove]
    tools=display_plug.access_spaces()
    for p in tools:check(p,access_obstacles,service_checker,'tool-access')
    final=display_plug.body(c['withdrawal_distance_mm']).BoundingBox()
    native=display_plug.references()['native-port'].BoundingBox()
    separated=final.xmin-native.xmax
    shape=display_plug.references()['pull-bar'];b=shape.BoundingBox();pivot=c['bar_pivot_reference_xyz_mm']
    radius_bound=((max(abs(b.ymin-pivot[1]),abs(b.ymax-pivot[1])))**2+
                  (max(abs(b.zmin-pivot[2]),abs(b.zmax-pivot[2])))**2)**.5
    result={'configuration':c,'external_collisions':hits,'bar_swing_samples':sweep_bounds,
            'nominal_bar_radius_upper_bound_mm':round(radius_bound,5),
            'nominal_highest_bar_H_mm':max(r['bounds_construction_xyz'][5] for r in sweep_bounds),
            'reference_receptacle_bounds':bounds(display_plug.reference_envelope()),
            'native_receptacle_bounds':bounds(display_plug.references()['native-port']),
            'native_port_excluded_from_mating_check':True,
            'excluded_interface_scope':'Only the uniquely identified native port solid is excluded for this bought connector-family reference. The module PCB and every other module component remain checked. This does not verify interchangeability with the installed connector.',
            'tool_corridors_checked':len(tools),'service_remove':sorted(remove),
            'withdrawal_steps':count+1,'fully_unmated_X_gap_mm':round(separated,5),
            'bound_rejections':closed_checker.box_rejections+service_checker.box_rejections,
            'nominal_external_geometry_pass':not hits and separated>0,
            'physical_part_identity_verified':False,'pin_1_orientation_verified':False,
            'physical_service_verified':False,'manufacturing_ready':False,
            'limits':['The reference archive predates the latest drawings and is used for family packaging only.',
                      'Bar rotation uses a drawing-derived pivot. Internal latch and hinge contact, release force and elastic deformation are outside this enclosure check.',
                      'The upper room allocation covers space above the connector, not all possible manufacturing variation at the mating interface.',
                      'Release the base jaw and free the loom before unplugging; wire strain during manipulation is not predicted.',
                      'The keyboard/carrier removal sequence and actual insulating-tool contact points need a physical check.']}
    print('module plug external collisions',len(hits),'fully unmated gap',separated,flush=True)
    return result


def draw(parts, render, here):
    from draw_fan_harness import crop_shape
    c=display_plug.config();region=box(230,38,9,27,41,12);context=[]
    for p in parts:
        if p.get('moving') or p.get('service') or p['group'] in ['keepout','changes','deck','inputs'] or p['name'].startswith('keyboard'):continue
        if not bbox_overlap(p['shape'],region):continue
        shape=crop_shape(p['shape'],region)
        if shape is not None:context.append({**p,'shape':shape})
    for angle,travel,label in [(0,0,'seated'),(90,0,'unlocked'),(90,5,'withdrawn')]:
        plug=[{'name':'module-plug-body','shape':display_plug.body(travel),'color':(.74,.53,.2)},
              {'name':'module-pull-bar','shape':display_plug.bar(angle,travel),'color':(.86,.33,.12)}]
        render(context+plug,here/f'views/display-plug-{label}.png',f'documented connector family / {label} / exact installed suffix unconfirmed',(.45,-1,1),(1550,1050),focus=((242,-58.54,14),24))
    scene=context+display_plug.geometry()+display_plug.access_spaces()
    render(scene,here/'views/display-plug-access.png','plug access corridors / keyboard and carrier removed',(.55,-1,.8),(1550,1050))
    dest=here/'exports/display-plug-study.step'
    export_step(compound(p['shape'] for p in context+display_plug.geometry()),dest)
    reopened=cq.importers.importStep(str(dest)).val();assert reopened.isValid()
    return {'file':str(dest.relative_to(here)),'solids':len(reopened.Solids()),'reopens':True}

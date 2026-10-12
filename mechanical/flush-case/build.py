#!/usr/bin/env python3
"""Build a flush clamshell candidate while preserving the earlier case and PCBs."""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT/'mechanical/case-prototype'
# The earlier geometry modules use imports relative to their own directory.
sys.path.insert(0, str(BASE))
import hinges
import model_cache
from cad import box, cylinder, compound, bounds, render, export_step, mesh, _MESHES
from build import CONFIG as OLD, INVENTORY
from review import bbox_overlap, intersection_volume

C = json.loads((HERE/'assembly.json').read_text())
CACHE = ROOT/'.workbench/flush-case-20261009/brep'
COLORS = {'shell':(.61,.66,.69), 'lid':(.43,.50,.55), 'deck':(.69,.73,.76),
          'boards':(.14,.43,.30), 'inputs':(.19,.23,.26), 'cells':(.79,.68,.34),
          'hinges':(.30,.32,.35), 'supports':(.28,.49,.55), 'cooling':(.67,.42,.26),
          'wiring':(.79,.31,.17), 'keepout':(.3,.64,.81,.25), 'changes':(.88,.23,.16,.65),
          'panel':(.075,.09,.10)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    data=model_cache.geometry_inputs()
    for name in ['assembly.json','board-inventory.json']:
        p=BASE/name;data[str(p.relative_to(ROOT))]=sha(p)
    for name,row in INVENTORY.items():
        p=ROOT/row['file'];digest=sha(p)
        if digest!=row['sha256']:raise ValueError(name+' PCB changed since the frozen case inputs')
        data[row['file']]=digest
    for p in [HERE/'assembly.json',HERE/'build.py']:
        data[str(p.relative_to(ROOT))]=sha(p)
    if C.get('usb_power_route'):
        for p in [HERE/'usb_harness.py',HERE/'usb_clearances.py',HERE/'usb_collision.py',HERE/'usb-part-heights.json',HERE/'usb-harness.json']:
            data[str(p.relative_to(ROOT))]=sha(p)
        for p in [ROOT/'mechanical/component-placement.json',BASE/'height-allowances.json']:
            data[str(p.relative_to(ROOT))]=sha(p)
    if C.get('cooling_layout'):
        for name in ['remote_cooler.py','cooler.json','cooler-part-heights.json','check_cooler.py','cooler_hardware.py','hardware_checks.py','cooler-hardware.json','reference/delta-fan-source.json','reference/BFB04512HHA-DV52.step']:
            p=HERE/name;data[str(p.relative_to(ROOT))]=sha(p)
    if C.get('feet'):
        for name in ['feet.json','case_feet.py']:
            p=HERE/name;data[str(p.relative_to(ROOT))]=sha(p)
    if C.get('fan_harness'):
        for name in ['fan-harness.json','fan-harness-heights.json','fan_harness.py','fan_harness_checks.py','fan_guide_mounts.py','fan-guide-mounts.json']:
            p=HERE/name;data[str(p.relative_to(ROOT))]=sha(p)
    if C.get('lid_stops'):
        for name in ['lid_stops.py','lid_stop_checks.py','lid-stop-hardware.json','fan-harness-heights.json','display-part-heights.json']:
            p=HERE/name;data[str(p.relative_to(ROOT))]=sha(p)
    if C.get('keyboard_mounts'):
        for name in ['keyboard_mounts.py','keyboard-mounts.json']:
            p=HERE/name;data[str(p.relative_to(ROOT))]=sha(p)
        p=ROOT/'ducktop2.pretty/Cherry_MX_ULP_SMD.kicad_mod';data[str(p.relative_to(ROOT))]=sha(p)
    return data


def rounded_slab(h,t,inset=0):
    b=C['outline'];x=b['x_min']+inset;y=b['y_min']+inset
    w=b['x_max']-b['x_min']-2*inset;d=b['y_max']-b['y_min']-2*inset
    radius=max(.2,b['corner_radius']-inset)
    return cq.Workplane('XY').box(w,d,t,centered=(False,False,False)).edges('|Z').fillet(radius).val().translate((x,-y-d,h))


def pose(item,angle):
    if not item.get('moving'):return item
    h=C['hinges'];p=(0,-h['pivot_y'],h['pivot_height'])
    return {**item,'shape':item['shape'].rotate(p,(1,p[1],p[2]),-angle)}


def fresh_model():
    before=inputs();m=model_cache.load();model_cache.preload_viewer_meshes(m)
    print('loaded checked baseline geometry',flush=True)
    parts=[]
    def add(name,shape,group='supports',moving=False,**extra):
        if not shape.isValid():raise ValueError('invalid shape: '+name)
        parts.append({'name':name,'shape':shape,'group':group,'moving':moving,'color':COLORS[group],**extra})
    def translated(source,delta,group=None):
        s=source['shape'].translate((0,0,delta))
        q={**source,'shape':s,'group':group or source['group'],'moving':False,'original_name':source['name']}
        if 'thread_height_range_mm' in q:q['thread_height_range_mm']=[h+delta for h in q['thread_height_range_mm']]
        # Reuse display tessellations after a rigid translation. CAD checks still use the BRep.
        if id(source['shape']) in _MESHES:
            vertices,triangles=_MESHES[id(source['shape'])][1]
            _MESHES[id(s)]=(s,([cq.Vector(v.x,v.y,v.z+delta) for v in vertices],triangles))
        parts.append(q)
    for p in m.parts:
        name=p['name']
        if C.get('usb_power_route') and name.startswith(('usb5-','harness-USB-')):continue
        if name in [n+'-pcb-and-available-models' for n in ['left','center','right','bms']]:translated(p,-1.2,'boards')
        elif name=='keyboard-pcb-and-available-models':translated(p,C['boards']['keyboard_bottom_H']-OLD['boards']['keyboard']['bottom_height'],'boards')
        elif name=='key-travel-and-cap-envelopes':translated(p,C['boards']['keyboard_bottom_H']-OLD['boards']['keyboard']['bottom_height'],'inputs')
        elif name.startswith('cell-') and p['group']=='cells':translated(p,-1.2,'cells')
        elif name.startswith('oled-') and p['group']=='inputs':translated(p,-8.5,'inputs')
        elif name.startswith('speaker-') and p['group']=='inputs':translated(p,-8.5,'inputs')
        elif p.get('power_wire') or p.get('harness_part') or p.get('harness_fastener') or p.get('terminal') or p.get('braid') or p.get('service'):
            translated(p,-1.2,'keepout' if p['group']=='keepout' else 'wiring')
        elif name=='raw-pack-J2-wire-exit-reservation':translated(p,-1.2,'keepout')
    usb_mounts=[]
    if C.get('usb_power_route'):
        import usb_harness
        usb_parts,usb_data,usb_mounts=usb_harness.load_parts()
        parts.extend(usb_parts)
    b=C['base'];o=C['outline'];dt=b['deck_top'];floor=b['floor'];h=C['hinges'];l=C['lid'];hy=h['pivot_y'];hh=h['pivot_height']
    width=o['x_max']-o['x_min'];depth=o['y_max']-o['y_min']
    body=rounded_slab(0,floor)
    walls=rounded_slab(floor,dt-floor-b['deck_thickness']).cut(rounded_slab(floor-.1,dt+1,b['wall']))
    # Leave the purchased hinge barrels visible in local rear openings.
    for hx in h['pivot_x']:
        walls=walls.cut(box(hx-27,o['y_min']-.1,hh-8.5,54,7,15.5))
    # The candidate has a direct side exhaust and bottom inlet.
    cx,cy=C['cooling']['fan_center'];rr=C['cooling']['fan_radius']
    if C.get('cooling_layout'):
        import cooler_hardware
        body=cooler_hardware.floor_shape(body,C)
    else:
        body=body.cut(cylinder(cx,cy,-.1,rr-4,floor+.2))
    if C.get('fan_harness'):
        import fan_harness
        body=fan_harness.floor_shape(body)
    fx,fy,fw,fd=C['cooling']['fins_xywh']
    if C.get('cooling_layout'):
        import remote_cooler
        exhaust_bottom=remote_cooler.config()['fins']['bottom_H']
    else:exhaust_bottom=1.8
    exhaust_height=C['cooling']['fins_height']+.5 if C.get('cooling_layout') else 7
    walls=walls.cut(box(o['x_max']-b['wall']-.1,fy-.5,exhaust_bottom-.25,2,fd+1,exhaust_height))
    # Existing ports stay in their current XY positions. Generous service slots
    # keep the shape study from claiming finished connector openings.
    walls=walls.cut(box(o['x_min']-.1,18,4,2,139,14))
    walls=walls.cut(box(o['x_max']-b['wall']-.1,15,3.5,2,100,15.5))
    if C.get('keyboard_mounts'):
        import keyboard_mounts
        walls=keyboard_mounts.wall_shape(walls)
    add('base-floor',body,'shell');add('base-walls',walls,'shell')
    if C.get('feet'):
        import case_feet
        parts.extend(case_feet.parts())
    deck=rounded_slab(dt-b['deck_thickness'],b['deck_thickness'])
    deck=deck.cut(box(41.75,19.5,dt-3,274.5,81,4)).cut(box(306,50,dt-3,23,23,4))
    t=C['trackpad'];deck=deck.cut(box(t['x']-.5,t['y']-.5,dt-3,t['width']+1,t['depth']+1,4))
    # A continuous rear band is cut only around the actual hinge seats.
    for hx in h['pivot_x']:deck=deck.cut(box(hx-28,hy-4,dt-3,56,32,4))
    for x,y in OLD['oled']['xy']:
        deck=deck.cut(box(x-.2,y-.2,dt-3,OLD['oled']['width']+.4,OLD['oled']['depth']+.4,4))
    add('deck',deck,'deck')
    kh=C['keyboard']['carrier_bottom_H']
    if C.get('keyboard_mounts'):
        carrier,film=keyboard_mounts.plate_and_film()
        assert abs(C['boards']['keyboard_bottom_H']-21.327)<1e-8
        add('keyboard-carrier-reservation',carrier,'supports',color=(.57,.61,.63),keyboard_mount=True)
        add('keyboard-insulating-sheet',film,'supports',color=(.7,.49,.18,.7),keyboard_mount=True)
        parts.extend(keyboard_mounts.hardware_parts())
    else:
        carrier=box(41.25,19,kh,275.5,82,1).cut(box(306,50,kh-.1,24,23,1.2))
        if C.get('usb_power_route'):carrier=usb_harness.carrier_tabs(carrier)
        if C.get('cooling_layout'):
            import remote_cooler
            carrier=remote_cooler.carrier_reliefs(carrier)
        if C.get('fan_harness'):carrier=fan_harness.carrier_shape(carrier)
        add('keyboard-carrier-reservation',carrier,'supports')
    tp=dt-t['body_thickness'];support=tp-t['click_travel']-t['under_clearance']-t['support_thickness']
    add('trackpad-body-reservation',box(t['x'],t['y'],tp,t['width'],t['depth'],t['body_thickness']),'inputs')
    add('trackpad-motion-reservation',box(t['x'],t['y'],tp-t['click_travel'],t['width'],t['depth'],t['body_thickness']+t['click_travel']),'keepout')
    add('trackpad-support-reservation',box(t['x']-2,t['y']-2,support,t['width']+4,t['depth']+4,t['support_thickness']),'supports')
    for x in OLD['cells']['x']:
        add('cell-swelling-space-'+str(x),box(x,188,13.2,100,60,3),'keepout')
    # All existing motherboard mounting holes stay fixed in XY.
    for board in ['left','center','right','bms']:
        for hole in INVENTORY[board]['holes']:
            ref=hole.get('reference')
            if (board=='bms' and ref is None) or (ref and ref.startswith('H') and ref not in ['H1','H2','H3','H4']):
                from build import installed
                x,y=installed(board,hole['position']);z=C['boards']['bms_bottom_H'] if board=='bms' else C['boards']['main_bottom_H']
                add(board+'-'+str(ref or hole['position'])+'-support',cylinder(x,y,floor,2.1,z-floor).cut(cylinder(x,y,floor-.1,1.1,z-floor+.2)),'supports')
    # New hinge supports carry loads into the rear reinforcement, not the PCB.
    spine=box(0,-16,floor,358,14,3)
    mount_rows=list(usb_mounts);lid_plates=[];lid_seats=[]
    for side,hx in zip(['left','right'],h['pivot_x']):
        for q in hinges.parts(side,hx,hy,hh,0):
            add(q['name'],q['shape'],'hinges',q['moving'],OEM=True)
        plate,bolts=hinges.base_plate(side,hx,hy,hh)
        add(side+'-base-seat-plate',plate,'supports')
        bb=plate.BoundingBox();seat=hh+hinges.BASE_SEAT[side]
        ear=box(bb.xmin,-2,floor,bb.xlen,19,3)
        spine=spine.fuse(ear)
        for index,(x,y) in enumerate(bolts):
            post=cylinder(x,y,floor+3,3,seat-3-floor-3).cut(cylinder(x,y,floor+2.9,1.25,seat-floor))
            add(f'{side}-hinge-post-{index}',post,'supports')
            mount_rows.append({'part':side,'x':x,'y':y,'top_H':seat-3,'note':'new support; bolt access and load capacity need checking'})
        p,seats,_=hinges.lid_plate(side,hx,hy,hh);lid_plates.append(p)
        for index,s in enumerate(seats):
            lid_seats.append(s);add(f'{side}-lid-seat-{index}',s,'supports',True)
    add('rear-base-reinforcement',spine,'supports')
    # A single 3 mm backing member occupies the same plane as the two former
    # lid plates. It does not add another plate behind them.
    rear_member=box(o['x_min']+6,hy-4,hh+10,width-12,31,3)
    rear_member=rear_member.intersect(rounded_slab(hh+9.9,3.2,l['rim_thickness']))
    for side,hx in zip(['left','right'],h['pivot_x']):
        for x,y,level,diam,thread,old,new in hinges.lid_holes(side,hx,hy):
            radius=.8 if thread=='M2' else .625
            rear_member=rear_member.cut(cylinder(x,y,hh+9.9,radius,3.2))
    add('rear-lid-backing-member',rear_member,'supports',True)
    back=hh+l['back_inner_height_from_axis']
    skin=rounded_slab(back,l['skin'])
    rim=rounded_slab(hh+l['rim_bottom_height_from_axis'],l['back_inner_height_from_axis']-l['rim_bottom_height_from_axis'])
    rim=rim.cut(rounded_slab(hh+l['rim_bottom_height_from_axis']-.1,8,l['rim_thickness']))
    rear_y=-o['y_min'];lower=hh+l['rim_bottom_height_from_axis'];bevel=l['rear_lower_bevel']
    cut=cq.Workplane('YZ').polyline([(rear_y+.1,lower-.1),(rear_y-bevel-.1,lower-.1),
                                    (rear_y+.1,lower+bevel+.1)]).close().extrude(width+2).val().translate((o['x_min']-1,0,0))
    rim=rim.cut(cut)
    add('lid-skin',skin,'lid',True);add('lid-rim',rim,'lid',True)
    ph=hh+l['panel_back_height_from_axis']-l['panel_thickness']
    panel=box(l['panel_x'],l['panel_y'],ph,l['panel_width'],l['panel_depth'],l['panel_thickness'])
    add('display-panel-reservation',panel,'panel',True)
    bezel=rounded_slab(ph-.8,.8)
    bezel=bezel.cut(box(l['panel_x']+2,l['panel_y']+2,ph-1,l['panel_width']-4,l['panel_depth']-4,2))
    # The rear band below the panel follows the OEM leaves instead of filling
    # their sweep with a flat decorative sheet.
    bezel=bezel.cut(box(o['x_min']-1,hy-4,ph-1,width+2,31,2))
    add('bezel',bezel,'lid',True)
    co=C['cooling'];fh=co['fan_bottom_H']
    if C.get('cooling_layout'):
        parts.extend(remote_cooler.make_parts(C))
    else:
        add('fan-body-reservation',cylinder(cx,cy,fh,rr,co['fan_height_with_allowance']),'cooling')
        add('fan-intake-space',cylinder(cx,cy,fh+co['fan_height_with_allowance'],rr,co['fan_inlet_height']),'keepout')
        add('fin-reservation',box(fx,fy,fh,fw,fd,co['fins_height']),'cooling')
        add('CPU-cooler-height-budget',box(193,30,co['CPU_contact_top_H'],33,31,co['CPU_cooling_height_budget']),'cooling')
        add('proposed-fan-cutout',cylinder(cx,cy,3.9,co['board_pocket_radius'],1.6),'changes')
    if C.get('fan_harness'):parts.extend(fan_harness.make_parts())
    if C.get('lid_stops'):
        import lid_stops
        parts,stop_changes=lid_stops.adapt_case(parts,C)
        mount_rows.extend({'lid_stop_change':row} for row in stop_changes)
    assert before==inputs(),'source files changed during build'
    CACHE.mkdir(parents=True,exist_ok=True);rows=[]
    for i,p in enumerate(parts):
        file=f'{i:04d}.brep';p['shape'].exportBrep(str(CACHE/file))
        rows.append({k:v for k,v in {**p,'brep':file}.items() if k not in ['shape','_mesh_source']})
    (CACHE/'model.json').write_text(json.dumps({'parts':rows,'source_hashes':before,'hinge_supports':mount_rows},indent=2)+'\n')
    return parts,before,mount_rows


def load_model():
    d=json.loads((CACHE/'model.json').read_text());assert d['source_hashes']==inputs(),'candidate cache stale'
    parts=[{**{k:v for k,v in p.items() if k!='brep'},'shape':cq.Shape.importBrep(str(CACHE/p['brep']))} for p in d['parts']]
    if C.get('cooling_layout'):
        import remote_cooler
        remote_cooler.register_shapes(parts)
    return parts,d['source_hashes'],d['hinge_supports']


def check(parts,before,mounts):
    fixed=[p for p in parts if not p.get('moving') and p['group'] not in ['keepout','changes']]
    moving=[p for p in parts if p.get('moving')]
    sweep=[]
    import lid_stops
    opening_samples=lid_stops.angles(C)
    for angle in opening_samples:
        hits=[]
        for p in moving:
            s=pose(p,angle)['shape']
            for q in fixed:
                if p.get('OEM') and q.get('OEM'):continue
                if not bbox_overlap(s,q['shape']):continue
                v=intersection_volume(s,q['shape'])
                if v>.01:hits.append({'moving':p['name'],'fixed':q['name'],'overlap_mm3':round(v,4)})
        if hits:sweep.append({'angle_deg':angle,'hits':hits})
        if angle%20==0:print(f'hinge sweep {angle} degrees: {len(hits)} overlaps',flush=True)
    internals=[]
    obstacles=[p for p in fixed if p['group'] in ['boards','wiring','cells','inputs']]
    candidates=[p for p in fixed if p['group'] in ['shell','deck','supports','cooling']]
    for p in candidates:
        if p.get('remote_cooler'):continue # Dedicated size, cable and height checks below.
        for q in obstacles:
            if C.get('usb_power_route') and q['name'].startswith(('usb5-','harness-USB-')):continue
            if not bbox_overlap(p['shape'],q['shape']):continue
            if p['name']=='base-floor' and q['name']=='fan-loom-envelope':
                from fan_harness_checks import floor_cable_overlap
                v=floor_cable_overlap(p['shape'],q['shape'])
            else:v=intersection_volume(p['shape'],q['shape'])
            if v>.01:internals.append({'new':p['name'],'existing':q['name'],'overlap_mm3':round(v,4)})
    usb_checks=None
    if C.get('usb_power_route'):
        import usb_clearances
        usb_checks=usb_clearances.check(parts,C)
    cooler_checks=None
    if C.get('cooling_layout'):
        import check_cooler
        cooler_checks=check_cooler.evaluate(parts,C,before.copy(),draw=False)
    feet_checks=None;fan_checks=None
    if C.get('feet'):
        import case_feet
        feet_checks=case_feet.check(parts,C)
    if C.get('fan_harness'):
        import fan_harness_checks
        fan_checks=fan_harness_checks.check(parts,C,before.copy())
    import lid_stop_checks
    stop_checks=lid_stop_checks.evaluate(parts,C,before.copy())
    h=C['hinges'];o=C['outline'];l=C['lid']
    # This geometric check detects a fixed rear platform behind the open lid's
    # back plane, rather than assuming that equal closed outlines are sufficient.
    no_shelf=[]
    for angle in [90,105,120,135]:
        skin=pose(next(p for p in parts if p['name']=='lid-skin'),angle)['shape']
        # Intersect a thin horizontal slab at deck level. If the lid is entirely
        # above it, use the projected rear heel at its lowest edge instead.
        slab=box(-20,-400,C['base']['deck_top']-.05,410,800,.1)
        cut=skin.intersect(slab)
        rear_at_deck=-cut.BoundingBox().ymin if cut.Volume()>.0001 else None
        no_shelf.append({'angle_deg':angle,'lid_skin_frontmost_Y_at_deck_H':rear_at_deck,
                         'base_rear_Y':o['y_min'],'fixed_rear_projection_mm':None if rear_at_deck is None else max(0,rear_at_deck-o['y_min'])})
    perimeter=[]
    for p in parts:
        if p['group'] in ['keepout','changes']:continue
        bb=p['shape'].BoundingBox()
        excess={'left':max(0,o['x_min']-bb.xmin),'right':max(0,bb.xmax-o['x_max']),
                'rear':max(0,o['y_min']+bb.ymax),'front':max(0,-bb.ymin-o['y_max'])}
        if max(excess.values())>.02:
            perimeter.append({'part':p['name'],'group':p['group'],'excess_mm':excess})
    shell=[p for p in parts if p['name'] in ['base-floor','lid-skin']]
    measured={p['name']:[bounds(p['shape'])[i] for i in [0,1,3,4]] for p in shell}
    assert measured['base-floor']==measured['lid-skin'],'actual closed shell outlines differ'
    assert not [p for p in perimeter if p['group'] in ['shell','lid','deck','supports','hinges']]
    rim=next(p for p in moving if p['name']=='lid-rim')
    walls=next(p for p in fixed if p['name']=='base-walls')
    rim_gaps={str(a):round(pose(rim,a)['shape'].distance(walls['shape']),5) for a in [135,140]}
    result={'date':C['date'],'source_hashes':before,'configuration':C,
            'closed_outline_mm':{'base':[o['x_min'],o['y_min'],o['x_max'],o['y_max']],
                                 'lid':[o['x_min'],o['y_min'],o['x_max'],o['y_max']],
                                 'mismatch_mm':0,'width':o['x_max']-o['x_min'],'depth':o['y_max']-o['y_min']},
            'measured_shell_XY_bounds_construction_frame':measured,
            'other_parts_outside_nominal_outline':perimeter,
            'lid_rim_to_base_wall_nominal_gap_mm':rim_gaps,
            'closed_height_without_feet_mm':h['pivot_height']+l['back_inner_height_from_axis']+l['skin'],
            'feet_checks':feet_checks,'fan_harness_checks':fan_checks,'lid_stop_checks':stop_checks,
            'nominal_closed_height_with_feet_mm':feet_checks['nominal_closed_height_with_feet_mm'] if feet_checks else None,
            'screen_to_key_nominal_gap_mm':h['pivot_height']+l['panel_back_height_from_axis']-l['panel_thickness']-(C['boards']['keyboard_bottom_H']+.8+4.5),
            'hinge_sweep':{'sample_range_deg':[0,C['hinges']['requested_opening_deg']],'sample_angles_deg':opening_samples,'step_deg':C['hinges']['check_step_deg'],'collisions':sweep,
                           'last_clear_sample_before_first_collision_deg':max([a for a in opening_samples if a<sweep[0]['angle_deg']],default=None) if sweep else opening_samples[-1],
                           'scope':'new rigid shell, panel reservation and actual OEM hinge parts versus retained PCB models, power harness and candidate supports; OEM internal bearing contact excluded'},
            'rear_projection_screen':no_shelf,'internal_interferences':internals,'hinge_supports':mounts,
            'USB_harness_checks':usb_checks,'cooler_checks':cooler_checks,
            'radio_internal':False,'PCB_files_unchanged':before==inputs(),'complete_fit_verified':False,
            'thermal_performance_verified':False,'structural_load_verified':False,'manufacturing_ready':False,
            'limitations':C['notes']}
    result['nominal_opening_geometry_pass']=not sweep and not internals and stop_checks['stop_geometry_pass']
    (HERE/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print('internal interference pairs',len(internals),flush=True)
    return result


def views(parts):
    out=HERE/'views';out.mkdir(exist_ok=True)
    visible=[p for p in parts if p['group'] not in ['keepout','changes']]
    render(visible,out/'closed.png','flush clamshell candidate / 370 x 274 mm / internal fit unfinished',direction=(1,-1.6,.75),size=(1750,1100))
    render([pose(p,105) for p in visible],out/'open.png','external radio / same lid and base outline / 105 degrees',direction=(1,-1.8,1.2),size=(1750,1200))
    inside=[p for p in parts if not p['moving'] and p['group'] not in ['shell','deck','inputs','keepout'] and not p['name'].startswith(('keyboard','trackpad'))]
    render(inside,out/'inside.png','right-side cooler and retained boards / no board cutout / radio external',direction=(.1,-.25,1.6),size=(1700,1150))
    section=[];clip=box(1,-30,0,65,62,50)
    for p in visible:
        if bbox_overlap(p['shape'],clip):
            s=p['shape'].intersect(clip)
            if s.Volume()>.001:section.append({**p,'shape':s})
    render(section,out/'hinge-detail.png','left Framework hinge / new rear position and supports',direction=(1,.8,.9),size=(1550,1100))
    import lid_stop_checks
    lid_stop_checks.draw(parts)
    fig,axs=plt.subplots(1,2,figsize=(14,6),facecolor='#faf9f5')
    for ax,title,base_y,lid_y in [(axs[0],'saved case',-26,-18),(axs[1],'flush candidate',-18,-18)]:
        ax.add_patch(Rectangle((-6,base_y),370,256-base_y,fc='#809795',alpha=.45,ec='#244c46',lw=2))
        ax.add_patch(Rectangle((-6,lid_y),370,256-lid_y,fill=False,ec='#313d5d',ls='--',lw=2.5))
        ax.axhline(256,color='#333333',lw=.8);ax.text(179,249,'front edge stays here',ha='center',fontsize=10)
        ax.set(xlim=(-22,380),ylim=(269,-43),aspect='equal',title=title,xlabel='X / mm',ylabel='Y / mm')
    axs[0].annotate('8 mm rear ledge',(175,-22),(130,42),arrowprops={'arrowstyle':'->'},color='#b74232',fontsize=12)
    axs[1].annotate('matching edges',(179,-18),(120,42),arrowprops={'arrowstyle':'->'},color='#245b4c',fontsize=12)
    fig.suptitle('remove the rear ledge by shortening the base',fontsize=18,fontweight='bold')
    fig.text(.075,.035,'Nominal shell outlines only. Corner fillets and hinge details are included in the CAD; internal fit is still being checked.',fontsize=10)
    fig.subplots_adjust(top=.85,bottom=.15,wspace=.16)
    fig.savefig(out/'outline-comparison.png',dpi=150);plt.close(fig)


def export(parts):
    out=HERE/'exports';out.mkdir(exist_ok=True)
    rows=[]
    for name,angle in [('closed',0),('open',105)]:
        assembly=cq.Assembly()
        for p in parts:
            if p['group'] in ['keepout','changes']:continue
            s=pose(p,angle)['shape'].rotate((0,0,0),(1,0,0),180)
            assembly.add(s,name=p['name'],color=cq.Color(*p['color'][:3]))
        path=out/(name+'.step');assembly.export(str(path),write_pcurves=False)
        reopened=cq.importers.importStep(str(path)).val()
        assert reopened.isValid()
        rows.append({'file':str(path.relative_to(HERE)),'sha256':sha(path),'solids':len(reopened.Solids()),'reopens':True})
    (HERE/'exports.json').write_text(json.dumps(rows,indent=2)+'\n')
    data=[]
    for p in parts:
        verts,triangles=mesh(p['shape'])
        data.append({'name':p['name'],'group':p['group'],'moving':p['moving'],'color':list(p['color']),
                     'v':[[round(v,4) for v in q.toTuple()] for q in verts],'f':[list(t) for t in triangles]})
    config=copy.deepcopy(C);config['selected_profile']='flush-external-radio'
    payload={'parts':data,'pivot':[0,-C['hinges']['pivot_y'],C['hinges']['pivot_height']],'findings':C['notes'],'configuration':config,'source_hashes':inputs()}
    template=(BASE/'viewer-template.html').read_text().replace('ducktop2 / case prototype','ducktop2 / flush case')
    template=template.replace('370 × 282 mm base','370 × 274 mm matching outlines').replace('Current power wires are shown, including unresolved clashes.','Right-side cooler and revised power guides; mounting and thermal tests remain unfinished.')
    maximum=C['hinges']['requested_opening_deg']
    template=template.replace('setAngle(180)','setAngle('+str(maximum)+')').replace('>180°</button>','>'+str(maximum)+'°</button>').replace('max="180"','max="'+str(maximum)+'"')
    template=template.replace('function setAngle(v){angle=v;', 'function setAngle(v){v=Math.max(0,Math.min('+str(maximum)+',v));angle=v;')
    (HERE/'inspection.html').write_text(template.replace('/*ASSEMBLY_DATA*/',json.dumps(payload,separators=(',',':'))))


def main():
    a=argparse.ArgumentParser();a.add_argument('--cached',action='store_true');a.add_argument('--skip-check',action='store_true');a.add_argument('--skip-export',action='store_true');args=a.parse_args()
    parts,before,mounts=load_model() if args.cached else fresh_model()
    if not args.skip_check:check(parts,before,mounts)
    views(parts)
    if not args.skip_export:export(parts)
    assert before==inputs()
    print('candidate saved; baseline and PCB inputs unchanged',flush=True)


if __name__=='__main__':main()

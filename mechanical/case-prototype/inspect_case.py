#!/usr/bin/env python3
"""Inspect the last staged BRep assembly; refuses changed config/inventory."""
import argparse
from cad import HERE,box,render
from model_cache import load
from deliver import posed,deliver


def views(m):
    from build import CONFIG
    out=HERE/'views';out.mkdir(exist_ok=True)
    visible=[p for p in m.parts if p['group'] not in ['keepout','routes']]
    # These are the same conservative height envelopes used by the checker,
    # not substitute manufacturer body models. Keep their color distinct.
    import json
    from case_inputs import path as input_path
    from cables import polygon_prism
    from build import pcb_top
    for row in json.loads(input_path('component-placement.json').read_text())['parts']:
        if row['board']=='center' and row['reference'] in ['C762','C797','C2610']:
            for ring in row['courtyards_installed_mm']['front']:
                visible.append({'name':row['reference']+'-height-envelope','shape':polygon_prism(ring['outer'],pcb_top('center'),row['height_mm']),
                                'color':(.95,.65,.15,.65),'group':'boards','moving':False})
    render([posed(p,105) for p in visible],out/'open.png',f"current boards / {CONFIG['base']['deck_top']} mm base candidate / 105 degrees",direction=(1,-1.7,1.1))
    render(visible,out/'closed.png','closed case study / prototype geometry',direction=(1,-1.5,1))
    harness=[p for p in visible if p.get('harness_part') or p.get('power_wire') or p.get('terminal') or p.get('harness_fastener') or p.get('braid')]
    render(harness,out/'harness-detail.png','18 routed wires / independent guides and strain relief',direction=(.1,-.65,1.5))
    # This close-up keeps the PCB, clamps and actual enlarged BMS notch visible.
    scene=[];clip=box(101,131,0,153,72,35)
    from review import bbox_overlap
    for p in visible:
        if p.get('moving') or p['group'] in ['deck','inputs'] or p['name']=='trackpad-bridge':continue
        if bbox_overlap(p['shape'],clip):
            scene.append(p)
    render(scene,out/'bms-guides.png','BMS power leads / current connectors and revised guides',direction=(.3,-.6,1.5),focus=((155,-156,12),54))
    scene=[];clip=box(289,45,0,39,25,20)
    for p in visible:
        if p.get('moving') or p['group'] in ['deck','inputs'] or p['name']=='trackpad-bridge':continue
        if bbox_overlap(p['shape'],clip):scene.append(p)
    row=next(p for p in json.loads(input_path('component-placement.json').read_text())['parts']
             if p['board']=='right' and p['reference']=='R2045')
    for ring in row['courtyards_installed_mm']['front']:
        scene.append({'shape':polygon_prism(ring['outer'],pcb_top('right'),row['height_mm']+.3),
                      'color':(.95,.65,.15,.8),'group':'boards','moving':False})
    render(scene,out/'right-power-guide.png','shortened PD2 guide / amber = R2045 height and assembly space',
           direction=(.5,-.8,1.2),focus=((304,-56,8.5),12),size=(1500,1000))
    cooling_views(m)
    internal=[p for p in visible if not p.get('moving') and p['group'] not in ['deck','inputs'] and not p['name'].startswith('keyboard-')]
    render(internal,out/'inside.png','current PCB geometry / harness carriers anchored outside the cells',direction=(.15,-.8,1.7))
    for label,x in [('cooling',132.45),('compute-keyboard',205),('trackpad-battery',179),('power-loom',166)]:
        cut=box(x-.5,-50,-8,1,360,100);scene=[]
        for p in visible:
            if bbox_overlap(cut,p['shape']):
                for solid in p['shape'].Solids():
                    if not bbox_overlap(cut,solid):continue
                    s=solid.intersect(cut)
                    if s.Volume()>.0001:scene.append({'shape':s,'color':p['color']})
        render(scene,out/(label+'-section.png'),f'CAD section X={x} / {label} / amber = component-height envelopes',direction=(1,0,.001),size=(1500,850))
    render([posed(p,90,True) for p in visible],out/'exploded.png','exploded / separate manufactured parts and supports',direction=(1,-1.8,.8))


def cooling_views(m):
    out=HERE/'views';out.mkdir(exist_ok=True)
    cooling=[]
    for p in m.parts:
        if p['group']=='cooling' or p['name'].startswith(('blower-','fan-through')):
            q=dict(p)
            if 'blower-reservation' in p['name']:q['color']=(.24,.27,.30)
            if 'fins-reservation' in p['name']:q['color']=(.67,.71,.74)
            if 'heatpipe-reservation' in p['name']:q['color']=(.87,.49,.23)
            cooling.append(q)
    for name in ['left','center']:
        cooling.append({'shape':m.board_material[name],'color':(.13,.43,.31),'group':'boards','moving':False})
    render(cooling,out/'cooling-layout.png','cooling fit study / wider fins and stepped CPU/memory spreader',
           direction=(.25,-.65,1.5),focus=((146,-41,16),75),size=(1600,1050))
    plate=next(p for p in m.parts if p['name']=='cooling-cold_plate-reservation')
    render([plate],out/'cooling-spreader.png','spreader underside / CPU and memory contact study',
           direction=(.4,-.6,-1),size=(1300,950))


def cooling_clearance_views(m):
    import json
    from case_inputs import path as input_path
    from component_heights import resolve
    from cables import polygon_prism
    from build import pcb_top
    from review import bbox_overlap
    out=HERE/'views';out.mkdir(exist_ok=True)
    settings=json.loads((HERE/'height-allowances.json').read_text())
    parts=json.loads(input_path('component-placement.json').read_text())['parts']
    report=json.loads((HERE/'cooling-checks.json').read_text())
    for slug,key,near,clip,direction in [
        ('cooling-j53-clearance','center/J53','cooling-fins-reservation',
         box(79,12,5,12,15,20),(.7,-1,.5)),
        ('cooling-sw3-clearance','center/SW3','fan-through-screw-3',
         box(113,91,5,16,16,25),(.8,-1,.35))]:
        scene=[]
        targets=[p for p in m.parts if p['group']=='cooling' or p['name'].startswith(('blower-','fan-through'))]
        for p in targets:
            if not bbox_overlap(p['shape'],clip):continue
            shape=p['shape'].intersect(clip)
            if shape.Volume()>.001:scene.append({'shape':shape,'color':(.58,.63,.67,.65)})
        for board in ['left','center']:
            shape=m.board_material[board].intersect(clip)
            if shape.Volume()>.001:scene.append({'shape':shape,'color':(.13,.43,.31)})
        for p in parts:
            if p['side']!='front' or p['dnp']:continue
            limit=resolve(p,settings)
            if limit is None:continue
            for ring in p['courtyards_installed_mm']['front']:
                shape=polygon_prism(ring['outer'],pcb_top(p['board']),limit['height_mm'])
                if not bbox_overlap(shape,clip):continue
                shape=shape.intersect(clip)
                if shape.Volume()<.001:continue
                color=(.96,.59,.10) if p['board']+'/'+p['reference']==key else (.15,.65,.57,.65)
                scene.append({'shape':shape,'color':color})
        row=next(r for r in report['component_height_crossings'] if r['part']==key and r['near']==near)
        title=f"{key.split('/')[1]} / amber = height + assembly space / remaining gap {row['planning_gap_mm']:.2f} mm"
        render(scene,out/(slug+'.png'),title,direction=direction,size=(1500,1050))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--views',action='store_true');p.add_argument('--checks',action='store_true');p.add_argument('--export',action='store_true');p.add_argument('--cooling-views',action='store_true');p.add_argument('--cooling-clearances',action='store_true');a=p.parse_args()
    m=load();print('staged assembly loaded',flush=True)
    if a.checks:
        from review import review
        review(m)
    if a.export:
        import json,hashlib
        record=json.loads((HERE/'assembly-checks.json').read_text())
        assert record.get('config_sha256')==hashlib.sha256((HERE/'assembly.json').read_bytes()).hexdigest(),'run current checks before exporting'
        height_checks=json.loads((HERE/'harness-case-checks.json').read_text())
        for name,digest in height_checks['height_check_sources_sha256'].items():
            assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,'height assumptions changed: rerun checks before exporting'
        thermal=json.loads((HERE/'cooling-checks.json').read_text())
        for name,digest in thermal['source_sha256'].items():
            assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,'cooling inputs changed: rerun checks before exporting'
        for key in ['cooling_body_collisions','internal_cooling_collisions','inlet_obstructions','known_component_height_conflicts']:
            assert not thermal[key], 'resolve '+key+' before exporting'
        assert not record['checks']['case_sweep']['collisions'],'resolve lid sweep conflicts before exporting'
        m.findings=list(dict.fromkeys(record['limitations']))
        deliver(m,render_views=False,checked=True)
    if a.views:views(m)
    if a.cooling_views:cooling_views(m)
    if a.cooling_clearances:cooling_clearance_views(m)

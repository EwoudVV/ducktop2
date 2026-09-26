"""Export CAD, part schedules, views and a self-contained inspection viewer."""
import csv
import json
import math
import cadquery as cq
from cad import HERE, box, compound, bounds, export_step, export_stl, render, mesh


def posed(part,angle=0,exploded=False):
    from build import CONFIG
    shape=part['shape'];h=CONFIG['hinges'];pivot=(0,-h['pivot_y'],h['pivot_height'])
    dz=0
    if part.get('moving'):shape=shape.rotate(pivot,(1,pivot[1],pivot[2]),-angle)
    if exploded:
        dz={'boards':18,'cells':12,'inputs':55,'deck':70,'supports':35,'cooling':45,'cables':0,'hardware':15}.get(part['group'],0)
        if part.get('moving'):dz=100
        shape=shape.translate((0,0,dz))
    return {**part,'shape':shape,'_mesh_source':part['shape'],'_mesh_angle':angle if part.get('moving') else 0,'_mesh_pivot':pivot,'_mesh_lift':dz}


def assembly_step(parts,path):
    assy=cq.Assembly(name='ducktop2_case_prototype')
    for p in parts:
        if p['group']=='keepout':continue
        col=p.get('color',(.4,.4,.4))
        shape=p['shape'].rotate((0,0,0),(1,0,0),180)
        assy.add(shape,name=p['name'],color=cq.Color(*col[:3]))
    assy.export(str(path))


def deliver(m,render_views=True):
    from build import CONFIG, INVENTORY
    # Resolve the final suspension stack in the schedule before writing it.
    # The bolts are not used as solid manufacturing geometry.
    carrier_bottom=CONFIG['boards']['keyboard']['bottom_height']-4.5
    fan_bottom=CONFIG['cooling']['blower'][2]
    for row in m.mounts:
        if row['reference'].startswith('cooling-cradle-'):
            row['fastener_length_mm']=round(carrier_bottom-fan_bottom+5.5,1)
            row['status']='low-profile head, 1.5 mm nut engagement; trim to length to clear SW3; thermal test pending'
    out=HERE/'exports';out.mkdir(exist_ok=True);parts_dir=out/'parts';parts_dir.mkdir(exist_ok=True)
    views=HERE/'views';views.mkdir(exist_ok=True)
    catalog=[]
    for p in m.parts:
        shape=p['shape'];row={k:v for k,v in p.items() if k not in ['shape','color']}
        row['bounds_view_frame']=bounds(shape);row['volume_mm3']=round(shape.Volume(),3);row['solids']=len(shape.Solids())
        if p.get('manufactured'):
            export_step(shape,parts_dir/(p['name']+'.step'))
            bb=shape.BoundingBox();size=sorted([bb.xlen,bb.ylen,bb.zlen],reverse=True)
            row['fits_P1S_with_6mm_margin']=max(size)<=244
            if row['fits_P1S_with_6mm_margin']:
                export_stl(shape,parts_dir/(p['name']+'.stl'))
            else:
                # Fit-only fragments of continuous metal stock; no claimed
                # structural equivalence to the continuous reinforcement.
                xmid=(bb.xmin+bb.xmax)/2
                for i,cut in enumerate([box(bb.xmin-1,-bb.ymax-1,bb.zmin-1,xmid-bb.xmin+1,bb.ylen+2,bb.zlen+2),
                                        box(xmid,-bb.ymax-1,bb.zmin-1,bb.xmax-xmid+1,bb.ylen+2,bb.zlen+2)]):
                    s=shape.intersect(cut)
                    export_stl(s,parts_dir/(p['name']+f'-fit-only-{i+1}.stl'))
                row['print_note']='split STL fragments for fit only; install continuous metal part for hinge load tests'
        catalog.append(row)
    (HERE/'parts.json').write_text(json.dumps(catalog,indent=2)+'\n')
    keys=list(dict.fromkeys(k for row in m.mounts for k in row))
    with (HERE/'mounting-schedule.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(m.mounts)
    (HERE/'cable-checks.json').write_text(json.dumps(m.cable_records,indent=2)+'\n')
    (HERE/'open-findings.json').write_text(json.dumps(m.findings,indent=2)+'\n')
    print('manufactured parts and mounting schedule exported',flush=True)
    # Only a single large assembly STEP is stored; source/HTML supplies all poses.
    assembly_step([posed(p,CONFIG['hinges']['view_angle']) for p in m.parts],out/'ducktop2-assembly.step')
    print('named STEP assembly exported',flush=True)
    mesh_rows=[]
    for p in m.parts:
        verts,tris=mesh(p['shape'])
        mesh_rows.append({'name':p['name'],'group':p['group'],'moving':p.get('moving',False),
                     'color':list(p.get('color',(.4,.4,.4))),
                     'v':[[round(t,4) for t in q.toTuple()] for q in verts], 'f':[list(t) for t in tris]})
    payload={'parts':mesh_rows,'pivot':[0,-CONFIG['hinges']['pivot_y'],CONFIG['hinges']['pivot_height']],
             'findings':m.findings,'configuration':CONFIG}
    template=(HERE/'viewer-template.html').read_text()
    (HERE/'inspection.html').write_text(template.replace('/*ASSEMBLY_DATA*/',json.dumps(payload,separators=(',',':'))))
    print('interactive CAD viewer exported',flush=True)
    from review import review
    review(m)
    if render_views:
        openparts=[posed(p,105) for p in m.parts if p['group']!='keepout']
        render(openparts,views/'open.png','ducktop2 / current-hardware fit prototype / 105 degrees',direction=(1,-1.7,1.1))
        closed=[posed(p,0) for p in m.parts if p['group']!='keepout']
        render(closed,views/'closed.png','closed / current power loom height retained',direction=(1,-1.5,1.0))
        exploded=[posed(p,90,True) for p in m.parts if p['group']!='keepout']
        render(exploded,views/'exploded.png','exploded / separate case parts and supports',direction=(1,-1.8,.8))
        internal=[p for p in m.parts if not p.get('moving') and p['group'] not in ['deck','keepout'] and not p['name'].startswith(('keyboard-carrier','key-travel','trackpad-body'))]
        render(internal,views/'inside.png','base / preserved PCB geometry, supports and power wire arches',direction=(.15,-.8,1.7))
        # Thin sections are intersections of actual solids, not illustrative rectangles.
        sections=[('cooling',205,(1,0,0)),('trackpad-battery',179,(1,0,0)),('power-loom',78,(1,0,0))]
        for name,x,direction in sections:
            cut=box(x-.5,-50,-8,1,360,120)
            scene=[]
            for p in closed:
                bb=p['shape'].BoundingBox()
                if bb.xmin<=x+.5 and bb.xmax>=x-.5:
                    s=p['shape'].intersect(cut)
                    if s.Volume()>.0001:scene.append({'shape':s,'color':p['color']})
            if scene:render(scene,views/(name+'-section.png'),f'X={x} mm / {name} section / actual CAD',direction=(1,0,.001),size=(1500,850))
        print('open, closed, exploded, internal and section views rendered',flush=True)

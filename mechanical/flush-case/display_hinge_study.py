"""Inspect a partial display route and hinge-axis strain-relief concept."""
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np
import check_cooler
import usb_harness
from cad import box, compound, bounds, export_step, _MESHES
from cables import tube
from component_heights import screen_routes, resolve
from review import bbox_overlap
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def config():return json.loads((HERE/'display-hinge-study.json').read_text())


def route_points():
    c=config();p=[]
    def line(a,b):
        v=np.linspace(a,b,max(2,math.ceil(np.linalg.norm(np.array(b)-a)/.2)+1))
        p.extend(v[1:] if p else v)
    def arc(x,y,r,a,b,h):
        t=np.linspace(a,b,math.ceil(abs(b-a)*r/.2)+1)
        v=np.c_[x+r*np.cos(t),y+r*np.sin(t),np.full(len(t),h)]
        p.extend(v[1:] if p else v)
    line(c['fanout_start_xyH'],c['fanout_end_xyH'])
    arc(258,48.54,10,math.pi/2,0,13.3)
    first=len(p)-1;radius=14;angle=math.acos(1-24.5/(2*radius))
    for t in np.linspace(0,angle,105)[1:]:
        p.append([268-radius*(1-math.cos(t)),48.54-radius*math.sin(t),13.3])
    x,y,h=p[-1]
    for t in np.linspace(angle,0,105)[1:]:
        p.append([x-radius*(math.cos(t)-math.cos(angle)),y-radius*(math.sin(angle)-math.sin(t)),h])
    line(p[-1],[243.5,-5,13.3])
    raised=np.asarray(p[first:],dtype=float)
    stations=np.r_[0,np.cumsum(np.linalg.norm(np.diff(raised,axis=0),axis=1))]
    u=stations/stations[-1];raised[:,2]+=6*u*u*(3-2*u)
    p[first:]=raised.tolist()
    arc(233.5,-5,10,0,-math.pi/2,19.3)
    line(p[-1],c['fixed_anchor_xyH'])
    return np.array(p)


def lid_tail():
    # Two opposite circular arcs raise the lid-side tail 8 mm while
    # preserving its axial tangent at both ends. This ends before the panel.
    c=config();start=c['lid_anchor_xyH_closed'][0];bend=start-c['lid_tail_straight_before_bend_mm']
    radius=20;angle=math.acos(.8);p=np.linspace([start,-15,19.3],[bend,-15,19.3],41).tolist()
    for t in np.linspace(0,angle,70)[1:]:
        p.append([bend-radius*math.sin(t),-15,19.3+radius*(1-math.cos(t))])
    x,y,h=p[-1]
    for t in np.linspace(angle,0,70)[1:]:
        p.append([x-radius*(math.sin(angle)-math.sin(t)),y,h+radius*(math.cos(t)-math.cos(angle))])
    return np.array(p)


def anchor(x,moving):
    # These split shapes reserve a broad lined grip. Screw and insert
    # details depend on the actual loom and its permitted compression.
    bore=cq.Solid.makeCylinder(config()['grip_bore_diameter_mm']/2,12.2,cq.Vector(x-6.1,15,19.3),cq.Vector(1,0,0))
    if moving:
        saddle=box(x-6,-17.5,19.3,12,12,2.6).cut(bore)
        saddle=saddle.fuse(box(x-6,-11.5,21.9,12,6,5.9),box(x-9,-12,27.8,18,12,1.5))
        cap=box(x-6,-17.5,16.4,12,12,2.9).cut(bore)
    else:
        saddle=box(x-6,-17.5,16.7,12,12,2.6).cut(bore)
        saddle=saddle.fuse(box(x-6,-11.5,4.2,12,6,12.5))
        cap=box(x-6,-17.5,19.3,12,12,2.9).cut(bore)
    role='lid' if moving else 'base'
    # Open the back of the lined grip rather than thinning the whole case
    # wall around it. The opening is narrower than the nominal 3 mm loom.
    rear=box(x-7,-30,0,14,13.5,34)
    saddle=saddle.cut(rear);cap=cap.cut(rear)
    return [{'name':f'display-{role}-anchor-saddle','shape':saddle,'moving':moving,'color':(.17,.51,.65)},
            {'name':f'display-{role}-anchor-cap','shape':cap,'moving':moving,'color':(.33,.68,.77)}]


def geometry():
    c=config();p=route_points();r=c['maximum_dressed_bundle_diameter_mm']/2+c['position_allowance_mm']
    assert abs(r-1.8)<1e-9,'resize the grip and fanout after changing the cable envelope'
    assert c['fanout_start_xyH']==[245.9,58.54,13.3] and c['fanout_end_xyH']==[258,58.54,13.3]
    assert c['fanout_start_width_mm']==28.6,'redraw the tapered fanout for its new width'
    ax=c['fixed_anchor_xyH'][0];bx=c['lid_anchor_xyH_closed'][0]
    start=np.argmin(np.linalg.norm(p-np.array(c['fanout_end_xyH']),axis=1));roundp=p[start:]
    model_points=np.vstack([roundp[::2],roundp[-1:]])
    model_points=model_points[np.r_[True,np.linalg.norm(np.diff(model_points,axis=0),axis=1)>1e-8]]
    fanout=cq.Workplane('XY').polyline([(245.9,-44.24),(245.9,-72.84),(258,-60.34),(258,-56.74)]).close().extrude(3.6).val().translate((0,0,11.5))
    span=cq.Solid.makeCylinder(r,ax-bx,cq.Vector(bx,15,19.3),cq.Vector(1,0,0))
    new=[{'name':'display-flat-fanout-space','shape':fanout,'moving':False,'color':(.95,.45,.12)},
         {'name':'display-base-bundle-space','shape':tube(model_points,r),'moving':False,'color':(.95,.45,.12)},
         {'name':'display-axis-flex-space','shape':span,'moving':False,'color':(.65,.28,.7)},
         {'name':'display-lid-tail-space','shape':tube(lid_tail(),r),'moving':True,'color':(.95,.45,.12)}]
    new+=anchor(ax,False)+anchor(bx,True)
    assert all(n['shape'].isValid() for n in new)
    return new,p


def pose(p,angle):
    if not p.get('moving'):return p
    return {**p,'shape':p['shape'].rotate((0,15,19.3),(1,15,19.3),-angle)}


def overlap(a,b):
    if not bbox_overlap(a,b):return 0.0,[]
    total=0;where=[]
    for solid in b.Solids():
        if not bbox_overlap(a,solid):continue
        hit=a.intersect(solid)
        volume=hit.Volume() if hit.Solids() else 0.0
        assert math.isfinite(volume) and volume>=-.01
        total+=max(0,volume)
        if volume>.01:where.append(bounds(hit))
    return total,where


def study_case_parts(parts):
    """Apply explicit rear reliefs to a local copy of the case geometry."""
    cuts={
        'deck':[box(130,-19,23.5,43,14.5,1.8)],
        'base-walls':[
            box(135,-18.1,12.25,38,1.5,12),
            box(161,-17.0,17.2,75,0.3,4.2),
        ],
    }
    result=[];records=[]
    for p in parts:
        if p['name'] not in cuts:
            result.append(p);continue
        shape=p['shape']
        # Overlapping tools in one compound can leave the input material
        # unchanged in this geometry. Keep the Boolean subtractions separate.
        for cut in cuts[p['name']]:shape=shape.cut(cut)
        assert shape.isValid() and shape.Solids()
        records.append({'part':p['name'],'removed_volume_mm3':round(p['shape'].Volume()-shape.Volume(),4),
                        'cut_bounds_construction_xyz':[bounds(cut) for cut in cuts[p['name']]]})
        result.append({**p,'shape':shape})
    return result,records


def height_screen(points):
    table,settings=usb_harness.height_inputs()
    for filename in ['cooler-part-heights.json','fan-harness-heights.json','display-part-heights.json']:
        extra=json.loads((HERE/filename).read_text());settings['reservations'].update(extra.get('reservations',{}))
        for p in table:
            if p.get('mpn') in extra.get('manufacturer_maximums',{}):
                h=extra['manufacturer_maximums'][p['mpn']]
                p.update(height_mm=h['height_mm'],height_kind='maximum',height_status='verified_maximum',
                         height_source_url=h['source'],height_basis=h['basis'])
    settings.update(sampling_step_mm=.2,wire_position_allowance_mm=.3,guide_curve_allowance_mm=.05)
    part={'name':'display-base-bundle','points':points.tolist(),'wire_od_mm':3,'ends':[{'board':'center','ref':'A1'}]}
    out=screen_routes([part],table,{'left':5.5,'center':5.5,'right':5.5},{'guide_radial_clearance':0,'guide_wall':0},settings)
    fanout=Polygon([(245.9,44.24),(245.9,72.84),(258,60.34),(258,56.74)])
    extra=[]
    for p in table:
        if p['dnp'] or p['side']!='front' or (p['board']=='center' and p['reference']=='A1'):continue
        rings=p['courtyards_installed_mm']['front']
        if not rings:continue
        a=unary_union([Polygon(r['outer'],r['holes']) for r in rings])
        if a.intersection(fanout).area<1e-6:continue
        height=resolve(p,settings)
        extra.append({'part':p['board']+'/'+p['reference'],'available_height_mm':6,
                      'height':height,'gap_mm':None if height is None else 6-height['height_mm']})
    out['flat_fanout_crossings']=extra
    return out


def main():
    saved,case,sources=check_cooler.load_case();c=config()
    case_sources=sources.copy()
    original,case_changes=study_case_parts(saved)
    assert sha(ROOT/'ducktop2-center.kicad_pcb')==c['source_center_PCB_sha256']
    assert case['hinges']['pivot_y']==-15 and case['hinges']['pivot_height']==19.3
    assert case['boards']['main_bottom_H']==3.9
    for path in [Path(__file__),HERE/'display-hinge-study.json',HERE/'display-part-heights.json',HERE/'draw_cooler.py',
                 ROOT/'reference/lattepanda/mu-ultra-edp-pinout.json']:
        sources[str(path.relative_to(ROOT))]=sha(path)
    new,p=geometry();fixed=[];sweep=[];internal=[]
    physical=[q for q in original if not q.get('service') and q['group'] not in ['keepout','changes']]
    for n in [q for q in new if not q.get('moving')]:
        print('static check',n['name'],flush=True)
        for q in [v for v in physical if not v.get('moving')]:
            v,where=overlap(n['shape'],q['shape'])
            if v>.01:fixed.append({'new':n['name'],'part':q['name'],'overlap_mm3':round(v,4),'where':where})
    maximum=c['opening_study_degrees'][1]
    assert maximum==case['hinges']['requested_opening_deg']
    samples=sorted(set(range(0,maximum+1,c['opening_step_degrees']))|{maximum})
    for angle in samples:
        for n in new:
            pn=pose(n,angle)
            for q in physical:
                if not n.get('moving') and not q.get('moving'):continue
                pq=pose(q,angle)
                v,where=overlap(pn['shape'],pq['shape'])
                if v>.01:sweep.append({'angle':angle,'new':n['name'],'part':q['name'],'overlap_mm3':round(v,4),'where':where})
        for i,n in enumerate(new):
            for q in new[i+1:]:
                if n['name'].endswith('-space') and q['name'].endswith('-space'):continue
                if angle and n.get('moving',False)==q.get('moving',False):continue
                # The axis-aligned circular envelope is itself unchanged by
                # the lid rotation. Its relative grip fit is checked at zero.
                if angle and 'display-axis-flex-space' in [n['name'],q['name']]:continue
                v,where=overlap(pose(n,angle)['shape'],pose(q,angle)['shape'])
                if v>.01:internal.append({'angle':angle,'new':n['name'],'part':q['name'],'overlap_mm3':round(v,4),'where':where})
        if angle%20==0:print('opening',angle,flush=True)
    heights=height_screen(p)
    lengths=np.linalg.norm(np.diff(p,axis=0),axis=1)
    stations=np.r_[0,np.cumsum(lengths)]
    tangent=np.gradient(p,stations,axis=0);second=np.gradient(tangent,stations,axis=0)
    curvature=np.linalg.norm(np.cross(tangent,second),axis=1)/np.linalg.norm(tangent,axis=1)**3
    sampled_radius=1/float(curvature.max())
    angle=math.radians(maximum);r=c['maximum_dressed_bundle_diameter_mm']/2;length=c['axial_free_span_mm']
    pitch=c['fixed_anchor_xyH'][0]-c['lid_anchor_xyH_closed'][0]
    assert abs(pitch-c['anchor_grip_length_mm']-length)<1e-9,'free flex length excludes both half-grips'
    report={'date':c['date'],'source_hashes':sources,'configuration':c,
            'static_solid_conflicts':fixed,'opening_solid_conflicts':sweep,'internal_solid_conflicts':internal,'height_screen':heights,
            'internal_check_scope':'Common-frame pairs and pairs with the rotation-invariant axis cylinder are checked once. Other moving-versus-fixed pairs use the full opening sample range. Adjacent volumes representing the same continuous cable are not treated as independent physical parts.',
            'base_centerline_length_mm':round(float(lengths.sum()),3),
            'sampled_minimum_base_centerline_radius_mm':round(sampled_radius,3),
            'sampled_minimum_base_inside_radius_mm':round(sampled_radius-r,3),
            'axial_centerline_length_mm':pitch,'unclamped_axial_length_mm':length,'relative_end_rotation_degrees':maximum,'opening_sample_angles_deg':samples,
            'average_rotation_per_length_degrees_per_mm':maximum/length,
            'outer_helix_geometric_extra_length_mm':math.sqrt(length*length+(r*angle)**2)-length,
            'helix_note':'Illustrative outer path at 1.5 mm radius with uniformly distributed twist. This is not a material strain or fatigue prediction; actual wire lay, sliding, slack and strain concentration are unknown.',
            'proposed_case_reliefs':case_changes,'saved_full_case_changed':False,
            'proposed_geometry_solid_clear':not fixed and not sweep and not internal,
            'component_height_screen_clear':not heights['unverified_height_limits'] and not heights['known_height_clearance_conflicts'] and all(v['height'] is not None and v['gap_mm']>=0 for v in heights['flat_fanout_crossings']),
            'full_harness_length_mm':None,'physical_fit_verified':False,'manufacturing_ready':False}
    out=HERE/'display-hinge-checks.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print('static conflicts',len(fixed),'opening conflicts',len(sweep),'internal conflicts',len(internal),flush=True)
    # The existing viewer provides meshes from the same checked source set.
    raw=(HERE/'inspection.html').read_text();data,_=json.JSONDecoder().raw_decode(raw.split('const DATA=',1)[1])
    assert data['source_hashes']==case_sources,'rebuild the case viewer before drawing the cable study'
    meshes={v['name']:v for v in data['parts']}
    for q in saved:
        m=meshes[q['name']];_MESHES[id(q['shape'])]=(q['shape'],([cq.Vector(*v) for v in m['v']],m['f']))
    from draw_cooler import render
    nearby=[q for q in original if not q.get('moving') and q['group'] in ['boards','cooling','wiring','supports'] and not q['name'].startswith('keyboard')]
    render(nearby+new,HERE/'views/display-base-route.png','display cable space / proposed anchors / panel end unconfirmed',(.1,-.3,1.5),(1550,1050),focus=((233,-30,15),69))
    crop=box(129,-18,0,109,36,34);context=[]
    for q in physical:
        if q.get('moving') or q['name'] in ['base-floor','base-walls','deck']:
            if not bbox_overlap(q['shape'],crop):continue
            s=q['shape'].intersect(crop)
            if s.Solids():context.append({**q,'shape':s,'color':(*q['color'][:3],.22)})
    for angle in [0,105,maximum]:
        scene=[pose(q,angle) for q in context]+[pose(q,angle) for q in new[2:]]
        render(scene,HERE/f'views/display-hinge-{angle}.png',f'hinge-axis cable study at {angle} degrees / proposed rear reliefs / 50 mm free span',(.45,-1,.8),(1550,1050))
    dest=HERE/'exports/display-hinge-study.step'
    export_step(compound(q['shape'] for q in new+context),dest)
    reopened=cq.importers.importStep(str(dest)).val();assert reopened.isValid()
    outputs=['views/display-base-route.png',*[f'views/display-hinge-{a}.png' for a in [0,105,maximum]],'exports/display-hinge-study.step']
    report['outputs']={name:sha(HERE/name) for name in outputs};report['STEP_reopens']=True;report['STEP_solids']=len(reopened.Solids())
    for path,h in sources.items():assert sha(ROOT/path)==h,path
    out.write_text(json.dumps(report,indent=2)+'\n')
    print('saved cable study, four views and reopened STEP',flush=True)


if __name__=='__main__':main()

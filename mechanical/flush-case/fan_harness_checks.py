"""Check the fan's dressed routing envelope against the saved assembly."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

import fan_harness as harness
import usb_harness
from cad import bounds,box
from review import bbox_overlap,intersection_volume
from component_heights import screen_routes
from cooling_review import screen_component_heights

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def floor_cable_overlap(floor,cable):
    """Exact set clipping removes the low floor before the curved comparison."""
    if not bbox_overlap(floor,cable):return 0.0
    f=floor.BoundingBox();c=cable.BoundingBox();low=max(f.zmin-.01,c.zmin-.01)
    high=floor.intersect(box(f.xmin-.01,-f.ymax-.01,low,f.xlen+.02,f.ylen+.02,f.zmax-low+.02))
    assert high.Solids(),'floor clipping lost a positive-height section'
    b=high.BoundingBox();region=box(b.xmin-.01,-b.ymax-.01,b.zmin-.01,b.xlen+.02,b.ylen+.02,b.zlen+.02)
    total=0.0
    for s in cable.Solids():
        if not bbox_overlap(s,high):continue
        clipped=s.intersect(region)
        # A failed empty crop must not turn into a clear result.
        total+=intersection_volume(clipped if clipped.Solids() else s,high)
    return total


def check(parts,case,sources):
    g=harness.geometry();c=g['config'];xyz=g['points']*np.array([1,-1,1])
    pcb=ROOT/'ducktop2-center.kicad_pcb'
    assert hashlib.sha256(pcb.read_bytes()).hexdigest()==c['source_center_PCB_sha256'],'J52 source changed'
    d=c['layout_datums'];import remote_cooler
    fan=remote_cooler.config()['fan']
    assert case['boards']['main_bottom_H']==d['main_bottom_H'] and case['boards']['bms_bottom_H']==d['bms_bottom_H'],'redress the fan loom after board height changes'
    assert case['keyboard']['carrier_bottom_H']==d['carrier_bottom_H'] and case['base']['floor']==d['floor_mm'],'fan supports need updated case datums'
    assert fan['xy']==d['fan_xy'] and fan['bottom_H']==d['fan_bottom_H'],'fan exit moved'
    sources=dict(sources)
    for name in ['fan_harness.py','fan_harness_checks.py','fan-harness.json','fan-harness-heights.json','case_feet.py','feet.json']:
        path=HERE/name;sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    fixed=[p for p in parts if not p.get('moving') and not p.get('fan_harness') and p['group']!='changes' and not p.get('service')]
    new=[p for p in parts if p.get('fan_harness')]
    clashes=[];service=[];internal=[];cards=[]
    for card in [p for p in parts if p.get('fan_card_space')]:
        for name,shape in [('carrier-guides',harness.carrier_guide()),('splice-brace',harness.fan_wire_brace())]:
            if not bbox_overlap(shape,card['shape']):continue
            v=intersection_volume(shape,card['shape'])
            if v>.01:cards.append({'support':name,'card_space':card['name'],'overlap_mm3':round(v,5)})
    for p in new:
        if p.get('service'):
            hits=[]
            for q in fixed+[r for r in new if r['group']!='keepout' and r['name']!='fan-loom-envelope']:
                if q['name'] in p['service_removes']+p.get('service_moves',[]) or q['group']=='keepout' or not bbox_overlap(p['shape'],q['shape']):continue
                v=intersection_volume(p['shape'],q['shape'])
                if v>.01:hits.append({'part':q['name'],'overlap_mm3':round(v,5)})
            service.append({'access':p['name'],'remove_first':p['service_removes'],'moving_parts':p.get('service_moves',[]),'conflicts_after_removal':hits})
            continue
        if p['name']=='fan-loom-envelope':continue # Its larger position envelope is checked instead.
        for q in fixed:
            if not bbox_overlap(p['shape'],q['shape']):continue
            if p['name']=='fan-loom-position-space' and q['name']=='base-floor':
                v=floor_cable_overlap(q['shape'],p['shape'])
                if v>.01:clashes.append({'new':p['name'],'existing':q['name'],'overlap_mm3':round(v,5)})
                continue
            shape=p['shape'];regions=shape.Solids()
            if p['name']=='fan-loom-position-space' and q['name']=='blower-size-and-position-allowance':
                regions=[s.cut(harness.factory_exit_zone()) for s in regions]
            if p['name']=='fan-splice-support-brace' and q['name']=='blower-size-and-position-allowance':
                regions=[s.cut(harness.fan_mount_zone()) for s in regions]
            volume=0;where=[]
            for solid in q['shape'].Solids():
                if not bbox_overlap(shape,solid):continue
                if p['name']=='fan-loom-position-space':
                    b=solid.BoundingBox();lo=np.array([b.xmin,b.ymin,b.zmin]);hi=np.array([b.xmax,b.ymax,b.zmax])
                    # Circumscribes the widest fanout rectangle, plus the
                    # sampled route spacing and the fitted-curve allowance.
                    if not np.any(np.all((xyz>lo-3.6)&(xyz<hi+3.6),axis=1)):continue
                for region in regions:
                    if not region.Solids() or not bbox_overlap(region,solid):continue
                    rb=region.BoundingBox()
                    if p['name']=='fan-loom-position-space' and rb.xlen>100 and rb.ylen>100:
                        # Only the 1.8 mm round main sweep has this span. The
                        # short, wider fanout/splice pieces keep exact checks.
                        # 2 mm includes the sampled path and curve allowances.
                        if not np.any(np.all((xyz>lo-2.0)&(xyz<hi+2.0),axis=1)):continue
                    hit=region.intersect(solid)
                    raw=hit.Volume() if hit.Solids() else 0.0
                    assert math.isfinite(raw) and raw>=-.01,'invalid collision volume'
                    v=max(0,raw);volume+=v
                    if v>.01:where.append(bounds(hit))
            if volume>.01:clashes.append({'new':p['name'],'existing':q['name'],'overlap_mm3':round(volume,5),'regions':where})
        print('fan harness checked',p['name'],flush=True)
    physical=[p for p in new if p['group']!='keepout']
    for i,p in enumerate(physical):
        for q in physical[i+1:]:
            if not bbox_overlap(p['shape'],q['shape']):continue
            if {p['name'],q['name']}=={'fan-loom-envelope','fan-J52-plug-envelope'}:
                loom=p if p['name']=='fan-loom-envelope' else q;plug=q if loom is p else p
                v=sum(intersection_volume(s.cut(harness.header_wire_entry_zone()),plug['shape']) for s in loom['shape'].Solids())
            else:v=intersection_volume(p['shape'],q['shape'])
            if v>.01:internal.append({'a':p['name'],'b':q['name'],'overlap_mm3':round(v,5)})

    table,settings=usb_harness.height_inputs()
    for file in ['cooler-part-heights.json','fan-harness-heights.json']:
        extra=json.loads((HERE/file).read_text())
        for p in table:
            if p.get('mpn') in extra['manufacturer_maximums']:
                h=extra['manufacturer_maximums'][p['mpn']]
                p.update(height_mm=h['height_mm'],height_kind='maximum',height_status='verified_maximum',height_source_url=h['source'],height_basis=h['basis'])
        settings['reservations'].update(extra['reservations'])
    route={'name':'fan','group':'fan','points':g['points'].tolist(),'wire_od_mm':c['maximum_finished_bundle_OD_mm'],
           'ends':[{'board':'center','ref':'J52'},{'board':'external','ref':'fan'}]}
    tops={'center':5.5,'left':5.5,'right':5.5,'bms':9.5}
    guide={'guide_radial_clearance':0,'guide_wall':0,'guide_end_trim_by_route_mm':{'fan':0}}
    heights=screen_routes([route],table,tops,guide,settings)
    larger=[{'name':'fan-splice-envelope','shape':harness.tube(g['splice_points'],2.8)},
            {'name':'fan-header-fanout','shape':harness.sweep_rect(g['fanout_points'],-2.8,-1.8,5.6,3.6)},
            {'name':'fan-carrier-guide','shape':harness.carrier_guide()},
            {'name':'fan-splice-support-brace','shape':harness.fan_wire_brace()}]
    structural=screen_component_heights([p for p in table if not(p['board']=='center' and p['reference']=='J52')],larger,tops,settings)
    data=json.loads((HERE/'usb-harness.json').read_text());pairs=[]
    samples=usb_harness.dense_polyline(g['points'],.05)
    stations=np.r_[0,np.cumsum(np.linalg.norm(np.diff(samples,axis=0),axis=1))]
    radii=np.full(len(samples),1.8)
    tails=[pin['factory_run_to_splice_mm'] for pin in c['pins']];half=c['heatshrink_length_each_mm']/2
    splice=(stations>=stations[-1]-max(tails)-half-.05)&(stations<=stations[-1]-min(tails)+half+.05)
    radii[splice]=2.8;radii[stations<=20.05]=math.hypot(2.8,1.8)
    for r in data['routes']+data['other_routes']:
        q=usb_harness.dense_polyline(r['points'],.05);distance,indices=cKDTree(q).query(samples)
        # Includes both wire position budgets and a conservative allowance
        # for route sampling and interpolation. Actual rigid guides are
        # checked separately above.
        gaps=distance-radii-r['wire_od_mm']/2-.2-.05-.05;i=int(gaps.argmin());gap=float(gaps[i])
        pairs.append({'wire':r['name'],'gap_after_allowances_mm':round(gap,4),'pass':bool(gap>=.5)})
    radius=1/max(g['edge'].curvatures(np.linspace(0,1,20000),mode='parameter'))
    cuts=[];total=g['edge'].Length()
    for pin in c['pins']:
        factory=pin['factory_run_to_splice_mm']+c['splice_lap_allowance_mm']
        extension=total-pin['factory_run_to_splice_mm']+c['splice_lap_allowance_mm']+c['header_hidden_wire_allowance_mm']
        cuts.append({**pin,'factory_wire_nominal_cut_mm':round(factory,2),'extension_from_crimp_back_nominal_cut_mm':round(extension,2),
                     'stock_length_pass':factory<=140 and extension<=c['lead_inside_length_mm']-c['lead_length_tolerance_mm']})
    result={'date':c['date'],'source_hashes':sources,'configuration':c,'solid_conflicts':clashes,'internal_conflicts':internal,
            'card_space_support_conflicts':cards,
            'component_heights':heights,'larger_envelope_heights':structural,'wire_separation_checks':pairs,'service_checks':service,
            'nominal_route_length_mm':round(total,3),'minimum_centerline_bend_radius_mm':round(radius,4),
            'minimum_inside_bundle_bend_radius_mm':round(radius-1.6,4),'cut_schedule':cuts,
            'physical_fit_verified':False,'electrical_tests_complete':False,'strain_relief_verified':False,'manufacturing_ready':False,
            'limits':['Maximum dressed envelopes are modeled; individual wires, twist and solder-joint surfaces are not exact CAD.',
                      'The factory exit alone is exempt from the coarse rectangular blower allowance. The real housing is still checked.',
                      'The brace shares the fan mounting interface; only that bounded corner is exempt from the coarse body box.',
                      'The bounded J52 wire-entry aperture is an intentional connector interface. Withdrawal checks move the plug rather than treating its initial position as an obstacle.',
                      'J73 and J421 use explicit installed-height allocations. The programming plug and speaker cable still need service checks.',
                      'Cut dimensions include provisional lap and hidden-wire allowances; dress and measure the actual leads before final trimming.',
                      'The carrier guide and clamp require material, pull, heat and assembly tests. The case and keyboard removal sequence remains a prototype.']}
    result['nominal_geometry_pass']=bool(not(clashes or internal or cards or heights['unverified_height_limits'] or heights['known_height_clearance_conflicts'] or structural['known_component_height_conflicts'] or structural['unverified_component_height_screens']) and
        all(r['pass'] for r in pairs) and all(r['stock_length_pass'] for r in cuts) and radius-1.6>=c['minimum_inside_bend_radius_mm'] and
        not any(r['conflicts_after_removal'] for r in service))
    (HERE/'fan-harness-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['nominal_geometry_pass','solid_conflicts','internal_conflicts','minimum_inside_bundle_bend_radius_mm']},indent=2),flush=True)
    return result

"""Power guides, measured-height envelopes and service checks.

Courtyards are conservative plan envelopes, not manufacturer body shapes.
Unknown heights stay unknown. A clean BRep intersection check is not a
complete assembly approval when some parts lack models or measurements.
"""
import json
import hashlib
from shapely.geometry import Polygon
from cad import HERE,ROOT,box,cylinder
from case_inputs import path as input_path
from component_heights import resolve, screen_routes


def check(m):
    from build import CONFIG,pcb_top
    from review import bbox_overlap,intersection_volume
    results={'power_wire_collisions':[],'guide_case_collisions':[],'service_conflicts':[],
             'known_height_clearance_conflicts':[],'unverified_height_limits':[],
             'component_height_vs_structure':[], 'harness_internal_clashes':[],
             'braid_joint_clearance_conflicts':[],
             'scope':'BRep checks, with pre-fusion carrier pieces as a conservative superset; carrier hits may include subsequently relieved material. Courtyard-height checks are conservative too. No physical fit approval.'}
    def checkpoint(phase):
        results['phase']=phase
        (HERE/'harness-case-checks.json').write_text(json.dumps(results,indent=2)+'\n')
    checkpoint('started')
    def volume(a,b):
        if not bbox_overlap(a,b):return 0
        return intersection_volume(a,b)
    wires=[p for p in m.parts if p.get('power_wire')]
    for w in wires:
        print('checking '+w['name'],flush=True)
        for p in m.parts:
            if p is w or p['group'] in ['keepout','routes'] or p.get('power_wire') or p.get('intentional_wire_grip'):continue
            v=volume(w['shape'],p['shape'])
            if v>.02 and p.get('harness_part'):
                # Carrier primitives are a superset. Confirm an apparent wire
                # hit against the final part after its bore/relief cuts.
                v=max(0,w['shape'].intersect(p['shape']).Volume())
            if v>.02:results['power_wire_collisions'].append({'wire':w['name'],'part':p['name'],'overlap_mm3':round(v,4)})
    print('power-wire BRep checks complete',flush=True)
    checkpoint('power-wire checks complete')
    guides=[p for p in m.parts if p.get('harness_part') and not p.get('intentional_wire_grip')]
    others=[p for p in m.parts if not p.get('harness_part') and not p.get('power_wire') and p['group'] not in ['keepout','routes']]
    for g in guides:
        print('checking support '+g['name'],flush=True)
        for p in others:
            prefix=g['name'].removesuffix('-carrier').removesuffix('-pedestal').removesuffix('-cap')
            if p.get('harness_fastener') and p['name'].startswith(prefix+'-'):continue
            v=volume(g['shape'],p['shape'])
            if v>.05 and p.get('thread_host')==g['name']:
                x,y=p['thread_axis_xy_mm'];lo,hi=p['thread_height_range_mm']
                contact=cylinder(x,y,lo,p['thread_radius_mm'],hi-lo)
                overlap=g['shape'].intersect(p['shape'])
                v=max(0,overlap.cut(contact).Volume())
            if v>.05:results['guide_case_collisions'].append({'guide':g['name'],'part':p['name'],'overlap_mm3':round(v,3)})
    for i,g in enumerate(guides):
        for p in guides[i+1:]:
            ga=g['name'].removesuffix('-carrier').removesuffix('-cap').removesuffix('-pedestal')
            pa=p['name'].removesuffix('-carrier').removesuffix('-cap').removesuffix('-pedestal')
            if ga==pa:continue # actual cap shape was cut from the carrier
            v=volume(g['shape'],p['shape'])
            if v>.02:results['harness_internal_clashes'].append({'a':g['name'],'b':p['name'],'overlap_mm3':round(v,3)})
    for braid in [p for p in m.parts if p.get('braid_allowance')]:
        for p in guides+[p for p in m.parts if p.get('harness_fastener')]:
            v=volume(braid['shape'],p['shape'])
            if v>.02:results['braid_joint_clearance_conflicts'].append({'braid':braid['name'],'part':p['name'],'overlap_mm3':round(v,3)})
    # These parts are removed before a terminal is serviced. The pedestals stay
    # fixed, so cables never depend on lifting the keyboard/trackpad support.
    def removed(p):
        return p.get('moving') or p['group'] in ['deck','inputs'] or p.get('service_removable') or p['name'].startswith(
            ('keyboard-','key-travel','trackpad-','radio-','oled-','speaker-','blower-','fan-through'))
    retained=[p for p in m.parts if not removed(p) and (p.get('manufactured') or p.get('power_wire')) and not p.get('intentional_wire_grip')]
    for s in [p for p in m.parts if p.get('service')]:
        for p in retained:
            # A wire can occupy its own wire-release envelope before removal.
            if p.get('power_wire') and ('button' in s['name'] or 'XT30' in s['name']):continue
            v=volume(s['shape'],p['shape'])
            if v>.1:results['service_conflicts'].append({'access':s['name'],'part':p['name'],'overlap_mm3':round(v,3)})
    results['service_removed_first']=['lid open','removable deck and inputs','keyboard carrier and fan cradle as service procedure permits','split clamp caps','selected cable guide section for XT30 axial extraction']
    results['intentional_contacts_excluded']=['0.025 mm radial liner grip','M2 thread envelope in its own 1.6 mm pilot','source PCB component solder seating']
    print('guide and service BRep checks complete',flush=True)
    checkpoint('guide and service checks complete')
    parts=json.loads(input_path('component-placement.json').read_text())['parts']
    height_settings=json.loads((HERE/'height-allowances.json').read_text())
    results['height_check_sources_sha256']={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
        for name in ['height-allowances.json','component_heights.py','clearance_review.py']}
    results['height_allowances']=height_settings
    from cables import polygon_prism
    structures=[p for p in m.parts if (p.get('manufactured') or p['group']=='cooling') and not p.get('moving') and not p.get('intentional_wire_grip')]
    for p in parts:
        if p['dnp']:continue
        limit=resolve(p,height_settings)
        if limit is None:continue
        rings=p['courtyards_installed_mm'][p['side']]
        if not rings:continue
        height=limit['height_mm']
        h=pcb_top(p['board']) if p['side']=='front' else CONFIG['boards'][p['board']]['bottom_height']-height
        # This is a conservative courtyard-height volume. Report it separately
        # from actual BRep body collisions, never as a verified physical clash.
        for ring in rings:
            poly=Polygon(ring['outer']);x0,y0,x1,y1=poly.bounds
            rough=box(x0,y0,h,max(.01,x1-x0),max(.01,y1-y0),height)
            candidates=[s for s in structures if bbox_overlap(rough,s['shape'])]
            if not candidates:continue
            envelope=polygon_prism(ring['outer'],h,height)
            for s in candidates:
                v=volume(envelope,s['shape'])
                if v>.02:results['component_height_vs_structure'].append({'component':p['board']+'/'+p['reference'],'structure':s['name'],
                    'overlap_mm3':round(v,3),'height_basis':limit['basis'],
                    'screen':'courtyard x reviewed height and assembly allowance; exact body-fit check needed'})
    results.update(screen_routes(m.harness['routes'],parts,
        {name:pcb_top(name) for name in CONFIG['boards']},CONFIG['cables'],height_settings))
    # Backside limits apply to the whole main-board floor, not only components
    # present in the partial native STEP export.
    back=[p for p in parts if p['side']=='back' and not p['dnp']]
    gaps=[CONFIG['boards'][p['board']]['bottom_height']-p['height_mm']-(p['planning_allowance_mm'] or 0)-CONFIG['base']['floor'] for p in back if p['height_mm'] is not None]
    results['main_backside_to_floor_mm']=min(gaps)
    results['unverified_backside_height_count']=sum(p['height_mm'] is None for p in back)
    results['power_path_checks']={k:v for k,v in m.harness.items() if k.startswith('all_') or k=='minimum_wire_separation_mm'}
    results['guide_fit_tolerance_mm']=CONFIG['cables']['guide_radial_clearance']
    results['physical_fit_verified']=False
    results['phase']='complete'
    (HERE/'harness-case-checks.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({k:len(v) for k,v in results.items() if isinstance(v,list) and k!='service_removed_first'},indent=2),flush=True)
    return results

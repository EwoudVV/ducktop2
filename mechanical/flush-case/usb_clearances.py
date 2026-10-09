"""Check the revised USB guides against retained parts and component heights."""
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

from cad import box
from cables import polygon_prism
from component_heights import resolve
from review import bbox_overlap,intersection_volume
import usb_harness
from usb_collision import Checks

HERE=Path(__file__).resolve().parent


def usb_part(part):
    return part['name'].startswith(('usb5-','harness-USB-'))


def check(parts,case):
    new=[p for p in parts if usb_part(p) and p['group']!='keepout']
    others=[p for p in parts if not usb_part(p) and not p.get('moving')
            and p['group'] not in ['keepout','changes']]
    others += [p for p in parts if p['name']=='raw-pack-J2-wire-exit-reservation']
    # Curved guide channels and bare wires use the full route height screen.
    # These crops cover all extra clamp/support material outside those channels.
    # They are intersections of the final carrier, so cap holes and reliefs stay.
    rigid=[]
    for p in new:
        if p.get('power_wire') or p.get('intentional_wire_grip'):continue
        if p['name'].endswith('-carrier'):
            side='left' if '-left-' in p['name'] else 'right'
            seam=70.75 if side=='left' else 299.25
            bracket=130 if side=='left' else 225
            for tag,region in [('clamp',box(seam-4.5,0,0,9,260,26)),
                               ('bracket',box(bracket-5.1,100.9,0,10.2,25,26))]:
                cropped=p['shape'].intersect(region)
                if cropped.Volume()>.001:rigid.append({**p,'shape':cropped,'screen_region':tag})
        else:rigid.append({**p,'screen_region':'whole part'})
    data=json.loads((HERE/'usb-harness.json').read_text())
    checker=Checks(parts,case,data,rigid)
    clashes=[]
    for p in new:
        for q in others:
            volume=checker.volume(p,q)
            if volume>.01:
                clashes.append({'USB_part':p['name'],'other':q['name'],'detected_overlap_mm3':round(volume,4)})
    print('USB solids checked against retained parts:',len(clashes),'overlaps',flush=True)
    table,settings=usb_harness.height_inputs()
    unknown=[];conflicts=[];count=0
    for part in table:
        if part['dnp'] or part['board']=='radio':continue
        rings=part['courtyards_installed_mm'][part['side']]
        if not rings:continue
        area=unary_union([Polygon(r['outer'],r['holes']) for r in rings]).buffer(.3)
        minx,miny,maxx,maxy=area.bounds
        if part['board']=='bms':bottom=case['boards']['bms_bottom_H']
        elif part['board']=='keyboard':bottom=case['boards']['keyboard_bottom_H']
        else:bottom=case['boards']['main_bottom_H']
        limit=resolve(part,settings)
        height=limit['height_mm'] if limit else 25.0
        plane=bottom if part['side']=='back' else bottom+part['board_thickness_mm']
        low=plane-height if part['side']=='back' else plane
        proxy=box(minx,miny,low,maxx-minx,maxy-miny,height)
        possible=[p for p in rigid if bbox_overlap(p['shape'],proxy)]
        if not possible:continue
        shapes=[polygon_prism(list(poly.exterior.coords),low,height) for poly in (list(area.geoms) if hasattr(area,'geoms') else [area])]
        for p in possible:
            volume=sum(intersection_volume(p['shape'],s) for s in shapes)
            if volume<=.01:continue
            row={'USB_part':p['name'],'screen_region':p['screen_region'],
                 'component':part['board']+'/'+part['reference'],'side':part['side'],
                 'mpn':part['mpn'],'overlap_mm3':round(volume,4),
                 'scope':'courtyard plus 0.3 mm XY; height includes the recorded assembly allowance'}
            if limit:conflicts.append({**row,**limit})
            else:unknown.append(row)
            count+=1
    service=[]
    feet=[p for p in new if p['name'].endswith('-fixed-seam-foot')]
    envelopes=[p for p in parts if p.get('service') and not usb_part(p)]
    for p in feet:
        for q in envelopes:
            if not bbox_overlap(p['shape'],q['shape']):continue
            volume=intersection_volume(p['shape'],q['shape'])
            if volume>.01:service.append({'fixed_foot':p['name'],'access':q['name'],'overlap_mm3':round(volume,4)})
    result={'date':'2026-10-09','solid_conflicts':clashes,
            'conservative_bound_rejections':checker.bound_rejections,'exact_contact_checks':checker.exact_checks,
            'rigid_component_height_conflicts':conflicts,'unverified_rigid_component_heights':unknown,
            'fixed_feet_service_conflicts':service,
            'route_component_crossings':len(data['component_height_crossings']),
            'route_unknown_heights':data['unverified_height_limits'],
            'route_height_conflicts':data['known_height_clearance_conflicts'],
            'smallest_wire_gap_after_allowances_mm':min(r['gap_after_allowances_mm'] for r in data['pairs']),
            'nominal_geometry_pass':not(clashes or conflicts or unknown or service),
            'scope':'new USB physical parts versus retained rigid CAD and raw-pack exit reservation; extra clamp/support material uses front and back component height envelopes; fixed feet checked after removing the deck, keyboard carrier and USB upper rails',
            'guide_screen':'sampled cable-channel bounds include position, curve and sample-spacing allowances. Added bracket/clamp material is checked separately; potential contacts are confirmed against final solids. Detected overlap volumes may be from actual subsets, not the total union volume.',
            'own_wire_bore_clearance_basis':'0.15 mm guide clearance, 0.25 mm bracket bores and 0.35 mm end-clamp bores, each larger than two 0.008 mm curve-fit allowances; TPU liner grip is intentional',
            'physical_fit_verified':False,
            'remaining':['dressed wire cut lengths and solder-cup seating','carrier/clip stiffness and pull tests',
                         'actual screw fit and assembly order','complete signal, raw-pack, tap and probe harnesses']}
    (HERE/'usb-clearances.json').write_text(json.dumps(result,indent=2)+'\n')
    print('USB component envelope conflicts:',len(conflicts),'unknown heights:',len(unknown),flush=True)
    return result

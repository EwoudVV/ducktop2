"""Shorter USB power wires and removable guides behind the keyboard."""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
from scipy.spatial import cKDTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'mechanical/case-prototype'
sys.path.insert(0,str(BASE))
import build as baseline
from cad import box,cylinder,compound
from cables import path_edge,tube,guide,strain_clamp,clean_left_usb_trim,polygon_prism
from component_heights import guided_points,screen_routes,resolve
from harness_geometry import smooth


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def line(a,b):
    return np.linspace(a,b,max(2,math.ceil(np.linalg.norm(np.array(b)-a)/.2)+1))


def dense_polyline(points,step=.05):
    p=np.array(points);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    at=np.linspace(0,s[-1],math.ceil(s[-1]/step)+1)
    return np.column_stack([np.interp(at,s,p[:,i]) for i in range(3)])


def height_inputs():
    parts=json.loads((ROOT/'mechanical/component-placement.json').read_text())['parts']
    settings=json.loads((BASE/'height-allowances.json').read_text())
    extra=json.loads((HERE/'usb-part-heights.json').read_text())
    for p in parts:
        if p.get('mpn') in extra['manufacturer_maximums']:
            h=extra['manufacturer_maximums'][p['mpn']]
            p.update(height_mm=h['height_mm'],height_kind='maximum',height_status='verified_maximum',
                     height_source_url=h['source'],height_basis=h['basis'])
    settings['reservations'].update(extra['reservations'])
    return parts,settings


def make_paths(case):
    path=BASE/'installed-power-harness.json';source=json.loads(path.read_text())
    dz=case['boards']['main_bottom_H']-baseline.CONFIG['boards']['center']['bottom_height']
    if abs((case['boards']['bms_bottom_H']-baseline.CONFIG['boards']['bms']['bottom_height'])-dz)>1e-8:
        raise ValueError('BMS and main boards need the same height change for retained wires')
    if source['USB_front_drop_mm']!=.5:raise ValueError('source USB approach changed')
    rows=[]
    for route in source['routes']:
        r=copy.deepcopy(route);p=np.array(r['points']);p[:,2]+=dz
        for end in r['ends']:end['point'][2]+=dz
        if r['group']=='usb5':
            positive=r['name']=='usb5-USB_PORT_5V'
            endpoint_h=route['ends'][0]['point'][2]+dz
            common_h=18+dz
            # Keep the original XT30 approaches and recover their upper plane.
            old_weight=smooth((p[:,0]-60)/45)*smooth((280-p[:,0])/45)*smooth((p[:,1]-90)/25)
            p[:,2]+=.5*old_weight
            if positive:p[:,2]=endpoint_h+(p[:,2]-endpoint_h)*(18-9.5)/(21.2-9.5)
            front_y=124 if positive else 119
            cx=256 if positive else 258;radius=20 if positive else 24
            cy=front_y-radius;right_x=cx+radius
            indices=np.flatnonzero(p[:,0]<140);trough=indices[p[indices,1].argmin()]
            head=p[:trough+1].copy();head[-1,1]=front_y
            straight=line(head[-1],[cx,front_y,common_h])
            angle=np.linspace(math.pi/2,0,301)
            turn=np.column_stack([cx+radius*np.cos(angle),cy+radius*np.sin(angle),np.full(len(angle),common_h)])
            indices=np.flatnonzero((p[:,0]>=(278 if positive else 282)-.01)&(p[:,1]<=cy))
            tail=p[indices[0]:].copy()
            if positive:tail[:,0]-=2*smooth((tail[:,1]-45)/25)
            join=line(turn[-1],tail[0])
            p=np.vstack([head,straight[1:],turn[1:],join[1:],tail[1:]])
            shift=smooth((p[:,0]-114)/28)*smooth((254-p[:,0])/22)*smooth((p[:,1]-108)/6)
            p[:,1]-=2*shift
            if positive:
                bridge=smooth((p[:,0]-235)/25)*smooth((p[:,1]-94)/20)
                p[:,2]+=3.6*bridge
            if case.get('usb_heatpipe_crossing'):
                dip=case['usb_heatpipe_crossing']
                weight=smooth((p[:,0]-dip['x_start'])/(dip['x_full']-dip['x_start']))
                weight*=smooth((p[:,1]-dip['rear_start_y'])/(dip['rear_full_y']-dip['rear_start_y']))
                weight*=smooth((dip['front_end_y']-p[:,1])/(dip['front_end_y']-dip['front_full_y']))
                p[:,2]-=dip['drop_mm']*weight
            edge=path_edge(p)
            radius_min=1/max(max(edge.curvatures(np.linspace(0,1,20000),mode='parameter')),1e-12)
            endpoint_error=max((edge.startPoint()-cq.Vector(*[p[0,0],-p[0,1],p[0,2]])).Length,
                               (edge.endPoint()-cq.Vector(*[p[-1,0],-p[-1,1],p[-1,2]])).Length)
            inside=radius_min-r['wire_od_mm']/2
            r.update(exposed_length_mm=edge.Length(),nominal_cut_length_mm=round(edge.Length()+4,2),
                     minimum_inside_radius_mm=inside,minimum_centerline_radius_mm=radius_min,
                     bend_5d_pass=inside>=5*r['wire_od_mm']*1.01,bend_10d_pass=inside>=10*r['wire_od_mm']*1.01,
                     endpoint_fit_error_mm=endpoint_error,
                     old_400_to_420mm_length_pass=400<=edge.Length()+4<=420,
                     within_existing_420mm_electrical_max=edge.Length()+4<=420,
                     length_pass=edge.Length()+4<=420,
                     length_criterion='maximum 420 mm per wire; old 400 mm minimum cutting target superseded by this shorter case route',
                     case_route_change='front run behind keyboard with a local raised crossover; terminal positions retained',
                     length_basis='shorter case route; 2 mm provisional hidden length at each solder cup. Final cut length needs a dressed sample.',
                     bend_basis='actual fitted CAD spline, 20000 curvature stations; 1 percent margin on 5D inside radius')
            if not r['bend_5d_pass'] or not r['within_existing_420mm_electrical_max'] or endpoint_error>.01:
                raise ValueError(r['name']+' fails its geometric limits: '+json.dumps({k:r[k] for k in ['minimum_inside_radius_mm','nominal_cut_length_mm','endpoint_fit_error_mm']}))
        r.pop('sparse_interpolant_inside_radius_diagnostic_mm',None)
        r['max_wire_height_mm']=float(p[:,2].max()+r['wire_od_mm']/2+.2+.025)
        r['points']=p.tolist();rows.append(r)
    samples=[dense_polyline(r['points']) for r in rows]
    pairs=[]
    for i,(a,pa) in enumerate(zip(rows,samples)):
        for b,pb in list(zip(rows,samples))[i+1:]:
            if a['group']!='usb5' and b['group']!='usb5':continue
            d,ix=cKDTree(pa).query(pb);k=d.argmin()
            # Cover both sampling intervals, 0.2 mm wire position each, and
            # 0.025 mm fitted-curve allowance each. The last allowance also
            # covers interpolation between original source stations.
            gap=float(d[k])-(a['wire_od_mm']+b['wire_od_mm'])/2-.4-.05-.05
            pairs.append({'a':a['name'],'b':b['name'],'gap_after_allowances_mm':gap,'pass':gap>=.5})
    usb=[r for r in rows if r['group']=='usb5'];parts,settings=height_inputs()
    tops={n:case['boards']['main_bottom_H']+1.6 for n in ['left','center','right']};tops['bms']=case['boards']['bms_bottom_H']+1.6
    heights=screen_routes(usb,parts,tops,baseline.CONFIG['cables'],settings)
    if any(not r['pass'] for r in pairs) or heights['known_height_clearance_conflicts'] or heights['unverified_height_limits']:
        raise ValueError('USB route clearance failed: '+json.dumps({'pairs':[r for r in pairs if not r['pass']],**heights}))
    return {'source':'mechanical/case-prototype/installed-power-harness.json','source_sha256':digest(path),
            'date':case['date'],'coordinate_frame':'installed X,Y,+H; export uses Z=-H',
            'source_height_change_mm':dz,'routes':usb,'other_routes':rows[:-2] if all(r['group']=='usb5' for r in rows[-2:]) else [r for r in rows if r['group']!='usb5'],
            'pairs':pairs,**heights,'physical_fit_verified':False,
            'wire_source':'https://www.alphawire.com/Products/wire/ecogen/ecowire/6716',
            'length_change':'The old 400 to 420 mm cutting range is not retained. The 420 mm electrical maximum is unchanged.',
            'limits':{'wire_position_each_mm':.2,'curve_each_mm':.025,'sampling_pair_mm':.05,'minimum_wire_surface_gap_mm':.5}}


def guide_bracket(model,side,rows,x):
    ys=[float(np.array(r['points'])[np.argmin(abs(np.array(r['points'])[:,0]-x)),1]) for r in rows]
    low=min(float(np.array(r['points'])[np.argmin(abs(np.array(r['points'])[:,0]-x)),2])-r['wire_od_mm']/2-.55 for r in rows)-.15
    rear_y=105.5
    arm=box(x-4,rear_y-2,low-3,8,max(ys)+2-(rear_y-2),3)
    arm=arm.fuse(box(x-4,rear_y-2,low-3,8,4,20-(low-3)))
    arm=arm.fuse(box(x-5,101,18.5,10,8,1.5))
    arm=arm.cut(cylinder(x,rear_y,16.5,.8,3.6))
    for r,y in zip(rows,ys):
        p=np.array(r['points']);local=p[(p[:,0]>=x-5)&(p[:,0]<=x+5)]
        boss=box(x-3,y-2,low-.1,6,4,1)
        boss=boss.cut(tube(local,r['wire_od_mm']/2+.25))
        arm=arm.fuse(boss)
    model.add('harness-USB-'+side+'-keyboard-bracket',arm,'supports',harness_part=True)
    model.add('harness-USB-'+side+'-keyboard-screw',cylinder(x,rear_y,17,1,4).fuse(cylinder(x,rear_y,21,2,2)),
              'hardware','nylon',False,False,harness_fastener=True,service_removable=True,
              thread_host='harness-USB-'+side+'-carrier',thread_axis_xy_mm=[x,rear_y],
              thread_height_range_mm=[17,20],thread_radius_mm=1.)
    model.mount('USB-'+side+'-keyboard-bracket',x,rear_y,21,'removable guide bracket below keyboard-carrier tab',
                2.2,'M2',3,4,'insulating bracket; plug pull loads go into separate seam clamps',
                'head space 2 mm; thread and deflection test required',minimum_thread_engagement_mm=3)


def build_parts(case,data):
    saved=baseline.CONFIG
    config=copy.deepcopy(saved);config['base']['floor']=case['base']['floor']
    for name in ['left','center','right']:config['boards'][name]['bottom_height']=case['boards']['main_bottom_H']
    config['boards']['bms']['bottom_height']=case['boards']['bms_bottom_H']
    baseline.CONFIG=config
    model=baseline.Model();model.harness=data
    try:
        rows=data['routes'];c=config['cables']
        for r in rows:
            model.add(r['name']+'-power-wire',tube(r['points'],r['wire_od_mm']/2),'cables','Alpha 6716',False,False,
                      power_wire=True,wire_name=r['name'])
            full=guide(guided_points(r,c),r['wire_od_mm'],c['guide_radial_clearance'],c['guide_wall'])
            for side,x,w in [('left',0,179),('right',179,250)]:
                model.add(r['name']+'-guide-'+side,full.intersect(box(x,0,0,w,260,40)),
                          'supports',harness_part=True,guide_for=r['name'])
        for side,x in [('left',70.75),('right',299.25)]:strain_clamp(model,'harness-USB-'+side,rows,x)
        for side,x in [('left',130),('right',225)]:guide_bracket(model,side,rows,x)
        for side,seam_x in [('left',70.75),('right',299.25)]:
            prefix='harness-USB-'+side
            pieces=[p for p in model.parts if p['name'].endswith('-guide-'+side) or p['name'] in [prefix+'-pedestal',prefix+'-keyboard-bracket']]
            shape=pieces[0]['shape']
            for p in pieces[1:]:shape=shape.fuse(p['shape'])
            for bore in model.clamp_bores[prefix]:shape=shape.cut(bore)
            cap=next(p for p in model.parts if p['name']==prefix+'-cap')['shape'];shape=shape.cut(cap)
            if side=='left':shape=clean_left_usb_trim(shape)
            reliefs=[]
            if side=='right':
                from shapely.geometry import Polygon,Point
                from shapely.ops import unary_union
                table,settings=height_inputs()
                pilots=[Point(r['X_mm'],r['Y_mm']) for r in model.mounts if r['reference'].startswith(prefix+'-cap-')]
                for reference in ['U913','C924']:
                    component=next(p for p in table if p['board']=='center' and p['reference']==reference)
                    limit=resolve(component,settings)
                    region=unary_union([Polygon(r['outer'],r['holes']) for r in component['courtyards_installed_mm']['front']]).buffer(.3)
                    top=case['boards']['main_bottom_H']+1.6
                    relief=polygon_prism(list(region.exterior.coords),top-.1,limit['height_mm']+.3)
                    shape=shape.cut(relief)
                    pilot_margin=min(region.distance(point) for point in pilots)-.8
                    if pilot_margin<.4:raise ValueError(reference+' relief leaves too little clamp-pilot wall')
                    reliefs.append({'reference':'center/'+reference,'above_PCB_to_mm':limit['height_mm']+.2,
                                    'courtyard_expansion_mm':.3,'minimum_pilot_ligament_mm':round(pilot_margin,4)})
            # Detachable upper rail: only its narrow tongue enters the PCB seam.
            floor=config['base']['floor'];low=box(seam_x-4,0,floor-.1,8,260,5.5-floor+.1)
            slot=box(seam_x-.7,0,floor+1,1.4,260,3.3);blade=box(seam_x-.5,0,floor+1.3,1,260,3)
            foot=shape.intersect(low).cut(slot);upper=shape.cut(low).fuse(shape.intersect(blade))
            for suffix,s in [('carrier',upper),('fixed-seam-foot',foot)]:
                if not s.isValid() or len(s.Solids())!=1:raise ValueError(prefix+' '+suffix+' is not one solid')
                model.add(prefix+'-'+suffix,s,'supports',harness_part=True,service_removable=suffix=='carrier',component_reliefs=reliefs)
            remove={p['name'] for p in pieces};model.parts=[p for p in model.parts if p['name'] not in remove]
    finally:baseline.CONFIG=saved
    for p in model.parts:
        p['group']='keepout' if p.get('service') else 'wiring'
        p['moving']=False
    return model.parts,model.mounts


def carrier_tabs(carrier):
    for x in [130,225]:
        carrier=carrier.fuse(box(x-5,99,20,10,10,1)).cut(cylinder(x,105.5,19.9,1.1,1.2))
    return carrier


def load_parts():
    cache=ROOT/'.workbench/flush-case-usb-20261009/parts'
    record=json.loads((cache/'parts.json').read_text())
    assert record.get('source_hashes'),'USB cache needs its input hashes; rebuild it'
    assert all(digest(Path(p))==value for p,value in record['source_hashes'].items()),'USB cache input changed'
    assert record['module_sha256']==digest(Path(__file__)),'USB part cache source changed'
    assert record['case_sha256']==digest(HERE/'assembly.json'),'USB case datums changed'
    assert record['routes_sha256']==digest(HERE/'usb-harness.json'),'USB routes changed'
    parts=[]
    for row in record['parts']:
        shape=cq.Shape.importBrep(str(cache/row['brep']))
        if not shape.isValid():raise ValueError('invalid cached USB shape: '+row['name'])
        parts.append({**{k:v for k,v in row.items() if k!='brep'},'shape':shape})
    return parts,json.loads((HERE/'usb-harness.json').read_text()),record['mounts']


def main():
    before={str(p):digest(p) for p in [Path(__file__),HERE/'assembly.json',HERE/'usb-part-heights.json',BASE/'installed-power-harness.json',
                                     BASE/'cables.py',BASE/'component_heights.py',ROOT/'mechanical/component-placement.json']}
    case=json.loads((HERE/'assembly.json').read_text());data=make_paths(case)
    (HERE/'usb-harness.json').write_text(json.dumps(data,indent=2)+'\n')
    print('USB route checks passed',flush=True)
    parts,mounts=build_parts(case,data)
    cache=ROOT/'.workbench/flush-case-usb-20261009/parts';cache.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i,p in enumerate(parts):
        file=f'{i:03}.brep';p['shape'].exportBrep(str(cache/file))
        rows.append({**{k:v for k,v in p.items() if k!='shape'},'brep':file})
    assert before=={p:digest(Path(p)) for p in before},'sources changed during USB build'
    record={'parts':rows,'mounts':mounts,'source_hashes':before,'module_sha256':digest(Path(__file__)),
            'case_sha256':digest(HERE/'assembly.json'),'routes_sha256':digest(HERE/'usb-harness.json')}
    (cache/'parts.json').write_text(json.dumps(record,indent=2)+'\n')
    print('USB guide parts saved:',len(parts),flush=True)


if __name__=='__main__':main()

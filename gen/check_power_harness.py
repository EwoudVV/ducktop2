"""Check the BMS cable paths against current board, component and plug envelopes."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]


def prism_distance(points,polygon,low,high):
    """Signed distance to an extruded polygon, including its board cutouts."""
    xy=shapely.points(points[:,:2])
    planar=shapely.distance(polygon.boundary,xy)
    planar[shapely.contains(polygon,xy)]*=-1
    vertical=np.abs(points[:,2]-(low+high)/2)-(high-low)/2
    return np.hypot(np.maximum(planar,0),np.maximum(vertical,0))+np.minimum(np.maximum(planar,vertical),0)


def dense(points,step=.025):
    points=np.asarray(points,float)
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    return CubicSpline(s,points,axis=0)(np.linspace(0,s[-1],int(np.ceil(s[-1]/step))+1))


def check(root=ROOT):
    from fpc_contract import BMS_POWER_WIRE_LENGTH_BUDGET_MM
    def read(name):return json.loads((root/name).read_text())
    harness=read('mechanical/power-harness.json');datums=read('mechanical/board-datums.json')
    parts=read('mechanical/component-placement.json')['parts']
    access=read('mechanical/bms-connector-access.json')['connectors']
    settings=read('mechanical/bms-harness-routing.json');tops=harness['study_board_top_z']
    failures=[];rows=[];unknown=[];assumptions=[]
    for name,digest in {**harness['source_sha256'],**harness.get('generator_sources_sha256',{})}.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:failures.append('stale board: '+name)
    obstacles=[]
    for name in ('center','bms'):
        for outline in datums['boards'][name]['outlines']:
            obstacles.append((name+'/substrate',Polygon(outline['outer'],outline['holes']),tops[name]-1.6,tops[name],False))
        for i,hole in enumerate(datums['boards'][name]['mounting_holes']):
            obstacles.append((name+'/mount-'+str(i),Point(hole['position']).buffer(2.5,quad_segs=32),tops[name],tops[name]+2.5,True))
    for p in parts:
        if p['side']!='front' or p['dnp'] or p['reference']=='J2071':continue
        name=p['board']+'/'+p['reference'];height=p['height_mm'];reserved=False
        if p['reference'].startswith('H'):continue
        if name=='center/J2073':height=3.2;reserved=True
        if name in settings['assembly_reservations_mm']:height=settings['assembly_reservations_mm'][name];reserved=True
        for ring in p['courtyards_installed_mm']['front']:
            polygon=Polygon(ring['outer'],ring['holes'])
            if height is None:unknown.append((name,polygon,tops[p['board']]))
            else:obstacles.append((name,polygon,tops[p['board']],tops[p['board']]+height,reserved))
    for c in access:
        if c['reference']=='J2072':continue
        obstacles.append(('bms/'+c['reference'],Polygon(c['installed_mated_polygon_mm']),tops['bms'],
                          tops['bms']+c['reserved_height_above_pcb_mm'],True))
        if c['installed_withdrawal_polygon_mm']:
            obstacles.append(('bms/'+c['reference']+'/withdrawal',Polygon(c['installed_withdrawal_polygon_mm']),tops['bms'],
                              tops['bms']+c['reserved_height_above_pcb_mm'],True))
    obstacles_tree=shapely.STRtree([o[1] for o in obstacles])
    curves={r['name']:dense(r['points']) for r in harness['routes']}
    missing=[]
    for route in harness['routes']:
        if route['group']!='bms-power':continue
        p=curves[route['name']]
        radius=route['wire_od_mm']/2+settings['guide_radial_clearance_mm']+settings['guide_wall_mm']
        required=radius+settings['wire_position_allowance_mm']+settings['body_clearance_mm']+.041
        shadow=LineString(p[:,:2]).buffer(required)
        crossings=[]
        for i in obstacles_tree.query(shadow):
            name,polygon,low,high,reserved=obstacles[i]
            clearance=float(prism_distance(p,polygon,low,high).min()-required)
            crossings.append({'part':name,'remaining_clearance_mm':round(clearance,5),'uses_assembly_reservation':reserved})
            if clearance<0:failures.append(route['name']+' intersects '+name)
            if reserved and polygon.intersects(shadow):assumptions.append(name)
        for name,polygon,top in unknown:
            if not shadow.intersects(polygon):continue
            xy=shapely.points(p[:,:2]);near=shapely.distance(polygon,xy)<=required
            limit=float(p[near,2].min()-required-top)
            missing.append({'wire':route['name'],'part':name,'maximum_component_height_mm':round(limit,4)})
        # This is the same fitted centerline used to construct the swept CAD.
        import cadquery as cq
        edge=cq.Edge.makeSplineApprox([cq.Vector(float(x),float(-y),float(z)) for x,y,z in route['points']],
                                     tol=.008,minDeg=3,maxDeg=6)
        inside=1/max(edge.curvatures(np.linspace(0,1,10000),mode='parameter'))-route['wire_od_mm']/2
        minimum=5*route['wire_od_mm']*1.01
        cut=edge.Length()+16
        if inside<minimum:failures.append(route['name']+' exported CAD bend is too tight')
        if cut>BMS_POWER_WIRE_LENGTH_BUDGET_MM:failures.append(route['name']+' exceeds electrical wire-length budget')
        rows.append({'wire':route['name'],'cut_length_mm':round(cut,3),'CAD_minimum_inside_radius_mm':round(inside,5),
                     'required_inside_radius_mm':minimum,'closest_bodies':sorted(crossings,key=lambda x:x['remaining_clearance_mm'])[:12]})
    distances=[]
    for i,a in enumerate(harness['routes']):
        for b in harness['routes'][i+1:]:
            if a['group']!='bms-power' and b['group']!='bms-power':continue
            distance=float(cKDTree(curves[a['name']]).query(curves[b['name']])[0].min())
            gap=distance-(a['wire_od_mm']+b['wire_od_mm'])/2-.4-.05-.016
            if gap<.5:failures.append(a['name']+' is too close to '+b['name'])
            # Separate guide bodies need their full enclosing radii. Guides
            # belonging to the same BMS carrier can share a wall.
            guide_gap=distance-(a['wire_od_mm']+b['wire_od_mm'])/2-1.1-.05-.016
            if a['group']!=b['group'] and guide_gap<.2:failures.append(a['name']+' guide is too close to '+b['name'])
            distances.append({'a':a['name'],'b':b['name'],'wire_surface_gap_after_allowances_mm':round(gap,5),
                              'guide_envelope_gap_mm':round(guide_gap,5)})
    if missing:failures.append('component heights remain unverified on the revised paths')
    return {'passed':not failures,'failures':failures,'BMS_routes':rows,
            'closest_wire_pairs':sorted(distances,key=lambda x:x['wire_surface_gap_after_allowances_mm'])[:8],
            'unverified_height_limits':missing,'assembly_reservations_used':sorted(set(assumptions)),
            'notes':['Courtyards are conservative body envelopes. Mounting hardware and dressed cable reservations need physical confirmation.',
                     'Body checks include 0.3 mm clearance, 0.2 mm positioning, 0.15 mm guide fit, 0.4 mm guide walls and 0.041 mm interpolation/sampling allowance.',
                     'CAD curvature is sampled at 10,000 parameter positions on the actual fitted wire edge.',
                     'Guide carriers, clamps, screws and the full case are checked separately in the case assembly.'],
            'physical_fit_verified':False,
            'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                ['mechanical/power-harness.json','mechanical/board-datums.json','mechanical/component-placement.json',
                 'mechanical/bms-connector-access.json','mechanical/bms-harness-routing.json']}}


if __name__=='__main__':
    result=check();out=ROOT/'mechanical/power-harness-checks.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','failures','BMS_routes','unverified_height_limits']},indent=2))
    raise SystemExit(0 if result['passed'] else 1)

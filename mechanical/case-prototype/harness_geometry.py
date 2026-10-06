"""Read-only harness adaptation and numerical checks in installed X,Y,+height.

The electronics curves are immutable inputs. A case variant may translate all
four boards together and lower only the USB front run. Recheck every resulting
curve; never inherit a pass flag after changing its geometry.
"""
import hashlib
import json
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree
from cad import HERE, ROOT
from case_inputs import path as input_path


def smooth(t):
    t=np.clip(t,0,1)
    return t*t*t*(10+t*(-15+6*t))


def bms_case_loop(route,radius,hump=0,rear_lead=2.5):
    """Experimental loop family; body, bend, length and separation checks apply."""
    import math
    a,b=[np.array(e['point'],float) for e in route['ends']]
    r=14;cx=b[0]-2*radius-r;cy=a[1]-r;top=b[1]-rear_lead
    def line(p,q):return np.linspace(p,q,max(2,math.ceil(np.linalg.norm(np.array(q)-p)/.025)+1))
    t=np.linspace(math.pi/2,0,1001)
    first=np.column_stack([cx+r*np.cos(t),cy+r*np.sin(t)])
    t=np.linspace(math.pi,2*math.pi,2001)
    turn=np.column_stack([b[0]-radius+radius*np.cos(t),top+radius*np.sin(t)])
    xy=np.vstack([line(a[:2],first[0])[:-1],first[:-1],line(first[-1],turn[0])[:-1],turn[:-1],line(turn[-1],b[:2])])
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
    z=a[2]+(b[2]-a[2])*smooth((s-2)/(s[-1]-4))
    z+=hump*smooth((s-2)/25)*(1-smooth((s-(s[-1]-24))/22))
    return np.column_stack([xy,z])


def paths(config):
    source=input_path('power-harness.json')
    data=json.loads(source.read_text())
    offsets={name:config['boards'][name]['bottom_height']+1.6-z
             for name,z in data['study_board_top_z'].items()}
    assert max(offsets.values())-min(offsets.values())<1e-6, 'independent board Z changes need a new harness'
    dz=next(iter(offsets.values()))
    rows=[]
    for route in data['routes']:
        changed_bms=route['group']=='bms-power' and config['cables'].get('bms_avoid_J2074',False)
        ground=route['name']=='bms-FG_VSS'
        p=bms_case_loop(route,config['cables'].get('bms_negative_radius',19.5) if ground else config['cables'].get('bms_positive_radius',19.5),config['cables'].get('bms_ground_hump',4) if ground else 0,config['cables'].get('bms_rear_lead',2.5)) if changed_bms else np.asarray(route['points'],float).copy()
        p[:,2]+=dz
        s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        if route['group']=='usb5':
            # Only the long front run is lowered. Rear crystal/crossover and
            # plug approaches keep their source heights. Smooth ramps are
            # deliberately longer than the wire's minimum bend radius.
            weight=smooth((p[:,0]-60)/45)*smooth((280-p[:,0])/45)*smooth((p[:,1]-90)/25)
            p[:,2]-=config['cables'].get('usb_front_drop',0)*weight
        curve=CubicSpline(s,p,axis=0)
        ss=np.linspace(0,s[-1],max(100,int(s[-1]/.025)+1))
        q=curve(ss);d1=curve(ss,1);d2=curve(ss,2)
        curvature=np.linalg.norm(np.cross(d1,d2),axis=1)/np.linalg.norm(d1,axis=1)**3
        radius=1/max(curvature.max(),1e-12);od=route['wire_od_mm']
        length=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum())
        hidden=4 if route['group']=='usb5' else 16
        low,high=(400,420) if route['group']=='usb5' else (20,120 if route['group']=='bms-power' else 100)
        ends=[]
        for e in route['ends']:
            e=dict(e);e['point']=list(e['point']);e['point'][2]+=dz;ends.append(e)
        unchanged=not changed_bms and (route['group']!='usb5' or config['cables'].get('usb_front_drop',0)==0)
        saved=p[::10] if changed_bms else p
        if not np.array_equal(saved[-1],p[-1]):saved=np.vstack([saved,p[-1]])
        rows.append({**route,'ends':ends,'points':saved.tolist(),
                     'exposed_length_mm':length,'nominal_cut_length_mm':round(length+hidden,1),
                     'minimum_inside_radius_mm':route['minimum_inside_radius_mm'] if unchanged else float(radius-od/2),
                     'minimum_centerline_radius_mm':route['minimum_centerline_radius_mm'] if unchanged else float(radius),
                     'bend_5d_pass':route['bend_5d_pass'] if unchanged else bool(radius-od/2>=5*od*1.01),
                     'bend_10d_pass':route['bend_10d_pass'] if unchanged else bool(radius-od/2>=10*od*1.01),
                     'bend_basis':'unchanged source curve under rigid Z translation' if unchanged else 'new dense spline derivative check',
                     'case_route_change':'case-specific turns around J2074 and perimeter hardware; see assembly.json for radii and ground lift' if changed_bms else None,
                     'sparse_interpolant_inside_radius_diagnostic_mm':float(radius-od/2),
                     'length_pass':bool(low<=length+hidden<=high),
                     'max_wire_height_mm':float(q[:,2].max()+od/2+.2),
                     'source_max_wire_height_mm':route['max_wire_height_mm'],
                     'sampling_error_bound_mm':.025})
    pairs=[]
    for i,a in enumerate(rows):
        pa=np.array(a['points']);sa=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pa,axis=0),axis=1))]
        aa=CubicSpline(sa,pa)(np.linspace(0,sa[-1],int(sa[-1]/.05)+1));tree=cKDTree(aa)
        for b in rows[i+1:]:
            pb=np.array(b['points']);sb=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pb,axis=0),axis=1))]
            bb=CubicSpline(sb,pb)(np.linspace(0,sb[-1],int(sb[-1]/.05)+1))
            d=float(tree.query(bb)[0].min())-(a['wire_od_mm']+b['wire_od_mm'])/2-.4-.05
            pairs.append({'a':a['name'],'b':b['name'],'surface_gap_after_position_and_sampling_mm':d,'pass':d>=.5})
    return {'source':'mechanical/power-harness.json','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'coordinate_frame':'installed X,Y,positive height H; STEP Z=-H',
            'uniform_height_change_mm':dz,'USB_front_drop_mm':config['cables'].get('usb_front_drop',0),
            'wire_position_allowance_mm':.2,'guide_fit_requires_physical_test':True,
            'all_bend_pass':all(r['bend_5d_pass'] for r in rows),
            'all_length_pass':all(r['length_pass'] for r in rows),
            'all_separation_pass':all(r['pass'] for r in pairs),
            'minimum_wire_separation_mm':min(r['surface_gap_after_position_and_sampling_mm'] for r in pairs),
            'routes':rows,'pairs':pairs,'terminals':data['terminals']}


if __name__=='__main__':
    from build import load_config
    c=load_config()
    report=[]
    for drop in [0,1,2,3,4,5]:
        c['cables']['usb_front_drop']=drop
        r=paths(c)
        report.append({'drop_mm':drop,**{k:v for k,v in r.items() if k.startswith('all_') or k=='minimum_wire_separation_mm'},
                       'USB':[{'name':p['name'],'height':p['max_wire_height_mm'],'inside_radius':p['minimum_inside_radius_mm'],'cut':p['nominal_cut_length_mm']} for p in r['routes'] if p['group']=='usb5']})
    (HERE/'harness-height-study.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

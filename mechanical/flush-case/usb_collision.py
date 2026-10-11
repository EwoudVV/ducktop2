"""Conservative cable bounds and local solid checks for the USB assembly."""
import json
from pathlib import Path
import cadquery as cq
import numpy as np

from cad import box
from component_heights import guide_samples
from review import bbox_overlap,intersection_volume
import build as baseline
import model_cache


class Checks:
    def __init__(self,parts,case,data,rigid):
        self.case=case;self.data=data
        self.routes={r['name']:r for r in data['routes']+data['other_routes']}
        self.gaps={frozenset([r['a'],r['b']]):r['gap_after_allowances_mm'] for r in data['pairs']}
        self.rigid={}
        for p in rigid:self.rigid.setdefault(p['name'],[]).append(p['shape'])
        self.parts={p['name']:p for p in parts};self.pieces={};self.envelopes={}
        self.old=json.loads((model_cache.CACHE/'model.json').read_text())
        assert self.old['geometry_inputs_sha256']==model_cache.geometry_inputs(),'baseline primitives are stale'
        self.dz=case['boards']['main_bottom_H']-baseline.CONFIG['boards']['center']['bottom_height']
        old_routes={r['name']:r for r in self.old['harness']['routes']}
        for route in data['other_routes']:
            old_points=np.array(old_routes[route['name']]['points']);old_points[:,2]+=self.dz
            if not np.allclose(old_points,np.array(route['points']),rtol=0,atol=1e-9):
                raise ValueError('retained guide differs from its source curve: '+route['name'])
        self.exact_checks=0;self.bound_rejections=0

    def envelope(self,name,guide,clip=None):
        key=(name,guide,clip)
        if key in self.envelopes:return self.envelopes[key]
        r=self.routes[name]
        settings={'sampling_step_mm':.05,'wire_position_allowance_mm':.2,'guide_curve_allowance_mm':.025}
        xyz,radius=guide_samples(r,baseline.CONFIG['cables'],settings,include_guide=guide)
        xyz=xyz*[1,-1,1]
        low=xyz-radius;high=xyz+radius
        if guide:
            outer=r['wire_od_mm']/2+.55
            # The C-profile opens upward from 45 to 135 degrees. Its highest
            # lips cannot exceed R/sqrt(2), even along an inclined wire.
            high[:,2]=xyz[:,2]+outer/np.sqrt(2)+(radius-outer)
        if clip is not None:
            mask=(high[:,0]>=clip[0])&(low[:,0]<=clip[1])
            low=low[mask];high=high[mask]
            low[:,0]=np.maximum(low[:,0],clip[0]);high[:,0]=np.minimum(high[:,0],clip[1])
        self.envelopes[key]=(low,high)
        return low,high

    def get_pieces(self,part):
        name=part['name']
        if name in self.pieces:return self.pieces[name]
        result=[]
        if part.get('power_wire'):
            result=[{'curve':part['wire_name'],'guide':False,'clip':None}]
        elif name in ['harness-USB-left-carrier','harness-USB-right-carrier']:
            clip=(0,179) if '-left-' in name else (179,429)
            result=[{'curve':r['name'],'guide':True,'clip':clip} for r in self.data['routes']]
            result += [{'shape':s,'subset':True} for s in self.rigid[name]]
        elif name in self.old.get('collision_primitives',{}) and part.get('integrated_from'):
            names=part['integrated_from'];count=sum('-guide' in n for n in names)
            routes=[r for r in self.data['other_routes'] if r['name']+'-guide' in names]
            if len(routes)!=count:raise ValueError('unrecognized guide primitive order: '+name)
            result=[{'curve':r['name'],'guide':True,'clip':None} for r in routes]
            files=self.old['collision_primitives'][name]
            for file in files[count:]:
                shape=cq.Shape.importBrep(str(model_cache.CACHE/file)).translate((0,0,self.dz))
                result.append({'shape':shape,'subset':False})
        elif name=='keyboard-carrier-reservation':
            result=[{'shape':box(41.25,19,20,275.5,82,1),'subset':False}]
            result += [{'shape':box(x-5,99,20,10,10,1),'subset':False} for x in [130,225]]
            if self.case.get('fan_harness'):
                import fan_harness
                result += [{'shape':s,'subset':True} for s in fan_harness.carrier_guide().Solids()]
        elif 'remote_pipe_offset' in part:
            # Keep the registered extrusion object instead of a new Solids()
            # wrapper, so its conservative planar bound remains available.
            result=[{'shape':part['shape'],'subset':True}]
        else:
            result=[{'shape':s,'subset':True} for s in part['shape'].Solids()]
        self.pieces[name]=result
        return result

    def curve_might_meet(self,piece,shape):
        lo,hi=self.envelope(piece['curve'],piece['guide'],piece['clip'])
        b=shape.BoundingBox();a=np.array([b.xmin,b.ymin,b.zmin]);z=np.array([b.xmax,b.ymax,b.zmax])
        mask=np.all((hi>a+.001)&(lo<z-.001),axis=1)
        if not mask.any():return False
        import remote_cooler
        plan=remote_cooler.planar_bound(shape)
        if plan is not None:
            from shapely import box as boxes,intersects
            lo,hi=lo[mask],hi[mask]
            return bool(np.any(intersects(plan,boxes(lo[:,0],-hi[:,1],hi[:,0],-lo[:,1]))))
        return True

    def volume(self,a,b):
        if not bbox_overlap(a['shape'],b['shape']):return 0
        for aa in self.get_pieces(a):
            for bb in self.get_pieces(b):
                if 'curve' in aa and 'curve' in bb:
                    key=frozenset([aa['curve'],bb['curve']])
                    if key not in self.gaps:raise ValueError('missing wire pair check')
                    extra=.55*(int(aa['guide'])+int(bb['guide']))
                    minimum=.3 if extra else .5
                    if self.gaps[key]-extra>=minimum:
                        self.bound_rejections+=1;continue
                elif 'curve' in aa:
                    if not self.curve_might_meet(aa,bb['shape']):
                        self.bound_rejections+=1;continue
                elif 'curve' in bb:
                    if not self.curve_might_meet(bb,aa['shape']):
                        self.bound_rejections+=1;continue
                else:
                    if not bbox_overlap(aa['shape'],bb['shape']):continue
                    v=intersection_volume(aa['shape'],bb['shape'])
                    if v<=.01:continue
                    if aa.get('subset') and bb.get('subset'):return v
                # A coarse hit is never a reported collision by itself. Confirm
                # it against the saved final part, preserving holes and reliefs.
                p=aa['shape'] if aa.get('subset') else a['shape']
                q=bb['shape'] if bb.get('subset') else b['shape']
                self.exact_checks+=1
                print('USB exact check:',a['name'],'/',b['name'],flush=True)
                v=intersection_volume(p,q)
                if v>.01:return v
        return 0

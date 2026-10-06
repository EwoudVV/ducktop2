"""BMS power-wire curves with straight terminal exits and a controlled rise."""
from pathlib import Path
import json
import math
import numpy as np
from scipy.interpolate import CubicSpline,make_interp_spline

ROOT=Path(__file__).resolve().parents[1]


def power_loop(a,b,net,step=.025):
    settings=json.loads((ROOT/'mechanical/bms-harness-routing.json').read_text())
    spec=settings['routes'][net]
    a,b=np.asarray(a,float),np.asarray(b,float)
    turn=spec['turn_radius_mm'];first=spec['first_radius_mm'];lead=spec['terminal_lead_mm']
    cx=b[0]-2*turn-first;cy=a[1]-first;top=b[1]-lead
    if cx<a[0]+2 or cy<top or lead<2:
        raise ValueError('BMS curve cannot keep the required straight terminal exits')
    if not math.isclose(b[2]-a[2],settings['bms_to_center_height_difference_mm'],abs_tol=1e-6):
        raise ValueError('BMS mounting height changed; recheck the cable geometry')
    def line(p,q):
        return np.linspace(p,q,max(2,math.ceil(np.linalg.norm(np.asarray(q)-p)/step)+1))
    t=np.linspace(math.pi/2,0,math.ceil(math.pi*first/2/step)+1)
    corner=np.column_stack([cx+first*np.cos(t),cy+first*np.sin(t)])
    t=np.linspace(math.pi,2*math.pi,math.ceil(math.pi*turn/step)+1)
    rear=np.column_stack([b[0]-turn+turn*np.cos(t),top+turn*np.sin(t)])
    xy=np.vstack([line(a[:2],corner[0])[:-1],corner[:-1],line(corner[-1],rear[0])[:-1],
                  rear[:-1],line(rear[-1],b[:2])])
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
    knots=[2,*[v*s[-1] for v in settings['height_knot_fractions']],s[-1]-2]
    heights=[a[2],*[a[2]+v for v in spec['height_above_start_mm']],b[2]]
    if spec.get('height_profile')=='quintic':
        # Zero slope and curvature at the straight ends prevent a sharp
        # compound bend when the height change meets the first plan turn.
        rise=make_interp_spline(knots,heights,k=5,bc_type=([(1,0),(2,0)],[(1,0),(2,0)]))
    else:
        rise=CubicSpline(knots,heights,bc_type=((1,0),(1,0)))
    return np.column_stack([xy,rise(np.clip(s,2,s[-1]-2))])

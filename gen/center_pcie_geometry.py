"""Exact line and circular-arc interval geometry for trace coupling checks."""
import math
import numpy as np
from shapely.geometry import Point,Polygon,box
TAU=2*math.pi

def merge(values):
 result=[]
 for low,high in sorted(values):
  if high-low<=1e-13:continue
  if result and low<=result[-1][1]+1e-12:result[-1][1]=max(result[-1][1],high)
  else:result.append([low,high])
 return result

def complement(values):
 result=[];at=0.
 for low,high in merge(values):
  if low>at+1e-12:result.append((at,low))
  at=max(at,high)
 if at<1.-1e-12:result.append((at,1.))
 return result

def intersection(a,b):return merge((max(x,z),min(y,w)) for x,y in a for z,w in b if max(x,z)<min(y,w))

class Curve:
 def __init__(self,item):
  self.item=item;self.a=np.asarray(item['start'],dtype=float);self.b=np.asarray(item['end'],dtype=float);self.arc=item['type']=='PCB_ARC';self.width=item['width']
  if self.arc:
   middle_point=np.asarray(item['mid'],dtype=float)
   self.center=np.asarray(item['center'],dtype=float)
   u=middle_point-self.a;v=self.b-self.a
   three_point_center=self.a+np.linalg.solve(2*np.asarray([u,v]),np.asarray([np.dot(u,u),np.dot(v,v)]))
   self.center_rounding=float(np.linalg.norm(self.center-three_point_center))
   self.rounding_uncertainty=2*self.center_rounding+.000001
   if self.rounding_uncertainty>.00015:raise ValueError('native arc center uncertainty exceeds 0.15 micrometre: '+item['id'])
   self.radius=float(np.linalg.norm(self.a-self.center));self.angle=math.atan2(*(self.a-self.center)[::-1]);end=math.atan2(*(self.b-self.center)[::-1]);middle=math.atan2(*(middle_point-self.center)[::-1]);self.span=(end-self.angle)%TAU
   if (middle-self.angle)%TAU>self.span:self.span-=TAU
   if abs(self.span)<1e-12 or self.radius<1e-9:raise ValueError('degenerate arc: '+item['id'])
   self.length=self.radius*abs(self.span)
   # KiCad computes radius from its native center and start. Its rounded
   # center can leave the stored end slightly off that circle. Preserve
   # both native endpoint caps and report the bounded radial discrepancy.
   self.endpoint_radial_error=abs(float(np.linalg.norm(self.b-self.center))-self.radius)
   if self.endpoint_radial_error>.0001:raise ValueError('native arc endpoint radial discrepancy exceeds 0.1 micrometre: '+item['id'])
   if 'length' in item and abs(self.length-item['length'])>.000005:raise ValueError('analytical arc length disagrees with native length by over 5 nm: '+item['id'])
  else:
   self.rounding_uncertainty=0.;self.center_rounding=0.;self.endpoint_radial_error=0.
   self.vector=self.b-self.a;self.length=float(np.linalg.norm(self.vector))
   if self.length<1e-12:raise ValueError('zero-length trace: '+item['id'])
 def point(self,t):
  if self.arc:
   angle=self.angle+t*self.span;return self.center+self.radius*np.asarray([math.cos(angle),math.sin(angle)])
  return self.a+t*self.vector
 def points(self,ts):
  if self.arc:
   angles=self.angle+np.asarray(ts)*self.span;return self.center+self.radius*np.stack([np.cos(angles),np.sin(angles)],axis=-1)
  return self.a+np.asarray(ts)[:,None]*self.vector
 def _angular_roots(self,a,b,c):
  amplitude=math.hypot(a,b)
  if amplitude<1e-20:return []
  ratio=-c/amplitude
  if ratio < -1.-1e-12 or ratio > 1.+1e-12:return []
  phase=math.atan2(b,a);offset=math.acos(max(-1.,min(1.,ratio)));out=[]
  lower,upper=sorted((self.angle,self.angle+self.span))
  for initial in [phase-offset,phase+offset]:
   first=math.floor((lower-initial)/TAU)-1;last=math.ceil((upper-initial)/TAU)+1
   for n in range(first,last+1):
    t=(initial+n*TAU-self.angle)/self.span
    if -1e-12<=t<=1.+1e-12:out.append(max(0.,min(1.,t)))
  return out
 def line_roots(self,normal,anchor,value=0.):
  normal=np.asarray(normal);anchor=np.asarray(anchor)
  if self.arc:return self._angular_roots(normal[0]*self.radius,normal[1]*self.radius,float(np.dot(normal,self.center-anchor))-value)
  slope=float(np.dot(normal,self.vector));initial=float(np.dot(normal,self.a-anchor))-value
  if abs(slope)<1e-20:return []
  t=-initial/slope
  return [max(0.,min(1.,t))] if -1e-12<=t<=1.+1e-12 else []
 def circle_roots(self,center,radius):
  center=np.asarray(center)
  if radius<0:return []
  if self.arc:
   delta=self.center-center
   return self._angular_roots(2*self.radius*delta[0],2*self.radius*delta[1],self.radius*self.radius+float(np.dot(delta,delta))-radius*radius)
  delta=self.a-center;aa=float(np.dot(self.vector,self.vector));bb=2*float(np.dot(delta,self.vector));cc=float(np.dot(delta,delta))-radius*radius;disc=bb*bb-4*aa*cc
  if disc < -1e-12:return []
  root=math.sqrt(max(0.,disc));out=[]
  for t in [(-bb-root)/(2*aa),(-bb+root)/(2*aa)]:
   if -1e-12<=t<=1.+1e-12:out.append(max(0.,min(1.,t)))
  return out
 def distances(self,points):
  points=np.asarray(points)
  if self.arc:
   vectors=points-self.center;angles=np.arctan2(vectors[:,1],vectors[:,0]);progress=(angles-self.angle)%TAU if self.span>0 else (self.angle-angles)%TAU;inside=progress<=abs(self.span)+1e-12
   radial=np.abs(np.linalg.norm(vectors,axis=1)-self.radius);endpoints=np.minimum(np.linalg.norm(points-self.a,axis=1),np.linalg.norm(points-self.b,axis=1));return np.where(inside,np.minimum(radial,endpoints),endpoints)
  projection=np.clip(((points-self.a)@self.vector)/float(np.dot(self.vector,self.vector)),0.,1.);nearest=self.a+projection[:,None]*self.vector;return np.linalg.norm(points-nearest,axis=1)
 def capsule_coverage(self,other,radius):
  boundaries=[0.,1.]
  if other.arc:
   boundaries+=self.circle_roots(other.center,other.radius+radius)
   if other.radius>radius:boundaries+=self.circle_roots(other.center,other.radius-radius)
   for angle in [other.angle,other.angle+other.span]:boundaries+=self.line_roots([-math.sin(angle),math.cos(angle)],other.center)
  else:
   vector=other.vector;length2=float(np.dot(vector,vector));normal=np.asarray([-vector[1],vector[0]])
   boundaries+=self.line_roots(vector,other.a,0.)+self.line_roots(vector,other.a,length2)
   boundaries+=self.line_roots(normal,other.a,-radius*other.length)+self.line_roots(normal,other.a,radius*other.length)
  for end in [other.a,other.b]:boundaries+=self.circle_roots(end,radius)
  cuts=sorted(set(round(x,14) for x in boundaries));out=[]
  for low,high in zip(cuts,cuts[1:]):
   if high-low>1e-13 and other.distances(self.points([(low+high)/2]))[0]<=radius+1e-11:out.append((low,high))
  return merge(out)
 def inside(self,polygon):
  boundaries=[0.,1.];rings=[polygon.exterior]+list(polygon.interiors)
  for ring in rings:
   coords=list(ring.coords)
   for a,b in zip(coords,coords[1:]):
    vector=np.asarray(b)-a;boundaries+=self.line_roots([-vector[1],vector[0]],a)
  cuts=sorted(set(round(x,14) for x in boundaries));return merge((low,high) for low,high in zip(cuts,cuts[1:]) if high-low>1e-13 and polygon.covers(Point(self.point((low+high)/2))))

def gap_measure(curve,others,low,high,step):
 length=(high-low)*curve.length;n=max(1,math.ceil(length/step));points=curve.points(low+(np.arange(n)+.5)*(high-low)/n);gap=np.full(n,np.inf)
 for other in others:gap=np.minimum(gap,other.distances(points)-(curve.width+other.width)/2)
 sampled=float(gap.max());return sampled,sampled+length/n/2

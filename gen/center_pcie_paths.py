"""Complete PCIe signal paths, including both sides of series parts."""
from pathlib import Path
import math,heapq,collections
from shapely.geometry import Point,LineString,box
from shapely.ops import nearest_points,substring
def line(t):
 if t['type']!='PCB_ARC':return LineString([t['start'],t['end']])
 cx,cy=t['center'];a=math.atan2(t['start'][1]-cy,t['start'][0]-cx);e=math.atan2(t['end'][1]-cy,t['end'][0]-cx);m=math.atan2(t['mid'][1]-cy,t['mid'][0]-cx);s=(e-a)%(2*math.pi)
 if (m-a)%(2*math.pi)>s:s-=2*math.pi
 r=math.dist(t['start'],t['center']);n=max(8,math.ceil(t['length']/.002));pts=[[cx+r*math.cos(a+s*j/n),cy+r*math.sin(a+s*j/n)] for j in range(n+1)];pts[0]=t['start'];pts[-1]=t['end'];return LineString(pts)
def endpoints(g):
 if g.is_empty:return []
 if g.geom_type=='Point':return [g]
 if g.geom_type=='LineString':return [Point(g.coords[0]),Point(g.coords[-1])]
 return [p for sub in g.geoms for p in endpoints(sub)] if hasattr(g,'geoms') else []
def shortest(adj,start,end):
 dist={start:0.};prev={};q=[(0.,start)]
 while q:
  weight,node=heapq.heappop(q)
  if weight>dist[node]+1e-10:continue
  if node==end:break
  for other,w,e in adj[node]:
   value=weight+w
   if value+1e-10<dist.get(other,float('inf')):dist[other]=value;prev[other]=(node,e);heapq.heappush(q,(value,other))
 if end not in dist:return None
 result=[];node=end
 while node!=start:node,e=prev[node];result.append(e)
 return {'length':dist[end],'edges':list(reversed(result))}

def check_paths(data,definitions):
 nets=sorted({net for pair in definitions for pol in ['P','N'] for net in pair['nets'][pol]})
 items=[v for v in data['items'] if v['net'] in nets]
 expected={net:ends for pair in definitions for net,ends in pair['endpoints'].items()}
 for net in nets:
  actual=sorted(v['ref']+'.'+v['number'] for v in items if v['net']==net and v['type']=='PAD')
  if actual!=sorted(expected[net]):return {'status':'failed','scope':'complete PCIe signal paths','blocking_findings':[{'kind':'wrong_endpoints','net':net,'actual':actual,'expected':expected[net]}]}
 results={};all_overlaps=[];offpath=[];gap_contacts=[]
 for net in nets:
  selected={t['id']:t for t in items if t['net']==net};tracks={k:t for k,t in selected.items() if t['type'] in ('PCB_TRACK','PCB_ARC')};pads={k:t for k,t in selected.items() if t['type']=='PAD'};vias={k:t for k,t in selected.items() if t['type']=='PCB_VIA'}
  assert len(pads)==2,(net,'unexpected endpoint count',[(t['ref'],t['number']) for t in pads.values()])
  geometry={k:line(t) for k,t in tracks.items()};cuts={k:{0.,round(g.length,9)} for k,g in geometry.items()};joins=[];contacts=[];overlaps=[]
  def ontrack(key,point):
   x=max(0.,min(geometry[key].length,geometry[key].project(point)));x=round(x,9);cuts[key].add(x);return ('T',key,x)
  def join(a,b,weight,kind,**extra):return {'a':a,'b':b,'weight':weight,'kind':kind,**extra}
  keys=list(tracks)
  for i,key in enumerate(keys):
   t=tracks[key];g=geometry[key]
   for key2 in keys[i+1:]:
    u=tracks[key2]
    if t['layers']!=u['layers']:continue
    h=geometry[key2];intersection=g.intersection(h)
    if not intersection.is_empty:
     for pt in endpoints(intersection):joins.append(join(ontrack(key,pt),ontrack(key2,pt),0.,'centerline-junction'))
     if intersection.length>2e-6:overlaps.append({'net':net,'first':key,'second':key2,'length':intersection.length,'bounds':list(intersection.bounds),'layer':t['layers'][0]})
    elif key2 in t['neighbors'] or key in u['neighbors']:
     a,b=nearest_points(g,h);distance=a.distance(b)
     record=join(ontrack(key,a),ontrack(key2,b),distance,'copper-contact',first=key,second=key2)
     if distance<=2e-6:joins.append(record)
     else:contacts.append(record)
   for key2 in t['neighbors']:
    if key2 in pads:
     q=Point(pads[key2]['start']);proj=g.interpolate(g.project(q));joins.append(join(ontrack(key,proj),('P',key2,0.),q.distance(proj),'pad-approach'))
    elif key2 in vias:
     q=Point(vias[key2]['start']);proj=g.interpolate(g.project(q));joins.append(join(ontrack(key,proj),('V',key2,t['layers'][0]),q.distance(proj),'via-approach'))
  for key,v in vias.items():
   layers=sorted({tracks[k]['layers'][0] for k in v['neighbors'] if k in tracks})
   for a,b in zip(layers,layers[1:]):joins.append(join(('V',key,a),('V',key,b),0.,'layer-transition',via=key,layers=[a,b]))
  edges=[]
  for key,distances in cuts.items():
   order=sorted(distances)
   for a,b in zip(order,order[1:]):
    if b-a>1e-9:edges.append(join(('T',key,a),('T',key,b),(b-a)*tracks[key]['length']/geometry[key].length,'trace',track=key,layer=tracks[key]['layers'][0],distances=[a,b]))
  edges+=joins
  def adjacency(extra):
   adj=collections.defaultdict(list)
   for edge in edges+extra:
    a,b=edge['a'],edge['b'];adj[a].append((b,edge['weight'],edge));adj[b].append((a,edge['weight'],edge))
   return adj
  primary=adjacency([]);physical=adjacency(contacts);ends=list(pads.values());start,end=('P',ends[0]['id'],0.),('P',ends[1]['id'],0.)
  main=shortest(primary,start,end);contact_path=shortest(physical,start,end)
  native_connected=ends[1]['id'] in ends[0]['native_component_pad_ids']
  assert native_connected==bool(contact_path),(net,'graph and native disagree')
  chosen=main or contact_path;used={}
  if chosen:
   for e in chosen['edges']:
    if e['kind']=='trace':used.setdefault(e['track'],[]).append(tuple(e['distances']))
  landing=[box(*q['box']) for q in pads.values()]+[Point(v['start']).buffer(v['width']/2+2e-6) for v in vias.values()]
  residual=[]
  for e in edges:
   if e['kind']!='trace' or tuple(e['distances']) in used.get(e['track'],[]):continue
   geom=substring(geometry[e['track']],*e['distances']);inside=any(g.buffer(tracks[e['track']]['width']/2+2e-6).covers(geom) for g in landing)
   if e['weight']>5e-6:residual.append({'track':e['track'],'length':e['weight'],'layer':e['layer'],'inside_pad_or_via_envelope':inside,'bounds':list(geom.bounds)})
  suspicious=[]
  for e in contacts:
   route=shortest(primary,e['a'],e['b']);excess=route['length']-e['weight'] if route else None
   if excess is None or excess>.1:suspicious.append({'first':e['first'],'second':e['second'],'centerline_separation':e['weight'],'nominal_detour':excess})
  def compact(path):
   if path is None:return None
   lengths=collections.defaultdict(float)
   for e in path['edges']:
    if e['kind']=='trace':lengths[e['layer']]+=e['weight']
   return {'planar_length_mm':path['length'],'trace_length_by_layer':dict(lengths),'pad_and_via_approach_mm':sum(e['weight'] for e in path['edges'] if e['kind'] in ('pad-approach','via-approach')),'via_transitions':[{'via':e['via'],'layers':e['layers']} for e in path['edges'] if e['kind']=='layer-transition'],'used_copper_contacts':[{'first':e['first'],'second':e['second'],'length':e['weight']} for e in path['edges'] if e['kind']=='copper-contact']}
  result={'endpoints':[{'id':q['id'],'ref':q['ref'],'number':q['number'],'position':q['start']} for q in ends],'native_connected':native_connected,'nominal_centerline_path':compact(main),'copper_contact_path':compact(contact_path),'assigned_trace_length_mm':sum(t['length'] for t in tracks.values()),'overlapping_centerlines':overlaps,'off_path_trace_parts':residual,'nonlocal_copper_contacts':suspicious,'via_count':len(vias),'widths_by_layer':{layer:sorted({t['width'] for t in tracks.values() if t['layers'][0]==layer}) for layer in sorted({t['layers'][0] for t in tracks.values()})}}
  results[net]=result;all_overlaps+=overlaps;offpath += [dict(net=net,**v) for v in residual if not v['inside_pad_or_via_envelope']];gap_contacts += [dict(net=net,**v) for v in suspicious]

 rows=[];errors=[]
 for pair in definitions:
  row={'name':pair['name'],'limit_mm':pair['max_pn_difference_mm']}
  for method in ['nominal_centerline_path','copper_contact_path']:
   lengths={};transitions={}
   for pol in ['P','N']:
    paths=[results[net][method] for net in pair['nets'][pol]]
    lengths[pol]=sum(q['planar_length_mm'] for q in paths) if all(paths) else None
    transitions[pol]=[e for q in paths if q for e in q['via_transitions']]
   difference=abs(lengths['P']-lengths['N']) if all(x is not None for x in lengths.values()) else None
   row[method]={'lengths_mm':lengths,'difference_mm':difference,'via_transition_counts':{pol:len(v) for pol,v in transitions.items()}}
   if difference is None:errors.append({'kind':'incomplete_signal_path','signal':pair['name'],'method':method})
   elif difference>pair['max_pn_difference_mm']:errors.append({'kind':'signal_skew','signal':pair['name'],'method':method,'actual_mm':difference,'limit_mm':pair['max_pn_difference_mm']})
   if any(len(v)!=pair['via_transition_count'] for v in transitions.values()):errors.append({'kind':'via_transition_count','signal':pair['name'],'method':method,'actual':row[method]['via_transition_counts'],'expected':pair['via_transition_count']})
  if pair.get('post_cap_nets'):
   local={}
   for pol,net in pair['post_cap_nets'].items():
    path=results[net]['copper_contact_path']
    if path:
     depth=data.get('board_thickness_mm',1.6);length=path['planar_length_mm']+len(path['via_transitions'])*depth;local[pol]={'planar_plus_nominal_via_mm':length,'via_depth_mm':depth}
     if length>pair['max_post_cap_path_with_via_mm']:errors.append({'kind':'post_cap_path_length','signal':pair['name'],'polarity':pol,'actual_mm':length,'limit_mm':pair['max_post_cap_path_with_via_mm']})
   row['post_cap_paths']=local
  rows.append(row)
 errors += [dict(kind='duplicate_copper',**v) for v in all_overlaps]
 errors += [dict(kind='free_branch_or_stub',**v) for v in offpath]
 errors += [dict(kind='nonlocal_copper_contact',**v) for v in gap_contacts]
 return {'status':'passed' if not errors else 'failed','scope':'complete PCIe signal paths','candidate_sha256':data['source_sha256'],'blocking_findings':errors,'signals':rows,'net_paths':results,'measurement_note':'Native pad connectivity is checked before measuring the complete path through each capacitor or zero-ohm resistor. The noded centerline and copper-contact paths are both measured. Equal package pad spans and equal used via depths cancel in P/N skew; this is not a measured electrical delay. Arc path edges use the native arc length, with at most 2 micrometre chord spacing to locate local junctions.'}

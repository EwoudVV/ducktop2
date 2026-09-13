#!/usr/bin/env python3
"""Check the center board's PCIe layout limits without changing the board."""
from pathlib import Path
import argparse,hashlib,json,math,os,shutil,subprocess,sys,collections
DEPENDENCY_ERROR=None
try:
 import numpy as np
 from shapely.geometry import LineString,Polygon,Point,box
 from shapely.ops import unary_union
 import shapely
except ImportError as error:
 DEPENDENCY_ERROR=str(error)
ROOT=Path(__file__).resolve().parents[1]
def cross(a,b):return float(a[0]*b[1]-a[1]*b[0])
def polygon(r):return Polygon(r['polygon_mm']) if 'polygon_mm' in r else box(*r['bounds_mm'])
def automatic_corners(tracks,nominal,tolerance):
 result=[]
 for net in sorted({v['net'] for v in tracks}):
  stem=net[:-2];opp=stem+('_N' if net.endswith('_P') else '_P')
  for layer in sorted({t['layers'][0] for t in tracks if t['net']==net}):
   own=[t for t in tracks if t['net']==net and t['layers']==[layer]];others=[t for t in tracks if t['net']==opp and t['layers']==[layer]];joints=collections.defaultdict(list)
   for t in own:
    for end,other in [(t['start'],t['end']),(t['end'],t['start'])]:joints[tuple(end)].append((t,np.asarray(other)-end))
   for at,joined in joints.items():
    if len(joined)!=2 or any(np.linalg.norm(v)<1e-10 for _,v in joined):continue
    directions=[v/np.linalg.norm(v) for _,v in joined]
    bend=math.pi-math.acos(max(-1.,min(1.,float(np.dot(*directions)))))
    if bend<1e-5 or bend>math.pi/2+2e-5:continue
    matching=[]
    for t,u in joined:
     uu=u/np.linalg.norm(u);valid=[]
     for n in others:
      vv=np.asarray(n['end'])-n['start'];vv=vv/np.linalg.norm(vv)
      if abs(cross(uu,vv))>2e-5:continue
      gap=abs(cross(uu,np.asarray(n['start'])-at))-(t['width']+n['width'])/2
      # Reject remote parallel lines: matching projection must reach this
      # corner neighborhood, not merely lie on the same infinite line.
      if abs(gap-nominal)<=tolerance and LineString([n['start'],n['end']]).distance(Point(at))<2*(nominal+t['width']):valid.append({'id':n['id'],'gap_mm':gap})
     matching.append(valid)
    if not all(matching):continue
    width=joined[0][0]['width'];pitch=nominal+width;radius=pitch*math.tan(bend/2)+.008
    result.append({'name':f'paired corner {net} {at[0]:.6f},{at[1]:.6f}','category':'paired_corner','stem':stem,'layer':layer,'bounds_mm':[at[0]-radius,at[1]-radius,at[0]+radius,at[1]+radius],'own_tracks':[t['id'] for t,_ in joined],'matching_parallel_tracks':matching,'bend_degrees':math.degrees(bend),'max_nearest_gap_mm':pitch/math.cos(bend/2)-width+.00001,'max_total_length_mm':{'P':4*radius,'N':4*radius},'max_uncoupled_length_mm':{'P':4*radius,'N':4*radius},'automatic_corner_radius_mm':radius})
 return result

def measure_max(part,width,others,step):
 if not others:return float('inf'),float('inf')
 n=max(1,math.ceil(part.length/step));coords=np.asarray([part.interpolate((i+.5)*part.length/n).coords[0] for i in range(n)]);points=shapely.points(coords)
 bywidth=collections.defaultdict(list)
 for t in others:bywidth[t['width']].append(LineString([t['start'],t['end']]))
 gaps=np.full(n,np.inf)
 for w,lines in bywidth.items():gaps=np.minimum(gaps,shapely.distance(points,unary_union(lines))-(width+w)/2)
 sampled=float(gaps.max());return sampled,sampled+part.length/n/2

def check(data,spec):
 from center_pcie_geometry import Curve,merge as curve_merge,complement,intersection,gap_measure
 assert spec['schema_version']==1;stems={v['stem'] for v in spec['pairs']};items=[v for v in data['items'] if v['net'][:-2] in stems];tracks=[v for v in items if v['type'] in ('PCB_TRACK','PCB_ARC')];errors=[];curves={}
 for t in tracks:
  try:curves[t['id']]=Curve(t)
  except (ValueError,KeyError,np.linalg.LinAlgError) as error:errors.append({'kind':'invalid_curve','id':t['id'],'reason':str(error)})
 if len(curves)!=len(tracks):return {'status':'failed','candidate_sha256':data['source_sha256'],'scope':spec['scope'],'blocking_findings':errors,'outside_region_uncoupled':[],'region_measurements':[],'minimum_gaps':[]}
 nominal=spec['nominal_gap_mm'];tol=spec['maximum_rounding_tolerance_mm'];regions=list(spec['regions']);corners=automatic_corners([t for t in tracks if t['type']=='PCB_TRACK'],nominal,spec['paired_corner_leg_tolerance_mm']);regions+=corners
 bystem={v['stem']:v for v in spec['pairs']};summaries={r['name']:{'P':{'length_mm':0.,'uncoupled_length_mm':0.},'N':{'length_mm':0.,'uncoupled_length_mm':0.},'maximum_nearest_gap_sample_mm':0.,'maximum_nearest_gap_upper_bound_mm':0.} for r in regions};outside=[];minimums=[]
 for stem in sorted(stems):
  allowed=bystem[stem]['widths_by_layer']
  for pol in ['P','N']:
   if not any(t['net']==stem+'_'+pol for t in tracks):errors.append({'kind':'missing_polarity','net':stem+'_'+pol})
  for t in tracks:
   if t['net'][:-2]!=stem:continue
   if len(t['layers'])!=1 or t['layers'][0] not in allowed or min(abs(t['width']-x) for x in allowed.get(t['layers'][0],[float('inf')]))>.000001:errors.append({'kind':'width_or_layer','id':t['id'],'net':t['net'],'layers':t['layers'],'width':t['width']})
  for layer in sorted({t['layers'][0] for t in tracks if t['net'][:-2]==stem}):
   rs=[r for r in regions if r['stem']==stem and r['layer']==layer];both={pol:[curves[t['id']] for t in tracks if t['net']==stem+'_'+pol and t['layers']==[layer]] for pol in ['P','N']};minimum_count=0
   for a in both['P']:
    for b in both['N']:
     close=a.capsule_coverage(b,nominal-spec['paired_corner_leg_tolerance_mm']-a.rounding_uncertainty-b.rounding_uncertainty+(a.width+b.width)/2)
     if sum(high-low for low,high in close)*a.length>spec['outside_uncoupled_rounding_length_mm']:
      errors.append({'kind':'minimum_gap','stem':stem,'layer':layer,'items':[a.item['id'],b.item['id']],'below_minimum_length_mm':sum(high-low for low,high in close)*a.length});minimum_count+=1
   minimums.append({'stem':stem,'layer':layer,'minimum_gap_floor_mm':nominal-spec['paired_corner_leg_tolerance_mm'],'below_minimum_pairs':minimum_count,'method':'exact line/circular-arc capsule intersections'})
   for pol,opp in [('P','N'),('N','P')]:
    others=both[opp]
    for curve in both[pol]:
     coverage=[]
     for other in others:coverage+=curve.capsule_coverage(other,nominal+tol+curve.rounding_uncertainty+other.rounding_uncertainty+(curve.width+other.width)/2)
     uncoupled=complement(coverage);inside=[];portions=[]
     for r in rs:
      clipped=curve.inside(polygon(r));inside+=clipped;portions.extend((r,low,high) for low,high in clipped)
     portions.extend((None,low,high) for low,high in complement(inside))
     for r,low,high in portions:
      intervals=intersection(uncoupled,[(low,high)]);length=sum(b-a for a,b in intervals)*curve.length
      if r:
       row=summaries[r['name']];row[pol]['length_mm']+=(high-low)*curve.length;row[pol]['uncoupled_length_mm']+=length;sampled,upper=gap_measure(curve,others,low,high,spec['maximum_sample_step_mm']);row['maximum_nearest_gap_sample_mm']=max(row['maximum_nearest_gap_sample_mm'],sampled);row['maximum_nearest_gap_upper_bound_mm']=max(row['maximum_nearest_gap_upper_bound_mm'],upper)
      elif length>spec['outside_uncoupled_rounding_length_mm']:
       outside.append({'net':curve.item['net'],'layer':layer,'track':curve.item['id'],'type':curve.item['type'],'length_mm':length,'pieces_mm':[[curve.point(a).tolist(),curve.point((a+b)/2).tolist(),curve.point(b).tolist()] for a,b in intervals]})
 for r in regions:
  row=summaries[r['name']]
  for pol in ['P','N']:
   for measured,bound in [('length_mm','max_total_length_mm'),('uncoupled_length_mm','max_uncoupled_length_mm')]:
    if row[pol][measured]>r[bound][pol]+1e-8:errors.append({'kind':'region_length','region':r['name'],'polarity':pol,'measurement':measured,'actual_mm':row[pol][measured],'limit_mm':r[bound][pol]})
  margin=spec['maximum_sample_step_mm']/2 if r['category'] in ('paired_corner','paired_45_corner') else 0.
  if row['maximum_nearest_gap_upper_bound_mm']>r['max_nearest_gap_mm']+margin+1e-8:errors.append({'kind':'region_maximum_gap','region':r['name'],'upper_bound_mm':row['maximum_nearest_gap_upper_bound_mm'],'limit_mm':r['max_nearest_gap_mm']})
 errors += [dict(kind='outside_region_uncoupled',**v) for v in outside]
 return {'status':'passed' if not errors else 'failed','candidate_sha256':data['source_sha256'],'scope':spec['scope'],'blocking_findings':errors,'outside_region_uncoupled':outside,'region_measurements':[dict(region=r,measurements=summaries[r['name']]) for r in regions],'minimum_gaps':minimums,'exact_circular_arc_count':sum(c.arc for c in curves.values()),'arc_rounding':[{'id':c.item['id'],'center_rounding_mm':c.center_rounding,'endpoint_radial_error_mm':c.endpoint_radial_error,'gap_uncertainty_mm':c.rounding_uncertainty} for c in curves.values() if c.arc],'method':'Exact line and native circular-arc clipping. Capsule interval boundaries are solved analytically against lines, circles and arc-sector edges; the intervals determine uncoupled lengths without tessellation. Maximum nearest-copper distance has a conservative Lipschitz upper bound from samples at most 5 micrometres apart. A long object crossing a local area is still checked everywhere outside it.'}

def file_sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def native_python(explicit=None):
 candidates=[explicit,os.environ.get('KICAD_PYTHON'),sys.executable,shutil.which('python3')]
 candidates += [str(p) for p in Path('/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions').glob('*/bin/python3')]
 for candidate in dict.fromkeys(v for v in candidates if v):
  result=subprocess.run([candidate,'-c','import pcbnew'],capture_output=True,timeout=15)
  if result.returncode==0:return candidate
 raise RuntimeError('KiCad Python was not found; set KICAD_PYTHON or pass --kicad-python')

def export_board(pcb,stems,python=None):
 before=file_sha(pcb)
 code=r'''import sys,json,hashlib,wx
app=wx.App(False);wx.Log.EnableLogging(False)
import pcbnew as p
path=sys.argv[1];stems=set(json.loads(sys.argv[2]));b=p.LoadBoard(path)
if b is None:raise RuntimeError('could not load board')
b.BuildConnectivity();c=b.GetConnectivity();xy=lambda v:[v.x/1e6,v.y/1e6];uid=lambda v:v.m_Uuid.AsString();wanted=lambda n:n.endswith(('_P','_N')) and n[:-2] in stems
allpads={uid(q):q for f in b.GetFootprints() for q in f.Pads()};items=[];enabled=set(b.GetEnabledLayers().Seq())
for t in b.GetTracks():
 if not wanted(t.GetNetname()):continue
 via=isinstance(t,p.PCB_VIA);row={'id':uid(t),'type':t.GetClass(),'net':t.GetNetname(),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':(t.GetWidth(t.GetLayer()) if via else t.GetWidth())/1e6,'layers':[b.GetLayerName(l) for l in t.GetLayerSet().Seq() if l in enabled and b.GetLayerName(l).endswith('.Cu')],'length':t.GetLength()/1e6,'neighbors':sorted({uid(q) for q in list(c.GetConnectedTracks(t))+list(c.GetConnectedPads(t))})}
 if via:row['drill']=t.GetDrillValue()/1e6
 if isinstance(t,p.PCB_ARC):row.update(center=xy(t.GetCenter()),mid=xy(t.GetMid()),angle=t.GetAngle().AsDegrees())
 items.append(row)
for f in b.GetFootprints():
 for q in f.Pads():
  if not wanted(q.GetNetname()):continue
  rect=q.GetBoundingBox();component={uid(i) for i in c.GetConnectedItems(q)}
  items.append({'id':uid(q),'type':'PAD','ref':f.GetReference(),'number':q.GetNumber(),'net':q.GetNetname(),'start':xy(q.GetPosition()),'end':xy(q.GetPosition()),'size':xy(q.GetSize()),'angle':q.GetOrientationDegrees(),'layers':[b.GetLayerName(l) for l in q.GetLayerSet().Seq() if l in enabled and b.GetLayerName(l).endswith('.Cu')],'length':0,'native_component_pad_ids':sorted(k for k in component if k in allpads),'neighbors':sorted({uid(i) for i in list(c.GetConnectedTracks(q))+list(c.GetConnectedPads(q))}),'box':[rect.GetLeft()/1e6,rect.GetTop()/1e6,rect.GetRight()/1e6,rect.GetBottom()/1e6]})
print(json.dumps({'source':path,'source_sha256':hashlib.sha256(open(path,'rb').read()).hexdigest(),'copper_layers':b.GetCopperLayerCount(),'board_thickness_mm':b.GetDesignSettings().GetBoardThickness()/1e6,'items':items}))
'''
 command=[python or native_python(),'-c',code,str(pcb),json.dumps(sorted(stems))]
 if sys.platform=='darwin':command+=['-ApplePersistenceIgnoreState','YES']
 result=subprocess.run(command,capture_output=True,text=True,timeout=120)
 if result.returncode:raise RuntimeError('native PCB export failed: '+result.stderr.strip()[-2000:])
 data=json.loads(result.stdout.strip().splitlines()[-1])
 if file_sha(pcb)!=before or data['source_sha256']!=before:raise RuntimeError('board changed during read-only export')
 return data

def run_checks(data,limits):
 if limits.get('schema_version')!=1 or not isinstance(limits.get('suites'),list) or not limits['suites']:raise ValueError('limits need schema_version1 and a nonempty suites list')
 results=[check(data,suite) for suite in limits['suites']]
 if limits.get('signal_paths'):
  from center_pcie_paths import check_paths
  results.append(check_paths(data,limits['signal_paths']))
 return {'status':'passed' if all(r['status']=='passed' for r in results) else 'failed','candidate_sha256':data['source_sha256'],'suites':results,'scope':'center PCIe coupling and complete signal paths; native DRC remains a separate required release gate'}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pcb',type=Path);parser.add_argument('--native-json',type=Path);parser.add_argument('--limits',type=Path,default=ROOT/'manufacturing/center_pcie_layout_limits.json');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--kicad-python');args=parser.parse_args()
 try:
  if DEPENDENCY_ERROR:raise RuntimeError('missing geometry dependency: '+DEPENDENCY_ERROR+'; install gen/requirements-release.txt')
  limits=json.loads(args.limits.read_text());suites=limits.get('suites',[])
  if not suites:raise ValueError('limits contain no suites')
  if args.native_json:
   data=json.loads(args.native_json.read_text())
   if args.pcb and data.get('source_sha256')!=file_sha(args.pcb):raise ValueError('native export is not from the specified PCB')
  elif args.pcb:
   stems={p['stem'] for suite in suites for p in suite['pairs']};data=export_board(args.pcb.resolve(),stems,native_python(args.kicad_python))
  else:raise ValueError('pass --pcb or --native-json')
  result=run_checks(data,limits);result['limits_sha256']=file_sha(args.limits)
  result['exact_pcb_path']=str(args.pcb.resolve()) if args.pcb else data.get('source');code=0 if result['status']=='passed' else 1
 except Exception as error:
  result={'status':'failed','error':str(error),'candidate_sha256':file_sha(args.pcb) if args.pcb and args.pcb.exists() else None,'limits_sha256':file_sha(args.limits) if args.limits.exists() else None,'suites':[]};code=2
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'candidate_sha256':result.get('candidate_sha256'),'suites':len(result['suites']),'error':result.get('error')},indent=2));return code
if __name__=='__main__':raise SystemExit(main())

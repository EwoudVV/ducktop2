#!/usr/bin/env python3
"""Check source geometry, adapter contacts and a sampled unloaded hinge sweep."""
import json
import math
import cadquery as cq
from cad import HERE, compound, bounds
import hinges


def main():
    report={'units':'mm','scope':'CAD fit only; no material, torque or physical qualification','sides':{}}
    for side,x in [('left',30),('right',328)]:
        h=75;y=-10
        base,bolts=hinges.base_plate(side,x,y,h)
        lid,seats,lb=hinges.lid_plate(side,x,y,h)
        assert base.isValid() and lid.isValid() and all(s.isValid() for s in seats)
        seat=h+hinges.BASE_SEAT[side]
        # Seat must be the OEM flat foot, not the lowest rivet or bent transition.
        foot=hinges.parts(side,x,y,h,105)[4]['shape']
        for hx,hy in hinges.base_holes(side,x,y):
            ring=cq.Solid.makeCylinder(2.0,12,cq.Vector(hx,-hy,h-7))
            bb=foot.intersect(ring).BoundingBox()
            assert abs(bb.zmin-seat)<1e-5 and abs(bb.zmax-seat-1)<1e-5
        holes=hinges.lid_holes(side,x,y)
        closed=compound(t['shape'] for t in hinges.parts(side,x,y,h,0)[:3])
        for hx,hy,level,diam,thread,old,new in holes:
            r=2.4 if thread=='M2' else 1.45
            bb=closed.intersect(cq.Solid.makeCylinder(r,20,cq.Vector(hx,-hy,h))).BoundingBox()
            assert abs(bb.zmax-h-level)<1e-5
        clashes=[]; max_volume=0
        for angle in range(0,181,5):
            hp=hinges.parts(side,x,y,h,angle)
            moving=compound(t['shape'] for t in hp[:3])
            lp=compound([lid,*seats]).rotate((0,-y,h),(1,-y,h),-angle)
            # OEM shaft contact is intentional. New adapters must not cut either half.
            checks=[base.intersect(compound(t['shape'] for t in hp)).Volume(),
                    lp.intersect(compound(t['shape'] for t in hp)).Volume(),
                    base.intersect(lp).Volume()]
            v=max(checks);max_volume=max(max_volume,v)
            if v>.01: clashes.append({'angle':angle,'overlap_mm3':v})
        assert not clashes,(side,clashes)
        head_clearance=min(math.dist(a,b)-(4.6+5.5)/2 for a in hinges.base_holes(side,x,y) for b in bolts)
        assert head_clearance>1
        report['sides'][side]={'valid_source_solids':len(hinges.raw(side)),
            'base_seat_below_axis':-hinges.BASE_SEAT[side], 'sampled_sweep_degrees':[0,180,5],
            'maximum_adapter_overlap_mm3':round(max_volume,9),'base_screw_head_edge_gap_mm':round(head_clearance,3),
            'source_and_adapter_seats_match':True,'physical_test_complete':False}
    files={}
    for path in (HERE/'exports/hinge-tests').glob('*.step'):
        s=cq.importers.importStep(str(path)).val()
        assert s.isValid(),path
        files[path.name]={'valid':True,'solids':len(s.Solids())}
    report['step_roundtrip']=files
    (HERE/'hinge-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

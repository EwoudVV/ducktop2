"""Keep the CSD17577Q3A DNH lands and stencil tied to TI SLPS515A."""
import copy
import json
import math
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
FP=ROOT/'ducktop2.pretty/CSD17577Q3A_DNH.kicad_mod'

def parse(text):
    tokens=iter(re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+',text))
    def node(first):
        if first!='(':return json.loads(first) if first.startswith('"') else first
        out=[]
        for token in tokens:
            if token==')':return out
            out.append(node(token))
        raise ValueError('unclosed s-expression')
    return node(next(tokens))

def children(node,key):return [n for n in node if isinstance(n,list) and n and n[0]==key]
def child(node,key):return children(node,key)[0]
def nums(node,key):return tuple(float(v) for v in child(node,key)[1:])
def pads(node):return children(node,'pad')
def near(a,b):return len(a)==len(b) and all(abs(x-y)<1e-6 for x,y in zip(a,b))

def reviewed_contract(node):
    """Check the independent dimensions printed in TI sections 7.2/7.3."""
    copper={p[1]:p for p in pads(node) if 'F.Cu' in child(p,'layers')[1:]}
    if set(copper)!={'1','2','3','4','5'}:raise ValueError('wrong electrical pad set')
    for i,y in enumerate([-.975,-.325,.325,.975],1):
        p=copper[str(i)]
        if not near(nums(p,'at'),(-1.55,y)):raise ValueError('wrong pin order or exact pitch')
        if not near(nums(p,'size'),(.7,.4)):raise ValueError('wrong DNH copper size')
        if nums(p,'solder_mask_margin')!=(-.05,) or nums(p,'solder_paste_margin')!=(-.05,):raise ValueError('DNH uses mask-defined 0.6x0.3 openings')
    d=copper['5']
    if d[3]!='custom' or 'F.Paste' in child(d,'layers'):raise ValueError('drain needs the combined copper shape and separate stencil windows')
    if nums(d,'solder_mask_margin')!=(-.05,):raise ValueError('drain mask is inset 0.05 from the copper')
    poly=child(child(d,'primitives'),'gr_poly');points=[tuple(map(float,p[1:])) for p in child(poly,'pts')[1:]];ox,oy=nums(d,'at');points=[(x+ox,y+oy) for x,y in points]
    bounds=(min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points))
    if not near(bounds,(-.61,-1.275,1.9,1.275)):raise ValueError('wrong combined drain copper envelope')
    paste=[p for p in pads(node) if p[1]=='' and child(p,'layers')[1:]==['F.Paste']]
    if len(paste)!=8:raise ValueError('four drain fingers plus four thermal windows required')
    thermal=[p for p in paste if near(nums(p,'size'),(.705,1.125))]
    expected={(x,y) for x in [-.2075,.6975] for y in [-.6625,.6625]}
    if {nums(p,'at') for p in thermal}!=expected:raise ValueError('wrong thermal window dimensions or spacing')
    fingers=[p for p in paste if near(nums(p,'size'),(.6,.3))]
    if {nums(p,'at') for p in fingers}!={(1.55,y) for y in [-.975,-.325,.325,.975]}:raise ValueError('wrong drain finger stencil')
    return copper,points

def contains(points,p):
    inside=False;x,y=p
    for (ax,ay),(bx,by) in zip(points,points[1:]+points[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

class DNHFootprintTests(unittest.TestCase):
    def setUp(self):self.node=parse(FP.read_text())

    def test_primary_land_and_stencil_dimensions(self):reviewed_contract(self.node)

    def test_gate_source_clearance_has_margin_over_board_rule(self):
        copper,_=reviewed_contract(self.node);a,b=copper['3'],copper['4']
        gap=nums(b,'at')[1]-nums(a,'at')[1]-(nums(a,'size')[1]+nums(b,'size')[1])/2
        self.assertAlmostEqual(gap,.25)
        self.assertGreater(gap,.15)

    def test_drain_has_all_four_leads_and_thermal_pad(self):
        _,points=reviewed_contract(self.node)
        for y in [-.975,-.325,.325,.975]:
            for x in [1.25,1.55,1.8]:self.assertTrue(contains(points,(x,y)))
        for x in [-.5,0,.5,1.1]:
            for y in [-1.1,0,1.1]:self.assertTrue(contains(points,(x,y)))
        for y in [-.65,0,.65]:self.assertFalse(contains(points,(1.75,y)))
        self.assertFalse(contains(points,(-1.55,.975)))

    def test_mask_defined_openings_and_radius(self):
        copper,_=reviewed_contract(self.node)
        for p in list(copper.values())[:4]:
            w,h=nums(p,'size');margin,=nums(p,'solder_mask_margin');ratio,=nums(p,'roundrect_rratio')
            self.assertTrue(near((w+2*margin,h+2*margin),(.6,.3)))
            self.assertAlmostEqual(min(w,h)*ratio+margin,.05)

    def test_courtyard_includes_lands_and_max_body(self):
        rect=next(r for r in children(self.node,'fp_rect') if child(r,'layer')[1]=='F.CrtYd')
        self.assertEqual(nums(rect,'start'),(-2.15,-1.9));self.assertEqual(nums(rect,'end'),(2.15,1.9))
        self.assertGreaterEqual(2.15-1.9,.25-1e-9)
        self.assertGreaterEqual(1.9-3.25/2,.25)
        self.assertTrue(all(not children(p,'drill') for p in pads(self.node)))

    def test_stencil_windows_do_not_cover_the_whole_drain(self):
        blank=[p for p in pads(self.node) if p[1]=='']
        thermal=[p for p in blank if near(nums(p,'size'),(.705,1.125))]
        self.assertEqual(len(thermal),4)
        self.assertAlmostEqual(.905-.705,.2);self.assertAlmostEqual(1.325-1.125,.2)
        for p in blank:
            w,h=nums(p,'size');r,=nums(p,'roundrect_rratio');self.assertAlmostEqual(min(w,h)*r,.05,places=7)

    def test_reject_rounded_generic_pitch(self):
        n=copy.deepcopy(self.node);p=next(p for p in pads(n) if p[1]=='3');child(p,'at')[2]='0.33'
        with self.assertRaisesRegex(ValueError,'pitch'):reviewed_contract(n)

    def test_reject_generic_half_mm_lead_height(self):
        n=copy.deepcopy(self.node);p=next(p for p in pads(n) if p[1]=='4');child(p,'size')[2]='0.5'
        with self.assertRaisesRegex(ValueError,'copper size'):reviewed_contract(n)

    def test_reject_mirrored_pin_one(self):
        n=copy.deepcopy(self.node);p=next(p for p in pads(n) if p[1]=='1');child(p,'at')[2]='0.975'
        with self.assertRaisesRegex(ValueError,'pin order'):reviewed_contract(n)

    def test_reject_solid_drain_paste(self):
        n=copy.deepcopy(self.node);p=next(p for p in pads(n) if p[1]=='5');child(p,'layers').append('F.Paste')
        with self.assertRaisesRegex(ValueError,'stencil'):reviewed_contract(n)

    def test_model_is_explicitly_an_envelope_not_generic_q3(self):
        model=child(self.node,'model')[1]
        self.assertEqual(model,'${KIPRJMOD}/ducktop2.3dshapes/ti_csd17577q3a_dnh_body_envelope.step')
        self.assertTrue((ROOT/'ducktop2.3dshapes/ti_csd17577q3a_dnh_body_envelope.step').is_file())
        self.assertIn('not a manufacturer model',(ROOT/'ducktop2.3dshapes/ti_csd17577q3a_dnh_body_envelope.md').read_text())

if __name__=='__main__':unittest.main()

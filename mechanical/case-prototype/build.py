#!/usr/bin/env python3
"""Build the editable case fit prototype. Run from any working directory."""
import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
import cadquery as cq
from cad import HERE, ROOT, box, cylinder, compound, drilling, bounds, export_step, export_stl, render
import hinges

if __name__=='__main__':sys.modules['build']=sys.modules[__name__]


def load_config(profile=None):
    data=json.loads((HERE/'assembly.json').read_text())
    selected=profile or data['selected_profile']
    profiles=data.pop('profiles')
    def merge(base,extra):
        for k,v in extra.items():
            if isinstance(v,dict) and isinstance(base.get(k),dict):merge(base[k],v)
            else:base[k]=v
    merge(data,profiles[selected]);data['selected_profile']=selected
    return data


CONFIG=load_config()
INVENTORY=json.loads((HERE/'board-inventory.json').read_text())['boards']
PLACEMENT=json.loads((ROOT/'mechanical/board-placement.json').read_text())
CACHE=ROOT/'.workbench/case-prototype/pcb-step'
COLORS={'structure':(.60,.68,.73),'deck':(.75,.79,.82),'lid':(.52,.61,.69),
        'supports':(.20,.59,.65),'boards':(.13,.43,.31),'hardware':(.30,.33,.37),
        'panel':(.12,.17,.20),'cells':(.78,.68,.33),'cables':(.80,.30,.16),
        'cooling':(.68,.39,.19),'inputs':(.25,.31,.36),'keepout':(.91,.50,.21,.28),'routes':(.15,.48,.75)}


def installed(name, point):
    spec=CONFIG['boards'][name];a=math.radians(-spec['rotation_deg']);c=math.cos(a);s=math.sin(a)
    x,y=point;tx,ty=spec['translation_xy']
    return [c*x-s*y+tx,s*x+c*y+ty]


def fp(name, ref):
    return next(x for x in INVENTORY[name]['footprints'] if x['reference']==ref)


def pcb_top(name):
    return CONFIG['boards'][name]['bottom_height']+INVENTORY[name]['thickness']


def stroke(points, radius):
    """Swept circular cable or a rounded line, points in construction XYZ."""
    edges=[]
    for a,b in zip(points,points[1:]):
        va,vb=cq.Vector(*a),cq.Vector(*b);delta=vb-va
        if delta.Length>1e-6:
            edges.append(cq.Solid.makeCylinder(radius,delta.Length,va,delta.normalized()))
    return compound(edges)


class Model:
    def __init__(self):
        self.parts=[];self.mounts=[];self.findings=[];self.cable_records=[];self.board_material={}

    def add(self,name,shape,group='supports',material='PETG',moving=False,manufactured=True,**extra):
        if not shape.isValid():raise ValueError(name+' invalid BRep')
        self.parts.append({'name':name,'shape':shape,'group':group,'color':COLORS.get(group,(.5,.5,.5)),
                           'material':material,'moving':moving,'manufactured':manufactured,**extra})
        return shape

    def mount(self,ref,x,y,height,mate,hole,thread,support,length,insulation,status='proposed; physical fit pending',**extra):
        self.mounts.append({'reference':ref,'X_mm':round(x,4),'Y_mm':round(y,4),'Z_mm':round(-height,4),
            'mating_part':mate,'hole_mm':hole,'thread':thread,'support_height_mm':support,
            'fastener_length_mm':length,'insulation':insulation,'status':status,**extra})

    def split(self,name,shape,group,material='PETG',moving=False,xcut=179,ycut=115):
        # All pieces share assembly coordinates. STL derivatives are placed on Z=0.
        for i,(x,w) in enumerate([(-50,xcut+50),(xcut,450-xcut)]):
            for j,(y,d) in enumerate([(-60,ycut+60),(ycut,350-ycut)]):
                if w<=0 or d<=0:continue
                s=shape.intersect(box(x,y,-20,w,d,180))
                if s.Volume()>1:
                    self.add(f'{name}-{i+1}{j+1}',s,group,material,moving)

    def boards(self):
        coverage={}
        for name,row in INVENTORY.items():
            sha=hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()
            if sha!=row['sha256']:raise RuntimeError(name+' source changed; review new PCB before refresh')
            s=cq.importers.importStep(str(CACHE/(name+'.step'))).val()
            spec=CONFIG['boards'][name];tx,ty=spec['translation_xy'];z=spec['bottom_height']
            s=s.rotate((0,0,0),(0,0,1),spec['rotation_deg']).translate((tx,-ty,z))
            self.add(name+'-pcb-and-available-models',s,'boards','PCB',False,False)
            # Exact native board material from saved Edge.Cuts entities, through
            # KiCad's own BRep export. The thin slab isolates substrate for checks.
            slab=box(-40,-40,z+.001,450,350,row['thickness']-.002)
            solids=s.Solids()
            board=max((q for q in solids if q.BoundingBox().zlen<row['thickness']+.01),key=lambda q:q.Volume())
            self.board_material[name]=board
            cov=CACHE/(name+'.coverage.json')
            coverage[name]=json.loads(cov.read_text()) if cov.exists() else {'complete_component_assembly':False,'coverage_record_missing':True}
        # J70/J71 have no model attached in the saved board. Add the existing
        # project body model at the corrected footprint centres, without editing PCB data.
        dra=cq.importers.importStep(str(ROOT/'ducktop2.3dshapes/DRA818_Castellated.step')).val()
        dra=dra.rotate((0,0,0),(1,0,0),90)
        for ref in ['J70','J71']:
            f=fp('radio',ref);x,y=installed('radio',f['position'])
            shape=dra.rotate((0,0,0),(0,0,1),f['rotation']+CONFIG['boards']['radio']['rotation_deg']).translate((x,-y,pcb_top('radio')))
            self.add('radio-'+ref+'-DRA818-body',shape,'hardware','reference',False,False)
        coverage['radio']['case_added_models']={'J70':'existing project DRA818 body, 35.6 x 19 x 4; physical height confirmation pending',
                                              'J71':'same body envelope at its own saved footprint centre'}
        (HERE/'component-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

    def chassis(self):
        b=CONFIG['base'];floor=b['floor'];top=b['deck_top'];wall=b['wall']
        x0,x1,y0,y1=b['x_min'],b['x_max'],b['y_min'],b['y_max']
        base=box(x0,y0,0,x1-x0,y1-y0,floor)
        rim=box(x0,y0,floor,x1-x0,y1-y0,top-floor-b['deck_thickness'])
        rim=rim.cut(box(x0+wall,y0+wall,floor-.1,x1-x0-2*wall,y1-y0-2*wall,top))
        # Open side service windows keep unmated ports accessible while exact
        # plug overmoulds and cosmetic port inserts are still being measured.
        rim=rim.cut(box(x0-1,20,3,wall+2,162,23))
        rim=rim.cut(box(x1-wall-1,20,3,wall+2,98,23))
        rim=rim.cut(box(x0-1,y0-1,b['rear_wall_top'],x1-x0+2,10-y0+1,50))
        # Rear cooling outlet and radio connector access.
        rim=rim.cut(box(120,y0-1,23,56,wall+2,19))
        for yy in [133,198]:rim=rim.cut(box(x1-wall-1,yy-6,pcb_top('radio')-4.58,wall+2,12,10))
        base=base.fuse(rim)
        # Main board isolation: separate nylon male/female supports, no metal
        # boss or screw connects copper domains to the case.
        for name,refs in PLACEMENT['chassis_mounts'].items():
            z=CONFIG['boards'][name]['bottom_height']
            for ref in refs:
                hole=next(q for q in INVENTORY[name]['holes'] if q['reference']==ref)
                x,y=installed(name,hole['position'])
                post=cylinder(x,y,floor,2.5,z-floor).cut(cylinder(x,y,floor-.1,1.0,z-floor+.2))
                self.add(name+'-'+ref+'-nylon-support',post,'supports','nylon',False,False)
                base=base.cut(cylinder(x,y,-.1,1.4,floor+.2))
                self.mount(name+'/'+ref,x,y,z,'base, nylon M2.5 male/female standoff',2.7,'M2.5',z-floor,5,
                           'nylon screw, support, washer and underside nut; preserve PCB isolation',
                           'XY/drill verified from saved board; purchased hardware fit pending',washer_thickness_mm=.5,top_thread_engagement_mm=2.9)
        for i,hole in enumerate(q for q in INVENTORY['bms']['holes'] if q['reference'] is None):
            x,y=installed('bms',hole['position']);z=CONFIG['boards']['bms']['bottom_height']
            p=cylinder(x,y,floor,2.1,z-floor).cut(cylinder(x,y,floor-.1,1,z-floor+.2))
            self.add(f'bms-perimeter-{i+1}-support',p,'supports','nylon',False,False)
            base=base.cut(cylinder(x,y,-.1,1.4,floor+.2))
            self.mount(f'bms/edge-hole-{i+1}',x,y,z,'base, 8 mm insulating standoff',round(hole['drill'][0],6),
                       'M2.5 proposed',z-floor,5,'all support, screw, washer and nut parts electrically insulating',
                       'four real Edge.Cuts holes; no middle supports; hardware fit pending')
        for ref,height,desc in [('H1',5.5,'Wurth 9774055243R Mu support'),('H2',5.5,'Wurth 9774055243R Mu support'),
                                ('H3',2.5,'M2 NVMe retainer'),('H4',2.5,'M2 Wi-Fi retainer')]:
            q=next(q for q in INVENTORY['center']['holes'] if q['reference']==ref)
            x,y=installed('center',q['position'])
            self.mount('center/'+ref,x,y,pcb_top('center')+height,desc,q['drill'][0],'M2',height,'measure module/card stack',
                       'existing PCB support; not a chassis hole','saved geometry; screw length unresolved')
        # Rear metal spine: the hinge loads run into a continuous structure.
        spine=box(4,-23,floor,350,18,3).fuse(box(4,-23,floor+3,350,3,b['rear_wall_top']-floor-3))
        spine=spine.cut(box(120,-25,23,56,24,19))
        for x in [10,70,110,190,270,348]:
            spine=spine.cut(cylinder(x,-14,floor-.1,1.6,3.2))
            base=base.cut(cylinder(x,-14,-.1,1.6,floor+.2))
            self.mount(f'spine-{x}',x,-14,floor+3,'rear spine to base',3.2,'M3',3,10,'clear of all PCBs')
        self.add('rear-spine',spine,'structure','aluminum')
        hinge=CONFIG['hinges'];hy=hinge['pivot_y'];hh=hinge['pivot_height']
        for side,hx in zip(['left','right'],hinge['pivot_x']):
            self.parts.extend(hinges.parts(side,hx,hy,hh,0))
            for part in self.parts[-7:]:part.update(manufactured=False,material='OEM steel')
            plate,bolts=hinges.base_plate(side,hx,hy,hh)
            self.add(side+'-hinge-base-steel-plate',plate,'hardware','steel')
            bb=plate.BoundingBox();seat=hh+hinges.BASE_SEAT[side]
            xmin=bb.xmin
            relief=b['rear_wall_top']
            tower=box(xmin,-14,floor,bb.xlen,30,relief-floor)
            tower=tower.cut(box(xmin-1,-24,floor-.1,bb.xlen+2,19,3.1))
            tower=tower.fuse(box(xmin,5.5,relief,bb.xlen,16.5,seat-3-relief))
            if relief>20:tower=tower.cut(box(xmin+3,-10,10,bb.xlen-6,21,relief-16))
            if side=='left':
                # Existing F195 holder projects forward of the PCB notch.
                tower=tower.cut(box(33.96,17.33,4.247,18,8.73,12.16))
            for x,y in bolts:
                tower=tower.cut(cylinder(x,y,seat-11,1.6,9))
                pocket=cq.Workplane('XY').polygon(6,5.7/math.cos(math.pi/6)).extrude(2.8).val().translate((x,-y,seat-5.7))
                tower=tower.cut(pocket)
                self.mount(side+'-base-adapter-'+str(round(x,1)),x,y,seat,'steel adapter to captured M3 hex nut in hinge tower',3.2,'M3',3,6,'structural metal, isolated from board','nut pockets loaded before steel adapter; F195 withdrawal needs adapter removal')
            # Four foot bolts, independent of board mounts and within the notch.
            for x in [xmin+3.5,xmin+29.5]:
                for y in [-11,12]:
                    tower=tower.cut(cylinder(x,y,floor-.1,1.6,seat-floor))
                    # Rear access bores break through the wall deliberately;
                    # a tangent 6 mm bore leaves a non-manifold zero-thickness seam.
                    tower=tower.cut(cylinder(x,y,floor+5.5,3.2 if y<0 else 3.0,seat-floor))
                    base=base.cut(cylinder(x,y,-.1,1.6,floor+.2))
                    self.add(f'{side}-tower-bolt-head-{x:.1f}-{y}',cylinder(x,y,floor+5.5,2.75,2.4),'hardware','steel',False,False)
                    self.mount(f'{side}-tower-{x:.1f}-{y}',x,y,floor+5.5,'tower to base/spine; through-bolt and underside nut',3.2,'M3',5.5,12,'no board contact','head access counterbore; fit before hinge adapter plate')
            self.add(side+'-hinge-tower',tower,'supports')
            for j,(x,y) in enumerate(hinges.base_holes(side,hx,hy)):
                self.mount(f'{side}-hinge-base-{j+1}',x,y,seat+1,'OEM hinge to steel plate','2.7 round/slot','M2',3,4,'structural',
                           'CAD seat verified; tap and physical fit pending',engagement_mm=3,head_diameter_mm=4.6,head_height_mm=.6)
        # Microphone bottom port goes through the actual PCB aperture and a gasket.
        mic=fp('center','MK430');x,y=installed('center',mic['position'])
        base=base.cut(cylinder(x,y,-.1,1,floor+.2))
        gasket=cylinder(x,y,floor,2,CONFIG['boards']['center']['bottom_height']-floor)
        gasket=gasket.cut(cylinder(x,y,floor-.1,1,8))
        self.add('microphone-foam-duct',gasket,'supports','closed-cell foam',False,False)
        self.mount('MK430/acoustic-duct',x,y,floor,'base acoustic port and foam gasket',2,'none',4,'none','insulating foam','mic XY verified; port offset/seal acoustic test pending')
        # Seven deck posts outside PCB material. The keyboard carrier stiffens
        # the rear deck span; do not put a centre post through the compute PCB.
        deck_points=[(-3,12),(361,12),(-3,122),(361,122),(-3,251),(179,251),(361,251)]
        self.deck_points=deck_points
        for i,(x,y) in enumerate(deck_points):
            post=cylinder(x,y,floor,2.5,top-floor-b['deck_thickness'])
            post=post.cut(cylinder(x,y,top-9,1.025,9))
            base=base.fuse(post)
            self.mount(f'deck-{i+1}',x,y,top,'removable deck to case post',2.8,'M2.5',top-floor-b['deck_thickness'],8,
                       'posts remain outside PCB material','2.05 mm tap pilot; FDM tapped-thread pullout test pending')
        # Bottom splice plates and corner feet allow the four P1S tiles to join.
        for i,(x,y) in enumerate([(169,20),(169,160),(40,105),(285,105)]):
            splice=box(x,y,-3,20,20,3)
            for dx,dy in [(4,4),(16,4),(4,16),(16,16)]:
                splice=splice.cut(cylinder(x+dx,y+dy,-3.1,1.6,6))
                base=base.cut(cylinder(x+dx,y+dy,-.1,1.6,floor+.2))
                self.mount(f'base-splice-{i+1}-{dx}-{dy}',x+dx,y+dy,floor,'base tiles to 3 mm underside splice',3.2,'M3',3,8,'clear of electronics; countersunk head fit pending')
            self.add(f'base-splice-{i+1}',splice,'structure','aluminum')
        for i,(x,y) in enumerate([(1,-19),(357,-19),(1,249),(357,249)]):
            foot=cylinder(x,y,-5,4,5)
            self.add(f'rubber-foot-{i+1}',foot,'supports','rubber',False,False)
        self.split('base',base,'structure',xcut=b['split_x'],ycut=b['split_y'])

    def inputs(self):
        b=CONFIG['base'];dt=b['deck_top'];th=b['deck_thickness']
        deck=box(b['x_min'],b['y_min'],dt-th,b['x_max']-b['x_min'],b['y_max']-b['y_min'],th)
        # Expose the keyboard, trackpad and independent wired OLEDs.
        deck=deck.cut(box(41.75,19.5,dt-th-1,274.5,81,th+2))
        deck=deck.cut(box(306,50,dt-th-1,23,23,th+2))
        t=CONFIG['trackpad']; deck=deck.cut(box(t['x']-.5,t['y']-.5,dt-th-1,t['width']+1,t['depth']+1,th+2))
        deck=drilling(deck,self.deck_points,2.8,dt-th-.1,th+.2)
        # Open rear hinge/service band, no cosmetic cover hiding the mechanism.
        deck=deck.cut(box(-7,-27,dt-th-1,372,37,th+2))
        # Keyboard carrier floor, edge stops and pads in actual free backside areas.
        kh=CONFIG['boards']['keyboard']['bottom_height'];kx,ky=42.25,20;kw,kd=273.5,80
        tray=box(kx-8,ky-7,kh-4.5,kw+16,kd+14,2)
        lips=box(kx-2,ky-2,kh-2.5,kw+4,kd+4,2.5).cut(box(kx+1,ky+1,kh-2.6,kw-2,kd-2,2.7))
        tray=tray.fuse(lips)
        # Avoid the edge connector's insertion path.
        tray=tray.cut(box(306,50,kh-3,24,23,8))
        from shapely.geometry import Polygon,Point
        from shapely.ops import unary_union
        back=unary_union([Polygon([installed('keyboard',v) for v in ring]) for f in INVENTORY['keyboard']['footprints'] for ring in f['courtyards']['back']])
        supports=[]
        for x in [65,100,140,180,220,260,295]:
            for y in [36,63,86]:
                disk=Point(x,y).buffer(2.2)
                if disk.distance(back)>.5:
                    tray=tray.fuse(cylinder(x,y,kh-2.5,2,2.5));supports.append([x,y])
                    self.mount(f'keyboard-pad-{x}-{y}',x,y,kh,'insulating underside pad on carrier',0,'none',2.5,'none','insulating contact only','clear of exported B.CrtYd; first-article pad contact pending')
        # Eight edge clips bolt to the carrier, never to the keyboard PCB.
        for i,(x,y) in enumerate([(48,17.8),(100,17.8),(258,17.8),(310,17.8),(48,102.2),(100,102.2),(258,102.2),(310,102.2)]):
            tray=tray.fuse(cylinder(x,y,kh-4.5,2.2,5.4))
            clip=box(x-3,y-3,kh+.9,6,6,1.6)
            clip=clip.cut(cylinder(x,y,kh+.8,1.1,2))
            tray=tray.cut(cylinder(x,y,kh-4.6,.8,5.5))
            self.add(f'keyboard-clip-{i+1}',clip,'supports')
            self.mount(f'keyboard-clip-{i+1}',x,y,kh+2.5,'edge clip to carrier; no PCB drilling',2.2,'M2',.9,6,'nylon pad against PCB','edge/cap fit pending')
        for i,(x,y) in enumerate([(37,35),(37,85),(321,35),(321,85)]):
            tray=tray.fuse(cylinder(x,y,kh-4.5,2.7,dt-th-kh+4.5))
            tray=tray.cut(cylinder(x,y,kh-4.6,1.025,9))
            deck=deck.cut(cylinder(x,y,dt-th-.1,1.4,th+.2))
            self.mount(f'keyboard-carrier-deck-{i+1}',x,y,dt,'carrier to removable deck',2.8,'M2.5',dt-th-kh+4.5,8,'insulating supports; no PCB hole','insert and carrier stiffness fit pending')
        self.split('keyboard-carrier',tray,'supports',ycut=400)
        # Key envelope uses every real switch centre and leaves key width uncertain.
        keys=[]
        for f in INVENTORY['keyboard']['footprints']:
            if f['reference'].startswith('SW'):
                x,y=installed('keyboard',f['position'])
                keys.append(box(x-7.2,y-7.2,kh+.8,14.4,14.4,CONFIG['keyboard']['key_height_above_pcb']))
        self.add('key-travel-and-cap-envelopes',compound(keys),'inputs','reference',False,False)
        # Trackpad's bridge is supported by the deck frame, never by the cells.
        tp_h=dt-t['thickness'];bridge_h=tp_h-t['click_travel']-t['under_clearance']-2.5
        bridge=box(t['x']-6,t['y']-5,bridge_h,t['width']+12,t['depth']+10,2.5)
        for x in [t['x']-4,t['x']+t['width']+4]:
            rail=box(x-2,t['y']-5,bridge_h+2.5,4,t['depth']+10,dt-th-bridge_h-2.5)
            bridge=bridge.fuse(rail)
            for yy in [t['y'],t['y']+t['depth']-2]:
                bridge=bridge.cut(cylinder(x,yy,bridge_h-.1,1.6,20))
                deck=deck.cut(cylinder(x,yy,dt-th-.1,1.6,th+.2))
                self.mount(f'trackpad-bridge-{x}-{yy}',x,yy,dt,'deck to independent trackpad bridge with underside nut',3.2,'M3',dt-bridge_h,16,'insulating pads; no contact with cells','click loads into bridge and deck; actual mounting pending')
        # Rear ledge and two side guides retain the body while leaving the front click free.
        bridge=bridge.fuse(box(t['x']-1,t['y']-2,bridge_h+2.5,t['width']+2,3,tp_h-bridge_h-2.5))
        self.add('trackpad-bridge',bridge,'supports')
        self.add('trackpad-body-envelope',box(t['x'],t['y'],tp_h,t['width'],t['depth'],t['thickness']),'inputs','reference',False,False)
        # Cell trays and strap slots sit entirely below the palm structure.
        c=CONFIG['cells'];floor=b['floor']
        for i,x in enumerate(c['x']):
            pad_h=floor+c['pad_thickness']
            self.add(f'cell-{i+1}-measured-plan-assumed-depth',box(x,c['y'],pad_h,c['width'],c['depth'],c['thickness']),'cells','reference',False,False)
            tray=box(x-1.5,c['y']-1.5,floor,c['width']+3,c['depth']+3,1)
            rim=box(x-1.5,c['y']-1.5,floor+1,c['width']+3,c['depth']+3,5).cut(box(x-.3,c['y']-.3,floor+.9,c['width']+.6,c['depth']+.6,6))
            rim=rim.cut(box(x+40,c['y']-2,floor,20,5,8))
            tray=tray.fuse(rim)
            for xx in [x+20,x+80]:
                tab=box(xx-5,248,floor,10,6,1)
                tab=tab.cut(cylinder(xx,251,floor-.1,1.4,1.2))
                tray=tray.fuse(tab)
                for part in self.parts:
                    if part['name'].startswith('base-') and part['group']=='structure':
                        part['shape']=part['shape'].cut(cylinder(xx,251,-.1,1.4,floor+.2))
                self.mount(f'cell-{i+1}-tray-{xx}',xx,251,floor+1,'cell tray tab to floor with underside nut',2.8,'M2.5',1,6,'nylon hardware; all fasteners outside cell plan','tab fit and full pack outline pending')
            for yy in [c['y']+12,c['y']+48]:
                # Strap exits outside the cell body; no screw or hard clamp above a pouch.
                for xx in [x-1.2,x+c['width']+.2]:tray=tray.cut(box(xx,yy,floor-.1,1,5,1.3))
            self.add(f'cell-{i+1}-tray',tray,'supports')
            self.mount(f'cell-{i+1}-retention',x+50,c['y']+30,pad_h,'padded tray with noncompressive removable straps',0,'none',1,'none','dielectric tray/pad, tabs individually insulated','full pack dimensions, tabs and swelling allowance pending')
        # Optional radio hangs from the removable deck. No long posts pass through a PCB.
        rad=[]
        for hole in INVENTORY['radio']['holes']:
            if not hole['reference'].startswith('H'):continue
            x,y=installed('radio',hole['position']);rad.append((x,y))
            z=pcb_top('radio');length=dt-th-z
            sleeve=cylinder(x,y,z,2.4,length).cut(cylinder(x,y,z-.1,1.1,length+.2))
            self.add('radio-'+hole['reference']+'-suspension',sleeve,'supports','nylon',False,False)
            deck=deck.cut(cylinder(x,y,dt-th-.1,1.1,th+.2))
            self.mount('radio/'+hole['reference'],x,y,z,'radio to deck, insulating suspension tube',2.2,'M2',round(length,2),math.ceil((length+7)/5)*5,
                       'insulating standoff and washers','PCB hole verified; suspended placement proposed')
        # OLEDs are separate modules in shallow clip trays, not the JST connector bodies.
        o=CONFIG['oled']
        for i,(x,y) in enumerate(o['xy']):
            deck=deck.cut(box(x-.2,y-.2,dt-th-.1,o['width']+.4,o['depth']+.4,th+.2))
            carrier=box(x-2,y-2,dt-o['thickness']-2,o['width']+4,o['depth']+4,2)
            carrier=carrier.fuse(box(x-2,y-2,dt-o['thickness'],2,o['depth']+4,o['thickness']))
            carrier=carrier.fuse(box(x+o['width'],y-2,dt-o['thickness'],2,o['depth']+4,o['thickness']))
            for j,yy in enumerate([y-5,y+o['depth']+5]):
                xx=x+o['width']/2
                tab=box(xx-4,yy-3,dt-o['thickness']-2,8,6,2)
                post=cylinder(xx,yy,dt-o['thickness']-2,2.5,o['thickness']+2-th)
                carrier=carrier.fuse(tab).fuse(post).cut(cylinder(xx,yy,dt-o['thickness']-2.1,1.1,10))
                deck=deck.cut(cylinder(xx,yy,dt-th-.1,1.1,th+.2))
                self.mount(f'oled-{i+1}-deck-{j+1}',xx,yy,dt,'OLED tray to deck with underside M2 nut',2.2,'M2',o['thickness']+2,10,'insulating module tray','module edge/clamp fit pending')
            self.add(f'oled-{i+1}-clip-tray',carrier,'supports')
            self.add(f'oled-{i+1}-module',box(x,y,dt-o['thickness'],o['width'],o['depth'],o['thickness']),'inputs','reference',False,False)
            self.mount(f'oled-{i+1}',x+o['width']/2,y+o['depth']/2,dt-o['thickness'],'clip tray under removable deck',0,'clips',2,'none','insulating','module dimensions and tabs pending')
        # Speaker cups hang from the deck, above the cells; the acoustic volume is a trial.
        s=CONFIG['speakers']
        for i,(x,y) in enumerate(s['xy']):
            bottom=s['body_bottom']-s['cavity_depth']-2;body=s['body_bottom']
            cup=box(x-2,y-2,bottom,s['width']+4,s['depth']+4,dt-th-bottom)
            cup=cup.cut(box(x-.3,y-.3,bottom+2,s['width']+.6,s['depth']+.6,dt-bottom))
            for xx in [x-.3,x+s['width']-1.2]:
                cup=cup.fuse(box(xx,y+2,body-1.5,1.5,s['depth']-4,1.5))
            self.add(f'speaker-{i+1}-cup',cup,'supports')
            self.add(f'speaker-{i+1}-body',box(x,y,body,s['width'],s['depth'],s['height']),'inputs','reference',False,False)
            for j,yy in enumerate([y-4,y+s['depth']+4]):
                xx=x+s['width']/2
                hanger=cylinder(xx,yy,bottom,2.5,dt-th-bottom).cut(cylinder(xx,yy,bottom-.1,1.1,dt-bottom))
                cup_tab=box(xx-4,yy-3,bottom,8,6,2).cut(cylinder(xx,yy,bottom-.1,1.1,2.2))
                cup_part=next(p for p in self.parts if p['name']==f'speaker-{i+1}-cup')
                cup_part['shape']=cup_part['shape'].fuse(hanger).fuse(cup_tab)
                deck=deck.cut(cylinder(xx,yy,dt-th-.1,1.1,th+.2))
                self.mount(f'speaker-{i+1}-{j+1}',xx,yy,dt,'speaker cup to deck',2.2,'M2',dt-bottom,45,'cup/pad insulating','depth and acoustic tuning pending')
            # Trial grilles are separate from the battery floor.
            for gy in range(6):deck=deck.cut(box(x+3,y+3+5*gy,dt-th-.1,s['width']-6,1.5,th+.2))
        self.split('deck',deck,'deck')

    def lid(self):
        l=CONFIG['lid'];hh=CONFIG['hinges']['pivot_height'];hy=CONFIG['hinges']['pivot_y']
        x0,x1=l['x_min'],l['x_max'];y0=hy+l['s_min'];y1=hy+l['s_max'];back=hh+l['back_inner_height_from_axis']
        skin=box(x0,y0,back,x1-x0,y1-y0,l['skin'])
        # A continuous aluminum rail replaces the printed skin across the hinge band.
        skin=skin.cut(box(x0-1,hy-4,back-.1,x1-x0+2,31,l['skin']+.2))
        walls=box(x0,y0,hh+8,x1-x0,y1-y0,5)
        walls=walls.cut(box(x0+l['side_wall'],y0+l['side_wall'],hh+7.9,x1-x0-2*l['side_wall'],y1-y0-2*l['side_wall'],5.2))
        skin=skin.fuse(walls)
        # The cable slot would isolate a thin central heel strip from this
        # printed tile. Leave the rear rail exposed there instead.
        skin=skin.cut(box(69,hy-9,hh+7.9,x1-l['side_wall']-69,5.1,10))
        rail=box(x0,hy-4,back,x1-x0,31,3)
        cable_slot=box(57,hy-9,hh+5,12,27,20)
        rail=rail.cut(cable_slot)
        skin=skin.cut(cable_slot)
        for side,hx in zip(['left','right'],CONFIG['hinges']['pivot_x']):
            plate,seats,bolts=hinges.lid_plate(side,hx,hy,hh)
            self.add(side+'-lid-steel-plate',plate,'hardware','steel',True)
            for i,s in enumerate(seats):self.add(f'{side}-lid-seat-{i+1}',s,'hardware','aluminum',True)
            for i,(x,y) in enumerate(bolts):
                rail=rail.cut(cylinder(x,y,back-.1,1.25,3.2))
                self.mount(f'{side}-lid-adapter-{i+1}',x,y,hh+10,'steel plate to aluminum cross rail',3.2,'M3',3,6,'no panel contact','tap fit pending')
            for i,(x,y,level,diam,thread,old,new) in enumerate(hinges.lid_holes(side,hx,hy)):
                self.mount(f'{side}-hinge-lid-{i+1}',x,y,hh+level-1,'OEM bracket through sleeve to steel plate',diam,thread,10-level,new,
                           'no panel contact','source seat and hole verified; physical fit pending',OEM_screw_length_mm=old,
                           engagement_mm=round(new-(10-(level-1)),2))
        self.add('lid-cross-rail',rail,'structure','aluminum',True)
        px=l['panel_x'];py=hy+l['panel_s'];pw=l['panel_width'];pd=l['panel_depth'];ph=hh+l['panel_back_height_from_axis']-l['panel_thickness']
        self.add('display-panel-envelope',box(px,py,ph,pw,pd,l['panel_thickness']),'panel','reference',True,False)
        bezel=box(x0,y0,ph-.8,x1-x0,y1-y0,.8)
        bezel=bezel.cut(box(px+l['bezel_overlap'],py+l['bezel_overlap'],ph-1,pw-2*l['bezel_overlap'],pd-2*l['bezel_overlap'],2))
        bezel=bezel.cut(cable_slot)
        # Shoulder-controlled perimeter stops retain only the panel frame.
        for i,(x,y) in enumerate([(px-3,py+10),(px+pw+3,py+10),(px-3,py+pd/2),(px+pw+3,py+pd/2),(px-3,py+pd-10),(px+pw+3,py+pd-10)]):
            boss=cylinder(x,y,ph,2.4,back-ph)
            boss=boss.cut(cylinder(x,y,ph-.1,.8,back-ph+.2));skin=skin.fuse(boss)
            bezel=bezel.cut(cylinder(x,y,ph-.9,1.1,1))
            self.mount(f'bezel-{i+1}',x,y,ph-.8,'bezel to frame with shoulder stop',2.2,'M2',back-ph,4,
                       'soft gasket; hard stop bypasses LCD glass','panel flange and active-area margins pending')
        # Back pads and narrow ledges leave the active panel uncompressed.
        for x in [px,px+pw-3]:
            self.add(f'panel-back-pad-{x}',box(x,py+5,ph+l['panel_thickness'],3,pd-10,.5),'supports','silicone foam',True,False)
        self.split('lid-shell',skin,'lid',moving=True,ycut=hy+130)
        self.split('bezel',bezel,'deck',moving=True,ycut=hy+130)
        # Small splices on the back join print tiles; production lid is one CNC part.
        for i,(x,y) in enumerate([(169,hy+55),(169,hy+200),(20,hy+120),(318,hy+120)]):
            join=box(x,y,back+l['skin'],20,20,2)
            for dx,dy in [(4,4),(16,4),(4,16),(16,16)]:
                join=join.cut(cylinder(x+dx,y+dy,back+l['skin']-.1,1.1,2.2))
                for part in self.parts:
                    if part['name'].startswith('lid-shell-'):
                        part['shape']=part['shape'].cut(cylinder(x+dx,y+dy,back-.1,.8,l['skin']+.2))
                self.mount(f'lid-splice-{i+1}-{dx}-{dy}',x+dx,y+dy,back+l['skin']+2,'outer lid splice; tap lid holes after fit',2.2,'M2',2,4,'do not let tips reach panel','pilot transfer and depth stop required')
            self.add(f'lid-print-splice-{i+1}',join,'hardware','aluminum',True)

    def thermal(self):
        c=CONFIG['cooling']
        for name in ['cold_plate','heatpipe','fins','blower']:
            shape=box(*c[name])
            if name=='fins':
                x,y,h,w,d,t=c[name]
                shape=compound([box(x,y,h,w,d,1)]+[box(x+2+2*i,y,h+1,.5,d,t-1) for i in range(23)])
            if name=='blower':
                x,y,h,w,d,t=c[name]
                for xx,yy in [(x+41.75,y+3.25),(x+41.75,y+41.75),(x+3.25,y+41.75)]:
                    shape=shape.cut(cylinder(xx,yy,h-.1,1.4,t+.2))
            self.add('cooling-'+name+'-reservation',shape,'cooling','reference',False,False)
        # A separate cradle carries fan/fin mass; TIM load and Ultra screw pattern
        # remain unresolved, so no invented holes are added to the module.
        x,y,h,w,d,t=c['blower'];cradle=box(x-7,y-7,h-2,w+14,d+14,2)
        cradle=cradle.cut(cylinder(x+w/2,y+d/2,h-2.1,18,2.2))
        upper=CONFIG['boards']['keyboard']['bottom_height']-4.5
        for i,(xx,yy) in enumerate([(x-5,y-5),(x+w+5,y-5),(x-5,y+d+5),(x+w+5,y+d+5)]):
            cradle=cradle.cut(cylinder(xx,yy,h-2.1,1.1,2.2))
            if upper>h:
                post=cylinder(xx,yy,h,2.2,upper-h).cut(cylinder(xx,yy,h-.1,1.1,upper-h+.2))
                self.add(f'blower-cradle-suspension-{i+1}',post,'supports','nylon',False,False)
            for part in self.parts:
                if part['name'].startswith('keyboard-carrier-'):
                    part['shape']=part['shape'].cut(cylinder(xx,yy,upper-.1,1.1,2.2))
            self.mount(f'cooling-cradle-{i+1}',xx,yy,upper+2,'blower cradle suspended from keyboard carrier, through-bolt and nuts',2.2,'M2',round(upper-h,2),round(upper-h+5.5,1),'insulating sleeves','low-profile head, 1.5 mm nut engagement; trim to length to clear SW3; thermal test pending')
        for i,(xx,yy) in enumerate([(x+41.75,y+3.25),(x+41.75,y+41.75),(x+3.25,y+41.75)]):
            cradle=cradle.cut(cylinder(xx,yy,h-2.1,1.6,2.2))
            self.add(f'fan-through-screw-{i+1}',cylinder(xx,yy,h-2,1,15).fuse(cylinder(xx,yy,h-3.5,2.25,1.5)),'hardware','steel',False,False)
            self.mount(f'Delta-blower-{i+1}',xx,yy,h-2,'Delta BFB04512HHA-CZ0T through-bolt to cradle, washer and nut above',2.8,'M2 chosen with washers',2,15,
                       'fan plastic frame; clear of PCB','manufacturer 38.5 mm three-hole pattern, body-centering datum and sample fit pending',head_diameter_mm=4.5,head_height_mm=1.5)
        self.add('blower-fit-cradle',cradle,'supports')
        if h+t>upper:
            # The low carrier needs a window around the real 10.3 mm fan body.
            # Keep the PCB intact and retain contact pads outside this window.
            cut=box(x-1,y-1,upper-.1,w+2,d+2,10)
            for part in self.parts:
                if part['name'].startswith('keyboard-carrier-'):part['shape']=part['shape'].cut(cut)
            self.mounts=[row for row in self.mounts if not (row['reference'].startswith('keyboard-pad-') and
                         x-3<row['X_mm']<x+w+3 and y-3<row['Y_mm']<y+d+3)]
        self.add('pending-100W-power-space',box(*c['pending_power_reserve']),'keepout','reservation',False,False)
        self.findings.append('cooler geometry is a reserved volume, not a qualified Ultra cooler; contact, springs and thermal performance for 256V remain open')


def main():
    global CONFIG
    parser=argparse.ArgumentParser();parser.add_argument('--no-render',action='store_true');parser.add_argument('--profile',choices=['compact-study','current-hardware']);args=parser.parse_args()
    CONFIG=load_config(args.profile)
    m=Model();m.boards();print('boards loaded',flush=True)
    m.chassis();print('base and hinges built',flush=True)
    m.inputs();print('deck and component supports built',flush=True)
    m.lid();m.thermal();print('lid and cooling built',flush=True)
    from cables import add_cables
    add_cables(m)
    from deliver import deliver
    deliver(m,render_views=not args.no_render)


if __name__=='__main__':main()

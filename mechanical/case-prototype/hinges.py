"""Framework 13 revision-00 hinges, independent left/right mounting adapters."""
import hashlib
import json
import math
from functools import lru_cache
import cadquery as cq
from cad import HERE, ROOT, box, cylinder, compound, drilling, export_step, export_stl, render, bounds

SOURCE = HERE / 'reference/framework13'
SOURCE_COMMIT = 'b3872f334810103c758e39a33572b42a5e4d67e0'
PIVOT_NATIVE = (0,-4,4.25)
BASE_SEAT = {'left': -1.3, 'right': -2.2}
LID_HOLES = [
    # abs(native X), distance from axis along closed lid, seating height,
    # OEM hole, screw, OEM screw length, new tapped-adapter screw length
    (118.45,5.85,7.0,3.3,'M2',2.0,6.0),
    (124.45,2.95,7.0,3.3,'M2',2.0,6.0),
    (98.4,.45,6.1,1.9,'M1.6',3.0,7.0),
]


@lru_cache(None)
def raw(side):
    file = '13_5_hinge_l_assy.stp' if side=='left' else '13_5_hinge_R_assy.stp'
    shape=cq.importers.importStep(str(SOURCE/file)).val()
    assert shape.isValid() and len(shape.Solids())==7
    return shape.Solids()


def local_hinge(side, angle=105):
    """Unmirrorable OEM parts: translate native pivot then rotate, never reflect.

    Construction frame: front -Y, height +Z. Base foot is horizontal at
    native opening 105 deg. Solids 0,1,2 move; 3,4,5,6 stay on the base.
    """
    result=[]
    for i,s in enumerate(raw(side)):
        s=s.translate((0,4,-4.25)).rotate((0,0,0),(1,0,0),-15)
        if i<3:
            s=s.rotate((0,0,0),(1,0,0),105-angle)
        result.append(s)
    return result


def location(side, x, y, height):
    return (x-(-120 if side=='left' else 120), -y, height)


def parts(side, x, y, height, angle=105):
    shift=location(side,x,y,height)
    return [{'name':f'hinge-{side}-{i}', 'group':'lid' if i<3 else 'hinges',
             'shape':s.translate(shift), 'color':(.21,.24,.28), 'moving':i<3}
            for i,s in enumerate(local_hinge(side,angle))]


def hole_x(side, absolute, pivot_x):
    return pivot_x + ((120-absolute) if side=='left' else (absolute-120))


def base_holes(side, x, y):
    return [(hole_x(side,a,x),y+18.55) for a in [134,125.5]]


def lid_holes(side, x, y):
    return [(hole_x(side,a,x),y+along,seat,diam,thread,old,new)
            for a,along,seat,diam,thread,old,new in LID_HOLES]


def base_plate(side,x,y,height):
    """3 mm steel adapter, tapped M2; rivet relief and two M3 chassis bolts."""
    seat=height+BASE_SEAT[side]
    # Located on the 36 mm board notch, separated from its edge by >=1 mm.
    xmin=x-17 if side=='left' else x-16
    plate=box(xmin,y+15.9,seat-3,33,16,3)
    for hx,hy in base_holes(side,x,y):
        plate=plate.cut(cylinder(hx,hy,seat-3.1,.8,3.2))
    # Chassis attachment pattern is independent of the PCB mounting holes.
    bolts=[(xmin+3.5,y+28),(xmin+29.5,y+28)]
    plate=drilling(plate,bolts,3.2,seat-3.1,3.2)
    return plate,bolts


def lid_plate(side,x,y,height):
    """3 mm tapped backing plate and removable stepped seating sleeves."""
    xmin=x-17 if side=='left' else x-26
    plate=box(xmin,y-4,height+10,43,31,3)
    seats=[]
    for hx,hy,seat,diam,thread,_,_ in lid_holes(side,x,y):
        tap=.8 if thread=='M2' else .625
        plate=plate.cut(cylinder(hx,hy,height+9.9,tap,3.2))
        r=2.4 if thread=='M2' else 1.5
        sleeve=cylinder(hx,hy,height+seat,r,10-seat)
        sleeve=sleeve.cut(cylinder(hx,hy,height+seat-.1,1.1 if thread=='M2' else .9,10-seat+.2))
        seats.append(sleeve)
    bolts=[(xmin+3,y+22),(xmin+40,y+22)]
    plate=drilling(plate,bolts,3.2,height+9.9,3.2)
    return plate,seats,bolts


def source_record():
    records=[]
    for file in sorted(SOURCE.iterdir()):
        if file.name=='sources.json': continue
        records.append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                        'url':f'https://raw.githubusercontent.com/FrameworkComputer/Framework-Laptop-13/{SOURCE_COMMIT}/'+('LICENSE' if file.name=='LICENSE' else 'Hinges/'+file.name)})
    return {'copyright':'Framework Computer Inc', 'license':'CC-BY-4.0',
            'repository_commit':SOURCE_COMMIT, 'files':records,
            'drawing_date':'2023-06-27', 'revision':0, 'version':0,
            'part_numbers':{'left':'AM3BA000I00','right':'AM3BA000J00'},
            'selected_kit':'Framework Laptop 13 Hinge Kit - 3.3kg',
            'match_status':'drawing torque label matches selected original kit; physical markings and coupon fit pending',
            'printed_torque_unit':'kg-f/cm',
            'torque_note':'printed unit is dimensionally ambiguous; calculations interpreting it as kgf*cm are conditional and require supplier confirmation or measured torque',
            'open_torque_printed':[3.3,.5], 'close_torque_printed':[4.3,.5],
            'oem_stop_degrees':[180,190], 'source_pose_degrees':105,
            'guide':'https://guides.frame.work/Guide/Hinge+Replacement+Guide/104',
            'fasteners':'https://guides.frame.work/Guide/Fasteners+Guide/106',
            'modifications':'reference files unchanged; assembly uses rigid transforms and new separate adapters'}


def build_coupons():
    dest=HERE/'exports/hinge-tests'; dest.mkdir(parents=True,exist_ok=True)
    views=HERE/'views'; views.mkdir(exist_ok=True)
    records=[]; render_parts=[]
    for side,x in [('left',30),('right',108)]:
        y=0; h=12
        fixed=local_hinge(side,105)[3:]
        base,bolts=base_plate(side,x,y,h)
        # FDM fit block with two counterbored nut pockets. Use M2x8 and M3
        # through-bolts for the coupon; tapped steel is the full assembly part.
        bb=base.BoundingBox(); seat=h+BASE_SEAT[side]
        block=box(bb.xmin,-bb.ymax,0,bb.xlen,bb.ylen,seat-3)
        for hx,hy in base_holes(side,x,y):
            block=block.cut(cylinder(hx,hy,-.1,1.15,seat+1))
            pocket=cq.Workplane('XY').polygon(6,4.5/math.cos(math.pi/6)).extrude(2.1).val().translate((hx,-hy,seat-5))
            block=block.cut(pocket)
        block=drilling(block,bolts,3.3,-.1,seat+1)
        # Coupon plate has clearance holes. The actual steel adapter has tap pilots.
        gauge=drilling(base,base_holes(side,x,y),2.3,seat-3.1,3.2)
        export_stl(block,dest/f'{side}-base-block.stl')
        export_stl(gauge,dest/f'{side}-base-seat-gauge.stl')
        export_step(compound([block,gauge]),dest/f'{side}-base-coupon.step')
        export_step(base,dest/f'{side}-base-steel-adapter.step')
        lid,seats,lb=lid_plate(side,x,y,h)
        for hx,hy,seat0,diam,thread,_,_ in lid_holes(side,x,y):
            lid=lid.cut(cylinder(hx,hy,h+9.9,1.15 if thread=='M2' else .9,3.2))
        # One-piece stepped seating gauge, turned over for printing.
        gauge_lid=lid
        for s in seats: gauge_lid=gauge_lid.fuse(s)
        export_stl(gauge_lid.rotate((0,0,0),(1,0,0),180),dest/f'{side}-lid-seat-gauge.stl')
        export_step(gauge_lid,dest/f'{side}-lid-seat-gauge.step')
        render_parts += [{'shape':block,'color':(.23,.55,.68)}, {'shape':gauge,'color':(.66,.69,.73)}]
        render_parts += parts(side,x,y,h,105)
        pivot=(0,-y,h)
        opened=gauge_lid.rotate(pivot,(1,-y,h),-105)
        render_parts.append({'shape':opened,'color':(.83,.49,.21)})
        for hx,hy,seat0,diam,thread,old,new in lid_holes(side,x,y):
            records.append({'part':side+' lid','xy_closed_relative_pivot':[round(hx-x,4),round(hy-y,4)],
                            'height_above_axis':seat0,'hole_mm':diam,'thread':thread,
                            'oem_length_mm':old,'adapter_length_mm':new})
        records.append({'part':side+' base','xy_relative_pivot':[[round(a-x,4),round(b-y,4)] for a,b in base_holes(side,x,y)],
                        'seat_below_axis_mm':-BASE_SEAT[side],'thread':'M2','oem_length_mm':4,
                        'adapter_length_mm':4,'locators_mm':[2.6,2.6],
                        'oem_middle_holes':'2.7 round; 2.7 wide x 3.1 long slot, centres 8.5 apart'})
    (HERE/'hinge-datums.json').write_text(json.dumps({'units':'mm','datums':records},indent=2)+'\n')
    (SOURCE/'sources.json').write_text(json.dumps(source_record(),indent=2)+'\n')
    render(render_parts,views/'hinge-mounts.png','Framework 13: separate stepped base and lid adapters',direction=(1,-2,1.4))
    export_step(compound(p['shape'] for p in render_parts),dest/'hinge-coupon-assembly.step')
    print('exported left/right hinge coupons, steel adapters, datum and source records')


if __name__=='__main__':
    build_coupons()

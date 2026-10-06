"""Required Alpha 1230 seam bonds, separate from the 18 insulated wires."""
from cad import box


def add(m):
    from build import fp,installed,pcb_top
    pairs=[('left-1','left','J2440','center','J2441'),('left-2','left','J2442','center','J2443'),
           ('right-1','center','J2444','right','J2445'),('right-2','center','J2446','right','J2447')]
    for name,a,ar,b,br in pairs:
        x1,y=installed(a,fp(a,ar)['position']);x2,y2=installed(b,fp(b,br)['position'])
        assert abs(y-y2)<1e-5 and abs(pcb_top(a)-pcb_top(b))<1e-5
        center=(x1+x2)/2;h=pcb_top(a)
        m.add('ground-braid-'+name,box(center-10,y-2.38125,h+.1,20,4.7625,.508),
              'cables','Alpha 1230 tinned braid',False,False,braid=True,color=(.70,.73,.76))
        # The straight strip is a nominal starting cut, not a solder-joint
        # shape or strain-relief qualification. Keep the full attachment height.
        reserve=box(center-10,y-2.38125,h,20,4.7625,1)
        m.add('ground-braid-'+name+'-joint-allowance',reserve,'keepout','solder allowance',False,False,braid_allowance=True)
        m.mount('braid/'+name,center,y,h,ar+' / '+br+' solder lands',0,'none',0,'none',
                'main ground bond, never a BMS support or case screw','20 mm starting cut; finished joints and independent retention not qualified',
                nominal_width_mm=4.7625,nominal_thickness_mm=.508)
    m.findings.append('All four required Alpha 1230 seam braids are shown at their actual solder lands. Their clamp integration and soldered shapes remain unresolved; do not omit them to make the case fit.')

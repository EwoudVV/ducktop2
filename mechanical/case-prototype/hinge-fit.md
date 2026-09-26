# hinge mounts

the selected kit is the original Framework Laptop 13 3.3 kg kit. the retained
drawings are revision 0, version 0, dated 27 june 2023: AM3BA000I00 left and
AM3BA000J00 right. the drawings carry the matching 3.3 label. compare the
owned parts and their markings against these drawings before machining.

the seven solids in each STEP stay separate. the lid bracket, small attached
detail and lid reinforcement move together. the shaft, base bracket and
rivets stay with the base. neither side is made by mirroring the other.

## actual attachment pattern

the [hinge guide](https://guides.frame.work/Guide/Hinge+Replacement+Guide/104)
shows three lid screws and two base screws per hinge. its photographs and
the [fastener guide](https://guides.frame.work/Guide/Fasteners+Guide/106)
identify the lid pattern as two M2 screws and one M1.6 screw. the third
3.3 mm hole in the lid bracket belongs to the display mounting arrangement.
it is left unused here. the small 1.3 mm holes are rivet/locating features.

| feature | actual geometry | original screw | prototype adapter screw |
| --- | --- | --- | --- |
| base, round | 2.7 mm | M2 x 4, head 4.6 x 0.6 | M2 x 4 into 3 mm steel |
| base, slot | 2.7 wide, 3.1 long, 8.5 mm from round hole | M2 x 4 | M2 x 4 into 3 mm steel |
| two main lid screws | 3.3 mm, 5.2 mm reinforcement openings | M2 x 2, head 4.5 x 0.5 | M2 x 6 through 3 mm sleeves into 3 mm steel |
| small inner lid tab | 1.9 mm | M1.6 x 3, head 3 x 0.65 | M1.6 x 7 through 3.9 mm sleeve into steel |

lengths exclude the head. the proposed lid screws engage steel by 2.0 mm
(M2) and 2.1 mm (M1.6). verify that the specified M1.6 x 7 length is available
with the required head and check pullout and fit. tap depth and thread relief must be checked on
the actual plate. the drawings show clearance holes, not threads in the hinge.

the left base seats 1.3 mm below the axis; the right seats 2.2 mm below it.
the two main lid seats are 7.0 mm above the axis when closed. the small tab
seats at 6.1 mm. the unused display hole seats at 7.5 mm. stepped sleeves
bridge the used faces to the backing plate at 10 mm above the axis.

the adapter base begins 15.9 mm forward of the axis to clear the right
bracket's transition. separate M3 chassis bolts sit 28 mm forward of the
axis, beyond the OEM screw heads. the mount details and `hinge-datums.json`
give every hole position. do not scale a screenshot for drilling.

## small prints first

`exports/hinge-tests/` contains separate left/right base blocks, base seating
gauges and lid seating gauges. these are geometry checks, not a substitute
for metal reinforcement. print flat on the P1S; the lid gauges are already
turned seating-side up. use a 0.2 mm layer height, at least four walls and
solid material around holes. ream printed clearance holes after printing.

1. place an M2 nut in each open base-block pocket and cover it with the
   seating gauge. check the actual hinge sits flat without rocking.
2. use M2 x 8 screws through the hinge and gauge into those nuts. these
   longer screws are for the printed coupon only. do not use them in the
   3 mm tapped steel adapter.
3. hold the lid gauge against all three stepped seats. use M2 x 10 and
   M1.6 x 10 screws with separate rear nuts for this fit-only gauge.
4. use temporary pins in the unused base locating holes only to compare
   alignment. the case does not depend on those pins or force them into place.
5. check the two base screws with the hinge at 90 degrees and lid screws
   with the panel absent. verify head seating, tool access and end clearance.
6. clamp both base coupons to a rigid straight bar, align their axes and
   attach a light dummy lid. do not start with the display panel. add known
   masses gradually and measure opening, closing and static holding torque.

the CAD does not predict printed creep, thread pullout, hinge wear or impact
strength. the full base needs a continuous rear spine and the lid needs a
continuous cross rail. isolated printed bosses are not the load path.

## torque evidence

the drawings print opening 3.3 +/- 0.5 and closing 4.3 +/- 0.5 **kg-f/cm**.
that slash is dimensionally inconsistent with torque. if the intended unit
is kgf*cm, the nominal pair values are 0.647 N*m opening and 0.843 N*m
closing. these conversions are conditional. they are not inferred from the
marketplace kit name and are not a lid mass rating.

the source also specifies a 180 to 190 degree hinge stop and a 105 +/- 3
degree delivered angle. it allows free motion near the closed/open ends
after cycling. measure the actual pair with the complete lid and use a
temporary lid prop until the holding test passes. installed opening and
cable behavior need the separate assembly sweep.

Framework Computer Inc reference geometry is retained unmodified under
CC BY 4.0. `reference/framework13/sources.json` records URLs, source commit,
hashes, revision and license. the new adapters are separate project parts.

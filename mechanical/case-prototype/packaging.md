# current-board packaging study

the active candidate is a 370 x 282 mm base with a 33.5 mm deck height.
it is not ready for a full case print, powered operation or a CNC order.
the case now uses the saved connector redesign, not the old vertical
Micro-Fit and Mega-Fit assumptions. there is no supported complete minimum
yet: the battery, trackpad, panel, cooler and several signal harnesses still
have unresolved dimensions or qualifications.

the case width keeps the real 358 mm PCB span and both 1.5 mm seams. the
additional 6 mm on each side carries the walls and deck posts. board
material comes from native KiCad STEP exports of the saved Edge.Cuts,
including the notches and holes, rather than rectangular stand-ins.

## assembly datums

all dimensions are millimeters. H is height above the outside bottom;
the exported STEP coordinate is Z=-H. harness inputs use X,Y,H. construction
uses X,-Y,H, followed by a 180 degree X rotation for export. the two
transforms are rotations, not reflections.

| board | native-to-installed XY translation | rotation | bottom H | top H |
| --- | --- | ---: | ---: | ---: |
| left | 0, 0 | 0 | 5.1 | 6.7 |
| center | -30.550001, -36.55 | 0 | 5.1 | 6.7 |
| right | 0, 0 | 0 | 5.1 | 6.7 |
| BMS | 47.35, 91.448 | 0 | 9.1 | 10.7 |
| keyboard | 24.75, 19.7 | 0 | 29.5 | 30.3 |
| radio | 376, 90 | -90 | 20.0 | 21.6 |

the BMS is 80 x 36.148 mm at X145..225, Y150.2..186.348. it sits in the
center board's wider front cutout, not beneath the center board. all five
connectors are on top. the 4 mm relative lift is retained for withdrawal
over the adjacent main board and its hardware, not for obsolete underside
plugs. the older notch rectangle in `board-placement.json` is not used.

`input-audit.json` records the current hashes and each file's last commit.
some source inputs still carry earlier hashes because the electronics work
resaved metadata. the audit compares outlines, holes, footprint poses,
model transforms, pad positions and courtyards before accepting this.
no board geometry is silently adjusted to fit the case.

## height budget

`thickness-study.json` calculates the stack directly from the active
parameters. 33.5 mm is the smallest half-millimeter trial satisfying these
particular stack allowances. it is not a proof that every unmeasured part
fits, or that a different cooler/harness arrangement cannot be thinner.

| driver | required deck height or clearance | basis |
| --- | ---: | --- |
| positioned USB wire below trackpad bridge | 33.454 mm deck | 22.454 wire envelope, 0.5 clearance, 2.5 bridge, 2 free space, 1 click travel, 5 trackpad |
| blower and intake below keyboard | 33.3 mm deck | fan bottom 15.7, body 10.3 +0.3, 3 intake gap, 4 keyboard-to-deck offset |
| actual selected bridge to wire envelope | 0.546 mm | 23.0 bridge underside minus 22.454 positioned wire |
| selected fan envelope to keyboard PCB | 3.2 mm | 29.5 minus 26.3 |
| main underside component to floor | 0.6 mm | reviewed 1.8 maximum body +0.3 planning allowance |
| lowest modeled left pin tail to floor | 0.537 mm | after a separate 0.3 planning allowance |
| panel face to assumed key tops, closed | 2.0 mm | actual assembly coordinates, assumed panel/key thicknesses |
| panel face to radio screw heads, closed | 1.3 mm | modeled 2 mm head envelope above the deck |

the keyboard has no saved backside footprints over the fan inlet. its
carrier has a clearance opening there. this geometric intake gap does not
qualify airflow, pressure drop, noise or thermal capacity.

33 mm leaves only about 0.046 mm under the trackpad bridge and 2.7 mm above
the maximum fan body. it fails the stated 0.5 and 3 mm allowances. a 32 mm
base intersects the current USB envelope under that bridge. lowering the USB front run by 0.5 or 1 mm passes the updated wire-only
checks, but the blower still needs 33.3 mm before half-millimeter rounding.
1.5 and 2 mm drops fail wire separation. the selected arrangement keeps
the original USB height; lower guides and a thinner cooler still need their
own fit and thermal work.

the deck number is not the closed laptop thickness. assumed keys reach
H34.8. the printed lid and its external splice plates reach H44.8 when
closed; the 5 mm feet make that 49.8 mm overall. a one-piece production
lid can remove the external print splices, but that has not been released
as a thinner CNC design.

## guides and strain relief

all 18 wires use the saved connector positions. the source harness and
all four boards share a rigid -1.3 mm height translation in this case.

the revised BMS leads turn around the left and rear of the crowded area,
then enter J2072 from the rear. they clear the board substrate, J2074,
C797, L1 and the other wires. the positive lead is about 119.6 mm including
stripped ends; the return is 126.6 mm. the electrical allowance is 130 mm
each. the fitted CAD inside bend radii are 11.92 and 9.27 mm, above the
8.85 mm project limit. a smooth return-wire rise avoids the tighter bend
introduced by fitting a single spline through the old transition.

no connector, mounting hole, outline or PCB route moved. J2074 remains at
its saved location. the previous 7 mm move is no longer needed for the
power harness.

wire, guide, braid-joint and connector-service intersections are clear in
the current model. so are the known component-height screens. the right
carrier has local relief pockets over U904 and C2069; both are front-side
parts beneath its overhang. their courtyards and maximum heights get an
additional 0.3 mm allowance.

the left main carrier has the same type of pocket over center R2443,
and the right USB carrier has one over center U913. both use the newly
confirmed manufacturer maxima, with 0.3 mm vertical and lateral clearance.

the right PD2 guide ends 5 mm before J2433 instead of 3 mm, leaving
assembly space over R2045. the wire and clamp remain in place. the height
check covers the bare wire beyond each guide end as well as the guide
itself, using the round cross-section and separate fit, wall, position
and curve allowances. all 189 wire/component crossings have a recorded
height basis. fourteen footprints use assembly reservations that still
need a physical check. dimensions and sources are in `component-heights.md`.

the independent separation check uses 0.2 mm allowance on each wire plus
0.05 mm sampling allowance. its minimum is about 0.642 mm. dimensions and
pin maps remain in `docs/hardware/cables-and-connectors.md` and
`docs/hardware/power-harness-fit.md`.

the WAGO body envelopes are 4.5 mm high. short wires are Alpha 6715;
the direct USB pair is Alpha 6716. the 18-wire set does not include a
finished raw battery harness.

the four required Alpha 1230 seam bonds are also shown separately: J2440/41,
J2442/43, J2444/45 and J2446/47. each uses the documented 20 mm starting cut
and 4.7625 x0.508 mm nominal section, with a 1 mm solder-joint reservation.
the guide feet now have windows around all three previously obstructed
braid locations, with 0.4 mm space around the nominal solder reservations.
the formed braid shape, soldered joints and retention under case flex still
need physical checks. no electrical return bond was removed to gain space.

the guide channels use 0.15 mm radial fit clearance and 0.4 mm walls.
these are fit-coupon dimensions, not a tolerance capability claim for a
P1S. open channels follow the real curved paths. split clamp caps have
parting faces that follow each wire's height through the clamp. clearance
holes run through the full cap thickness. the BMS cap has an offset screw
lug clear of both the bend and screwdriver path. slit TPU liners have a provisional 0.025 mm radial grip; screws
close against hard stops. measure the wire and tune the liner before a
pull test. do not rely on friction calculated from an unmeasured TPU part.

the seam pedestals have 1 mm webs within the existing 1.5 mm gaps. their
feet attach from beneath the case. the USB guide has additional ribbed
supports through the spaces between cells, not through their bodies.
the BMS power clamp has a dogleg support through the left inter-cell gap,
clear of the H23 head and the BMS board. the six adjacent right-side wires share one stepped comb. the left
power and return wires share a carrier with a window for their nearby braid.
these hold the harness independently of the removable input deck. the
right support includes open-bottom raw-lead crossing slots. its reduced
section and every long guide require a deflection test under a dressed
harness: the curve assumption is only valid if the wires stay within
the recorded 0.2 mm position allowance.

the J2 fixture is separate from the BMS supports. its short straight
pigtails illustrate only the known connector exit and local clamp fit.
J2 pin 1 is negative at Y169.448; pin 2 is positive at Y173.448. finished
pack lead exits, usable lengths, pack outline and any splice insulation
must be measured before completing that route. nothing connects the BMS
return domains through mounting hardware.

## mounts and service order

the mounting schedule retains all 13 isolated main-board mounts and all
four current BMS Edge.Cuts holes. H24 is at X156.75, Y145.5. the main
supports are short custom insulating parts; the proposed M2.5 x4 top
screws give 1.9 mm engagement after the 1.6 PCB and 0.5 washer. this short
engagement needs a physical pullout test. BMS screws, washers, supports and
underside fasteners remain insulating. modeled top hardware is at most
5 mm in diameter with a 2.5 mm head/washer stack.

Mu H1/H2 stay M2 module supports, not chassis mounts. H3/H4 remain card
retainers. radio H1-H4 are in the radio's own coordinate system. all mount
locations, thread choices and unverified lengths are in
`mounting-schedule.csv`.

radio retention now includes screw, washer and nut envelopes. the proposed
M2 x16 screws are trimmed to 15.5 mm, with 6 mm insulating washers and
1.5 mm nut engagement. their length is limited by the closed lid above
and the packs below, not rounded up to an arbitrary 20 mm screw.

1. fit the rear spine, hinge towers and captured nuts before their adapters.
2. fit case-mounted harness feet, insulating PCB supports and the bare boards.
   check that feet do not touch backside parts or copper.
3. install the wire guides and liners. lay in each numbered wire, make the
   terminal connections while supporting the wire, then close the clamps.
4. inspect polarity and independent return isolation before connecting cells.
5. fit cooling hardware only after resolving the Ultra contact and retention
   design. keep its load off the cells and signal connectors.
6. install the input assemblies and removable deck last. the trackpad bridge
   takes clicking and palm loads through the deck, not through the packs.
7. for service, disconnect external power and the packs first. open the lid,
   unplug the input modules as needed and remove the deck/keyboard/bridge.
   remove the relevant clamp cap before releasing a terminal. the fixed
   pedestal stays in the case while the wire is supported.
8. XT30 needs 14 mm axial withdrawal. its nearby guide section must be
   removed first. BMS SH/GH housings need their saved 5 mm withdrawal
   envelopes plus real latch/finger access. use the interference report;
   release the two cell-gap screws and lift the USB upper rail before
   withdrawing a plug; the lower feet stay in the case.

top button/tool corridors and BMS withdrawal volumes are explicit keepouts.
the check distinguishes a closed assembly from the service state. full
finger ergonomics and exact driver head choices still require coupons.

the USB carriers now have detachable upper sections. their narrow blades
locate in fixed seam feet, and two nylon M2 screws at each cell-gap post
hold the rail down with at least 2.5 mm thread engagement. the checker
allows only the designed shaft engagement inside each named post; it
continues checking the rest of the screw for interference.

the final service check includes the BMS screwdriver corridor and right
XT30 withdrawal. neither requires removing the main-board row. actual
tool and finger access, pilot fit and pull strength still need coupons.

both prototype speaker cups sit in the left palm area. this avoids the
USB turn and optional radio corridor without making the base taller. their
close stereo spacing and acoustic behavior are not a final audio layout.

## hinges, lid and cooling

the actual handed Framework 13 assemblies, their coaxial pivots, stepped
seats, tapped steel adapters, sleeves and rear/lid reinforcement are kept.
the source drawings are revision 0, dated 2023-06-27, from Framework's
published reference commit. the user selected the original 3.3 kg kit;
physical markings and coupon seating still need confirmation.

`assembly-checks.json` samples 0..180 degrees in 2 degree steps against
the current fixed assembly, including wires and guides. it reports actual
collision angles rather than treating the hinge's own stop as case travel.
sampling does not prove continuous collision freedom between poses.

the eDP annular bend corridor and service-slack bay remain reservations,
not a solved constant-length cable. actual display connector position,
dynamic bend specification, strain relief and full-motion pinch testing
are open. therefore the lid motion is not cable-qualified even if the
rigid-part sweep is clear.

both 226V and 256V use the same corrected Mu Ultra module/socket geometry
in this study. no N305 cooler is used. the Delta fan has a modeled cradle
and attachment holes. the cold plate, heatpipe and fin stack are still
proposed envelopes, not a released or thermally tested Ultra cooler. their
contact interface, mounting load, airflow path and capacity for each CPU
must be resolved before the 33.5 mm candidate can become a complete fit.

lid mass/COM and stability calculations remain assumption-based. the
original 3.3 kg product label is not a supported-lid-mass specification.
use the existing hinge coupons and a restrained dummy lid for holding
torque and mounting-load tests before a complete print.

## measurements still needed

| item | known basis | still open |
| --- | --- | --- |
| PCB outlines, holes and footprint poses | saved board files | fabrication tolerances and first-article fit |
| WAGO 4.5 mm bodies and wire OD/bend data | retained manufacturer/electronics inputs | spring-tool access and assembled wire position |
| panel 352 x227 | recorded plan dimensions | complete thickness, brackets, connector, mass and COM |
| three packs 100 x60 | recorded footprints | finished thickness, tabs, lead exits, usable lengths and swelling specification |
| trackpad 140 x105 | recorded footprint | complete body, connector, mounting features and click travel |
| keyboard | saved 273.5 x80 PCB and switch poses | keycap height/travel and support deflection |
| speakers and OLEDs | recorded/assumed module envelopes | complete bodies, fasteners, cable exits and acoustic cavities |
| Ultra cooling | corrected module STEP and selected fan dimensions | complete cooling assembly and tests on both CPUs |

the 11 mm pack shown in CAD uses the nominal listing recorded in the
current hardware notes, not a measured maximum. the current radio pose
allows roughly 11.0 mm finished pack thickness
after the chosen padding, 3 mm swelling reservation and 0.5 mm clearance.
the trackpad bridge permits more, about 16.1 mm under the same assumptions.
the radio, not the trackpad, therefore limits the illustrated right pack.
do not substitute these allowances for actual pack measurements.

## frozen PCB snapshot

`reference/pcb-snapshot/` pins the six reviewed native STEP exports,
inventory and source records. this prevents concurrent electronics saves
from silently changing the case halfway through a build. the live project
PCBs remain untouched. the exact snapshot hashes, rather than a claim
about the latest live working tree, identify this mechanical revision.

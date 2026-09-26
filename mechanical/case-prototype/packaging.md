# case packaging

the active model is the **35 mm compact study**. it does not fit the saved
power harnesses. their bodies and wires are kept in the assembly so the
conflicts can be inspected. `current-hardware` is the 73 mm clearance
reference, selected through the same CAD source. neither profile is ready
for a full case print or CNC order.

the base is 370 x 282 mm. the saved main boards already span 358 mm. the
extra 6 mm on either side carries walls and deck posts outside the boards.
the extra depth provides a rear hinge area and space beyond the cells,
which already end at Y=248. the previous 358 x 248 outside target cannot
contain those parts plus walls and mounting structure.

## datums and board poses

all dimensions are millimeters. the assembly STEP keeps the installed
board X/Y coordinates, with front at positive Y. Z=0 is the outside bottom
plane of the base; positive Z points down. a part at height 8 therefore
has Z=-8. the CAD builder and viewer use X,-Y,height and rotate the whole
assembly 180 degrees about X for export. imported parts are never mirrored.

| board | native-to-installed translation X,Y | rotation in placement convention | bottom height, compact | top height, compact |
| --- | --- | --- | ---: | ---: |
| left | 0, 0 | 0 | 6.4 | 8.0 |
| center | -30.550001, -36.55 | 0 | 6.4 | 8.0 |
| right | 0, 0 | 0 | 6.4 | 8.0 |
| BMS | +47.35, +91.448 | 0 | 10.4 | 12.0 |
| keyboard | +24.75, +19.7 | 0 | 31.0 | 31.8 |
| radio | +376, +90 | -90 | 20.0 | 21.6 |

the first four XY transforms are the saved assembly baseline. their Z
positions and both keyboard/radio poses are proposed. all six source hashes
are in `board-inventory.json`; rebuilding refuses a changed PCB until the
inventory has been refreshed and reviewed. the native KiCad export retains
the real notches, arcs and drilled holes. the center is not placed at its
raw file coordinates.

the BMS occupies X154.05..215.95, Y150.2..186.348, beside the center PCB in
its cutout. it is raised 4 mm relative to the main boards for underside
control/probe plugs. it is not stacked underneath the center board.

the keyboard is centered at X42.25..315.75, Y20..100. its carrier uses
edge clips and underside pads outside the saved backside courtyards. no
holes are added to the keyboard. the right edge has a cable-release opening.
actual pad contact, keycap sizes, key travel and carrier deflection need a
first-article check.

the optional radio occupies X286..356, Y110..230. its four H1-H4 supports
hang from the removable deck. its SMA axes face +X through the right side
at Y133 and Y198, height 21.98 in the compact profile. the connectors'
underside reaches height 18.02. that is only 1.62 mm above the assumed
cell thickness plus swelling allowance. measure the complete packs before
keeping this pose. the two DRA818 bodies use the existing 35.6 x 19 x 4 mm
project model at J70/J71; their saved footprints had no attached model.
the 20 mm diameter, 45 mm long SMA tool/plug corridors are allowances,
not a selected antenna model. external antennas are required for this
aluminum-case arrangement; internal antenna placement is not qualified.

## what sets the height

| stack | compact-model height above the base bottom | status |
| --- | ---: | --- |
| main PCB top | 8.0 | 1.6 mm board, proposed 4 mm insulating supports |
| Mu/socket model top | about 17.74 | current PCB model placement; no cooler included |
| cold plate | 18..20 | proposed contact envelope, TIM and fastening unverified |
| flat heatpipe | 20.5..23.5 | proposed envelope |
| fin top | 24 | proposed fin envelope, not a thermal result |
| Delta BFB04512HHA-CZ0T body | 17..27.3 | manufacturer lists 45 x 45 x 10.3 mm; sample/mount fit pending |
| keyboard carrier | 26.5..28.5 | manufactured carrier geometry |
| keyboard PCB | 31..31.8 | saved 0.8 mm board, proposed Z |
| key envelope top | 36.3 | assumed 4.5 mm above PCB; actual caps/travel pending |
| deck top | 35 | compact target |
| trackpad bridge bottom | 24.5 | separate load path to deck |
| trackpad body | 30..35 | assumed 5 mm thickness |
| cell body top | 13.4 | assumes 10 mm complete thickness and 1 mm pad |
| cell swelling reservation top | 16.4 | assumption, not a pack specification |
| current Micro-Fit mated body top | 25.64 | before wire bends |
| current individual power-wire arch top | about 62.36 | 100 mm wires, 17.78 mm radius, actual pin positions |
| BMS protected-power mated body top | 29.56 | before wire bends |
| BMS raw Mega-Fit mated body top | 28.78 | before wire bends |

the power wire arches cross the compact keyboard carrier by about 35.86 mm.
even the bare BMS plug bodies cross the trackpad bridge by 5.06 mm and
4.28 mm. a shorter enclosure cannot fix those conflicts by itself.

an optimistic current-harness stack is 62.36 mm to the highest individual
wire, 1 mm clearance, 2 mm carrier, 2.5 mm backside component space,
0.8 mm keyboard PCB and 4.5 mm key envelope: 73.16 mm to the keys. this
still does not resolve the wire-bundle crossings. after a horizontal-exit
power change, the module/cold-plate/heatpipe/keyboard stack is roughly
34 mm to the keys with the stated allowances. that is the basis for the
35 mm deck study, not a promise that the pending power/cooling design fits.

the height after connector changes is still controlled by cooling, the
keyboard carrier and key stack. the fan part recorded at J52 is
[Delta BFB04512HHA-CZ0T](https://www.delta-fan.com/technology/BFB04512HHA-CZ0T.html),
45 x 45 x 10.3 +/-0.3 mm. the revision-00 drawing gives three 2.8 mm
mounting holes on a 38.5 mm pattern. the cradle includes this pattern with
M2 through-bolts and washers; the centered 3.25 mm body-edge datum needs a
sample check. its body has a clearance window in the keyboard carrier;
the 0.8 mm keyboard PCB stays intact. the remaining intake plenum under the
keyboard is small. the cold plate/heatpipe/fins still need an Ultra cooler
design, and neither airflow, recirculation nor 256V thermal capacity is qualified.
the older N305 cooler is not used.

the pending 100 W power reservation remains visible as a separate volume.
it overlaps parts of the compact support stack. its component heights and
placement have to be agreed with the power layout before enclosure height
is frozen. this mechanical work does not restore or implement that redesign.

## connector changes to review

these are proposals, not edits to the saved boards. keep the signal maps,
return-domain isolation, current rating and electrical qualification with
the electronics work.

| location | current constraint | concrete mechanical proposal |
| --- | --- | --- |
| J2430/J2431, 12 contacts | vertical 43045-1212 and tall 18 AWG return loops | review a right-angle 12-contact header, with both exits aimed along a free board corridor rather than into the 1.5 mm seam |
| J2432/J2433, 10 contacts | vertical 43045-1012 and tall return loops | same change for the 10-contact pair; lay the bend in XY and retain the numbered-wire map |
| center J2071 / BMS J2072 | 17.56 mm vertical mated stack; 15.51 mm origin separation | review right-angle two-contact parts and an in-plane route; target complete body/wire envelope below height 23.5 in the trackpad area |
| BMS J2 | raw-pack plug already exceeds the bridge underside before bends | review a horizontal-entry raw-pack connector or a separately strain-relieved low-profile termination, preserving the existing circuit requirements |

Molex [43045-1210](https://www.molex.com/en-us/products/part-detail/430451210)
and [43045-1010](https://www.molex.com/en-us/products/part-detail/430451010)
are concrete dimensional candidates: 12/10 contacts, right angle, 10.29 mm
listed mated height. [43650-0203](https://www.molex.com/en-us/products/part-detail/436500203)
is a two-contact right-angle candidate listed at 6.98 mm. verify exact
plating/contact combinations, current derating, footprints, plug length,
latch access and horizontal keepouts. these are not drop-in substitutions.
their bodies have not replaced the current parts in the CAD.

the current mated-plug solids are conservative envelopes around the saved
pin locations, using the recorded 17.64/17.56 mm stack heights. they are
not detailed manufacturer latch/shell STEP models. several connector STEP
files are missing from the installed KiCad library. exact housing outlines,
latch motion and external plug overmoulds remain part of the fit checks.

the 75 mm BMS wire budget cannot use the same 17.78 mm-radius arch assumed
for the main looms: that screen needs about 122.6 mm. the visible BMS
candidate uses a 7 mm radius and therefore needs a specifically qualified
flexible wire, or the connector/route change above. individual main-loom
arches also intersect one another. their bend calculations do not establish
that the complete numbered bundle can be assembled.

## hinge and lid load path

the OEM hinges bolt to independent 3 mm steel adapters. captured M3 nuts
in the base towers and a continuous rear spine carry the base loads. the
lid adapters use stepped sleeves into a continuous aluminum cross rail.
the left/right 1.3/2.2 mm base offsets and the small inner M1.6 lid tab
are retained. details, original screw sizes and coupon hardware are in
`hinge-fit.md` and `drawings/hinge-left.svg` / `hinge-right.svg`.

the rear walls are relieved for the lid heel. the upper tower support sits
under the forward base foot, leaving space behind the axis. a slot in the
lower lid rail and bezel provides an eDP passage. the 10 mm radius bend
corridor is separate from the shaft, and a planar 52 x 21 x 6 mm bay holds
the service-loop allowance. the required pay-out allowance is about
31.4 mm over 180 degrees, plus 25 mm service slack. connector positions,
vendor bend limits and the actual constant-length cable still need fitting.

the complete lid estimate is around 0.88 kg using the CAD volumes,
material-density assumptions, a 0.4 kg panel assumption and 40 g for cables,
gaskets and screws. `assembly-checks.json` contains the current calculated
mass, center of mass, angle-dependent gravity torque and a separate base
stability screen. near-horizontal torque is about 1.0 N*m. the original
hinges must be tested with a dummy lid and added weights. the printed
torque unit in the Framework drawing is ambiguous; no marketplace mass
rating is inferred. use a temporary prop during the first loaded tests.

## assembly and access

1. print and check the small hinge gauges first. compare the owned kit's
   hole positions, steps, rivets and markings. fit the screws without the panel.
2. join the four base tiles with the underside splice plates. install the
   rear metal spine, tower foot bolts and underside nuts. the tower access
   bores are used before the hinge adapter plates are installed.
   the left tower has a relief for the saved F195 fuse holder. remove the
   hinge adapter before withdrawing F195 unless the actual tool/withdrawal
   path has been proven with the shorter M3 x 6 adapter screws.
3. load the captured M3 nuts into the tower pockets and fit the steel
   adapter plates. use the full continuous metal spine for lid-load tests;
   the split metal-part STLs are fit gauges only.
4. fit insulating main-board supports and all four BMS supports. install
   the main boards and BMS with insulating fasteners. keep H1/H2 Mu and
   H3/H4 M.2 supports as their own assemblies. check solder-tail clearance.
5. fit ground braids, signal FFCs, power wiring, underside BMS control/probe
   harnesses and the pack fuse access. this step cannot be completed in the
   compact profile with the currently modelled power harnesses.
6. fit the cell trays and their outside tabs. dress the tabs, tap wires and
   probes using measured complete pack outlines. straps retain the trays
   without compressing the pouches. no palm or click load goes through them.
7. assemble the removable deck separately: keyboard carrier/pads/clips,
   independent trackpad bridge, OLED trays, speaker cups and optional radio
   suspension. the radio antennas and SMA plugs must be removable before
   lifting the deck. check all long screw tips against lower components.
8. fit the cooler cradle and selected cooling parts. establish TIM contact,
   fastener loads and airflow using the actual Ultra parts before powered use.
9. join the lid tiles, install the cross rail and stepped hinge seats, then
   install the hinges with the panel absent. this exposes all three lid
   fasteners. install the panel on soft perimeter pads and shoulder stops,
   then fit the removable bezel. screws must not load the LCD glass.
10. hold the lid at 90 degrees while installing the two base screws per
    hinge. install the eDP cable with clamps on both sides and service slack.
    check the full travel by hand with a dummy cable before using the panel.
11. connect the deck harnesses with a supported service loop, lower the
    deck and tighten its perimeter screws. verify keyboard deflection,
    trackpad click travel, cable release access and cell clearance.
12. weigh the base/lid and measure the actual center of mass and hinge
    holding force. repeat fit checks with the real plugs and cables before
    thermal testing or ordering a machined case.

the seven deck screws are accessed from above. board screws require the
deck to be removed. the BMS underside connectors require the BMS to be
lifted after its power has been isolated. the lid hinge screws require the
panel/bezel to be removed. the mounting CSV records reference, XYZ, mating
part, hole/thread, support height, screw length, insulation and status.

## measured, manufacturer and assumed

no new physical measurements were taken for this model.

- saved-board data: outlines, holes, placement, footprint references and
  model transforms, verified against all six SHA-256 hashes.
- manufacturer reference: Framework STEP/drawing geometry, part numbers,
  revision and fastener guide; the corrected Mu Ultra/socket model;
  retained connector/wire dimensions cited in the hardware documents.
- recorded owned-part plan sizes: panel 352 x 227, cells 100 x 60 each,
  trackpad 140 x 105, speakers 38 x 18. these were not remeasured here.
- assumptions: panel thickness/mass/flanges/connector; complete pack
  thickness/tabs/protection boards/mass/swelling; trackpad thickness,
  click mechanism and plug datum; speaker depth/cavity/retention; OLED
  module mounting; keycaps; cooler/TIM/fan hardware; all proposed Z poses.

the `views/` sections come from intersections of the actual CAD solids.
`component-coverage.json` lists missing or omitted PCB models. a clean
case sweep does not prove component, wire-bundle or thermal qualification.

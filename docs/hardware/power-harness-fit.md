# power harness fit

5 october 2026. the connector positions are saved on the boards. the
wire paths are a case-layout input, not a finished cable assembly or an
approved case thickness.

- [wire paths and connector coordinates](../../mechanical/power-harness.json)
- [top view](../../mechanical/power-harness.png)
- [pin maps and parts](cables-and-connectors.md)
- [electrical acceptance limits](io-power-qualification.md)
- [component positions and heights](../../mechanical/component-placement.csv)

run `python gen/generate_power_harness_geometry.py` after refreshing the
board datums. it checks the source-board hashes, bend radii, wire lengths
and separation between the modelled wires. a stale board export stops it.

## connector positions

these are installed top-view coordinates in mm, using the same origin as
the board layout. rotations follow KiCad. the full component export above
includes the revised placement on both sides of the main boards.

| board | part | x | y | rotation / side |
| --- | --- | ---: | ---: | --- |
| center | J2452, right auxiliary rails | 282.45 | 64.50 | 270, front |
| center | J2462, right return | 281.45 | 80.00 | 180, front |
| center | J54, skin/hinge temperature | 274.00 | 75.00 | 180, front |
| center | J2071, protected BMS power | 111.45 | 173.848 | 270, front |
| right | J2453, auxiliary rails | 320.55 | 64.50 | 90, front |
| right | J2463, return | 324.55 | 115.40 | 90, front |

the right auxiliary wires now run above the signal connectors in the top
view. the separate return goes around their front ends. J2463's plastic
body projects about 0.35 mm beyond the front PCB edge; its solder lands
remain on the board. allow for the housing and its tolerance in the case.
U1760 is underneath the right board at x332.8, y48.7. its maximum body
height is 1.45 mm; reserve 1.75 mm below the solder plane with the 0.3 mm
assembly allowance. check that against the case floor and supports.

the revised power circuit and component placement are saved. the main-board
routing and the complete cable assembly still need finishing.

## clearance above components

the component export includes manufacturer height limits for the audio
codec, speaker amplifier, crystals, fuse, ferrites and small capacitors
under the proposed wire paths. the latest height check covers 13 parts
at 15 crossings. all clear the wires with a separate 0.3 mm assembly
allowance; the smallest remaining gap in this group is 3.90 mm at Y900.

i still need exact dimension drawings for C430/C431, C434 and C917's
stored Murata part numbers. the wire paths allow a body height of 3.45 mm
at C917 and at least 9.75 mm at the other three parts after the assembly
allowance. keep those limits when choosing or checking the fitted parts.

## wire space

the model uses main-board top surfaces at z = 8 mm and a BMS top surface
at z = 12 mm, measured above the outside bottom of the case. these came
from the case study and can change. they are not a thickness requirement.

the short looms use Alpha 6715, 18 AWG, with 1.7526 mm maximum outside
diameter. the direct USB pair uses Alpha 6716, 16 AWG, at 2.1082 mm maximum.
the current manufacturer pages specify a 5D minimum bend radius. the model
checks the inside radius of each curve, plus a 1% numerical allowance.
the old 2010 6715 sheet said 10D; that separate sensitivity result remains
in the geometry file.

the WAGO links use 8 mm stripped ends within the allowed 7..9 mm range.
the main-board links fit the existing 20..100 mm electrical bounds.
the protected BMS leads have modelled cut lengths of 108.7 mm for FG_VSS
and 106.1 mm for positive, within a 120 mm budget. their minimum inside
bend radii are 10.46 and 9.12 mm. the loops enter the rear-facing terminal
straight, with separate guides keeping the wires apart. the direct USB wires fit the
400..420 mm bounds, including a provisional 2 mm hidden at each solder cup.
confirm that allowance on a soldered sample before making a cut template.

the long pair has gentle service loops and different heights at the
crossover. the BMS pair now follows its actual connector endpoints, with
2 mm straight exits and a smooth rise between the two board heights.
its wire envelope reaches 17.95 mm above the study datum. repeat the full
component and case clearance check with the final clamps and supports.

the wire model allows 0.2 mm position error around each path. guides and
strain relief have to hold that shape; loose hand-dressed wires are not
proven to fit by this calculation. the highest wire reaches about 23.75 mm
above the case datum before adding a clamp. do not use that number to
declare the 35 mm case study valid.

keep both Alpha 1230 ground braids across each seam. their nominal section
is 4.7625 x 0.508 mm. reserve up to 1 mm above the PCB at their soldered
attachments and check the finished joints. the electrical requirement is
still at most 1 milliohm for each complete connection, including its joints.

## plugs, access and strain relief

the WAGO bodies are 4.5 mm high. their release buttons need access with the
keyboard or bridge removed. support the wires while releasing them; do
not pull against the soldered terminals. clamps must attach independently
to the case or a removable support, not to components or battery cells.

reserve 6 mm above the PCB for the complete XT30 connection and 14 mm of
axial withdrawal space. grip its housing when unplugging it. insulate the
solder cups separately and release the cable support before removal.

the raw-pack connector J2 is now a two-contact WAGO 2060-452/998-404,
4.5 mm high, at installed XY (218.35,171.448), facing right. pin 1 is raw
negative and pin 2 is raw positive; J2201 carries the two cell taps separately. leave access above
the release buttons and use separate strain relief. the cells' lead exit
positions and usable lead lengths are still missing, so the raw-pack cable
has no finished route.
all five BMS cable connectors are now on top. J2072, J2074 and J2200
face rearward; J2 and J2201 face right.
[plug and withdrawal envelopes](../../mechanical/bms-connector-access.json)
and [connector-clearance checks](../../mechanical/bms-connector-clearances.json)
record the installed positions and reference dimensions. remove the bridge
for button, latch and housing access. the control and temperature cable
routes still need to be included in the complete assembly clearance check.

## still needed from the complete assembly

the old planner records three user-measured 100 x 60 mm cells. it explicitly
leaves thickness and tabs unmeasured. the case's 10 mm thickness is an
assumption. measure the complete finished packs, including their wiring
and insulation.

the case work still needs the actual clamps, fasteners, insertion/removal
paths, signal cables, measured packs, cooling and keyboard/trackpad supports
checked together. repeat the component-height check if parts or wire paths
move. resistance, temperature and fault tests remain
separate requirements; the hardware qualification flags are still off.

## drawings used

- [Alpha 6715](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6715) and [6716](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6716)
- [Alpha 1230 braid](https://www.alphawire.com/products/accessories/fit-wire-management/braid/1230)
- [AMASS XT30PW-F30 drawing](https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf)

for the revised BMS pair, the maximum modelled wire envelope is 17.95 mm
above the case study origin. that is about 5.95 mm above its 12 mm PCB
top datum. the wire-to-wire screen keeps at least 0.65 mm after sampling
and positioning allowances. these curves require guides and separate
strain relief; loose wires are not constrained to the model.

the 120 mm per-wire allowance adds at most 57.6 mV drop and 0.461 W
combined wire loss at 8 A if the finished wire meets the existing
30 milliohm/metre hot-resistance criterion. contacts and solder joints
are additional and still need measurement.

[the BMS wire-height check](../../mechanical/bms-wire-clearances.json) covers
19 component and support crossings. H24 needs a low screw head and washer:
2.5 mm is reserved, against a 3.7 mm limit under the control-plug withdrawal
path at the study heights. the closest mated connector clears a planned
5 mm mounting-hardware diameter by 0.52 mm. verify the actual hardware
and guides when fitting the case.

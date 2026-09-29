# power harness fit

28 september 2026. the connector positions are saved on the boards. the
wire paths are a case-layout input, not a finished cable assembly or an
approved case thickness.

- [wire paths and connector coordinates](../../mechanical/power-harness.json)
- [top view](../../mechanical/power-harness.png)
- [pin maps and parts](cables-and-connectors.md)
- [electrical acceptance limits](io-power-qualification.md)

run `python gen/generate_power_harness_geometry.py` after refreshing the
board datums. it checks the source-board hashes, bend radii, wire lengths
and separation between the modelled wires. a stale board export stops it.

## saved placement changes

these are installed top-view coordinates in mm, using the same origin as
the board layout. rotations follow KiCad. none of these parts had tracks
attached. the existing tracks, vias, outlines, mounting holes and pad nets
were preserved. the BMS component positions are unchanged; its separate
assembly check moved two vias clear of the WAGO solder-mask openings.

| board | part | x | y | rotation / side |
| --- | --- | ---: | ---: | --- |
| center | J2452, right auxiliary rails | 282.45 | 64.50 | 270, front |
| center | J2462, right return | 281.45 | 80.00 | 180, front |
| center | J54, skin/hinge temperature | 274.00 | 75.00 | original rotation, front |
| center | J2071, protected BMS power | 111.45 | 173.848 | 270, front |
| right | J2453, auxiliary rails | 320.55 | 64.50 | 90, front |
| right | J2463, return | 324.55 | 115.40 | 90, front |
| right | C161, HDMI buffer bypass | 331.00 | 65.00 | 0, front |
| right | C158, HDMI switch input | 304.00 | 61.80 | 0, front |
| right | U1760, USB power switch | 303.25 | 47.50 | same x/y, moved underneath |

the right auxiliary wires now run above the signal connectors in the top
view. the separate return goes around their front ends. J2463's plastic
body projects about 0.35 mm beyond the front PCB edge; its solder lands
remain on the board. allow for the housing and its tolerance in the case.
U1760 needs a 1.6 mm component allowance below the right board, including
solder. check that against the final case floor and supports.

the placement changes add no physical DRC errors. the right board has none;
the center board still has existing routing and clearance errors. this is
not a claim that the main boards are ready to order or route without the
remaining power integration and checks.

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
their calculated cut lengths fit the existing 20..100 mm electrical bounds.
the protected BMS pair fits its 90 mm budget. the direct USB wires fit the
400..420 mm bounds, including a provisional 2 mm hidden at each solder cup.
confirm that allowance on a soldered sample before making a cut template.

the long pair has gentle service loops and different heights at the
crossover. the blue BMS pair rises over the power FETs, with about 1.9 mm
side clearance from the fuse body. the fuse courtyard includes its much
wider solder lands, so a courtyard crossing alone is not a body collision.

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

the raw-pack connector is Molex 43045-0400 with a 43025-0400 housing and
43030-0038 tin contacts. the detailed plug drawing gives 10.81 mm mated
height and 11 mm for latch movement. the case reservation is 11.35 mm
above the BMS to include drawing tolerance. this is larger than the
catalogue's 10.29 mm summary, which is not the clearance envelope used here.

Molex's board-edge dimension starts at the front pin row. the saved board
has 9.80 mm against a 10.16 mm maximum. limit the combined header and board
edge positioning error to 0.25 mm toward that limit. reserve 14 mm axial
withdrawal and room above the latch with the trackpad bridge removed.

leave at least 12.7 mm of relaxed wire behind that four-contact housing
before any bend, twist or clamp. the cells' lead exit positions and usable
lead lengths are still missing, so the raw-pack cable has no finished route.
the isolated BMS control and temperature cables also need to be included
in the complete assembly clearance check.

## still needed from the complete assembly

the old planner records three user-measured 100 x 60 mm cells. it explicitly
leaves thickness and tabs unmeasured. the case's 10 mm thickness is an
assumption. keep the protection boards, wiring and insulation in the final
pack measurements.

the case work still needs the actual clamps, fasteners, insertion/removal
paths, signal cables, measured packs, cooling and keyboard/trackpad supports
checked together. repeat the component-height check after the new 100 W
power parts are placed. resistance, temperature and fault tests remain
separate requirements; the hardware qualification flags are still off.

## drawings used

- [Alpha 6715](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6715) and [6716](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6716)
- [Alpha 1230 braid](https://www.alphawire.com/products/accessories/fit-wire-management/braid/1230)
- [Molex header drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43045/430450400_sd.pdf)
- [Molex plug drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43025/430250400_sd.pdf)
- [Molex mating and wire-dressing instructions](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/applicationspecificationspdf/430/43045/430450001-AS-000.pdf)
- [AMASS XT30PW-F30 drawing](https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf)

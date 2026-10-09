# power harness fit

6 october 2026. the BMS power leads now clear the board edge and control
plug with the existing connector positions. the case uses revised guides,
removable USB rails and reliefs for the ground braids. this is a checked
CAD arrangement, not a physical fit or thermal qualification.

the separate [flush case](../../mechanical/flush-case/README.md) now has a
shorter USB power route behind the keyboard. its calculated ground/5 V
cut lengths are 338.2/348.9 mm, and the guide rails attach to removable
keyboard-carrier tabs. it retains the 420 mm electrical length ceiling.
the 400–420 mm USB cutting range and cell-gap carriers described below
belong to the earlier case. the other sixteen power paths are unchanged
apart from the common board-height translation.

- [wire paths and connector coordinates](../../mechanical/power-harness.json)
- [BMS route and height view](../../mechanical/bms-power-route.png)
- [wire and body checks](../../mechanical/power-harness-checks.json)
- [case clearance results](../../mechanical/case-prototype/harness-case-checks.json)
- [pin maps and parts](cables-and-connectors.md)
- [electrical acceptance limits](io-power-qualification.md)
- [component positions and heights](../../mechanical/component-placement.csv)
- [component clearance details](../../mechanical/case-prototype/component-heights.md)

## BMS power leads

both wires leave the center terminal straight, turn around the left and
rear of the crowded area, then enter the rear-facing BMS terminal. the
return has a smoother height transition so the fitted CAD curve also
meets the wire bend limit. J2074 stays at its saved position; the proposed
7 mm connector move is unnecessary for these paths. no PCB geometry or
routing changed.

| lead | modeled cut length, including two 8 mm stripped ends | minimum inside bend radius in the fitted CAD |
| --- | ---: | ---: |
| FG_VSS protected return | 126.6 mm | 9.27 mm |
| protected positive | 119.6 mm | 11.92 mm |

the electrical length allowance is now 130 mm per wire. using the existing
30 milliohm/metre hot-resistance acceptance limit, both wires contribute
at most 62.4 mV drop and 0.499 W loss at 8 A. contacts, solder and PCB
copper are additional. [the battery-path calculation](battery-path.md)
uses the same length constant as the geometry checks.

the routing check covers the center and BMS substrates, mated BMS plugs,
withdrawal envelopes, mounting hardware, manufacturer component heights
and the other sixteen power wires. it measures bend radius on the fitted
CAD edge, rather than relying only on the original sampled curve.

clearance includes 0.2 mm wire-position allowance, 0.15 mm guide fit,
0.4 mm guide walls, 0.3 mm body clearance and a separate sampling/curve
allowance. the closest two BMS wires have about 0.67 mm surface separation
after the wire allowances. their guide walls share one carrier.

J58 reserves 4 mm above the PCB for the soldered trackpad cable and
insulation. H24 and the BMS mounting points reserve 2.5 mm for screw heads
and washers. these are assembly limits to check on the fitted parts.
the raw-pack leads, taps, probe leads and control cable are separate from
the eighteen-wire power model.

## guides, braids and service

the clamps use split TPU liners and hard stops. their parting surfaces
follow the local wire height so a rising cable is not trapped in a closed
bore. the BMS clamp has an offset screw lug that leaves room for the wire
bend and its screwdriver.

the left power and return wires share a carrier. the left and right
carriers have windows around the required seam braids and their 1 mm
solder-joint reservations. local pockets in the right carrier clear U904
and C2069, including their maximum heights and an added 0.3 mm allowance.
all four electrical ground bonds remain in place.

the left carrier has another pocket above center R2443, and the right
USB carrier has one above U913. these also include 0.3 mm around the
courtyard and above the manufacturer's maximum height.

the right PD2 guide stops 5 mm before J2433's wire entrance, 2 mm earlier
than the other short guides. this leaves room over R2045 while retaining
the nearby clamp. the wire path, cut length and terminal position are
unchanged. the exposed wire section is still included in the clearance check.

the height screen uses the round guide profile, the real guide ends and
maximum component heights with 0.3 mm assembly space. it also includes
the 0.15 mm guide fit, 0.4 mm wall, 0.2 mm wire-position allowance and
sampling/curve allowance. all 189 wire/component crossings have a height
basis and clear the chosen allowances. fourteen footprints use explicit
assembly reservations for connectors, joints, pads or hardware. those
reservations still need confirmation on the fitted assembly.

the USB guide rails lift off their fixed feet after releasing two screws
at each cell-gap post. narrow locating blades lift through the board
seams; the wider feet stay below the PCBs. this lets the plugs and terminal
buttons be reached without removing the complete main-board row. the
release screws have at least 2.5 mm modeled thread engagement. only their
intended threaded volumes are excluded from the collision results.

remove the deck and input assemblies first, then the relevant clamp cap,
liners and detachable rail. support each wire while releasing its WAGO
terminal. allow the full 14 mm XT30 withdrawal and the SH/GH housing
withdrawal space. screw, liner and guide fit still need printed coupons,
pull tests and a dressed-harness deflection check.

## connector positions

installed top-view coordinates use the same origin as the board layout.
rotations follow KiCad. the component export includes both sides of the
boards.

| board | part | x | y | rotation / side |
| --- | --- | ---: | ---: | --- |
| center | J2452, right auxiliary rails | 282.45 | 64.50 | 270, front |
| center | J2462, right return | 281.45 | 80.00 | 180, front |
| center | J54, skin/hinge temperature | 274.00 | 75.00 | 180, front |
| center | J2071, protected BMS power | 111.45 | 173.848 | 270, front |
| right | J2453, auxiliary rails | 320.55 | 64.50 | 90, front |
| right | J2463, return | 324.55 | 115.40 | 90, front |

the right auxiliary wires run above the signal connectors in top view.
the separate return goes around their front ends. J2463 projects about
0.35 mm beyond the front PCB edge; its solder lands remain on the board.
U1760 is underneath the right board at x332.8, y48.7. reserve 1.75 mm below
its solder plane for the 1.45 mm maximum body and 0.3 mm assembly allowance.

all five BMS cable connectors are on top. J2072, J2074 and J2200 face
rearward; J2 and J2201 face right. J2 is the two-contact WAGO at
(218.35,171.448): pin 1 is raw negative, pin 2 is raw positive. J2201
carries the two taps. mounting hardware must not join the return domains.

## wire and case limits

the short looms use Alpha 6715, 18 AWG, with 1.7526 mm maximum OD. the
direct USB pair uses Alpha 6716, 16 AWG, at 2.1082 mm maximum OD. the
current manufacturer pages specify a 5D bend radius; the design checks
the inside radius with another 1% margin. the older 10D figure remains
visible as a separate sensitivity result.

WAGO stripped ends are 8 mm within the specified 7..9 mm range. main-board
links retain their 20..100 mm limits. the USB wires retain 400..420 mm,
including a provisional 2 mm inside each solder cup. verify cut lengths
and stripped ends on a sample before making an assembly template.

the source harness uses main-board top planes at 8 mm and BMS top at
12 mm. the current case translates all four boards down by 1.3 mm. these
are study datums, not a final case-height requirement. changing the
relative board heights requires new wire paths.

the case now lowers the USB front run by 0.5 mm. bend radius and cut length
use the actual fitted CAD curves. the stack calculation includes the open
guide lips beneath the trackpad support, rather than a wire's highest
point anywhere on the board. the current candidate retains a 33.5 mm
deck. complete cooling, trackpad and lid dimensions are needed before
choosing a thinner stack; see the [cooling fit notes](../../mechanical/case-prototype/cooling-fit.md).

the three owned packs are 100 x 60 mm in the saved measurements. their
confirmed listing gives 11 mm nominal thickness, with no maximum tolerance.
measure the finished packs, insulation, tabs and replacement lead exits.
the complete raw-pack harness still has no qualified route.

## rebuild and verify

refresh the native board datums with `gen/export_board_assembly.py`, then
run `gen/generate_power_harness_geometry.py` and `gen/check_power_harness.py`
in the layout environment. the checks reject changed source boards or
routing inputs. the case's pinned inputs must then be refreshed deliberately.
see the [case rebuild instructions](../../mechanical/case-prototype/README.md).

## drawings used

- [Alpha 6715](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6715) and [6716](https://www.alphawire.com/en/products/wire/ecogen/ecowire/6716)
- [WAGO 2060 two-contact terminal](https://www.wago.com/global/pcb-interconnect/pcb-terminal-block/p/2060-452_998-404)
- [AMASS XT30PW-F30 drawing](https://www.china-amass.net/uploads/31.XT30PW-F30-SPEC-2025V0.pdf)

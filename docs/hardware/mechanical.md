# mechanical layout

the base and lid target is 358 x 248 mm. the final height, cooling stack,
board supports, and cable installation still need a measured assembly.
board coordinates below were checked on 6 september 2026.

## recorded parts

| Part | Recorded information | Still needed |
| --- | --- | --- |
| AUO B160QAN03.K panel | 352 x 227 mm | Thickness, protrusions, bezel offsets, mounting, connector datum |
| Three cells | 100 x 60 mm each | Exact identity, thickness, tabs, wiring, cutoff boards, clearance allowance |
| Keyboard rev A | 273.5 x 80.0 x 0.8 mm PCB | Switch/keycap/plate stack, fastening, stiffness |
| JOMAA trackpad | 140 x 105 mm | Height, travel, mounting, plug and bend clearance |
| Speakers | 38 x 18 mm each in plan view | Depth, fastening, acoustic volume and openings |

## packaging

the left, center, and right PCBs use the original shared XY frame. their
nominal widths are 70, 230, and 58 mm, with a depth of 185 mm. the seams
are at x=70 and x=300. each board needs its own structural support.

the two OLED modules mount separately in the case and connect to J41/J45
with wires. their module bodies are not part of the center-board footprint.
the floorplan positions remain a packaging sketch until the case mounts
and cable routes are set.

the BMS is 61.9 x 30.348 mm. it sits in an open notch at the front center,
with its components up and its center at x=185. the installed board spans
x=154.05-215.95 and y=154-184.348. the notch has 1.5 mm inside radii and
1.5 mm board-to-board clearance. the battery row stays at y=188.

the BMS keeps its own mounting points and needs chassis support. the center
board's H24 moved to (149,148), outside the notch. H22 is now (105,70).
the BMS file uses its original coordinates; the installed translation is
(+47.35,+91.448), with no rotation.

the radio outline is about 120 x 70 mm in its own layout frame. its installed
position and the keyboard's assembly transform still need the case model.
the corrected SMA axes are at x=43 and x=108, pointing through the rear
edge at y=20. their centerlines sit 0.38 mm above the PCB top. the connector
bodies extend 9.52 mm beyond that edge and 3.58 mm below the PCB top.
[`radio-datums.json`](../../mechanical/radio-datums.json) records the complete
nominal body envelopes and mounting holes from the saved board. regenerate
it with `gen/export_radio_mechanical.py` using KiCad's Python. add connector
tolerances, the selected antenna plugs and room to tighten them in the case.

the working packaging plan puts the cells across the front band and the
trackpad above them on its own support plate. the keyboard overlaps part of
the compute/cooling area in XY. actual volumes, insulation, click travel,
cell clearance, and fasteners must stay separate. click loads go into the
trackpad supports, not the cells.

the cooler is a Mu cold plate, flat heatpipe, fins, and a blower. measure
the seated module, socket/support plane, TIM, cooler, and keyboard stack
before setting deck height. plan the inlet/exhaust and verify recirculation.
Framework 13 hinges are the working choice; use the actual brackets and
full sweep to place the display cable and case cutouts.

`mechanical/board-layout.svg` shows the current board arrangement. regenerate
it with `gen/export_board_assembly.py` using KiCad's Python. the exporter
checks the BMS conductor alignment and the M.2 socket-to-retainer offsets.
`mechanical/board-placement.json` stores the installed board transforms;
`mechanical/board-datums.json` is the generated mounting and connector data.

`mechanical/floorplan.json` is the current packaging sketch. the layout
planner is `mechanical/layout-planner.html`. reconcile its envelopes
and positions with the current boards when editing the mechanical model.
the sketch does not establish that the depicted fit has been validated.

## mounting and retention

the Mu uses TE `2309411-1` and separate Wurth `9774055243R` M2 supports,
5.5 mm high. socket clips are not the complete structural restraint.
check module contact, cooler loads, screw engagement, and board bow with
actual parts. Wurth specifies a 0.2 N*m maximum; assembly torque still
needs its own fit/process check.

| Ref | Board | Function | X (mm) | Y (mm) |
| --- | --- | --- | ---: | ---: |
| A1 | Center | Mu socket, rotation 90 | 181.3 | 45.0 |
| H1 | Center | Mu M2 support | 238.3 | 76.8 |
| H2 | Center | Mu M2 support | 238.3 | 13.2 |
| H3 | Center | NVMe retainer | 279.98 | 116.0 |
| H4 | Center | Wi-Fi retainer | 261.55 | 167.25 |

the M.2 sockets are MDT420M01001 and MDT420E01001. J10 is at
(196.43,125.25), rotation 90; J40 is at (228,176.5), rotation 90. their
courtyards include the complete 2280 and 2230 card areas. the power parts,
boot button, and programming connector have been moved out of those areas.

the retainer offsets from pad 1, in the socket's local axes, are
(9.25,83.55) for 2280 and (9.25,33.55) for 2230. these match the Mu reference
carrier geometry. the exporter checks the offsets using the actual pad rows,
so changing a socket's rotation cannot silently leave its mounting nut behind.
 H3/H4 use the recorded
Mu reference-carrier 2.5 mm-high M2 nut/standoff geometry, with a 2.75 mm
drill and 5.0 mm solder land. MDT420STD001 has different thread/hole
geometry and is not interchangeable. retain exact sourcing and sample fit.

| Chassis hole | Board | X (mm) | Y (mm) |
| --- | --- | ---: | ---: |
| H10 | Left | 5.0 | 150.75 |
| H11 | Left | 5.0 | 180.75 |
| H12 | Left | 63.8 | 6.1 |
| H16 | Left | 5.0 | 12.85 |
| H14 | Center | 260.0 | 6.0 |
| H21 | Center | 110.25 | 6.05 |
| H22 | Center | 105.0 | 70.0 |
| H23 | Center | 124.1 | 180.4 |
| H24 | Center | 149.0 | 148.0 |
| H25 | Center | 208.85 | 4.95 |
| H26 | Center | 253.15 | 134.5 |
| H13 | Right | 353.0 | 58.75 |
| H15 | Right | 353.0 | 19.65 |
| H17 | Right | 353.0 | 112.05 |
| H27 | Right | 353.316 | 180.611 |

these are file datums, not approval that the split boards have enough
supports. review flex, heavy components, connector loads, boss geometry,
fastening access, and electrical isolation in the chassis model.

the BMS mounting circles are Edge.Cuts geometry. their installed centers are
in `mechanical/board-datums.json`. radio H1-H4 are (24,24), (136,24), (24,86), and (136,86)
in the radio frame; they are different parts from center H1-H4.

## cables and access

the current FFC, keyboard, radio, and J58 datums are in
[cables and connectors](cables-and-connectors.md). include insertion depth,
actuator access, bends, strain relief, and removal paths in the model.

J58 is the trackpad's four solder lands: 1 GND, 2 D-, 3 D+, 4 VBUS. its
cable needs a defined part/gauge, clamp, service loop, bend route, and pull
test. the solder joints must not carry service loads. keep access to the
pack fuse, module screws, programming points, and replaceable cables.

## measurements

| Work | Evidence needed |
| --- | --- |
| Panel and hinges | Dimensioned parts, pivot/sweep, fasteners, connector and bezel geometry |
| Pack | Cell identity/ratings, thickness, tabs, wiring, cutoff assemblies and clearance |
| Mu and cooling | Complete seated height stack, contact/flatness, airflow and thermal measurements |
| Keyboard and trackpad | Actual deck height, mounting stiffness, click travel and clearance |
| Split-board support | Common assembly model with PCB revisions and installed transforms |
| Cables | Measured routing, insertion, bends, strain relief and hinge movement |
| Audio and RF | Speaker volume, mic opening/channel, antenna placement and measured validation |
| Assembly and service | Fastener access, fuse/programming access, replacement paths, weight balance and stiffness |

case cutouts follow the actual board outlines, connector bodies, and
installed transforms. compare the final model to the reviewed PCB revisions
before making the case. the [display harness](display-direct-edp.md) also
has unresolved electrical requirements.

references: [Wurth drawing](https://www.we-online.com/components/products/datasheet/9774055243R.pdf)
and [Mu reference hardware](https://github.com/LattePandaTeam/LattePanda-Mu).

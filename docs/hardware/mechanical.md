# mechanical layout

the base and lid target is 358 x 248 mm. the final height, cooling stack,
board supports, and cable installation still need a measured assembly.
main-board coordinates below were checked on 10 september 2026.

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
widths are 70, 227, and 58 mm. the left and center are 185 mm deep; the
right board ends at y=117. the center runs from x=71.5 to x=298.5, leaving
1.5 mm gaps to both I/O boards. the board span stays at 358 mm before case
walls. each board needs its own structural support.

the two OLED modules mount separately in the case and connect to J41/J45
with wires. their module bodies are not part of the center-board footprint.
the floorplan positions remain a packaging sketch until the case mounts
and cable routes are set.

the revised BMS under review is 61.9 x 36.148 mm at its widest bounds. its
installed outline spans x=154.05 to x=215.95 and y=150.2 to y=186.348,
centered at x=185. the small rear extension is tapered. the center board's
notch is already set for it, with its back at y=148.7, 1.5 mm inside radii,
and 1.5 mm board clearance. the battery row stays at y=188. this BMS layout
is still being routed and has not replaced the saved BMS board yet.

the BMS keeps its own mounting points and needs chassis support. the center
board's H24 moved to (149,148), outside the notch. H22 is now (105,70).
the BMS file uses its original coordinates; the installed translation is
(+47.35,+91.448), with no rotation. the main component side faces up;
the isolated-control and raw-probe connectors face down. include their
housings and wire bends below the board. all six BMS supports and fasteners
must be insulating so they cannot bridge its separate ground domains.

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

regenerate `mechanical/board-layout.svg` with `gen/export_board_assembly.py`
using KiCad's Python after the revised BMS is saved. the exporter checks
both BMS connector maps and the M.2 socket-to-retainer offsets, and includes
front- and back-side connector courtyards. the existing public export still
needs that refresh.
`mechanical/board-placement.json` stores the installed board transforms;
`mechanical/board-datums.json` is the generated mounting and connector data.

the same export refreshes board outlines and parts linked to a PCB in
`mechanical/floorplan.json`. the layout planner is
`mechanical/layout-planner.html`. free case parts, cells and cooling parts
remain a packaging sketch. their volumes and assembly fit still need checking.

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
| H3 | Center | NVMe retainer | 273.10 | 97.35 |
| H4 | Center | Wi-Fi retainer | 144.25 | 97.30 |

the M.2 sockets are MDT420M01001 and MDT420E01001. J10 is at
(189.55,106.60), rotation 90; J40 is at (177.80,88.05), rotation -90. their
courtyards include the complete 2280 and 2230 card areas. the power parts,
boot button, and programming connector have been moved out of those areas.

the retainer offsets from pad 1, in the socket's local axes, are
(9.25,83.55) for 2280 and (9.25,33.55) for 2230. these match the Mu reference
carrier geometry. the exporter checks the offsets using the actual pad rows,
so changing a socket's rotation cannot silently leave its mounting nut behind.
H3/H4 use the recorded Mu reference-carrier 2.5 mm-high M2 nut/standoff geometry, with a 2.75 mm
drill and 5.0 mm solder land. MDT420STD001 has different thread/hole
geometry and is not interchangeable. retain exact sourcing and sample fit.

the chassis mounts are H10/H11/H12/H16 on the left, H21 through H26 on the
center, and H13/H15/H17 on the right. H14 and H27 are gone. use the generated
datum file for positions. review flex, heavy components, connector loads,
boss geometry, fastening access and electrical isolation in the chassis model.

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

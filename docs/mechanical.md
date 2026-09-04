# mechanical plan

the base and lid target is 358 x 248 mm. the final height, cooling stack,
board supports, and cable installation still need a measured assembly.
board coordinates below were checked on 4 september 2026.

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

the BMS is about 62 x 30 mm, with its outline at roughly x=106.7-168.6,
y=62.552-92.9 in its current file. the radio outline is about 120 x 70 mm,
at x=20-140, y=20-90 in its file. those are separate layout frames, not
installed chassis positions. the keyboard also needs an assembly transform.

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

the floorplan JSON files are packaging sketches. reconcile their envelopes
and positions with the current boards when editing the mechanical model.
their names do not establish that the depicted fit has been validated.

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

the M.2 sockets are MDT420M01001 and MDT420E01001. H3/H4 use the recorded
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
| H13 | Right | 353.0 | 58.75 |
| H15 | Right | 353.0 | 19.65 |
| H17 | Right | 353.0 | 112.05 |

these are file datums, not approval that the split boards have enough
supports. review flex, heavy components, connector loads, boss geometry,
fastening access, and electrical isolation in the chassis model.

the BMS mounting circles are Edge.Cuts geometry and need an installed
mounting drawing. radio H1-H4 are (24,24), (136,24), (24,86), and (136,86)
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

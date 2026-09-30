# bms order files

this is the pcbway package for the four-layer bms. the exact source files,
checks and output hashes are recorded in `manifest.json` and `SHA256SUMS.txt`.
these are checked prototype files. pcbway has not reviewed or quoted this
package yet, and no order has been submitted.

## uploads

- `bms_GERBERS.zip`: bare-board fabrication files, including separate plated
  and unplated drills. all four copper layers are included.
- `BOM.csv`: 125 fitted parts, grouped into 60 part numbers.
- `CPL.csv`: 124 smt placements, 78 on top and 46 underneath.
- `through-hole-positions.csv`: J2, fitted from the top.
- `paste/`: top and bottom stencil artwork. the power-fet stencil windows
  are intentional. the assembler should review stencil thickness and process.
- `bms.ipc`: the bare-board electrical test netlist, with 808 records and 73 nets.
- `assembly/`: both assembly drawings and the test-point map.
- `previews/`: rendered gerbers for inspection. the gerbers control fabrication.

the cpl uses millimetres, the same absolute origin as the gerbers, positive x
to the right and positive y up. bottom x coordinates are not mirrored.
rotations follow kicad. match pin 1 and polarity against the assembly drawings
when pcbway checks the placement preview. the bottom drawing is viewed from
underneath; it is not the coordinate convention used by the cpl.

## board settings

| setting | value |
| --- | --- |
| outline | 61.900 x 36.148 mm, routed contour |
| layers, top to bottom | F.Cu, In1.Cu, In2.Cu, B.Cu |
| material and nominal thickness | standard FR-4, 1.6 mm |
| copper | 1 oz on all four layers, including the inner layers |
| finish | ENIG |
| mask and printing | green mask, white printing on both sides |
| smallest track | 0.10 mm |
| smallest via hole / land | 0.20 / 0.50 mm |
| via annular ring | at least 0.15 mm |
| vias | through vias, tented on both sides |
| filled or capped vias | not required by this layout |
| impedance control | not required |
| electrical test | flying probe against the supplied IPC-D-356 netlist |

the four support holes are unplated circular cutouts in Edge.Cuts. the
NPTH drill file also contains J2's 3 mm locating hole. retain all five.

the cad dielectric entries total about 1.626 mm. they are indicative, not a
custom impedance stackup. quote a standard 1.6 mm build with 1 oz copper on
every layer. the power checks used 35 um copper and 20 um barrel plating;
confirm the finished copper and minimum hole plating before releasing it.
report any lower guaranteed thickness so the power checks can be revisited.

## assembly

fit the exact BOM, including the 0.1% thermal resistors and both current
shunts. substitutions need review. do not replace BQ7791500 with another
threshold option, or LTC4368-1 with the -2 variant.

RS10 is WSL2512R0110FEA18, 11 milliohms, 1%, 2 W. keep that exact
resistance and high-power suffix; a 10 milliohm substitute changes the trip
current. RS11 is WSLP25128L000FEA, 8 milliohms.

F1 is the SCHURTER 3-101-056 HCF fuse, 5 A, fast acting, with a 1000 A
interrupt rating at 125 VDC under the specified L/R condition. it is an SMT
part, not a holder or a removable fuse. use the exact part. test pads are
exposed copper, not components to fit.

the smt count is 381 copper lands. the extra power-fet stencil windows
are apertures within those lands, not extra components or solder joints.
there are 4 soldered through holes, excluding vias and locating holes.
use the supplied paste apertures, check polarity and inspect the power-fet
joints. use lead-free assembly and component-appropriate reflow profiles.

keep the raw, protected and isolated grounds separate. use insulating board
supports. batteries, probe wiring and the mating cable harnesses are not
included in this pcb assembly order. no programming is required on the bms.
powered protection tests will be done during bring-up with simulated cells.

J2 is the right-angle Molex 43045-0400 Micro-Fit header. its mating cable
uses 43025-0400 and tin 43030-0038 contacts. the plug drawing gives a
10.81 mm mated height and 11 mm latch envelope above the PCB. reserve the
plug and cable space shown in the harness notes, including 12.7 mm of free
wire before bending. the front pin row is 9.80 mm from the board edge;
Molex allows 10.16 mm maximum. keep the combined header/edge positioning
error within 0.25 mm toward the edge-clearance limit.

J2072 is the two-pole WAGO 2060-452/998-404. the assembler must solder both
lands for each contact. its body is 4.5 mm high; the wire and release-tool
space are separate. the two bottom JST connectors also need cable access.

pcbway can add process rails and fiducials if their assembly setup needs
them. send the panel drawing for review; do not change the finished outline,
mounting holes or component positions. return the unused bare boards.

## quantity and quote

compare five bare pcbs with one assembled against five bare pcbs with two
assembled. keep the stackup, parts and shipping choices identical. one is
enough to start testing; two gives me a spare. there is no confirmed total
yet. the price needs the parts, assembly setup, attrition, shipping and tax.

check the sourced BOM, part availability, placement preview, finished copper,
hole plating and any panel changes before paying. this package records the
design checks; it does not claim factory acceptance or powered testing.

## checks and regeneration

the saved and refilled boards passed connectivity, schematic parity and the
0.10 mm fabrication checks. footprint pads and drills match the libraries.
all four plotted copper layers match the native geometry within a 2 um
boundary approximation. drill coordinates match their 1 um export grid.
mask openings expose no via holes, including a 0.05 mm outward-margin screen
around the smt mask openings. the stencil openings stay on pads. confirm
the actual mask registration with pcbway; this screen is a design check.

the refilled report retains these warnings: 19 track_not_centered_on_via, 73 lib_footprint_mismatch.
no electrical errors, dangling copper or silkscreen violations were waived.
the existing ERC warnings are recorded separately in the manifest.
the generic fuse and two-pin connector symbols also retain their library-name
filter warnings for F1 and J2072. their exact footprints, pads and pin maps
are checked separately; no netlist mismatch is accepted.
`checks/layout-checks.json` holds the power-path review. the 3 A pack
qualification limit remains in force; a 5 A fuse does not raise it.

install `gen/requirements-bms-fabrication.txt` in a local virtual environment.
run `python gen/generate_bms_pcbway_package.py --output NEW_PACKAGE --work
NEW_SCRATCH_DIRECTORY` from the project root. both paths should be in this
project. kicad cli and its pcbnew python are required. keep an old package
until its replacement has passed. verify a retained package with
`python gen/generate_bms_pcbway_package.py --output manufacturing/bms/pcbway --verify`.
a source edit makes the old package stale.

## supplier references

- [pcbway fabrication limits](https://www.pcbway.com/capabilities.html)
- [pcbway assembly files](https://www.pcbway.com/assembly-file-requirements.html)
- [pcbway confirms assembly from one piece](https://www.pcbway.com/blog/PCB_Basic_Information/PCBWay_Q_A_003___Common_Questions_for_PCBA_Ordering_01.html)
- [molex 43045-0400 header](https://www.molex.com/en-us/products/part-detail/430450400)
- [molex 43025-0400 plug drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43025/430250400_sd.pdf)
- [schurter HCF fuse](https://www.schurter.com/en/datasheet/typ_HCF.pdf)
- [WAGO 2060-452](https://www.wago.com/2060-452/998-404)

# bms order files

this is the pcbway package for the four-layer bms. the exact source files,
checks and output hashes are recorded in `manifest.json` and `SHA256SUMS.txt`.
these are checked prototype files. pcbway has not reviewed or quoted this
package yet, and no order has been submitted.

## uploads

- `bms_GERBERS.zip`: bare-board fabrication files, including separate plated
  and unplated drills. all four copper layers are included.
- `BOM.csv`: 125 fitted parts, grouped into 60 part numbers.
- `CPL.csv`: 123 smt placements, 77 on top and 46 underneath.
- `through-hole-positions.csv`: F1 and J2, both fitted from the top.
- `loose-parts.csv`: one removable 10 A fuse per assembled board.
- `paste/`: top and bottom stencil artwork. the power-fet stencil windows
  are intentional. the assembler should review stencil thickness and process.
- `bms.ipc`: the bare-board electrical test netlist, with 809 records and 73 nets.
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

the four support holes are unplated circular cutouts in Edge.Cuts. the two
3 mm holes in the NPTH drill file are J2's locating holes. retain all six.

the cad dielectric entries total about 1.626 mm. they are indicative, not a
custom impedance stackup. quote a standard 1.6 mm build with 1 oz copper on
every layer. the power checks used 35 um copper and 20 um barrel plating;
confirm the finished copper and minimum hole plating before releasing it.
report any lower guaranteed thickness so the power checks can be revisited.

## assembly

fit the exact BOM, including the 0.1% thermal resistors and both current
shunts. substitutions need review. do not replace BQ7791500 with another
threshold option, or LTC4368-1 with the -2 variant.

F1 in the placement drawing is the Keystone 3568 through-hole holder. the
Littelfuse 0297010.WXNV fuse is a separate purchased part and should be
supplied loose. test pads are exposed copper, not components to fit.

the smt count is 379 copper lands. the 48 extra power-fet stencil windows
are apertures within those lands, not extra components or solder joints.
there are ten soldered through holes, excluding vias and locating holes.
use the supplied paste apertures, check polarity and inspect the power-fet
joints. use lead-free assembly and component-appropriate reflow profiles.

keep the raw, protected and isolated grounds separate. use insulating board
supports. batteries, probe wiring and the mating cable harnesses are not
included in this pcb assembly order. no programming is required on the bms.
powered protection tests will be done during bring-up with simulated cells.

J2 is the tall Mega-Fit connector, not a low-profile header. Molex lists
14.8 mm unmated and 16.78 mm mated height, before cable bending space.
the two bottom JST connectors also need access for their mating cables.

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

the reports retain 73 library graphic differences, eight connected track-end
flags, two single-layer via flags and eight off-centre track/via flags.
the last category was re-enabled for this review. no electrical errors or
silkscreen violations were waived. the 92 existing ERC warnings are recorded
separately. `checks/layout-checks.json` holds the power-path review.

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
- [molex 76829 connector dimensions](https://www.molex.com/en-us/products/series-chart/76829)
- [keystone 3568 fuse holder](https://www.keyelco.com/product.cfm/product_id/306)

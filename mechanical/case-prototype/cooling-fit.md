# cooling and trackpad fit

7 october 2026. this pass keeps the 33.5 mm deck while improving the cooling
layout beneath it. the trackpad's complete height is still needed before
lowering the deck. the cooling parts are a fit study, not a finished or
thermally tested heatsink.

## blower and fin bank

the existing Delta BFB04512HHA-CZ0T stays at (122,52) in the installed top
view, with its bottom 15.7 mm above the case bottom. lower placements hit
the power capacitors, inductors or F190 fuse holder. a useful reduction in
fan height needs a separate electronics placement change. one cradle
anchor moves to leave room for the revised heatpipe.

the [Delta drawing](https://www.delta-fan.com/Download/Spec/BFB04512HHA-CZ0T.pdf)
gives 10.3 +/-0.3 mm thickness. the retained fan's upper envelope is 26.3 mm,
with 3.2 mm to the keyboard PCB. a separate 3 mm inlet
reservation must stay clear. the keyboard carrier has an opening around
the fan and its inlet, with support pads retained outside that opening.

the fin bank stays in front of the hinge line. putting it behind that line
interferes with the bezel when the lid opens. the new envelope is
110 x24 x11.2 mm, with 54 fins at 2 mm pitch and 0.5 mm thickness. the
shorter depth is offset by extra width and fin count. gross broad-face
fin area is 26,438 mm² before heatpipe slots, compared with 23,276 mm² in
the old 50 x46 x12 mm reservation. matching surface area alone does not
establish equal cooling: pressure drop, airflow distribution and the
bonded heatpipe contact still need checking.

the proposed flattened heatpipe uses an 8.1 x3 mm envelope and two 18 mm
centreline-radius bends. it runs around the fan and through slots in the
fin bank. these are supplier requirements to check, not confirmed capacity
or bending limits for a purchased part. the nominal 0.1 mm gap above the
spreader reserves its bonding layer.

## Mu Ultra contact and mounting

the [official module and FIT1049 cooler models](https://github.com/LattePandaTeam/LattePanda-Mu-Ultra/tree/main/Mechanicals)
use different coordinate axes. their three mounting-hole centres match
within 0.0081 mm after rotation and translation. `cooling-datums.json`
retains the exact source revisions and the installed coordinates.

| mounting point | installed x | installed y |
| --- | ---: | ---: |
| left rear | 189.75 | 25.91 |
| left front | 189.75 | 62.56 |
| right | 230.38 | 44.24 |

the module holes are nominally 3.2 mm. the spreader study uses 2.2 mm
clearance holes on that pattern; the final spring, screw, bushing and
support stack still needs choosing. do not transfer the fan cradle's
fastener specification to the processor mount.

the plate now has separate CPU and memory landings. the CPU landing
follows the official cooler's contact area and leaves a nominal 0.101 mm
gap in the reference geometry. the memory landings reserve 0.5 mm for
compressed pads. the main underside sits 0.5 mm above the tallest nominal
module components. these model gaps do not define pad compression,
flatness tolerances, allowable package pressure or PCB bending loads.

both the [226V](https://www.intel.com/content/www/us/en/products/sku/240960/intel-core-ultra-5-processor-226v-8m-cache-up-to-4-50-ghz/specifications.html)
and [256V](https://www.intel.com/content/www/us/en/products/sku/240954/intel-core-ultra-7-processor-256v-12m-cache-up-to-4-80-ghz/specifications.html)
are listed at 17 W processor base power and 37 W maximum turbo power.
the module's other losses are additional. this CAD work does not lower
either processor's power limit or establish that the proposed cooler can
hold those loads. qualify the complete heatpipe, fins, duct and fan on
both modules, with the lid at the intended operating angles.

## trackpad and local height budget

the user-confirmed purchase is
[AliExpress item 3256808869212952](https://www.aliexpress.us/item/3256808869212952.html).
the saved measured outline is 140 x105 mm. complete thickness, feet,
click mechanism, connector and plug projection remain unmeasured. the
5 mm body, 1 mm click travel and 2 mm underside allowance remain marked
as assumptions in `assembly.json`.

the stack calculation now considers only wires and guides that pass
beneath the trackpad support. it includes the open guide lips and checks
bare wire beyond each guide end. a high point elsewhere on a wire no
longer sets the trackpad stack height.

the USB front run is lowered by 0.5 mm in this candidate. its cut length,
separation and bend radius are recalculated, including curvature on the
actual fitted CAD edge. the original PCB geometry and all terminal
positions stay fixed. `thickness-study.json` and `harness-height-study.json`
record the resulting budgets; full carrier and part clearance comes from
the separate solid checks.

before lowering the deck, measure the full trackpad and its plugged-in
cable, then check the click motion and independent support. retain the
cell padding and swelling space. a clean case intersection report is
not a thermal qualification or a substitute for those measurements.

# fan wiring and feet

the smaller Delta fan keeps J52's existing four connections. this case
layout uses BFB04512HHA-DV52; the saved board text still names CZ0T. the
electrical pin map is the same. no board, schematic or firmware edits
are included in this mechanical pass.

| J52 pin | connection | Delta lead |
| --- | --- | --- |
| 1 | ground | black |
| 2 | fused 12 V | red |
| 3 | tachometer | white |
| 4 | PWM | yellow |

the [Delta drawing](https://www.delta-fan.com/Download/Spec/BFB04512HHA-DV52.pdf)
specifies 150 +/-10 mm of 32 AWG wire. the
[JST GH contacts](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf) accept
26 to 30 AWG, so the factory fan wires cannot go straight into those crimps.

use one GHR-04V-S housing and four
[AGHGH28K305 pre-crimped leads](https://gam-gec.com/wp-content/uploads/2018/10/GAM-048.pdf).
each has two SSHL-002T-P0.2 contacts on 304.8 +/-5 mm of black 28 AWG
UL1571 wire. keep one end and trim the other after dressing the route.
mark both ends with their pin numbers first. wire colours alone cannot
identify these four black extension leads.

splice to the fan leads outside the case. the four joints are staggered
and individually insulated with
[RNF-3000-1.5/0.5-0-SP](https://www.te.com/en/product-5677554004.html).
the tubing starts at 1.5 mm minimum inside diameter and recovers to
0.5 mm maximum. keep the bare joint within 1.25 mm diameter and use
12 mm pieces over the short joints. check coverage and grip on the actual
wire insulation, and keep recovery heat away from the fan and housing.

the model allows a 3.2 mm dressed bundle and 5.2 mm across the splice
region. these are limits to check on the completed loom, not measurements
of a built harness. `fan-harness-checks.json` gives the calculated cut
schedule, including provisional 3 mm splice laps and 4 mm hidden at J52.
fit the actual leads before final trimming.

## route and supports

the wires leave the side-entry connector toward the rear, turn back along
the side of the module and pass beneath the heatpipes. farther right, the
route moves in front of the pipes and rises over the power guides. it
then drops beside the fan and turns into its factory lead opening.

the middle run is 14 mm above the base bottom. the full NVMe 2280 and
Wi-Fi 2230 areas are now reserved to the existing 6 mm installed-height
limit above the motherboard. the earlier model only contained the sockets
and retainers. these are selection volumes, not measurements of the cards;
confirm the chosen modules, antenna plugs and service motion separately.

five guides on the keyboard carrier support the loop, middle run and
raised crossover. their arms release sideways. a separate brace beside
the fan supports the splice region and shares the front-inner fan mount.
its 1 mm plate replaces the top millimetre of that spacer, keeping the
fan at the same height. the separate floor clamp holds the fan end, with a
removable cap, soft liner and two M2 x 8 screws. the M2 x 3 insert and
washer dimensions use the same fit allocations as the fan mounts.
the clamp screws are [ISO 7045 / DIN 7985H pan heads](https://www.westfieldfasteners.co.uk/Bolts-Screws-Metric/Machine-Screw-Phillips-Pan-M2x8-A2-Stainless.html),
with the modeled 4 mm head diameter and 1.8 mm head-height allowance.
match the small washers to the stated 4.5 mm outside diameter and 0.3 mm
thickness before checking the screw stack.
the inspection model contains installed insert cavities, not finished
heat-set pilots. the liner is a clearance representation; choose its free
thickness to grip the measured loom with light compression at the cap stop.
the clip, liner and clamp need a dressed pull test and
temperature test before picking the final material and screw torque.
fit removable guide liners or sleeves to the measured loom so it stays
within the 0.2 mm positioning budget. the maximum bundle diameters are
not a substitute for measuring the actual finished harness.

fan replacement now includes the cable: expose J52 by removing the
keyboard assembly and carrier, release the guides, unplug the housing,
then remove the fan clamp cap and outlet bridge. remove the fan screws
and lift out the fan, brace and disconnected harness. the exact keyboard removal
sequence still depends on its finished support and cables.

J73 and J421 use explicit installed-height allocations in this route.
release the nearby harness before servicing the programming port or
speaker connector. those mating cables and their full removal paths are
not qualified by the bare connector height check.

before connecting the fan, check all four wires end to end and for shorts.
the completed power pair, including contacts and splices, has a 0.5 ohm
loop-resistance acceptance limit at 25 C. that corresponds to 0.13 V at
0.26 A. verify the voltage drop with a lead-compensated measurement or a
known load. the existing 25 kHz open-drain PWM and two-pulse tach interface
still need checking with the actual fan and extension.

## feet and intake clearance

the foot candidate is [3M SJ5344](https://www.3m.co.uk/3M/en_GB/p/dc/v100720231/),
also sold as the 16-piece SJ5344BL pack. it is a clear 19.1 mm round foot,
4.1 mm high, with A-20 acrylic adhesive. the
[manufacturer drawing](https://multimedia.3m.com/mws/media/117314O/3m-bumpon-protective-products-molded-shapes-colored-and-clear.pdf)
gives +/-0.5 mm dimensional tolerance without the release liner.

four feet sit near the corners and a fifth sits beside the intake. none
cover the grille or the fin screw access. the CAD uses cylindrical outer
envelopes, not the exact rounded rubber profile. the nominal complete
height becomes 37.4 mm with feet; the body remains 33.3 mm without them.

subtracting 0.5 mm dimensional tolerance, a 0.25 mm compression budget
and a 0.25 mm local floor-deflection budget leaves 3.1 mm underneath
the intake. the last two figures are design budgets, not measured foot
or case behaviour. confirm at least 3 mm on a hard flat surface with the
warm, loaded laptop. check adhesion on the finished printed material too.
soft surfaces can still block a bottom intake.

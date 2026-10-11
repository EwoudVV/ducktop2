# cooler supports

10 october 2026. this is the mounting and assembly layout for the smaller
right-side cooler. dimensions use installed X/Y and height H above the
outside of the base floor. the STEP export uses Z = -H.

## fan

| part | position or size |
| --- | --- |
| rear screw | X301.75, Y127.25 |
| front inner screw | X301.75, Y165.75 |
| front outer screw | X340.25, Y165.75 |
| short base bosses | radius 3.1 mm, top H5.5 |
| separate tubular spacers | 4.8 mm outside diameter; two 7.7 mm, front-inner 6.7 mm plus the 1 mm wire brace |
| lower fan-ear seats | H13.2 |
| upper fan ears | H16.7 nominal |
| washers | 4.5 mm outside diameter, 0.3 mm thick, size allocation |
| screws | M2 x 14, ISO 7045 / DIN 7985H, A2 |

the [Westfield screw](https://www.westfieldfasteners.co.uk/Bolts-Screws-Metric/Machine-Screw-Phillips-Pan-M2x14-A2-Stainless.html)
has a listed 4 mm head diameter and 1.6 mm head height. the model keeps
1.8 mm for the head. delivered dimensions and screw-length tolerances
still need checking. the [CNC Kitchen M2 x 3 insert](https://cnckitchenus.store/products/heat-set-insert-m2-x-3-100-pieces)
has a published 3 mm length. its 3.6 mm outer body and 3.2 mm trial pilot
are allocations to confirm on the part and a printed coupon.

the inspection STEP contains the installed insert cavity. it is not the
smaller pilot needed for heat setting, so do not print it as a finished
insert fit. fit the inserts in the short bosses before adding the separate
spacers. full-width tall bosses hit the fan casing.

## fin stack and duct

the rear fin screw is at X353.5, Y121.5; the front one is at X353.5,
Y179. the screws enter from below the base and thread into 2.5 mm thick
solid copper tabs. they do not thread into individual fins.

the [M2 x 8 countersunk screw](https://www.accu.co.uk/phillips-countersunk-screws/65899-SIK-M2-8-A2)
has a 3.8 mm maximum head diameter and a 1.2 mm head height. the nominal
thread engagement in the copper is 2.1 mm. this is geometry only; the
copper thread, case recess and tightening torque need a pull test.

from the 1.2 mm floor upwards, each support has a 3.6 mm G10/FR4 spacer,
the 0.8 mm duct ear and a 0.3 mm insulating washer. the copper tab begins
at H5.9. the duct is held by these screws. the proposed insulating parts
need a material specification and finished-height tolerance; the duct
also needs a material that survives its actual temperature and clamp load.

the cowl has a 0.8 mm floor and roof. its roof reaches H21.5. the 0.25 mm
inlet baffle and 0.05 mm removable foil bridge are separate pieces. the
bridge, split pipe/tab seals and sidewall seal need leak testing. the split
seals are fitted after bench assembly. their cutouts follow nominal parts;
actual compression and adhesive overlaps are not qualified. a metal
bridge also needs insulation and secure edges near the boards.

a small sealing bead fills the clearance around each fin screw through
the duct ear. this is an applied gasket compound, not a machined 0.2 mm
tube. select a noncorrosive removable material for the actual temperature
and nearby electronics. renew these beads after removing the fin screws.

## assembly access

slide the fin/pipe/contact-plate unit into the open exhaust side of the
cowl on the bench. the copper tabs pass through slots that reach that
edge. fit the insulating washers, baffle and seals before installing the
unit. the final CPU attachment sequence depends on the spring hardware.

the two fin screws are accessible from underneath. to replace the fan,
remove the deck and both OLED modules, expose J52 under the keyboard,
release the carrier guide and fan-end clamp, and disconnect the harness.
peel back the short outlet bridge. remove the three fan screws and washers,
then lift the fan, wire-support brace and disconnected loom off the spacers. the nominal model clears a 30 mm lift
at the sampled positions. wiring slack and real tool access still need
checking with the parts in hand.

the complete cooler removal path is not released. it needs the keyboard
support sequence and a finished CPU clamp, not just the fan access result.

## CPU reference still needed

the [FIT1049 cooler](https://www.dfrobot.com/product-3156.html) uses three
spring screws. the published installation directions say to tighten them
gradually and alternately. they do not give the spring force, package-load
limit or a torque for this custom plate. the official geometry gives the
mounting centers at X189.75/Y25.91, X189.75/Y62.56 and X230.38/Y44.24.

before finishing the clamp, record the screw thread and pitch, shoulder
and stop lengths, free and installed spring lengths, spring force over
that travel, post height and how the load returns through the module.
confirm the CPU and memory contact heights, pad compression and package
load limits with the manufacturer. a caliper measurement alone cannot
establish a safe spring load. the current three mounting cylinders are
space reservations, not screws or an approved clamp.

all of these exports remain inspection geometry. the insert fit, cowl
material, seals, clamp and thermal performance need sample testing before
making the final assembly.

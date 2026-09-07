# center board

checked 7 september 2026. this is the eight-layer Mu carrier in
`ducktop2-center.kicad_pcb`. it still has 726 footprints and no tracks or
vias. the separate BMS is four layers and its routing is unchanged.

## placement

the BMS now fits in a front-center notch. the opening runs from x=152.55
to x=217.45, with its back at y=152.5 and 1.5 mm inside radii. the installed
BMS has 1.5 mm clearance from the center board. FPC105 faces it at
(184.251,132.5), rotation 0. all 30 cable conductors line up with the
reversed pin map.

the regulator capacitors, feedback networks, inductors, crystals, and gauge
parts are grouped with their circuits. U2 is at (174.5,118). U10 and RS1
are beside the battery interface, with the sense filters kept separate from
the load-current path. RS1 still separates `FG_VSS` from system `GND`;
do not bypass it with a ground pour.

the Mu courtyard is clear apart from its two supports. the M.2 courtyards
now include the 2280 and 2230 cards. their sockets face the mounting nuts,
and the power parts, boot button, and programming connector are outside
the card areas. the case still needs a measured height and cable fit.

J41/J45 are wired JST GH OLED connectors. J310 is at (145,49), rotation
270; J2300 is at (155,67.75), rotation 0. the trackpad lands are at
(141,162.25). the speaker connectors are at (103,171) and (115,171).
see [cables and connectors](cables-and-connectors.md) and the
[mechanical layout](mechanical.md) for the installed datums.

## schematic and footprint fixes

C170 now has the 47u part number `GRM31CR61A476ME15L` on both the
schematic and board. the left USB3-A coupling capacitors C1852/C1853 now
specify real 100n 16 V X7R parts, `GRM155R71C104KA88D`, in the same 0402
footprints. the old part number was 100pF.

the I/O cables use FH41-68S-0.5SH(28), Hirose's compatible replacement for
(05). the JST connector symbols include their mounting pads, so a netlist
update keeps all 18 hold-down pads grounded.

USB data nets use matching P/N suffixes, including the segments through
switches and protection parts. KiCad can now recognize the pairs. the
netlist comparison checked every affected reference and pin before and
after the rename, with no signal-connection changes.

## HDMI power

R40/R41 stay at 75.0k/10.0k, giving 5.10 V nominal. the right board now
has the TPS22948 HDMI 5 V switch and TPD4E05U06 control-line protection,
with the TMDS protection and DDC/HPD translation retained.

the checked rail minimum is 5.01464 V. allowing 27.5 mV for the switch at
55 mA and 50 mV for the board and connectors leaves 4.93714 V, above the
4.80 V requirement. routing has to meet that drop allowance. startup,
short-circuit, reverse-current response, and cable behavior still need
hardware tests.
[TPS56637](https://www.ti.com/lit/ds/symlink/tps56637.pdf),
[TPS22948](https://www.ti.com/lit/ds/symlink/tps22948.pdf).

## routing setup

controlled-impedance routes use F.Cu, In2.Cu, or B.Cu. In2.Cu has ground
on both sides. In5.Cu faces split power islands and is for general routing.
the ground layers reject non-ground tracks. the old disconnected power-pour
placeholders are removed; In4.Cu power distribution will be drawn with the
routes. the same layer rules cover
the center and both I/O boards.

| netclass | outer width / gap, mm | In2.Cu width / gap, mm |
| --- | --- | --- |
| DIFF_85 | 0.183 / 0.1524 | 0.114 / 0.1524 |
| DIFF_90, USB 2.0 and USB 3.x | 0.1796 / 0.2032 | 0.111 / 0.203 |
| DIFF_100 | 0.1521 / 0.254 | 0.091 / 0.254 |

these are the approved geometries in
`manufacturing/mainboard_stackup_release.json`. USB 2.0 now uses the
90-ohm coupled geometry, rather than a width-only single-ended preset.
[TI USB layout guidance](https://www.ti.com/lit/an/spraar7/spraar7.pdf).

`gen/setup_net_classes.py --project all` checks the actual split projects.
add `--apply` to update their project settings. local fanout neckdowns and
uncoupled escapes need their own routing review.

the chassis-hole keepouts use the actual mount positions on each board.
soldered module retainers rely on their footprint and drill clearances.

the existing left-board copper has been preserved. the stricter rules
expose its USB escape widths and pair spacing for correction during routing.
no new routing was added in this preparation pass.

## current checks

| board | physical pad comparison | tracks / vias | native airwires |
| --- | --- | --- | --- |
| center | 3,018 pads match | 0 / 0 | 2,038 |
| left I/O | 1,278 pads match | 144 / 0 | 804 |
| right I/O | 714 pads match | 0 / 0 | 506 |
| BMS | 187 pads match | 730 / 313 | 0 |

the center has no DRC violations beyond the unconnected list. the left
board has 20 existing USB escape-width findings and 31 pair-gap findings;
those need routing changes. its two dangling ends are also existing work.
the right and BMS boards have no copper DRC errors. local silkscreen and
footprint differences remain visible as library-comparison warnings.

ERC has no errors on these four schematics. the remaining main-board
warnings concern grounded configuration pins and cached library symbols.
27 regression tests and all 67 electrical calculations pass.

## checking progress

use the native connectivity count for airwires. KiCad's DRC report caps the
unconnected list at 499, and several other finding categories are capped too.
a smaller displayed list does not establish that the board is clean.
[KiCad DRC source](https://gitlab.com/kicad/code/kicad/-/blob/10.0/pcbnew/drc/drc_engine.cpp).

the current reports are in `verification/generated/routing-prep-2026-09-06/`.
these checks are preparation for routing, not a manufacturing release.

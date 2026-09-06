# center board

checked 5 september 2026. this is the eight-layer Mu carrier board in
`ducktop2-center.kicad_pcb`. the verification pass changed the checking and
import tools. the board and schematics were left untouched.

## current checks

| check | result |
| --- | --- |
| physical footprints | 728, with no duplicate references |
| copper layers | 8 |
| tracks / vias | 0 / 0 |
| native connectivity count | 2,026 airwires |
| ordinary and expanded DRC | 158 errors, 248 warnings |
| unconnected findings listed in the DRC report | 499 |
| schematic ERC | 0 errors, 10 library-symbol warnings |
| physical pad comparisons | 3,000, including repeated and shield pads |
| missing physical pin pads | 0 |
| new reported DRC findings after a copied-board refill | 0 |
| generated schematics match the working files | yes |
| pin-review rows | 1,686 pass, 0 fail |

KiCad 10 caps unconnected-item reports at 499 entries, so that number is
not the full airwire count. use native connectivity for routing progress.
[source: KiCad 10 DRC engine](https://gitlab.com/kicad/code/kicad/-/blob/10.0/pcbnew/drc/drc_engine.cpp). the saved and refilled DRC
runs report no shorts or copper-to-copper clearance violations, but the
placement and board-edge findings still need work.

the ten ERC warnings concern flattened library symbols: U311, U431, and
U914-U921. they match the existing reference-specific classifications.

## board and schematic differences

| item | what needs correcting |
| --- | --- |
| R40 | PCB value is 76.8k; the schematic specifies 75.0k for the 5.10 V rail. settle the HDMI budget before choosing the final value. |
| Q25 | PCB footprint ID names CSD19537; the schematic names CSD17575. the two project library footprints have identical pad positions, sizes, and layer assignments, so relinking does not require moving the pads. |
| 16 other footprint IDs | library prefixes are missing. restore the schematic's qualified IDs and check the actual footprint definitions. |
| 22 value fields | includes R40, missing values in the newer selector parts, and changed descriptions. sync these from the reviewed schematic. |
| J8 and J50 | both remain on the PCB despite `exclude_from_board` in the schematic. |
| 324 pad names on 91 nets | the PCB contains literal `&amp;` in sheet names. the XML reader is corrected; an isolated normalization trial clears every pad-name mismatch. |

the name differences currently form a one-to-one mapping between schematic
and PCB net groups. no split or merged net groups were found. the trial
only fixes names; it does not resolve footprint IDs, values, or extra parts.

## placement work before routing

26 board-edge errors come from FPC102, U913, and C703. FPC102 has 15 affected
shield/mount pads at 0.20 mm clearance. U913 has ten affected pads, including
pads touching the edge. C703's closest pad is 0.07 mm from the edge. the
current board rule is 0.50 mm.

there are also 106 courtyard overlaps, 21 plated-hole/courtyard findings,
and five non-plated-hole/courtyard findings. review these groups first:

- FPC103 and the surrounding passives;
- H22, U750, and C750;
- J422 and SW900;
- J41, J420, J310, and H25;
- J901 and J4 beneath the Mu footprint.

44 courtyard pairs include A1. some parts may fit below the raised Mu,
but that needs an actual height and socket-clearance check. do not move all
of them just to clear the courtyard report.

all footprint anchors are inside the outline. that alone does not prove
that every pad, body, or mounting hole has enough room.

## power and routing constraints

the dielectric thicknesses and outer-layer DIFF_85, DIFF_90, and DIFF_100
settings match `manufacturing/mainboard_stackup_release.json`. the inner-layer
trace geometries are different. set the intended layer-specific widths and
return paths before routing controlled-impedance signals on inner layers.

the current 75k/10k divider gives 5.10 V nominal. with the reference and
resistor corners already used in the calculation, the rail minimum is
5.01464 V. subtracting 2 mV for TPS22975, 205 mV for TPD13S523, and the
50 mV board/connector allowance leaves 4.75764 V at the HDMI connector.
that misses the 4.80 V requirement by about 42 mV. the requirement remains
in the checker and still fails.

sources: [TPS56637 electrical characteristics](https://www.ti.com/lit/ds/symlink/tps56637.pdf)
and [TPD13S523 supply and drop requirements](https://www.ti.com/lit/ds/symlink/tpd13s523.pdf).

the pin review now covers both U15 and U15B and the full selector cascade.
GND is pin 8, CAS is pin 9, INTVCC is pin 10, and VALID1/VALID2 are pins 6/7.
the previous review table still contained the older pin map.
[source: LTC4418 pin functions](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4418.pdf).

R747 is the remaining procurement gap: its generator has no manufacturer or
MPN. the installed cable orientations and lengths also remain open in
[cables and connectors](cables-and-connectors.md).

## check outputs

the reports, source hashes, normalization trial results, and placement plot
are in `verification/generated/center-review-2026-09-05/`. these are regenerated
checks, not a manufacturing release. the complete four-board release check
still fails on the remaining design and assembly findings.

next comes the reviewed board/schematic sync, HDMI power decision, and
connector/mounting clearance work. routing starts after those are resolved.

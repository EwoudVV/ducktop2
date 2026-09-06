# center board

checked 6 september 2026. this is the eight-layer Mu carrier in
`ducktop2-center.kicad_pcb`. routing has not started. the BMS is a separate,
four-layer board.

## current checks

| check | result |
| --- | --- |
| footprints | 726, with no duplicate references |
| copper layers | 8 |
| tracks / vias | 0 / 0 |
| native connectivity | 2,020 airwires |
| DRC after refilling the working board | 61 errors, 240 warnings |
| copper clearance, hole clearance, and copper-to-edge errors | 0 |
| unconnected findings shown in DRC | 499 |
| schematic ERC | 0 errors, 10 library-symbol warnings |
| regression tests | 23 pass |
| electrical calculations | 67 pass |

the remaining errors are 55 courtyard overlaps, three plated-hole/courtyard
findings, and three non-plated-hole/courtyard findings. the warnings are
mostly silkscreen, with ten isolated-copper warnings.

KiCad caps unconnected reports at 499 entries. use the native connectivity
count to track routing, and use the report to locate problems.
[KiCad DRC source](https://gitlab.com/kicad/code/kicad/-/blob/10.0/pcbnew/drc/drc_engine.cpp).

## corrected on the board

the board now has the schematic's net names, qualified footprint IDs, and
component values from the reviewed sync. Q25 is linked to CSD17575, R40 is
75.0k, and the excluded J8/J50 connectors are gone. all 3,000 checked pads
matched after the sync, including repeated and shield pads.

FPC102 moved to (73.85, 92.5), U913 to (295.89, 19.12), and C703 to
(72.62, 122.72). those changes cleared all 26 copper-to-edge errors. another
37 placement changes cleared crowded groups around the connectors, power
parts, and mounting holes.

the OLEDs now use wired JST GH connectors. J41 is at (271.5, 27.5), rotation
270; J45 is at (280, 155), rotation 90. the maker header J901 is at
(255.5, 65), rotation 90, alongside the Mu. the OLED modules mount separately
in the case. their cable maps are in [cables and connectors](cables-and-connectors.md).

## HDMI power

R40/R41 stay at 75.0k/10.0k, giving 5.10 V nominal. the right-board schematic
now uses TPS22948 for the HDMI 5 V switch and TPD4E05U06 for control-line and
5 V ESD protection. the TMDS protection and DDC/HPD translation stay in place.
the right PCB still needs this schematic update applied.

at the checked reference and resistor corners, the rail minimum is
5.01464 V. allowing 27.5 mV for the switch at 55 mA and 50 mV for the board
and connectors leaves 4.93714 V, above the 4.80 V requirement. short-circuit,
startup, reverse-current response, and cable behavior still need hardware tests.
[TPS56637](https://www.ti.com/lit/ds/symlink/tps56637.pdf),
[TPS22948](https://www.ti.com/lit/ds/symlink/tps22948.pdf),
[TPD4E05U06](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf).

## routing layers

controlled-impedance routes use F.Cu, In2.Cu, or B.Cu. In2.Cu has GND on
both sides. In5.Cu faces split power islands and is reserved for general
routing. the ground layers reject non-ground tracks.

| netclass | outer width / gap, mm | In2.Cu width / gap, mm |
| --- | --- | --- |
| DIFF_85 | 0.183 / 0.1524 | 0.114 / 0.1524 |
| DIFF_90 | 0.1796 / 0.2032 | 0.111 / 0.203 |
| DIFF_100 | 0.1521 / 0.254 | 0.091 / 0.254 |
| USB2_45 | 0.2248 single-ended width | 0.1313 single-ended width |

the rules use the approved geometries in `manufacturing/mainboard_stackup_release.json`.
fixture checks accept the intended geometry and reject deliberately wrong
widths, gaps, and layers. local fanout neckdowns need their own checked rules.

## remaining placement and field work

C170 was labeled 47u but had a 10u part number. its generator now specifies
`GRM31CR61A476ME15L`, a 47u 10 V X5R part in the same 1206 footprint. the PCB
value and part-number fields still need syncing. C780, U44's local bypass,
also needs moving beside the IC; it is currently far away.

some small overlaps remain around FPC103, U4, F190, the speaker connectors,
and the rear switches. the U12/J2300 group and H21/FPC105 also need room.
under-Mu placements still need the socket, clip, package-height, and service
access checks. the installed BMS position and component-side orientation
are needed to finish FPC105 and the cable route.

the current evidence and placement image are in
`verification/generated/center-corrections-2026-09-06/`. these checks describe
an unfinished layout, not a manufacturing release.

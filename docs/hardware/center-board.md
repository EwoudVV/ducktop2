# center board

updated 10 september 2026. the saved eight-layer board now has 781
footprints. it is 227 mm wide, from x=71.5 to x=298.5. narrowing the center
leaves a 1.5 mm gap to each I/O board while keeping the total span at
358 mm. the center still has no tracks or vias.

## placement

the M.2 retainers now follow their sockets. the maker circuit, its switching
keepouts, and the nearby header/jack group moved inward together. the
lower-right USB-C and speaker group also moved inward to clear the new
edge. the Mu, M.2 sockets, supports, and main cable connector datums stayed
in place.

| part | saved position, mm | rotation |
| --- | --- | --- |
| J10, NVMe socket | 189.55, 106.60 | 90° |
| H3, NVMe retainer | 273.10, 97.35 | 0° |
| J40, Wi-Fi/Bluetooth socket | 177.80, 88.05 | -90° |
| H4, Wi-Fi/Bluetooth retainer | 144.25, 97.30 | 0° |
| J2071, BMS power | 188.60, 143.69 | 0° |
| J2073, BMS control | 176.50, 145.30 | 180° |
| RS1, gauge shunt | 165.95, 135.40 | 180° |
| J41, left OLED | 201.05, 145.00 | 180° |
| J45, right OLED | 210.575, 145.00 | 180° |
| J901, maker connector | 296.30, 6.00 | 180° |
| J2300, radio interface | 82.25, 117.75 | 0° |

RS1 separates FG_VSS from system GND. its sense filters and gauge inputs
need short Kelvin connections. all return wiring must respect the gauge
shunt and the separate BMS control island.

the BMS opening runs from x=152.55 to x=217.45, with its back at y=148.7
and 1.5 mm inside radii. the notch and its two connectors now clear the BMS
thermal circuit's 0.8 mm rear strip. the complete cable and case fit is still
being checked.

## completed checks

the power-converter support parts were placed by their actual functions.
bootstrap, supply, feedback, current-sense and compensation connections
were checked before fitting optional snubbers. bypasses that had been left
behind by earlier IC moves were brought back to their own supply pins.
J4 and J902 also have their native programming-probe keepouts restored.
MK430 has its acoustic-port keepout back too. it blocks tracks, vias and
pours on both outer layers while preserving the microphone's ground ring.

the saved board passes the strict physical, edge, courtyard and silkscreen
checks. its 781 components match the corrected schematic, all source links
survive native save/reload, and all 3,235 pads match the native footprint
definitions within the recorded serialization tolerance. the audit also
corrected older pad-coordinate rounding and missing pad-role/zone metadata.

the remaining advisories are documented library/marking differences,
hybrid mounting-footprint types and generic symbol footprint filters.
there are 2,087 native unconnected items. the complete laptop still needs
the BMS work and the final project-wide checks before main routing starts.

## routing setup

controlled-impedance routes use F.Cu, In2.Cu, or B.Cu. In2.Cu has ground
on both sides. In5.Cu faces split power islands and is for general routing.
the ground layers reject non-ground tracks. In4.Cu power distribution still
needs to be drawn with the routes.

| netclass | outer width / gap, mm | In2.Cu width / gap, mm |
| --- | --- | --- |
| DIFF_85 | 0.183 / 0.1524 | 0.114 / 0.1524 |
| DIFF_90 | 0.1796 / 0.2032 | 0.111 / 0.203 |
| DIFF_100 | 0.1521 / 0.254 | 0.091 / 0.254 |

these settings come from `manufacturing/mainboard_stackup_release.json`.
use `gen/setup_net_classes.py --project all` to check the actual projects.
local escapes, neckdowns, reference transitions, and connector launches
need their own review.

use [build and verify](../build-and-verify.md) for the checks. native
connectivity gives the full airwire count; KiCad's DRC list can stop at 499
unconnected findings. run the six-board routing check after the source,
layout, and mechanical records agree.

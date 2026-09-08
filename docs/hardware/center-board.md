# center board

updated 8 september 2026. this is the eight-layer Mu carrier in
`ducktop2-center.kicad_pcb`. the saved board has 735 footprints. the audit
repairs and manual placement changes are still being brought together;
remaining main-board routing has not started.

## current placement

i moved both M.2 sockets and several power, audio, and service connectors.
these positions are the starting point for the next fit check. the card
retainers and nearby parts still need to follow the sockets.

| part | saved position, mm | rotation |
| --- | --- | --- |
| J10, NVMe socket | 189.55, 106.60 | 90° |
| J40, Wi-Fi/Bluetooth socket | 177.80, 88.05 | -90° |
| J2071, BMS power | 188.60, 144.54 | 0° |
| J2073, BMS control | 176.50, 145.45 | 180° |
| RS1, gauge shunt | 165.95, 135.40 | 180° |
| J41, left OLED | 201.05, 145.00 | 180° |
| J45, right OLED | 210.575, 145.00 | 180° |
| J901, maker connector | 298.00, 6.00 | 180° |

RS1 separates `FG_VSS` from system `GND`. its sense filters and gauge inputs
need short Kelvin connections; a ground pour or cable return must not bypass
it. the BMS control return is a separate isolated interface.

the front-center BMS opening still runs from x=152.55 to x=217.45, with its
back at y=152.5 and 1.5 mm inside radii. the revised BMS outline, connectors,
wire bends, and insulated supports need a combined fit check. H14 was
removed from the center board and H27 from the right board; the support and
keepout records still need to be updated with the placement review.

## applied corrections

the saved center board includes the corrected always-on input protection,
Mu supply parts, isolated BMS control connector, and charge-temperature
gate. the RP2350 regulator uses the reference-design inductor and local
capacitor placement, with copper exclusions beneath its switching region.
the USB protection supply and RTC diode connections were also corrected.

those changes passed the physical and schematic comparisons before the
latest manual moves. that result does not cover the new placement. the
next check includes the actual card outlines, support positions, capacitor
locations, connector access, and every changed pad-net assignment.

## changes still being applied

the generators now include revised power stages, USB power permissions,
separate I/O power looms, and 41- and 51-contact shielded signal interfaces.
some saved schematics and boards still contain the previous parts. update
from a reviewed fresh netlist and preserve the manual placements.

see [power and battery](power-and-battery.md) and
[cables and connectors](cables-and-connectors.md) for the circuit and harness
work. connector selection alone does not qualify the complete high-speed
channel. board routes, cable bends, return paths, and assembled testing are
part of that check.

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

# center board

updated 14 september 2026. the center board is 227 x 185 mm on the
approved eight-layer stack. it has 781 footprints and 3,235 pads. the
nvme and wi-fi pcie routing repairs are complete, but there is still a
lot of main routing to do before this board can be ordered.

## routing so far

the nvme data pairs and reference clock are routed, along with the wi-fi
pcie data and clock connections. their tx capacitors sit on the back of
the board near the sockets. the repairs include pair spacing, length
matching, layer transitions, local ground returns and the nearby control
routes. the repaired signals use F.Cu, In2.Cu and B.Cu.

this checkpoint has 2,863 straight track sections, 33 arcs and 669 vias.
native connectivity counts 1,725 unconnected items. KiCad's DRC list can
stop at 499, so use the native count when checking routing progress.

FPC103 pin 5 still has its original unfinished `/PLTRST_SRC_N` reset
escape. the reset connection to the right board needs routing. the 42 usb
pair-gap reports are fixed, with checked local pad and via exits. the full
usb connections still need routing and length matching. power distribution,
hdmi, the ethernet host link and the remaining main-board connections
are unfinished.

the footprint review is current. the symbol filters now name the actual
packages, and 25 library and footprint-type advisories have exact saved
reviews. the remaining dangling tracks and vias are still part of the
unfinished routing.

the removed nvme ground stub did not break a return connection. four other
ground pieces were entirely covered by longer tracks and have been removed.
that cleanup leaves the copper area and ground-pad/via connections unchanged.

## shape and placement

in the pcb editor, the outline runs from x=102.05 to x=329.05 and from
y=36.55 to y=221.55. the installed layout uses the center translation
`[-30.550001, -36.55]` in
[`board-placement.json`](../../mechanical/board-placement.json). that puts
the center back at x=71.5 to x=298.5, with 1.5 mm gaps to both i/o boards
and a 358 mm board span before case walls.

the bms notch is 64.9 mm wide with 1.5 mm inside radii. its editor side
walls are x=183.10 and x=248.00, and its back is at y=185.25. in the
installed frame those become x=152.55 and x=217.45, with the back at
y=148.7. the notch opens through the front edge.

the positions below use pcb editor coordinates, in mm.

| part | position | rotation |
| --- | --- | --- |
| A1, mu socket | 211.850, 81.550 | 90° |
| J10, nvme socket | 220.100, 143.150 | 90° |
| H3, nvme retainer | 303.650, 133.900 | 0° |
| J40, wi-fi/bluetooth socket | 208.350, 124.600 | -90° |
| H4, wi-fi retainer | 174.800, 133.850 | 0° |
| FPC102, left signals | 109.350, 71.050 | -90° |
| FPC103, right signals | 321.750, 127.050 | 90° |
| J2071, bms power | 219.150, 180.240 | 0° |
| J2073, bms control | 207.050, 181.850 | 180° |
| RS1, gauge shunt | 196.500, 171.950 | 180° |
| J41, left oled | 231.600, 181.550 | 180° |
| J45, right oled | 241.125, 181.550 | 180° |
| J901, maker connector | 326.850, 42.550 | 180° |
| J2300, radio interface | 112.800, 154.300 | 0° |

the m.2 retainers line up with their sockets: the local offsets from pad 1
are 9.25 x 83.55 mm for nvme 2280 and 9.25 x 33.55 mm for wi-fi 2230.
both socket models now sit flat at their 4.2 mm height, with the contacts
and locating pegs aligned to the footprints. the microphone model also
matches its pads and acoustic port.

RS1 separates `FG_VSS` from system `GND`. its sense filters and gauge
inputs need short kelvin connections. return wiring must respect the
shunt and the separate bms control island.

## routing setup

In1.Cu, In3.Cu and In6.Cu are ground. In2.Cu has ground on both sides.
In4.Cu is for power distribution; In5.Cu faces split power islands and
is used for general routing. controlled-impedance signals use F.Cu,
In2.Cu or B.Cu.

| netclass | outer width / gap, mm | In2.Cu width / gap, mm |
| --- | --- | --- |
| DIFF_85 | 0.183 / 0.1524 | 0.114 / 0.1524 |
| DIFF_90 | 0.1796 / 0.2032 | 0.111 / 0.203 |
| DIFF_100 | 0.1521 / 0.254 | 0.091 / 0.254 |

these dimensions come from
[`mainboard_stackup_release.json`](../../manufacturing/mainboard_stackup_release.json).
the ethernet controller's pcie data and reference clock use `DIFF_85`;
its mdi pairs use `DIFF_100`. usb uses `DIFF_90` and hdmi uses `DIFF_100`.

the small gap areas around pads, vias and tuning are checked individually.
`gen/check_center_pcie_coupling.py` checks the local limits and the copper
outside them, plus the completed pcie paths. use
[build and verify](../build-and-verify.md) for the release checks.

## assembly work left

the center frame and m.2 offsets are checked. the complete assembly
export still stops at the saved bms board, which lacks J2072 from the
current harness definition. the generated assembly datums also need a
refresh after that is resolved. connector housings, cable bends, board
supports and the final case height still need a measured fit.

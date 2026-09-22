# bms layout checks

22 september 2026. the bms routing is finished and saved in
[`bms/bms.kicad_pcb`](../bms/bms.kicad_pcb). it is still a four-layer board.
the two middle mounting holes were removed; the four perimeter supports remain.

the [pcbway package](../manufacturing/bms/pcbway/README.md) includes the
checked fabrication and assembly files. the order cleanup widened three
short traces to 0.10 mm, made the printing 0.15 mm thick and moved six vias
away from solder-mask openings. the filled power paths, quiet return and
positive-load connection were checked again after those moves.

| check | result |
| --- | --- |
| native connectivity | 0 unconnected items |
| physical DRC | 0 errors |
| schematic-to-board comparison | 0 mismatches |
| schematic ERC | 0 errors |
| thermal circuit tests | 13 passed |
| electrical calculation checks | 31 passed |
| filled power paths | connected in both grid sizes and both copper-margin cases |
| battery-positive path to the fuse | connected through the actual layers and plated connections, without relying on thin sensing traces |
| quiet raw return | connected, with the load return and Kelvin pickup kept separate |

the checks include the three probe pairs, charge/discharge temperature
references, isolated control cable, retry circuits and regulator returns.
the wide power tracks were converted to fills within their existing outlines
where needed for signal-via clearance. the FET positions and shunt pickups
were preserved. the clearances and rule severities were not relaxed.

the saved board's hashes and counts are in
[`bms-layout.json`](bms-layout.json). the power calculations use nominal
35 um copper at 85 C. the 0.025/0.05 mm grids and 0.05 mm copper erosion are
sensitivity checks, not measurements of a manufactured board. the 8 A
copper screen does not establish an 8 A operating mode.

## remaining warnings

KiCad reports differences from library silkscreen graphics because some
outlines were moved to the fabrication layers and printing was thickened.
there are 73 library graphic warnings. the pads, drills and
component positions were checked separately. it also flags eight short
track ends and two vias connected on one layer. their component nets are
connected; they are not missing pad connections. the report keeps these
warnings visible.

the fabrication check also enables the normally hidden categories. this
adds eight off-centre track/via warnings on connected copper, for 91 warnings
in that report. none are clearance, missing-connection or printing errors.

ERC still has 89 cached-symbol differences and three ground-name warnings
for the separate return domains. these are unchanged from the circuit review.

## assembly and first power

use the [front assembly view](../manufacturing/bms/front-assembly.svg),
[back assembly view](../manufacturing/bms/back-assembly.svg) and
[test-point map](../manufacturing/bms/test-points.csv). the small numbers
on the board match the TPB references. point 14 uses a stacked number.
crowded component references are shown in the assembly views.

cell ratings, the actual harnesses, protection trips, temperature response
and powered operation still need the tests in the
[bring-up plan](../docs/BRINGUP_TEST_PLAN.md). confirm the finished copper,
hole plating and assembly details with the fabricator before ordering.

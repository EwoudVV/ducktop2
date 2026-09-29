# bms layout checks

28 september 2026. the new connector and fuse revision is routed and saved in
[`bms/bms.kicad_pcb`](../bms/bms.kicad_pcb). it is still four layers and
1.6 mm thick, with 149 footprints and the four perimeter mounting holes.

| check | result |
| --- | --- |
| native connectivity | 0 unconnected items |
| physical DRC | 0 errors |
| schematic-to-board comparison | 0 mismatches |
| schematic ERC | 0 errors, 92 existing warnings |
| dangling tracks and vias | 0 warnings |
| silkscreen and copper slivers | 0 warnings |
| routing | 2,187 track segments, 398 vias |
| library pad and drill comparison | 0 differences |
| quiet return | 48 analogue pads, one join to the six bulk-return pads |
| positive shunt pickup | meets the load path at the shunt pad |
| main current paths | all nine checked through the filled copper and plated connections |
| solder-mask openings | no exposed via holes, including the 0.05 mm registration screen |

the cleanup merged straight fragments, removed unused tails and vias, and
shortened unnecessary bends. there are 625 fewer track segments than the
completed routing checkpoint before cleanup. the old connector-shaped
battery-positive pour was removed and its test point now connects directly
to the new connector. nine clipped labels were moved. component positions,
component pads and holes, 3D models, board outline and mounting holes were preserved.
the clearances and rule severities were not relaxed.

the assembly check found two via holes inside the new WAGO solder openings.
both vias now sit outside those openings. three short connections preserve
their layer joins. the via diameters and drill sizes are unchanged, and the
exported masks also pass with a 0.05 mm outward registration allowance.
all nine copper-path estimates were repeated; the largest resistance change
was 0.057 milliohms. the quiet return still passes the same separation check.

C2230 and the reset supervisor now return through the bulk branch. the
analogue return still uses the original single join. removing that join
in the geometry check separates exactly the intended two groups. the
positive current-sense lead has local pour clearances so load current does
not enter it before the shunt. the modelled pickup offset fell from about
5.09 mV to zero at the 5.6 A screening point.

the power check uses a 0.1 mm sheet mesh, nominal 35 um copper and assumed
20 um hole plating. it estimates copper resistance at 20 C and 80 C.
it excludes connector and component resistance and does not predict
temperature rise. 5.6 A is a fault-corner check, not a continuous rating.
the firmware's qualified pack-current ceiling remains 3 A and the hardware
qualification flags remain off.

## remaining warnings

the normal board check retains 73 differences from library graphics and
text. pad and drill geometry matches the libraries. the fabrication pass
also restores 19 off-centre track/via warnings and two generic-symbol
footprint-name filter warnings. the off-centre endpoints are within their
via lands, and the exact footprint and netlist checks pass. all of these
warnings remain in the package reports. ERC
retains 89 cached-symbol differences and three ground-name warnings for
the separate return domains.

source hashes, counts, preservation checks and copper estimates are in
[`bms-layout.json`](bms-layout.json). these replace the old revision's
layout results; the earlier 8 A screen is not evidence for this revision.

## before ordering

the [PCBWay files](../manufacturing/bms/README.md), assembly views and
test-point map now match this saved board, including the new WAGO output,
right-angle raw-pack connector and 5 A Schurter fuse. the package has its
own source hashes and file checksums. any later source edit needs a fresh
export and verification.

the actual cells, harnesses, protection trips, temperature response and
powered operation still need the [bring-up checks](../docs/BRINGUP_TEST_PLAN.md).
finished copper, hole plating and assembly details also need the fabricator's
confirmation. this layout check is not an order release.

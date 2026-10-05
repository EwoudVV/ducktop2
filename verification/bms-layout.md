# bms layout checks

5 october 2026. the BQ76922 revision is routed and saved in
[`bms/bms.kicad_pcb`](../bms/bms.kicad_pcb). it is 80 x 36.148 mm, four layers
and 1.6 mm thick. the board has 201 footprints and four perimeter supports.

| check | result |
| --- | --- |
| native connectivity, without the DRC report limit | 0 unconnected items |
| physical DRC, including fabrication rules | 0 findings |
| dangling tracks and vias | 0 |
| duplicate track geometry | 0 |
| direct check for overlapping copper on different nets | 0 overlaps |
| schematic-to-board pin and part comparison | pass |
| physical pads checked | 608, including paste and mask objects |
| library pad and drill differences | 0 |
| schematic ERC | 0 errors, 2 ground-name warnings |
| routing | 2,100 track segments and 280 vias |
| filled force paths and return separation | pass |

84 duplicate track objects and the unused routing ends were removed.
the cell-tap resistor was turned around to give its input a clear escape.
the monitor fanout now stays out of the main power copper. the 3.3 V branch
uses a checked inner-layer connection instead of crossing the battery feed.

## power copper

the check follows the filled front-layer copper and component lands. thin
bias tracks cannot stand in for a force path. the minimum width checks are
3 mm for VIN, protected positive and FG_VSS, 5 mm for the common drains,
6.25 mm for the raw return and 2.8 mm for raw positive's short BAT-feed
notch. the raw, protected, isolated-control and startup-return domains
remain separate. the isolator barrier has no copper on any layer.

these are geometry checks. the 8 A discharge target and 3 A charging target
still need voltage-drop, temperature, startup and fault measurements on the
finished board with qualified cells and wiring.

## connector access

all five cable connectors are on top and face an edge. the control and
temperature connectors moved off the underside. the battery terminal
faces right, with pin 1 negative and pin 2 positive, matching the new
polarity marks. the schematic and pin checks use that same mapping.

C2281 and two test points moved to clear the connectors. the nearby
routes and pours were repaired, including two raw-return stitches.
the outline, mounting holes and component count are unchanged.

## assembly details

the first assembly has 168 SMT parts. R870, R871 and R872 remain unpopulated
for configuration and bench testing. the three cell probes are separate
wired parts, and the 30 test points are bare pads.

the limiter's 15 plated thermal holes are marked as heat-sink pads in the
project footprint. its copper, holes and paste windows match the original
land pattern. this keeps it correctly classified as an SMT part.

there is one 0.2 mm ground via in the BQ76922 exposed pad. nominal paste does
not overlap its hole, but one paste edge has no registration margin. the
opposite face is tented. the factory must confirm that closure, stencil
alignment and solder-wicking/voiding control, or quote filling/plugging.
the package records this intentional opening separately. ordinary ground
stitches must remain outside the component mask openings.

## remaining schematic notes

the two ERC warnings concern isolated-device ground pins on PACK_NEG_RAW.
their explicit return connections are checked. three generic-symbol
footprint filters do not recognize the custom fuse and WAGO footprint
names; the exact part, footprint and pin checks pass. these notes remain
visible in the fabrication reports.

source hashes, native counts and measured widths are in
[`bms-layout.json`](bms-layout.json). the [prototype files](../manufacturing/bms/README.md)
are tied to that saved source. the [bring-up plan](../docs/BRINGUP_TEST_PLAN.md)
covers programming, calibration and powered tests before the drive links
are fitted. no order or operating qualification is implied by this layout check.

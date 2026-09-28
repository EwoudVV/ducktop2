# power revision

28 september 2026. this is an unfinished checkpoint for the 100 W input
and thinner power wiring. the boards are not ready to order.

the saved center, left, right and BMS schematics now match their revised
connector footprints and pin maps. the main power links use WAGO 2060
spring terminals. the protected BMS pair uses the two-pole version, and
the raw-pack input uses a right-angle Molex 43045-0400 with a new four-pin
map. F1 is now a 5 A Schurter HCF fuse. Alpha 6715 is specified for the
18 AWG links and Alpha 6716 for the 16 AWG direct USB5 loom.

the BMS routing and cleanup are finished. the saved board has zero
unconnected items, zero physical DRC errors and no dangling-copper,
silkscreen or copper-sliver warnings. the quiet return, shunt pickup and
main current paths were checked again after cleanup. the
[layout report](../../verification/bms-layout.md) records the checks and
the remaining library warnings. the main boards remain unfinished.
no new main-board routing was added,
and their outlines, mounting holes and remaining copper were preserved.

the ISL9241 charger, TPS552882 Mu supply, input switches and always-on power
work are in the generators and firmware. those circuits are not yet
integrated into the saved schematics and PCBs. source switching, current
limits and charger communication have host tests, but that does not establish
operation on the laptop. the hardware qualification flags remain off.
the current target firmware is part of this redesign, not a release for
the previous board revision.

all four connector schematic ERC checks have zero errors, with warnings
remaining. schematic-to-board comparisons pass for all four boards. the
firmware host test script and 19 power/control tests pass. physical tests
have not been run.

the case study contains the mounting schedule, Framework hinge supports,
keyboard and trackpad supports, battery trays, lid, cooling reservations,
STEP/STL exports and an interactive viewer. its exports still use the
previous PCB snapshots. the 35 mm study has unresolved harness conflicts;
the final thickness is still undecided. new plug, wire, clamp and service
clearance checks are not finished.

the BMS quote files under `manufacturing/bms/` describe the previous
revision. they must be regenerated for the new connectors, fuse and saved layout.

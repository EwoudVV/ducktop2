# power revision

29 september 2026. this is an unfinished checkpoint for the 100 W input
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
changes are in the generators and firmware. they are not yet integrated into
the saved main-board schematics and PCBs. the placement copy still needs work,
including the charger bootstrap and gate-drive spacing. main-board routing
has not started as part of this revision.

standby power now uses the system rail for its battery feed, so that current
passes through the charger's discharge shunt. an LTC4231 adds active current
limiting and a deliberate reset after a persistent fault. the startup and
fault calculations still depend on measured load, capacitor and temperature
limits. the Mu output uses two 16 milliohm shunts in parallel, and its firmware
budget is now 60 W for the module and display, leaving room for the fan.
these changes still need the final placement and electrical checks.

both official PD exports now include the 20 V / 5 A sink setting. their register
data, binaries, C arrays and archives pass the updated checks and 20 configuration
tests. the firmware host tests, ARM build and linked-image checks pass. no hardware
has been programmed or tested, and the qualification flags remain off. this
firmware belongs to the revised power circuit, not the previous board.

all four connector schematic ERC checks have zero errors, with warnings
remaining. schematic-to-board comparisons pass for all four boards. the
firmware host test script and 19 power/control tests pass. physical tests
have not been run.

the case study contains the mounting schedule, Framework hinge supports,
keyboard and trackpad supports, battery trays, lid, cooling reservations,
STEP/STL exports and an interactive viewer. its exports still use the
previous PCB snapshots. the 35 mm study has unresolved harness conflicts;
the final thickness is still undecided. the saved connector placements now
have [proposed wire paths and service requirements](power-harness-fit.md).
raw-pack lead measurements, clamps and the complete assembly check remain.

the BMS quote files under `manufacturing/bms/` have been regenerated and
checked against the saved board. the assembly review moved two vias clear
of the WAGO solder openings. RS10 now specifies WSL2512R0110FEA18, a valid
11 milliohm part. that correction only changes its ordering code, not the
BMS routing. the rebuilt package passes its source and export checks. factory
review and physical tests remain.

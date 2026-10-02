# bms

2 october: i'm revising the battery path for stronger unplugged performance.
the schematic generator now includes the proposed 8 A circuit, but the saved
BMS schematic, PCB and files below still belong to the previous 3 A design.
i haven't finished the new startup and fault-recovery circuit or its routing.
don't build or order the new revision from these files.

29 september: RS10 now uses the verified WSL2512R0110FEA18 ordering code,
11 milliohms, 1%, 2 W. the assembly BOM and package have been rebuilt and
checked. the resistor value, pads and all routing are unchanged.

the files below now match the saved BMS, including the new connectors,
5 A Schurter fuse and two vias moved clear of the WAGO solder openings.
the copper, holes, mask, paste, netlist, BOM and placements have been checked.
the current results are in the [layout checks](../../verification/bms-layout.md).
see [power revision status](../../docs/hardware/power-revision.md) for the
remaining system and harness work.

- [checked pcbway package](bms_PCBWAY.zip)
- [gerbers and drills](pcbway/bms_GERBERS.zip)
- [assembly BOM](pcbway/BOM.csv) and [SMT placements](pcbway/CPL.csv)
- [order settings and assembly notes](pcbway/README.md)

- [front assembly view](front-assembly.svg)
- [back assembly view](back-assembly.svg), viewed from underneath
- [test-point map](test-points.csv), using the pcb file's coordinates in mm
- [front artwork](front.png) and [back artwork](back.png)

the small numbers beside the test pads match TPB1, TPB2 and so on. point 14
is stacked. use the assembly views for the component references that do not
fit clearly on the silkscreen.

the previews show the exported board artwork without component bodies.
the back is viewed from underneath. use the assembly drawings for placement
and the [harness notes](../../docs/hardware/power-harness-fit.md) for plug
dimensions and access.

the package includes the four copper layers, masks, printing, outline,
separate drill files, electrical test netlist, both paste layers, BOM and
placement files. there are 125 fitted parts: 124 SMT and one through-hole
connector. F1 is a soldered 5 A fuse; the old loose 10 A insert is gone.
the mask check includes a 0.05 mm registration allowance around SMT openings.

compare one and two assembled boards from the same bare-board batch.
pcbway still needs to confirm the sourced parts, finished copper, hole
plating and any assembly-panel details in its quote. no order has been placed.

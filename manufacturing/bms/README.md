# bms

the saved BMS is being revised for the new power wiring and is not ready
to order. the files below belong to the previous routed revision. they
have not been regenerated for the new connector, fuse and placement changes.
see [power revision status](../../docs/hardware/power-revision.md).

- [previous pcbway package](bms_PCBWAY.zip)
- [gerbers and drills](pcbway/bms_GERBERS.zip)
- [assembly BOM](pcbway/BOM.csv) and [SMT placements](pcbway/CPL.csv)
- [order settings and assembly notes](pcbway/README.md)

- [front assembly view](front-assembly.svg)
- [back assembly view](back-assembly.svg), viewed from underneath
- [test-point map](test-points.csv), using the pcb file's coordinates in mm
- [front preview](front.png) and [back preview](back.png)

the small numbers beside the test pads match TPB1, TPB2 and so on. point 14
is stacked. use the assembly views for the component references that do not
fit clearly on the silkscreen.

the previews omit the J2 and J2072 connector bodies because their model
files are not in the installed library. their footprints and pin maps are
included in the layout checks. use the connector drawings for body and
cable clearance.

the package includes the four copper layers, masks, printing, outline,
separate drill files, electrical test netlist, both paste layers, BOM and
placement files. three short traces were widened to 0.10 mm, printing was
thickened to 0.15 mm, and six vias were moved clear of solder-mask openings.

compare one and two assembled boards from the same bare-board batch.
pcbway still needs to confirm the sourced parts, finished copper, hole
plating and any assembly-panel details in its quote. no order has been placed.

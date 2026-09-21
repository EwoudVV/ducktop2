# bms

the four-layer board is routed. [layout checks](../../verification/bms-layout.md)
records the checks on the saved pcb.

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

this folder is a layout and assembly reference, not an order package.
the final gerbers, drills and bare-board test netlist should be exported
from the reviewed revision with the fabricator's confirmed stackup and
assembly settings.

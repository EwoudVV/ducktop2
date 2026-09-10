# parts and cost

updated 10 september 2026. the split design needs a new per-board quote.
there is no reconciled current total yet.

## what the next estimate needs to cover

| Item | Basis for the next quote |
| --- | --- |
| Center, left, and right PCBs | Three separate eight-layer boards, current outlines, approved stackup/impedance requirements |
| BMS PCB | Four layers, 35 um copper, 1.6 mm board; confirm 20 um hole plating in the quote |
| PCBA and component sourcing | Separate BOM/CPL for each board, DNPs, hand assembly, fixtures, setup charges, and spares |
| Radio board | Separate four-layer board and its assembly/components |
| Keyboard | Existing rev A package; check what has already been ordered/received |
| Mu | Exact N305 module/RAM variant and cooling/retention hardware |
| NVMe and Wi-Fi/Bluetooth | Final module identities and capacities |
| Display | Current AUO panel, final compatible eDP harness, mounting and hinge hardware |
| Pack | Exact cells and owned stock, harness, connectors, cutoff assemblies, fuse and mounting |
| Interconnect | Four Molex 503908 signal connectors and their 41/51-contact cables, separate Micro-Fit/XT30 power looms, ground braids, BMS control/probe cables, and keyboard/radio/trackpad cables |
| Case and cooler | Measured design, material/process, fasteners, cold plate, heatpipe, fins, blower |
| Other costs | Shipping, tax, assembly tooling, test fixtures, and replacement parts |

## where part identity lives

schematic fields and generation-time assignments hold manufacturer, MPN,
footprint, DNP, and controlled assembly information. `gen/bom_catalog.py`
supplies many of the passive identities. component inventory tools turn a
schematic export into a sourcing report.

the corrected center and I/O source packets have manufacturer and part-number
fields for their populated board components. run the complete six-board
inventory again after the BMS integration. include off-board items such as
probes, fuse/holder assemblies, crimp contacts, housings, braids and wire.
DNPs and owned assemblies need their intended classification.

one physical footprint is not necessarily one purchased component or one
assembler placement. test points, holes, modules, compound fuse/holder
assemblies, DNPs, and hand-soldered parts affect those counts.

## ownership and sponsorship

check receipts and actual on-hand stock before subtracting owned parts from
the budget. confirm supplier credits, covered costs, and timing from the
correspondence before using them in the total.

## quote record

for each quote, retain supplier/date, exact board revision, layer/finish/copper
options, assembly side and quantities, BOM/CPL versions, substitutions,
shipping/tax, and expiry. keep component cost separate from bare-board fab
and assembly labor so it is not counted twice.

the [build and verification guide](build-and-verify.md) describes the files
needed for an order. the [Forge pitch](forgery_pitch.md) should
use this page's reviewed budget once that quote work is complete.
